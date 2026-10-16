# Log

What changed in the knowledge base, newest first. Each entry sits under its date and starts with a bold word, such as **Ingest**, **Update**, **Answer**, **Tidy** or **Decision**. Add one entry for each change worth knowing about, not one for each run.

## 2026-10-15

- **Update**: Moved the pages to OKF v0.2. `generated` replaces `timestamp`, and each page's sources moved from a Citations list into its frontmatter, cited with footnotes. [0001](decisions/0001-every-change-goes-through-a-pr.md) is now `status: deprecated`. [Why the knowledge base is laid out this way](questions/why-this-layout.md) explains the v0.2 fields, from a new capture of the spec in `kb/sources/processed/`.
- **Layout**: Moved the notes into `kb/bundle/`, an Open Knowledge Format bundle with an index in every folder and this log. Added `topics/`, `questions/` and `kb/sources/`. [Why the knowledge base is laid out this way](questions/why-this-layout.md) explains the layout.
- **Answer**: Filed [Why the knowledge base is laid out this way](questions/why-this-layout.md), from Karpathy's LLM Wiki and the OKF spec. Their captures are in `kb/sources/processed/`.

## 2026-10-14

- **Decision**: Filed [0002. CI decides what merges](decisions/0002-ci-decides-what-merges.md), which replaces [0001. Every change goes through a PR](decisions/0001-every-change-goes-through-a-pr.md).
- **Ingest**: Started the knowledge base with [Grok Bot platform](references/grok-bot-platform.md), [Example App](projects/example-app.md) and [0001. Every change goes through a PR](decisions/0001-every-change-goes-through-a-pr.md).
