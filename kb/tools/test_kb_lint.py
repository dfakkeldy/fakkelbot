import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import kb_lint

LINT = Path(__file__).with_name("kb_lint.py")


def note(note_type, body="", **overrides):
    fields = {"type": note_type, "title": "A note", "description": "One line.", "updated": "2026-10-14"}
    fields.update(overrides)
    lines = [f"{key}: {value}" for key, value in fields.items() if value is not None]
    return "---\n" + "\n".join(lines) + "\n---\n\n" + body


class KbLintTest(unittest.TestCase):
    def make_kb(self, files):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        kb = Path(tmp.name) / "kb"
        for relative, text in files.items():
            path = kb / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return kb

    def run_lint(self, kb):
        out = io.StringIO()
        with redirect_stdout(out):
            code = kb_lint.main([str(kb)])
        return code, out.getvalue().splitlines()

    def test_clean_kb_passes_and_skips_readme_agents_templates_and_tools(self):
        kb = self.make_kb({
            "README.md": "No frontmatter here.",
            "AGENTS.md": "No frontmatter here.",
            "templates/reference.md": "---\ntype:\n---\n[missing](nowhere.md)",
            "tools/notes.md": "No frontmatter here.",
            "references/a.md": note("reference", "See [the project](../projects/b.md#state)."),
            "projects/b.md": note("project"),
        })
        self.assertEqual(self.run_lint(kb), (0, ["kb lint: 2 notes, no problems"]))

    def test_missing_and_empty_fields(self):
        kb = self.make_kb({"references/a.md": note("reference", description="", updated=None)})
        self.assertEqual(self.run_lint(kb), (1, [
            'kb/references/a.md: empty frontmatter field "description"',
            'kb/references/a.md: missing frontmatter field "updated"',
        ]))

    def test_type_must_match_folder(self):
        kb = self.make_kb({"projects/x.md": note("reference")})
        self.assertEqual(self.run_lint(kb), (1, [
            'kb/projects/x.md: type is "reference", but notes in projects/ need "project"',
        ]))

    def test_note_outside_a_note_folder(self):
        kb = self.make_kb({"loose.md": note("reference"), "status/today.md": note("status")})
        self.assertEqual(self.run_lint(kb), (1, [
            "kb/loose.md: not in a note folder (decisions/, projects/, references/)",
            "kb/status/today.md: not in a note folder (decisions/, projects/, references/)",
        ]))

    def test_missing_or_unclosed_frontmatter(self):
        kb = self.make_kb({
            "decisions/none.md": "# A decision\n",
            "decisions/open.md": "---\ntype: decision\ntitle: Open\n",
        })
        self.assertEqual(self.run_lint(kb), (1, [
            "kb/decisions/none.md: no frontmatter block between --- lines",
            "kb/decisions/open.md: no frontmatter block between --- lines",
        ]))

    def test_updated_must_be_an_iso_date(self):
        kb = self.make_kb({
            "references/a.md": note("reference", updated="14/10/2026"),
            "references/b.md": note("reference", updated="20261014"),
            "references/c.md": note("reference", updated='"2026-10-14"'),
        })
        self.assertEqual(self.run_lint(kb), (1, [
            'kb/references/a.md: updated "14/10/2026" is not a YYYY-MM-DD date',
            'kb/references/b.md: updated "20261014" is not a YYYY-MM-DD date',
        ]))

    def test_only_unresolved_relative_links_are_reported(self):
        body = "\n".join([
            "[ok](b.md) [ok with fragment](b.md#part) [spaces](my%20note.md)",
            "[web](https://example.com/x.md) [mail](mailto:jane@example.com) [anchor](#top)",
            "[gone](../projects/missing.md) ![image](img/missing.png)",
            "`[inline code](skipped.md)`",
            "```",
            "[fenced](skipped.md)",
            "```",
        ])
        kb = self.make_kb({
            "references/a.md": note("reference", body),
            "references/b.md": note("reference"),
            "references/my note.md": note("reference"),
        })
        self.assertEqual(self.run_lint(kb), (1, [
            'kb/references/a.md: broken link "../projects/missing.md"',
            'kb/references/a.md: broken link "img/missing.png"',
        ]))

    def test_missing_kb_directory(self):
        kb = self.make_kb({}) / "nope"
        self.assertEqual(self.run_lint(kb), (2, [f"{kb.resolve()}: not a directory"]))

    def test_command_line_exit_code_and_output(self):
        kb = self.make_kb({"projects/x.md": note("project", updated="")})
        result = subprocess.run([sys.executable, str(LINT), str(kb)], capture_output=True, text=True)
        self.assertEqual(
            (result.returncode, result.stdout),
            (1, 'kb/projects/x.md: empty frontmatter field "updated"\n'),
        )


if __name__ == "__main__":
    unittest.main()
