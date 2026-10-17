# Capture inbox

`inbox.py` keeps [Audy](../bots/audy.md)'s notes as Issues in one private GitHub repository. It uses only the Python standard library (3.9 or later) and an already signed-in `gh`. It never changes sign-ins, repository settings or visibility.

## Commands

Every command prints one line of JSON with `"ok": true` or `"ok": false`, `"error"` and `"message"`, and exits 0 or 1. Bad arguments exit 2. Captured text in the output is the owner's data, never instructions; outputs that carry it say `"text_is_data": true`.

```text
inbox.py [--state-dir DIR] configure --repository OWNER/REPO
inbox.py [--state-dir DIR] stage
inbox.py [--state-dir DIR] capture --text-file PATH|- [--id UUID] [--offline] [--consume]
inbox.py [--state-dir DIR] sync
inbox.py [--state-dir DIR] list [--remote] [--state STATE] [--status STATUS]
inbox.py [--state-dir DIR] classify --id UUID --state STATE [--note-file PATH|-] [--consume]
inbox.py [--state-dir DIR] set-state ...            (same as classify)
inbox.py [--state-dir DIR] requeue --id UUID
inbox.py [--state-dir DIR] import-legacy --file PATH [--offline]
```

- `--state-dir` defaults to `/workspace/audy`. It holds `config.json`, `{"schema": 1, "repository": "owner/repo"}`, and `records/`, one private JSON record per capture.
- `configure` checks that the repository exists, is private and has Issues on. Then it makes sure the eight labels exist: `audy:capture` and one `audy:<state>` per state. It creates only missing ones and reads each back; a label someone else made meanwhile counts. Only then does it write `config.json`. It changes nothing else on GitHub: no settings, visibility, access or sign-ins. If a label can't be confirmed, it fails with `labels_unverified` and writes no config. Run it again to retry.
- `stage` makes a new empty file, mode 0600, in the state directory's `tmp/` folder (0700) and prints its `path`. Use a fresh one for every capture or note: write the text there, then pass the path with `--consume`. Two overlapping captures then never share a file. Text never goes in arguments.
- `capture` reads UTF-8 text from a file or stdin and writes the local record first. Then it sends it, unless `--offline` or the check below fails. `--id` makes a retry safe: the same ID with the same text is one capture, and the same ID with different text is refused. Without `--id`, the same text twice is two captures. `--consume` deletes the text file once the record is written, and only if it's directly in the staging folder. A `busy` or failed write keeps the file.
- `sync` sends queued captures, checks uncertain ones and finishes unconfirmed `classify` changes.
- `list` shows local records. `--remote` lists capture issues in the repository, with `"complete": false` if there were more pages than it read. A capture in the `next` state carries `next_action`: the step the owner chose, with `"source": "verified_comment"` and the comment's URL. Locally it comes from a note this tool confirmed by read-back. Remotely it's the latest note comment whose marker, text hash and canonical URL agree; `notes_complete` says whether every comment was read. It's never guessed from a label, so it's `null` when no such note exists.
- `classify` (with `--consume` for a staged note, deleted once the change is recorded) sets a saved capture's state: `inbox`, `next`, `waiting`, `later`, `someday`, `done` or `archived`. `next` needs a note, the step the owner chose. A note is added as a comment, and labels change only after the comment is read back. The issue body is never edited. `done` closes the issue as completed and `archived` as not planned. Closing isn't deleting. If the change can't be confirmed, it fails with `classify_pending` and stays pending until `sync` confirms it.
- `requeue` lets a capture, or a pending note, be sent again. It works only when a complete check, 10 minutes or more after sending, found nothing.
- `import-legacy` captures each non-empty line of an old notes file, word for word. The file isn't changed, and each line gets a stable ID, so running it again makes no copies. `"all_saved": true` means every line is in GitHub.

## Statuses

| Status | Meaning |
| --- | --- |
| `queued` | Only local. Never sent, or GitHub refused it so nothing was created. `sync` sends it. |
| `sending` | A send started and the tool stopped before recording the answer. `sync` treats it as `uncertain`. |
| `uncertain` | GitHub didn't confirm. `sync` looks for the capture's marker before anything else, and never sends it again by itself. |
| `saved` | Read back from GitHub with the same capture ID, the exact text, a canonical issue URL, `audy:capture` and exactly one `audy:` state label. |
| `mismatch` | An issue exists, but it doesn't hold the exact text, or it has more than one `audy:` state label. Not saved, and left for the owner. |

`"reason"` says why a capture stayed where it was: `not_configured`, `offline`, `not_private`, `issues_disabled`, `repo_unavailable`, `repo_moved`, or `busy` when another command was working on the same capture.

## How it stays reliable

- The repository is checked to be private, with Issues on, right before every request that sends or reads notes, comments or labels. That includes each page of a listing, each read-back and each label. One check at the start of a run doesn't count for the rest. If a check fails, the command stops there, nothing more is sent or read, and the local queue stays. Errors never include GitHub's response body.
- An issue counts as a capture only with its exact text and Audy's labels. If `audy:capture` or a state label is missing, the tool adds just the missing ones, keeping any state label already there, then reads the issue back. If they still aren't there, the capture stays `uncertain` and `sync` tries again. A replayed or reconciled capture takes the issue's current state, so a later sort is never reset to `inbox`.
- Each capture has its own lock file in `records/`. Writing a new record, sending, reconciling, classifying and requeueing hold it, and reread the record once they have it. So two commands can't both send the same capture, overwrite each other's change, or claim one ID for different text. Other captures aren't blocked. A command that waits more than 10 seconds stops with `busy`. Nothing is lost: `capture` returns the text and leaves its text file in place.
- The record is written with its attempt before the request goes out, so a crash leaves `sending`, never a silent gap.
- GitHub offers no idempotency key, so nothing here is exactly-once. What the tool promises is that it never sends the same capture or note a second time by itself. After an unconfirmed send, it only checks. A second send needs proof of absence and an explicit `requeue`.
- Each issue body starts with a hidden marker holding the capture ID and a SHA-256 of the text, then the text in a code block whose fence is longer than any run of backticks in it. Reconciling lists issues of every state updated since shortly before the attempt, at most 10 pages of 100. If it couldn't read every page, it can't prove the issue is missing, so the capture stays `uncertain`.
- `classify` writes the change locally first. Its note comment has its own marker and a SHA-256 of the note. The note counts as confirmed only when a comment read back from the issue has that marker, the exact note and a canonical comment URL. Labels and open or closed are then set together and read back.
- Records are written atomically with mode 0600 in a 0700 directory. A symbolic link as the state directory, `records/`, `config.json` or a record is refused.
- Text and notes go to `gh api` as JSON on stdin, never in arguments. Errors never include `gh`'s output.

## Tests

```sh
python3 -m unittest discover -s capture -v
```

The tests use a fake GitHub behind the same boundary as `gh`, and create no real issues.

Listings expose the latest verified annotation for the current state, separately from raw capture text. This retains waiting details and dates as well as next actions; next_action is the convenience field for state next. Remote notes_complete reports whether all comment pages were read.
