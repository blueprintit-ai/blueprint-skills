---
name: bp-update
description: "Pull the latest Shop OS skills from Blueprint IT. Runs the update command, then tells you to restart Claude Code. TRIGGERS: /bp-update, update skills, update shop os, update my skills, get latest skills, skills are outdated."
---

# Shop OS Skills Updater

Pull the latest skills from Blueprint IT without re-running the full installer. Does not touch your vault, license, or settings.

## Steps

1. Run the update command:

```bash
npx -y --package=@blueprintit/shop-os-install shop-os-update
```

2. Wait for it to complete. It prints "Update complete." when done.

3. Tell the user:

> Skills updated. **Restart Claude Code now** to load the new versions. Your vault and license are unchanged.

## If the command fails

- **"command not found: npx"** — Node.js is not installed or not on PATH. Ask the user to install Node.js from nodejs.org and try again.
- **"network error" or timeout** — Check internet connection and retry.
- **Any other error** — Tell the user to re-run the full installer instead: the install command from their welcome email.

## Hard rules

- Do not modify any vault files.
- Do not run any other commands beyond the one above.
- Always tell the user to restart Claude Code after the command completes.
