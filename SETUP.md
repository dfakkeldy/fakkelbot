# Setup procedure

fakkelbot follows these steps.

Each step checks first. If what it makes already exists, skip the step and tell the owner. So the whole procedure is safe to rerun, for example to add a bot later.

fakkelbot saves its progress and the owner's choices in `/workspace/setup/`. After each step, add a line such as `step 3 done` to `/workspace/setup/progress.md`. On a rerun, read that folder first, tell the owner in one line which steps are done, and continue from the first step that isn't. Never ask again for a choice saved there, unless the owner asks to change it. Still run each step's check, because something may have changed since.

`<owner>` is the owner's GitHub username, as defined in [bots/README.md](bots/README.md). `<tz>` is their timezone, such as `Europe/Berlin`. Schedules in `bots/*.md` are cron in `<tz>`.

The Grok Bot facts here are as of 2026-10-14. Grok Bot is in beta, so they may change. [kb/bundle/references/grok-bot-platform.md](kb/bundle/references/grok-bot-platform.md) has the sources.

## Steps

1. **Welcome the owner and record the answers.** First build the bot menu. Read each file in `bots/` except `README.md` and `fakkelbot.md`. Start with "I'll set up these unless you drop some:". Then write one line per category for the bots whose **Default** is `yes`, in the order that `bots/README.md` lists the categories. Write each bot as its name with a few words from the first sentence of its note in parentheses, such as `Daily life: liaison (morning brief), inbox (email triage)`. Leave out a category with no bots. If any bot's **Default** is `no`, end with "You can also add:" and list those bots the same way.

   In the optional Builders line, show `Coding group (claude, cursor, codex)` together, using [groups/coding.md](groups/coding.md). The owner can select the group or any subset of its members. Selecting `Coding` adds all three to the chosen bot list; selecting one adds only that member. They stay optional and have no routines.

   If `/workspace/setup/owner.md` exists, use its answers and don't ask the three questions again. If the owner asked to add or drop a bot, or to change an answer, change only that line. Otherwise send this welcome, with the menu in place of `<menu>`, and wait for the answers:

   ```text
   Hi. I'll set up a small team of Grok bots for you.
   I'll make a private GitHub repo with each bot's instructions, and a private message board the bots share. After that, you change a bot by asking me or with a pull request. Low-risk changes go live by themselves, and I'll ask you about the rest.
   Three questions:
   1. Your GitHub username?
   2. Your timezone, such as Europe/Berlin?
   3. Which bots? <menu>
   ```

   The owner can add or drop any bot. Then write the file:

   ```sh
   mkdir -p /workspace/setup
   printf 'github: %s\ntimezone: %s\nbots: %s\n' '<owner>' '<tz>' '<bots>' > /workspace/setup/owner.md
   ```

2. **Sign in to GitHub on the bots' computer.** Run `gh auth status`. If it shows `<owner>` signed in to github.com, go on to the last two commands. Otherwise stop and ask the owner to sign in. They can take over this computer and run this in a terminal:

   ```sh
   gh auth login --hostname github.com --git-protocol https --web
   ```

   If they'd rather use a token, use Grok Bot's secure secret request so the token never shows in chat, and feed it to `gh auth login --with-token`. Never ask them to paste a token in chat. Then run:

   ```sh
   gh auth setup-git
   gh api user --jq .login
   ```

   If the login isn't `<owner>`, stop and ask.

3. **Create the owner's copy of this repo.** If `gh repo view <owner>/grok-bot-setup --json visibility` succeeds, the repo exists, so skip. Tell the owner if it shows `PUBLIC`. Otherwise run:

   ```sh
   gh repo create <owner>/grok-bot-setup --private --template dfakkeldy/fakkelbot
   ```

4. **Clone it.** If `git -C /workspace/grok-bot-setup remote get-url origin` names `<owner>/grok-bot-setup`, run `git -C /workspace/grok-bot-setup pull --ff-only` and skip. If the folder holds anything else, stop and ask. Otherwise run:

   ```sh
   gh repo clone <owner>/grok-bot-setup /workspace/grok-bot-setup
   ```

   If the clone has no `SETUP.md`, GitHub is still copying the template. Wait a minute and pull again. From now on, read this file and `bots/` from `/workspace/grok-bot-setup`. Never edit files there, because every bot reads that checkout. A bot that changes the repo works in its own git worktree.

5. **Create the board.** The board is a private repo where the bots and the owner's other agents leave each other messages. If `gh repo view <owner>/agent-board` succeeds, the owner already has a repo with that name, maybe a board other agents use. Stop and ask whether these bots should share it. Connect to it only after the owner says yes. Otherwise run:

   ```sh
   gh repo create <owner>/agent-board --private
   ```

   Then connect the board client with the command from `## Set up` in `board/README.md`. `connect` syncs, and running it again is safe.

   ```sh
   python3 /workspace/grok-bot-setup/board/board.py connect --repository <owner>/agent-board
   ```

   If `connect` fails after a mistyped repo name and `/workspace/.agent-board/messages.jsonl.remote.json` doesn't exist, ask the owner whether to delete `/workspace/.agent-board`, then connect again with the right name.

6. **Ask the owner to connect what the bots need.** Ask for all of these in one message, then wait until the owner says each is done. Skip any that `progress.md` marks done or that you can see is done. Add a line to `progress.md` as each one is done, such as `gmail done`, so a rerun doesn't ask again.
   - **Board and KB instructions for other coding agents, optional.** Once the board connection works, offer to add two short sections to the owner's `CLAUDE.md` and `AGENTS.md`, one for the board and one for the knowledge base, following [the instruction-file setup guide](docs/agent-instructions-setup.md). They can choose user-level files, selected private projects, or skip, and take one section or both. Show the paths and exact diff, preserve existing instructions, and update an existing board or KB section instead of duplicating it. Private board routing and local clone paths belong in private instructions. Record the choice in `/workspace/setup/agent-instructions.md`, so a rerun preserves it and does not ask again unless the owner wants a change. Skipping or a pending local-computer step does not block the rest of setup. Repository changes go through a PR; never edit a shared checkout or change computer permissions to install this section.
   - **GitHub events.** Connect the GitHub integration on the account that runs Grok Bot, and give it access to `<owner>/grok-bot-setup`. The `apply` routine's trigger needs it. It's separate from `gh` and from the GitHub plugin.
   - **Gmail, if they chose inbox.** In Grok Bot, open Connect apps and add Gmail. Then turn off the connector's send, reply and forward tools, and keep read, search, mark read, labels and drafts. inbox's rule against sending is only an instruction, and the switch enforces it.
   - **Google Calendar, if they chose scheduler.** In Grok Bot, open Connect apps and add Google Calendar. If it lists its tools, turn off deleting events and answering invites. scheduler's rules against both are only instructions.
   - **A computer, if they chose clerk.** clerk works on the owner's own Mac or Windows computer, not on this one. Ask them to connect it to Grok Bot. The docs don't explain how yet, so if they're stuck, point them to Settings > Computer in the desktop app. Then ask them to keep that computer's setting at Ask every time under Settings > Computer > Computers. Always allow would let every bot run commands there without asking.
   - **Coding tools, if they chose claude, cursor or codex.** Follow steps 1-4 of [Coding setup](docs/coding-group.md#setup). Verify the selected CLI and sign-in on each intended computer, record readiness, the default worker and review preference, and preserve existing choices on reruns. Grok's computer is the default; recommend a connected local computer when the project needs it, and confirm that project's first local choice once. Use its existing permissions. A missing CLI or sign-in leaves only that member pending; continue the rest of setup. Never install on a different computer, copy credentials or add paid access as a fallback. Skip this entire step when no coding member was chosen.
   - **Automatic applies.** Low-risk bot changes go live with nobody watching, and a bot that replaces its own instructions may raise an approval card that expires after about 10 minutes. Suggest one narrow rule in Grok Bot under Settings > General > Auto-review, as an Allow automatically rule: `Allow automatically when a bot replaces its own instructions or routines with text that fakkelbot sent, and that text matches bots/<the bot's own name>.md on main in /workspace/grok-bot-setup.` Never suggest a broader rule. Auto Review still stops an action it finds another reason to stop. The rule is saved on the desktop where it's added, so the owner adds it again on another desktop. If they skip it, applies still work while they're nearby to answer the card.
   - **Repos, if they chose pr-watch, librarian or editor.** pr-watch always watches `<owner>/grok-bot-setup`, so leave that repo out. Ask which other repos pr-watch should watch, librarian should collect merged PRs from, and editor should find post ideas in, as `owner/repo`. Use one list for all of them unless the owner wants separate lists. If a list file exists, keep it without asking. Write one repo per line, to the file of each chosen bot:

     ```sh
     mkdir -p /workspace/pr-watch /workspace/librarian /workspace/editor
     printf '%s\n' 'example-org/example-app' > /workspace/pr-watch/repos.txt
     printf '%s\n' 'example-org/example-app' > /workspace/librarian/repos.txt
     printf '%s\n' 'example-org/example-app' > /workspace/editor/repos.txt
     ```

7. **Create the bots.** Create liaison first, because the others report to it, then librarian, because others send it facts. Put the owner's username in place of `<owner>` everywhere in a bot's text. For each chosen bot:
   1. If a bot with that name exists, skip it. Check your bot list, or the `name` in each `profile.json` under `/home/box/agent-data/agents`. If your own name is still setup, you are fakkelbot from before the rename and `bots/fakkelbot.md` is your own file, so never create another bot from it. Ask the owner once to rename you to fakkelbot under Edit Profile in Grok Bot, and to change setup to fakkelbot in their Auto-review rule, because the other bots take updates only from fakkelbot.
   2. Read `bots/<name>.md`. Create the bot with CreateAgent. Use the file's heading as its name and its Instructions text exactly.
   3. Create each routine in the file with its folder name, its schedule in `<tz>`, its enabled flag and its exact prompt. If CreateAgent can't add routines, send the new bot one SendToAgent message with them, and ask it to create each one exactly and reply with the list.
   4. Check that the bot's routines match the file. Tell the owner to answer any approval card within 10 minutes, because a card raised by another bot expires.

   If coding members were chosen, follow step 5 of [Coding setup](docs/coding-group.md#setup) to create or help the owner create **Coding** with the chosen members. A single member needs no group. Verify membership before reusing a group; never replace an unrelated one. Skip this step on a rerun when the matching group already exists and the kickoff was sent.

8. **Create your own routines.** From `bots/fakkelbot.md`, create `apply` and `weekly-sync` for yourself, unless they exist. Fill in `<owner>` as in step 7.

9. **Post to the board.** These commands are from `## Post and read` in `board/README.md`. Look for an earlier post:

   ```sh
   python3 /workspace/grok-bot-setup/board/board.py threads --project grok-bot-setup --search "First setup" --limit 20
   ```

   If it prints a thread with the topic `First setup`, skip. Otherwise post:

   ```sh
   printf '%s\n' 'Setup finished. Bot changes go through PRs in grok-bot-setup.' | python3 /workspace/grok-bot-setup/board/board.py post --author fakkelbot --task first-setup --project grok-bot-setup --topic "First setup" --kind update --owner-visible
   ```

   If the post reports `queued`, run `python3 /workspace/grok-bot-setup/board/board.py sync`. Never post it twice.

10. **Tell the owner.** Send one message with:
    - what you created, with links to both repos
    - what already existed and you skipped
    - each chosen bot, one line each, as one of these. Save the same list in `/workspace/setup/status.md`.
      - **ready**: the bot and its routines match its file, and everything it needs is connected.
      - **onboarding needed**: it works once the owner does one thing, such as answering its first questions in its own chat, adding a connector or answering an approval card. Name the thing.
      - **blocked**: it couldn't be created, or something it needs failed, such as a missing CLI or sign-in. Say what failed and the next step.
    - what's left that isn't about one bot, such as GitHub events or the board
    - for Coding, which members and CLIs are ready on which computer, the default worker, and whether the group is ready or pending
    - how to change a bot, which is to edit its file in `bots/` and open a PR. A low-risk change merges itself once its checks pass and goes live, with a line in the morning brief. A PR that adds a bot, a trigger or a power waits for the owner to merge it. Then fakkelbot asks them to reply "apply" or "revert", unless they asked fakkelbot for that change.
    - a reminder to check that Settings > General > Bot > Timezone shows `<tz>`
