---
type: Decision
title: Every change goes through a PR
description: Replaced by 0002. Changes to bots/ and kb/ went through a pull request, and live bots changed only after the owner replied "apply".
tags:
  - pull-requests
superseded_by: /decisions/0002-ci-decides-what-merges.md
timestamp: 2026-10-15T07:04:54-03:00
---

# 0001. Every change goes through a PR

Accepted on 2026-10-14. Replaced on 2026-10-14 by [0002. CI decides what merges](0002-ci-decides-what-merges.md), which lets low-risk PRs merge themselves and go live.

## Context

Bots write to this repository. Their instructions are in `bots/`, and their shared memory is in `kb/`. A change to either one changes what every bot does next.

As of 2026-10-14, all of an account's bots share one computer, with the same files and sign-ins. The Grok Bot docs say not to use separate bots as a security boundary ([approvals and security](https://docs.x.ai/grok-bot/approvals-security-and-privacy)). One bot that is misled can change files that every other bot reads.

Bots read outside text all the time, such as email, web pages, pull requests and each other's messages. Some of that text is written to trick a bot into acting.

An approval card raised by a routine or by another bot expires after about 10 minutes, and the action doesn't run ([same page](https://docs.x.ai/grok-bot/approvals-security-and-privacy)). A routine can't wait for the owner to approve a change.

## Decision

- Every change to `bots/` or `kb/` goes through a pull request against `main`. No bot pushes to `main`.
- Most KB changes come from the librarian bot, in at most one pull request a day. Other bots hand it facts instead of editing notes. A large piece, such as a research report, can come as its own pull request.
- The owner reviews and merges. No bot merges a pull request that changes `bots/` or `kb/`.
- Merging a change to `bots/` doesn't change a live bot. The setup bot lists the changes and waits. It sends each affected bot its new text only after the owner replies "apply" in the setup bot's own chat.
- Approval from another bot never counts as the owner's approval.
- Once a week, the setup bot compares the live bots with `bots/`. If they differ, it opens a pull request on a branch named `sync/export-YYYY-MM-DD`, so the owner can see the drift.

## Why

- A pull request shows the exact change before it takes effect. The owner can read it, ask for changes or close it.
- Git keeps every version. A bad change comes out with `git revert`, followed by another "apply" for bot changes.
- The lint and the secret scan run on every pull request. A broken note or a leaked token fails CI before it reaches `main`.
- A merge alone never rewrites a live bot. The owner says "apply" as a message in a live chat, so nothing expires while the setup bot waits.
- One writer for the KB means facts get recorded even when the bot that found them forgets, and the owner reviews one pull request a day instead of many.

Options turned down:

- Bots push straight to `main`. It's faster, but one misled bot could rewrite the rules for every other bot with nobody looking.
- Every merged change to `bots/` goes live at once. It's simpler, but a merge made for one reason would change a live bot without the owner asking for it.
- Every bot writes its own KB notes. Bots forget, and the owner would review a stream of small pull requests.

## Consequences

- Changes take longer. The owner has to review, merge and, for bot changes, reply "apply".
- A routine that wants to change the KB hands the fact to librarian or opens a pull request, then moves on. It never waits for an answer.
- Live bots can drift from `bots/` when someone edits a bot in the app. The weekly sync pull request shows the drift.
