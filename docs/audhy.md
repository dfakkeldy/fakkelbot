# How audhy works

[audhy](../bots/audhy.md) is an optional bot for people who find starting, switching or coming back to things hard. That might be ADHD, autism, burnout or none of those. It doesn't ask, and you don't need a diagnosis. This page explains its rules, what the first version leaves out on purpose, and how to check it once you've created it.

## What it does

| You say | audhy |
| --- | --- |
| `dump: <anything>` | Adds your words to `inbox.md` exactly as written. It says "saved" only after reading the note back. If the save fails, it gives you the text back to copy. |
| `sort` | Takes one note and helps you decide what it is: a next step, waiting on someone, later, someday, not yours, or done with. The note leaves the inbox only after its new line reads back. You can stop after any note. |
| `stuck: <thing>` | Gives one small first step. If that's wrong, say smaller, help, later or drop it. |
| `restart`, or "where am I at" | Starts from today. It shows at most three items and says what it didn't look at. It never brings up how long you were away. |
| `skill` | Offers one short practice to try, with an easy way out. |
| `prefs` | Shows what it keeps about how you like help. You can change or remove any line. |
| "what do you keep" | Names its three files and shows the one you pick. |

## The rules that matter

Each rule names where its idea comes from. A book means audhy adapts an idea its authors describe, in its own words. It doesn't mean they tested a chat bot or reviewed audhy. "Design choice" means the rule is ours.

- **Keeping, sorting and acting are separate.** Keeping a thought never makes you organise it, and sorting happens only when you ask. (Allen, ch. 2.)
- **"Saved" means it read the note back.** If the save fails, you get your words back to copy. Sorting works the same way: a note leaves `inbox.md` only after its new line in `items.md` reads back, so a failed save can't lose it. (Design choice.)
- **A next step is something you could start now.** Making contact with the task counts, such as opening the file. If the step is still too big, it gets smaller. If the task is unclear, finding the missing fact can be the step. (Ramsay and Rostain, ch. 5; Tuckman, ch. 29 and 30.)
- **It asks once what's in the way, if at all.** Any answer is fine, including "don't know" or no answer. (Tuckman, ch. 6, separates planning, noticing and motivation. Asking only once is a design choice.)
- **You choose where to stop.** audhy never sets a timer or a quota. The books suggest different starting lengths, from ten minutes down to three, so audhy leaves it to you. (Ramsay and Rostain, ch. 5; Tuckman, ch. 29; Davis, ch. 10.)
- **Saying no changes the task, not the pressure.** A refused step leads to changing it, getting help, putting it off or dropping it. (Kemp and Mitchelson, ch. 5.)
- **A stuck item gets one change to try.** When you say an item keeps coming back, audhy asks where it stopped and suggests one change, then you see how it went next time. (Spradlin and Spradlin, on problem solving.)
- **Restarting is ordinary.** There's no catching up, no count of missed days and no need to explain. audhy doesn't notice gaps at all: it restarts only when you say `restart`. A real deadline is still stated plainly, with the date and the choices left, but never as a count of days. (Ramsay and Rostain, ch. 18; Davis, ch. 32 and 40.)
- **Rest doesn't have to be earned.** (Davis, ch. 24.)
- **No feeling name or rating needed.** "stop asking" ends the questions. (Wise suggests other ways to describe a feeling than naming it.)
- **Your preferences, not a default.** audhy doesn't assume you need quiet, or more input. It uses what you've said helps, and where. (Wise, on sensory needs; Kemp and Mitchelson.)
- **Short practices only, and only if you want one.** Pausing before a reply or decision, noticing one detail, or changing what's coming in. (Wise; Spradlin and Spradlin, on pausing before reacting.) It never offers the physical skills some DBT books include, such as cold water or holding the breath.
- **A short look-around isn't a full review.** It says what it covered and what it skipped. (Allen, ch. 8, describes the full weekly review.)
- **It sends nothing to other bots.** Unlike most bots, audhy sends no reports to liaison and no facts to librarian, because those end up in your morning brief and your repo. (Design choice.)

## What it leaves out on purpose

- **Reminders, check-ins and any message it starts.** A nudge you didn't ask for is another demand, and a missed one turns into guilt. If you want one, audhy helps you word it for your own calendar or phone.
- **Streaks, scores, counts of missed days and overdue lists.**
- **Mood logs, feeling ratings and anything that profiles you.**
- **Your calendar.** audhy can't see it and never guesses what's on it. scheduler reads it, if you have scheduler.
- **A weekly review ritual.** You can ask for a review. It's never scheduled.
- **Diagnosis, medication and health advice.**
- **Claims that it's like a person in the room.** It replies when you write, and says plainly that it can't see you or notice if you stop.
- **Copies of book exercises or worksheets.**

## It isn't therapy

audhy is practical help with tasks. It isn't therapy, diagnosis or crisis support, and it doesn't treat ADHD or anything else. If you talk about harming yourself or being in danger, it stops the task help and points you to emergency services or a crisis line, and to the people you've told it you'd turn to. It gives a phone number only if it's sure the number is right for where you are, and it goes back to tasks only when you ask. To tell it who they are, say something like "if things get bad I'd call Sam", and it saves that in `prefs.md`.

## Privacy

audhy keeps three plain files in `/workspace/audhy`: `inbox.md`, `items.md` and `prefs.md`. They're on the computer your bots share, so another bot could read them, and Grok Bot keeps the chat. Ask "what do you keep" to see the files, or ask audhy to change or clear them. Clearing empties the files, but not the chat or anything Grok Bot remembers. audhy is told to keep notes in its files rather than its memory, but that's an instruction, not a switch.

To share audhy as your own template, make the template from a fresh bot, as [bots/README.md](../bots/README.md#share-a-bot-as-your-own-template) says. A bot you've used may hold your notes in its memory.

## Try it

After fakkelbot creates audhy, try these in its chat. Each line is what to say, then what should happen.

1. `dump: vet about the cat's meds, what Sam said about Friday, gutters?` One line saying it's saved, as one note. The first time, three short lines about what it does follow. Then ask "what do you keep", pick the inbox, and check that it has your words exactly.
2. `stuck: tax forms` One small first step, with no timer. Reply `no`, and it offers other routes rather than the same step again.
3. `too much` A one-line reply, with no question and no new suggestion.
4. `sort` One note at a time, ending with "Another, or stop here?"
5. `restart` Today first, at most three items, and a line about what it didn't look at. No count of missed days.
6. `skill` One short practice, and no rating asked. Reply "that one doesn't help". It drops it and offers once to note that in `prefs.md`.
7. `remind me at 3` It says it can't message first and offers to word a reminder for your calendar or phone.
8. `prefs` It shows only what you told it.

If a reply breaks a rule, tell fakkelbot what happened and what you expected, and it'll change audhy's file with you.

## Open questions for a later version

- Should audhy offer a check-in you set up yourself, with limits you choose? That would need a routine, and an unwanted message can't be taken back.
- Could it read what's fixed today from scheduler, so "where am I at" can name the next appointment?
- How should a put-off item come back: only on restart, as now, or on a date you pick?
- Should `dump:` take voice notes, once someone has checked that Grok Bot handles them well?

## Sources

- David Allen, *Getting Things Done*, revised edition, 2015.
- J. Russell Ramsay and Anthony L. Rostain, *The Adult ADHD Tool Kit*, 2015.
- Ari Tuckman, *The ADHD Productivity Manual*, 2025.
- KC Davis, *How to Keep House While Drowning*, 2022.
- Jennifer Kemp and Monique Mitchelson, *The Neurodivergence Skills Workbook for Autism and ADHD*, 2024.
- Sonny Jane Wise, *The Neurodivergent Friendly Workbook of DBT Skills*, 2022.
- Scott E. Spradlin and Mariah Spradlin, *Dialectical Behavior Therapy Skills Workbook for Adult ADHD*, audiobook, 2026. Reviewed from a machine transcript of the audio.
