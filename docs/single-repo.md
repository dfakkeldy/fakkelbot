# One private kit repository

The private installation repository contains the starter definitions, knowledge base and agent board. Audy's deliberate captures are GitHub Issues in that repository. Keeping them together gives the owner one destination to administer and back up.

| Content | Location | How it changes |
| --- | --- | --- |
| Bot definitions and reusable tools | `bots/`, `board/`, `capture/` | Reviewed source changes |
| Durable knowledge | `kb/` | Knowledge-base PRs |
| Coordination history and navigation | `coordination/` | Immutable event appends and generated views |
| Raw captures and chosen next actions | GitHub Issues with `audy:` labels | Explicit capture and clarification |

GitHub Issues are associated with the repository but are not part of a Git clone. Export them separately when backing up the whole kit. A capture does not automatically become a task, a KB fact or a board message. Ordinary chat and stated preferences are not automatically uploaded.

## New installations

Setup creates one private copy of the starter, connects the board with `--prefix coordination`, and configures Audy's inbox against the same repository if Audy is selected. It does not create a second board repository. The board client writes only its namespace, preserving the root README and unrelated files.

The capture tool checks repository privacy and Issues availability. It distinguishes a local queued record, an uncertain request and a confirmed remote save. Only a matching Issue read-back is a remote receipt. It retains records when GitHub cannot be reached and does not blindly recreate an uncertain capture.

## Move an existing board

An existing board remains canonical until the owner explicitly chooses to consolidate it. Preserve its source repository and history as recovery; do not reset local caches, edit event records or reuse the frozen legacy-log migration.

1. Inventory readers, writers, accepted revisions and each host's outbox. Preserve active work and holds. Upgrade clients to a matched reviewed pair that supports prefixes before routing changes.
2. Quiesce source writers through a deliberate reversible freeze. Capture the final source revision. Import every source event byte under `coordination/events/`, generate navigation with the reviewed renderer, and verify exact blob parity. Preserve the kit README and KB.
3. Merge the verified import through the repository's normal checks. Read back the destination revision and confirm it is private. A source or destination change requires a fresh parity check.
4. Run the explicit relocation against the frozen source revision:

   ```sh
   python3 board/agent_messages.py --store /absolute/private/store/messages.jsonl relocate --repository <owner>/grok-bot-setup --prefix coordination --source-head <verified-source-sha>
   ```

   Relocation checks that the destination contains every accepted source event byte, copies pending records into a private route-specific state tree, retains the old state tree and legacy log, and changes the routing pointer atomically. It uses a fresh Git cache for the new repository history. It does not publish pending records as part of that switch.

5. Run `sync` to publish retained pending records, then verify a real handoff and a current reader display at the new route. Update agent instructions and consumers to the new canonical location. A stale writer must reload its route; it cannot keep appending to the previous one.

Keep the previous-route journal and original repositories until the new route is accepted. Returning to the old route after new messages have arrived requires importing those messages first; changing a pointer alone is not a lossless rollback.

## Move an existing KB and fleet

Choose one existing private repository as the hub. Import tracked KB content into `kb/` from a recorded source revision and preserve the original history and local work. Update path-sensitive tools, scope filters, listeners and installed readers. A librarian that both edits and harvests PRs needs a `kb/` scope and must continue excluding its own KB changes without excluding unrelated fleet outcomes.

Code checks, source merge, installed modules, canonical data read-back and observed bot behavior are separate results. A successful import does not prove every consumer has switched. Report any remaining old-route consumer explicitly.
