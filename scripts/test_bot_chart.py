import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import bot_chart as bc
from bot_chart import Edge, RepoListener

SCRIPT = Path(__file__).with_name("bot_chart.py")


def bot_file(name="solo", instructions="Does one job.", routines="", default="yes", category="Work"):
    return (
        f"# {name}\n\n- **Category:** {category}\n- **Default:** {default}\n\nA note for people.\n\n"
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


class ConfigTest(unittest.TestCase):
    def test_the_script_path_in_the_config_finds_the_repo_root(self):
        self.assertEqual(bc.ROOT / bc.CONFIG["script"], SCRIPT.resolve())
        self.assertTrue((bc.ROOT / "bots").is_dir())


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

    def test_creation_lines_are_not_read_here(self):
        text = bot_file(default="no").replace("- **Default:** no", "- **Default:** no\n- **Created:** maybe\n- **ID:** (not created yet)")
        with fleet_dir(text) as directory:
            (bot,) = bc.load_bots(directory)
        self.assertEqual((bot.optional, bot.created), (True, None))
        page = bc.render([bot])
        self.assertIn("### solo (optional)\n", page)
        self.assertNotIn("Recorded setup", page)
        self.assertNotIn("_planned", page)

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
        fakkelbot = bot_file("fakkelbot", "Apply changes.")
        reader = bot_file("reader", "Read SETUP.md, grok-bot-setup, bots/fakkelbot.md and https://github.com/dfakkeldy/fakkelbot. Use SendToAgent.")
        with fleet_dir(fakkelbot, reader) as directory:
            self.assertEqual(bc.find_edges(bc.load_bots(directory)), set())

    def test_the_owner_s_github_username_is_not_github_use(self):
        text = bot_file("solo", "Fill in the owner's GitHub username. Open a PR with gh.")
        with fleet_dir(text) as directory:
            self.assertEqual(bc.find_edges(bc.load_bots(directory)), {Edge("solo", "github", "instructions", "uses")})

    def test_coding_bots_use_their_cli_without_creating_handoffs(self):
        with fleet_dir(
            bot_file("claude", "Use Claude Code for the assigned task.", default="no", category="Builders"),
            bot_file("cursor", "Use Cursor Agent for the assigned task.", default="no", category="Builders"),
            bot_file("codex", "Use Codex CLI for the assigned task.", default="no", category="Builders"),
        ) as directory:
            bots = bc.load_bots(directory)
        self.assertEqual(bc.find_edges(bots), {
            Edge("claude", "claude_cli", "instructions", "uses"),
            Edge("cursor", "cursor_cli", "instructions", "uses"),
            Edge("codex", "codex_cli", "instructions", "uses"),
        })
        page = bc.render(bots)
        self.assertIn('bot_claude --> sys_claude_cli', page)
        self.assertIn('sys_cursor_cli["Cursor Agent"]', page)
        self.assertIn('sys_codex_cli["Codex CLI"]', page)

    def test_negated_cli_use_does_not_create_a_system_edge(self):
        with fleet_dir(bot_file("solo", "Never use Claude Code. Don't use Cursor Agent. No Codex CLI.")) as directory:
            self.assertEqual(bc.find_edges(bc.load_bots(directory)), set())


class ParseErrorTest(unittest.TestCase):
    def assert_fails(self, message, *files):
        with fleet_dir(*files) as directory:
            with self.assertRaises(bc.ChartError) as caught:
                bc.load_bots(directory)
        self.assertEqual(str(caught.exception), message)

    def test_schedule_with_a_time_zone(self):
        self.assert_fails("solo: check: cannot read schedule 'CRON_TZ=UTC 0 9 * * *'",
                          bot_file(routines=routines(routine(schedule="`CRON_TZ=UTC 0 9 * * *`"))))

    def test_reported_routine_with_a_time_zone(self):
        self.assert_fails("solo: ping: schedule uses time zone UTC, expected none",
                          bot_file(routines="## Routines (reported by bot)\n\n1. ping. Enabled. Cron 0 9 * * * (UTC). Pings.\n"))

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

    def test_empty_step(self):
        self.assert_fails("solo: check: cannot read the step in the minute field '0/'",
                          bot_file(routines=routines(routine(schedule="`0/ 7 * * *`"))))

    def test_github_events_must_be_a_list(self):
        self.assert_fails("solo: check: a github trigger needs a repo name and a list of event names",
                          bot_file(routines=routines(routine(schedule="None", trigger='{"type": "github", "repo": "o/r", "events": "pr-merged"}'))))

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
    ), category="Daily life"),
    bot_file("beta", "Never tell alpha anything.", routines(
        routine("digest: morning notes", "`30 6 * * 6,0` (owner's timezone)", prompt="Summarise."),
        routine("old-sweep", "`0 22 * * *` (owner's timezone)", "false", prompt="Sweep."),
    ), default="no", category="Content"),
)

TINY_CHART_MD = """> Generated by `scripts/bot_chart.py` from `bots/*.md`. Don't edit this file by hand. After you change a bot file, run `python3 scripts/bot_chart.py`.

# Bot chart

Times are in the owner's timezone, like the schedules in the bot files. [scripts/README.md](../scripts/README.md#bot_chartpy) explains how the chart finds each arrow.

## Who talks to whom

### Hand-offs and what wakes each bot

Grey arrows are hand-offs between bots. The table of every edge below says where each one appears. Thick amber arrows are GitHub events that wake a bot. A bot's colour is its category: green for Daily life and orange for Content. A pale bot with a dashed outline is one that fakkelbot adds only when the owner asks for it.

```mermaid
%%{init: {"flowchart": {"curve": "basis"}}}%%
flowchart TB
    bot_alpha("alpha")
    bot_beta("beta")
    sys_github["GitHub"]
    bot_alpha --> bot_beta
    sys_github ==>|"wakes: merge #quot;watch#quot;"| bot_alpha
    classDef daily_life fill:#1a7f37,stroke:#1a7f37,color:#ffffff
    class bot_alpha daily_life
    classDef content_optional fill:#bc4c0026,stroke:#bc4c00,stroke-width:2px,stroke-dasharray:5 3
    class bot_beta content_optional
    classDef system fill:transparent,stroke:#8c959f,stroke-width:1.5px
    class sys_github system
    linkStyle 0 stroke:#8c959f,stroke-width:1.5px
    linkStyle 1 stroke:#d4a72c,stroke-width:3px
```

### What each bot uses

Each teal arrow points from a bot to a system it uses.

```mermaid
%%{init: {"flowchart": {"curve": "basis"}}}%%
flowchart TB
    bot_alpha("alpha")
    sys_github["GitHub"]
    sys_gmail["Gmail"]
    bot_alpha --> sys_github
    bot_alpha --> sys_gmail
    classDef daily_life fill:#1a7f37,stroke:#1a7f37,color:#ffffff
    class bot_alpha daily_life
    classDef system fill:transparent,stroke:#8c959f,stroke-width:1.5px
    class sys_github,sys_gmail system
    linkStyle 0,1 stroke:#3192aa,stroke-width:1.5px
```

### Every edge

| From | To | Kind | Where |
|---|---|---|---|
| alpha | beta | hands off to | instructions, standup |
| GitHub | alpha | wakes | merge "watch" |
| alpha | GitHub | uses | instructions |
| alpha | Gmail | uses | merge "watch" |

## A day of scheduled routines

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="bot-chart-schedule-dark.svg">
  <img alt="A day of scheduled routines, with one row per routine and a dot at each start time. The tables below list the same times." src="bot-chart-schedule-light.svg">
</picture>

Each dot is a routine's start time. A filled dot on the left marks a bot fakkelbot adds by default, and a ring marks an optional one.

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

    def test_short_day_labels(self):
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

    def test_the_legend_names_only_the_categories_present(self):
        with fleet_dir(bot_file("a"), bot_file("b", category="Hobbies"), bot_file("c", category="Daily life")) as directory:
            self.assertEqual(bc.legend(bc.load_bots(directory)),
                             "A bot's colour is its category: green for Daily life, blue for Work and grey for other categories.")

    def test_rerun_with_another_hash_seed_is_byte_identical(self):
        with fleet_dir(*FLEET) as directory:
            outputs = []
            for seed in ("1", "2"):
                out = directory / f"out-{seed}" / "chart.md"
                env = {**os.environ, "PYTHONHASHSEED": seed}
                subprocess.run([sys.executable, str(SCRIPT), "--bots", str(directory), "--out", str(out)], check=True, env=env)
                outputs.append({path.name: path.read_bytes() for path in out.parent.iterdir()})
        self.assertEqual(len(outputs[0]), 3)
        self.assertEqual(outputs[0], outputs[1])
        self.assertIn(b"| scout | clerk | hands off to | instructions |", outputs[0]["chart.md"])

    def test_cli_writes_the_page_and_both_schedule_images(self):
        with fleet_dir(*TINY) as directory:
            self.assertEqual(bc.main(["--bots", str(directory), "--out", str(directory / "out" / "chart.md")]), 0)
            self.assertEqual(sorted(path.name for path in (directory / "out").iterdir()),
                             ["chart-schedule-dark.svg", "chart-schedule-light.svg", "chart.md"])
            self.assertIn('srcset="chart-schedule-dark.svg"', (directory / "out" / "chart.md").read_text())

    def test_cli_names_the_bot_and_routine_on_error(self):
        with fleet_dir(bot_file(routines=routines(routine(schedule="`0 9 * * mon`")))) as directory:
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = bc.main(["--bots", str(directory), "--out", str(directory / "out" / "chart.md")])
            self.assertEqual((code, stderr.getvalue(), (directory / "out").exists()),
                             (1, "bot_chart: solo: check: cannot read schedule '0 9 * * mon'\n", False))


SVG = "{http://www.w3.org/2000/svg}"


def schedule(*files, theme=bc.LIGHT):
    with fleet_dir(*files) as directory:
        return bc.schedule_svg(bc.load_bots(directory), theme)


def svg_texts(svg):
    return [text.text for text in ET.fromstring(svg).iter(SVG + "text")]


def mark_labels(svg):
    return [text.text for text in ET.fromstring(svg).iter(SVG + "text")
            if float(text.get("y")) > bc.AXIS_PX and len(text.text) == 5 and text.text[2] == ":"]


def mark_xs(svg):
    return [float(circle.get("cx")) for circle in ET.fromstring(svg).iter(SVG + "circle") if circle.get("r") == "5.5"]


class ScheduleTest(unittest.TestCase):
    def test_one_row_per_enabled_scheduled_routine_and_a_dot_per_start(self):
        svg = schedule(*TINY)
        routine_names = ("standup", 'merge "watch"', "digest: morning notes", "old-sweep")
        self.assertEqual([text for text in svg_texts(svg) if text in routine_names], ["standup", "digest: morning notes"])
        alpha, beta = mark_xs(svg)
        self.assertEqual(round(alpha - beta, 1), round((9 + 5 / 60 - 6.5) * bc.TIMELINE_PX / 6, 1))
        self.assertEqual(mark_labels(svg), ["09:05", "06:30"])

    def test_the_axis_covers_the_hours_with_runs_in_three_hour_steps(self):
        self.assertEqual([text for text in svg_texts(schedule(*TINY)) if text.endswith(":00")], ["06:00", "09:00", "12:00"])

    def test_a_crowded_row_labels_only_the_times_with_room(self):
        svg = schedule(bot_file(routines=routines(routine(schedule="`*/5 9 * * *`"))))
        self.assertEqual(len(mark_xs(svg)), 12)
        self.assertEqual(mark_labels(svg), ["09:55"])

    def test_light_and_dark_use_their_own_colours(self):
        light, dark = schedule(*TINY, theme=bc.LIGHT), schedule(*TINY, theme=bc.DARK)
        self.assertIn('fill="#ffffff"', light)
        self.assertIn('fill="#0d1117"', dark)
        self.assertIn('fill="#1a7f37"', light)
        self.assertIn('fill="#3fb950"', dark)
        self.assertNotIn("#3fb950", light)
        self.assertNotIn("#1a7f37", dark)

    def test_names_are_escaped(self):
        texts = svg_texts(schedule(bot_file("a&b", routines=routines(routine("<check>")))))
        self.assertIn("a&b", texts)
        self.assertIn("<check>", texts)

    def test_no_scheduled_routine(self):
        texts = svg_texts(schedule(bot_file()))
        self.assertIn("No routine runs on a schedule.", texts)
        self.assertEqual([text for text in texts if text.endswith(":00")],
                         ["00:00", "03:00", "06:00", "09:00", "12:00", "15:00", "18:00", "21:00", "24:00"])

if __name__ == "__main__":
    unittest.main()
