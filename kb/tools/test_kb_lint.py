import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import kb_lint

LINT = Path(__file__).with_name("kb_lint.py")
REAL_KB = Path(__file__).parents[1]
GENERATED = "{ by: librarian/grok-bot, at: 2026-10-15T09:30:00-03:00 }"
SOURCES = "sources:\n  - id: a-source\n    resource: https://example.com/a\n    checked: 2026-10-15\n"
CITED = "A fact.[^a-source]\n\n[^a-source]: [A source](https://example.com/a).\n"
LOG = "# Log\n\n## 2026-10-15\n\n- **Update**: One line.\n\n## 2026-10-14\n\n- **Ingest**: One line.\n"
TS_HINT = "is not an ISO 8601 date and time with its UTC offset, such as 2026-10-15T09:30:00-03:00"
ACTOR_HINT = "is not an actor, such as human:owner, process:nightly or librarian/grok-bot"


def page(page_type, body="", extra="", **overrides):
    """A page with type, title, description and generated, plus extra frontmatter lines."""
    fields = {"type": page_type, "title": "A page", "description": "One line.", "generated": GENERATED}
    fields.update(overrides)
    lines = [f"{key}: {value}" for key, value in fields.items() if value is not None]
    return "---\n" + "\n".join(lines) + "\n" + extra + "---\n\n" + body


def sourced(page_type, body="", extra="", **overrides):
    """A page that lists a source and cites it."""
    return page(page_type, body + CITED, SOURCES + extra, **overrides)


def index(*names):
    return "# Pages\n\n" + "".join(f"- [{name}]({name.replace(' ', '%20')}) - One line.\n" for name in names)


def root_index(*folders):
    entries = "".join(f"- [{folder}]({folder}/index.md) - One line.\n" for folder in folders)
    return '---\nokf_version: "0.2"\n---\n\n# Knowledge base\n\n## Folders\n\n' + entries


class KbLintTest(unittest.TestCase):
    maxDiff = None

    def make_kb(self, files):
        """Write a KB with a root index, a log and an index for each folder.

        Each folder index lists the pages given for that folder. An entry in
        files replaces a generated file, and None leaves it out.
        """
        tree = {"bundle/index.md": root_index(*kb_lint.FOLDERS), "bundle/log.md": LOG}
        for folder in kb_lint.FOLDERS:
            names = sorted(
                Path(path).name for path in files
                if path.startswith(f"bundle/{folder}/") and path.count("/") == 2
                and Path(path).name not in kb_lint.RESERVED
            )
            tree[f"bundle/{folder}/index.md"] = index(*names)
        tree.update(files)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        kb = Path(tmp.name) / "kb"
        for relative, text in tree.items():
            if text is None:
                continue
            path = kb / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return kb

    def run_lint(self, kb):
        out = io.StringIO()
        with redirect_stdout(out):
            code = kb_lint.main([str(kb)])
        return code, out.getvalue().splitlines()

    def test_clean_kb_passes_and_skips_files_outside_the_bundle(self):
        capture = "    capture: ../../sources/inbox/raw.md\n"
        kb = self.make_kb({
            "README.md": "No frontmatter. [A page](bundle/projects/b.md)",
            "AGENTS.md": "No frontmatter.",
            "templates/reference.md": "---\ntype:\n---\n[missing](nowhere.md)",
            "tools/notes.md": "No frontmatter.",
            "sources/inbox/raw.md": "No frontmatter.",
            "bundle/references/a.md": sourced(
                "Reference",
                "See [the project](../projects/b.md#state), [the same](/projects/b.md) "
                "and [the source](../../sources/inbox/raw.md).\n\n",
                capture,
            ),
            "bundle/projects/b.md": page("Project"),
        })
        self.assertEqual(self.run_lint(kb), (0, ["kb lint: 2 pages, no problems"]))

    def test_the_real_kb_passes(self):
        code, out = self.run_lint(REAL_KB)
        self.assertEqual(code, 0, "\n".join(out))

    def test_reads_the_yaml_forms_the_templates_use(self):
        extra = "\n".join([
            "# A comment line.",
            "tags:",
            "- block-list",
            "- 'quoted # not a comment'",
            "verified:",
            "  - { by: human:owner, at: 2026-10-15T10:00:00Z }",
            "  - by: process:nightly",
            "    at: '2026-10-16T02:00:00+00:00'",
            "status: stable  # a trailing comment",
            "stale_after: 2027-01-01T00:00:00Z",
            "",
        ])
        kb = self.make_kb({
            "bundle/projects/a.md": page(
                "Project", extra=extra,
                title='"A title: with a colon"',
                description="It's fine, and so is #this.",
                generated="\n  by: human:owner\n  at: 2026-10-15T09:30:00-03:00",
            ),
        })
        self.assertEqual(self.run_lint(kb), (0, ["kb lint: 1 pages, no problems"]))
        lines = kb_lint.split_page((kb / "bundle/projects/a.md").read_text())[0]
        fields = kb_lint.parse_frontmatter(lines)
        self.assertEqual(fields["title"], "A title: with a colon")
        self.assertEqual(fields["tags"], ["block-list", "quoted # not a comment"])
        self.assertEqual(fields["generated"], {"by": "human:owner", "at": "2026-10-15T09:30:00-03:00"})
        self.assertEqual(fields["verified"][1], {"by": "process:nightly", "at": "2026-10-16T02:00:00+00:00"})
        self.assertEqual(fields["status"], "stable")

    def test_frontmatter_that_doesnt_parse(self):
        kb = self.make_kb({
            "bundle/projects/a.md": "---\ntype: Project\n\ttitle: Tabbed\n---\n",
            "bundle/projects/b.md": "---\ntype: Project\ntitle: \"Open\n---\n",
            "bundle/projects/c.md": "---\ntype: Project\n  title: Indented\n---\n",
            "bundle/projects/d.md": "---\ntype: Project\ntype: Again\n---\n",
            "bundle/projects/e.md": "---\ntype: Project\ngenerated: { by: [a, b] }\n---\n",
            "bundle/projects/f.md": "---\ntype: Project\njust words\n---\n",
        })
        self.assertEqual(self.run_lint(kb), (1, [
            "kb/bundle/projects/a.md: frontmatter line 3: indent with spaces, not tabs",
            "kb/bundle/projects/b.md: frontmatter line 3: a quote isn't closed",
            "kb/bundle/projects/c.md: frontmatter line 3: unexpected indentation",
            'kb/bundle/projects/d.md: frontmatter line 3: "type" appears twice',
            "kb/bundle/projects/e.md: frontmatter line 3: a [ ] or { } inside another isn't supported",
            "kb/bundle/projects/f.md: frontmatter line 3: expected key: value",
        ]))

    def test_missing_and_empty_fields(self):
        kb = self.make_kb({
            "bundle/projects/a.md": page("Project", description="", generated=None),
            "bundle/projects/b.md": page("Project", title="[a, list]"),
        })
        self.assertEqual(self.run_lint(kb), (1, [
            'kb/bundle/projects/a.md: empty frontmatter field "description"',
            'kb/bundle/projects/a.md: missing frontmatter field "generated"',
            'kb/bundle/projects/b.md: frontmatter field "title" must be text',
        ]))

    def test_missing_or_unclosed_frontmatter(self):
        kb = self.make_kb({
            "bundle/projects/none.md": "# A project\n",
            "bundle/projects/open.md": "---\ntype: Project\ntitle: Open\n",
        })
        self.assertEqual(self.run_lint(kb), (1, [
            "kb/bundle/projects/none.md: no frontmatter block between --- lines",
            "kb/bundle/projects/open.md: no frontmatter block between --- lines",
        ]))

    def test_generated_needs_an_actor_and_a_timestamp(self):
        kb = self.make_kb({
            "bundle/projects/a.md": page("Project", generated="2026-10-15T09:30:00Z"),
            "bundle/projects/b.md": page("Project", generated="{ at: 2026-10-15T09:30:00Z }"),
            "bundle/projects/c.md": page("Project", generated="{ by: Owner, at: 2026-10-15T09:30:00Z }"),
            "bundle/projects/d.md": page("Project", generated="{ by: human:owner, at: 2026-10-15 }"),
            "bundle/projects/e.md": page("Project", generated="{ by: human:owner, at: 2026-10-15T09:30:00 }"),
            "bundle/projects/f.md": page("Project", generated="{ by: human:owner, at: 2026-13-15T09:30:00Z }"),
            "bundle/projects/g.md": page("Project", generated="{ by: human:owner, at: 2026-10-15T12:30:00Z }"),
        })
        self.assertEqual(self.run_lint(kb), (1, [
            "kb/bundle/projects/a.md: generated must be { by, at }",
            f'kb/bundle/projects/b.md: generated.by "" {ACTOR_HINT}',
            f'kb/bundle/projects/c.md: generated.by "Owner" {ACTOR_HINT}',
            f'kb/bundle/projects/d.md: generated.at "2026-10-15" {TS_HINT}',
            f'kb/bundle/projects/e.md: generated.at "2026-10-15T09:30:00" {TS_HINT}',
            f'kb/bundle/projects/f.md: generated.at "2026-13-15T09:30:00Z" {TS_HINT}',
        ]))

    def test_okf_v0_1_fields_are_rejected(self):
        kb = self.make_kb({
            "bundle/projects/a.md": page("Project", "# A\n\n## Citations\n\n- [1] A source.\n", timestamp="2026-10-15T09:30:00Z"),
        })
        self.assertEqual(self.run_lint(kb), (1, [
            "kb/bundle/projects/a.md: timestamp is OKF v0.1. Write generated: { by, at } instead",
            "kb/bundle/projects/a.md: a Citations heading is OKF v0.1. List sources in the frontmatter and cite them with footnotes",
        ]))

    def test_verified_status_and_stale_after(self):
        kb = self.make_kb({
            "bundle/projects/a.md": page("Project", verified="{ by: human:owner, at: 2026-10-15T10:00:00Z }"),
            "bundle/projects/b.md": page("Project", verified="[]"),
            "bundle/projects/c.md": page("Project", verified="yes"),
            "bundle/projects/d.md": page("Project", extra="verified:\n  - { by: someone, at: 2026-10-15T10:00:00Z }\n"),
            "bundle/projects/e.md": page("Project", status="current", stale_after="2027-01-01"),
        })
        self.assertEqual(self.run_lint(kb), (1, [
            "kb/bundle/projects/b.md: verified must be { by, at } or a list of them",
            "kb/bundle/projects/c.md: verified must be { by, at }",
            f'kb/bundle/projects/d.md: verified.by "someone" {ACTOR_HINT}',
            'kb/bundle/projects/e.md: status "current" is not draft, stable or deprecated',
            f'kb/bundle/projects/e.md: stale_after "2027-01-01" {TS_HINT}',
        ]))

    def test_decisions_live_only_in_decisions(self):
        kb = self.make_kb({
            "bundle/decisions/0001-a.md": page("Decision"),
            "bundle/decisions/0002-b.md": page("Topic"),
            "bundle/projects/c.md": page("Decision"),
            "bundle/topics/d.md": sourced("decision"),
        })
        self.assertEqual(self.run_lint(kb), (1, [
            'kb/bundle/decisions/0002-b.md: type is "Topic", but pages in decisions/ need "Decision"',
            'kb/bundle/projects/c.md: type "Decision" belongs only in decisions/',
            'kb/bundle/topics/d.md: type "decision" belongs only in decisions/',
        ]))

    def test_superseded_by_names_a_page_and_deprecates_this_one(self):
        kb = self.make_kb({
            "bundle/decisions/0001-a.md": page("Decision", superseded_by="/decisions/0002-b.md", status="deprecated"),
            "bundle/decisions/0002-b.md": page("Decision"),
            "bundle/decisions/0003-c.md": page("Decision", superseded_by="0002-b.md", status="deprecated"),
            "bundle/decisions/0004-d.md": page("Decision", superseded_by="/decisions/missing.md", status="deprecated"),
            "bundle/decisions/0005-e.md": page("Decision", superseded_by="/../README.md", status="deprecated"),
            "bundle/decisions/0006-f.md": page("Decision", superseded_by="/decisions/0002-b.md"),
        })
        hint = "is not a page in the bundle, written /folder/page.md"
        self.assertEqual(self.run_lint(kb), (1, [
            f'kb/bundle/decisions/0003-c.md: superseded_by "0002-b.md" {hint}',
            f'kb/bundle/decisions/0004-d.md: superseded_by "/decisions/missing.md" {hint}',
            f'kb/bundle/decisions/0005-e.md: superseded_by "/../README.md" {hint}',
            "kb/bundle/decisions/0006-f.md: superseded_by is set, so status must be deprecated",
        ]))

    def test_sourced_folders_need_sources(self):
        kb = self.make_kb({
            "bundle/projects/a.md": page("Project"),
            "bundle/questions/b.md": page("Question"),
            "bundle/references/c.md": sourced("Reference"),
            "bundle/topics/d.md": page("Topic", sources="https://example.com"),
        })
        self.assertEqual(self.run_lint(kb), (1, [
            "kb/bundle/questions/b.md: no sources. Pages in questions, references, topics list theirs in the frontmatter",
            "kb/bundle/topics/d.md: sources must be a list",
        ]))

    def test_each_source_and_footnote(self):
        sources = "\n".join([
            "sources:",
            "  - id: one",
            "    resource: https://example.com/1",
            "    author: Example Inc",
            "    checked: 15/10/2026",
            "    last_modified: 2026-10-01",
            "    capture: ../../sources/processed/missing.md",
            "  - id: one",
            "    resource: https://example.com/2",
            "  - title: No resource",
            "  - just a string",
            "",
        ])
        body = "A.[^one] B.[^nobody] C.[^undefined] `[^in-code]`\n\n[^one]: One.\n[^nobody]: Nobody.\n"
        kb = self.make_kb({"bundle/references/a.md": page("Reference", body, sources)})
        self.assertEqual(self.run_lint(kb), (1, [
            f'kb/bundle/references/a.md: source "one": author "Example Inc" {ACTOR_HINT}',
            'kb/bundle/references/a.md: source "one": checked "15/10/2026" is not a YYYY-MM-DD date',
            f'kb/bundle/references/a.md: source "one": last_modified "2026-10-01" {TS_HINT}',
            'kb/bundle/references/a.md: source "one": capture "../../sources/processed/missing.md" is not a file in the repository',
            'kb/bundle/references/a.md: source "one" appears twice',
            "kb/bundle/references/a.md: source 3 has no resource",
            "kb/bundle/references/a.md: source 4 must be a mapping with a resource",
            "kb/bundle/references/a.md: footnote [^nobody] has no source with that id",
            "kb/bundle/references/a.md: footnote [^undefined] has no source with that id",
            "kb/bundle/references/a.md: footnote [^undefined] has no definition line",
        ]))

    def test_only_unresolved_or_escaping_local_links_are_reported(self):
        body = "\n".join([
            "[ok](b.md) [ok with fragment](b.md#part) [spaces](my%20page.md) [from the root](/projects/b.md)",
            "[web](https://example.com/x.md) [mail](mailto:jane@example.com) [anchor](#top)",
            "[gone](../references/missing.md) ![image](img/missing.png) [gone from the root](/topics/x.md)",
            "[out of the bundle](/../README.md) [out of the repo](../../../../elsewhere.md)",
            "`[inline code](skipped.md)`",
            "```",
            "[fenced](skipped.md)",
            "```",
        ])
        kb = self.make_kb({
            "README.md": "[gone](bundle/nowhere.md)",
            "bundle/projects/a.md": page("Project", body),
            "bundle/projects/b.md": page("Project"),
            "bundle/projects/my page.md": page("Project"),
        })
        self.assertEqual(self.run_lint(kb), (1, [
            'kb/bundle/projects/a.md: broken link "../references/missing.md"',
            'kb/bundle/projects/a.md: broken link "img/missing.png"',
            'kb/bundle/projects/a.md: broken link "/topics/x.md"',
            'kb/bundle/projects/a.md: link "/../README.md" goes outside bundle/',
            'kb/bundle/projects/a.md: link "../../../../elsewhere.md" goes outside the repository',
            'kb/README.md: broken link "bundle/nowhere.md"',
        ]))

    def test_every_page_is_listed_in_its_folder_index(self):
        kb = self.make_kb({
            "bundle/projects/a.md": page("Project"),
            "bundle/projects/b.md": page("Project"),
            "bundle/projects/index.md": index("a.md", "gone.md"),
            "bundle/topics/c.md": sourced("Topic"),
            "bundle/topics/index.md": None,
        })
        self.assertEqual(self.run_lint(kb), (1, [
            'kb/bundle/index.md: broken link "topics/index.md"',
            'kb/bundle/projects/index.md: broken link "gone.md"',
            "kb/bundle/projects/b.md: not listed in projects/index.md",
            "kb/bundle/topics: no index.md",
        ]))

    def test_the_root_index_lists_every_folder(self):
        folders = "".join(f"- [{folder}]({folder}/) - One line.\n" for folder in ("decisions", "projects", "questions"))
        kb = self.make_kb({"bundle/index.md": "# Knowledge base\n\n" + folders + "- [References](references/index.md) - One.\n"})
        self.assertEqual(self.run_lint(kb), (1, ["kb/bundle/topics/index.md: not listed in index.md"]))

    def test_log_dates_are_newest_first(self):
        log = "\n".join([
            "# Log", "## 2026-10-14", "- **Ingest**: One.", "## 2026-10-15", "- **Update**: Two.",
            "## 2026-10-15", "- **Update**: A union merge can repeat a date.", "## Notes", "## 2026-10-5",
            "```", "## Not a heading", "```",
        ])
        kb = self.make_kb({"bundle/log.md": log})
        self.assertEqual(self.run_lint(kb), (1, [
            "kb/bundle/log.md: 2026-10-15 comes after 2026-10-14, but the newest date goes first",
            'kb/bundle/log.md: heading "## Notes" is not a date written YYYY-MM-DD',
            'kb/bundle/log.md: heading "## 2026-10-5" is not a date written YYYY-MM-DD',
        ]))

    def test_layout(self):
        kb = self.make_kb({
            "loose.md": "Not here.",
            "decisions/0001-old.md": page("Decision"),
            "bundle/loose.md": page("Project"),
            "bundle/people/someone.md": page("Person"),
            "bundle/projects/sub/x.md": page("Project"),
            "bundle/log.md": None,
        })
        folders = "decisions/, projects/, questions/, references/, topics/"
        entries = "README.md, AGENTS.md, bundle/, sources/, templates/, tools/"
        self.assertEqual(self.run_lint(kb), (1, [
            f"kb/decisions: doesn't belong in kb/ ({entries})",
            f"kb/loose.md: doesn't belong in kb/ ({entries})",
            f"kb/bundle/loose.md: not in a KB folder ({folders})",
            f"kb/bundle/people: not a KB folder ({folders})",
            "kb/bundle/projects/sub: a folder inside a KB folder. Keep pages one folder deep",
            "kb/bundle/log.md: missing",
        ]))

    def test_missing_kb_directory(self):
        kb = self.make_kb({}) / "nope"
        self.assertEqual(self.run_lint(kb), (2, [f"{kb.resolve()}: not a directory"]))

    def test_kb_without_a_bundle(self):
        kb = self.make_kb({}) / "bundle" / "projects"
        self.assertEqual(self.run_lint(kb), (2, [f"{kb.resolve()}: no bundle/ folder"]))

    def test_command_line_exit_code_and_output(self):
        kb = self.make_kb({"bundle/projects/x.md": page("Project", title="")})
        result = subprocess.run([sys.executable, str(LINT), str(kb)], capture_output=True, text=True)
        self.assertEqual(
            (result.returncode, result.stdout),
            (1, 'kb/bundle/projects/x.md: empty frontmatter field "title"\n'),
        )


if __name__ == "__main__":
    unittest.main()
