# scripts

## leak_check.py

`leak_check.py` checks a repository and its whole history for the terms you list, including old commits. Run it before you make a copy public.

It needs Python 3.9 or newer and git. It scans the following.

- Every file in every commit on every branch and tag, and the file names.
- Every commit message, and every author and committer name and email.
- Every tag name, tag message and tagger, and every branch name.

### Keep the denylist outside the repo

The list of terms is itself personal, so it never goes in the repo. Keep it in a file of your own, for example `~/private/denylist.txt`.

```text
# one term per line
jane example
jane@example.com
re:555-01\d\d
```

- Blank lines and lines starting with `#` are ignored.
- A plain line is a case-insensitive literal.
- A line starting with `re:` is a case-insensitive regular expression.
- Surrounding spaces are trimmed. Use `\s` in a regular expression when a space matters.

### Run the check

Use a full clone. A shallow clone has no old commits, and the script warns when it sees one.

```sh
python3 scripts/leak_check.py --denylist ~/private/denylist.txt
python3 scripts/leak_check.py --denylist ~/private/denylist.txt --repo ../other-copy
```

Do not run it in CI with a denylist, because the list would have to be stored there.

### Read the output

Each hit is one line. The script never prints the matched text or the line it was in, so a terminal or CI log does not repeat the leak.

```text
3f2a9b1 notes.txt:2 denylist:3
msg 3f2a9b1:1 denylist:1
author 3f2a9b1:committer-email denylist:2
tag 9c04d7e:name denylist:1
```

| Line starts with | Meaning |
|---|---|
| a short sha, then a path and a line number | that line of that file, in the first commit that has it. `git show 3f2a9b1:notes.txt` shows it |
| a short sha, then a path and `path` | the file name itself matched. The line shows `blob-<id>` in place of the name, unless you pass `--show` |
| `msg` | that line of the commit message |
| `author` | `author-name`, `author-email`, `committer-name` or `committer-email` of the commit |
| `tag` | the tag, by the id of its tag object, or of the commit for a lightweight tag. `git for-each-ref --points-at 9c04d7e` finds it |
| `branch` | the branch, by the commit it points at |

`denylist:3` is the line number in your denylist file, counting blank and comment lines.

A summary goes to stderr, including how many binary files were skipped. `--show` adds the matched text to each line. Use it only on your own machine.

The exit status is 0 when clean, 1 when there are hits and 2 for bad usage, such as a missing file or a bad regular expression.

### Allow a known match

Some matches are fine, such as your name in `LICENSE`. List them in an allow file and pass it with `--allow`. Each line is a path glob, a tab, then the exact text. Blank lines and lines starting with `#` are ignored.

```text
LICENSE	Jane Example
*	example-org/example-app
git:author	Jane Example
```

- A match counts unless it falls entirely inside the allowed text on its line. A match that sticks out of it still counts.
- The text is case sensitive.
- The glob is matched against the whole path, and `*` also matches `/`.
- For text outside files, use the globs `git:msg`, `git:author`, `git:tag` and `git:branch`. `*` matches all of them. `git:author` also covers the name and email of a tagger.

### What it does not catch

- Binary files are not read. A file with a NUL byte in its first 8000 bytes counts as binary, which includes UTF-16 text. Images and PDFs can carry names in their metadata, so check them by hand.
- The signature block of a signed tag is not read.
- Terms are matched one line at a time, so a term split over two lines is missed.
- Accented letters in a different Unicode form do not match. List both spellings. Text that is not UTF-8 is read with replacement characters, so accented terms in it may not match.
- It finds only what you list. It does not remove anything. Removing an old hit means rewriting history.

## bot_chart.py

`bot_chart.py` reads every bot file in `bots/` and writes [the bot chart](../docs/bot-chart.md), `docs/bot-chart.md`. The page shows which bots hand work to which, what wakes each bot, which outside systems each bot uses, and when the scheduled routines run.

- GitHub draws the hand-off and system charts from their Mermaid text. Each bot is coloured by its **Category**, and an optional bot is pale with a dashed outline. Hand-off arrows are grey, wake arrows are thick and amber, and arrows to outside systems are teal.
- The schedule is two images the script draws, `docs/bot-chart-schedule-light.svg` and `docs/bot-chart-schedule-dark.svg`. GitHub shows the one that matches the reader's light or dark theme. Each enabled routine with a schedule gets a row, with a dot at each start time. The time axis covers only the hours that have runs, in 3-hour steps.

### Settings

Everything specific to this repo's chart is in `scripts/bot_chart.json`, beside the script. The script is the same file in every copy, so you can take a newer `bot_chart.py` and keep your settings. The JSON sets:

- `categories`: each category's colour word for the legend, and its colour in light and dark themes.
- `systems`: the outside systems, under the heading of the chart that shows them. Each has a `key`, a `label` and `patterns`, which are Python regular expressions with every backslash doubled. Keep the `github` system, because GitHub triggers come from it. With more than one heading, the page draws one chart per heading.
- `owner_words`: what the bot files call the owner, as in "tell the owner and liaison".
- `time_zone`: `null`, so a schedule with a `CRON_TZ=` prefix is an error. With a time zone name, every schedule must use that zone, and a schedule without one counts as that zone.
- `github_owner` and `repo_systems`: `null` and empty. A GitHub username adds a count of that owner's repos to the GitHub node. `repo_systems` maps a repo, such as a knowledge base repo, to another system, so its triggers come from that system.
- `creation_status`: `false`, so a pale bot with a dashed outline is one whose **Default** is `no`. `true` reads **Created**, **Observed** and **Evidence** lines instead, adds a table of them, and makes a pale bot one that isn't created yet. Either way, a pale bot isn't live until someone acts.
- `title`, `intro` and `regenerate`: the page's title, the line under it, and the sentence after its "Generated by" note. `{script}`, `{time_zone}` and `{readme}`, a link to the README section, are filled in.
- `script`, `out` and `readme`: the script's path, the page it writes by default, and the README section the page links to, all from the repo root. The script finds the repo root from `script`.

Arrow and theme colours are `ARROW_STYLES`, `LIGHT` and `DARK` in `bot_chart.py`.

### Update the chart

After you change a bot file, run this from the repo root. Then commit `docs/bot-chart.md` and both schedule images with your change.

```sh
python3 scripts/bot_chart.py
```

`--bots <folder>` reads another folder, and `--out <file>` writes the page to another file, with its images beside it. The script needs Python 3.9 or newer, with `bot_chart.json` beside it, and nothing else. The same bot files always give the same files, byte for byte. If it can't read a bot file, it names the bot and the routine on stderr, exits with 1 and writes nothing.

The `Bot chart` workflow runs on every push and PR, and never writes to the repo. It fails when the script can't read a bot file. It only warns when the page or an image doesn't match `bots/`, so a bot change made on GitHub's website isn't blocked. Nothing regenerates the chart for you, because changes reach `main` only through a PR, as [decision 0002](../kb/bundle/decisions/0002-ci-decides-what-merges.md) says.

### How it reads a bot file

It reads the format in [bots/README.md](../bots/README.md), and skips `bots/README.md` itself.

- The bot's name is the first `#` heading. **Category** sets its colour, and a category outside the four in bots/README.md is grey. A bot whose **Default** is `no` is drawn as optional.
- Its instructions are the text block under `## Instructions`.
- Its routines are the `###` sections under `## Routines`. The script reads each one's **Schedule**, **Enabled** and **Trigger** fields above its text block, then the text block. A `group` trigger adds its cron schedules to the routine's schedule and its GitHub events to its triggers.
- A bot with no `## Routines` section, or one with no `###` headings, such as a section that only says "None.", has no routines.

It stops with an error when:

- a schedule isn't five numeric cron fields, such as `0 9 * * mon` or one with a `CRON_TZ=` prefix
- a cron sets both the day of the month and the day of the week, or has a step (`/`) outside the minute and hour
- **Enabled** isn't `true` or `false`, or a routine has no text block
- a trigger can't be read, or its type isn't `cron`, `github` or `group`
- a routine field comes before the first `###` heading under `## Routines`, or another `##` heading names routines, such as `## Paused routines`
- a bot file has no `## Instructions` section, or two files share a bot name

### How it finds the arrows

It reads only each bot's own file, one sentence at a time, in the instructions and every routine's text. Each arrow is labelled `instructions` or with the name of the routine that holds the sentence.

A bot hands off to another bot when a sentence has one of these:

- A hand-off verb right before the bot's name, as in "send scheduler one message" or "tell the owner and liaison". The verbs are send, tell, ask, hand, pass, forward, relay, message and report.
- A hand-off verb and, later in the sentence, "to" and the bot's name, as in "Send reports for the owner to liaison".
- "save" and, later in the sentence, "for" and the bot's name, as in "save them for librarian".
- `SendToAgent` and another bot's name. If the sentence names no other bot, the script uses the bots that the sentence before it names.

"each affected bot", "each changed bot", "that bot" and "the bot that owns it" all point to one node, `each affected bot`. fakkelbot and liaison send to whichever bot a change or a board thread touches, so the chart can't name them.

A bot uses an outside system when a sentence matches one of that system's patterns in `systems` in `bot_chart.json`. It lists GitHub, the knowledge base, the agent board, Gmail, Google Calendar, Claude Code, Cursor Agent and Codex CLI. To chart another app, add it there. A routine's GitHub trigger is a thick arrow from GitHub to its bot.

Three rules keep a mention from counting:

- A bot's name inside a path, repo or file name doesn't count, so `bots/inbox.md`, `bots/fakkelbot.md` and `dfakkeldy/fakkelbot` don't mention inbox or fakkelbot.
- A sentence in which a bot's name comes right before `=`, such as a map of which bot does what (`inbox = mail; scheduler = calendar`), is skipped.
- A name or pattern doesn't count when "never", "not", "no", "don't" or "without" is one of the three words before it in the same clause. A comma, a semicolon, a colon or a parenthesis ends a clause.

### Limits

The rules read words, not meaning. The script misses a hand-off phrased another way, and a name still counts when its "never" is more than three words before it. Names match in any case, so the product name FakkelBot in a bot's text counts as a mention of fakkelbot. If an arrow looks wrong, check the bot's sentences against the rules above.

## auto_merge.py

`auto_merge.py` decides whether a PR merges itself, and merges it. The [Auto-merge workflow](../.github/workflows/auto-merge.yml) runs it from `main` each time a check workflow finishes on a PR, so a PR can't change the rules that judge it. [Decision 0002](../kb/bundle/decisions/0002-ci-decides-what-merges.md) explains why.

It reads the PR through the GitHub API as data, and never checks out or runs the PR's code. It merges only when all of these hold:

- The PR is open and isn't a draft. It targets the default branch and comes from a branch in the same repo. It has no `hold` label and no merge conflict, and changes at most 300 files.
- Every changed path is low risk, as `PATH_RULES` says: notes and sources in `kb/` (not `kb/bundle/decisions/`, `kb/AGENTS.md`, `kb/tools/` or `kb/templates/`), `docs/`, `README.md`, and wording in `bots/*.md` other than `bots/fakkelbot.md`. A renamed file counts under both names.
- A bot file change adds no bot or routine, changes no trigger, turns no routine on, leaves its notification settings and sidebar default alone, and changes at most 40 lines. The file has no more words from `POWER_TERMS` than before, and no fewer phrases from `SAFETY_PHRASES`. A word doesn't count when "never", "not", "no", "don't", "without" or a similar word is one of the three words before it in the same clause.
- Every workflow in `REQUIRED_WORKFLOWS` that applies to the PR passed on its current head commit, with every job in it. A workflow with path filters applies only when the PR changes a path it watches. Any other workflow run on that commit, and any check from an app outside GitHub Actions, must not have failed.

It merges with `gh pr merge --squash --match-head-commit`, so GitHub refuses the merge if a newer commit arrived after the checks. A merge made with the workflow's own token starts no workflow on `main`. So when the merged result differs from the commit the checks tested, because `main` moved meanwhile, the script starts each required workflow on `main` itself.

Each Auto-merge run's summary says what happened: the PR merged, waits for the owner and why, waits for its checks, can't merge until something is fixed, or isn't checked here.

### Run it by hand

```sh
python3 scripts/auto_merge.py --repo <owner>/grok-bot-setup --pr 12 --dry-run
```

It uses your `gh` sign-in, and `--dry-run` merges nothing. To check a PR again on GitHub, run the Auto-merge workflow from the Actions tab with the PR's number.

### Change the rules

The rules are the constants at the top of the script. A PR that changes `scripts/` or `.github/` waits for the owner, so the rules can't loosen themselves. When you add a check workflow, add it to `REQUIRED_WORKFLOWS` and to the `workflows` list in `auto-merge.yml`, and give it a `workflow_dispatch` trigger. A test fails until all three match.

## Tests

```sh
python3 -m unittest discover -s scripts -v
```
