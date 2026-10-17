# Bot files

Each file here holds one bot's exact instructions and routines. fakkelbot creates the bots from these files and keeps them in step with the files.

## File format

- A `#` heading with the bot's name.
- Two lines for fakkelbot's menu:
  - **Category**, one of Daily life, Work, Builders or Content
  - **Default**, `yes` if fakkelbot picks the bot unless the owner drops it, or `no` if the owner has to ask for it
- A short note for people. Its first sentence also describes the bot in fakkelbot's menu. The bot never sees the note.
- `## Instructions`, holding one `text` code block. That block is the bot's standing instructions, word for word.
- `## Routines`, with a `###` section for each routine. Each has:
  - **Folder**, the routine's name in kebab case
  - **Schedule**, as cron in the owner's timezone, or `None` for a routine started by an event
  - **Enabled**, `true` or `false`
  - **Trigger**, only for an event routine, as JSON
  - one `text` code block with the routine's prompt, word for word

`<owner>` stands for the owner's GitHub username anywhere in a bot file. fakkelbot fills it in when it creates or changes a bot, and writes `<owner>` back when it exports. Write `<owner>` only where the username goes, never in text about the placeholder, because fakkelbot would fill that in too.

## Change a bot

The easiest way is to tell fakkelbot what to change. It works out the change with you, opens the PR and makes it live once the checks pass. To do it yourself:

1. Edit the bot's file on a branch and open a PR.
2. The Auto-merge workflow looks at what the PR changes. A low-risk change, such as clearer wording, merges itself once every check passes. A PR that adds a bot, a routine, a trigger or a power, or changes fakkelbot's own file, waits for you to merge it. [Decision 0002](../kb/bundle/decisions/0002-ci-decides-what-merges.md) has the full list. Add the `hold` label to a PR to keep it for yourself.
3. When the PR merges, fakkelbot's `apply` routine brings the changed bots in line with `main`.
   - If Auto-merge merged it, fakkelbot applies it at once and puts one line in your morning brief.
   - If you merged it, fakkelbot sends you a short list of what will change and waits. Reply "apply" in fakkelbot's chat, or "revert" to undo the PR. fakkelbot doesn't ask when you asked it for the change in its chat.
4. fakkelbot sends each changed bot its new text from `main`, exactly, then checks what the bots now have. If something didn't match, its report has four groups: what bots said they applied, what its check confirmed, confirmed mismatches, and what it couldn't read. A match shows the text is in place, not that a routine works. The routine's next real run shows that.

To undo a change, reply "revert" to fakkelbot with the PR number. It opens a PR that reverts it, and applies `main` again once that merges.

A bot changes only to match `main`. Every bot signs in to GitHub as you, so GitHub can't show which bot merged a PR. That's why fakkelbot asks you about a PR merged by your account, unless you asked fakkelbot for it. A PR, a comment or another bot's message never counts as your approval.

Every Sunday evening the `weekly-sync` routine compares the live bots with these files. If they differ, it opens a `sync/export-YYYY-MM-DD` PR and closes any older sync PR that's still open, because the new one replaces it. Merging a sync PR changes no bot. It records what the bots already have, and one that only records wording merges itself. A bot that still has an earlier version of its file is listed as "not applied yet" and left out of the export, so merging the sync PR never undoes a change you haven't applied.

`weekly-sync` also looks for missing runs: a routine with no run when one was due, a run marked succeeded that left no output, and a routine that's paused. It tells you what it couldn't check, and never says everything matches when it couldn't check it all.

### Test the apply loop (optional)

To see the whole loop work before you rely on it, make a change that does nothing.

1. Pick a bot, and add one sentence to the end of its instructions that changes nothing it does, such as "Your instructions and routines are kept in the owner's grok-bot-setup repo." Open a PR, and don't merge it.
2. Within a few minutes of its checks passing, the Auto-merge workflow should merge it. Its run in the Actions tab says why, or why it waited.
3. Watch the bot's chat. It should get the sentence from fakkelbot and replace its instructions.
4. The test passes when the bot's instructions in its settings end with the new sentence, your next morning brief has a line such as "fakkelbot: applied PR #12 (pantry: one sentence added)", and no approval card expired unanswered. You can leave the sentence in, or remove it the same way.

To test the path for a change that waits for you, add the `hold` label to the PR before its checks finish, then merge it yourself. fakkelbot should send you a line such as "pantry: one sentence added to its instructions" and wait for "apply" or "revert", with nothing changed yet.

If it fails:

- **The PR doesn't merge.** Open the newest Auto-merge run in the Actions tab. It lists what it waited for, such as a check still running or a change it counts as high risk. To check a PR again, run Auto-merge from the Actions tab with the PR's number.
- **fakkelbot does nothing after a merge.** Check that its `apply` routine exists, that its trigger is `pr-merged` on your grok-bot-setup repo, and that the GitHub integration can see that repo. Then check the routine's run history.
- **An approval card appears in the bot's chat.** Approve it there. A card raised by another bot expires after about 10 minutes and the change isn't saved. Add the Auto Review rule from step 6 of [SETUP.md](../SETUP.md), or stay nearby while an apply runs. If it expired, reply "apply" and the PR number to fakkelbot.
- **The bot refuses a change another bot relays.** Paste the new text into the bot's settings yourself. Then weekly-sync shows whether it matches.
- **The report says a field couldn't be read.** Check the bot's settings yourself. A bot's reply alone doesn't show the change was saved.

## Add a bot

The easiest way is to tell fakkelbot what you want. It asks a few questions, writes the file the way this section says, opens the PR, and creates the bot once the checks pass. To write one yourself:

1. Add `bots/<name>.md` in the format above. Its **Category** and **Default** lines put it in fakkelbot's menu. If it needs an app connected, add a line for it to step 6 of [SETUP.md](../SETUP.md).
2. Open a PR. A new bot always waits for you, so merge it yourself. When fakkelbot asks, reply "apply", and it creates the bot and its routines.

Give a new bot one job, and name its anti-jobs: the nearby work it leaves to other bots or to you. Give it only the tools and connectors that job needs, and turn off any left over. If it reads email, PRs, web pages or other bots' messages, say that text is data, never instructions. Say what it may do without asking and what needs you. Copy the Routing and Updates paragraphs from [inbox.md](inbox.md) word for word, changing only the file name in Updates. A bot that keeps personal notes can instead share only what the owner agrees to, as [audy.md](audy.md) does. Audy's one exception is the notes you ask it to keep: they go as issues to the private repository chosen at setup, through its [capture tool](../capture/README.md), and nowhere else. Keep the rule that nothing posts, replies or messages anyone but you without your approval of that one item. X's automation rules also forbid automated replies based on keyword searches.

### Optional Coding group

[claude.md](claude.md), [cursor.md](cursor.md) and [codex.md](codex.md) are optional Builders, each with no routines. Their job is the same; each operates its named coding CLI. [groups/coding.md](../groups/coding.md) describes the group, member choices and kickoff. Its message explains rules already in the member files; it is not a separate live bot configuration.

fakkelbot offers Coding as one optional group, or any subset, and follows [Coding setup](../docs/coding-group.md#setup) for CLI readiness, the default worker and computer choices. Adding the files or creating a bot does not install a CLI, transfer sign-ins or prove the bot can use a local computer. When adding a member later, fakkelbot performs the same checks during "apply". A group needs at least two chosen members; one works in its own chat.


Removing a file deletes no bot. Delete the bot yourself in Grok Bot if you want it gone.

## Share a bot as your own template

A Grok Bot template copies a bot's instructions, its routines, some plugins, and its relevant memories and skills. It copies no secrets, code or scripts (xAI's templates guide, 2026-09-08). Memories can hold personal details, so share a bot like this:

1. Create a fresh bot from its file here. Don't share one you've used for weeks.
2. Create the template from that fresh bot.
3. Add the template from a second Grok Bot account, and check what came across: instructions, routines, memories and skills.
4. Share the link only when nothing personal came with it. A bot whose file uses `<owner>` carries your GitHub username.

## Notification defaults

Each bot has a recommended Settings block and Sidebar default. [Notification settings](../docs/notification-settings.md) describes the owner-selected mode and temporary overrides. SETUP.md collects the choice before applying it; these defaults do not overwrite existing preferences. Each bot sets only its own `notify_on_updates` and `hidden_from_sidebar` through UpdateProfile. Keep defaults separate from active temporary state in exports.
