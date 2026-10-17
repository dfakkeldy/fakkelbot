# How Audy works

[Audy](../bots/audy.md) is an optional bot for people who find starting, switching or coming back to things hard. That might be ADHD, autism, burnout or none of those, and you don't need a diagnosis. It keeps what's on your mind, gives you one small step at a time, reminds you when you ask, and lets you restart after any gap without catching up.

## What it does

| You say | Audy |
| --- | --- |
| Anything you need to remember, with or without `dump:` | Saves your words exactly, as an issue in your private GitHub repository, and says "saved" once GitHub has them. If it isn't sure something was a note, it saves it and says "undo" closes it. |
| `stuck: <thing>` | Gives one small first step. If that's wrong, say smaller, help, later or drop it. It can check back in after the time you choose. |
| "remind me at 3 to call the vet" | Creates a reminder routine for that time. A check-in after a work session works the same way. |
| `restart`, or "I'm back" | Starts from today with up to three notes, next steps first. No catching up. |
| `sort` | Takes one note and helps you decide what it is: a next step, waiting on someone, later, someday, done with or not yours. It offers a reminder for anything with a time. |
| `skill` | Offers one short practice when everything is too much. |
| `reminders` | Lists your reminders, so you can cancel any of them. |
| `prefs` | Shows what it keeps about how you like help. |

## What makes it work

Each idea names where it comes from. A book means Audy adapts an idea its authors describe, in its own words. It doesn't mean they tested a chat bot or reviewed Audy.

- **Getting a thought out of your head is one step.** Saving never makes you organise anything, and a saved note isn't a task until you sort it. (Allen, ch. 2.)
- **"Saved" means GitHub has your exact words.** Audy reads the issue back before it says so. Sorting adds your chosen step as a comment and never rewrites the note.
- **A next step is something you could start now.** Making contact with the task counts, such as opening the file. If the step is still too big, it gets smaller. If the task is unclear, finding the missing fact can be the step. (Ramsay and Rostain, ch. 5; Tuckman, ch. 29 and 30.)
- **Reminders go where the action happens.** A reminder at the right time, in your own words, does more than a long list. Audy sets the ones you ask for, offers one when a note has a time, and offers a check-in when you start something hard. (Tuckman, ch. 21.)
- **Saying no changes the task, not the pressure.** A refused step leads to changing it, getting help, putting it off or dropping it. (Kemp and Mitchelson, ch. 5.)
- **A stuck item gets one change to try.** When you say an item keeps coming back, Audy asks where it stopped and suggests one change. (Spradlin and Spradlin, on problem solving.)
- **Restarting is ordinary.** No catching up, no count of missed days and no need to explain. A real deadline is still stated plainly, with the date and the choices left. (Ramsay and Rostain, ch. 18; Davis, ch. 32 and 40.)
- **Rest doesn't have to be earned.** (Davis, ch. 24.)
- **Your preferences, not a default.** Audy uses what you've said helps, and where, such as "one question at a time" or "music helps when writing". (Wise; Kemp and Mitchelson.)
- **Short practices when you want one.** Noticing one detail, a slow breath, pausing before a reply, or changing what's coming in. A practical "what should I try first?" gets a first step instead. (Wise; Spradlin and Spradlin.)

## Reminders and check-ins

Audy turns each reminder or check-in into a Grok routine whose folder name starts with `reminder-`, and lists it in `/workspace/audy/reminders.md`. A one-time reminder retires itself after it runs. A repeating one stays until you say stop.

- Grok routines can start up to half an hour late, so use a phone alarm for anything that can't be.
- Each run uses a little of your plan's usage. Audy keeps at most 40 reminders at once, under Grok's limit of 50 routines per bot.
- Reminders belong to you, not to Audy's file, so weekly-sync leaves `reminder-` routines out of its comparison.

## Sharing with your other bots

Audy offers these when they fit, and remembers your answer:

- **Morning brief.** When you choose a next step for a later day, Audy sends it to liaison for your morning brief.
- **Calendar.** When you mention a hard deadline or an appointment, Audy can pass it to scheduler, which adds it to its list or suggests a slot.

## Where things are kept

Setup asks which private repository should hold your notes and writes it to `/workspace/audy/config.json`. A fresh install uses your `grok-bot-setup` repository, alongside your knowledge base and board. Audy's [capture tool](../capture/README.md) checks the repository is still private before every request.

- **Notes** are issues labelled `audy:capture` and `audy:inbox`, with your words in a code block, so an `@name` in a note notifies no one. Sorting changes the `audy:` label, adds your step as a comment, and closes the issue for done or not yours.
- **Preferences** are one issue titled "Audy preferences", labelled `audy:prefs`, with a working copy in `prefs.md`.
- **Reminders** are routines on Audy, listed in `reminders.md`.

| What Audy says | What it means |
| --- | --- |
| Saved | The issue exists and holds your exact words. |
| Kept on this computer, not in GitHub yet | GitHub wasn't reachable, no repository is set up, or the repository isn't private. Audy sends it the next time it syncs. |
| Not sure it reached GitHub | GitHub didn't confirm it. Audy checks before sending it again, so you never get duplicates. |

Ask "what do you keep" to see where everything is. Audy can close a note but not delete it. You can delete an issue yourself in GitHub.

To share Audy as your own template, make the template from a fresh bot, as [bots/README.md](../bots/README.md#share-a-bot-as-your-own-template) says, because a bot you've used may hold your notes in its memory.

## Earlier notes

If you used Audy before notes moved to GitHub, your notes are in `/workspace/audhy/inbox.md` and `items.md`. When you restart or ask about your notes, Audy offers to copy them to GitHub, each line as its own note. Copying twice doesn't make duplicates, and Audy empties an old file only after every line is saved and you say so.

## Try it

After fakkelbot creates Audy and setup has chosen your notes repository, try these in its chat.

1. `vet about the cat's meds, what Sam said about Friday, gutters?` One line saying it's saved, as one note. The first time, three short lines about what it does follow. Check the new issue has your words exactly.
2. `undo` It closes that note.
3. `stuck: tax forms` One small first step, and maybe an offer to check back. Reply `no`, and it offers other routes rather than the same step again.
4. `remind me in 10 minutes to stretch` It confirms the time. The reminder arrives, possibly a little late, and the routine is gone afterwards.
5. `sort` One note at a time. Pick a next step, then check the issue: your words are unchanged, the label is `audy:next`, and your step is a comment.
6. `restart` Today first, at most three notes, with the step you chose in step 5.
7. `one question at a time, please` Then `prefs`. It shows the line, and the "Audy preferences" issue has it too.
8. `too much` A one-line reply, with no question.

If a reply misses, tell fakkelbot what happened and what you expected, and it'll change Audy's file with you.

## Ideas for later

- Read what's fixed today from scheduler, so "where am I at" can name the next appointment.
- Take voice notes for captures, once someone has checked that Grok Bot handles them well.
- Offer to remove a note's local copy once GitHub has it.

## Sources

- David Allen, *Getting Things Done*, revised edition, 2015.
- J. Russell Ramsay and Anthony L. Rostain, *The Adult ADHD Tool Kit*, 2015.
- Ari Tuckman, *The ADHD Productivity Manual*, 2025.
- KC Davis, *How to Keep House While Drowning*, 2022.
- Jennifer Kemp and Monique Mitchelson, *The Neurodivergence Skills Workbook for Autism and ADHD*, 2024.
- Sonny Jane Wise, *The Neurodivergent Friendly Workbook of DBT Skills*, 2022.
- Scott E. Spradlin and Mariah Spradlin, *Dialectical Behavior Therapy Skills Workbook for Adult ADHD*, audiobook, 2026. Reviewed from a machine transcript of the audio.
