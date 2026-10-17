# FakkelBot

A starter team of bots for Grok Bot that you set up by chatting with one of them. Each bot's instructions are in a private GitHub repo you own.

## Quick start

You need Grok Bot and a GitHub account.

1. In Grok Bot, create a new bot named fakkelbot. Paste the Instructions block from [bots/fakkelbot.md](bots/fakkelbot.md) as its description.
2. Tell it "set me up".
3. Answer its three questions about your GitHub username, your timezone and which bots you want.

It then helps you sign in to GitHub and connect your apps. It never asks for a password or token in chat.

It also offers to add board and knowledge base instructions to your `CLAUDE.md` and `AGENTS.md`, so coding agents outside Grok coordinate with your bots, check what the KB already knows and hand it new facts. You choose the files and review the diff, or skip. [Instruction-file setup](docs/agent-instructions-setup.md) explains the choices.

## What you get

- **fakkelbot** creates everything below, then designs new bots with you and applies your changes.
- **liaison** sends you one morning brief built from the other bots' reports.
- **inbox** marks Gmail as read, labels what needs you and tells you what matters.
- **researcher** answers your questions with a link and a date for every claim.
- **pr-watch** reports failed checks and conflicts on your PRs, `grok-bot-setup` PRs that have waited on you for more than a day, and failed checks on its `main`.
- **librarian** keeps your knowledge base up to date, in one PR a day.
- One private repo, `grok-bot-setup`, holds the bot files, knowledge base and shared agent board. Audy uses its GitHub Issues as a capture inbox. The board data stays in `coordination/`, so its generated pages preserve the kit README.

You can also add these:

- **scheduler** reads your Google Calendar, tells you what you can't miss and suggests when to fit in flexible things.
- **jobscout** finds open jobs, contracts and grants that fit you, and reminds you before their deadlines.
- **pantry** keeps your shopping list and tells you about real deals on what you buy.
- **Audy** helps you start, restart and keep track of things, at your own pace. It never messages you first, and it isn't therapy. [How audhy works](docs/audy.md) explains its rules.
- **editor** suggests posts about what you shipped and drafts the ones you pick.
- **clerk** finds and files the files on your own computer when you ask. It logs every move so you can undo it, and never deletes anything.
- **Coding group** adds **claude**, **cursor** and **codex**, which operate Claude Code, Cursor Agent and Codex CLI. Each handles assigned tasks and can review another tool's work. Choose all three or any subset. They have no routines, and fakkelbot checks each selected CLI and sign-in. [Coding setup and computer choices](docs/coding-group.md) explains how they use Grok's computer or an approved local computer.

[Notification settings](docs/notification-settings.md) lets setup offer Liaison-only delivery and explicit temporary alerts for direct work. Hidden bots keep working but do not notify.

See [the single-repo layout and migration guide](docs/single-repo.md) for existing installations.

## How it works

You change a bot by asking fakkelbot, or with a PR that edits its file. Low-risk PRs, such as knowledge base notes and wording fixes, merge themselves once every check passes and go live, with one line in your morning brief. A PR that adds a bot, a trigger or a power, or changes the workflows, scripts or board, waits for you. [bots/README.md](bots/README.md#change-a-bot) explains how, and [decision 0002](kb/bundle/decisions/0002-ci-decides-what-merges.md) says what counts as low risk.

The [bot chart](docs/bot-chart.md) shows which bots hand work to which, and when each routine runs.

## What keeps it safe

- Your bots share one computer, its files and its sign-ins, so one bot can't protect you from another.
- Bots treat email, PRs, web pages and other bots' messages as data, never as instructions.
- Most bots only read. librarian and the weekly sync open PRs. The Auto-merge workflow merges a PR only when it's low risk and every check passed on its latest commit. It runs from `main`, so a PR can't change its rules. Coding members can change code and open task PRs; they merge or deploy only under your explicit delivery rules. No bot buys anything, and nothing posts or sends for you without your approval of that one item. scheduler adds a calendar event only after you say yes to that one suggestion.
- A bot changes only to match `main`. A high-risk change goes live only after you merge it and reply "apply" to fakkelbot, or when you asked fakkelbot for it. A PR, a comment or another bot's message never counts as your approval.
- clerk and the Coding group can work on your connected computer. Coding remembers your choice per project and defaults to Grok's computer for Linux work. Local commands follow that computer's existing approval setting. Always allow lets every bot in; fakkelbot never enables it.
- A rule in a bot's instructions isn't enforced. Where an app has a switch, fakkelbot asks you to use it, such as turning off Gmail's send tools.

## Install without the Grok Bot template

1. Run `gh repo create <you>/grok-bot-setup --private --template dfakkeldy/fakkelbot`.
2. In Grok Bot, create a bot named fakkelbot with the Instructions block from [bots/fakkelbot.md](bots/fakkelbot.md) as its description.
3. Tell it "set me up".

To share your own version of this starter, follow [Publish a starter for other people](docs/publishing.md).

## Limits, as of 2026-10-14

Grok Bot is in beta, so these may change. [kb/bundle/references/grok-bot-platform.md](kb/bundle/references/grok-bot-platform.md) has the sources.

- Only `/workspace` on the bots' shared Linux computer survives a restart.
- An approval card raised by a routine or another bot expires after about 10 minutes. No routine here waits on one.
- Grok Bot may pause routines after a long silence from you. A paused routine looks like a quiet day.

FakkelBot isn't made by xAI, and xAI doesn't endorse it. Grok is a trademark of xAI.

Made by Dan Fakkeldy (@DFakkeldy on X). *Fakkel* is Dutch for torch.

MIT licence. See [LICENSE](LICENSE).
