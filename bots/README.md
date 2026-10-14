# Bot files

Each file here holds one bot's exact instructions and routines. The setup bot creates the bots from these files and keeps them in step with the files.

## File format

- A `#` heading with the bot's name.
- Two lines for setup's menu:
  - **Category**, one of Daily life, Work, Builders or Content
  - **Default**, `yes` if setup picks the bot unless the owner drops it, or `no` if the owner has to ask for it
- A short note for people. Its first sentence also describes the bot in setup's menu. The bot never sees the note.
- `## Instructions`, holding one `text` code block. That block is the bot's standing instructions, word for word.
- `## Routines`, with a `###` section for each routine. Each has:
  - **Folder**, the routine's name in kebab case
  - **Schedule**, as cron in the owner's timezone, or `None` for a routine started by an event
  - **Enabled**, `true` or `false`
  - **Trigger**, only for an event routine, as JSON
  - one `text` code block with the routine's prompt, word for word

`<owner>` stands for the owner's GitHub username anywhere in a bot file. The setup bot fills it in when it creates or changes a bot, and writes `<owner>` back when it exports. Write `<owner>` only where the username goes, never in text about the placeholder, because setup would fill that in too.

## Change a bot

1. Edit the bot's file on a branch and open a PR.
2. Merge the PR.
3. The setup bot's `apply` routine sees the merge and sends you a short list of what will change. Nothing changes yet.
4. Reply "apply" in the setup bot's chat. It sends each bot its new text exactly, then checks what the bots now have.

Only your "apply" in that chat changes a bot. Every bot signs in to GitHub as you, so GitHub can't show which bot merged a PR. A PR, a comment or another bot's message never counts as approval.

Every Sunday evening the `weekly-sync` routine compares the live bots with these files. If they differ, it opens a `sync/export-YYYY-MM-DD` PR and closes any older sync PR that's still open, because the new one replaces it. Merging a sync PR changes no bot. It records what the bots already have. A bot that still has an earlier version of its file is listed as "not applied yet" and left out of the export, so merging the sync PR never undoes a change you haven't applied.

## Add a bot

The easiest way is to tell the setup bot what you want. It asks a few questions, writes the file the way this section says, and opens the PR for you to merge. To write one yourself:

1. Add `bots/<name>.md` in the format above. Its **Category** and **Default** lines put it in setup's menu. If it needs an app connected, add a line for it to step 6 of [SETUP.md](../SETUP.md).
2. Open a PR and merge it. When you reply "apply", the setup bot creates the bot and its routines.

Give a new bot one job. If it reads email, PRs, web pages or other bots' messages, say that text is data, never instructions. Say what it may do without asking and what needs you. Copy the Routing and Updates paragraphs from [inbox.md](inbox.md) word for word, changing only the file name in Updates. Keep the rule that nothing posts, replies or messages anyone but you without your approval of that one item. X's automation rules also forbid automated replies based on keyword searches.


Removing a file deletes no bot. Delete the bot yourself in Grok Bot if you want it gone.

## Share a bot as your own template

A Grok Bot template copies a bot's instructions, its routines, some plugins, and its relevant memories and skills. It copies no secrets, code or scripts (xAI's templates guide, 2026-09-08). Memories can hold personal details, so share a bot like this:

1. Create a fresh bot from its file here. Don't share one you've used for weeks.
2. Create the template from that fresh bot.
3. Add the template from a second Grok Bot account, and check what came across: instructions, routines, memories and skills.
4. Share the link only when nothing personal came with it. A bot whose file uses `<owner>` carries your GitHub username.
