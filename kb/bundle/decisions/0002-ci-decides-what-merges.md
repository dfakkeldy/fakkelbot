---
type: Decision
title: CI decides what merges
description: Low-risk PRs merge themselves once every check passes on their head commit, the bots follow main, and the owner decides only high-risk changes.
tags:
  - pull-requests
  - auto-merge
timestamp: 2026-10-15T21:50:05-03:00
---

# 0002. CI decides what merges

Accepted on 2026-10-14. It replaces [0001. Every change goes through a PR](0001-every-change-goes-through-a-pr.md). On 2026-10-15 the KB paths below were updated when the notes moved into `kb/bundle/`. The decision itself didn't change.

## Context

Under 0001, the owner merged every PR and replied "apply" to every bot change. That meant an approval for each daily KB PR, each weekly sync and each wording fix, which the checks in CI could judge just as well.

As of 2026-10-14, GitHub's own auto-merge works in a private repo only on a paid plan ([automatically merging a pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/automatically-merging-a-pull-request)). Most owners keep `grok-bot-setup` private on GitHub Free.

Every bot signs in to GitHub as the owner, so GitHub can't show whether the owner or a bot merged a PR. A merge made with a workflow's own token shows up as `github-actions[bot]`, and it starts no other workflow except a manual dispatch ([triggering a workflow from a workflow](https://docs.github.com/en/actions/using-workflows/triggering-a-workflow#triggering-a-workflow-from-a-workflow)).

All of an account's bots share one computer, with its files and sign-ins ([approvals and security](https://docs.x.ai/grok-bot/approvals-security-and-privacy)). So the "apply" reply never made one bot safe from another. It slowed down every change, the safe ones too.

## Decision

- Every change still goes through a PR against `main`, and no bot pushes to `main`.
- The Auto-merge workflow merges a PR by itself when all of these hold:
  - The PR is open, isn't a draft, targets `main` and comes from a branch in the same repo. It has no `hold` label.
  - It changes only low-risk paths: notes and sources in `kb/`, `docs/`, `README.md`, and wording in `bots/*.md`. `kb/bundle/decisions/`, `kb/AGENTS.md`, `kb/tools/`, `kb/templates/` and `bots/setup.md` aren't low risk.
  - A bot file change adds no bot, routine or trigger, turns no routine on, adds no words about a power, drops no safety rule and changes at most 40 lines. Powers include merging, deleting, buying, sending email, posting publicly, approvals, secrets and connectors. A sync export is judged the same way.
  - Every check workflow that applies to the PR passed on its current head commit, with every job in it. A workflow whose path filter skips the PR, such as Board tests on a docs-only PR, isn't required.
  - It merges with `gh pr merge --squash --match-head-commit`, so a commit pushed after the checks ran can't slip in.
- Everything else waits for the owner. That covers `.github/`, `scripts/`, `board/`, `SETUP.md`, setup's own file, a new or renamed bot, a new routine or trigger, a new power and anything the workflow can't judge.
- The workflow starts through `workflow_run`, so GitHub runs it from `main`, and a PR can't change the rules that judge it. It reads the PR through the GitHub API as data, and never runs the PR's code. Its rules are in `scripts/auto_merge.py`, and a change to them waits for the owner.
- `main` is what the bots should have. setup applies a bot change from current `main`, never from an older commit.
  - A PR the workflow merged goes live at once. setup puts one line in the owner's morning brief.
  - A PR merged by the owner's account goes live at once if the owner asked setup for that change in setup's chat. The owner's request covers its whole scope: the design, the PR, the merge and the apply. Otherwise setup asks once whether to apply or revert it.
- "revert" replaces "skip". Leaving a merged change unapplied keeps `main` and the bots apart, so setup opens a PR that reverts it instead.
- Approval from another bot still never counts as the owner's approval.

## Why

- CI checks the actual diff every time. The owner's attention goes to the few changes that add a power or change the rules.
- Running from `main` and matching the head commit close the obvious ways around the check: a PR that edits its own rules, and a push after the checks passed.
- Applying `main` means an older PR never undoes a newer one, and weekly-sync compares the bots with the same text setup applies.

Options turned down:

- Keep 0001. The owner approved a stream of changes that no person needed to read, and the bots share a computer anyway.
- Let each bot merge its own PRs. A bot could merge before its checks finish, and every bot would need the same rules.
- Merge everything that passes CI. A PR that adds a trigger or a power would go live with nobody looking.
- GitHub's own auto-merge. It needs a paid plan in a private repo.

## Consequences

- KB notes, docs, sync exports and wording fixes merge and go live within minutes, with one line in the morning brief.
- The workflow reads words, not meaning. A power phrased in words it doesn't list could merge as low risk. The owner sees the change in the brief and can reply "revert". Add the missing word to `POWER_TERMS` in `scripts/auto_merge.py`.
- A merge by the workflow starts no workflow on `main`. When `main` moved after the checks ran, the merged result differs from what they tested, so the workflow reruns the checks on `main` itself. pr-watch reports a failed check on `main`.
- A bot that replaces its own instructions can raise an approval card, which expires after about 10 minutes when no one is in that chat. SETUP.md suggests a narrow Auto Review rule, so an automatic apply finishes on its own.
- Each check workflow that finishes on a PR starts one short Auto-merge run, so a push can start up to five. In a private repo, that uses Actions minutes.
