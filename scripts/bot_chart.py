#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Iterable, NamedTuple, Sequence
from uuid import UUID
from xml.sax.saxutils import escape

SCRIPT = Path(__file__).resolve()
CONFIG = json.loads(SCRIPT.with_suffix(".json").read_text(encoding="utf-8"))
ROOT = SCRIPT.parents[len(Path(CONFIG["script"]).parts) - 1]
OUT = Path(CONFIG["out"])
TIME_ZONE = CONFIG["time_zone"]
CREATION_STATUS = CONFIG["creation_status"]
NOT_CREATED = "(not created yet)"


class ChartError(Exception):
    pass


class Cron(NamedTuple):
    minute: str
    hour: str
    dom: str
    month: str
    dow: str


class RepoListener(NamedTuple):
    repo: str
    events: tuple[str, ...]


class Routine(NamedTuple):
    name: str
    crons: tuple[Cron, ...]
    listeners: tuple[RepoListener, ...]
    enabled: bool
    prompt: str


class Bot(NamedTuple):
    name: str
    category: str
    optional: bool
    instructions: str
    routines: tuple[Routine, ...]
    created: bool | None = None
    observed: str = ""
    evidence: str = ""


HANDOFF = "handoff"
USES = "uses"
WAKES = "wakes"


class Edge(NamedTuple):
    source: str
    target: str
    label: str
    kind: str


class System(NamedTuple):
    key: str
    label: str
    group: str
    patterns: tuple[str, ...]


INSTRUCTIONS = "instructions"
FAN_OUT = "each affected bot"
FAN_OUT_PHRASES = (FAN_OUT, "each changed bot", "that bot", "the bot that owns it")
OWNER_WORDS = tuple(CONFIG["owner_words"])
HANDOFF_VERBS = ("send", "sends", "tell", "tells", "ask", "asks", "hand", "hands", "pass", "passes",
                 "forward", "forwards", "relay", "relays", "message", "report", "reports")
HANDOFF_STEMS = ("send", "tell", "ask", "hand", "pass", "forward", "relay", "message", "report")
NEGATIONS = frozenset({"never", "not", "no", "don't", "without"})
NEGATION_REACH = 3
SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
CLAUSE_BREAK = re.compile(r"[,;:()]")
WORD = re.compile(r"[\w'-]+")

SYSTEMS = tuple(System(system["key"], system["label"], group, tuple(system["patterns"]))
                for group, systems in CONFIG["systems"].items() for system in systems)
SYSTEM_BY_KEY = {system.key: system for system in SYSTEMS}
GROUPS = tuple(CONFIG["systems"])
GITHUB_OWNER = CONFIG["github_owner"]
REPO_SYSTEMS = {repo.lower(): key for repo, key in CONFIG["repo_systems"].items()}
NOT_IN_A_PATH = r"(?<![\w/])"
AFTER_GITHUB_COM = r"(?<=github\.com/)"


def negated(sentence: str, start: int) -> bool:
    clause = CLAUSE_BREAK.split(sentence[:start])[-1]
    return any(word.lower() in NEGATIONS for word in WORD.findall(clause)[-NEGATION_REACH:])


def sentences(text: str) -> list[str]:
    return [part for line in text.replace("’", "'").splitlines() for part in SENTENCE_BREAK.split(line) if part.strip()]


def name_pattern(names: Iterable[str]) -> str:
    alternatives = sorted(names, key=len, reverse=True)
    return (r"(?<![\w/.-])(?:" + "|".join(re.escape(name).replace(r"\ ", r"\s+") for name in alternatives)
            + r")(?![\w/-]|\.\w)")


class EdgeRules:
    def __init__(self, bot_names: Iterable[str]):
        self.keys = {name.lower(): name for name in bot_names}
        self.skip = re.compile(r"(?i)" + name_pattern(self.keys) + r"\s*=")
        self.keys.update(dict.fromkeys(FAN_OUT_PHRASES, FAN_OUT))
        target = name_pattern(self.keys)
        self.mention = re.compile(r"(?i)" + target)
        owner = name_pattern(OWNER_WORDS)
        self.verb_then_name = re.compile(rf"(?i)\b(?:{'|'.join(HANDOFF_VERBS)})\s+(?:{owner}\s+and\s+)?(?P<name>{target})")
        self.verb = re.compile(rf"(?i)\b(?:{'|'.join(HANDOFF_STEMS)})(?:e?s|e?d)?\b")
        self.to_name = re.compile(rf"(?i)\bto\s+(?P<name>{target})")
        self.save = re.compile(r"(?i)\bsav(?:e|es|ed)\b")
        self.for_name = re.compile(rf"(?i)\bfor\s+(?P<name>{target})")
        self.systems = [(system.key, [re.compile(p) for p in system.patterns]) for system in SYSTEMS]

    def key(self, text: str) -> str:
        return self.keys[" ".join(text.split()).lower()]

    def mentions(self, sentence: str) -> set[str]:
        return {self.key(m.group()) for m in self.mention.finditer(sentence) if not negated(sentence, m.start())}

    def later(self, sentence: str, verb: re.Pattern, target: re.Pattern) -> set[str]:
        verbs = [m.start() for m in verb.finditer(sentence) if not negated(sentence, m.start())]
        return {self.key(m.group("name")) for m in target.finditer(sentence)
                if verbs and verbs[0] < m.start() and not negated(sentence, m.start("name"))}

    def handoffs(self, bot: str, sentence: str, previous: str) -> set[str]:
        found = {self.key(m.group("name")) for m in self.verb_then_name.finditer(sentence)
                 if not negated(sentence, m.start()) and not negated(sentence, m.start("name"))}
        found |= self.later(sentence, self.verb, self.to_name)
        found |= self.later(sentence, self.save, self.for_name)
        agent = sentence.find("SendToAgent")
        if agent >= 0 and not negated(sentence, agent):
            found |= (self.mentions(sentence) - {bot}) or self.mentions(previous)
        return found - {bot}

    def systems_used(self, sentence: str) -> set[str]:
        return {key for key, patterns in self.systems
                if any(not negated(sentence, m.start()) for p in patterns for m in p.finditer(sentence))}


def repo_system(repo: str) -> str:
    return REPO_SYSTEMS.get(repo.lower(), "github")


CRON_FIELD = r"[0-9*,/-]+"
FIVE_FIELDS = rf"({CRON_FIELD}) ({CRON_FIELD}) ({CRON_FIELD}) ({CRON_FIELD}) ({CRON_FIELD})"
DISK_SCHEDULE = re.compile(rf"(?:CRON_TZ=(\S+) )?{FIVE_FIELDS}")
REPORTED_CRON_TZ = re.compile(rf"\bCRON_TZ=(\S+) {FIVE_FIELDS}")
REPORTED_CRON_WORD = re.compile(rf"\bCron {FIVE_FIELDS} \(([^)]+)\)")
FIELD_LIMITS = {"minute": (0, 59), "hour": (0, 23), "dom": (1, 31), "month": (1, 12), "dow": (0, 7)}
STEPPED_FIELDS = ("minute", "hour")

SECTION_HEADING = re.compile(r"^## (?!\d+\. )")
NUMBERED_LINE = re.compile(r"^\d+\. (?P<name>.+?)\. (?P<state>Enabled|Disabled)\.(?:\s|$)")
NUMBERED_HEADING = re.compile(r"^## \d+\. (?P<name>.+)$")
STATE_LINE = re.compile(r"^(?P<state>Enabled|Disabled)\.(?:\s|$)")
DISK_FIELD = re.compile(r"^- \*\*(?P<key>[A-Za-z ]+):\*\* (?P<value>.*)$")
CODE_SPAN = re.compile(r"`([^`]*)`")
REPORTED_MARK = "(reported by bot"


def expand(field: str, value: str, where: str) -> tuple[int, ...]:
    low, high = FIELD_LIMITS[field]
    values: set[int] = set()
    for part in value.split(","):
        span, _, step_text = part.partition("/")
        if step_text and field not in STEPPED_FIELDS:
            raise ChartError(f"{where}: steps are not supported in the {field} field ({value!r})")
        if span == "*":
            start, end = low, high
        elif re.fullmatch(r"\d+", span):
            start = end = int(span)
        elif re.fullmatch(r"\d+-\d+", span):
            start, end = (int(n) for n in span.split("-"))
        else:
            raise ChartError(f"{where}: cannot read the {field} field {value!r}")
        if step_text and not re.fullmatch(r"[1-9]\d*", step_text):
            raise ChartError(f"{where}: cannot read the step in the {field} field {value!r}")
        if not low <= start <= end <= high:
            raise ChartError(f"{where}: the {field} field {value!r} is out of range")
        if step_text and span != "*" and start == end:
            end = high
        values.update(range(start, end + 1, int(step_text or 1)))
    if field == "dow" and 7 in values:
        values = (values - {7}) | {0}
    return tuple(sorted(values))


def make_cron(where: str, fields: Sequence[str], zone: str | None) -> Cron:
    if zone is not None and zone != TIME_ZONE:
        raise ChartError(f"{where}: schedule uses time zone {zone}, expected {TIME_ZONE or 'none'}")
    cron = Cron(*fields)
    for field, value in zip(Cron._fields, cron):
        expand(field, value, where)
    if cron.dom != "*" and cron.dow != "*":
        raise ChartError(f"{where}: cron {' '.join(cron)} restricts both day of month and day of week")
    return cron


def parse_schedule(where: str, text: str) -> Cron:
    match = DISK_SCHEDULE.fullmatch(text.strip())
    if not match or (match.group(1) and not TIME_ZONE):
        raise ChartError(f"{where}: cannot read schedule {text!r}")
    return make_cron(where, match.groups()[1:], match.group(1))


def reported_cron(where: str, line: str) -> Cron:
    cron_tz = REPORTED_CRON_TZ.search(line)
    if cron_tz:
        return make_cron(where, cron_tz.groups()[1:], cron_tz.group(1))
    cron_word = REPORTED_CRON_WORD.search(line)
    if cron_word:
        return make_cron(where, cron_word.groups()[:5], cron_word.group(6))
    raise ChartError(f"{where}: no cron on the routine's header line {line!r}")


def trigger_parts(where: str, trigger: dict) -> tuple[tuple[Cron, ...], tuple[RepoListener, ...]]:
    kind = trigger.get("type")
    if kind == "github":
        return (), (RepoListener(trigger["repo"], tuple(trigger["events"])),)
    if kind == "cron":
        return (parse_schedule(where, trigger["schedule"]),), ()
    if kind == "group":
        crons: tuple[Cron, ...] = ()
        listeners: tuple[RepoListener, ...] = ()
        for listener in trigger["listeners"]:
            more_crons, more_listeners = trigger_parts(where, listener)
            crons += more_crons
            listeners += more_listeners
        return crons, listeners
    raise ChartError(f"{where}: unknown trigger type {kind!r}")


def fence_starts(lines: Sequence[str]) -> list[int]:
    return [i for i, line in enumerate(lines) if line.startswith("```")]


def fenced_text(lines: Sequence[str], where: str) -> str:
    starts = fence_starts(lines)
    if len(starts) < 2:
        raise ChartError(f"{where}: no text block")
    return "\n".join(lines[starts[0] + 1 : starts[1]])


def fields(lines: Iterable[str]) -> dict[str, str]:
    found = {}
    for line in lines:
        match = DISK_FIELD.match(line)
        if match:
            value = match.group("value").strip()
            span = CODE_SPAN.match(value)
            found[match.group("key")] = span.group(1) if span else value
    return found


def split_at_unfenced_headings(lines: Sequence[str], is_heading) -> tuple[list[str], list[tuple[str, list[str]]]]:
    preamble: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    in_fence = False
    for line in lines:
        if line.startswith("```"):
            in_fence = not in_fence
        if not in_fence and is_heading(line):
            sections.append((line, []))
        else:
            (sections[-1][1] if sections else preamble).append(line)
    return preamble, sections


def trimmed(lines: Sequence[str]) -> str:
    return "\n".join(lines).strip("\n")


def disk_routines(bot: str, body: Sequence[str]) -> list[Routine]:
    preamble, sections = split_at_unfenced_headings(body, lambda line: line.startswith("### "))
    stray = [line for line in preamble if DISK_FIELD.match(line)]
    if stray:
        raise ChartError(f"{bot}: a routine field under ## Routines has no ### heading: {stray[0]!r}")
    routines = []
    for heading, lines in sections:
        name = heading[len("### "):].strip()
        where = f"{bot}: {name}"
        prompt = fenced_text(lines, where)
        values = fields(lines[:fence_starts(lines)[0]])
        enabled = values.get("Enabled", "").lower()
        if enabled not in ("true", "false"):
            raise ChartError(f"{where}: Enabled must be true or false")
        crons: tuple[Cron, ...] = ()
        if values.get("Schedule", "None") != "None":
            crons = (parse_schedule(where, values["Schedule"]),)
        listeners: tuple[RepoListener, ...] = ()
        if "Trigger" in values:
            try:
                trigger_crons, listeners = trigger_parts(where, json.loads(values["Trigger"]))
            except (ValueError, KeyError, TypeError, AttributeError) as error:
                raise ChartError(f"{where}: cannot read trigger {values['Trigger']!r} ({error!r})") from error
            crons = tuple(dict.fromkeys(crons + trigger_crons))
        routines.append(Routine(name, crons, listeners, enabled == "true", prompt))
    return routines


def reported_routines(bot: str, body: Sequence[str]) -> list[Routine]:
    content = trimmed(body)
    if content.startswith("None."):
        return []
    _, sections = split_at_unfenced_headings(body, lambda line: NUMBERED_LINE.match(line) or NUMBERED_HEADING.match(line))
    if not sections and content:
        raise ChartError(f"{bot}: could not find any routine under the reported routines heading")
    routines = []
    for heading, lines in sections:
        numbered = NUMBERED_LINE.match(heading)
        if numbered:
            name, state, cron_line = numbered.group("name"), numbered, heading
        else:
            name = NUMBERED_HEADING.match(heading).group("name").strip()
            cron_line = lines[0] if lines else ""
            state = STATE_LINE.match(cron_line)
            if not state:
                raise ChartError(f"{bot}: {name}: expected Enabled. or Disabled. after the heading")
        routines.append(Routine(name, (reported_cron(f"{bot}: {name}", cron_line),), (),
                                state.group("state") == "Enabled", trimmed([heading, *lines])))
    return routines


def creation(name: str, header: dict[str, str]) -> tuple[bool | None, str, str]:
    observed, evidence = header.get("Observed", ""), header.get("Evidence", "")
    if "Created" in header:
        states = {"yes": True, "no": False, "unknown": None}
        if header["Created"] not in states:
            raise ChartError(f"{name}: Created must be yes, no or unknown")
        created = states[header["Created"]]
        if created is not None and not (observed and evidence):
            raise ChartError(f"{name}: Created yes/no needs Observed and Evidence")
    else:
        identity = header.get("ID", "")
        created = None
        if identity == NOT_CREATED:
            created = False
        else:
            try:
                UUID(identity)
            except ValueError:
                pass
            else:
                created = True
    if observed:
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", observed):
                raise ValueError
            date.fromisoformat(observed)
        except ValueError:
            raise ChartError(f"{name}: Observed must be a valid YYYY-MM-DD date") from None
    return created, observed, evidence


def parse_bot(path: Path) -> Bot:
    lines = path.read_text(encoding="utf-8").splitlines()
    preamble, sections = split_at_unfenced_headings(lines, SECTION_HEADING.match)
    titles = [line[2:].strip() for line in preamble if line.startswith("# ")]
    if not titles:
        raise ChartError(f"{path.name}: no '# ' heading with the bot's name")
    name = titles[0]
    header = fields(preamble)
    created, observed, evidence = creation(name, header) if CREATION_STATUS else (None, "", "")
    optional = not CREATION_STATUS and header.get("Default", "").lower() == "no"
    instructions = None
    routines: list[Routine] = []
    for heading, body in sections:
        if heading.startswith("## Instructions"):
            instructions = fenced_text(body, f"{name}: instructions")
        elif heading.strip() == "## Routines":
            routines += disk_routines(name, body)
        elif REPORTED_MARK in heading:
            routines += reported_routines(name, body)
        elif "routines" in heading.lower():
            raise ChartError(f"{name}: unknown routines heading {heading!r}")
    if instructions is None:
        raise ChartError(f"{name}: no ## Instructions section")
    return Bot(name, header.get("Category", ""), optional, instructions, tuple(routines), created, observed, evidence)


def load_bots(directory: Path) -> list[Bot]:
    paths = [path for path in sorted(directory.glob("*.md")) if path.name.lower() != "readme.md"]
    bots = sorted((parse_bot(path) for path in paths), key=lambda bot: bot.name.lower())
    for first, second in zip(bots, bots[1:]):
        if first.name.lower() == second.name.lower():
            raise ChartError(f"two bot files share the name {second.name}")
    return bots


def bot_texts(bot: Bot) -> list[tuple[str, str]]:
    return [(INSTRUCTIONS, bot.instructions)] + [(routine.name, routine.prompt) for routine in bot.routines]


def find_edges(bots: Sequence[Bot]) -> set[Edge]:
    rules = EdgeRules(bot.name for bot in bots)
    edges = set()
    for bot in bots:
        for label, text in bot_texts(bot):
            previous = ""
            for sentence in sentences(text):
                if rules.skip.search(sentence):
                    previous = ""
                    continue
                targets = rules.handoffs(bot.name, sentence, previous)
                edges.update(Edge(bot.name, target, label, HANDOFF) for target in targets)
                edges.update(Edge(bot.name, key, label, USES) for key in rules.systems_used(sentence))
                previous = sentence
        for routine in bot.routines:
            edges.update(Edge(repo_system(l.repo), bot.name, routine.name, WAKES) for l in routine.listeners)
    return edges


def github_repos(bots: Sequence[Bot]) -> set[str]:
    mention = re.compile(rf"(?:{NOT_IN_A_PATH}|{AFTER_GITHUB_COM}){re.escape(GITHUB_OWNER)}/([A-Za-z0-9._-]+)")
    repos = {listener.repo for bot in bots for routine in bot.routines for listener in routine.listeners}
    repos.update(f"{GITHUB_OWNER}/" + m.group(1).rstrip("._-")
                 for bot in bots for _, text in bot_texts(bot) for m in mention.finditer(text))
    return {repo.lower() for repo in repos if repo_system(repo) == "github"}


WEEKDAYS = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")
WEEKDAY_PLURALS = ("Sundays", "Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
KIND_WORDS = {HANDOFF: "hands off to", WAKES: "wakes", USES: "uses"}
SYSTEM_ORDER = {system.key: i for i, system in enumerate(SYSTEMS)}


def config_text(key: str) -> str:
    readme = CONFIG["readme"]
    link = f"[{readme.partition('#')[0]}]({'../' * (len(OUT.parts) - 1)}{readme})"
    return CONFIG[key].format(script=CONFIG["script"], readme=link, time_zone=TIME_ZONE)


HEADER = f"> Generated by `{CONFIG['script']}` from `bots/*.md`. Don't edit this file by hand. {config_text('regenerate')}"
TITLE = config_text("title")
INTRO = config_text("intro")
if CREATION_STATUS:
    PALE_NOTE = "A pale bot with a dashed outline is not created yet."
    DOT_NOTE = "Each dot is a routine's start time, in its bot's colour. Creation status is in the tables, not the image."
else:
    PALE_NOTE = "A pale bot with a dashed outline is one that setup adds only when the owner asks for it."
    DOT_NOTE = ("Each dot is a routine's start time. A filled dot on the left marks a bot setup adds by default, "
                "and a ring marks an optional one.")


class Colour(NamedTuple):
    word: str
    light: str
    dark: str


CATEGORY_COLOURS = {name: Colour(**colour) for name, colour in CONFIG["categories"].items()}
OTHER_CATEGORY = "other"
OTHER_COLOUR = Colour("grey", "#59636e", "#9198a1")
ARROW_STYLES = {
    HANDOFF: "stroke:#8c959f,stroke-width:1.5px",
    WAKES: "stroke:#d4a72c,stroke-width:3px",
    USES: "stroke:#3192aa,stroke-width:1.5px",
}
OUTLINE = "#8c959f"
PALE_TINT = "26"
FLOWCHART_INIT = '%%{init: {"flowchart": {"curve": "basis"}}}%%'


class Theme(NamedTuple):
    name: str
    background: str
    border: str
    text: str
    muted: str
    grid: str
    grid_major: str
    band: str


LIGHT = Theme("light", "#ffffff", "#d1d9e0", "#1f2328", "#59636e", "#eff2f5", "#d1d9e0", "#f6f8fa")
DARK = Theme("dark", "#0d1117", "#3d444d", "#f0f6fc", "#9198a1", "#1b2129", "#3d444d", "#151b23")
THEMES = (LIGHT, DARK)
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
NAME_PX, TEXT_PX, SMALL_PX = 7.8, 7.2, 6.3
PAD, TIMELINE_PX, ROW_PX, AXIS_PX = 20, 600, 30, 44


def join_and(items: Sequence[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def join_commas(items: Sequence[str]) -> str:
    return ", ".join(items)


def ordinal(n: int) -> str:
    suffix = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def clock(time: tuple[int, int]) -> str:
    return f"{time[0]:02d}:{time[1]:02d}"


def run_times(cron: Cron) -> list[tuple[int, int]]:
    return sorted((hour, minute) for hour in expand("hour", cron.hour, "")
                  for minute in expand("minute", cron.minute, ""))


def weekday_words(days: Sequence[int], short: bool) -> str:
    days = list(days)
    if len(days) == 7:
        return "daily"
    if days == [1, 2, 3, 4, 5]:
        return "weekdays"
    if days == [0, 6]:
        return "weekends"
    if len(days) == 1:
        return WEEKDAYS[days[0]] if short else WEEKDAY_PLURALS[days[0]]
    names = [WEEKDAYS[day] for day in days]
    if len(days) >= 3 and days == list(range(days[0], days[-1] + 1)):
        return f"{names[0]} to {names[-1]}"
    return join_commas(names) if short else join_and(names)


def day_words(cron: Cron, short: bool) -> str:
    listing = join_commas if short else join_and
    if cron.dom != "*":
        doms = expand("dom", cron.dom, "")
        if cron.month == "*":
            days = listing([ordinal(day) for day in doms])
            return f"{days} of month" if short else f"on the {days} of each month"
        days = listing([str(day) for day in doms])
        dates = listing([f"{MONTHS[month - 1]} {days}" for month in expand("month", cron.month, "")])
        return dates if short else f"on {dates}"
    words = weekday_words(expand("dow", cron.dow, ""), short)
    if cron.month != "*":
        words += " in " + listing([MONTHS[month - 1] for month in expand("month", cron.month, "")])
    return words


def times_by_days(crons: Sequence[Cron], short: bool) -> dict[str, list[tuple[int, int]]]:
    found: dict[str, set[tuple[int, int]]] = {}
    for cron in crons:
        found.setdefault(day_words(cron, short), set()).update(run_times(cron))
    return {days: sorted(times) for days, times in found.items()}


def schedule_words(crons: Sequence[Cron]) -> str:
    if not crons:
        return "none"
    return "; ".join(f"{days} at {join_commas([clock(time) for time in times])}"
                     for days, times in times_by_days(crons, short=False).items())


def trigger_words(listeners: Sequence[RepoListener]) -> str:
    if not listeners:
        return "none"
    repos_by_events: dict[tuple[str, ...], list[str]] = {}
    for listener in listeners:
        repos_by_events.setdefault(listener.events, []).append(listener.repo.split("/")[-1])
    return "; ".join(f"{join_commas(events)} in {join_commas(repos)}" for events, repos in repos_by_events.items())


def creation_note(bot: Bot) -> str:
    if not CREATION_STATUS:
        return ""
    return {True: "", False: NOT_CREATED, None: "(creation unknown)"}[bot.created]


def bot_title(bot: Bot) -> str:
    return f"{bot.name} {'(optional)' if bot.optional else creation_note(bot)}".rstrip()


def category(bot: Bot) -> str:
    return bot.category if bot.category in CATEGORY_COLOURS else OTHER_CATEGORY


def colour(bot: Bot) -> Colour:
    return CATEGORY_COLOURS.get(bot.category, OTHER_COLOUR)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def node_id(key: str) -> str:
    prefix = "fan_" if key == FAN_OUT else "sys_" if key in SYSTEM_BY_KEY else "bot_"
    return prefix + slug(key)


def node_order(key: str) -> tuple[int, str]:
    return SYSTEM_ORDER.get(key, -1), key.lower()


def label_order(label: str) -> tuple[bool, str, str]:
    return label != INSTRUCTIONS, label.lower(), label


def quoted(text: str) -> str:
    return '"' + text.replace('"', "#quot;") + '"'


def grouped(edges: Iterable[Edge]) -> dict[tuple[str, str], list[str]]:
    labels: dict[tuple[str, str], set[str]] = {}
    for edge in edges:
        labels.setdefault((edge.source, edge.target), set()).add(edge.label)
    pairs = sorted(labels, key=lambda pair: (node_order(pair[0]), node_order(pair[1])))
    return {pair: sorted(labels[pair], key=label_order) for pair in pairs}


def bot_node(bot: Bot) -> str:
    note = creation_note(bot)
    label = f"{bot.name}<br/>{note}" if note else bot.name
    return f"    {node_id(bot.name)}({quoted(label)})"


def node_styles(bots: Iterable[Bot], systems: Iterable[str] = (), fan_out: bool = False) -> list[str]:
    classes: dict[str, tuple[str, list[str]]] = {}
    for bot in bots:
        name, hue = slug(category(bot)), colour(bot).light
        style = f"fill:{hue},stroke:{hue},color:#ffffff"
        if bot.optional or bot.created is False:
            name = f"{name}_optional" if bot.optional else f"{name}_planned"
            style = f"fill:{hue}{PALE_TINT},stroke:{hue},stroke-width:2px,stroke-dasharray:5 3"
        classes.setdefault(name, (style, []))[1].append(node_id(bot.name))
    systems = sorted(systems, key=node_order)
    if systems:
        classes["system"] = (f"fill:transparent,stroke:{OUTLINE},stroke-width:1.5px", [node_id(key) for key in systems])
    if fan_out:
        classes["fan_out"] = (f"fill:transparent,stroke:{OUTLINE},stroke-dasharray:4 3", [node_id(FAN_OUT)])
    lines = []
    for name, (style, ids) in classes.items():
        lines += [f"    classDef {name} {style}", f"    class {','.join(ids)} {name}"]
    return lines


def link_styles(kinds: Sequence[str]) -> list[str]:
    indexes: dict[str, list[str]] = {}
    for index, kind in enumerate(kinds):
        indexes.setdefault(kind, []).append(str(index))
    return [f"    linkStyle {','.join(ids)} {ARROW_STYLES[kind]}" for kind, ids in indexes.items()]


def system_labels(bots: Sequence[Bot]) -> dict[str, str]:
    labels = {system.key: system.label for system in SYSTEMS}
    if GITHUB_OWNER:
        repos = len(github_repos(bots))
        labels["github"] += f" ({repos} repo{'' if repos == 1 else 's'})"
    return labels


class Chart:
    def __init__(self, bots: Sequence[Bot], edges: set[Edge]):
        self.bots = bots
        self.edges = edges
        self.system_labels = system_labels(bots)

    def system_nodes(self, keys: Iterable[str]) -> list[str]:
        return [f"    {node_id(key)}[{quoted(self.system_labels[key])}]" for key in sorted(keys, key=node_order)]

    def handoffs_and_wakes(self) -> list[str]:
        handoffs = grouped(edge for edge in self.edges if edge.kind == HANDOFF)
        wakes = grouped(edge for edge in self.edges if edge.kind == WAKES)
        fan_out = any(target == FAN_OUT for _, target in handoffs)
        systems = {source for source, _ in wakes}
        lines = [FLOWCHART_INIT, "flowchart TB", *(bot_node(bot) for bot in self.bots)]
        if fan_out:
            lines.append(f"    {node_id(FAN_OUT)}([{quoted(FAN_OUT)}])")
        lines += self.system_nodes(systems)
        lines += [f"    {node_id(source)} --> {node_id(target)}" for source, target in handoffs]
        for (source, target), labels in wakes.items():
            label = f"wakes: {labels[0]}" if len(labels) == 1 else f"wakes: {len(labels)} routines"
            lines.append(f"    {node_id(source)} ==>|{quoted(label)}| {node_id(target)}")
        lines += node_styles(self.bots, systems, fan_out)
        return lines + link_styles([HANDOFF] * len(handoffs) + [WAKES] * len(wakes))

    def uses(self, group: str) -> list[str]:
        pairs = grouped(edge for edge in self.edges if edge.kind == USES and SYSTEM_BY_KEY[edge.target].group == group)
        if not pairs:
            return []
        users = [bot for bot in self.bots if any(source == bot.name for source, _ in pairs)]
        systems = {target for _, target in pairs}
        lines = [FLOWCHART_INIT, "flowchart TB", *(bot_node(bot) for bot in users), *self.system_nodes(systems)]
        lines += [f"    {node_id(source)} --> {node_id(target)}" for source, target in pairs]
        return lines + node_styles(users, systems) + link_styles([USES] * len(pairs))


def legend(bots: Sequence[Bot]) -> str:
    present = {category(bot) for bot in bots}
    words = [f"{CATEGORY_COLOURS[name].word} for {name}" for name in CATEGORY_COLOURS if name in present]
    others = {bool(bot.category) for bot in bots if category(bot) == OTHER_CATEGORY}
    if not words and others == {False}:
        return f"A bot's colour comes from the Category line in its file. No bot file has one yet, so every bot is {OTHER_COLOUR.word}."
    if others:
        whom = "other categories or none" if len(others) == 2 else "other categories" if True in others else "bots without one"
        words.append(f"{OTHER_COLOUR.word} for {whom}")
    return f"A bot's colour is its category: {join_and(words)}."


def mermaid(lines: Sequence[str]) -> list[str]:
    return ["```mermaid", *lines, "```"]


def cell(text: str) -> str:
    return text.replace("|", "\\|")


def creation_table(bots: Sequence[Bot]) -> list[str]:
    states = {True: "Created", False: "Not created", None: "Unknown"}
    return ["| Bot | Recorded creation status | Last observed | Evidence |", "|---|---|---|---|", *[
        f"| {cell(bot.name)} | {states[bot.created]} | {bot.observed or 'Not recorded'} | "
        f"{cell(bot.evidence) if bot.evidence else 'Not recorded'} |" for bot in bots
    ]]


def edge_table(edges: set[Edge]) -> list[str]:
    def name(key: str) -> str:
        return SYSTEM_BY_KEY[key].label if key in SYSTEM_BY_KEY else key

    rows = []
    for kind in (HANDOFF, WAKES, USES):
        for (source, target), labels in grouped(edge for edge in edges if edge.kind == kind).items():
            rows.append(f"| {cell(name(source))} | {cell(name(target))} | {KIND_WORDS[kind]} | "
                        f"{cell(', '.join(labels))} |")
    return ["| From | To | Kind | Where |", "|---|---|---|---|", *rows]


class Row(NamedTuple):
    bot: Bot
    routine: str
    days: str
    times: tuple[tuple[int, int], ...]


def schedule_rows(bots: Sequence[Bot]) -> list[Row]:
    return [Row(bot, routine.name, days, tuple(times))
            for bot in bots for routine in bot.routines if routine.enabled
            for days, times in times_by_days(routine.crons, short=True).items()]


def px(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def text_px(text: str, per_char: float) -> float:
    return len(text) * per_char


def svg_text(x: float, y: float, text: str, fill: str, size: float, extra: str = "") -> str:
    return f'<text x="{px(x)}" y="{px(y)}" fill="{fill}" font-size="{px(size)}"{extra}>{escape(text)}</text>'


def hour_span(rows: Sequence[Row]) -> tuple[int, int]:
    hours = [hour for row in rows for hour, _ in row.times]
    if not hours:
        return 0, 24
    return min(hours) // 3 * 3, min(24, -(-(max(hours) + 1) // 3) * 3)


def schedule_svg(bots: Sequence[Bot], theme: Theme) -> str:
    rows = schedule_rows(bots)
    first, last = hour_span(rows)
    hour_px = TIMELINE_PX / (last - first)
    bot_width = max([text_px(row.bot.name, NAME_PX) + (text_px(" optional", SMALL_PX) if row.bot.optional else 0)
                     for row in rows], default=0) + 40
    routine_width = max([text_px(row.routine, TEXT_PX) for row in rows], default=0) + 20
    days_width = max([text_px(row.days, SMALL_PX) for row in rows], default=0) + 24
    left = PAD + bot_width + routine_width + days_width
    width = left + TIMELINE_PX + PAD + 16
    bottom = AXIS_PX + max(len(rows), 1) * ROW_PX
    height = bottom + PAD
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{px(width)}" height="{px(height)}" '
        f'viewBox="0 0 {px(width)} {px(height)}" role="img" aria-labelledby="title">',
        '<title id="title">A day of scheduled routines</title>',
        f"<style>text {{ font-family: {FONT}; }}</style>",
        f'<rect x="0.5" y="0.5" width="{px(width - 1)}" height="{px(height - 1)}" rx="10" '
        f'fill="{theme.background}" stroke="{theme.border}"/>',
    ]
    starts = [i for i, row in enumerate(rows) if i == 0 or rows[i - 1].bot != row.bot]
    for number, start in enumerate(starts):
        end = starts[number + 1] if number + 1 < len(starts) else len(rows)
        if number % 2:
            parts.append(f'<rect x="1" y="{px(AXIS_PX + start * ROW_PX)}" width="{px(width - 2)}" '
                         f'height="{px((end - start) * ROW_PX)}" fill="{theme.band}"/>')
    for hour in range(first, last + 1):
        x = left + (hour - first) * hour_px
        major = hour % 3 == 0
        parts.append(f'<line x1="{px(x)}" y1="{px(AXIS_PX - 6)}" x2="{px(x)}" y2="{px(bottom)}" '
                     f'stroke="{theme.grid_major if major else theme.grid}"/>')
        if major:
            parts.append(svg_text(x, AXIS_PX - 14, f"{hour:02d}:00", theme.muted, 11, ' text-anchor="middle"'))
    if not rows:
        parts.append(svg_text(left + TIMELINE_PX / 2, AXIS_PX + ROW_PX / 2 + 4, "No routine runs on a schedule.",
                              theme.muted, 13, ' text-anchor="middle"'))
    for index, row in enumerate(rows):
        middle = AXIS_PX + index * ROW_PX + ROW_PX / 2
        hue = getattr(colour(row.bot), theme.name)
        halo = theme.band if len([start for start in starts if start <= index]) % 2 == 0 else theme.background
        if index in starts:
            dot = (f'fill="none" stroke="{hue}" stroke-width="2"' if row.bot.optional else f'fill="{hue}"')
            parts.append(f'<circle cx="{px(PAD + 6)}" cy="{px(middle)}" r="5" {dot}/>')
            parts.append(svg_text(PAD + 20, middle + 4.5, row.bot.name, theme.text, 13, ' font-weight="600"'))
            if row.bot.optional:
                parts.append(svg_text(PAD + 20 + text_px(row.bot.name, NAME_PX) + 5, middle + 4, "optional",
                                      theme.muted, 11))
        parts.append(svg_text(PAD + bot_width, middle + 4.5, row.routine, theme.text, 13))
        parts.append(svg_text(PAD + bot_width + routine_width, middle + 4, row.days, theme.muted, 11.5))
        xs = [left + (hour - first + minute / 60) * hour_px for hour, minute in row.times]
        for number, (x, time) in enumerate(zip(xs, row.times)):
            parts.append(f'<circle cx="{px(x)}" cy="{px(middle)}" r="5.5" fill="{hue}" '
                         f'stroke="{theme.background}" stroke-width="2"/>')
            label = clock(time)
            room = xs[number + 1] - x if number + 1 < len(xs) else left + TIMELINE_PX + PAD - x
            if room >= 10 + text_px(label, SMALL_PX) + 6:
                parts.append(svg_text(x + 9, middle + 4, label, theme.muted, 11,
                                      f' stroke="{halo}" stroke-width="4" paint-order="stroke"'))
    return "\n".join([*parts, "</svg>"]) + "\n"


def schedule_files(stem: str) -> dict[Theme, str]:
    return {theme: f"{stem}-schedule-{theme.name}.svg" for theme in THEMES}


def schedule_notes(bots: Sequence[Bot]) -> str:
    disabled = [f"{bot.name}'s {routine.name}"
                for bot in bots for routine in bot.routines if routine.crons and not routine.enabled]
    notes = [DOT_NOTE]
    if len(disabled) == 1:
        notes.append(f"The chart leaves out one disabled routine, {disabled[0]}.")
    elif disabled:
        notes.append(f"The chart leaves out {len(disabled)} disabled routines, which are {join_and(disabled)}.")
    notes.append("Routines that only run on GitHub events are in the tables below.")
    return "\n\n".join(notes)


def routine_tables(bots: Sequence[Bot]) -> list[str]:
    lines = []
    for bot in bots:
        lines += [f"### {bot_title(bot)}", ""]
        if bot.routines:
            lines += ["| Routine | Schedule | Trigger | Enabled |", "|---|---|---|---|"]
            lines += [f"| {cell(r.name)} | {schedule_words(r.crons)} | {cell(trigger_words(r.listeners))} | "
                      f"{'yes' if r.enabled else 'no'} |" for r in bot.routines]
        else:
            lines.append("No routines.")
        lines.append("")
    return lines[:-1]


def render(bots: Sequence[Bot], stem: str = OUT.stem) -> str:
    edges = find_edges(bots)
    files = schedule_files(stem)
    chart = Chart(bots, edges)
    lines = [HEADER, "", f"# {TITLE}", "", INTRO, ""]
    if CREATION_STATUS:
        lines += [
            "## Recorded setup", "",
            "Creation status and its observation date come from each bot's header. This is not a live poll or verification of every routine. "
            "An undated legacy ID records existence in an earlier export; a missing ID stays unknown.", "",
            *creation_table(bots), "",
        ]
    lines += [
        "## Who talks to whom", "",
        "### Hand-offs and what wakes each bot", "",
        "Grey arrows are hand-offs between bots. The table of every edge below says where each one appears. "
        "Thick amber arrows are GitHub events that wake a bot. "
        f"{legend(bots)} {PALE_NOTE}", "",
        *mermaid(chart.handoffs_and_wakes()), "",
    ]
    for group in GROUPS:
        uses = chart.uses(group)
        lines += [f"### {group}", ""]
        if uses:
            lines += ["Each teal arrow points from a bot to a system it uses.", "", *mermaid(uses)]
        else:
            lines.append("No bot uses an outside system." if len(GROUPS) == 1 else "No bot uses these systems.")
        lines.append("")
    lines += ["### Every edge", "", *edge_table(edges), ""]
    lines += [
        "## A day of scheduled routines", "",
        "<picture>",
        f'  <source media="(prefers-color-scheme: dark)" srcset="{files[DARK]}">',
        f'  <img alt="A day of scheduled routines, with one row per routine and a dot at each start time. '
        f'The tables below list the same times." src="{files[LIGHT]}">',
        "</picture>", "",
        schedule_notes(bots), "",
    ]
    lines += ["## Routines by bot", "", *routine_tables(bots)]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"Write {OUT.as_posix()} and its schedule images from the bot files in bots/.")
    parser.add_argument("--bots", type=Path, default=ROOT / "bots", help="folder of bot files (default: bots/)")
    parser.add_argument("--out", type=Path, default=ROOT / OUT,
                        help=f"page to write, with its images beside it (default: {OUT.as_posix()})")
    args = parser.parse_args(argv)
    try:
        bots = load_bots(args.bots)
        if not bots:
            raise ChartError(f"no bot files in {args.bots}")
        outputs = {args.out: render(bots, args.out.stem)}
        for theme, name in schedule_files(args.out.stem).items():
            outputs[args.out.with_name(name)] = schedule_svg(bots, theme)
    except ChartError as error:
        print(f"{SCRIPT.stem}: {error}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    for path, text in outputs.items():
        with open(path, "w", encoding="utf-8", newline="\n") as out:
            out.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
