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

`bot_chart.py` reads every bot file in `bots/` and writes [the bot chart](../docs/bot-chart.md), `docs/bot-chart.md`. The page shows which bots hand work to which, what wakes each bot, which outside systems each bot uses, and when the scheduled routines run. GitHub draws its Mermaid charts.

### Update the chart

After you change a bot file, run this from the repo root and commit `docs/bot-chart.md` with your change.

```sh
python3 scripts/bot_chart.py
```

`--bots <folder>` reads another folder, and `--out <file>` writes another file. The script needs Python 3.9 or newer and nothing else. The same bot files always give the same page, byte for byte. If it can't read a bot file, it names the bot and the routine on stderr, exits with 1 and writes nothing.

The `Bot chart` workflow runs on every push and PR, and never writes to the repo. It fails when the script can't read a bot file. It only warns when `docs/bot-chart.md` doesn't match `bots/`, so a bot change made on GitHub's website isn't blocked. Nothing regenerates the chart for you, because changes reach `main` only through a PR, as [decision 0001](../kb/decisions/0001-every-change-goes-through-a-pr.md) says.

### How it reads a bot file

It reads the format in [bots/README.md](../bots/README.md), and skips `bots/README.md` itself.

- The bot's name is the first `#` heading. A bot whose **Default** is `no` gets a dashed border and "(optional)".
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

"each affected bot", "each changed bot" and "that bot" all point to one node, `each affected bot`. setup and liaison send to whichever bot a change or a board thread touches, so the chart can't name them.

A bot uses an outside system when a sentence matches one of that system's patterns in the `SYSTEMS` table in `bot_chart.py`. The table has GitHub, the knowledge base, the agent board, Gmail and Google Calendar. To chart another app, add a line to the table. A routine's GitHub trigger is a thick arrow from GitHub to its bot.

Two rules keep a mention from counting:

- A bot's name inside a path, repo or file name doesn't count, so `grok-bot-setup`, `bots/inbox.md` and `SETUP.md` don't mention setup or inbox.
- A name or pattern doesn't count when "never", "not", "no", "don't" or "without" is one of the three words before it in the same clause. A comma, a semicolon, a colon or a parenthesis ends a clause.

### Limits

The rules read words, not meaning. The script misses a hand-off phrased another way, and a name still counts when its "never" is more than three words before it. If an arrow looks wrong, check the bot's sentences against the rules above.

## Tests

```sh
python3 -m unittest discover -s scripts -v
```
