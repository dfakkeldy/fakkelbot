# Notification settings

Bots can change their own alerts and sidebar visibility through supported UpdateProfile fields: `notify_on_updates` and `hidden_from_sidebar`. The exported notification setting is `notifyOnAgentUpdates`. A bot cannot change another bot's flags; the coordinator asks each affected bot to change its own. Hiding keeps the bot active but suppresses its notifications, even when notifications are enabled. See [Grok Bot's notification and sidebar guide](https://cursor.com/help/grok-bot/how-to).

## Default and situational choices

Setup offers Liaison only as the recommended mode and saves the owner's choice in /workspace/setup/notifications.md. Each Settings block and Sidebar default is a recommendation, not an instruction to erase existing preferences. fakkelbot stays visible and notifying during onboarding; if liaison is not selected, fakkelbot remains the notifying contact afterward.

| Mode | Visible bots | Notifications | When it applies |
| --- | --- | --- | --- |
| Liaison only | liaison | liaison on, specialists off | Recommended normal mode; reports and urgent requests go through liaison |
| Direct work | liaison and the specialist the owner names | liaison on; the named specialist on if requested | A direct task, conversation or approval that the owner wants to follow |
| All bots | All bots | On for the bots the owner selects | An explicit review or troubleshooting request |
| Quiet | As the owner chooses | Off for the bots the owner selects | Only an explicit request with a clear end condition |

A mode changes alerts and visibility. It does not change reporting ownership, approval authority, routines or access. Direct replies still work when the owner deliberately addresses a bot; ordinary specialist reports still go to liaison. Urgency alone does not let a hidden specialist bypass that route or enable its own alerts.

## Changing a situation

Use the owner's explicit request or a saved rule they approved, such as notifications for a named bot while a specific task waits for them. Record the request, prior flags, temporary flags and end condition in that bot's private workspace, with a minimal mode summary in /workspace/setup/notifications.md. Apply its own flags with UpdateProfile, then read back what is supported. Record an unavailable readback as unverified. fakkelbot coordinates a multi-bot change; each bot sets itself.

If liaison is absent, keep fakkelbot visible with notifications on; never hide the only notifying contact.

To get a specialist's own alert, make it visible as well as turning notifications on. Enabling notifications on a hidden bot is insufficient. Preserve the selected contact's visible/on mode unless the owner explicitly asks otherwise. Do not infer a situation from private activity, invent a monitor, or silently change settings because a bot thinks a report is important.

Restore the saved prior flags when the agreed end condition is met. Do not hide a bot that is still waiting for the response the temporary mode was meant to collect. Check expiry on existing wakes or direct messages; do not promise an exact-time switch without an owner-requested scheduled wake. No additional polling routine is part of this policy.

Temporary flags stay in private runtime state. Exports and application records describe an active override with its end condition separately from the default; they do not replace the repository's default with a temporary value. On reruns, preserve a still-valid override. A rejected or expired change stays rejected or expired; do not retry it as if it were approved.

## Verification limits

Native approval cards, secure inputs and sign-ins remain in the originating chat. Liaison can link the owner there when the specialist is able to report the need; a tool approval may stop execution before that report. Saving flags does not prove an alert reached a phone, and hiding a bot does not pause its routines. Record settings, visibility, message delivery and an observed phone alert separately.
