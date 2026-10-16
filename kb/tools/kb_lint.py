#!/usr/bin/env python3
"""Check the knowledge base.

The pages live in kb/bundle/, an Open Knowledge Format (OKF) v0.2 bundle.
The lint fails when:

- kb/ holds anything but README.md, AGENTS.md, bundle/, sources/, templates/
  and tools/, or bundle/ holds a folder it doesn't know or a folder inside a
  folder.
- A page's frontmatter doesn't parse, or lacks type, title, description or
  generated: { by, at }. Every by is an actor and every timestamp is an ISO
  8601 date and time with its UTC offset.
- A page still uses the v0.1 timestamp field or a Citations heading.
- verified, status, stale_after or superseded_by has a bad value. A page with
  superseded_by has status deprecated.
- A page outside decisions/ has type Decision, or a page in decisions/ has
  another type. The Auto-merge workflow holds decisions/ for the owner.
- A page in questions/, references/ or topics/ lists no sources, a source has
  no resource, or a footnote doesn't match a source id and a definition line.
- A local link points to nothing, or a link leaves the repository. A link that
  starts with / resolves from bundle/ and must stay in it.
- A folder has no index.md, its index.md doesn't list one of its pages, or
  bundle/index.md doesn't list a folder.
- log.md has a ## heading that isn't a date, or its dates aren't newest first.

The frontmatter reader takes the YAML that kb/templates/ uses: key: value
lines, nested blocks indented with spaces, - lists, one-level [a, b] and
{ key: value } values, quotes and # comments.

Usage: python3 kb/tools/kb_lint.py [kb_dir]
"""

import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

FOLDERS = ("decisions", "projects", "questions", "references", "topics")
SOURCED_FOLDERS = {"questions", "references", "topics"}
KB_ENTRIES = ("README.md", "AGENTS.md", "bundle/", "sources/", "templates/", "tools/")
RESERVED = {"index.md", "log.md"}
REQUIRED_TEXT = ("type", "title", "description")
STATUSES = ("draft", "stable", "deprecated")
DECISION = "Decision"

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)[^)]*\)")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
FOOTNOTE_RE = re.compile(r"\[\^([^\]\s]+)\](?!:)")
FOOTNOTE_DEF_RE = re.compile(r"^\[\^([^\]\s]+)\]:")
CITATIONS_RE = re.compile(r"^#{1,6}\s*Citations\s*$", re.MULTILINE)
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$")
ACTOR_RE = re.compile(r"^(?:(?:human|process|team):\S+|[\w.-]+/[^\s/]+)$")
KEY_RE = re.compile(r"^([A-Za-z_][\w.-]*):(?:[ \t]+(.*))?$")
FENCE = ("```", "~~~")
TIMESTAMP_HINT = "is not an ISO 8601 date and time with its UTC offset, such as 2026-10-15T09:30:00-03:00"
ACTOR_HINT = "is not an actor, such as human:owner, process:nightly or librarian/grok-bot"


# Frontmatter


class FrontmatterError(Exception):
    pass


def strip_comment(text):
    quote = None
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'" and text[:i].rstrip()[-1:] in ("", ":", "[", "{", ",", "-"):
            quote = ch
        elif ch == "#" and (i == 0 or text[i - 1] in " \t"):
            return text[:i].rstrip()
    return text.rstrip()


def scalar(text, number):
    text = text.strip()
    if text[:1] in ("'", '"'):
        if len(text) < 2 or text[-1] != text[0]:
            raise FrontmatterError(f"line {number}: a quote isn't closed")
        inner = text[1:-1]
        return inner.replace("''", "'") if text[0] == "'" else inner.replace('\\"', '"')
    if text in ("~", "null"):
        return ""
    return text


def split_flow(inner, number):
    parts, part, quote = [], "", None
    for ch in inner:
        if quote:
            quote = None if ch == quote else quote
        elif ch in "\"'" and not part.strip():
            quote = ch
        elif ch in "[]{}":
            raise FrontmatterError(f"line {number}: a [ ] or {{ }} inside another isn't supported")
        elif ch == ",":
            parts.append(part)
            part = ""
            continue
        part += ch
    if quote:
        raise FrontmatterError(f"line {number}: a quote isn't closed")
    parts.append(part)
    return [p for p in parts if p.strip()]


def value_of(text, number):
    text = text.strip()
    opener, closer = text[:1], {"[": "]", "{": "}"}.get(text[:1])
    if closer is None:
        return scalar(text, number)
    if text[-1:] != closer:
        raise FrontmatterError(f"line {number}: {opener} isn't closed on the same line")
    parts = split_flow(text[1:-1], number)
    if opener == "[":
        return [scalar(part, number) for part in parts]
    mapping = {}
    for part in parts:
        key, colon, value = part.partition(":")
        if not colon or not key.strip():
            raise FrontmatterError(f'line {number}: "{part.strip()}" needs the form key: value')
        mapping[key.strip()] = scalar(value, number)
    return mapping


def is_item(text):
    return text == "-" or text.startswith("- ")


def parse_block(rows, i, indent):
    if is_item(rows[i][2]):
        return parse_list(rows, i, indent)
    return parse_map(rows, i, indent)


def parse_map(rows, i, indent):
    mapping = {}
    while i < len(rows) and rows[i][1] == indent and not is_item(rows[i][2]):
        number, _, text = rows[i]
        match = KEY_RE.match(text)
        if not match:
            raise FrontmatterError(f"line {number}: expected key: value")
        key, rest = match.groups()
        if key in mapping:
            raise FrontmatterError(f'line {number}: "{key}" appears twice')
        i += 1
        if rest:
            mapping[key] = value_of(rest, number)
        elif i < len(rows) and (rows[i][1] > indent or (rows[i][1] == indent and is_item(rows[i][2]))):
            mapping[key], i = parse_block(rows, i, rows[i][1])
        else:
            mapping[key] = ""
    if i < len(rows) and rows[i][1] > indent:
        raise FrontmatterError(f"line {rows[i][0]}: unexpected indentation")
    return mapping, i


def parse_list(rows, i, indent):
    items = []
    while i < len(rows) and rows[i][1] == indent and is_item(rows[i][2]):
        number, _, text = rows[i]
        rest = text[1:].lstrip(" ")
        if not rest:
            i += 1
            if i < len(rows) and rows[i][1] > indent:
                value, i = parse_block(rows, i, rows[i][1])
            else:
                value = ""
        elif KEY_RE.match(rest):
            rows[i] = (number, indent + len(text) - len(rest), rest)
            value, i = parse_map(rows, i, rows[i][1])
        else:
            value = value_of(rest, number)
            i += 1
        items.append(value)
    if i < len(rows) and rows[i][1] > indent:
        raise FrontmatterError(f"line {rows[i][0]}: unexpected indentation")
    return items, i


def parse_frontmatter(lines):
    """Read frontmatter lines into dicts, lists and strings."""
    rows = []
    for number, line in enumerate(lines, 2):
        stripped = line.lstrip(" ")
        if stripped.startswith("\t"):
            raise FrontmatterError(f"line {number}: indent with spaces, not tabs")
        text = strip_comment(stripped)
        if text:
            rows.append((number, len(line) - len(stripped), text))
    if not rows:
        return {}
    mapping, i = parse_map(rows, 0, rows[0][1])
    if i < len(rows):
        raise FrontmatterError(f"line {rows[i][0]}: unexpected indentation")
    return mapping


def split_page(text):
    """Return the frontmatter lines and the body, or None without a closed block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for n, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            return lines[1:n], "\n".join(lines[n + 1:])
    return None


def is_timestamp(value):
    if not isinstance(value, str) or not TIMESTAMP_RE.match(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def is_date(value):
    try:
        return date.fromisoformat(value).isoformat() == value
    except (TypeError, ValueError):
        return False


def is_actor(value):
    return isinstance(value, str) and bool(ACTOR_RE.match(value))


# Body


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


def footnotes(body):
    """Return the footnote labels used in the body and the labels defined."""
    used, defined = [], set()
    for line in outside_fences(body):
        line = INLINE_CODE_RE.sub("", line)
        definition = FOOTNOTE_DEF_RE.match(line)
        if definition:
            defined.add(definition.group(1))
        for label in FOOTNOTE_RE.findall(line):
            if label not in used:
                used.append(label)
    return used, defined


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
        split = split_page(text)
        if split is None:
            self.report(page, "no frontmatter block between --- lines")
            return
        lines, body = split
        try:
            fields = parse_frontmatter(lines)
        except FrontmatterError as err:
            self.report(page, f"frontmatter {err}")
            return
        for field in REQUIRED_TEXT:
            if field not in fields:
                self.report(page, f'missing frontmatter field "{field}"')
            elif not isinstance(fields[field], str):
                self.report(page, f'frontmatter field "{field}" must be text')
            elif not fields[field]:
                self.report(page, f'empty frontmatter field "{field}"')
        self.check_type(page, folder, fields.get("type"))
        self.check_trust(page, fields)
        self.check_lifecycle(page, fields)
        self.check_sources(page, folder, fields, body)

    def check_type(self, page, folder, page_type):
        if not isinstance(page_type, str) or not page_type:
            return
        if folder == "decisions" and page_type != DECISION:
            self.report(page, f'type is "{page_type}", but pages in decisions/ need "{DECISION}"')
        elif folder != "decisions" and page_type.lower() == DECISION.lower():
            self.report(page, f'type "{page_type}" belongs only in decisions/')

    def check_event(self, page, field, event):
        if not isinstance(event, dict):
            self.report(page, f"{field} must be {{ by, at }}")
            return
        if not is_actor(event.get("by")):
            self.report(page, f'{field}.by "{event.get("by", "")}" {ACTOR_HINT}')
        if not is_timestamp(event.get("at")):
            self.report(page, f'{field}.at "{event.get("at", "")}" {TIMESTAMP_HINT}')

    def check_trust(self, page, fields):
        if "timestamp" in fields:
            self.report(page, "timestamp is OKF v0.1. Write generated: { by, at } instead")
        if "generated" not in fields:
            self.report(page, 'missing frontmatter field "generated"')
        else:
            self.check_event(page, "generated", fields["generated"])
        verified = fields.get("verified")
        if verified is None:
            return
        events = verified if isinstance(verified, list) else [verified]
        if not events:
            self.report(page, "verified must be { by, at } or a list of them")
        for event in events:
            self.check_event(page, "verified", event)

    def check_lifecycle(self, page, fields):
        status = fields.get("status")
        if status is not None and status not in STATUSES:
            self.report(page, f'status "{status}" is not {", ".join(STATUSES[:-1])} or {STATUSES[-1]}')
        if "stale_after" in fields and not is_timestamp(fields["stale_after"]):
            self.report(page, f'stale_after "{fields["stale_after"]}" {TIMESTAMP_HINT}')
        replaced_by = fields.get("superseded_by")
        if replaced_by is None:
            return
        target = None
        if isinstance(replaced_by, str) and replaced_by.startswith("/"):
            target = local_target(replaced_by, page, self.bundle)
        if not (target and inside(target, self.bundle) and target.is_file()):
            self.report(page, f'superseded_by "{replaced_by}" is not a page in the bundle, written /folder/page.md')
        if status != "deprecated":
            self.report(page, "superseded_by is set, so status must be deprecated")

    def check_sources(self, page, folder, fields, body):
        if CITATIONS_RE.search(body):
            self.report(page, "a Citations heading is OKF v0.1. List sources in the frontmatter and cite them with footnotes")
        sources = fields.get("sources")
        if sources is None or sources == "":
            sources = []
            if folder in SOURCED_FOLDERS:
                self.report(page, f"no sources. Pages in {', '.join(sorted(SOURCED_FOLDERS))} list theirs in the frontmatter")
        elif not isinstance(sources, list):
            self.report(page, "sources must be a list")
            sources = []
        ids = set()
        for number, source in enumerate(sources, 1):
            if not isinstance(source, dict):
                self.report(page, f"source {number} must be a mapping with a resource")
                continue
            source_id = source.get("id")
            label = f'source "{source_id}"' if source_id else f"source {number}"
            if not source.get("resource"):
                self.report(page, f"{label} has no resource")
            if source_id and not isinstance(source_id, str):
                self.report(page, f"{label}: id must be text")
            elif source_id:
                if source_id in ids:
                    self.report(page, f"{label} appears twice")
                ids.add(source_id)
            if "author" in source and not is_actor(source["author"]):
                self.report(page, f'{label}: author "{source["author"]}" {ACTOR_HINT}')
            if "checked" in source and not is_date(source["checked"]):
                self.report(page, f'{label}: checked "{source["checked"]}" is not a YYYY-MM-DD date')
            if "last_modified" in source and not is_timestamp(source["last_modified"]):
                self.report(page, f'{label}: last_modified "{source["last_modified"]}" {TIMESTAMP_HINT}')
            capture = source.get("capture")
            if capture:
                path = local_target(capture, page, self.bundle) if isinstance(capture, str) else None
                if path is None or not inside(path, self.repo) or not path.is_file():
                    self.report(page, f'{label}: capture "{capture}" is not a file in the repository')
        used, defined = footnotes(body)
        for label in used:
            if label not in ids:
                self.report(page, f"footnote [^{label}] has no source with that id")
            if label not in defined:
                self.report(page, f"footnote [^{label}] has no definition line")

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
        listed = set()
        for target in link_targets(index.read_text(encoding="utf-8")):
            path = local_target(target, index, self.bundle)
            if path is not None:
                listed.add(path / "index.md" if path.is_dir() else path)
        return listed

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
            if not is_date(heading):
                self.report(log, f'heading "{line.strip()}" is not a date written YYYY-MM-DD')
                continue
            day = date.fromisoformat(heading)
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
