---
name: relay-swap
description: Swap the official Relay (`system3-relay`) Obsidian plugin for the BenAI fork (`benai-relay-fork`). Bundled production build ships inside the skill — user just points to their Obsidian vault path. Use when the user wants to "install BenAI Relay", "swap relay for the fork", "replace the official relay plugin", or "use BenAI's relay in my vault".
---

# Relay Swap — Install BenAI Relay Fork

This skill replaces the upstream Relay plugin (`system3-relay`) with the BenAI fork (`benai-relay-fork`) in a target Obsidian vault. The compiled fork ships at `${CLAUDE_PLUGIN_ROOT}/skills/relay-swap/reference/benai-relay-fork/` (three files: `main.js`, `manifest.json`, `styles.css`). Copy from there — do not fetch from anywhere else.

## What the user provides

**Just the absolute path to their Obsidian vault** (the folder containing `.obsidian/`). Example: `/Users/jane/Documents/MyVault`.

That's it.

---

# Workflow

## Step 0 — Confirm intent + collect vault path

Tell the user what this will do, in plain language:

> I'm about to replace the official Relay plugin with the BenAI fork in your Obsidian vault. The fork has custom RBAC + access controls. This will:
> 1. Delete `<vault>/.obsidian/plugins/system3-relay/` if present.
> 2. Install the bundled BenAI Relay build into `<vault>/.obsidian/plugins/benai-relay-fork/`.
> 3. Update `<vault>/.obsidian/community-plugins.json` to disable the old one and enable the new one.
>
> **Close Obsidian first** — modifying plugin files while Obsidian is running can corrupt the install.
>
> Paste the absolute path to your vault (the folder containing `.obsidian/`):

Wait for the path. Do not proceed until you have it.

## Step 1 — Verify it's a valid Obsidian vault

```bash
VAULT="<paste>"
test -d "$VAULT/.obsidian" || echo "NOT_A_VAULT"
```

If `NOT_A_VAULT` prints, tell the user the path doesn't contain `.obsidian/` and ask them to re-check. Do not proceed.

## Step 2 — Snapshot current plugins

```bash
ls "$VAULT/.obsidian/plugins/" 2>/dev/null
cat "$VAULT/.obsidian/community-plugins.json" 2>/dev/null
```

Show the user what's there. If `community-plugins.json` doesn't exist, that's fine — Obsidian creates it on first community plugin install. We'll handle both cases.

Confirm with the user before proceeding:
- If `system3-relay` is present, we'll remove it.
- If `benai-relay-fork` already exists, we'll overwrite it (warn and ask).

## Step 3 — Confirm Obsidian is closed

```bash
pgrep -x Obsidian && echo "OBSIDIAN_RUNNING"
```

If `OBSIDIAN_RUNNING`, stop and tell the user to quit Obsidian (Cmd+Q on macOS), then re-run. Do not proceed while it's running.

## Step 4 — Remove the official plugin (if present)

```bash
if [ -d "$VAULT/.obsidian/plugins/system3-relay" ]; then
  rm -rf "$VAULT/.obsidian/plugins/system3-relay"
  echo "Removed system3-relay"
fi
```

This is destructive — that's why Step 0 told the user upfront. If the user has unsaved local changes inside that plugin's folder (rare; usually it's just compiled build artifacts), they should back it up first.

## Step 5 — Install the fork from the skill bundle

```bash
SRC="${CLAUDE_PLUGIN_ROOT}/skills/relay-swap/reference/benai-relay-fork"
DST="$VAULT/.obsidian/plugins/benai-relay-fork"

mkdir -p "$DST"
cp "$SRC/main.js" "$SRC/manifest.json" "$SRC/styles.css" "$DST/"
ls -la "$DST"
```

You should see the three files (`main.js`, `manifest.json`, `styles.css`) at the destination.

## Step 6 — Update `community-plugins.json`

Obsidian uses this file to track which community plugins are enabled. We need to:
- Remove `system3-relay` from the enabled list.
- Add `benai-relay-fork` to the enabled list.

```bash
CFG="$VAULT/.obsidian/community-plugins.json"
if [ ! -f "$CFG" ]; then echo '[]' > "$CFG"; fi

python3 - <<PY
import json, pathlib
p = pathlib.Path("$CFG")
data = json.loads(p.read_text() or "[]")
data = [x for x in data if x != "system3-relay"]
if "benai-relay-fork" not in data:
    data.append("benai-relay-fork")
p.write_text(json.dumps(data, indent=2) + "\n")
print("community-plugins.json:", data)
PY
```

## Step 7 — Verify

```bash
test -f "$VAULT/.obsidian/plugins/benai-relay-fork/main.js" && echo "INSTALLED OK"
grep -q "benai-relay-fork" "$VAULT/.obsidian/community-plugins.json" && echo "ENABLED OK"
test ! -d "$VAULT/.obsidian/plugins/system3-relay" && echo "OFFICIAL REMOVED OK"
```

All three should print `OK`.

## Step 8 — Tell the user how to finish

> Done. Open Obsidian and load this vault. The BenAI Relay plugin should be active. If you don't see it:
> - Settings → Community plugins → confirm "BenAI Relay" is toggled on.
> - If Obsidian shows a "safe mode" banner, click "Trust author and enable" or disable safe mode in Settings → Community plugins.
> - Sign in with your Relay.md credentials when prompted.

---

# Troubleshooting

**`NOT_A_VAULT`** — the path is wrong, or it's pointing at a parent. The right path is the folder that contains `.obsidian/` directly (e.g. `~/Documents/MyVault`, not `~/Documents`).

**Plugin doesn't appear in Obsidian.** Check `.obsidian/community-plugins.json` — it must contain `"benai-relay-fork"`. Restart Obsidian.

**Obsidian shows "Failed to load plugin".** The bundled `main.js` may be incompatible with the user's Obsidian version. Check `manifest.json`'s `minAppVersion` against Obsidian's "About" panel. The bundled fork requires Obsidian 0.15.0+.

**User wants to revert to upstream Relay.** Remove `<vault>/.obsidian/plugins/benai-relay-fork/`, edit `community-plugins.json` to remove `benai-relay-fork`, then install `system3-relay` from the Obsidian community plugins store normally.

**Want to update the bundled fork later.** The plugin is built into this skill — to update, the maintainer rebuilds `relay-fork`, copies the three artifacts into `shared-skills/relay-swap/reference/benai-relay-fork/`, runs `./sync-skills.sh && ./build-zips.sh`, and republishes.
