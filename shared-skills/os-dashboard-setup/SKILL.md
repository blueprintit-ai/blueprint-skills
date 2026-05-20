---
name: os-dashboard-setup
description: Install a full personal/team command-center dashboard in an Obsidian vault. Use when the user says "set up dashboard", "install command center", "create my Obsidian dashboard", "build a vault dashboard", "dashboard for my second brain", "team dashboard in Obsidian", "os dashboard", or wants a command-center style layout. Interviews about org, profiles, pages, buttons (with Claude prompts), and brand. Bundles and side-loads 5 plugins (Dataview, CustomJS, Shell-commands, Terminal, Homepage), wires shell-command aliases, configures a Claude terminal profile, enables the CSS snippet, sets the homepage. Generic — no personal branding.
allowed-tools: Bash, Read, Write, Edit, AskUserQuestion
---

# OS Dashboard Setup

Installs a configurable command-center dashboard in any Obsidian vault. Home + per-profile + Vault Overview pages, KPI cards, sparklines, heatmap, task rollup, recent-files lists, and a button bar wired to user-defined Claude prompts via the Shell-commands plugin. All 5 required plugins are bundled and auto-enabled — the user only has to restart Obsidian.

## What gets installed

```
{vault}/
├── Dashboard/
│   ├── Home.md                       # Team-wide dashboard
│   ├── Vault-Overview.md             # Top-level vault health view
│   ├── {Profile}.md                  # One per configured profile
│   ├── Setup.md                      # In-vault setup reference
│   ├── CLAUDE.md                     # AI routing rules for this folder
│   ├── components/dashboard.js       # The renderer (CONFIG substituted)
│   └── lib/frappe-charts.min.js
└── .obsidian/
    ├── snippets/command-center.css   # Brand-styled CSS (enabled)
    ├── plugins/dataview/             # Side-loaded, enabled
    ├── plugins/customjs/             # Side-loaded, enabled
    ├── plugins/obsidian-shellcommands/  # Side-loaded, enabled, aliases pre-registered
    ├── plugins/terminal/             # Side-loaded, enabled, "Claude" profile configured
    ├── plugins/homepage/             # Side-loaded, enabled, points to Dashboard/Home
    ├── community-plugins.json        # Union'd with the 5 plugin IDs
    └── appearance.json               # CSS snippet enabled
```

## Pre-flight checks

```bash
test -d .obsidian && echo "vault confirmed" || (echo "NOT A VAULT — cd into your Obsidian vault first" && exit 1)
test -d Dashboard && echo "DASHBOARD EXISTS — ask user before overwriting"
```

If `Dashboard/` exists, ask: cancel / install into `Dashboard-new/` / overwrite (require explicit "yes overwrite").

## Interview (always run before installing)

Use `AskUserQuestion` for each. Capture answers into variables for substitution into CONFIG.

### Q1. Organization name
"What's your organization or personal brand name? (Used in folder paths and dashboard header. Short — one word ideal.)"
Default if skipped: `MyOrg`. Variable: `ORG_NAME`.

### Q2. Brand label + subtitle
"What should the dashboard show as its title?" Two parts:
- Brand label (header text, e.g. "Acme"). Defaults to `ORG_NAME`. Variable: `BRAND_LABEL`.
- Brand subtitle (small text after the label, e.g. "Agentic OS", "Command Center"). Default `Command Center`. Variable: `BRAND_SUB`.

### Q3. Profile list
"Who's on the team? List each profile name on a separate line. Use lowercase or capitalized — must match the folder names you'll use in step 4. For a solo vault, just one name."
Parse into array. Variable: `PROFILES` (JSON array). The first is `DEFAULT_PROFILE`.

### Q4. Profile folder pattern
"Where do you keep per-profile data?" Show 4 options via AskUserQuestion:
- `Team/{ORG}/Profiles/{name}` (recommended for orgs — matches `Team/Acme/Profiles/Alex`)
- `Team/{name}` (flat team layout)
- `People/{name}` (alternative naming)
- Custom — ask user to type the exact pattern. Must contain `{name}`. `{ORG}` is optional.

Variable: `PROFILE_FOLDER_PATTERN`. Verify each `PROFILES[i]` folder exists (warn if missing — installer will still write the dashboard; profile folders just won't have data yet).

### Q5. Daily / Tasks / Snapshots subpaths
Three quick AskUserQuestion calls (each with sensible defaults):
- **Daily subpath** within each profile folder. Default `Daily`. Empty disables. Variable: `DAILY_SUBPATH`.
- **Tasks subpath** (Task Board plugin uses `task-list`). Default `task-list`. Empty disables the task widget. Variable: `TASKS_SUBPATH`.
- **Snapshots subpath** for JSON files the dashboard reads. Default `snapshots`. Variable: `SNAPSHOTS_SUBPATH`.

Also: **Root daily path** for team-wide rollups. Default `Daily`. Variable: `ROOT_DAILY_PATH`.

### Q6. Pages to ship
Which dashboard pages? MultiSelect:
- Home (team rollup) — always recommended
- Per-profile pages (one per Q3 profile)
- Vault Overview (top-level folder health)
- Custom — user names extra pages

Variable: `PAGES` (array). Installer creates one `.md` per page.

### Q7. Overview folders (only if Vault Overview is in PAGES)
"Name 3-5 top-level folders to show on the Vault Overview page. For each: folder path, one-line description, optional CLAUDE.md path (or empty)."
Variable: `OVERVIEW_FOLDERS` (array of `[path, description, claude_path]`).
Defaults if skipped: detect `Projects/`, `Resources/`, `Intelligence/`, `Departments/`, `Teams/`, `Daily/` if present.

### Q8. Buttons (with Claude prompts)
"What action buttons should the dashboard expose? For each button: label (short), icon (emoji or empty), scope (team / profile / both), and a Claude prompt (the text passed to `claude -p '...'`). Use `{profile}` in the prompt to interpolate the current profile name. Add as many as you want; defaults are zero."

Suggest these as starter buttons (user can accept/reject each):
- **Morning brief** (☀️, both, prompt: `"Read today's daily for {profile} if it exists. Write a 5-line morning brief covering open loops, top priorities, and energy level. Append under a '## Morning brief' heading."`)
- **New daily** (📝, both, prompt: `"Create today's daily note at <DAILY_PATH>/$(date +%Y-%m-%d).md with standard frontmatter and section headings. Don't overwrite if it exists."`)
- **Launch Claude** (💬, both, `cmd: terminal:open-terminal.claude.root`) — wired via Terminal plugin "Claude" profile, NOT a shell-command
- **Reload** (🔄, both, `cmd: app:reload`)
- **Settings** (⚙️, both, `cmd: app:open-settings`)

For every button with a `prompt`, the installer generates a shell-commands alias `shell-command-<kebab-label>` and a `cmd: obsidian-shellcommands:shell-command-<alias>`.

Variable: `BUTTONS` (object with `team` and `profile` arrays).

### Q9. Brand colors
Two hex colors. Defaults: primary `#020309`, canvas `#FAF3E3`. Substitute into CONFIG.COLORS and the CSS snippet variables at the top of `command-center.css`.

### Q10. Brand mark (optional)
"Path to a PNG/SVG logo to show in the dashboard header? Leave blank for no logo."
If provided, copy to `Dashboard/lib/brand-mark.png` and set `BRAND_MARK_PATH` to that. Default empty.

## Critical constraints — read before editing the renderer template

These two pitfalls broke real installs. Treat them as load-bearing.

### 1. CustomJS file shape: ONE class expression, period.

CustomJS evaluates each `.js` file as `eval(\`(${file_contents})\`)` — it wraps the entire file in parentheses to coerce it into a single expression and pull the class out. This means:

- ✅ Allowed: a single `class dashboard { ... }` declaration. Comments before and after are fine.
- ❌ NOT allowed: a top-level `const CONFIG = {...}` or any other statement before/after the class. `(const CONFIG = ...)` is a syntax error because `const` is a statement, not an expression. CustomJS surfaces this as `SyntaxError: ParseError: Unexpected token`.

In `references/dashboard-template.js`, CONFIG lives as a `static CONFIG = { ... }` field at the top of the class body. All code references it as `this.constructor.CONFIG.X` (not bare `CONFIG.X`). Preserve that pattern when editing — if you re-introduce a top-level `const`, the dashboard renders as a blank page with no console error from the dataviewjs block (the error fires deep inside CustomJS and the dataviewjs block just silently doesn't get the `dashboard` class).

Smoke test before shipping any renderer change:
```bash
node -e "$(cat dashboard-template.js | sed 's/__[A-Z_]*__/null/g' | python3 -c 'import sys; print(f\"({sys.stdin.read()})\");')"
```
If that fails with a SyntaxError, the file violates the constraint. Fix before substitution.

### 2. Plugin data.json keys are NOT what you'd guess.

Always cross-reference the keys against a known-working vault — do not invent them from the plugin's UI labels. Confirmed-correct keys:

| Plugin | Key | Wrong-but-tempting alternative |
|---|---|---|
| **customjs** | `jsFolder` (and `jsFiles: ""`) | ❌ `folder` (silently ignored — plugin scans nothing) |
| **dataview** | `enableDataviewJs`, `enableInlineDataviewJs`, `enableInlineDataview` | (these are correct) |
| **homepage** | `homepages` (plural, object keyed by display name) → `.value` | ❌ `homepage` (singular) |
| **terminal** | `profiles.claude.executable` (absolute path) | ❌ relying on `claude` in PATH (Obsidian doesn't inherit login shell PATH) |
| **obsidian-shellcommands** | `shell_commands[shell-command-<alias>].shell_command` | ❌ flat `commands[]` array |

When in doubt, look at a known-working install's `data.json` before writing the install flow.

## Install execution

After the interview, do these in order. Resolve `$SKILL_DIR` from the skill's own path.

### Step 1. Create folder structure
```bash
mkdir -p Dashboard/components Dashboard/lib Dashboard/snapshots
mkdir -p .obsidian/snippets .obsidian/plugins
```

### Step 2. Substitute CONFIG and write dashboard.js
Read `$SKILL_DIR/references/dashboard-template.js`. Substitute each placeholder with the captured value:

| Placeholder | Value |
|---|---|
| `__ORG_NAME__` | `ORG_NAME` |
| `__BRAND_LABEL__` | `BRAND_LABEL` |
| `__BRAND_SUB__` | `BRAND_SUB` |
| `__BRAND_MARK_PATH__` | `BRAND_MARK_PATH` (or `""`) |
| `__PROFILES_JSON__` | `JSON.stringify(PROFILES)` |
| `__DEFAULT_PROFILE__` | `DEFAULT_PROFILE` |
| `__PROFILE_FOLDER_PATTERN__` | `PROFILE_FOLDER_PATTERN` |
| `__DAILY_SUBPATH__` | `DAILY_SUBPATH` |
| `__TASKS_SUBPATH__` | `TASKS_SUBPATH` |
| `__SNAPSHOTS_SUBPATH__` | `SNAPSHOTS_SUBPATH` |
| `__ROOT_DAILY_PATH__` | `ROOT_DAILY_PATH` |
| `__OVERVIEW_FOLDERS_JSON__` | `JSON.stringify(OVERVIEW_FOLDERS)` |
| `__BUTTONS_JSON__` | `JSON.stringify(BUTTONS)` |
| `__CLAUDE_PROMPTS_JSON__` | `"{}"` (reserved for later use) |
| `__SKILLS_FOLDER__` | optional skills folder path (e.g. `Plugins/skills`); empty hides the Vault Overview Skills section |
| `__SKILL_GROUPS_JSON__` | `"{}"` (or `JSON.stringify({"Group": ["skill-a", "skill-b"]})` if user wants grouped skill chips) |
| `__PROJECT_CATEGORIES_JSON__` | `"[]"` (or `JSON.stringify(["Agency","Content"])` if user has `Projects/<Cat>/` subfolders) |
| `__CONNECTORS_JSON__` | `"[]"` (or `JSON.stringify([["Slack","Team comms"], ...])` for the connectors list widget) |
| `__CHEATSHEET_JSON__` | `"[]"` (or `JSON.stringify([["Meeting note","Intelligence/meetings/YYYY-MM-DD-{Title}.md"], ...])`) |

Ask the user about these five optional Vault Overview fields only if they chose to ship the Vault Overview page. All accept empty defaults.

Write the result to `Dashboard/components/dashboard.js`. **Verify with both checks before declaring success:**
```bash
# 1. Plain JS parse
node --check Dashboard/components/dashboard.js || { echo "FATAL: dashboard.js has a syntax error"; exit 1; }

# 2. CustomJS-wrapped parse — catches the 'top-level const' pitfall (see Critical Constraints)
node -e "try { new Function('return (' + require('fs').readFileSync('Dashboard/components/dashboard.js','utf8') + ')'); console.log('CustomJS wrap OK'); } catch (e) { console.error('FATAL — CustomJS will reject this file:', e.message); process.exit(1); }"
```
Both must pass. If check #2 fails but #1 passes, you've reintroduced a top-level statement before the class. Fix before continuing — the dashboard will render as a blank page otherwise.

### Step 3. Copy static assets
```bash
cp "$SKILL_DIR/references/frappe-charts.min.js" Dashboard/lib/
```
If a brand mark was provided in Q10, copy it into `Dashboard/lib/`.

### Step 4. Generate dashboard MD pages
For each page in `PAGES`, read the corresponding template and substitute placeholders:

- `references/home-template.md` → `Dashboard/Home.md` (no substitution beyond `{{BRAND_LABEL}}`)
- `references/vault-overview-template.md` → `Dashboard/Vault-Overview.md`
- For each profile in `PROFILES`: `references/profile-template.md` → `Dashboard/{Profile}.md`, substitute `{{PROFILE_NAME}}`

### Step 5. Setup + CLAUDE docs
- `references/setup-template.md` → `Dashboard/Setup.md`, substitute `{{BRAND_LABEL}}`, `{{PAGES_LINKS}}`
- `references/claude-md-template.md` → `Dashboard/CLAUDE.md`, substitute `{{ORG_NAME}}`, `{{PROFILE_FOLDER_PATTERN}}`

### Step 6. Side-load plugins
For each of `dataview`, `customjs`, `obsidian-shellcommands`, `terminal`, `homepage`:
```bash
if [ ! -d ".obsidian/plugins/$ID" ]; then
  mkdir -p ".obsidian/plugins/$ID"
  cp "$SKILL_DIR/references/plugins/$ID/"* ".obsidian/plugins/$ID/"
fi
```
The `if` guard preserves any newer version the user already has.

### Step 7. Plugin data.json files
Write each to `.obsidian/plugins/<id>/data.json` (merge with existing if present).

**dataview**:
```json
{"enableDataviewJs": true, "enableInlineDataviewJs": true, "enableInlineDataview": true}
```

**customjs**: The key is `jsFolder` (NOT `folder` — that's silently ignored by the plugin and was a real bug that made early installs render a blank page).
```json
{"jsFiles": "", "jsFolder": "Dashboard/components", "startupScriptNames": [], "registeredInvocableScriptNames": []}
```

**obsidian-shellcommands**: For each button in `BUTTONS.team` and `BUTTONS.profile` that has a `prompt` (not a `cmd`), generate one shell-commands entry. Schema:
```json
{
  "shell_commands": {
    "shell-command-<alias>": {
      "shell_command": "cd \"{{vault_dir}}\" && claude -p \"<escaped-prompt>\" --dangerously-skip-permissions",
      "alias": "<alias>",
      "platform_specific_commands": {"default": "use this"},
      "shells": {},
      "events": {},
      "debounce": null,
      "execution_notification_mode": "disabled",
      "output_channels": {"stdout": "notification", "stderr": "notification-bigger"},
      "output_handlers": {},
      "output_wrappers": {"stdout": null, "stderr": null},
      "command_palette_availability": "enabled"
    }
  },
  "preferences": {"debug": false},
  "settings_version": "0.23.0"
}
```
Replace `<alias>` with kebab-cased label (e.g. "Morning brief" → "morning-brief"). Escape double quotes in the prompt. Substitute `{profile}` in prompts at button-click time via the renderer (already supported).

**terminal**: Cross-platform "claude" integrated profile.

**Resolving the `claude` binary path** — this is the #1 source of "Launch Claude" button failures. Obsidian's Terminal plugin spawns processes without the user's login shell, so `claude` on PATH is not enough. You need an absolute path.

Probe in this order, take the first hit:
```bash
# 1. PATH lookup (via the user's interactive shell so .zshrc/.bashrc PATH applies)
CLAUDE_BIN="$(zsh -ic 'command -v claude' 2>/dev/null || bash -ic 'command -v claude' 2>/dev/null || command -v claude)"

# 2. Common install locations (in priority order)
if [ -z "$CLAUDE_BIN" ] || [ ! -x "$CLAUDE_BIN" ]; then
  for candidate in \
    "$HOME/.local/bin/claude" \
    "$HOME/.claude/local/claude" \
    "/opt/homebrew/bin/claude" \
    "/usr/local/bin/claude" \
    "$HOME/.npm-global/bin/claude" \
    "$HOME/.volta/bin/claude" \
    "/usr/bin/claude"; do
    [ -x "$candidate" ] && CLAUDE_BIN="$candidate" && break
  done
fi

# 3. Verify it actually runs
if [ -n "$CLAUDE_BIN" ] && "$CLAUDE_BIN" --version >/dev/null 2>&1; then
  echo "resolved: $CLAUDE_BIN"
else
  CLAUDE_BIN=""
fi
```

If the probe returns empty, fall through to `AskUserQuestion`: "I couldn't find the `claude` binary automatically. Paste the full path (run `which claude` in your shell to find it), or skip to disable the Launch Claude button."

Now write `terminal/data.json`. Set `executable` to the resolved absolute path. If empty and the user skipped, **omit the `claude` profile entirely** rather than ship a broken one. On Windows, repeat the probe with `claude.exe` candidates and use forward-slash paths.

```json
{
  "profiles": {
    "claude": {
      "args": ["--dangerously-skip-permissions"],
      "executable": "<resolved absolute path>",
      "followTheme": true,
      "name": "Claude",
      "platforms": {"darwin": true, "linux": true, "win32": true},
      "restoreHistory": false,
      "rightClickAction": "copyPaste",
      "successExitCodes": ["0", "SIGINT", "SIGTERM"],
      "terminalOptions": {"documentOverride": null},
      "type": "integrated",
      "useWin32Conhost": true
    }
  },
  "addToCommand": true,
  "focusOnNewInstance": true,
  "newInstanceBehavior": "newHorizontalSplit"
}
```

**Print the resolved path to the user** in the final summary so they know what was wired up. Sample line: `Launch Claude wired to: /opt/homebrew/bin/claude` — that way if it breaks later they know exactly what to verify.

**Post-install verification** — before declaring the install complete, sanity-check:
```bash
test -x "$CLAUDE_BIN" || { echo "WARN: $CLAUDE_BIN is not executable. Launch Claude button will fail."; }
"$CLAUDE_BIN" --version 2>&1 | head -1   # surfaces version to the user
```
If the version probe fails, don't silently move on — print the failure and tell the user how to fix it (`Re-run setup, or edit .obsidian/plugins/terminal/data.json profiles.claude.executable`).

**If the user later sees the FileNotFoundError Python traceback** (Terminal plugin uses a Python PTY shim, so a missing executable surfaces as a Python stack), it means `claude` moved or was uninstalled after setup. Recovery:
1. Run `which claude` in their shell to find the new path.
2. Edit `.obsidian/plugins/terminal/data.json` → `profiles.claude.executable`.
3. Reload Obsidian (Cmd/Ctrl + R).

The skill should offer to re-run just the terminal-profile step if invoked again on an existing install — detect via `test -f .obsidian/plugins/terminal/data.json && grep -q '"claude"' .obsidian/plugins/terminal/data.json` and ask "rewire Launch Claude with newly-detected path?".

**homepage**:
```json
{
  "version": 4,
  "homepages": {
    "Main Homepage": {
      "value": "Dashboard/Home",
      "kind": "File",
      "openOnStartup": true,
      "openMode": "Replace all open notes",
      "manualOpenMode": "Replace all open notes",
      "view": "Reading view",
      "revertView": true,
      "openWhenEmpty": true,
      "refreshDataview": true,
      "autoCreate": false,
      "autoScroll": false,
      "pin": false,
      "commands": [],
      "alwaysApply": false,
      "hideReleaseNotes": false
    }
  },
  "separateMobile": false
}
```

### Step 8. Enable plugins in community-plugins.json
Read `.obsidian/community-plugins.json` (create `[]` if missing). Backup to `.bak`. Union in `["dataview", "customjs", "obsidian-shellcommands", "terminal", "homepage"]`. Preserve all existing entries. Write back.

### Step 9. Enable CSS snippet
Read `.obsidian/appearance.json` (create `{}` if missing). Backup to `.bak`. Read `references/command-center.css`, substitute color placeholders (`--cc-primary`, `--cc-canvas` variables at the top — or wherever the CSS uses them), write to `.obsidian/snippets/command-center.css`. Set `enabledCssSnippets` to union with `["command-center"]`.

### Step 10. Print the one remaining manual step
```
Done. The dashboard, all 5 plugins, the Claude terminal profile, and the homepage are configured.

ONE final step Obsidian only picks up on launch:
  1. Quit Obsidian fully (Cmd/Ctrl + Q — not just close the window).
  2. Reopen the vault.
  3. Obsidian will ask you to "Trust" each plugin. Click Trust for all 5.
  4. Open Dashboard/Home — it should render immediately.

If a button doesn't fire, open Settings → Shell commands and confirm each alias matches the one shown in the button's tooltip. The dashboard's developer console (Cmd/Ctrl + Opt/Alt + I) logs every command attempt.
```

## Don't do

- Do not modify user content outside `Dashboard/` and `.obsidian/`. The dashboard is read-only on `Daily/`, `Team/`, `Tasks/`, etc.
- Do not overwrite existing `.obsidian/plugins/<id>/` installs — only side-load when missing. The user may have a newer version.
- Do not use any branded/personal names ("Ben", "BenAI", specific people). All identifiers come from the interview.
- Do not auto-fetch latest plugin versions at install time — the bundled versions are pinned for reproducibility. To refresh, re-run the curl commands in `references/plugins/`.

## File templates summary

| Template | Goes to | Substitutes |
|---|---|---|
| `dashboard-template.js` | `Dashboard/components/dashboard.js` | All `__*__` placeholders in CONFIG |
| `home-template.md` | `Dashboard/Home.md` | `{{BRAND_LABEL}}` |
| `vault-overview-template.md` | `Dashboard/Vault-Overview.md` | `{{BRAND_LABEL}}` |
| `profile-template.md` | `Dashboard/{Profile}.md` | `{{PROFILE_NAME}}` |
| `setup-template.md` | `Dashboard/Setup.md` | `{{BRAND_LABEL}}` |
| `claude-md-template.md` | `Dashboard/CLAUDE.md` | `{{ORG_NAME}}`, `{{PROFILE_FOLDER_PATTERN}}` |
| `command-center.css` | `.obsidian/snippets/command-center.css` | `--cc-primary`, `--cc-canvas` color vars |
| `frappe-charts.min.js` | `Dashboard/lib/frappe-charts.min.js` | none |

Bundled plugin folders under `references/plugins/` are copied verbatim into `.obsidian/plugins/<id>/`.
