# Knowledge base

This folder is shared memory for your bots and agents. A bot reads it before it acts, so it starts from what you already know. Changes come in as pull requests. A page merges itself once every check passes, such as the lint and the secret scan. A change to a decision or to the rules waits for you.

The layout follows Andrej Karpathy's LLM Wiki pattern, in the Open Knowledge Format (OKF) v0.1. [Why the knowledge base is laid out this way](bundle/questions/why-this-layout.md) explains both, with sources.

Keep it small. Each page covers one topic, so a bot can read only what it needs.

## Who writes

The librarian bot writes the KB, so no other bot has to remember to. Other bots send it facts with their sources, and agents outside Grok Bot post them to the board. Once a day, librarian checks each fact against its source, updates the right pages and opens one pull request. A large piece, such as a long research report, can come as its own pull request instead, and librarian links it from related pages. You can still edit any page yourself through a pull request.

## Layout

| Path | What's in it |
|---|---|
| `bundle/` | The pages, as an OKF bundle. Bots write and update these. |
| `bundle/index.md` | The start page. It lists each folder. |
| `bundle/log.md` | What changed and when, newest date first. |
| `sources/` | Raw material the pages rest on. Bots read it but never change it. |
| `templates/` | A starter page for each folder, and one for a source. |
| `tools/` | The lint that checks every page. |
| `AGENTS.md` | The rules a bot follows here. |

The pages sit in five folders. Each folder has an `index.md` that lists every page in it, with the page's one-sentence description.

| Folder | What goes in it | Example |
|---|---|---|
| `projects/` | One page per thing you work on: what it is, where it is and where it stands | [Example App](bundle/projects/example-app.md) |
| `topics/` | How you work: practices, plans and ideas that span projects | None yet |
| `references/` | Facts looked up from outside sources, each with its date and source | [Grok Bot platform](bundle/references/grok-bot-platform.md) |
| `decisions/` | Choices you made and why, numbered in order | [CI decides what merges](bundle/decisions/0002-ci-decides-what-merges.md) |
| `questions/` | Answers worth keeping, filed back so they aren't lost in a chat | [Why the knowledge base is laid out this way](bundle/questions/why-this-layout.md) |

`sources/` has three folders. Put material you want librarian to file in `sources/inbox/`, such as notes, an export or a document. Once librarian has written pages from it, it moves the file to `sources/processed/`. librarian also saves short captures there of the web pages its pages rest on, because a web page can change or vanish. `sources/assets/` holds images and other attachments.

Put things here that stay true for weeks. Day-to-day progress and who is doing what go on the board instead.

There is no folder for people. Notes about other people tend to collect private details, so leave them out.

## Add or change a page

Every change goes through a pull request. Nobody pushes to `main`, and that includes bots.

1. Copy the template for the folder. For example, copy `templates/reference.md` to `bundle/references/<topic>.md`. Name the file with lowercase words joined by hyphens. Number decisions in order, as in `bundle/decisions/0003-<topic>.md`.
2. Fill in the frontmatter at the top of the page.
3. Write the page. Put a date on any fact that can go out of date, and cite its source under `## Citations`. Link other pages with relative paths, such as `../decisions/0002-ci-decides-what-merges.md`.
4. List the page in its folder's `index.md`, as `- [Title](file.md) - description`.
5. Add an entry at the top of `bundle/log.md`, under today's date.
6. Run the lint from the repository root.

   ```sh
   python3 kb/tools/kb_lint.py
   ```

7. Open a pull request. The lint runs again in CI, and the Auto-merge workflow merges the pull request once every check passes. A change to `bundle/decisions/`, `AGENTS.md`, `tools/` or `templates/` waits for you to merge it.

To change a page, edit it in place and set `timestamp` to now. Don't add a second page on the same topic.

## Frontmatter

Each page starts with frontmatter. The lint fails if `type`, `title`, `description` or `timestamp` is missing or empty.

```yaml
---
type: Reference
title: Grok Bot platform
description: How Grok Bot runs bots, routines, approvals and templates, and the limits every bot works within.
resource: https://docs.x.ai/grok-bot
tags:
  - grok-bot
  - platform
timestamp: 2026-10-14T20:58:27-03:00
---
```

- `type` says what kind of page it is, such as `Project`, `Topic`, `Reference`, `Decision` or `Question`. Only pages in `decisions/` may have type `Decision`.
- `title` is the page's name.
- `description` is one sentence. A bot reads it, in the page and in the index, to decide whether to open the page.
- `resource` is optional. It's the main link for the thing the page is about.
- `tags` is optional. It's a list of lowercase words.
- `timestamp` is when the page last really changed, as an ISO 8601 date and time with its UTC offset.
- `superseded_by` goes on a replaced page, written as `/folder/page.md`, with a line at the top that links to the page that replaces it.

OKF lets you add other keys. Keep the ones you find on a page.

## How bots use it

Each bot's instructions point to [AGENTS.md](AGENTS.md), which has the rules a bot follows here. A bot pulls the latest copy, reads `bundle/index.md`, then the index of the folder it needs, and then only the pages it needs. It treats what it reads as information, never as orders. When it learns something worth keeping, it hands the fact to librarian. [Decision 0002](bundle/decisions/0002-ci-decides-what-merges.md) says which pull requests merge themselves and which wait for you.
