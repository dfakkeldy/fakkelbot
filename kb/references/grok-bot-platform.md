---
type: reference
title: Grok Bot platform
description: How Grok Bot runs bots, routines, approvals and templates, and the limits every bot works within.
updated: 2026-10-14
---

# Grok Bot platform

Grok Bot is xAI's service for always-on bots. xAI's launch post of 2026-08-11 says Grok Bot is in beta, and Cursor's announcement the same day calls it an early beta ([launch post](https://x.ai/news/introducing-grok-bot); [Cursor forum](https://forum.cursor.com/t/introducing-grok-bot/168053)). As of 2026-10-14, no source used here says it has left beta. The computers the bots work on run in Cursor's cloud ([overview](https://docs.x.ai/grok-bot)).

Every fact below was checked against its source on 2026-10-14, unless the line gives another date. The platform changes often, so check the source before you rely on a detail.

## The shared computer

- All of an account's bots share one cloud computer. They share its browser sign-ins, files, command-line credentials and saved work ([computer and apps](https://docs.x.ai/grok-bot/computer-and-apps)).
- The docs say team computers run Linux, with `sudo` available ([private networks](https://docs.x.ai/grok-bot/private-networks)).
- Each bot gets its own screen. The docs call the screens separate work surfaces, not security boundaries. Don't put a sign-in or a file on the computer if another bot shouldn't use it ([computer and apps](https://docs.x.ai/grok-bot/computer-and-apps)).
- Keep durable files in `/workspace`. Temporary folders, packages you install by hand and uncommitted app state can be lost ([computer and apps](https://docs.x.ai/grok-bot/computer-and-apps)).
- Settings > Computer has Update, which keeps your files, and Reset, which rebuilds the computer from the last saved snapshot and can lose recent changes ([computer and apps](https://docs.x.ai/grok-bot/computer-and-apps)).
- Work keeps running when you close the app, your laptop or your phone ([overview](https://docs.x.ai/grok-bot)).

## Bots

- A bot's description holds the rules that stay true across tasks. Instructions for one task go in the chat ([bots](https://docs.x.ai/grok-bot/bots)).
- The docs advise a separate bot when the work has its own goal, tools, working style, approval boundary or schedule. They also advise starting with the smallest roster that works ([bots](https://docs.x.ai/grok-bot/bots)).
- Hiding a bot doesn't pause it or its routines. Deleting a bot removes its profile, conversation and routines. Duplicating a bot copies its profile, settings, enabled skills, routines and avatar, but not its conversation history or learned memory ([bots](https://docs.x.ai/grok-bot/bots)).
- The docs say memory is not a substitute for an authoritative source. Keep facts that change in a source the bot can reopen ([bots](https://docs.x.ai/grok-bot/bots)).
- Bots can message each other, share context in group chats and pass a task to another bot ([overview](https://docs.x.ai/grok-bot)).
- As of 2026-10-13, a bot's tools include `CreateAgent`, which creates a bot, and `SendToAgent`, which sends a message to another bot. These names are unverified. The public docs don't name them. The public `grok-build` source defines bot tools under other names, including `bot_create_agent` and `bot_send_prompt`, and says a bot created that way can't be deleted through the tool ([bot_tools.rs](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/common/xai-computer-hub-core/src/bot_tools.rs)).
- Cursor chooses the model. There is no model picker ([settings](https://docs.x.ai/grok-bot/settings-and-notifications)).

## Routines

- A routine runs a bot's workflow on a schedule or after an event ([routines](https://docs.x.ai/grok-bot/skills-routines-and-automations)).
- A bot can own at most 50 routines. Schedules must be at least five minutes apart. The app keeps the 20 most recent run records for each routine ([routines](https://docs.x.ai/grok-bot/skills-routines-and-automations)).
- A Test run does real work. It can browse, change files and call connected tools ([routines](https://docs.x.ai/grok-bot/skills-routines-and-automations)).
- Deleting a routine takes effect at once and can't be undone ([routines](https://docs.x.ai/grok-bot/skills-routines-and-automations)).
- After a long time with no reply from you, Grok Bot may ask whether to keep routines running. If you don't answer, it pauses them. The docs don't say how long that takes ([routines](https://docs.x.ai/grok-bot/skills-routines-and-automations)).
- Settings > General > Bot > Timezone sets the time zone that every routine's schedule uses ([settings](https://docs.x.ai/grok-bot/settings-and-notifications)).
- The docs write schedules in plain language, such as "every weekday at 8:00 AM", and document no cron syntax ([routines](https://docs.x.ai/grok-bot/skills-routines-and-automations)).
- A new routine waits for its next scheduled time. Use Test to run it now ([Cursor help](https://cursor.com/help/grok-bot/routines)).
- Each run uses part of your plan's usage. Cursor warns that an hourly schedule, a short interval or a trigger on a busy Slack channel can use a week of usage in a day ([Cursor help](https://cursor.com/help/grok-bot/routines)).
- From 2026-09-02, users reported routines that started 10 to 37 minutes late or not at all. Cursor staff announced a queuing fix on 2026-09-16, and users still reported delays after it ([Cursor forum](https://forum.cursor.com/t/grok-bot-routines-dont-auto-run-on-schedule/170358)). Write routines so a late or missed run does no harm.

## Approvals

- An approval card offers Allow once, Always allow and Deny ([approvals and security](https://docs.x.ai/grok-bot/approvals-security-and-privacy)).
- An approval in a chat you're in waits for your answer. An approval raised by a routine, a trigger or another bot expires after about 10 minutes, and the action doesn't run. If you then choose to always allow it, the rule is saved, but you have to ask the bot to try again ([approvals and security](https://docs.x.ai/grok-bot/approvals-security-and-privacy)). So a routine never waits on an approval. It drafts, reports or opens a pull request, and leaves the action to you.
- The docs advise approval before sending, buying, deleting, publishing or changing production systems ([routines](https://docs.x.ai/grok-bot/skills-routines-and-automations)).
- Never send a password or a one-time code in an ordinary chat. For a sign-in, the bot hands you control of the computer. Some connections offer a secure secret request that hides the value from the model ([approvals and security](https://docs.x.ai/grok-bot/approvals-security-and-privacy)).

## Templates

- You make a template from a bot's Share menu with Create template. It gives you a public or team-only link ([bots](https://docs.x.ai/grok-bot/bots)).
- Whoever adds the template gets a copy of the bot's configuration on their own account. They don't get your computer, sign-ins or conversation history ([bots](https://docs.x.ai/grok-bot/bots)).
- Remove API keys, internal URLs and customer data before you share a template, because a public link shows its configuration ([bots](https://docs.x.ai/grok-bot/bots)).
- xAI's templates guide, dated 2026-09-08, says a template carries the bot's instructions, relevant memories, skills, certain plugins and its routines. It leaves out secrets, custom code, scripts, private skills and non-standard plugins such as MCP servers ([templates guide](https://x.ai/bot/guides/templates-for-grok-bot)). That's why this starter kit keeps its code in a repository, which the setup bot fetches after you add the template.

## Connectors and X

- A connector is installed once, and every bot on the account can use it ([computer and apps](https://docs.x.ai/grok-bot/computer-and-apps)).
- Without a connected X account, bots can search and read public X content only. The X plugin adds DMs, bookmarks, the home timeline and likes ([computer and apps](https://docs.x.ai/grok-bot/computer-and-apps)).
- X's developer guidelines don't allow an app that auto-replies to anyone who mentions a keyword. AI-generated replies need X's approval before deployment. Automated accounts must turn on the "Automated" profile label and honor opt-out requests at once ([X developer guidelines](https://docs.x.com/developer-guidelines)). So no starter bot posts, replies or sends a message to anyone but its owner without the owner's approval for that item.

## Sources

The docs.x.ai and docs.x.com pages show no date. Each source was checked on 2026-10-14.

- [Introducing Grok Bot](https://x.ai/news/introducing-grok-bot), xAI, 2026-08-11.
- [Introducing Grok Bot](https://forum.cursor.com/t/introducing-grok-bot/168053), Cursor forum, 2026-08-11.
- [Grok Bot overview](https://docs.x.ai/grok-bot), xAI docs.
- [Bots](https://docs.x.ai/grok-bot/bots), xAI docs.
- [Skills, routines and automations](https://docs.x.ai/grok-bot/skills-routines-and-automations), xAI docs.
- [Computer and apps](https://docs.x.ai/grok-bot/computer-and-apps), xAI docs.
- [Approvals, security and privacy](https://docs.x.ai/grok-bot/approvals-security-and-privacy), xAI docs.
- [Settings and notifications](https://docs.x.ai/grok-bot/settings-and-notifications), xAI docs.
- [Private networks](https://docs.x.ai/grok-bot/private-networks), xAI docs.
- [Grok Bot routines](https://cursor.com/help/grok-bot/routines), Cursor help.
- [Grok Bot routines don't auto run on schedule](https://forum.cursor.com/t/grok-bot-routines-dont-auto-run-on-schedule/170358), Cursor forum thread started 2026-09-02.
- [Templates for Grok Bot](https://x.ai/bot/guides/templates-for-grok-bot), xAI guide, 2026-09-08.
- [bot_tools.rs](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/common/xai-computer-hub-core/src/bot_tools.rs) in `xai-org/grok-build`, at commit `2bdd1d6`.
- [Developer guidelines](https://docs.x.com/developer-guidelines), X.
