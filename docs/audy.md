# How Audy works

[Audy](../bots/audy.md) is an optional bot for people who find starting, switching or coming back to things hard. That might be ADHD, autism, burnout or none of those. It doesn't ask, and you don't need a diagnosis. This page explains its rules, where your notes go, what the first version leaves out on purpose, and how to check it once you've created it.

## What it does

| You say | Audy |
| --- | --- |
| `dump: <anything>` | Keeps your words exactly as written, as an issue in the private GitHub repository you chose. It says "saved" only after reading the issue back. Otherwise it tells you the note is only on the bots' computer, or that it isn't sure GitHub has it. If the save fails, it gives you the text back to copy. |
| `sort` | Takes one note and helps you decide what it is: a next step, waiting on someone, later, someday, done with or not yours. You can stop after any note. |
| `stuck: <thing>` | Gives one small first step. If that's wrong, say smaller, help, later or drop it. |
| `restart`, or "where am I at" | Starts from today. It shows at most three notes and says what it didn't look at. It never brings up how long you were away. |
| `skill` | Offers one short practice to try, with an easy way out. |
| `prefs` | Shows what it keeps about how you like help. You can change or remove any line. |
| "what do you keep" | Says where your notes, preferences and any earlier notes are, and shows the one you pick. |

## The rules that matter

Each rule names where its idea comes from. A book means Audy adapts an idea its authors describe, in its own words. It doesn't mean they tested a chat bot or reviewed Audy. "Design choice" means the rule is ours.

- **Keeping, sorting and acting are separate.** Keeping a thought never makes you organise it, and sorting happens only when you ask. A kept note isn't a task until you sort it. (Allen, ch. 2.)
- **"Saved" means GitHub has your exact words.** Audy reads the issue back and checks it. A note that's only on the bots' computer, or that Audy isn't sure about, is called that. (Design choice.)
- **Sorting never rewrites your note.** Your original words stay on the issue. A step you choose is added as a comment underneath. (Design choice.)
- **A next step is something you could start now.** Making contact with the task counts, such as opening the file. If the step is still too big, it gets smaller. If the task is unclear, finding the missing fact can be the step. (Ramsay and Rostain, ch. 5; Tuckman, ch. 29 and 30.)
- **It asks once what's in the way, if at all.** Any answer is fine, including "both", "don't know" or no answer. (Tuckman, ch. 6, separates planning, noticing and motivation. Asking only once is a design choice.)
- **You choose where to stop.** Audy never sets a timer or a quota. The books suggest different starting lengths, from ten minutes down to three, so Audy leaves it to you. (Ramsay and Rostain, ch. 5; Tuckman, ch. 29; Davis, ch. 10.)
- **Saying no changes the task, not the pressure.** A refused step leads to changing it, getting help, putting it off or dropping it. (Kemp and Mitchelson, ch. 5.)
- **A stuck item gets one change to try.** When you say an item keeps coming back, Audy asks where it stopped and suggests one change, then you see how it went next time. (Spradlin and Spradlin, on problem solving.)
- **Restarting is ordinary.** There's no catching up, no count of missed days and no need to explain. Audy doesn't notice gaps at all: it restarts only when you say `restart`. A real deadline is still stated plainly, with the date and the choices left, without counting days. (Ramsay and Rostain, ch. 18; Davis, ch. 32 and 40.)
- **Rest doesn't have to be earned.** (Davis, ch. 24.)
- **No feeling name or rating needed.** "stop asking" ends the questions. (Wise suggests other ways to describe a feeling than naming it.)
- **Your preferences, not a default.** Audy doesn't assume you need quiet, or more input. It uses what you've said helps, and where. (Wise, on sensory needs; Kemp and Mitchelson.)
- **Short practices only, and only if you ask for help coping.** Pausing before a reply or decision, noticing one detail, or changing what's coming in. A practical "what should I try first?" gets a first step instead. (Wise; Spradlin and Spradlin, on pausing before reacting.) It never offers the physical skills some DBT books include, such as cold water or holding the breath.
- **A short look-around isn't a full review.** It says what it covered and what it skipped. (Allen, ch. 8, describes the full weekly review.)
- **It sends nothing to other bots.** Unlike most bots, Audy sends no reports to liaison and no facts to librarian, because those end up in your morning brief and knowledge base. Your notes go only to the repository you chose for them. (Design choice.)

## What it leaves out on purpose

- **Reminders, check-ins and any message it starts.** A nudge you didn't ask for is another demand, and a missed one turns into guilt. If you want one, Audy helps you word it for your own calendar or phone.
- **Streaks, scores, counts of missed days and overdue lists.**
- **Mood logs, feeling ratings and anything that profiles you.**
- **Your calendar.** Audy can't see it and never guesses what's on it. scheduler reads it, if you have scheduler.
- **A weekly review ritual.** You can ask for a review. It's never scheduled.
- **Deleting notes.** Audy can close a note in GitHub, but not delete it. See Privacy.
- **Diagnosis, medication and health advice.**
- **Claims that it's like a person in the room.** It replies when you write, and says plainly that it can't see you or notice if you stop.
- **Copies of book exercises or worksheets.**

## It isn't therapy

Audy is practical help with tasks. It isn't therapy, diagnosis or crisis support, and it doesn't treat ADHD or anything else. If you talk about harming yourself or being in danger, it stops the task help and points you to emergency services or a crisis line, and to the people you've told it you'd turn to. It gives a phone number only if it's sure the number is right for where you are, and it goes back to tasks only when you ask. To tell it who they are, say something like "if things get bad I'd call Sam", and it saves that in `prefs.md`.

## Where your notes go

Setup asks which private repository should hold your notes and writes it to `/workspace/audy/config.json`. A fresh install uses your `grok-bot-setup` repository. Audy's [capture tool](../capture/README.md) checks that the repository is still private every time it talks to GitHub, and sends nothing if it isn't.

Each note becomes one issue, labelled `audy:capture` and `audy:inbox`. Your words sit in a code block, exactly as written, so an `@name` in a note doesn't notify anyone. Sorting changes the `audy:` label, adds your chosen step as a comment, and closes the issue for done or not yours.

| What Audy says | What it means |
| --- | --- |
| Saved to GitHub | The issue exists and holds your exact words. |
| Kept on this computer, not in GitHub yet | GitHub wasn't reachable, no repository is set up, or the repository isn't private. Audy sends it the next time it syncs. |
| Not sure it reached GitHub | GitHub didn't confirm it. Audy checks the repository, and never sends it again by itself. If a complete check later finds nothing, it can send it again when you ask. |

## Privacy

Audy keeps:

- your notes, as issues in your private repository, and a private copy of each, with whether GitHub has it, in `/workspace/audy/records`;
- `prefs.md`, what you told it about how you like help, which never goes to GitHub;
- earlier notes in `/workspace/audhy`, if you used it before notes moved to GitHub.

Anyone you've given access to the repository can read your notes there. The files are on the computer your bots share, so another bot could read them, and Grok Bot keeps the chat. Ask "what do you keep" to see where everything is.

Audy can close a note but can't delete it, from GitHub or from its own copies. You can delete an issue yourself in GitHub, but other copies may remain, and Audy can't check them. Clearing your preferences empties `prefs.md`, and never touches your notes. Nothing Audy clears removes the chat or anything Grok Bot remembers. Audy is told to keep notes in its files and GitHub rather than its memory, but that's an instruction, not a switch.

To share Audy as your own template, make the template from a fresh bot, as [bots/README.md](../bots/README.md#share-a-bot-as-your-own-template) says. A bot you've used may hold your notes in its memory.

## Earlier notes

If you used Audy before notes moved to GitHub, your notes are in `/workspace/audhy/inbox.md` and `items.md`. Audy doesn't change them. When you restart or ask about your notes, it offers to copy them to GitHub. Each non-empty line becomes its own note, word for word, in your inbox, so you can sort it again. Copying twice doesn't make duplicates. Audy offers to empty an old file only after every line in it is saved, and empties it only if you say so.

## Try it

After fakkelbot creates Audy and setup has chosen your notes repository, try these in its chat. Each line is what to say, then what should happen.

1. `dump: vet about the cat's meds, what Sam said about Friday, gutters?` One line saying it's saved to GitHub, as one note. The first time, three short lines about what it does follow. Open the repository's Issues and check the new issue has your words exactly.
2. `stuck: tax forms` One small first step, with no timer. Reply `no`, and it offers other routes rather than the same step again.
3. `too much` A one-line reply, with no question and no new suggestion.
4. `sort` One note at a time, ending with "Another, or stop here?" Pick a next step, then check the issue: your original words are unchanged, the label is `audy:next`, and your step is a comment.
5. `restart` Today first, at most three notes, and a line about what it didn't look at. No count of missed days. The note you sorted in step 4 shows the step you chose, not a guess.
6. `skill` One short practice, and no rating asked. Reply "that one doesn't help". It drops it and offers once to note that in `prefs.md`.
7. `remind me at 3` It says it can't message first and offers to word a reminder for your calendar or phone.
8. `prefs` It shows only what you told it.
9. "what do you keep" It names the repository, its local copies and `prefs.md`, and says it can close notes but not delete them.

If a reply breaks a rule, tell fakkelbot what happened and what you expected, and it'll change Audy's file with you.

## Open questions for a later version

- Should Audy offer a check-in you set up yourself, with limits you choose? That would need a routine, and an unwanted message can't be taken back.
- Could it read what's fixed today from scheduler, so "where am I at" can name the next appointment?
- How should a put-off item come back: only on restart, as now, or on a date you pick?
- Should `dump:` take voice notes, once someone has checked that Grok Bot handles them well?
- Should Audy offer to remove a note's local copy once GitHub has it?

## Sources

- David Allen, *Getting Things Done*, revised edition, 2015.
- J. Russell Ramsay and Anthony L. Rostain, *The Adult ADHD Tool Kit*, 2015.
- Ari Tuckman, *The ADHD Productivity Manual*, 2025.
- KC Davis, *How to Keep House While Drowning*, 2022.
- Jennifer Kemp and Monique Mitchelson, *The Neurodivergence Skills Workbook for Autism and ADHD*, 2024.
- Sonny Jane Wise, *The Neurodivergent Friendly Workbook of DBT Skills*, 2022.
- Scott E. Spradlin and Mariah Spradlin, *Dialectical Behavior Therapy Skills Workbook for Adult ADHD*, audiobook, 2026. Reviewed from a machine transcript of the audio.

Waiting and later notes retain their verified clarification details, including a chosen person or date. Restart reads those details and checks whether dates still apply.
