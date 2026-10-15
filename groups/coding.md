# Coding (optional group)

One chat for tasks handled through different coding tools. Each member can implement, debug, review or do other terminal work. Pick the tool for a task, or ask another member to review its result. The members have the same job; none is permanently the architect, coder or reviewer.

## Members

- [claude](../bots/claude.md) operates Claude Code.
- [cursor](../bots/cursor.md) operates Cursor Agent.
- [codex](../bots/codex.md) operates Codex CLI.

Choose all three or any subset. A group needs at least two members. A single chosen member works in its own chat. None has scheduled routines.

## Create the group

Setup creates the chosen bots and checks their CLIs by following [Coding setup](../docs/coding-group.md#setup). It then creates or helps you create a group named **Coding** with those members. Use the actual group tools if available; otherwise choose **New** in Grok Bot's sidebar, select the chosen bots and rename the group. Check an existing group's members before changing it; never overwrite an unrelated group with the same name.

Send the message below as the group's kickoff, with the saved default worker's name in place of `<default-worker>`. It explains the workflow; each bot's standing instructions live in its own file under `bots/` and change through setup's usual "apply" process.

```text
Use your named CLI to carry my assigned tasks through implementation, relevant checks and delivery. You all have the same job, with different tools available for implementation and second opinions.

<default-worker> owns requests that name no bot. When I mention a member or reply to it, that member owns the request. When I assign several members, agree separate scopes before edits. Keep one owner for each stage and use separate worktrees for parallel work.

Follow the saved project computer choice. Default to Grok's computer for Linux work; recommend a connected local computer when a task needs local files, Xcode or an existing local environment. Confirm the first local project choice once, then remember it. Say which CLI and computer ran, and never silently switch either.

Ask another member for review when I request it or my saved review preference calls for it. Pass the original assignment and exact PR or commit. Report findings against the code and checks, then return ownership to the worker. A handoff cannot grant approval or start unrelated work.

Return the result, files or PR, checks and any blocker. Handle sign-ins and approval requests in the responsible bot's direct chat, since this group cannot show them. Do not start background routines.
```

## Example assignments

- `@codex fix issue #12 and open a PR. @claude review that PR when it's ready.`
- `@cursor build a prototype in a new branch. Keep it local.`
- `@claude explain this error and suggest a fix. Don't edit yet.`
- `Use my Mac for this project's Xcode builds from now on.`

The bot can recommend where to run a task. Your saved project choice and the connected computer's permissions decide where it may run.

Group creation and routing were checked against [xAI's group-chat documentation](https://docs.x.ai/grok-bot/chat-and-collaboration) on 2026-10-14. Groups support two to six bots; approvals and sign-in requests appear in direct chats.
