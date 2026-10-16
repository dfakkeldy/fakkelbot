---
type: Question
title: Why the knowledge base is laid out this way
description: Where the KB's layout comes from, Karpathy's LLM Wiki and the Open Knowledge Format, and what each part is for.
resource: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
tags: [knowledge-base, okf]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-15T22:20:40-03:00 }
sources:
  - id: llm-wiki
    resource: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
    title: LLM Wiki
    author: human:karpathy
    checked: 2026-10-15
    capture: ../../sources/processed/2026-10-15-karpathy-llm-wiki.md
  - id: okf-spec
    resource: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
    title: Open Knowledge Format specification, v0.2
    author: team:google-cloud
    checked: 2026-10-15
    capture: ../../sources/processed/2026-10-15-okf-spec-v0-2.md
  - id: github-readmes
    resource: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes
    title: About READMEs
    author: team:github-docs
    checked: 2026-10-15
---

# Why the knowledge base is laid out this way

## Question

Why does `kb/` have a bundle and a sources folder, an index in every folder, and a log?

## Answer

The layout follows Andrej Karpathy's LLM Wiki pattern[^llm-wiki], written in the Open Knowledge Format (OKF) v0.2[^okf-spec].

The LLM Wiki has three layers[^llm-wiki]:

- Raw sources, which bots read but never change. Here they're in `kb/sources/`.
- The wiki, which bots write and keep up to date. Here it's `kb/bundle/`.
- A rules file that tells bots how to keep the wiki. Here it's `kb/AGENTS.md`.

It has two files for finding your way[^llm-wiki]:

- `index.md` lists every page with a one-line summary, so a bot reads it first and opens only what it needs. Here every folder has one, and the lint fails when a page isn't listed.
- `log.md` records what changed and when. OKF puts the newest date first, under `## YYYY-MM-DD` headings[^okf-spec].

And it has three jobs[^llm-wiki]:

- Ingest: read a new source, then update the pages it touches, the index and the log. librarian's daily harvest does this.
- Query: answer a question from the pages. A good answer goes back in as a page in `questions/`, so it isn't lost in a chat. This page is one.
- Lint: look for contradictions, stale claims, pages nothing links to and missing links. The lint in `kb/tools/` checks the structure, and librarian's weekly tidy checks the facts.

OKF sets the page format[^okf-spec]. A page is Markdown with frontmatter, and `type` is the only required key. `title`, `description`, `resource` and `tags` are recommended, and `index.md` and `log.md` are reserved names. Version 0.2 puts what used to be in the page body into the frontmatter, where a bot can read it without parsing prose:

- `sources` lists what a page rests on. A footnote such as `[^okf-spec]` ties a single claim to one source by its `id`.
- `generated` says who wrote the current content and when. `verified` lists who checked it against its sources, and when.
- `status` marks a page `draft`, `stable` or `deprecated`, and `stale_after` says when a fact stops being current.

A few choices are this starter's own:

- There's no folder for people, because notes about people collect private details.
- There's no folder for status. Day-to-day progress goes on the board.
- Pages link with relative paths, which OKF allows[^okf-spec]. On GitHub a link that starts with `/` goes to the repository root, not to `kb/bundle/`[^github-readmes].
- Only pages in `decisions/` may have type `Decision`, so the Auto-merge workflow can hold every decision for the owner.
- Each source can carry two extra keys: `checked`, the date someone last checked it, and `capture`, the path of its copy in `kb/sources/processed/`. OKF lets a bundle add its own keys[^okf-spec].

[^llm-wiki]: [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f), Andrej Karpathy, GitHub gist, 2026-04-04.
[^okf-spec]: [Open Knowledge Format specification](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md), Google Cloud, v0.2.
[^github-readmes]: [About READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes), GitHub Docs, the section on relative links.
