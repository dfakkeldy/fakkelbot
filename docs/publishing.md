# Publish a starter for other people

Follow these steps when you maintain a copy of this starter and want other people to install it. Your own `grok-bot-setup` repo stays private. This is only for a copy you mean to share.

Other people can install a starter only when three things hold:

- Its repo is public, so fakkelbot can clone it without signing in. fakkelbot clones it before the owner has signed in to GitHub.
- Its repo is marked as a template, because SETUP.md step 3 runs `gh repo create --template` on it.
- Its README tells people how to add fakkelbot.

## Checklist

1. **Check for personal details.** Run the leak check over the whole history with your own denylist, as [scripts/README.md](../scripts/README.md#leak_checkpy) says. Allow only what you mean to publish, such as your name in `LICENSE`. Remember that PR titles, PR descriptions and commit messages become public too. Fixing an old commit means rewriting history, so decide before you publish.
2. **Point the starter at your repo.** If your copy isn't the original, replace the original's `<user>/<repo>` with yours in three places: the clone command in [bots/fakkelbot.md](../bots/fakkelbot.md), the `--template` command in step 3 of [SETUP.md](../SETUP.md), and "Install without the Grok Bot template" in [README.md](../README.md).
3. **Make the repo public and a template.** In the repo's Settings, change its visibility to public and tick Template repository. With `gh`:

   ```sh
   gh repo edit <user>/<repo> --visibility public --accept-visibility-change-consequences
   gh repo edit <user>/<repo> --template
   ```

4. **Check it from outside.** Sign out of GitHub, or use another machine, and run the clone that fakkelbot runs. Check that the repo reports as a template.

   ```sh
   git clone --depth 1 https://github.com/<user>/<repo> /tmp/starter-check
   gh api repos/<user>/<repo> --jq '{private, is_template}'
   ```

5. **Make fakkelbot's Grok Bot template.** Follow "Share a bot as your own template" in [bots/README.md](../bots/README.md#share-a-bot-as-your-own-template): create a fresh bot named fakkelbot from `bots/fakkelbot.md`, create the template from it, add it from a second Grok Bot account, and check that nothing personal came across.
6. **Put the template link in the README.** Replace the first Quick start step with this, using your link:

   ```markdown
   1. Add fakkelbot from its Grok Bot template: <template link>.
   ```

   Keep "Install without the Grok Bot template" for people who'd rather paste the instructions themselves.
7. **Test a full install** from the second Grok Bot account and a second GitHub account: "set me up", every question, the bots, the board and one PR that merges itself. A PR in the copy should show the Auto-merge workflow running after its checks.

## Notes

- A copy made from the template starts with its own history, so your old commits and PRs don't come with it. Your repo's own history is what step 1 checks.
- The Auto-merge workflow comes with every copy. In a private copy on GitHub Free it uses Actions minutes: about one short run for each check workflow that finishes on a PR.
