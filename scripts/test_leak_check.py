import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("leak_check.py")
SUMMARY = "commits scanned: {}, text blobs scanned: {}, refs scanned: {}, binary blobs skipped: {}, hits: {}\n"
LICENSE_TEXT = "MIT License\n\nCopyright (c) 2026 Jane Example\n"


class LeakCheckCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        (self.tmp / "home").mkdir()
        self.env = {
            **os.environ,
            "HOME": str(self.tmp / "home"),
            "XDG_CONFIG_HOME": str(self.tmp / "home"),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CEILING_DIRECTORIES": str(self.tmp),
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_AUTHOR_NAME": "Test Author",
            "GIT_AUTHOR_EMAIL": "author@example.com",
            "GIT_COMMITTER_NAME": "Test Committer",
            "GIT_COMMITTER_EMAIL": "committer@example.com",
            "PYTHONUTF8": "1",
        }
        self.repo = self.tmp / "repo"
        self.init(self.repo)
        self.clock = 1767225600

    def git(self, *args, cwd=None, env=None, check=True, data=None):
        done = subprocess.run(
            ["git", *args],
            cwd=cwd or self.repo,
            env=env or self.env,
            input=data,
            capture_output=True,
            encoding="utf-8",
            check=check,
        )
        return done.stdout.strip()

    def commit(self, message, files, author=None, committer=None):
        for name, content in files.items():
            self.write(self.repo / name, content)
        self.clock += 60
        env = {**self.env, "GIT_AUTHOR_DATE": f"{self.clock} +0000", "GIT_COMMITTER_DATE": f"{self.clock} +0000"}
        if author:
            env["GIT_AUTHOR_NAME"], env["GIT_AUTHOR_EMAIL"] = author
        if committer:
            env["GIT_COMMITTER_NAME"], env["GIT_COMMITTER_EMAIL"] = committer
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message, env=env)
        return self.git("rev-parse", "HEAD")

    def write(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode())
        return str(path)

    def file(self, name, content):
        return self.write(self.tmp / name, content)

    def init(self, path):
        self.git("init", "-q", "-b", "main", str(path), cwd=self.tmp)

    def run_script(self, *args, cwd=None, env=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=cwd or self.tmp,
            env=env or self.env,
            capture_output=True,
            encoding="utf-8",
        )

    def check(self, deny, *extra, allow=None, repo=None):
        args = ["--denylist", self.file("deny.txt", deny), "--repo", str(repo or self.repo)]
        if allow is not None:
            args += ["--allow", self.file("allow.txt", allow)]
        return self.run_script(*args, *extra)


class FindingTests(LeakCheckCase):
    def test_term_in_an_old_commit_is_found_after_it_is_gone_from_head(self):
        first = self.commit("add notes", {"notes.txt": "meeting notes\ncall Jane Example tomorrow\n"})
        self.commit("tidy notes", {"notes.txt": "meeting notes\n"})
        self.assertEqual((self.repo / "notes.txt").read_text(), "meeting notes\n")

        result = self.check("# private terms\n\njane example\n")

        self.assertEqual(result.stdout, f"{first[:7]} notes.txt:2 denylist:3\n")
        self.assertEqual(result.stderr, SUMMARY.format(2, 2, 1, 0, 1))
        self.assertEqual(result.returncode, 1)

    def test_hit_is_reported_at_the_first_commit_that_had_the_content(self):
        first = self.commit("add notes", {"notes.txt": "call Jane Example\n"})
        self.commit("rewrite notes", {"notes.txt": "call someone\n"})
        self.commit("restore notes", {"notes.txt": "call Jane Example\n"})

        result = self.check("jane example\n")

        self.assertEqual(result.stdout, f"{first[:7]} notes.txt:1 denylist:1\n")

    def test_commit_message_and_author_and_committer_fields_are_scanned(self):
        sha = self.commit(
            "Fix typo for jane@example.com",
            {"a.txt": "x\n"},
            author=("Pat Author", "pat@example.com"),
            committer=("Jane Example", "jane@example.com"),
        )

        result = self.check("jane@example.com\njane example\n")

        self.assertEqual(
            result.stdout,
            f"author {sha[:7]}:committer-name denylist:2\n"
            f"author {sha[:7]}:committer-email denylist:1\n"
            f"msg {sha[:7]}:1 denylist:1\n",
        )
        self.assertEqual(result.returncode, 1)

    def test_regex_term_matches_case_insensitively(self):
        sha = self.commit("add file", {"a.txt": "call 555-0142 now\ncall 555-0242 now\nask JANE   example\n"})

        result = self.check("re:555-01\\d\\d\nre:jane\\s+example\n")

        self.assertEqual(result.stdout, f"{sha[:7]} a.txt:1 denylist:1\n{sha[:7]} a.txt:3 denylist:2\n")

    def test_plain_line_is_a_literal_not_a_regex(self):
        sha = self.commit("add file", {"a.txt": "abc\na.c\n"})

        result = self.check("a.c\n")

        self.assertEqual(result.stdout, f"{sha[:7]} a.txt:2 denylist:1\n")

    def test_one_hit_per_term_per_line_and_one_line_per_term(self):
        sha = self.commit("add file", {"a.txt": "jane example and JANE EXAMPLE and jane\n"})

        result = self.check("jane example\njane\n")

        self.assertEqual(result.stdout, f"{sha[:7]} a.txt:1 denylist:1\n{sha[:7]} a.txt:1 denylist:2\n")

    def test_denylist_line_numbers_count_comments_blank_lines_crlf_and_bom(self):
        sha = self.commit("add file", {"a.txt": "jane example\n"})

        result = self.check(b"\xef\xbb\xbf# header\r\n\r\njane example\r\n")

        self.assertEqual(result.stdout, f"{sha[:7]} a.txt:1 denylist:3\n")

    def test_blob_that_exists_only_in_a_merge_resolution_is_found(self):
        self.commit("base", {"f.txt": "base\n"})
        self.git("checkout", "-q", "-b", "side")
        self.commit("side", {"f.txt": "side\n"})
        self.git("checkout", "-q", "main")
        self.commit("main", {"f.txt": "main\n"})
        self.git("merge", "side", check=False)
        merge = self.commit("merge", {"f.txt": "Jane Example resolved\n"})

        result = self.check("jane example\n")

        self.assertEqual(result.stdout, f"{merge[:7]} f.txt:1 denylist:1\n")

    def test_paths_with_spaces_and_non_ascii_print_as_is(self):
        sha = self.commit("add file", {"sp ace/ü.txt": "Jane Example\n"})

        result = self.check("jane example\n")

        self.assertEqual(result.stdout, f"{sha[:7]} sp ace/ü.txt:1 denylist:1\n")

    def test_output_is_utf8_whatever_the_locale(self):
        sha = self.commit("add file", {"d\u00fc.txt": "Jane Example\n"})
        env = {**self.env, "PYTHONUTF8": "0", "PYTHONIOENCODING": "ascii"}

        result = self.run_script("--denylist", self.file("deny.txt", "jane example\n"), "--repo", str(self.repo), env=env)

        self.assertEqual(result.stdout, f"{sha[:7]} d\u00fc.txt:1 denylist:1\n")

    def test_empty_repository_is_clean(self):
        empty = self.tmp / "empty"
        self.init(empty)

        result = self.check("jane example\n", repo=empty)

        self.assertEqual((result.stdout, result.stderr, result.returncode), ("", SUMMARY.format(0, 0, 0, 0, 0), 0))

    def test_repo_defaults_to_the_current_directory(self):
        sha = self.commit("add file", {"a.txt": "Jane Example\n"})

        result = self.run_script("--denylist", self.file("deny.txt", "jane example\n"), cwd=self.repo)

        self.assertEqual(result.stdout, f"{sha[:7]} a.txt:1 denylist:1\n")

    def test_binary_blobs_are_skipped_and_counted(self):
        self.commit("add files", {"data.bin": b"\x00\x01Jane Example\x00", "notes.txt": "plain\n"})

        result = self.check("jane example\n")

        self.assertEqual((result.stdout, result.stderr, result.returncode), ("", SUMMARY.format(1, 1, 1, 1, 0), 0))

    def test_shallow_clone_gets_a_warning(self):
        self.commit("one", {"a.txt": "one\n"})
        self.commit("two", {"a.txt": "two\n"})
        shallow = self.tmp / "shallow"
        self.git("clone", "-q", "--depth", "1", self.repo.as_uri(), str(shallow), cwd=self.tmp)

        result = self.check("jane example\n", repo=shallow)

        self.assertIn("warning: shallow clone, older history was not scanned\n", result.stderr)
        self.assertEqual(result.returncode, 0)

    def test_all_blobs_are_read_through_one_cat_file_process(self):
        files = {f"file-{n:03d}.txt": f"line one\nline two\nline {n}\n" for n in range(300)}
        files["file-042.txt"] = "line one\nline two\nthe needle\n"
        sha = self.commit("many files", files)
        shim = self.tmp / "bin"
        shim.mkdir()
        (shim / "git").write_text('#!/bin/sh\necho "$@" >> "$GIT_CALLS"\nexec "$REAL_GIT" "$@"\n')
        (shim / "git").chmod(0o755)
        calls = self.tmp / "calls.log"
        env = {
            **self.env,
            "PATH": f"{shim}{os.pathsep}{os.environ['PATH']}",
            "GIT_CALLS": str(calls),
            "REAL_GIT": shutil.which("git"),
        }

        result = self.run_script("--denylist", self.file("deny.txt", "needle\n"), "--repo", str(self.repo), env=env)

        self.assertEqual(result.stdout, f"{sha[:7]} file-042.txt:3 denylist:1\n")
        self.assertEqual([c for c in calls.read_text().splitlines() if "cat-file" in c], [f"-C {self.repo} cat-file --batch"])


class RefTests(LeakCheckCase):
    def test_branch_names_tag_names_and_tag_messages_are_scanned(self):
        sha = self.commit("initial", {"a.txt": "x\n"})
        self.git("checkout", "-q", "-b", "jane-example/work")
        self.git("tag", "jane-example-lite")
        self.git("tag", "-a", "v1", "-m", "release notes\nfor Jane Example")
        tag_object = self.git("rev-parse", "v1")

        result = self.check("re:jane.example\n")

        self.assertEqual(
            result.stdout,
            f"branch {sha[:7]}:name denylist:1\n"
            f"tag {sha[:7]}:name denylist:1\n"
            f"tag {tag_object[:7]}:2 denylist:1\n",
        )
        self.assertEqual(result.stderr, SUMMARY.format(1, 1, 4, 0, 3))

    def test_branches_at_one_commit_print_one_line(self):
        sha = self.commit("initial", {"a.txt": "x\n"})
        self.git("branch", "jane-a")
        self.git("branch", "jane-b")

        result = self.check("re:jane-\n")

        self.assertEqual(result.stdout, f"branch {sha[:7]}:name denylist:1\n")
        self.assertEqual(result.stderr, SUMMARY.format(1, 1, 3, 0, 1))

    def test_tagger_identity_is_scanned_and_a_signature_block_is_not(self):
        sha = self.commit("initial", {"a.txt": "x\n"})
        tag_text = (
            f"object {sha}\ntype commit\ntag signed-one\n"
            "tagger Pat Tagger <pat@example.com> 1767225600 +0000\n\n"
            "signed release\n-----BEGIN PGP SIGNATURE-----\n\njane example in the armor\n"
            "-----END PGP SIGNATURE-----\n"
        )
        tag_object = self.git("mktag", data=tag_text)
        self.git("update-ref", "refs/tags/signed-one", tag_object)

        result = self.check("jane example\npat@example.com\n")

        self.assertEqual(result.stdout, f"tag {tag_object[:7]}:tagger-email denylist:2\n")


class AllowTests(LeakCheckCase):
    def test_text_is_allowed_only_in_files_matching_the_glob(self):
        sha = self.commit("add files", {"LICENSE": LICENSE_TEXT, "README.md": "By Jane Example\n"})

        without = self.check("jane example\n")
        allowed = self.check("jane example\n", allow="LICENSE\tJane Example\n")

        self.assertEqual(without.stdout, f"{sha[:7]} LICENSE:3 denylist:1\n{sha[:7]} README.md:1 denylist:1\n")
        self.assertEqual((allowed.stdout, allowed.returncode), (f"{sha[:7]} README.md:1 denylist:1\n", 1))

    def test_star_glob_allows_a_slug_in_files_and_commit_messages(self):
        sha = self.commit("link example-org/example-app", {"README.md": "See example-org/example-app.\n"})
        deny = "example-org\n"

        without = self.check(deny)
        allowed = self.check(deny, allow="# the repo slug\n*\texample-org/example-app\n")

        self.assertEqual(without.stdout, f"msg {sha[:7]}:1 denylist:1\n{sha[:7]} README.md:1 denylist:1\n")
        self.assertEqual((allowed.stdout, allowed.returncode), ("", 0))

    def test_author_pseudo_path_allows_the_owner_name_in_commit_identities(self):
        sha = self.commit("add file", {"a.txt": "x\n"}, author=("Jane Example", "author@example.com"))

        without = self.check("jane example\n")
        allowed = self.check("jane example\n", allow="git:author\tJane Example\n")

        self.assertEqual(without.stdout, f"author {sha[:7]}:author-name denylist:1\n")
        self.assertEqual((allowed.stdout, allowed.returncode), ("", 0))

    def test_match_partly_outside_the_allowed_text_still_counts(self):
        sha = self.commit("add file", {"a.txt": "mail jane.example@example.com\n"})
        deny = "jane.example@example.com\n"

        partial = self.check(deny, allow="*\texample.com\n")
        whole = self.check(deny, allow="*\tmail jane.example@example.com\n")

        self.assertEqual(partial.stdout, f"{sha[:7]} a.txt:1 denylist:1\n")
        self.assertEqual((whole.stdout, whole.returncode), ("", 0))

    def test_allowed_text_does_not_hide_another_match_on_the_same_line(self):
        sha = self.commit("add file", {"a.txt": "Jane Example wrote to Jane\n", "b.txt": "Jane Example\n"})

        result = self.check("jane\n", allow="*\tJane Example\n")

        self.assertEqual(result.stdout, f"{sha[:7]} a.txt:1 denylist:1\n")

    def test_allowed_text_is_case_sensitive(self):
        sha = self.commit("add file", {"LICENSE": "COPYRIGHT JANE EXAMPLE\n"})

        result = self.check("jane example\n", allow="LICENSE\tJane Example\n")

        self.assertEqual(result.stdout, f"{sha[:7]} LICENSE:1 denylist:1\n")

    def test_a_blob_stored_at_two_paths_is_allowed_per_path(self):
        sha = self.commit("add files", {"LICENSE": LICENSE_TEXT, "docs/LICENSE": LICENSE_TEXT})

        result = self.check("jane example\n", allow="LICENSE\tJane Example\n")

        self.assertEqual(result.stdout, f"{sha[:7]} docs/LICENSE:3 denylist:1\n")


class OutputTests(LeakCheckCase):
    def make_leaky_commit(self):
        sha = self.commit("add file", {"jane-example.txt": "dear Jane Example\n"})
        blob = self.git("rev-parse", "HEAD:jane-example.txt")
        return sha[:7], blob[:7]

    def test_default_output_has_locations_only(self):
        sha, blob = self.make_leaky_commit()

        result = self.check("re:jane.example\n")

        self.assertEqual(
            result.stdout,
            f"{sha} blob-{blob}:path denylist:1\n{sha} blob-{blob}:1 denylist:1\n",
        )
        self.assertNotIn("jane", (result.stdout + result.stderr).lower())

    def test_show_prints_the_matched_text_and_the_real_path(self):
        sha, _ = self.make_leaky_commit()

        result = self.check("re:jane.example\n", "--show")

        self.assertEqual(
            result.stdout,
            f'{sha} jane-example.txt:path denylist:1 "jane-example"\n'
            f'{sha} jane-example.txt:1 denylist:1 "Jane Example"\n',
        )


class ExitCodeTests(LeakCheckCase):
    def test_clean_repository_exits_0(self):
        self.commit("add file", {"a.txt": "nothing here\n"})

        result = self.check("jane example\n")

        self.assertEqual((result.stdout, result.stderr, result.returncode), ("", SUMMARY.format(1, 1, 1, 0, 0), 0))

    def test_missing_denylist_file_exits_2(self):
        result = self.run_script("--denylist", str(self.tmp / "nope.txt"), "--repo", str(self.repo))

        self.assertEqual(result.stderr, "leak_check.py: error: cannot read the denylist file: No such file or directory\n")
        self.assertEqual((result.stdout, result.returncode), ("", 2))

    def test_missing_denylist_argument_exits_2(self):
        result = self.run_script("--repo", str(self.repo))

        self.assertIn("the following arguments are required: --denylist", result.stderr)
        self.assertEqual(result.returncode, 2)

    def test_bad_regex_exits_2_without_echoing_the_pattern(self):
        result = self.check("fine\nre:(secret-unclosed\n")

        self.assertTrue(result.stderr.startswith("leak_check.py: error: denylist line 2: bad regular expression ("))
        self.assertNotIn("secret-unclosed", result.stderr)
        self.assertEqual((result.stdout, result.returncode), ("", 2))

    def test_regex_that_matches_everything_exits_2(self):
        result = self.check("re:a*\n")

        self.assertEqual(result.stderr, "leak_check.py: error: denylist line 1: regular expression matches the empty string\n")
        self.assertEqual(result.returncode, 2)

    def test_denylist_without_terms_exits_2(self):
        result = self.check("# only a comment\n\n")

        self.assertEqual(result.stderr, "leak_check.py: error: denylist has no terms\n")
        self.assertEqual(result.returncode, 2)

    def test_allow_line_without_a_tab_exits_2(self):
        result = self.check("jane example\n", allow="# note\nLICENSE Jane Example\n")

        self.assertEqual(result.stderr, "leak_check.py: error: allow file line 2: expected <path glob><TAB><literal text>\n")
        self.assertEqual(result.returncode, 2)

    def test_directory_that_is_not_a_repository_exits_2(self):
        plain = self.tmp / "plain"
        plain.mkdir()

        result = self.check("jane example\n", repo=plain)

        self.assertTrue(result.stderr.startswith("leak_check.py: error: git rev-parse failed: fatal: not a git repository"))
        self.assertEqual((result.stdout, result.returncode), ("", 2))


if __name__ == "__main__":
    unittest.main()
