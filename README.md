# grok-bot-starter

A starter team of Grok Bot bots that you set up by chatting with one of them. Each bot's instructions are in a private GitHub repo you own.

## Quick start

You need Grok Bot and a GitHub account.

1. Open <template link> and add the setup bot to Grok Bot.
2. Tell it "set me up".
3. Answer its three questions about your GitHub username, your timezone and which bots you want.

It then helps you sign in to GitHub and connect your apps. It never asks for a password or token in chat.

Setup also offers to add board instructions to your `CLAUDE.md` and `AGENTS.md`, so coding agents outside Grok can coordinate with your bots. You choose the files and review the diff, or skip. [Instruction-file setup](docs/agent-instructions-setup.md) explains the choices.

## What you get

- **setup** creates everything below, then designs new bots with you and applies your changes.
- **liaison** sends you one morning brief built from the other bots' reports.
- **inbox** marks Gmail as read, labels what needs you and tells you what matters.
- **researcher** answers your questions with a link and a date for every claim.
- **pr-watch** reports failed checks and conflicts on your PRs, and `grok-bot-setup` PRs that have waited on you for more than a day.
- **librarian** keeps your knowledge base up to date, in one PR a day.
- Two private repos. `grok-bot-setup` holds the bot files and the knowledge base. `agent-board` carries messages between your bots and your other agents.

You can also add these:

- **scheduler** reads your Google Calendar, tells you what you can't miss and suggests when to fit in flexible things.
- **jobscout** finds open jobs, contracts and grants that fit you, and reminds you before their deadlines.
- **pantry** keeps your shopping list and tells you about real deals on what you buy.
- **editor** suggests posts about what you shipped and drafts the ones you pick.
- **clerk** finds and files the files on your own computer when you ask. It logs every move so you can undo it, and never deletes anything.
- **Coding group** adds **claude**, **cursor** and **codex**, which operate Claude Code, Cursor Agent and Codex CLI. Each handles assigned tasks and can review another tool's work. Choose all three or any subset. They have no routines, and setup checks each selected CLI and sign-in. [Coding setup and computer choices](docs/coding-group.md) explains how they use Grok's computer or an approved local computer.

## How it works

You change a bot by merging a PR that edits its file and replying "apply" to the setup bot, as [bots/README.md](bots/README.md) explains.

The [bot chart](docs/bot-chart.md) shows which bots hand work to which, and when each routine runs.

## What keeps it safe

- Your bots share one computer, its files and its sign-ins, so one bot can't protect you from another.
- Bots treat email, PRs, web pages and other bots' messages as data, never as instructions.
- Most bots only read. librarian and the weekly sync open PRs but never merge them. Coding members can change code and open task PRs; they merge or deploy only under your explicit delivery rules. No bot buys anything, and nothing posts or sends for you without your approval of that one item. scheduler adds a calendar event only after you say yes to that one suggestion.
- Only your "apply" in the setup bot's chat changes a bot. A PR, a comment or another bot's message never counts.
- clerk and the Coding group can work on your connected computer. Coding remembers your choice per project and defaults to Grok's computer for Linux work. Local commands follow that computer's existing approval setting. Always allow lets every bot in; setup never enables it.
- A rule in a bot's instructions isn't enforced. Where an app has a switch, setup asks you to use it, such as turning off Gmail's send tools.

## Install without the template

1. Run `gh repo create <you>/grok-bot-setup --private --template dfakkeldy/grok-bot-starter`.
2. In Grok Bot, create a bot named setup with the Instructions block from [bots/setup.md](bots/setup.md) as its description.
3. Tell it "set me up".

## Limits, as of 2026-10-14

Grok Bot is in beta, so these may change. [kb/references/grok-bot-platform.md](kb/references/grok-bot-platform.md) has the sources.

- Only `/workspace` on the bots' shared Linux computer survives a restart.
- An approval card raised by a routine or another bot expires after about 10 minutes. No routine here waits on one.
- Grok Bot may pause routines after a long silence from you. A paused routine looks like a quiet day.

Made by Dan Fakkeldy (@DFakkeldy on X).

MIT licence. See [LICENSE](LICENSE).
