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
CITATIONS = "\n\n## Citations\n\n- [1] [A source](https://example.com). Checked 2026-10-15.\n"
LOG = "# Log\n\n## 2026-10-15\n\n- **Update**: One line.\n\n## 2026-10-14\n\n- **Ingest**: One line.\n"


def page(page_type, body="", **overrides):
    fields = {
        "type": page_type,
        "title": "A page",
        "description": "One line.",
        "timestamp": "2026-10-15T09:30:00-03:00",
    }
    fields.update(overrides)
    lines = [f"{key}: {value}" for key, value in fields.items() if value is not None]
    return "---\n" + "\n".join(lines) + "\n---\n\n" + body


def index(*names):
    return "# Pages\n\n" + "".join(f"- [{name}]({name.replace(' ', '%20')}) - One line.\n" for name in names)


def root_index(*folders):
    entries = "".join(f"- [{folder}]({folder}/index.md) - One line.\n" for folder in folders)
    return '---\nokf_version: "0.1"\n---\n\n# Knowledge base\n\n## Folders\n\n' + entries


class KbLintTest(unittest.TestCase):
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
        kb = self.make_kb({
            "README.md": "No frontmatter. [A page](bundle/projects/b.md)",
            "AGENTS.md": "No frontmatter.",
            "templates/reference.md": "---\ntype:\n---\n[missing](nowhere.md)",
            "tools/notes.md": "No frontmatter.",
            "sources/inbox/raw.md": "No frontmatter.",
            "bundle/references/a.md": page(
                "Reference",
                "See [the project](../projects/b.md#state), [the same](/projects/b.md) "
                "and [the source](../../sources/inbox/raw.md)." + CITATIONS,
            ),
            "bundle/projects/b.md": page("Project"),
        })
        self.assertEqual(self.run_lint(kb), (0, ["kb lint: 2 pages, no problems"]))

    def test_the_real_kb_passes(self):
        code, out = self.run_lint(REAL_KB)
        self.assertEqual(code, 0, "\n".join(out))

    def test_missing_and_empty_fields(self):
        kb = self.make_kb({"bundle/projects/a.md": page("Project", description="", timestamp=None)})
        self.assertEqual(self.run_lint(kb), (1, [
            'kb/bundle/projects/a.md: empty frontmatter field "description"',
            'kb/bundle/projects/a.md: missing frontmatter field "timestamp"',
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

    def test_timestamp_needs_a_date_a_time_and_an_offset(self):
        kb = self.make_kb({
            "bundle/projects/a.md": page("Project", timestamp="2026-10-15"),
            "bundle/projects/b.md": page("Project", timestamp="2026-10-15T09:30:00"),
            "bundle/projects/c.md": page("Project", timestamp="2026-13-15T09:30:00Z"),
            "bundle/projects/d.md": page("Project", timestamp="2026-10-15T12:30:00Z"),
            "bundle/projects/e.md": page("Project", timestamp='"2026-10-15T09:30-03:00"'),
        })
        hint = "is not an ISO 8601 date and time with its UTC offset, such as 2026-10-15T09:30:00-03:00"
        self.assertEqual(self.run_lint(kb), (1, [
            f'kb/bundle/projects/a.md: timestamp "2026-10-15" {hint}',
            f'kb/bundle/projects/b.md: timestamp "2026-10-15T09:30:00" {hint}',
            f'kb/bundle/projects/c.md: timestamp "2026-13-15T09:30:00Z" {hint}',
        ]))

    def test_decisions_live_only_in_decisions(self):
        kb = self.make_kb({
            "bundle/decisions/0001-a.md": page("Decision"),
            "bundle/decisions/0002-b.md": page("Topic"),
            "bundle/projects/c.md": page("Decision"),
            "bundle/topics/d.md": page("decision", CITATIONS),
        })
        self.assertEqual(self.run_lint(kb), (1, [
            'kb/bundle/decisions/0002-b.md: type is "Topic", but pages in decisions/ need "Decision"',
            'kb/bundle/projects/c.md: type "Decision" belongs only in decisions/',
            'kb/bundle/topics/d.md: type "decision" belongs only in decisions/',
        ]))

    def test_cited_folders_need_a_citations_heading(self):
        kb = self.make_kb({
            "bundle/projects/a.md": page("Project"),
            "bundle/questions/b.md": page("Question", "# Citations\n\n- A source."),
            "bundle/references/c.md": page("Reference", "## Sources\n\n- A source."),
            "bundle/topics/d.md": page("Topic", CITATIONS),
        })
        self.assertEqual(self.run_lint(kb), (1, ['kb/bundle/references/c.md: no "## Citations" heading']))

    def test_superseded_by_names_a_page_in_the_bundle(self):
        kb = self.make_kb({
            "bundle/decisions/0001-a.md": page("Decision", superseded_by="/decisions/0002-b.md"),
            "bundle/decisions/0002-b.md": page("Decision"),
            "bundle/decisions/0003-c.md": page("Decision", superseded_by="0002-b.md"),
            "bundle/decisions/0004-d.md": page("Decision", superseded_by="/decisions/missing.md"),
            "bundle/decisions/0005-e.md": page("Decision", superseded_by="/../README.md"),
        })
        self.assertEqual(self.run_lint(kb), (1, [
            'kb/bundle/decisions/0003-c.md: superseded_by "0002-b.md" is not a page in the bundle, written /folder/page.md',
            'kb/bundle/decisions/0004-d.md: superseded_by "/decisions/missing.md" is not a page in the bundle, written /folder/page.md',
            'kb/bundle/decisions/0005-e.md: superseded_by "/../README.md" is not a page in the bundle, written /folder/page.md',
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
            "bundle/topics/c.md": page("Topic", CITATIONS),
            "bundle/topics/index.md": None,
        })
        self.assertEqual(self.run_lint(kb), (1, [
            'kb/bundle/index.md: broken link "topics/index.md"',
            'kb/bundle/projects/index.md: broken link "gone.md"',
            "kb/bundle/projects/b.md: not listed in projects/index.md",
            "kb/bundle/topics: no index.md",
        ]))

    def test_the_root_index_lists_every_folder_index(self):
        kb = self.make_kb({"bundle/index.md": root_index("decisions", "projects", "questions", "references")})
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
        self.assertEqual(self.run_lint(kb), (1, [
            "kb/decisions: doesn't belong in kb/ (README.md, AGENTS.md, bundle/, sources/, templates/, tools/)",
            "kb/loose.md: doesn't belong in kb/ (README.md, AGENTS.md, bundle/, sources/, templates/, tools/)",
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
        kb = self.make_kb({"bundle/projects/x.md": page("Project", timestamp="")})
        result = subprocess.run([sys.executable, str(LINT), str(kb)], capture_output=True, text=True)
        self.assertEqual(
            (result.returncode, result.stdout),
            (1, 'kb/bundle/projects/x.md: empty frontmatter field "timestamp"\n'),
        )


if __name__ == "__main__":
    unittest.main()
