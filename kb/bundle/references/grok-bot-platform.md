---
type: Reference
title: Grok Bot platform
description: How Grok Bot runs bots, routines, approvals and templates, and the limits every bot works within.
resource: https://docs.x.ai/grok-bot
tags: [grok-bot, platform]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-10-16T09:18:16-03:00 }
sources:
  - id: launch-post
    resource: https://x.ai/news/introducing-grok-bot
    title: "Introducing Grok Bot"
    author: team:xai
    checked: 2026-10-14
  - id: cursor-launch
    resource: https://forum.cursor.com/t/introducing-grok-bot/168053
    title: "Introducing Grok Bot"
    author: team:cursor
    checked: 2026-10-14
  - id: overview
    resource: https://docs.x.ai/grok-bot
    title: "Grok Bot overview"
    author: team:xai
    checked: 2026-10-14
  - id: bots
    resource: https://docs.x.ai/grok-bot/bots
    title: "Bots"
    author: team:xai
    checked: 2026-10-14
  - id: routines
    resource: https://docs.x.ai/grok-bot/skills-routines-and-automations
    title: "Skills, routines and automations"
    author: team:xai
    checked: 2026-10-14
  - id: computer-and-apps
    resource: https://docs.x.ai/grok-bot/computer-and-apps
    title: "Computer and apps"
    author: team:xai
    checked: 2026-10-14
  - id: approvals-and-security
    resource: https://docs.x.ai/grok-bot/approvals-security-and-privacy
    title: "Approvals, security and privacy"
    author: team:xai
    checked: 2026-10-14
  - id: settings
    resource: https://docs.x.ai/grok-bot/settings-and-notifications
    title: "Settings and notifications"
    author: team:xai
    checked: 2026-10-14
  - id: private-networks
    resource: https://docs.x.ai/grok-bot/private-networks
    title: "Private networks"
    author: team:xai
    checked: 2026-10-14
  - id: cursor-routines-help
    resource: https://cursor.com/help/grok-bot/routines
    title: "Grok Bot routines"
    author: team:cursor
    checked: 2026-10-14
  - id: routine-delays-thread
    resource: https://forum.cursor.com/t/grok-bot-routines-dont-auto-run-on-schedule/170358
    title: "Grok Bot routines don't auto run on schedule"
    checked: 2026-10-14
  - id: templates-guide
    resource: https://x.ai/bot/guides/templates-for-grok-bot
    title: "Templates for Grok Bot"
    author: team:xai
    checked: 2026-10-14
  - id: bot-tools
    resource: https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/common/xai-computer-hub-core/src/bot_tools.rs
    title: "bot_tools.rs in xai-org/grok-build at commit 2bdd1d6"
    author: team:xai
    checked: 2026-10-14
  - id: x-developer-guidelines
    resource: https://docs.x.com/developer-guidelines
    title: "Developer guidelines"
    author: team:x
    checked: 2026-10-14
---

# Grok Bot platform

Grok Bot is xAI's service for always-on bots. xAI's launch post of 2026-08-11 says Grok Bot is in beta, and Cursor's announcement the same day calls it an early beta[^launch-post][^cursor-launch]. As of 2026-10-14, no source used here says it has left beta. The computers the bots work on run in Cursor's cloud[^overview].

Every fact below was checked against its source on 2026-10-14, unless the line gives another date. The docs.x.ai and docs.x.com pages show no date. The platform changes often, so check the source before you rely on a detail.

## The shared computer

- All of an account's bots share one cloud computer. They share its browser sign-ins, files, command-line credentials and saved work[^computer-and-apps].
- The docs say team computers run Linux, with `sudo` available[^private-networks].
- Each bot gets its own screen. The docs call the screens separate work surfaces, not security boundaries. Don't put a sign-in or a file on the computer if another bot shouldn't use it[^computer-and-apps].
- Keep durable files in `/workspace`. Temporary folders, packages you install by hand and uncommitted app state can be lost[^computer-and-apps].
- Settings > Computer has Update, which keeps your files, and Reset, which rebuilds the computer from the last saved snapshot and can lose recent changes[^computer-and-apps].
- Work keeps running when you close the app, your laptop or your phone[^overview].

## Your own computer

- Bots can also work on the Mac or Windows computer in front of you. That's a separate capability from the cloud computer[^approvals-and-security].
- Settings > General > Bot > Execution on Local Computer offers Ask every time, Always allow and Never allow. Ask every time is the default. Answering Always allow or Never at the first prompt sets it for every bot[^approvals-and-security].
- Once the account has registered computers, the choice moves to Settings > Computer > Computers, with one setting for each computer[^approvals-and-security].
- The docs advise Never allow unless a bot has a specific reason to work on your local files. A team admin can cap the setting. It doesn't stop bots from using the cloud computer[^approvals-and-security].
- As of 2026-10-14, the docs don't explain how to register a computer[^approvals-and-security].

## Bots

- A bot's description holds the rules that stay true across tasks. Instructions for one task go in the chat[^bots].
- The docs advise a separate bot when the work has its own goal, tools, working style, approval boundary or schedule. They also advise starting with the smallest roster that works[^bots].
- Hiding a bot doesn't pause it or its routines. Deleting a bot removes its profile, conversation and routines. Duplicating a bot copies its profile, settings, enabled skills, routines and avatar, but not its conversation history or learned memory[^bots].
- The docs say memory is not a substitute for an authoritative source. Keep facts that change in a source the bot can reopen[^bots].
- Bots can message each other, share context in group chats and pass a task to another bot[^overview].
- As of 2026-10-13, a bot's tools include `CreateAgent`, which creates a bot, and `SendToAgent`, which sends a message to another bot. These names are unverified. The public docs don't name them. The public `grok-build` source defines bot tools under other names, including `bot_create_agent` and `bot_send_prompt`, and says a bot created that way can't be deleted through the tool[^bot-tools].
- Cursor chooses the model. There is no model picker[^settings].

## Routines

- A routine runs a bot's workflow on a schedule or after an event[^routines].
- A bot can own at most 50 routines. Schedules must be at least five minutes apart. The app keeps the 20 most recent run records for each routine[^routines].
- A Test run does real work. It can browse, change files and call connected tools[^routines].
- Deleting a routine takes effect at once and can't be undone[^routines].
- After a long time with no reply from you, Grok Bot may ask whether to keep routines running. If you don't answer, it pauses them. The docs don't say how long that takes[^routines].
- Settings > General > Bot > Timezone sets the time zone that every routine's schedule uses[^settings].
- The docs write schedules in plain language, such as "every weekday at 8:00 AM", and document no cron syntax[^routines].
- A new routine waits for its next scheduled time. Use Test to run it now[^cursor-routines-help].
- Each run uses part of your plan's usage. Cursor warns that an hourly schedule, a short interval or a trigger on a busy Slack channel can use a week of usage in a day[^cursor-routines-help].
- From 2026-09-02, users reported routines that started 10 to 37 minutes late or not at all. Cursor staff announced a queuing fix on 2026-09-16, and users still reported delays after it[^routine-delays-thread]. Write routines so a late or missed run does no harm.

## Approvals

- An approval card offers Allow once, Always allow and Deny[^approvals-and-security].
- An approval in a chat you're in waits for your answer. An approval raised by a routine, a trigger or another bot expires after about 10 minutes, and the action doesn't run. If you then choose to always allow it, the rule is saved, but you have to ask the bot to try again[^approvals-and-security]. So a routine never waits on an approval. It drafts, reports or opens a pull request, and leaves the action to you.
- The docs advise approval before sending, buying, deleting, publishing or changing production systems[^routines].
- Never send a password or a one-time code in an ordinary chat. For a sign-in, the bot hands you control of the computer. Some connections offer a secure secret request that hides the value from the model[^approvals-and-security].

## Templates

- You make a template from a bot's Share menu with Create template. It gives you a public or team-only link[^bots].
- Whoever adds the template gets a copy of the bot's configuration on their own account. They don't get your computer, sign-ins or conversation history[^bots].
- Remove API keys, internal URLs and customer data before you share a template, because a public link shows its configuration[^bots].
- xAI's templates guide, dated 2026-09-08, says a template carries the bot's instructions, relevant memories, skills, certain plugins and its routines. It leaves out secrets, custom code, scripts, private skills and non-standard plugins such as MCP servers[^templates-guide]. That's why this starter kit keeps its code in a repository, which fakkelbot fetches after you add the template.

## Connectors and X

- A connector is installed once, and every bot on the account can use it[^computer-and-apps].
- Without a connected X account, bots can search and read public X content only. The X plugin adds DMs, bookmarks, the home timeline and likes[^computer-and-apps].
- X's developer guidelines don't allow an app that auto-replies to anyone who mentions a keyword. AI-generated replies need X's approval before deployment. Automated accounts must turn on the "Automated" profile label and honor opt-out requests at once[^x-developer-guidelines]. So no starter bot posts, replies or sends a message to anyone but its owner without the owner's approval for that item.

[^launch-post]: [Introducing Grok Bot](https://x.ai/news/introducing-grok-bot), xAI, 2026-08-11.
[^cursor-launch]: [Introducing Grok Bot](https://forum.cursor.com/t/introducing-grok-bot/168053), Cursor forum, 2026-08-11.
[^overview]: [Grok Bot overview](https://docs.x.ai/grok-bot), xAI docs.
[^bots]: [Bots](https://docs.x.ai/grok-bot/bots), xAI docs.
[^routines]: [Skills, routines and automations](https://docs.x.ai/grok-bot/skills-routines-and-automations), xAI docs.
[^computer-and-apps]: [Computer and apps](https://docs.x.ai/grok-bot/computer-and-apps), xAI docs.
[^approvals-and-security]: [Approvals, security and privacy](https://docs.x.ai/grok-bot/approvals-security-and-privacy), xAI docs.
[^settings]: [Settings and notifications](https://docs.x.ai/grok-bot/settings-and-notifications), xAI docs.
[^private-networks]: [Private networks](https://docs.x.ai/grok-bot/private-networks), xAI docs.
[^cursor-routines-help]: [Grok Bot routines](https://cursor.com/help/grok-bot/routines), Cursor help.
[^routine-delays-thread]: [Grok Bot routines don't auto run on schedule](https://forum.cursor.com/t/grok-bot-routines-dont-auto-run-on-schedule/170358), Cursor forum thread started 2026-09-02.
[^templates-guide]: [Templates for Grok Bot](https://x.ai/bot/guides/templates-for-grok-bot), xAI guide, 2026-09-08.
[^bot-tools]: [bot_tools.rs](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/common/xai-computer-hub-core/src/bot_tools.rs) in `xai-org/grok-build`, at commit `2bdd1d6`.
[^x-developer-guidelines]: [Developer guidelines](https://docs.x.com/developer-guidelines), X.
