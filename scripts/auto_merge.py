#!/usr/bin/env python3
"""Merge a low-risk pull request once every check on its head commit passes.

.github/workflows/auto-merge.yml runs this file from main whenever a check
workflow finishes, so a pull request can't change the rules that judge it.
It reads the pull request through the GitHub API, as data. It never checks
out or runs the pull request's code.

Usage:
  python3 scripts/auto_merge.py --repo OWNER/REPO --sha SHA [--dry-run]
  python3 scripts/auto_merge.py --repo OWNER/REPO --pr NUMBER [--dry-run]
"""

from __future__ import annotations

import argparse
import difflib
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from typing import Dict, Iterable, List, NamedTuple, Optional, Sequence, Tuple
from urllib.parse import quote

LOW = "low"
HIGH = "high"
BOT = "bot"

# The check workflows. A workflow with path filters is required only when the
# pull request changes a path it watches, as GitHub decides whether it runs.
# auto-merge.yml lists the same workflows by name. A test keeps all three in
# step with .github/workflows.
REQUIRED_WORKFLOWS: Dict[str, Optional[Tuple[str, ...]]] = {
    ".github/workflows/board-tests.yml": ("board/**", ".github/workflows/board-tests.yml"),
    ".github/workflows/bot-chart.yml": None,
    ".github/workflows/kb-lint.yml": None,
    ".github/workflows/scripts-tests.yml": None,
    ".github/workflows/secret-scan.yml": None,
}

# Low-risk paths merge themselves. Everything else waits for the owner. The
# first rule that matches a path wins. Bot files are judged by what changes.
PATH_RULES: Tuple[Tuple[str, str, str], ...] = (
    (".github/**", HIGH, "changes the workflows"),
    ("scripts/**", HIGH, "changes the scripts"),
    ("board/**", HIGH, "changes the board client"),
    ("kb/decisions/**", HIGH, "changes a KB decision"),
    ("kb/AGENTS.md", HIGH, "changes the KB rules for bots"),
    ("kb/tools/**", HIGH, "changes the KB lint"),
    ("kb/templates/**", HIGH, "changes the KB templates"),
    ("kb/**", LOW, ""),
    ("docs/**", LOW, ""),
    ("README.md", LOW, ""),
    ("bots/setup.md", HIGH, "changes setup, which applies every bot change"),
    ("bots/*.md", BOT, ""),
)
OTHER_PATH = "isn't on the list of paths that merge themselves"

# More of these words in a bot file means a bot may get a new power. A word
# doesn't count when a negation comes in the three words before it.
POWER_TERMS: Tuple[Tuple[str, str], ...] = (
    ("merge", r"merg(?:e|es|ed|ing)"),
    ("push", r"push(?:es|ed|ing)?"),
    ("force", r"force[sd]?"),
    ("delete", r"delet(?:e|es|ed|ing)|trash(?:es|ed|ing)?|rm\s+-r"),
    ("unsubscribe", r"unsubscrib\w*"),
    ("publish", r"publish\w*|public"),
    ("deploy", r"deploy\w*"),
    ("buy", r"buy(?:s|ing)?|purchas\w*|checkout|pay(?:s|ing|ment|ments)?"),
    ("transfer", r"transfer\w*"),
    ("approve", r"approv\w*|always\s+allow|allow\s+automatically"),
    ("permission", r"permission\w*|sudo|admin\w*"),
    ("secret", r"tokens?|passwords?|secrets?|credentials?|api\s+keys?"),
    ("connector", r"connectors?|plugins?|install\w*"),
    ("invite", r"invit\w*|rsvp|accept\w*|declin\w*"),
    ("forward", r"forward\w*"),
    ("change mail", r"label\w*|archiv\w*|mark\w*\s+(?:\w+\s+)?(?:as\s+)?(?:read|spam)"),
    ("send email", r"send\w*\s+(?:an?\s+)?(?:e-?mails?|dms?|texts?|sms)"),
    ("post publicly", r"tweet\w*|post\w*\s+(?:on|to)\s+(?:x|twitter|linkedin|bluesky|mastodon|social)"),
    ("local computer", r"local\s+computer|connected\s+computer|osascript"),
    ("calendar write", r"(?:create|add|change|move)\w*\s+(?:an?\s+|the\s+)?(?:calendar\s+)?events?"),
)
# Fewer of these phrases in a bot file means a safety rule went away.
SAFETY_PHRASES: Tuple[Tuple[str, str], ...] = (
    ("data, never instructions", r"never\s+instructions|not\s+instructions"),
    ("the check against main", r"matches\s+bots/[\w.-]+\.md\s+on\s+main"),
)
NEGATIONS = {
    "never", "not", "no", "don't", "dont", "without", "nothing", "nor",
    "cannot", "can't", "won't", "doesn't", "isn't", "neither",
}
CLAUSE_END = re.compile(r"[.,;:()!?\n]")
WORD = re.compile(r"[\w'’-]+")

HOLD_LABEL = "hold"
MAX_FILES = 300
MAX_BOT_LINES = 40
PASSED = {"success"}
SKIPPED_OK = {"success", "skipped", "neutral"}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class FileChange(NamedTuple):
    path: str
    status: str
    previous: Optional[str] = None
    old_text: Optional[str] = None
    new_text: Optional[str] = None


class Routine(NamedTuple):
    folder: str
    enabled: str
    trigger: str


class Decision(NamedTuple):
    action: str  # merge, hold, wait, block or skip
    reasons: Tuple[str, ...]
    pr: Optional[int] = None
    sha: Optional[str] = None


# Paths and tiers


def matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        return path.startswith(pattern[:-2])
    if "*" in pattern:
        return fnmatch.fnmatchcase(path, pattern) and path.count("/") == pattern.count("/")
    return path == pattern


def path_rule(path: str) -> Tuple[str, str]:
    for pattern, tier, reason in PATH_RULES:
        if matches(path, pattern):
            return tier, reason
    return HIGH, OTHER_PATH


def workflow_applies(patterns: Optional[Sequence[str]], paths: Iterable[str]) -> bool:
    if patterns is None:
        return True
    return any(matches(path, pattern) for path in paths for pattern in patterns)


def term_count(text: str, pattern: str) -> int:
    count = 0
    for match in re.finditer(r"(?<![\w-])(?:" + pattern + r")(?![\w-])", text, re.IGNORECASE):
        clause = CLAUSE_END.split(text[: match.start()])[-1]
        before = [w.lower().replace("’", "'") for w in WORD.findall(clause)[-3:]]
        if not NEGATIONS.intersection(before):
            count += 1
    return count


def routines(text: str) -> Dict[str, Routine]:
    found: Dict[str, Routine] = {}
    section = text.split("\n## Routines", 1)
    if len(section) < 2:
        return found
    body = section[1].split("\n## ", 1)[0]
    for chunk in body.split("\n### ")[1:]:
        heading, _, rest = chunk.partition("\n")
        fields = {}
        for line in rest.split("```", 1)[0].splitlines():
            field = re.match(r"\s*-\s+\*\*(\w+):\*\*\s*(.*)", line)
            if field:
                fields[field.group(1).lower()] = " ".join(field.group(2).strip().strip("`").split())
        folder = fields.get("folder") or heading.strip()
        found[folder] = Routine(folder, fields.get("enabled", ""), fields.get("trigger", ""))
    return found


def changed_lines(old: str, new: str) -> int:
    diff = difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=0)
    return sum(1 for line in diff if line[:1] in "+-" and not line.startswith(("+++", "---")))


def bot_reasons(change: FileChange) -> List[str]:
    name = change.path
    if change.status == "added":
        return [f"{name} adds a bot"]
    if change.status == "removed":
        return []
    if change.old_text is None or change.new_text is None:
        return [f"{name} couldn't be read from GitHub"]
    old, new = change.old_text, change.new_text
    reasons = []
    if changed_lines(old, new) > MAX_BOT_LINES:
        reasons.append(f"{name} changes more than {MAX_BOT_LINES} lines")
    before, after = routines(old), routines(new)
    for folder, routine in after.items():
        earlier = before.get(folder)
        if earlier is None:
            reasons.append(f"{name} adds the routine {folder}")
            continue
        if routine.trigger and routine.trigger != earlier.trigger:
            reasons.append(f"{name} changes the trigger of {folder}")
        if routine.enabled == "true" and earlier.enabled != "true":
            reasons.append(f"{name} turns on {folder}")
    for label, pattern in POWER_TERMS:
        if term_count(new, pattern) > term_count(old, pattern):
            reasons.append(f'{name} adds wording about "{label}"')
    for label, pattern in SAFETY_PHRASES:
        if term_count(new, pattern) < term_count(old, pattern):
            reasons.append(f'{name} drops "{label}"')
    return reasons


def classify(changes: Sequence[FileChange]) -> Tuple[str, List[str]]:
    reasons: List[str] = []
    for change in changes:
        paths = [change.path] + ([change.previous] if change.previous else [])
        if change.status == "renamed" and any(matches(p, "bots/*.md") for p in paths):
            reasons.append(f"{change.previous} is renamed to {change.path}")
            continue
        for path in paths:
            tier, reason = path_rule(path)
            if tier == HIGH:
                reasons.append(f"{path} {reason}")
            elif tier == BOT and path == change.path:
                reasons.extend(bot_reasons(change))
    unique = list(dict.fromkeys(reasons))
    return (HIGH if unique else LOW), unique


# Checks


def latest_runs(runs: Iterable[dict]) -> Dict[str, dict]:
    newest: Dict[str, dict] = {}
    for run in runs:
        path = (run.get("path") or "").split("@", 1)[0]
        if path and (path not in newest or run["id"] > newest[path]["id"]):
            newest[path] = run
    return newest


def check_runs(
    runs: Dict[str, dict],
    jobs: Dict[int, List[dict]],
    paths: Sequence[str],
    outside_checks: Sequence[dict] = (),
) -> Tuple[str, List[str]]:
    """Return pass, wait or fail, with the reasons for wait or fail."""
    waiting: List[str] = []
    failed: List[str] = []
    for path, patterns in REQUIRED_WORKFLOWS.items():
        if not workflow_applies(patterns, paths):
            continue
        run = runs.get(path)
        if run is None:
            waiting.append(f"{path} hasn't started")
            continue
        name = run.get("name") or path
        if run.get("status") != "completed":
            waiting.append(f"{name} is still running")
        elif run.get("conclusion") not in PASSED:
            failed.append(f"{name} ended {run.get('conclusion')}")
        else:
            run_jobs = jobs.get(run["id"], [])
            if not any(job.get("conclusion") in PASSED for job in run_jobs):
                failed.append(f"{name} has no passed job")
            for job in run_jobs:
                if job.get("status") != "completed":
                    waiting.append(f"{name} / {job.get('name')} is still running")
                elif job.get("conclusion") not in SKIPPED_OK:
                    failed.append(f"{name} / {job.get('name')} ended {job.get('conclusion')}")
    for path, run in runs.items():
        if path in REQUIRED_WORKFLOWS:
            continue
        name = run.get("name") or path
        if run.get("status") != "completed":
            waiting.append(f"{name} is still running")
        elif run.get("conclusion") not in SKIPPED_OK:
            failed.append(f"{name} ended {run.get('conclusion')}")
    for check in outside_checks:
        if check.get("status") != "completed":
            waiting.append(f"{check.get('name')} is still running")
        elif check.get("conclusion") not in SKIPPED_OK:
            failed.append(f"{check.get('name')} ended {check.get('conclusion')}")
    if failed:
        return "fail", failed
    if waiting:
        return "wait", waiting
    return "pass", []


# GitHub


class GitHub:
    """Calls the GitHub API through gh, which reads GH_TOKEN."""

    def __init__(self, repo: str):
        self.repo = repo

    def _gh(self, *args: str) -> str:
        done = subprocess.run(["gh", *args], capture_output=True, encoding="utf-8")
        if done.returncode != 0:
            raise RuntimeError(f"gh {args[0]} {args[1] if len(args) > 1 else ''} failed: {done.stderr.strip()[:300]}")
        return done.stdout

    def get(self, path: str) -> dict:
        return json.loads(self._gh("api", f"repos/{self.repo}/{path}"))

    def items(self, path: str, jq: str = ".[]") -> List[dict]:
        out = self._gh("api", "--paginate", f"repos/{self.repo}/{path}", "--jq", jq)
        return [json.loads(line) for line in out.splitlines() if line.strip()]

    def text(self, path: str, ref: str) -> Optional[str]:
        try:
            return self._gh("api", f"repos/{self.repo}/contents/{quote(path)}?ref={ref}", "-H", "Accept: application/vnd.github.raw")
        except RuntimeError:
            return None

    def merge(self, number: int, sha: str) -> None:
        self._gh("pr", "merge", str(number), "--repo", self.repo, "--squash", "--match-head-commit", sha)

    def dispatch(self, workflow: str, ref: str) -> None:
        self._gh("workflow", "run", workflow.rsplit("/", 1)[-1], "--repo", self.repo, "--ref", ref)


def open_prs_for(gh: GitHub, sha: str) -> List[int]:
    pulls = gh.items(f"commits/{sha}/pulls?per_page=100")
    return sorted(p["number"] for p in pulls if p.get("state") == "open" and p.get("head", {}).get("sha") == sha)


def file_changes(gh: GitHub, pr: dict, sha: str) -> List[FileChange]:
    files = gh.items(f"pulls/{pr['number']}/files?per_page=100")
    base = None
    changes = []
    for item in files:
        change = FileChange(item["filename"], item["status"], item.get("previous_filename"))
        if path_rule(change.path)[0] == BOT and change.path != "bots/setup.md":
            if base is None:
                base = gh.get(f"compare/{quote(pr['base']['ref'])}...{sha}")["merge_base_commit"]["sha"]
            old_path = change.previous or change.path
            change = change._replace(
                old_text=None if change.status == "added" else gh.text(old_path, base),
                new_text=None if change.status == "removed" else gh.text(change.path, sha),
            )
        changes.append(change)
    return changes


def evaluate(gh: GitHub, number: int, sha: Optional[str] = None) -> Decision:
    pr = gh.get(f"pulls/{number}")
    head = pr["head"]["sha"]
    if sha and head != sha:
        return Decision("skip", ("the PR has a newer commit; its own checks decide",), number, sha)
    sha = head
    default = pr["base"]["repo"].get("default_branch", "main")
    if pr.get("state") != "open" or pr.get("merged"):
        return Decision("skip", ("the PR isn't open",), number, sha)
    if pr.get("draft"):
        return Decision("skip", ("the PR is a draft",), number, sha)
    if pr["base"]["ref"] != default:
        return Decision("skip", (f"the PR doesn't target {default}",), number, sha)
    if (pr["head"].get("repo") or {}).get("full_name") != gh.repo:
        return Decision("skip", ("the PR comes from a fork",), number, sha)
    if any(label.get("name") == HOLD_LABEL for label in pr.get("labels", [])):
        return Decision("hold", (f'the PR has the "{HOLD_LABEL}" label',), number, sha)
    if pr.get("mergeable") is False:
        return Decision("block", ("the PR has a merge conflict",), number, sha)
    if pr.get("changed_files", 0) > MAX_FILES:
        return Decision("hold", (f"the PR changes more than {MAX_FILES} files",), number, sha)

    changes = file_changes(gh, pr, sha)
    if len(changes) != pr.get("changed_files", len(changes)):
        return Decision("hold", ("GitHub didn't list every changed file",), number, sha)
    tier, reasons = classify(changes)
    if tier == HIGH:
        return Decision("hold", tuple(reasons), number, sha)

    paths = [p for c in changes for p in (c.path, c.previous) if p]
    runs = latest_runs(gh.items(f"actions/runs?head_sha={sha}&event=pull_request&per_page=100", ".workflow_runs[]"))
    jobs = {
        run["id"]: gh.items(f"actions/runs/{run['id']}/jobs?filter=latest&per_page=100", ".jobs[]")
        for path, run in runs.items()
        if path in REQUIRED_WORKFLOWS and run.get("status") == "completed"
    }
    outside = [
        c for c in gh.items(f"commits/{sha}/check-runs?per_page=100", ".check_runs[]")
        if (c.get("app") or {}).get("slug") != "github-actions"
    ]
    state, why = check_runs(runs, jobs, paths, outside)
    if state == "fail":
        return Decision("block", tuple(why), number, sha)
    if state == "wait":
        return Decision("wait", tuple(why), number, sha)
    return Decision("merge", (), number, sha)


def merge(gh: GitHub, decision: Decision) -> List[str]:
    """Merge, then rerun the checks on main if main now differs from what they tested."""
    assert decision.pr is not None and decision.sha is not None
    try:
        gh.merge(decision.pr, decision.sha)
    except RuntimeError:
        if gh.get(f"pulls/{decision.pr}").get("merged"):
            return ["it was already merged"]
        raise
    pr = {}
    for _ in range(5):
        pr = gh.get(f"pulls/{decision.pr}")
        if pr.get("merge_commit_sha"):
            break
        time.sleep(2)
    notes = ["merged"]
    merged = pr.get("merge_commit_sha")
    if not merged:
        return notes + ["couldn't read the merge commit, so the checks on main weren't rerun"]
    tested = gh.get(f"git/commits/{decision.sha}")["tree"]["sha"]
    landed = gh.get(f"git/commits/{merged}")["tree"]["sha"]
    if tested != landed:
        default = pr["base"]["ref"]
        for workflow in REQUIRED_WORKFLOWS:
            gh.dispatch(workflow, default)
        notes.append(f"main differs from the tested commit, so the checks are rerunning on {default}")
    return notes


def summary(decision: Decision, notes: Sequence[str] = ()) -> str:
    headline = {
        "merge": "merges itself: low risk, and every check passed",
        "hold": "waits for the owner",
        "wait": "waits for its checks",
        "block": "can't merge until this is fixed",
        "skip": "isn't checked here",
    }[decision.action]
    lines = [f"PR #{decision.pr} {headline}."]
    lines += [f"- {reason}" for reason in decision.reasons]
    lines += [f"- {note}" for note in notes]
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True, help="OWNER/REPO")
    parser.add_argument("--pr", type=int, help="the PR to check")
    parser.add_argument("--sha", help="a head commit whose checks just finished")
    parser.add_argument("--dry-run", action="store_true", help="say what would happen, and merge nothing")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", args.repo):
        parser.error("--repo must be OWNER/REPO")
    if args.sha and not SHA_RE.match(args.sha):
        parser.error("--sha must be a full commit SHA")
    if not args.pr and not args.sha:
        parser.error("give --pr or --sha")

    gh = GitHub(args.repo)
    numbers = [args.pr] if args.pr else open_prs_for(gh, args.sha)
    if not numbers:
        print(f"No open PR has {args.sha} as its head commit.")
        return 0
    report = []
    for number in numbers:
        decision = evaluate(gh, number, args.sha)
        notes: List[str] = []
        if decision.action == "merge" and not args.dry_run:
            notes = merge(gh, decision)
        elif decision.action == "merge":
            notes = ["dry run, so nothing was merged"]
        report.append(summary(decision, notes))
    text = "\n\n".join(report)
    print(text)
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as handle:
            handle.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
