#!/usr/bin/env python3
"""Check the notes in the knowledge base.

Usage: python3 kb/tools/kb_lint.py [kb_dir]
"""

import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlsplit

FOLDER_TYPES = {
    "decisions": "decision",
    "projects": "project",
    "references": "reference",
}
REQUIRED_FIELDS = ("type", "title", "description", "updated")
NOT_NOTES = {"README.md", "AGENTS.md", "templates", "tools"}

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)[^)]*\)")
INLINE_CODE_RE = re.compile(r"`[^`]*`")


def notes(kb_root):
    for path in sorted(kb_root.rglob("*.md")):
        if path.relative_to(kb_root).parts[0] not in NOT_NOTES:
            yield path


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


def is_date(value):
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def link_targets(text):
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
        elif not in_fence:
            yield from LINK_RE.findall(INLINE_CODE_RE.sub("", line))


def check_note(note, kb_root):
    name = note.relative_to(kb_root.parent).as_posix()
    folder = note.relative_to(kb_root).parts[0]
    expected_type = FOLDER_TYPES.get(folder)
    text = note.read_text(encoding="utf-8")
    problems = []

    if expected_type is None:
        folders = ", ".join(f"{f}/" for f in FOLDER_TYPES)
        problems.append(f"{name}: not in a note folder ({folders})")

    fields = frontmatter(text.splitlines())
    if fields is None:
        problems.append(f"{name}: no frontmatter block between --- lines")
    else:
        for field in REQUIRED_FIELDS:
            if field not in fields:
                problems.append(f'{name}: missing frontmatter field "{field}"')
            elif not fields[field]:
                problems.append(f'{name}: empty frontmatter field "{field}"')
        note_type = fields.get("type")
        if expected_type and note_type and note_type != expected_type:
            problems.append(f'{name}: type is "{note_type}", but notes in {folder}/ need "{expected_type}"')
        updated = fields.get("updated")
        if updated and not is_date(updated):
            problems.append(f'{name}: updated "{updated}" is not a YYYY-MM-DD date')

    for target in link_targets(text):
        url = urlsplit(target)
        if url.scheme or url.netloc or not url.path:
            continue
        if not (note.parent / unquote(url.path)).exists():
            problems.append(f'{name}: broken link "{target}"')

    return problems


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    kb_root = (Path(args[0]) if args else Path(__file__).parents[1]).resolve()
    if not kb_root.is_dir():
        print(f"{kb_root}: not a directory")
        return 2
    found = list(notes(kb_root))
    problems = [problem for note in found for problem in check_note(note, kb_root)]
    for problem in problems:
        print(problem)
    if problems:
        return 1
    print(f"kb lint: {len(found)} notes, no problems")
    return 0


if __name__ == "__main__":
    sys.exit(main())
