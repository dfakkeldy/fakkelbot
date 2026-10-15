import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import bot_chart as bc
from bot_chart import Edge, RepoListener

SCRIPT = Path(__file__).with_name("bot_chart.py")


def bot_file(name="solo", instructions="Does one job.", routines="", default="yes"):
    return (
        f"# {name}\n\n- **Category:** Work\n- **Default:** {default}\n\nA note for people.\n\n"
        f"## Instructions\n\n```text\n{instructions}\n```\n\n{routines}"
    )


def routine(name="check", schedule="`0 9 * * *` (owner's timezone)", enabled="true", trigger=None, prompt="Check."):
    trigger_line = f"- **Trigger:** `{trigger}`\n" if trigger else ""
    return (
        f"### {name}\n\n- **Folder:** `{name}`\n- **Schedule:** {schedule}\n- **Enabled:** {enabled}\n"
        f"{trigger_line}\n```text\n{prompt}\n```\n\n"
    )


def routines(*sections):
    return "## Routines\n\n" + "".join(sections)


def routine_rows(bot):
    return tuple((r.name, tuple(" ".join(c) for c in r.crons), r.listeners, r.enabled) for r in bot.routines)


@contextlib.contextmanager
def fleet_dir(*files, readme=None):
    with tempfile.TemporaryDirectory() as tmp:
        for i, text in enumerate(files):
            (Path(tmp) / f"bot{i}.md").write_text(text, encoding="utf-8")
        if readme is not None:
            (Path(tmp) / "README.md").write_text(readme, encoding="utf-8")
        yield Path(tmp)


GROUP_TRIGGER = ('{"type": "group", "listeners": [{"type": "cron", "schedule": "0 10 * * *"}, '
                 '{"type": "github", "repo": "<owner>/ledger", "events": ["pr-merged"]}]}')
FLEET = (
    bot_file("Night Owl", "You watch the ledger and use the knowledge base.", routines(
        routine("morning-sweep", "`0,30 7-9 * * *` (owner's timezone)", trigger=GROUP_TRIGGER,
                prompt="Sweep the ledger with gh. Send each affected bot a note."),
        routine("weekly-ledger", "`15 18 * * 0` (owner's timezone)", "false",
                prompt="Send the weekly totals to clerk with SendToAgent, not to scout.\n- **Enabled:** true"),
    ), default="no"),
    bot_file("clerk", "You file the owner's attachments from Gmail. Save receipts for Night Owl.", routines(
        routine("daily-filing", "`23 7 * * 1-5` (owner's timezone)",
                prompt="File new attachments. If one looks wrong, report it to scout."),
    )),
    bot_file("scout", "Ask clerk first. Never send Night Owl anything. Use SendToAgent."),
)


class ParseTest(unittest.TestCase):
    def setUp(self):
        with fleet_dir(*FLEET, readme="# Bot files\n\nNo instructions here.\n") as directory:
            self.bots = bc.load_bots(directory)
        self.by_name = {bot.name: bot for bot in self.bots}

    def test_bots_sort_by_name_ignoring_case_and_skip_the_readme(self):
        self.assertEqual([bot.name for bot in self.bots], ["clerk", "Night Owl", "scout"])

    def test_routines_merge_trigger_crons_and_keep_github_listeners(self):
        self.assertEqual(routine_rows(self.by_name["Night Owl"]), (
            ("morning-sweep", ("0,30 7-9 * * *", "0 10 * * *"), (RepoListener("<owner>/ledger", ("pr-merged",)),), True),
            ("weekly-ledger", ("15 18 * * 0",), (), False),
        ))

    def test_a_field_inside_a_prompt_is_prompt_text(self):
        self.assertEqual(self.by_name["Night Owl"].routines[1].prompt,
                         "Send the weekly totals to clerk with SendToAgent, not to scout.\n- **Enabled:** true")

    def test_default_no_marks_a_bot_optional(self):
        self.assertEqual([bot.optional for bot in self.bots], [False, True, False])

    def test_a_bot_without_routines(self):
        self.assertEqual((self.by_name["scout"].instructions, self.by_name["scout"].routines),
                         ("Ask clerk first. Never send Night Owl anything. Use SendToAgent.", ()))

    def test_a_routines_section_with_only_prose_has_no_routines(self):
        text = bot_file(routines="## Routines\n\nNone. It works only while the owner is in its chat.\n")
        with fleet_dir(text) as directory:
            (bot,) = bc.load_bots(directory)
        self.assertEqual(bot.routines, ())
        page = bc.render([bot])
        self.assertIn("### solo\n\nNo routines.\n", page)
        self.assertNotIn("section solo", page)

    def test_schedule_none_and_capitalised_enabled(self):
        text = bot_file(routines=routines(routine(schedule="None", enabled="True")))
        with fleet_dir(text) as directory:
            (bot,) = bc.load_bots(directory)
        self.assertEqual(routine_rows(bot), (("check", (), (), True),))


class EdgeTest(unittest.TestCase):
    def test_fixture_fleet_edges(self):
        with fleet_dir(*FLEET) as directory:
            edges = bc.find_edges(bc.load_bots(directory))
        self.assertEqual(edges, {
            Edge("Night Owl", "kb", "instructions", "uses"),
            Edge("Night Owl", "github", "morning-sweep", "uses"),
            Edge("Night Owl", "each affected bot", "morning-sweep", "handoff"),
            Edge("Night Owl", "clerk", "weekly-ledger", "handoff"),
            Edge("github", "Night Owl", "morning-sweep", "wakes"),
            Edge("clerk", "gmail", "instructions", "uses"),
            Edge("clerk", "Night Owl", "instructions", "handoff"),
            Edge("clerk", "scout", "daily-filing", "handoff"),
            Edge("scout", "clerk", "instructions", "handoff"),
        })

    def test_curly_apostrophes_read_like_straight_ones(self):
        solo = bot_file("solo", "Don’t tell duo. Check the owner’s Gmail.")
        duo = bot_file("duo", "Ask solo first.")
        with fleet_dir(solo, duo) as directory:
            self.assertEqual(bc.find_edges(bc.load_bots(directory)), {
                Edge("solo", "gmail", "instructions", "uses"),
                Edge("duo", "solo", "instructions", "handoff"),
            })

    def test_paths_repos_and_file_names_are_not_mentions(self):
        setup = bot_file("setup", "Apply changes.")
        reader = bot_file("reader", "Read SETUP.md, grok-bot-setup and bots/setup.md. Use SendToAgent.")
        with fleet_dir(setup, reader) as directory:
            self.assertEqual(bc.find_edges(bc.load_bots(directory)), set())

    def test_the_owner_s_github_username_is_not_github_use(self):
        text = bot_file("solo", "Fill in the owner's GitHub username. Open a PR with gh.")
        with fleet_dir(text) as directory:
            self.assertEqual(bc.find_edges(bc.load_bots(directory)), {Edge("solo", "github", "instructions", "uses")})


class ParseErrorTest(unittest.TestCase):
    def assert_fails(self, message, *files):
        with fleet_dir(*files) as directory:
            with self.assertRaises(bc.ChartError) as caught:
                bc.load_bots(directory)
        self.assertEqual(str(caught.exception), message)

    def test_schedule_with_a_time_zone(self):
        self.assert_fails("solo: check: cannot read schedule 'CRON_TZ=UTC 0 9 * * *'",
                          bot_file(routines=routines(routine(schedule="`CRON_TZ=UTC 0 9 * * *`"))))

    def test_day_of_month_with_day_of_week(self):
        self.assert_fails("solo: check: cron 0 9 1 * 1 restricts both day of month and day of week",
                          bot_file(routines=routines(routine(schedule="`0 9 1 * 1`"))))

    def test_step_outside_minute_and_hour(self):
        self.assert_fails("solo: check: steps are not supported in the dom field ('*/2')",
                          bot_file(routines=routines(routine(schedule="`0 9 */2 * *`"))))

    def test_out_of_range_field(self):
        self.assert_fails("solo: check: the hour field '24' is out of range",
                          bot_file(routines=routines(routine(schedule="`0 24 * * *`"))))

    def test_unknown_trigger_type(self):
        self.assert_fails("solo: check: unknown trigger type 'slack'",
                          bot_file(routines=routines(routine(schedule="None", trigger='{"type": "slack"}'))))

    def test_trigger_without_a_repo(self):
        self.assert_fails("solo: check: cannot read trigger '{\"type\": \"github\", \"events\": []}' (KeyError('repo'))",
                          bot_file(routines=routines(routine(schedule="None", trigger='{"type": "github", "events": []}'))))

    def test_enabled_must_be_true_or_false(self):
        self.assert_fails("solo: check: Enabled must be true or false",
                          bot_file(routines=routines(routine(enabled="yes"))))

    def test_routine_without_a_text_block(self):
        self.assert_fails("solo: check: no text block",
                          bot_file(routines="## Routines\n\n### check\n\n- **Enabled:** true\n"))

    def test_routine_field_without_a_routine_heading(self):
        self.assert_fails("solo: a routine field under ## Routines has no ### heading: '- **Schedule:** `0 9 * * *`'",
                          bot_file(routines="## Routines\n\n- **Schedule:** `0 9 * * *`\n"))

    def test_unknown_routines_heading(self):
        self.assert_fails("solo: unknown routines heading '## Paused routines'",
                          bot_file(routines="## Paused routines\n\nNone.\n"))

    def test_no_instructions(self):
        self.assert_fails("solo: no ## Instructions section", "# solo\n\nA note.\n")

    def test_two_files_with_one_name(self):
        self.assert_fails("two bot files share the name Solo", bot_file("solo"), bot_file("Solo"))


TINY = (
    bot_file("alpha", "Report to beta when done. Use gh for PRs.", routines(
        routine("standup", "`5 9 * * 1-5` (owner's timezone)", prompt="Tell beta the plan."),
        routine('merge "watch"', "None", trigger='{"type": "github", "repo": "<owner>/site", "events": ["pr-merged"]}',
                prompt="Check Gmail for the merge note."),
    )),
    bot_file("beta", "Never tell alpha anything.", routines(
        routine("digest: morning notes", "`30 6 * * 6,0` (owner's timezone)", prompt="Summarise."),
        routine("old-sweep", "`0 22 * * *` (owner's timezone)", "false", prompt="Sweep."),
    ), default="no"),
)

TINY_CHART_MD = """> Generated by `scripts/bot_chart.py` from `bots/*.md`. Don't edit this file by hand. After you change a bot file, run `python3 scripts/bot_chart.py`.

# Bot chart

Times are in the owner's timezone, like the schedules in the bot files. [scripts/README.md](../scripts/README.md#bot_chartpy) explains how the chart finds each arrow.

## Who talks to whom

### Hand-offs and what wakes each bot

Solid arrows are hand-offs between bots. Thick arrows are GitHub events that wake a bot. A dashed border marks a bot that setup adds only when the owner asks for it.

```mermaid
flowchart LR
    bot_alpha["alpha"]
    bot_beta["beta<br/>(optional)"]
    subgraph outside["Outside systems"]
        sys_github[("GitHub")]
    end
    bot_alpha -->|"instructions + 1 more"| bot_beta
    sys_github ==>|"wakes: merge #quot;watch#quot;"| bot_alpha
    classDef optional stroke-dasharray: 5 5
    class bot_beta optional
```

### What each bot uses

Each arrow points from a bot to a system it uses.

```mermaid
flowchart LR
    bot_alpha["alpha"]
    subgraph outside["Outside systems"]
        sys_github[("GitHub")]
        sys_gmail[("Gmail")]
    end
    bot_alpha --> sys_github
    bot_alpha --> sys_gmail
```

### Every edge

| From | To | Kind | Where |
|---|---|---|---|
| alpha | beta | hands off to | instructions, standup |
| GitHub | alpha | wakes | merge "watch" |
| alpha | GitHub | uses | instructions |
| alpha | Gmail | uses | merge "watch" |

## A day of scheduled routines

```mermaid
gantt
    dateFormat HH:mm
    axisFormat %H:%M
    tickInterval 1hour
    todayMarker off
    section alpha
    standup (weekdays) :09:05, 15m
    section beta (optional)
    digest#58; morning notes (weekends) :06:30, 15m
```

Bars mark start times, not run length.

The chart leaves out one disabled routine, beta's old-sweep.

Routines that only run on GitHub events are in the tables below.

## Routines by bot

### alpha

| Routine | Schedule | Trigger | Enabled |
|---|---|---|---|
| standup | weekdays at 09:05 | none | yes |
| merge "watch" | none | pr-merged in site | yes |

### beta (optional)

| Routine | Schedule | Trigger | Enabled |
|---|---|---|---|
| digest: morning notes | weekends at 06:30 | none | yes |
| old-sweep | daily at 22:00 | none | no |
"""


class RenderTest(unittest.TestCase):
    def test_tiny_fleet_document(self):
        with fleet_dir(*TINY) as directory:
            self.assertEqual(bc.render(bc.load_bots(directory)), TINY_CHART_MD)

    def test_schedule_in_plain_words(self):
        cases = {
            ("43 7,17 * * *",): "daily at 07:43, 17:43",
            ("33 0,7-23/2 * * *",): "daily at 00:33, 07:33, 09:33, 11:33, 13:33, 15:33, 17:33, 19:33, 21:33, 23:33",
            ("*/20 9 * * 1-5",): "weekdays at 09:00, 09:20, 09:40",
            ("49 8 * * 1",): "Mondays at 08:49",
            ("45 21 * * 0,2,4",): "Sun, Tue and Thu at 21:45",
            ("0 9 * * 1-6",): "Mon to Sat at 09:00",
            ("0 9 * * 6,7",): "weekends at 09:00",
            ("17 9 5 * *",): "on the 5th of each month at 09:17",
            ("30 6 15 10 *",): "on Oct 15 at 06:30",
            ("2 10 12,14,16,19 10 *",): "on Oct 12, 14, 16 and 19 at 10:02",
            ("0,30 7-9 * * *", "0 10 * * *"): "daily at 07:00, 07:30, 08:00, 08:30, 09:00, 09:30, 10:00",
            ("0 8 * * 1", "0 18 * * *"): "Mondays at 08:00; daily at 18:00",
            (): "none",
        }
        for crons, words in cases.items():
            with self.subTest(crons=crons):
                self.assertEqual(bc.schedule_words([bc.parse_schedule("test", cron) for cron in crons]), words)

    def test_gantt_day_labels(self):
        cases = {
            "0 9 * * 0,2,4": "Sun, Tue, Thu",
            "0 9 * * 1-6": "Mon to Sat",
            "0 9 * * 1": "Mon",
            "17 9 5 * *": "5th of month",
            "2 10 12,14,16,19 10 *": "Oct 12, 14, 16, 19",
        }
        for cron, label in cases.items():
            with self.subTest(cron=cron):
                self.assertEqual(bc.day_words(bc.parse_schedule("test", cron), short=True), label)

    def test_rerun_with_another_hash_seed_is_byte_identical(self):
        with fleet_dir(*FLEET) as directory:
            outputs = []
            for seed in ("1", "2"):
                out = directory / "out" / f"chart-{seed}.md"
                env = {**os.environ, "PYTHONHASHSEED": seed}
                subprocess.run([sys.executable, str(SCRIPT), "--bots", str(directory), "--out", str(out)], check=True, env=env)
                outputs.append(out.read_bytes())
        self.assertEqual(outputs[0], outputs[1])
        self.assertIn(b"| scout | clerk | hands off to | instructions |", outputs[0])

    def test_cli_names_the_bot_and_routine_on_error(self):
        with fleet_dir(bot_file(routines=routines(routine(schedule="`0 9 * * mon`")))) as directory:
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = bc.main(["--bots", str(directory), "--out", str(directory / "chart.md")])
            self.assertEqual((code, stderr.getvalue(), (directory / "chart.md").exists()),
                             (1, "bot_chart: solo: check: cannot read schedule '0 9 * * mon'\n", False))


if __name__ == "__main__":
    unittest.main()
