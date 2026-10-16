---
type: Question
title: Why the knowledge base is laid out this way
description: Where the KB's layout comes from, Karpathy's LLM Wiki and the Open Knowledge Format, and what each part is for.
resource: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
tags:
  - knowledge-base
  - okf
timestamp: 2026-10-15T21:50:05-03:00
---

# Why the knowledge base is laid out this way

## Question

Why does `kb/` have a bundle and a sources folder, an index in every folder, and a log?

## Answer

The layout follows Andrej Karpathy's LLM Wiki pattern [1], written in the Open Knowledge Format (OKF) [2].

The LLM Wiki has three layers [1]:

- Raw sources, which bots read but never change. Here they're in `kb/sources/`.
- The wiki, which bots write and keep up to date. Here it's `kb/bundle/`.
- A rules file that tells bots how to keep the wiki. Here it's `kb/AGENTS.md`.

It has two files for finding your way [1]:

- `index.md` lists every page with a one-line summary, so a bot reads it first and opens only what it needs. Here every folder has one, and the lint fails when a page isn't listed.
- `log.md` records what changed and when. OKF puts the newest date first, under `## YYYY-MM-DD` headings [2].

And it has three jobs [1]:

- Ingest: read a new source, then update the pages it touches, the index and the log. librarian's daily harvest does this.
- Query: answer a question from the pages. A good answer goes back in as a page in `questions/`, so it isn't lost in a chat. This page is one.
- Lint: look for contradictions, stale claims, pages nothing links to and missing links. The lint in `kb/tools/` checks the structure, and librarian's weekly tidy checks the facts.

OKF sets the page format [2]. A page is Markdown with frontmatter, and `type` is the only required key. `title`, `description`, `resource` and `tags` are recommended, and `index.md` and `log.md` are reserved names. This KB follows OKF v0.1, which dates a page with `timestamp` and lists its sources under a Citations heading. As of 2026-10-15 the spec is at v0.2, which moves both into the frontmatter, as `generated.at` and `sources` [2].

A few choices are this starter's own:

- There's no folder for people, because notes about people collect private details.
- There's no folder for status. Day-to-day progress goes on the board.
- Pages link with relative paths, which OKF allows [2]. On GitHub a link that starts with `/` goes to the repository root, not to `kb/bundle/` [3].
- Only pages in `decisions/` may have type `Decision`, so the Auto-merge workflow can hold every decision for the owner.

## Citations

- [1] [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f), Andrej Karpathy, GitHub gist, 2026-04-04. Checked 2026-10-15. [Capture](../../sources/processed/2026-10-15-karpathy-llm-wiki.md).
- [2] [Open Knowledge Format specification](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md), Google Cloud. Checked 2026-10-15. [Capture](../../sources/processed/2026-10-15-okf-spec.md).
- [3] [About READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes), GitHub Docs, section on relative links. Checked 2026-10-15.
