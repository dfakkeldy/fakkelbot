# Coding group setup and computers

The optional [Coding group](../groups/coding.md) contains Grok bots that launch Claude Code, Cursor Agent and Codex CLI. The selected CLI does the task work. Adding a bot does not install its CLI or sign it into an account.

## Setup

Setup follows this section when the owner chooses the Coding group or any of its members, including when adding them later with "apply".

1. Ask which tools they want, if their selection did not already say. Selecting **Coding** means all three; they can keep any subset. Explain that Grok's computer is the default and a connected local computer can be chosen per project.
2. Check the selected CLIs on Grok's computer, or on the local computer the owner chose. Inspect the executable, version and sign-in with the table below. Record readiness separately for each tool and computer. An app installed or signed in on the owner's laptop does not prove its CLI is ready on Grok's computer.
3. If a selected CLI is missing, offer to install it on the selected computer using its official installation guide, or leave that member pending. Install only after the owner chooses that option. If sign-in is missing, have the owner use Take over or the service's login flow in a direct chat. Never ask for credentials in chat or copy them from another computer. Check again after setup. Missing tools do not block the other selected members or the rest of the starter.
4. Record the selected members, readiness by computer, default worker and review preference in `/workspace/coding/setup.md`. Keep existing choices on a rerun and add newly selected members to the saved roster; never infer that an existing member should be removed. Unless the owner specifies otherwise, use their first selected ready member as the default worker and get cross-tool reviews only when requested. If none is ready, record that there is no default worker yet and report what is missing. Save no tokens, passwords or account exports.
5. Create the chosen bots in the normal SETUP bot step. With at least two chosen members, create or guide the owner through [creating Coding](../groups/coding.md#create-the-group). With one, use its direct chat. Verify membership and send the kickoff with the saved default worker, once a worker is ready. Report separately which bots, CLIs and group steps are ready or pending. Reuse the existing bots and matching group on a rerun.

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

Inspect the installed CLI's help before choosing flags. Run from the task worktree, with the owner assignment, relevant repo instructions, approved scope, expected checks and delivery rules in the prompt. Keep the task's exact session ID for follow-ups; avoid global latest-session shortcuts because other tasks share the computer.

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

CLI commands, authentication and computer behavior were checked against the linked official documentation on 2026-10-14. See also [Claude CLI reference](https://code.claude.com/docs/en/cli-reference), [Cursor authentication](https://cursor.com/docs/cli/reference/authentication) and [Grok computer documentation](https://docs.x.ai/grok-bot/computer-and-apps). This repository verifies its templates and chart; it does not exercise provider accounts or connected computers in CI.
