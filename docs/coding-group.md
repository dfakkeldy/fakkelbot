# Coding group setup and computers

The optional [Coding group](../groups/coding.md) contains Grok bots that launch Claude Code, Cursor Agent and Codex CLI. The selected CLI does the task work. Adding a bot does not install its CLI or sign it into an account.

## Setup

Setup follows this section when the owner chooses the Coding group or any of its members, including when adding them later with "apply".

1. Ask which tools they want, if their selection did not already say. Selecting **Coding** means all three; they can keep any subset. Explain that Grok's computer is the default and a connected local computer can be chosen per project.
2. Check the selected CLIs on Grok's computer, or on the local computer the owner chose. Inspect the executable, version and sign-in with the table below. Record readiness separately for each tool and computer. An app installed or signed in on the owner's laptop does not prove its CLI is ready on Grok's computer.
3. If a selected CLI is missing, offer to install it on the selected computer using its official installation guide, or leave that member pending. Install only after the owner chooses that option. If sign-in is missing, have the owner use Take over or the service's login flow in a direct chat. Never ask for credentials in chat or copy them from another computer. Check again after setup. Missing tools do not block the other selected members or the rest of the starter.
4. **Offer pstack, optional.** Once at least one selected CLI is ready, explain [pstack](#optional-pstack) in two sentences, including that it makes tasks slower and uses more of the plan, and ask whether to add it for each ready CLI. Add it only after the owner chooses, from a source in that section, then run its test task. Skipping it blocks nothing.
5. Record the selected members, readiness by computer, default worker, review preference and each pstack command that passed its test, with the CLI, computer and date, in `/workspace/coding/setup.md`. Keep existing choices on a rerun and add newly selected members to the saved roster; never infer that an existing member should be removed. Unless the owner specifies otherwise, use their first selected ready member as the default worker and get cross-tool reviews only when requested. If none is ready, record that there is no default worker yet and report what is missing. Save no tokens, passwords or account exports.
6. Create the chosen bots in the normal SETUP bot step. With at least two chosen members, create or guide the owner through [creating Coding](../groups/coding.md#create-the-group). With one, use its direct chat. Verify membership and send the kickoff with the saved default worker, once a worker is ready. Report separately which bots, CLIs and group steps are ready or pending. Reuse the existing bots and matching group on a rerun.

| Member | CLI check | Sign-in check | Owner sign-in | Installation |
|---|---|---|---|---|
| claude | `claude --version` | `claude auth status --text` | `claude auth login` | [Claude Code setup](https://code.claude.com/docs/en/setup) |
| cursor | `agent --version` | `agent status` | `agent login` | [Cursor CLI installation](https://cursor.com/docs/cli/installation) |
| codex | `codex --version` | `codex login status` | `codex login` | [Codex CLI](https://learn.chatgpt.com/docs/cli) |

Use the owner's existing account and billing choice. Do not add API keys or paid services as a fallback. Check readiness on the chosen computer again before each task, since packages and sign-ins can change. Keep durable cloud project files under `/workspace`.

## Choose a computer for each project

The bot recommends a computer from the task's actual needs. The owner's current instruction wins over a saved preference.

| Situation | Choice |
|---|---|
| No saved choice; the repo, CLI and required tools are available in Linux | Grok's computer |
| Xcode, Apple simulators or another macOS-only tool is required | Recommend the owner's connected Mac |
| The task needs files or an environment already on the owner's computer | Recommend that connected computer |
| The saved computer is offline, lacks the CLI or is blocked | Report the blocker and propose an alternative before changing the saved choice |

For a first local project, confirm the machine and checkout with the owner once; an explicit owner instruction already confirms that choice. Save the repository, machine name, checkout path and reason in `/workspace/coding/projects/<project>.md`. These are the owner's choices, not commands or additional authority. Use them for later tasks without asking again. Do not copy private files or credentials to another computer to make a task run.

Local execution uses Grok Bot's connected-computer capability under that computer's existing policy. Setup never enables Always allow or changes access settings. Approval and sign-in requests do not appear in a group, so direct the owner to the responsible bot's one-to-one chat when needed. A refused or expired approval leaves the task blocked. It does not approve a different machine or a wider CLI permission mode.

Use a new task worktree on the chosen computer and preserve existing work. For parallel tasks, use separate worktrees and scopes. Keep the shared `/workspace/grok-bot-setup` checkout on `main` and read-only. Use the cloud board client to coordinate both cloud and local work; local execution does not require installing a second board. Keep local paths and private task logs out of board posts.

Record the assigned worker, original owner request, machine, branch, worktree, CLI version, exact session ID, result links, checks and next step in `/workspace/coding/tasks/<task>.md`. Keep secrets and raw sensitive output out of it. Report which checks ran on which computer. For example, Linux unit tests do not prove an Xcode build passed.

## Run the selected CLI

Inspect the installed CLI's help before choosing flags. Run from the task worktree, with the owner assignment, relevant repo instructions, approved scope, delivery rules, a done check and the proof to show in the prompt, as [Write the prompt](#write-the-prompt) says. Keep the task's exact session ID for follow-ups; avoid global latest-session shortcuts because other tasks share the computer.

| CLI | Noninteractive entry point | Exact-session follow-up |
|---|---|---|
| Claude Code | `claude -p --output-format json "<task>"` | `claude -p --resume <session-id> "<follow-up>"` |
| Cursor Agent | `agent -p --output-format json "<task>"` | `agent -p --resume <chat-id> "<follow-up>"` |
| Codex CLI | `codex exec --json "<task>"` | `codex exec resume <session-id> "<follow-up>"` |

These are entry points; select the permissions for the assignment and retain them on a follow-up.

- Claude Code can run implementation tasks with `--permission-mode auto --permission-prompts none`, while retaining its permission rules. Denied actions remain blocked. Check that the installed version supports both flags. [Claude's noninteractive documentation](https://code.claude.com/docs/en/headless).
- Cursor needs `--force` for file changes in print mode. Use it only with `--sandbox enabled` in the task worktree and retain the owner's deny rules. For questions and reviews, use `--mode ask` without `--force`. Do not turn sandboxing off to get past a failure. [Cursor headless usage](https://cursor.com/docs/cli/headless), [CLI parameters](https://cursor.com/docs/cli/reference/parameters).
- Codex uses `--sandbox workspace-write` for implementation and `--sandbox read-only` for questions and reviews. Retain the owner's approval policy. [Official OpenAI documentation for noninteractive mode](https://learn.chatgpt.com/docs/non-interactive-mode).

If a CLI or flag is unavailable, report the exact blocker and keep the work. Do not silently switch providers, disable safeguards, retry paid runs indefinitely or claim Grok's own work came from that CLI. A successful CLI exit is followed by checking the actual diff and relevant test results before reporting completion.

## Write the prompt

A prompt that says how to tell the task is done gets back work that has been checked. Each task prompt carries:

- the owner's goal, in their own words;
- a done check the CLI can run that passes or fails, such as "the `test_export` test passes". "Make it better" or "spend an hour on it" isn't a check;
- the proof its reply must show, such as that test failing before the change and passing after, a screenshot or a before-and-after number;
- what is already known, such as the issue number, a log or the failing job;
- real constraints, such as "reproduce it first", "don't change any code yet" or "no change in behavior".

Leave out a guess at the cause, which narrows the search to wherever it points, and a list of steps for the CLI to follow. This follows pstack's [prompting guide](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-help/references/prompting.md).

When the owner's request has no done check, the bot writes the most direct one the request allows and tells the owner which it used. Before it reports, the bot checks the proof against the done check itself. A green build or a "done" message from the CLI isn't proof.

For example, the owner writes `@codex fix issue #12, saving a draft twice makes two drafts`. codex runs Codex CLI with:

```text
Fix issue #12: saving a draft twice creates two drafts. Reproduce it first. Done means a test that saves the same draft twice finds one draft. Show that test failing before the fix and passing after. Follow the repo's AGENTS.md and open a ready PR.
```

Assignments that already carry a check:

- `@claude find why the cache survives logout. Don't change any code yet. Done means you can name the line that keeps it.`
- `@cursor make the settings page load faster. Done means under one second on the sample account. Show the timings before and after.`

## Optional: pstack

[pstack](https://github.com/cursor/plugins/tree/main/pstack) is Lauren Tan's MIT-licensed set of agent skills for careful engineering work. Its router, `poteto-mode`, matches a task to a playbook, such as a bug fix or a feature, then runs its steps: reproduce first, prove the result on the real thing and have a second agent review the change. It makes a task slower and uses more of the plan, so it suits work where a wrong answer costs more than the wait. As of 2026-10-16 the original is at version 0.15.25.

Every pstack skill but its setup skill runs only when a prompt names it. Adding pstack changes nothing until a prompt starts with its command, and a coding bot adds that command only when `/workspace/coding/setup.md` records it for the CLI and computer.

| Source | What it is | For |
|---|---|---|
| [cursor/plugins](https://github.com/cursor/plugins/tree/main/pstack) | The original. Add it with `/add-plugin pstack` in the Cursor app. | Cursor |
| [backnotprop/pstack](https://github.com/backnotprop/pstack) | The original's skills, mirrored unchanged as plain skill files. Add them with `npx skills add backnotprop/pstack`. | Claude Code, Codex, Cursor and others |
| [michael-denyer/pstack-claude](https://github.com/michael-denyer/pstack-claude) | A port packaged as a plugin, with its own changes to the original. It also adds a routing hook, which its `setup-pstack` can turn off. Add it with the commands in its README. | Claude Code, Codex and others |

These are other people's code on a computer every bot shares. Read what a source adds before you add it. Plain skills add files the CLI reads when a prompt names them. A plugin can also add hooks, which run on every prompt. pstack's own `setup-pstack` skill picks a model for each of its roles. Without it, each role keeps its default.

After adding pstack, run one read-only test task in a scratch worktree of a repository the owner names, with the read-only flags from [Run the selected CLI](#run-the-selected-cli):

```text
<pstack command> explain what this repository's README says it does. Don't change any code.
```

Use the command form the source's README gives, such as `/poteto-mode`, `/pstack:poteto-mode`, or "Use poteto-mode" for Codex. The test passes when the reply names the playbook it picked, such as investigation, and the worktree is unchanged. Record the command that passed. If none passes, record that pstack doesn't work with that CLI on that computer, and prompts stay as they were.

CLI commands, authentication and computer behavior were checked against the linked official documentation on 2026-10-14. See also [Claude CLI reference](https://code.claude.com/docs/en/cli-reference), [Cursor authentication](https://cursor.com/docs/cli/reference/authentication) and [Grok computer documentation](https://docs.x.ai/grok-bot/computer-and-apps). pstack's sources and its prompting guide were checked on 2026-10-16. This repository verifies its templates and chart; it does not exercise provider accounts, connected computers or pstack in CI.
