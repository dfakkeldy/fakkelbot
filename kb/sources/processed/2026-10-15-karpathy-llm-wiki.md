# LLM Wiki

- URL: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Retrieved: 2026-10-15
- Author: Andrej Karpathy, GitHub gist `llm-wiki.md`, created 2026-04-04
- Why it matters: the pattern this KB's layout follows

## What it says

Notes on the parts this KB relies on, not a copy.

- Three layers. Raw sources are curated and never change: the model reads them but doesn't edit them. The wiki is Markdown the model writes and maintains, such as summaries, entity and concept pages and comparisons. A schema file, such as `CLAUDE.md` or `AGENTS.md`, sets the wiki's structure, conventions and workflows.
- `index.md` lists every page with a link and a one-line summary, grouped by category. The model updates it on every ingest and reads it first to answer a question.
- `log.md` is in date order and only ever added to. It records ingests, queries and lint passes. Each entry starts with the same kind of prefix, a date, the operation and a title, so grep can list the latest ones.
- Ingest: read a new source, write a summary page, update `index.md` and the related pages, and add to `log.md`. One source can touch 10 to 15 pages.
- Query: find pages through `index.md`, read them and answer with citations. Good answers are saved as new pages, so what you explore adds up instead of disappearing into chat history.
- Lint: a regular health check for contradictions, stale claims, orphan pages, missing concept pages, missing cross-references and gaps a web search could fill.
- Tools it mentions: Obsidian for browsing (graph view, Web Clipper), qmd for local search once the index isn't enough, Marp, Dataview and git.
