#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, Iterator, List, NamedTuple, Optional, Tuple

SHORT = 7
BINARY_PROBE = 8000
IDENT = re.compile(r"(?P<name>[^<]*?) ?<(?P<email>[^>]*)>")
SIGNATURE = re.compile(r"-----BEGIN (?:PGP|SSH) SIGNATURE-----")

EPILOG = """\
allow file lines are <path glob><TAB><literal text>. Blank lines and lines
starting with # are ignored. The text is allowed in matching files, and a match
that falls entirely inside it does not count.
Outside files, the glob matches git:msg, git:author, git:tag or git:branch.
git:author also covers the tagger of a tag.
The glob is matched against the whole path, and * also matches /.

Each hit prints as "<where> <ref>:<loc> denylist:<line>".
  <short sha> <path>:<n>          line n of a file, first seen in that commit
  <short sha> <path>:path         the file name itself
  msg <short sha>:<n>             line n of a commit message
  author <short sha>:<field>      author-name, author-email, committer-name
                                  or committer-email of that commit
  tag <short sha>:<field>         a tag, by the id of its tag object, or of the
                                  commit for a lightweight tag. The field is
                                  name, tagger-name, tagger-email or a message
                                  line
  branch <short sha>:name         a branch, by the commit it points at
A path that matches a term prints as blob-<id> instead of the path, unless
--show is given.

Exit status is 0 when clean, 1 when there are hits and 2 on bad usage.
"""


class UsageError(Exception):
    pass


class Term(NamedTuple):
    lineno: int
    pattern: re.Pattern[str]


class Allow(NamedTuple):
    glob: str
    text: str


class Rules(NamedTuple):
    terms: List[Term]
    allows: List[Allow]


class Hit(NamedTuple):
    where: str
    ref: str
    loc: str
    term: int
    text: str


@dataclass
class Stats:
    refs: int = 0
    commits: int = 0
    blobs: int = 0
    binary: int = 0


def parse_denylist(source: str) -> List[Term]:
    terms = []
    for lineno, raw in enumerate(source.split("\n"), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("re:"):
            try:
                pattern = re.compile(line[3:], re.IGNORECASE)
            except re.error as err:
                raise UsageError(f"denylist line {lineno}: bad regular expression ({err})")
            if pattern.search(""):
                raise UsageError(f"denylist line {lineno}: regular expression matches the empty string")
        else:
            pattern = re.compile(re.escape(line), re.IGNORECASE)
        terms.append(Term(lineno, pattern))
    if not terms:
        raise UsageError("denylist has no terms")
    return terms


def parse_allow(source: str) -> List[Allow]:
    allows = []
    for lineno, raw in enumerate(source.split("\n"), 1):
        if not raw.strip() or raw.startswith("#"):
            continue
        glob, tab, text = raw.partition("\t")
        if not tab or not glob or not text:
            raise UsageError(f"allow file line {lineno}: expected <path glob><TAB><literal text>")
        allows.append(Allow(glob, text))
    return allows


def inside(line: str, match: re.Match[str], allowed: str) -> bool:
    first = max(0, match.end() - len(allowed))
    return any(line.startswith(allowed, start) for start in range(first, match.start() + 1))


def scan_text(text: str, path: str, rules: Rules) -> Iterator[Tuple[int, int, str]]:
    allowed = [a.text for a in rules.allows if fnmatch.fnmatchcase(path, a.glob)]
    for lineno, line in enumerate(text.split("\n"), 1):
        for term in rules.terms:
            for match in term.pattern.finditer(line):
                if not any(inside(line, match, a) for a in allowed):
                    yield lineno, term.lineno, match.group()
                    break


def parse_object(data: bytes) -> Tuple[Dict[str, str], str]:
    head, _, body = data.decode("utf-8", errors="replace").partition("\n\n")
    headers: Dict[str, str] = {}
    for line in head.split("\n"):
        key, _, value = line.partition(" ")
        if key:
            headers[key] = value
    return headers, body


def identities(headers: Dict[str, str], roles: Tuple[str, ...]) -> Iterator[Tuple[str, str]]:
    for role in roles:
        if role in headers:
            found = IDENT.match(headers[role])
            name, email = (found["name"], found["email"]) if found else (headers[role], "")
            yield f"{role}-name", name
            yield f"{role}-email", email


def classify_ref(refname: str) -> Optional[Tuple[str, str]]:
    parts = refname.split("/", 3)
    if len(parts) < 3 or parts[0] != "refs":
        return None
    if parts[1] == "tags":
        return "tag", "/".join(parts[2:])
    if parts[1] == "heads":
        return "branch", "/".join(parts[2:])
    if parts[1] == "remotes" and len(parts) == 4:
        return "branch", parts[3]
    return None


def parse_diff_tree(raw: bytes) -> Iterator[Tuple[str, str, str]]:
    commit = ""
    tokens = iter(raw.split(b"\0"))
    for token in tokens:
        if token.startswith(b":"):
            _, dst_mode, _, oid, _ = token[1:].decode().split(" ")
            path = next(tokens).decode(errors="replace")
            if dst_mode not in ("000000", "160000"):
                yield commit, oid, path
        elif token:
            commit = token.decode()


def git(repo: str, *args: str, data: Optional[bytes] = None) -> bytes:
    try:
        done = subprocess.run(["git", "-C", repo, *args], input=data, capture_output=True, check=True)
    except FileNotFoundError:
        raise UsageError("git is not installed")
    except subprocess.CalledProcessError as err:
        raise UsageError(f"git {args[0]} failed: {err.stderr.decode(errors='replace').strip()}")
    return done.stdout


class ObjectReader:
    def __init__(self, repo: str) -> None:
        self.proc = subprocess.Popen(
            ["git", "-C", repo, "cat-file", "--batch"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    def read(self, oid: str) -> bytes:
        self.proc.stdin.write(oid.encode() + b"\n")
        self.proc.stdin.flush()
        header = self.proc.stdout.readline().split()
        if len(header) != 3:
            raise UsageError(f"cannot read object {oid}")
        return self.proc.stdout.read(int(header[2]) + 1)[:-1]

    def __enter__(self) -> ObjectReader:
        return self

    def __exit__(self, *exc: object) -> None:
        self.proc.stdin.close()
        self.proc.wait()


def scan_repo(repo: str, rules: Rules, reveal_paths: bool) -> Tuple[List[Hit], Stats]:
    hits: List[Hit] = []
    stats = Stats()

    def check(where: str, ref: str, glob: str, text: str, loc: Optional[str] = None) -> None:
        for lineno, term, matched in scan_text(text, glob, rules):
            hits.append(Hit(where, ref, loc or str(lineno), term, matched))

    with ObjectReader(repo) as objects:
        refs = git(repo, "for-each-ref", "--format=%(objectname) %(objecttype) %(refname)")
        for line in filter(None, refs.decode(errors="replace").split("\n")):
            oid, otype, refname = line.split(" ", 2)
            classified = classify_ref(refname)
            if not classified:
                continue
            stats.refs += 1
            kind, name = classified
            ref = oid[:SHORT]
            check(kind, ref, f"git:{kind}", name, "name")
            while kind == "tag" and otype == "tag":
                headers, body = parse_object(objects.read(oid))
                for label, value in identities(headers, ("tagger",)):
                    check("tag", ref, "git:author", value, label)
                check("tag", ref, "git:tag", SIGNATURE.split(body)[0])
                oid, otype = headers["object"], headers["type"]

        commits = git(repo, "rev-list", "--all", "--topo-order", "--reverse").decode().split()
        for commit in commits:
            stats.commits += 1
            headers, message = parse_object(objects.read(commit))
            for label, value in identities(headers, ("author", "committer")):
                check("author", commit[:SHORT], "git:author", value, label)
            check("msg", commit[:SHORT], "git:msg", message)

        # diff-tree prints nothing for a merge commit without -m, and a conflict resolution can add a blob no parent has
        raw = git(
            repo, "diff-tree", "--stdin", "-r", "-m", "--root", "-z", "--no-abbrev",
            data="".join(c + "\n" for c in commits).encode(),
        )
        first_seen: Dict[str, Tuple[str, str]] = {}
        by_blob: Dict[str, Dict[str, str]] = {}
        for commit, oid, path in parse_diff_tree(raw):
            first_seen.setdefault(path, (commit, oid))
            by_blob.setdefault(oid, {}).setdefault(path, commit)

        def label_of(path: str, oid: str) -> str:
            leaks = not reveal_paths and next(scan_text(path, path, rules), None)
            return f"blob-{oid[:SHORT]}" if leaks else path

        for path, (commit, oid) in first_seen.items():
            check(commit[:SHORT], label_of(path, oid), path, path, "path")

        for oid, paths in by_blob.items():
            data = objects.read(oid)
            if b"\0" in data[:BINARY_PROBE]:
                stats.binary += 1
                continue
            stats.blobs += 1
            text = data.decode("utf-8", errors="replace")
            for path, commit in paths.items():
                check(commit[:SHORT], label_of(path, oid), path, text)

    return hits, stats


def read_file(path: str, what: str) -> str:
    try:
        with open(path, encoding="utf-8-sig") as handle:
            return handle.read()
    except OSError as err:
        raise UsageError(f"cannot read the {what} file: {err.strerror}")
    except UnicodeDecodeError:
        raise UsageError(f"the {what} file is not valid UTF-8")


def format_hit(hit: Hit, show: bool) -> str:
    line = f"{hit.where} {hit.ref}:{hit.loc} denylist:{hit.term}"
    return f"{line} {json.dumps(hit.text, ensure_ascii=False)}" if show else line


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="leak_check.py",
        description="Scan a git repository and all of its history for terms from a private denylist.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--denylist", required=True, metavar="FILE",
        help="terms to look for, one per line. Blank lines and lines starting with # are ignored. "
        "A plain line is a case-insensitive literal. A line starting with re: is a case-insensitive "
        "regular expression.",
    )
    parser.add_argument("--allow", metavar="FILE", help="text allowed in matching paths, as described below")
    parser.add_argument("--repo", default=".", metavar="DIR", help="repository to scan (default: current directory)")
    parser.add_argument("--show", action="store_true", help="print the matched text too. For local use only")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        terms = parse_denylist(read_file(args.denylist, "denylist"))
        allows = parse_allow(read_file(args.allow, "allow")) if args.allow else []
        shallow = git(args.repo, "rev-parse", "--is-shallow-repository").strip() == b"true"
        hits, stats = scan_repo(args.repo, Rules(terms, allows), args.show)
    except UsageError as err:
        print(f"leak_check.py: error: {err}", file=sys.stderr)
        return 2
    lines = list(dict.fromkeys(format_hit(hit, args.show) for hit in hits))
    for line in lines:
        print(line)
    if shallow:
        print("leak_check.py: warning: shallow clone, older history was not scanned", file=sys.stderr)
    print(
        f"commits scanned: {stats.commits}, text blobs scanned: {stats.blobs}, refs scanned: {stats.refs}, "
        f"binary blobs skipped: {stats.binary}, hits: {len(lines)}",
        file=sys.stderr,
    )
    return 1 if lines else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
