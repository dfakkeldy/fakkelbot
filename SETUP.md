# Setup procedure

The setup bot follows these steps.

Each step checks first. If what it makes already exists, skip the step and tell the owner. So the whole procedure is safe to rerun, for example to add a bot later.

`<owner>` is the owner's GitHub username, as defined in [bots/README.md](bots/README.md). `<tz>` is their timezone, such as `Europe/Berlin`. Schedules in `bots/*.md` are cron in `<tz>`.

The Grok Bot facts here are as of 2026-10-14. Grok Bot is in beta, so they may change. [kb/references/grok-bot-platform.md](kb/references/grok-bot-platform.md) has the sources.

## Steps

1. **Welcome the owner and record the answers.** First build the bot menu, as described below. If `/workspace/setup/owner.md` exists, show the owner its answers and the menu, and ask what to change. Otherwise send this welcome, with the menu in place of `<menu>`, and wait for the answers:

   ```text
   Hi. I'll set up a small team of Grok bots for you.
   I'll make a private GitHub repo with each bot's instructions, and a private message board the bots share. After that, you change a bot by merging a pull request and replying "apply" here.
   Three questions:
   1. Your GitHub username?
   2. Your timezone, such as Europe/Berlin?
   3. Which bots? <menu>
   ```

   To build the menu, read each file in `bots/` except `README.md` and `setup.md`. Start with "I'll set up these unless you drop some:". Then write one line per category for the bots whose **Default** is `yes`, in the order Daily life, Work, Builders, Content. Write each bot as its name with a few words from the first sentence of its note in parentheses, such as `Daily life: liaison (morning brief), inbox (email triage)`. Leave out a category with no bots. If any bot's **Default** is `no`, end with "You can also add:" and list those bots the same way.

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
   gh repo create <owner>/grok-bot-setup --private --template dfakkeldy/grok-bot-starter
   ```

4. **Clone it.** If `git -C /workspace/grok-bot-setup remote get-url origin` names `<owner>/grok-bot-setup`, run `git -C /workspace/grok-bot-setup pull --ff-only` and skip. If the folder holds anything else, stop and ask. Otherwise run:

   ```sh
   gh repo clone <owner>/grok-bot-setup /workspace/grok-bot-setup
   ```

   If the clone has no `SETUP.md`, GitHub is still copying the template. Wait a minute and pull again. From now on, read this file and `bots/` from `/workspace/grok-bot-setup`. Never edit files there, because every bot reads that checkout. A bot that changes the repo works in its own git worktree.

5. **Create the board.** The board is a private repo where the bots and the owner's other agents leave each other messages. If `gh repo view <owner>/agent-board` succeeds, skip creating it. Otherwise run:

   ```sh
   gh repo create <owner>/agent-board --private
   ```

   Then connect the board client. `connect` syncs, and running it again is safe.

   ```sh
   python3 /workspace/grok-bot-setup/board/board.py connect --repository <owner>/agent-board
   ```

   If `connect` fails after a mistyped repo name and `/workspace/.agent-board/messages.jsonl.remote.json` doesn't exist, ask the owner whether to delete `/workspace/.agent-board`, then connect again with the right name.

6. **Ask the owner to connect what the bots need.** Ask for all of these in one message, then wait until the owner says each is done. Skip any that's already done.
   - **GitHub events.** Connect the GitHub integration on the account that runs Grok Bot, and give it access to `<owner>/grok-bot-setup`. The `apply` routine's trigger needs it. It's separate from `gh` and from the GitHub plugin.
   - **Gmail, if they chose inbox.** In Grok Bot, open Connect apps and add Gmail. Then turn off the connector's send, reply and forward tools, and keep read, search, mark read and drafts. inbox's rule against sending is only an instruction, and the switch enforces it.
   - **Repos, if they chose pr-watch or librarian.** pr-watch always watches `<owner>/grok-bot-setup`, so leave that repo out. Ask which other repos pr-watch should watch and librarian should collect merged PRs from, as `owner/repo`. Use one list for both unless the owner wants two. If a list file exists, show it and ask whether to keep it. Write one repo per line, to the file of each chosen bot:

     ```sh
     mkdir -p /workspace/pr-watch /workspace/librarian
     printf '%s\n' 'example-org/example-app' > /workspace/pr-watch/repos.txt
     printf '%s\n' 'example-org/example-app' > /workspace/librarian/repos.txt
     ```

7. **Create the bots.** Create liaison first, because the others report to it, then librarian, because others send it facts. Put the owner's username in place of `<owner>` everywhere in a bot's text. For each chosen bot:
   1. If a bot with that name exists, skip it. Check your bot list, or the `name` in each `profile.json` under `/home/box/agent-data/agents`.
   2. Read `bots/<name>.md`. Create the bot with CreateAgent. Use the file's heading as its name and its Instructions text exactly.
   3. Create each routine in the file with its folder name, its schedule in `<tz>`, its enabled flag and its exact prompt. If CreateAgent can't add routines, send the new bot one SendToAgent message with them, and ask it to create each one exactly and reply with the list.
   4. Check that the bot's routines match the file. Tell the owner to answer any approval card within 10 minutes, because a card raised by another bot expires.

8. **Create your own routines.** From `bots/setup.md`, create `apply` and `weekly-sync` for yourself, unless they exist. Fill in `<owner>` as in step 7.

9. **Post to the board.** Look for an earlier post:

   ```sh
   python3 /workspace/grok-bot-setup/board/board.py threads --project grok-bot-setup --search "First setup" --limit 20
   ```

   If it prints a thread with the topic `First setup`, skip. Otherwise post:

   ```sh
   python3 /workspace/grok-bot-setup/board/board.py post --author setup --task first-setup --project grok-bot-setup --topic "First setup" --kind update --owner-visible <<'EOF'
   Setup finished. Bot changes go through PRs in grok-bot-setup.
   EOF
   ```

   If the post reports `queued`, run `python3 /workspace/grok-bot-setup/board/board.py sync`. Never post it twice.

10. **Tell the owner.** Send one message with:
    - what you created, with links to both repos
    - what already existed and you skipped
    - what's left, such as a connector, an approval card or a step that failed
    - how to change a bot, which is to edit its file in `bots/`, open a PR, merge it, and reply "apply" here
    - a reminder to check that Settings > General > Bot > Timezone shows `<tz>`
