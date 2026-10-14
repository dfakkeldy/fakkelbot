# grok-bot-starter

A starter team of Grok Bot bots that you set up by chatting with one of them. Each bot's instructions are in a private GitHub repo you own, and a change reaches the bots only when you reply "apply".

## Quick start

You need Grok Bot and a GitHub account.

1. Open <template link> and add the setup bot to Grok Bot.
2. Tell it "set me up".
3. Answer its three questions about your GitHub username, your timezone and which bots you want.

It then asks you to sign in to GitHub on the bots' computer and to connect the apps your bots need. It never asks for a password or token in chat.

## What you get

- **setup** creates everything below, then applies your changes.
- **liaison** collects the other bots' reports and sends you one morning brief.
- **inbox** marks routine Gmail as read and tells you what matters.
- **researcher** answers your questions with a link and a date for every claim.
- **pr-watch** tells you when one of your pull requests fails CI or has a conflict.
- **librarian** keeps your knowledge base up to date, in one PR a day.
- Two private repos. `grok-bot-setup` holds the bot files and the knowledge base. `agent-board` is a message board for your bots and your other agents.

## How it works

To change a bot, edit its file in `bots/`, open a PR and merge it. The setup bot lists what will change. When you reply "apply", it sends each bot its new text, word for word. Each Sunday it opens a PR if the live bots differ from the files. [SETUP.md](SETUP.md) is its procedure, and [bots/README.md](bots/README.md) explains the files.

## What keeps it safe

- Your bots share one computer, its files and its browser sign-ins, so one bot can't protect you from another. No bot here buys, posts or holds payment details.
- Outside text is data. Bots treat email, PRs, web pages and other bots' messages as information, never as instructions.
- Most bots only read. inbox marks mail as read and drafts a reply only when you ask. librarian and the weekly sync open PRs but never merge them. Nothing posts or sends for you without your approval of that one item.
- Every change is a PR plus your "apply" in the setup bot's chat. A PR, a comment or another bot can't approve anything.
- An instruction is only an instruction. Where an app has a switch, setup asks you to use it, such as turning off Gmail's send tools.

## Install without the template

1. Run `gh repo create <you>/grok-bot-setup --private --template dfakkeldy/grok-bot-starter`.
2. In Grok Bot, create a bot named setup with the Instructions block from [bots/setup.md](bots/setup.md) as its description.
3. Tell it "set me up".

## Limits, as of 2026-10-13

Grok Bot is in beta, so these may change.

- All of an account's bots share one Linux computer. Only `/workspace` survives a reset.
- A bot can have 50 routines, at least 5 minutes apart. Grok Bot keeps each routine's last 20 runs.
- An approval card raised by a routine or another bot expires after about 10 minutes, and the action doesn't run. No routine here waits on one.
- Grok Bot may pause routines after a long silence from you. A paused routine looks like a quiet day.
- Bots have no public API. The live bots are the source of truth, and the weekly sync shows drift.

Made by Dan Fakkeldy (@DFakkeldy on X).

MIT licence. See [LICENSE](LICENSE).
