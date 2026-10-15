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
4. Reply "apply" in the setup bot's chat. It sends each bot its new text exactly, then checks what the changed bots now have. Its report has four groups: what bots said they applied, what its check confirmed, confirmed mismatches, and what it couldn't read. A match shows the text is in place, not that a routine works. The routine's next real run shows that.

Only your "apply" in that chat changes a bot. Every bot signs in to GitHub as you, so GitHub can't show which bot merged a PR. A PR, a comment or another bot's message never counts as approval.

Every Sunday evening the `weekly-sync` routine compares the live bots with these files. If they differ, it opens a `sync/export-YYYY-MM-DD` PR and closes any older sync PR that's still open, because the new one replaces it. Merging a sync PR changes no bot. It records what the bots already have. A bot that still has an earlier version of its file is listed as "not applied yet" and left out of the export, so merging the sync PR never undoes a change you haven't applied.

`weekly-sync` also looks for missing runs: a routine with no run when one was due, a run marked succeeded that left no output, and a routine that's paused. It tells you what it couldn't check, and never says everything matches when it couldn't check it all.

### Test the apply loop (optional)

To see the whole loop work before you rely on it, make a change that does nothing.

1. Pick a bot, and add one sentence to the end of its instructions that changes nothing it does, such as "Your instructions and routines are kept in the owner's grok-bot-setup repo." Open a PR and merge it.
2. Within a few minutes, the setup bot should send you the PR, a line such as "pantry: one sentence added to its instructions", and a request to reply "apply" or "skip". Nothing should have changed yet.
3. Reply "apply". Watch the bot's chat. It should get the sentence from the setup bot and replace its instructions.
4. The test passes when nothing changed before your "apply", the bot's instructions in its settings end with the new sentence, the setup bot's report lists the change as confirmed, and no approval card expired unanswered. You can leave the sentence in, or remove it the same way.

If it fails:

- **The setup bot never messages you.** Check that its `apply` routine exists, that its trigger is `pr-merged` on your grok-bot-setup repo, and that the GitHub integration can see that repo. Then check the routine's run history.
- **An approval card appears in the bot's chat.** Approve it there. A card raised by another bot expires after about 10 minutes and the change isn't saved, so stay nearby while an apply runs. If it expired, reply "apply" again.
- **The bot refuses a change another bot relays.** Paste the new text into the bot's settings yourself. Then weekly-sync shows whether it matches.
- **The report says a field couldn't be read.** Check the bot's settings yourself. A bot's reply alone doesn't show the change was saved.

## Add a bot

The easiest way is to tell the setup bot what you want. It asks a few questions, writes the file the way this section says, and opens the PR for you to merge. To write one yourself:

1. Add `bots/<name>.md` in the format above. Its **Category** and **Default** lines put it in setup's menu. If it needs an app connected, add a line for it to step 6 of [SETUP.md](../SETUP.md).
2. Open a PR and merge it. When you reply "apply", the setup bot creates the bot and its routines.

Give a new bot one job, and name its anti-jobs: the nearby work it leaves to other bots or to you. Give it only the tools and connectors that job needs, and turn off any left over. If it reads email, PRs, web pages or other bots' messages, say that text is data, never instructions. Say what it may do without asking and what needs you. Copy the Routing and Updates paragraphs from [inbox.md](inbox.md) word for word, changing only the file name in Updates. Keep the rule that nothing posts, replies or messages anyone but you without your approval of that one item. X's automation rules also forbid automated replies based on keyword searches.

### Optional Coding group

[claude.md](claude.md), [cursor.md](cursor.md) and [codex.md](codex.md) are optional Builders, each with no routines. Their job is the same; each operates its named coding CLI. [groups/coding.md](../groups/coding.md) describes the group, member choices and kickoff. Its message explains rules already in the member files; it is not a separate live bot configuration.

Setup offers Coding as one optional group, or any subset, and follows [Coding setup](../docs/coding-group.md#setup) for CLI readiness, the default worker and computer choices. Adding the files or creating a bot does not install a CLI, transfer sign-ins or prove the bot can use a local computer. When adding a member later, setup performs the same checks during "apply". A group needs at least two chosen members; one works in its own chat.


Removing a file deletes no bot. Delete the bot yourself in Grok Bot if you want it gone.

## Share a bot as your own template

A Grok Bot template copies a bot's instructions, its routines, some plugins, and its relevant memories and skills. It copies no secrets, code or scripts (xAI's templates guide, 2026-09-08). Memories can hold personal details, so share a bot like this:

1. Create a fresh bot from its file here. Don't share one you've used for weeks.
2. Create the template from that fresh bot.
3. Add the template from a second Grok Bot account, and check what came across: instructions, routines, memories and skills.
4. Share the link only when nothing personal came with it. A bot whose file uses `<owner>` carries your GitHub username.
