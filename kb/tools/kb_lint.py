#!/usr/bin/env python3
"""Check the knowledge base.

The pages live in kb/bundle/, an Open Knowledge Format (OKF) v0.1 bundle.
The lint fails when:

- kb/ holds anything but README.md, AGENTS.md, bundle/, sources/, templates/
  and tools/, or bundle/ holds a folder it doesn't know or a folder inside a
  folder.
- A page lacks type, title, description or timestamp, or its timestamp isn't
  an ISO 8601 date and time with a UTC offset.
- A page outside decisions/ has type Decision, or a page in decisions/ has
  another type. The Auto-merge workflow holds decisions/ for the owner.
- A page in questions/, references/ or topics/ has no Citations heading.
- superseded_by doesn't name a page in the bundle, written /folder/page.md.
- A local link points to nothing, or a link leaves the repository. A link that
  starts with / resolves from bundle/ and must stay in it.
- A folder has no index.md, its index.md doesn't list one of its pages, or
  bundle/index.md doesn't list a folder's index.md.
- log.md has a ## heading that isn't a date, or its dates aren't newest first.

Usage: python3 kb/tools/kb_lint.py [kb_dir]
"""

import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

FOLDERS = ("decisions", "projects", "questions", "references", "topics")
CITED_FOLDERS = {"questions", "references", "topics"}
KB_ENTRIES = ("README.md", "AGENTS.md", "bundle/", "sources/", "templates/", "tools/")
RESERVED = {"index.md", "log.md"}
REQUIRED_FIELDS = ("type", "title", "description", "timestamp")
DECISION = "Decision"

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)[^)]*\)")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
CITATIONS_RE = re.compile(r"^#{1,2}\s*Citations\s*$", re.MULTILINE)
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$")
FENCE = ("```", "~~~")


def frontmatter(lines):
    if not lines or lines[0].strip() != "---":
        return None
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        key, colon, value = line.partition(":")
        if colon:
            fields[key.strip()] = value.strip().strip("\"'")
    return None


def is_timestamp(value):
    if not TIMESTAMP_RE.match(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def outside_fences(text):
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith(FENCE):
            in_fence = not in_fence
        elif not in_fence:
            yield line


def link_targets(text):
    for line in outside_fences(text):
        yield from LINK_RE.findall(INLINE_CODE_RE.sub("", line))


def local_target(target, page, bundle):
    """Return the path a link points to, or None for a web link or an anchor."""
    url = urlsplit(target)
    if url.scheme or url.netloc or not url.path:
        return None
    path = unquote(url.path)
    if path.startswith("/"):
        return (bundle / path.lstrip("/")).resolve()
    return (page.parent / path).resolve()


def inside(path, folder):
    return path == folder or folder in path.parents


class Lint:
    def __init__(self, kb_root):
        self.kb_root = kb_root
        self.repo = kb_root.parent
        self.bundle = kb_root / "bundle"
        self.problems = []

    def name(self, path):
        return path.relative_to(self.repo).as_posix()

    def report(self, path, problem):
        self.problems.append(f"{self.name(path)}: {problem}")

    def check_layout(self):
        allowed = ", ".join(KB_ENTRIES)
        for entry in sorted(self.kb_root.iterdir()):
            label = entry.name + ("/" if entry.is_dir() else "")
            if not entry.name.startswith(".") and label not in KB_ENTRIES:
                self.report(entry, f"doesn't belong in kb/ ({allowed})")
        folders = ", ".join(f"{folder}/" for folder in FOLDERS)
        for entry in sorted(self.bundle.iterdir()):
            if entry.name.startswith(".") or entry.name in RESERVED:
                continue
            if entry.is_dir() and entry.name in FOLDERS:
                for inner in sorted(entry.iterdir()):
                    if inner.is_dir():
                        self.report(inner, "a folder inside a KB folder. Keep pages one folder deep")
            elif entry.is_dir():
                self.report(entry, f"not a KB folder ({folders})")
            else:
                self.report(entry, f"not in a KB folder ({folders})")
        for reserved in sorted(RESERVED):
            if not (self.bundle / reserved).is_file():
                self.report(self.bundle / reserved, "missing")

    def check_page(self, page, text):
        folder = page.relative_to(self.bundle).parts[0]
        fields = frontmatter(text.splitlines())
        if fields is None:
            self.report(page, "no frontmatter block between --- lines")
            return
        for field in REQUIRED_FIELDS:
            if field not in fields:
                self.report(page, f'missing frontmatter field "{field}"')
            elif not fields[field]:
                self.report(page, f'empty frontmatter field "{field}"')
        page_type = fields.get("type", "")
        if folder == "decisions" and page_type and page_type != DECISION:
            self.report(page, f'type is "{page_type}", but pages in decisions/ need "{DECISION}"')
        elif folder != "decisions" and page_type.lower() == DECISION.lower():
            self.report(page, f'type "{page_type}" belongs only in decisions/')
        timestamp = fields.get("timestamp")
        if timestamp and not is_timestamp(timestamp):
            self.report(
                page,
                f'timestamp "{timestamp}" is not an ISO 8601 date and time with its UTC offset, '
                "such as 2026-10-15T09:30:00-03:00",
            )
        if folder in CITED_FOLDERS and not CITATIONS_RE.search(text):
            self.report(page, 'no "## Citations" heading')
        replaced_by = fields.get("superseded_by")
        if replaced_by is not None:
            target = local_target(replaced_by, page, self.bundle)
            if not (replaced_by.startswith("/") and target and inside(target, self.bundle) and target.is_file()):
                self.report(page, f'superseded_by "{replaced_by}" is not a page in the bundle, written /folder/page.md')

    def check_links(self, page, text):
        for target in link_targets(text):
            path = local_target(target, page, self.bundle)
            if path is None:
                continue
            boundary = self.bundle if unquote(urlsplit(target).path).startswith("/") else self.repo
            if not inside(path, boundary):
                where = "bundle/" if boundary == self.bundle else "the repository"
                self.report(page, f'link "{target}" goes outside {where}')
            elif not path.exists():
                self.report(page, f'broken link "{target}"')

    def listed(self, index):
        if not index.is_file():
            return set()
        targets = (local_target(t, index, self.bundle) for t in link_targets(index.read_text(encoding="utf-8")))
        return {target for target in targets if target is not None}

    def check_indexes(self):
        root_listed = self.listed(self.bundle / "index.md")
        for folder in FOLDERS:
            folder_path = self.bundle / folder
            if not folder_path.is_dir():
                continue
            index = folder_path / "index.md"
            if not index.is_file():
                self.report(folder_path, "no index.md")
                continue
            if index.resolve() not in root_listed:
                self.report(index, "not listed in index.md")
            listed = self.listed(index)
            for page in sorted(folder_path.glob("*.md")):
                if page.name not in RESERVED and page.resolve() not in listed:
                    self.report(page, f"not listed in {folder}/index.md")

    def check_log(self):
        log = self.bundle / "log.md"
        if not log.is_file():
            return
        newer = None
        for line in outside_fences(log.read_text(encoding="utf-8")):
            if not line.startswith("## "):
                continue
            heading = line[3:].strip()
            try:
                day = date.fromisoformat(heading)
            except ValueError:
                day = None
            if day is None or day.isoformat() != heading:
                self.report(log, f'heading "{line.strip()}" is not a date written YYYY-MM-DD')
                continue
            if newer and day > newer:
                self.report(log, f"{heading} comes after {newer.isoformat()}, but the newest date goes first")
            newer = day

    def run(self):
        self.check_layout()
        pages = 0
        for path in sorted(self.bundle.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            if path.name not in RESERVED:
                pages += 1
                self.check_page(path, text)
            self.check_links(path, text)
        for doc in ("README.md", "AGENTS.md"):
            path = self.kb_root / doc
            if path.is_file():
                self.check_links(path, path.read_text(encoding="utf-8"))
        self.check_indexes()
        self.check_log()
        return pages


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    kb_root = (Path(args[0]) if args else Path(__file__).parents[1]).resolve()
    if not kb_root.is_dir():
        print(f"{kb_root}: not a directory")
        return 2
    if not (kb_root / "bundle").is_dir():
        print(f"{kb_root}: no bundle/ folder")
        return 2
    lint = Lint(kb_root)
    pages = lint.run()
    for problem in lint.problems:
        print(problem)
    if lint.problems:
        return 1
    print(f"kb lint: {pages} pages, no problems")
    return 0


if __name__ == "__main__":
    sys.exit(main())
