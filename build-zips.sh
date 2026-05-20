#!/bin/bash
#
# Builds distributable zip files for BluePrint skills.
# Reads marketplace.json, detects all department plugins, and generates:
#
#   dist/extension/                      Claude Code extension (Cursor, VS Code)
#     ├── <department>.zip               One department per zip (marketplace format)
#     └── blueprint-skills-marketplace.zip   All departments in one zip
#
#   dist/desktop/                        Claude Desktop (upload local plugin)
#     └── <department>.zip               Single plugin zips (plugin.json at root)
#
# Usage: ./build-zips.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Sync skills from _shared/ into department plugins before building
"$ROOT/sync-skills.sh"
echo ""
DIST="$ROOT/dist"
MARKETPLACE="$ROOT/.claude-plugin/marketplace.json"
TMP="$(mktemp -d)"

trap 'rm -rf "$TMP"' EXIT

# Check dependencies
if ! command -v python3 &>/dev/null; then
  echo "Error: python3 is required" >&2
  exit 1
fi

if [ ! -f "$MARKETPLACE" ]; then
  echo "Error: marketplace.json not found at $MARKETPLACE" >&2
  exit 1
fi

# Clean and create dist directories
rm -rf "$DIST"
mkdir -p "$DIST/extension" "$DIST/desktop" "$DIST/skill-zips" "$DIST/console"

# Read all plugins from marketplace.json
PLUGINS_JSON=$(python3 -c "
import json, sys
with open('$MARKETPLACE') as f:
    data = json.load(f)
for p in data['plugins']:
    print(p['name'] + '|' + p['source'])
")

echo "Found department plugins:"
echo "$PLUGINS_JSON" | while IFS='|' read -r name source; do
  echo "  - $name ($source)"
done
echo ""

# =============================================================
# EXTENSION ZIPS (Claude Code / Cursor / VS Code)
# Structure: .claude-plugin/marketplace.json + plugins/<department>/
# =============================================================
echo "--- Building extension zips ---"

echo "$PLUGINS_JSON" | while IFS='|' read -r name source; do
  staging="$TMP/ext-$name"
  rm -rf "$staging"
  mkdir -p "$staging/.claude-plugin"
  mkdir -p "$staging/$(dirname "$source")"

  # Copy the department plugin directory
  cp -R "$ROOT/$source" "$staging/$source"

  # Copy .env.example
  cp "$ROOT/.env.example" "$staging/.env.example" 2>/dev/null || true

  # Generate a marketplace.json with this department
  python3 -c "
import json
with open('$MARKETPLACE') as f:
    data = json.load(f)
envelope = {k: v for k, v in data.items() if k != 'plugins'}
envelope['name'] = data['name'] + '-$name'
plugin = next(p for p in data['plugins'] if p['name'] == '$name')
envelope['plugins'] = [plugin]
with open('$staging/.claude-plugin/marketplace.json', 'w') as f:
    json.dump(envelope, f, indent=2)
    f.write('\n')
"

  # Remove .gitkeep files and empty directories
  find "$staging" -name ".gitkeep" -delete 2>/dev/null || true
  find "$staging" -type d -empty -delete 2>/dev/null || true

  # Create zip
  (cd "$staging" && zip -r "$DIST/extension/$name.zip" . > /dev/null 2>&1)
  SIZE=$(du -h "$DIST/extension/$name.zip" | cut -f1 | xargs)
  SKILL_COUNT=$(find "$staging/$source/skills" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | xargs)
  echo "  Created extension/$name.zip ($SIZE) — $SKILL_COUNT skills"

  rm -rf "$staging"
done

# Full marketplace zip
(cd "$ROOT" && zip -r "$DIST/extension/blueprint-skills-marketplace.zip" .claude-plugin/marketplace.json plugins/ .env.example -x "*/\.*" > /dev/null 2>&1)
SIZE=$(du -h "$DIST/extension/blueprint-skills-marketplace.zip" | cut -f1 | xargs)
echo "  Created extension/blueprint-skills-marketplace.zip ($SIZE)"

# =============================================================
# DESKTOP ZIPS (Claude Desktop — upload local plugin)
# Structure: .claude-plugin/plugin.json + .mcp.json at zip root
# =============================================================
echo ""
echo "--- Building Desktop zips ---"

echo "$PLUGINS_JSON" | while IFS='|' read -r name source; do
  staging="$TMP/desktop-$name"
  rm -rf "$staging"
  mkdir -p "$staging"

  # Copy the plugin contents directly to root (no nesting)
  cp -R "$ROOT/$source"/* "$staging/" 2>/dev/null || true
  cp -R "$ROOT/$source"/.[!.]* "$staging/" 2>/dev/null || true

  # Remove .gitkeep files and empty directories
  find "$staging" -name ".gitkeep" -delete 2>/dev/null || true
  find "$staging" -type d -empty -delete 2>/dev/null || true

  # Create zip
  (cd "$staging" && zip -r "$DIST/desktop/$name.zip" . > /dev/null 2>&1)
  SIZE=$(du -h "$DIST/desktop/$name.zip" | cut -f1 | xargs)
  SKILL_COUNT=$(find "$staging/skills" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | xargs)
  echo "  Created desktop/$name.zip ($SIZE) — $SKILL_COUNT skills"

  rm -rf "$staging"
done

# =============================================================
# SKILL ZIPS (Individual skills for Cowork / Desktop)
# Structure: SKILL.md + references/ at zip root
# =============================================================
echo ""
echo "--- Building individual skill zips ---"

SKILL_COUNT=0
for skill_dir in "$ROOT/shared-skills"/*/; do
  skill_name=$(basename "$skill_dir")

  # Skip if no SKILL.md
  [ -f "$skill_dir/SKILL.md" ] || continue

  staging="$TMP/skill-$skill_name"
  rm -rf "$staging"
  mkdir -p "$staging"

  # Copy skill contents to root
  cp -R "$skill_dir"/* "$staging/" 2>/dev/null || true

  # Remove .gitkeep files and empty directories
  find "$staging" -name ".gitkeep" -delete 2>/dev/null || true
  find "$staging" -type d -empty -delete 2>/dev/null || true

  # Create zip
  (cd "$staging" && zip -r "$DIST/skill-zips/$skill_name.zip" . > /dev/null 2>&1)
  SKILL_COUNT=$((SKILL_COUNT + 1))

  rm -rf "$staging"
done

SIZE=$(du -sh "$DIST/skill-zips" | cut -f1 | xargs)
echo "  Created $SKILL_COUNT skill zips ($SIZE total) in skill-zips/"

# =============================================================
# CONSOLE ZIPS (Claude Console / platform.claude.com)
# Structure: skill-name/ wrapper folder containing SKILL.md + references/
# =============================================================
echo ""
echo "--- Building Console zips ---"

CONSOLE_COUNT=0
for skill_dir in "$ROOT/shared-skills"/*/; do
  skill_name=$(basename "$skill_dir")

  # Skip if no SKILL.md
  [ -f "$skill_dir/SKILL.md" ] || continue

  staging="$TMP/console-$skill_name"
  rm -rf "$staging"
  mkdir -p "$staging/$skill_name"

  # Copy skill contents into wrapper folder
  cp -R "$skill_dir"/* "$staging/$skill_name/" 2>/dev/null || true

  # Remove .gitkeep files and empty directories
  find "$staging" -name ".gitkeep" -delete 2>/dev/null || true
  find "$staging" -type d -empty -delete 2>/dev/null || true

  # Create zip
  (cd "$staging" && zip -r "$DIST/console/$skill_name.zip" . > /dev/null 2>&1)
  CONSOLE_COUNT=$((CONSOLE_COUNT + 1))

  rm -rf "$staging"
done

SIZE=$(du -sh "$DIST/console" | cut -f1 | xargs)
echo "  Created $CONSOLE_COUNT console zips ($SIZE total) in console/"

echo ""
echo "Done. All zips in $DIST/"
echo "  extension/   — for Claude Code, Cursor, VS Code"
echo "  desktop/     — for Claude Desktop (upload local plugin)"
echo "  skill-zips/  — individual skills for Cowork / Desktop"
echo "  console/     — for Claude Console (platform.claude.com)"
