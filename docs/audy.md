# How Audy works

[Audy](../bots/audy.md) is an optional assistant for getting things done. It captures what's on your mind, remembers your commitments, picks what matters today and says why, helps you start, and keeps what you see small while keeping the rest safe. It suits anyone who finds starting, switching or coming back to things hard, with or without an ADHD diagnosis.

If you add Audy, it becomes the bot that talks to you, and the others work behind it:

| Bot | Owns | What it sends Audy |
| --- | --- | --- |
| liaison | The back office: every other bot's reports, and the board | A morning digest at 06:50, and urgent items at once |
| scheduler, if you have it | Your time: calendar, appointments and hard deadlines | A day note at 06:45, a look-ahead at 20:15, the week ahead on Sundays at 20:15, and leave-by times |

Numbered calendar slots still arrive in scheduler's own chat, because only your "yes 2" there can write your calendar. A relayed "yes" or "apply" never counts as your approval; Audy tells you where to answer. Without Audy, liaison and scheduler talk to you directly, as before.

liaison and scheduler send their notes about 40 minutes before Audy's messages, because routines can start up to half an hour late. If one hasn't arrived, Audy goes ahead without it and says so. Audy keeps what it receives in `/workspace/audy/in/` and `day.md` until a message has used it.

## Your day

On its first run, Audy asks when your day starts, when you work and when you do your best work. It uses those hours from then on, and offers to move its routines if they don't fit.

| When | Audy |
| --- | --- |
| 07:30 weekdays, 09:00 weekends | Today: fixed events, one must-do and up to two more, each with a reason, decisions bots are waiting on, and how many things are parked |
| During work | Quiet, except due-day items, leave-by reminders and urgent items |
| Early evening | Light, time-sensitive things only |
| 21:00, Sunday to Thursday | Tonight: the one thing worth your evening, with its first step |
| Weekends | One big thing on Saturday, and a light Sunday |

## Choosing what matters

- **Ranking:** hard dates and what breaks if they're missed come first, then what unblocks other things, then what fits your time, then what you said matters. "This pays you", such as a refund, counts. Your "this matters" overrides the rest.
- **Reasons:** every pick comes with a few words, such as "due Friday, 10 minutes".
- **Escalating deadlines:** a hard deadline comes back from its latest sensible start, then weekly, every second day in its last week, and daily in its last three days. Each time you see what's done, what's left, the easiest next action, and an offer to do the prep.
- **Personal targets:** anything that takes more than about an hour gets an earlier target with checkpoints.
- **Collisions:** a new commitment that competes with a hard date this week gets flagged.

## Starting and staying on top

- **Stuck:** Audy first looks for an unanswered question blocking the task and splits it off, so the rest can go ahead. Otherwise it gives a first step, or asks once whether the task is unclear, too big, missing something or not now.
- **"Later" gets "later when?"** and becomes a reminder.
- **Check-ins:** offered for things you've been stuck on, and dropped if you ignore them.
- **Stale items:** after a week with no movement, Audy offers "someday" or an easy way back in, at most two at a time.
- **Book early:** scheduler offers the earliest slots first and flags afternoon ones, because waiting for an afternoon appointment can eat the day. When something has to be later, Audy reminds you at the leave-by time.

## Reminders

Audy creates a Grok routine for each reminder or check-in, with a folder name starting `reminder-`, and lists it in `/workspace/audy/reminders.md`. One-time reminders retire themselves. Grok routines can start up to half an hour late, so use a phone alarm for anything that can't be. Audy keeps at most 40, under Grok's limit of 50 routines per bot, and weekly-sync leaves `reminder-` routines out of the bot's file.

## Notes and storage

Audy's exact capture, sorting and preferences steps are in [capture/AUDY.md](../capture/AUDY.md). It reads that file when it needs it, which keeps its instructions short. The [capture tool](../capture/README.md) checks that your repository is still private before every request.

- **Notes** are issues labelled `audy:capture` in your private repo. "Saved" means the issue holds your exact words. "Undo" closes a note; nothing is deleted.
- **Preferences** are one "Audy preferences" issue, with a working copy in `prefs.md`.

To share Audy as your own template, make the template from a fresh bot, as [bots/README.md](../bots/README.md#share-a-bot-as-your-own-template) says, because a bot you've used may hold your notes in its memory.

## Try it

1. Send a task with a date, without `dump:`. It's saved, and it says the date back.
2. "remind me in 10 minutes to stretch". It confirms the time, the reminder arrives, and the routine is gone afterwards.
3. "I'm stuck on the report". You get a first step, or one question.
4. "what should I do today?". You get one must-do and up to two more, each with a reason.
5. "undo" right after a capture closes that note.

## Sources

- David Allen, *Getting Things Done*, revised edition, 2015.
- J. Russell Ramsay and Anthony L. Rostain, *The Adult ADHD Tool Kit*, 2015.
- Ari Tuckman, *The ADHD Productivity Manual*, 2025.
- KC Davis, *How to Keep House While Drowning*, 2022.
- Jennifer Kemp and Monique Mitchelson, *The Neurodivergence Skills Workbook for Autism and ADHD*, 2024.
- Sonny Jane Wise, *The Neurodivergent Friendly Workbook of DBT Skills*, 2022.
- Tina Mathams, *ADHD Money*.
- Scott E. Spradlin and Mariah Spradlin, *Dialectical Behavior Therapy Skills Workbook for Adult ADHD*, audiobook, 2026.
