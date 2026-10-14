# Setup procedure

The setup bot follows these steps.

Each step checks first. If what it makes already exists, skip the step and tell the owner. So the whole procedure is safe to rerun, for example to add a bot later.

`<owner>` is the owner's GitHub username. `<tz>` is their timezone, such as `Europe/Berlin`. Schedules in `bots/*.md` are cron in `<tz>`.

The Grok Bot facts here are as of 2026-10-13. Grok Bot is in beta, so they may change.

## Steps

1. **Record the answers.** If `/workspace/setup/owner.md` exists, read it and confirm it with the owner. Otherwise ask for `<owner>`, `<tz>` and the bots they want. The default is liaison, inbox, researcher, pr-watch and librarian. Then write the file:

   ```sh
   mkdir -p /workspace/setup
   printf 'github: %s\ntimezone: %s\nbots: %s\n' '<owner>' '<tz>' 'liaison inbox researcher pr-watch librarian' > /workspace/setup/owner.md
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
   gh repo create <owner>/grok-bot-setup --private --template dfakkeldy/grok-bot-starter
   ```

4. **Clone it.** If `git -C /workspace/grok-bot-setup remote get-url origin` names `<owner>/grok-bot-setup`, run `git -C /workspace/grok-bot-setup pull --ff-only` and skip. If the folder holds anything else, stop and ask. Otherwise run:

   ```sh
   gh repo clone <owner>/grok-bot-setup /workspace/grok-bot-setup
   ```

   If the clone has no `SETUP.md`, GitHub is still copying the template. Wait a minute and pull again. From now on, read this file from `/workspace/grok-bot-setup/SETUP.md`. Never edit files there, because every bot reads that checkout. A bot that changes the repo works in its own git worktree.

5. **Create the board.** The board is a private repo where the bots and the owner's other agents leave each other messages. If `gh repo view <owner>/agent-board` succeeds, skip creating it. Otherwise run:

   ```sh
   gh repo create <owner>/agent-board --private
   ```

   Then connect the board client. If `sync-status` prints a status, the client is already connected, so skip `connect`.

   ```sh
   python3 /workspace/grok-bot-setup/board/agent_messages.py sync-status
   python3 /workspace/grok-bot-setup/board/agent_messages.py connect --repository <owner>/agent-board
   python3 /workspace/grok-bot-setup/board/agent_messages.py refresh
   ```

   These commands come from the `## Set up` section of `board/README.md`. If that section differs, follow it.

6. **Ask the owner to connect what the bots need.** Ask for all of these in one message, then wait until the owner says each is done. Skip any that's already done.
   - **GitHub events.** Connect the GitHub integration on the account that runs Grok Bot, and give it access to `<owner>/grok-bot-setup`. The `apply` routine's trigger needs it. It's separate from `gh` and from the GitHub plugin.
   - **Gmail, if they chose inbox.** In Grok Bot, open Connect apps and add Gmail. Then turn off the connector's send, reply and forward tools, and keep read, search, mark read and drafts. inbox's rule against sending is only an instruction, and the switch enforces it.
   - **Repos, if they chose pr-watch or librarian.** Ask which repos pr-watch should watch and librarian should collect merged PRs from, as `owner/repo`. Use one list for both unless the owner wants two. If a list file exists, show it and ask whether to keep it. Write one repo per line, to the file of each chosen bot:

     ```sh
     mkdir -p /workspace/pr-watch /workspace/librarian
     printf '%s\n' 'example-org/example-app' > /workspace/pr-watch/repos.txt
     printf '%s\n' 'example-org/example-app' > /workspace/librarian/repos.txt
     ```

7. **Create the bots.** Create liaison first, because the others report to it, then librarian, because others send it facts. For each chosen bot:
   1. If a bot with that name exists, skip it. Check your bot list, or the `name` in each `profile.json` under `/home/box/agent-data/agents`.
   2. Read `bots/<name>.md`. Create the bot with CreateAgent. Use the file's heading as its name and its Instructions text exactly.
   3. Create each routine in the file with its folder name, its schedule in `<tz>`, its enabled flag and its exact prompt. If CreateAgent can't add routines, send the new bot one SendToAgent message with them, and ask it to create each one exactly and reply with the list.
   4. Check that the bot's routines match the file. Tell the owner to answer any approval card within 10 minutes, because a card raised by another bot expires.

8. **Create your own routines.** From `bots/setup.md`, create `apply` and `weekly-sync` for yourself, unless they exist. In the trigger, put the owner's username in place of `<owner>`.

9. **Post to the board.** If `threads --search "first setup"` finds a thread from `setup`, skip. Otherwise post:

   ```sh
   python3 /workspace/grok-bot-setup/board/agent_messages.py threads --search "first setup" --limit 5
   printf '%s\n' 'Setup finished. Bot changes go through PRs in grok-bot-setup.' | python3 /workspace/grok-bot-setup/board/agent_messages.py post --author setup --task "first setup" --project grok-bot-setup --kind update --owner-visible
   ```

   If the post reports `queued`, run `sync`. Never post it twice.

10. **Tell the owner.** Send one message with:
    - what you created, with links to both repos
    - what already existed and you skipped
    - what's left, such as a connector, an approval card or a step that failed
    - how to change a bot, which is to edit its file in `bots/`, open a PR, merge it, and reply "apply" here
    - a reminder to check that Settings > General > Bot > Timezone shows `<tz>`
