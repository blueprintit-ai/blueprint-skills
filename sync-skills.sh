#!/bin/bash
#
# Generates the entire plugins/ directory from shared-skills/ and .claude-plugin/skills-map.json.
# Everything under plugins/ is disposable — this script recreates it from scratch.
#
# Usage: ./sync-skills.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SHARED="$ROOT/shared-skills"
SKILLS_MAP="$ROOT/.claude-plugin/skills-map.json"
MARKETPLACE="$ROOT/.claude-plugin/marketplace.json"

if [ ! -d "$SHARED" ]; then
  echo "Error: shared-skills/ directory not found" >&2
  exit 1
fi

if [ ! -f "$SKILLS_MAP" ]; then
  echo "Error: .claude-plugin/skills-map.json not found" >&2
  exit 1
fi

if [ ! -f "$MARKETPLACE" ]; then
  echo "Error: .claude-plugin/marketplace.json not found" >&2
  exit 1
fi

# Wipe and regenerate plugins/
rm -rf "$ROOT/plugins"
mkdir -p "$ROOT/plugins"

AGENTS="$ROOT/agents"
CONNECTORS="$ROOT/connectors"
SCRIPTS="$ROOT/scripts"
HOOKS="$ROOT/hooks"

export ROOT SHARED SKILLS_MAP MARKETPLACE AGENTS CONNECTORS SCRIPTS HOOKS

python3 << 'PYEOF'
import json, os, shutil

root = os.environ.get("ROOT", "")
shared = os.environ.get("SHARED", "")
skills_map_path = os.environ.get("SKILLS_MAP", "")
marketplace_path = os.environ.get("MARKETPLACE", "")
agents_src = os.environ.get("AGENTS", "")
connectors_src = os.environ.get("CONNECTORS", "")
scripts_src = os.environ.get("SCRIPTS", "")
hooks_src = os.environ.get("HOOKS", "")

with open(skills_map_path) as f:
    skills_map = json.load(f)

with open(marketplace_path) as f:
    marketplace = json.load(f)

# Index marketplace plugins by directory name (derived from source path)
marketplace_plugins = {os.path.basename(p["source"]): p for p in marketplace["plugins"]}
departments = skills_map["departments"]

for dept_name, dept_config in departments.items():
    dept_dir = os.path.join(root, "plugins", dept_name)
    skills = dept_config["skills"]  # dict of skill_id -> {displayName, summary}

    # --- .claude-plugin/plugin.json ---
    plugin_json_dir = os.path.join(dept_dir, ".claude-plugin")
    os.makedirs(plugin_json_dir, exist_ok=True)

    mp = marketplace_plugins.get(dept_name, {})
    display_name = mp.get("displayName") or mp.get("name")
    plugin_data = {
        "name": dept_name,
        "description": mp.get("description", ""),
        "version": mp.get("version", "1.0.0"),
        "author": mp.get("author", {"name": "BenAI"}),
    }
    if display_name and display_name != dept_name:
        plugin_data["displayName"] = display_name

    with open(os.path.join(plugin_json_dir, "plugin.json"), "w") as f:
        json.dump(plugin_data, f, indent=2)
        f.write("\n")

    # --- .mcp.json ---
    connector_list = dept_config.get("connectors", [])
    if connector_list:
        mcp_servers = {}
        for conn_name in connector_list:
            conn_file = os.path.join(connectors_src, f"{conn_name}.json")
            if os.path.isfile(conn_file):
                with open(conn_file) as cf:
                    mcp_servers[conn_name] = json.load(cf)
            else:
                print(f"  Warning: connectors/{conn_name}.json not found, skipping")
        if mcp_servers:
            with open(os.path.join(dept_dir, ".mcp.json"), "w") as f:
                json.dump(mcp_servers, f, indent=2)
                f.write("\n")

    # --- skills/ ---
    skills_dir = os.path.join(dept_dir, "skills")
    os.makedirs(skills_dir, exist_ok=True)

    count = 0
    for skill_id, skill_config in skills.items():
        src = os.path.join(shared, skill_id)
        dst = os.path.join(skills_dir, skill_id)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
            count += 1
        else:
            print(f"  Warning: shared-skills/{skill_id} not found, skipping")

        # Copy global scripts into skill directory if declared
        script_list = skill_config.get("scripts", []) if isinstance(skill_config, dict) else []
        if script_list and os.path.isdir(dst):
            for script_name in script_list:
                script_src = os.path.join(scripts_src, script_name)
                if not os.path.isfile(script_src):
                    print(f"  Warning: scripts/{script_name} not found, skipping")
                    continue
                if script_name == "requirements.txt":
                    # requirements.txt goes in skill root
                    shutil.copy2(script_src, os.path.join(dst, script_name))
                else:
                    # .py files go in scripts/ subdir
                    script_dst_dir = os.path.join(dst, "scripts")
                    os.makedirs(script_dst_dir, exist_ok=True)
                    shutil.copy2(script_src, os.path.join(script_dst_dir, script_name))

    print(f"  {dept_name}: {count} skills synced")

    # --- agents/ ---
    agent_list = dept_config.get("agents", [])
    if agent_list:
        agents_dir = os.path.join(dept_dir, "agents")
        os.makedirs(agents_dir, exist_ok=True)
        agent_count = 0
        for agent_id in agent_list:
            src = os.path.join(agents_src, f"{agent_id}.md")
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(agents_dir, f"{agent_id}.md"))
                agent_count += 1
            else:
                print(f"  Warning: agents/{agent_id}.md not found, skipping")
        print(f"  {dept_name}: {agent_count} agents synced")

    # --- hooks/ ---
    hooks_config = dept_config.get("hooks", {})
    if hooks_config and isinstance(hooks_config, dict):
        hooks_dir = os.path.join(dept_dir, "hooks")
        os.makedirs(hooks_dir, exist_ok=True)
        hook_count = 0
        # Build plugin.json hooks structure and copy files
        plugin_hooks = {}
        for event_name, event_hooks in hooks_config.items():
            hook_entries = []
            for h in event_hooks:
                src = os.path.join(hooks_src, h["file"])
                if os.path.isfile(src):
                    shutil.copy2(src, os.path.join(hooks_dir, h["file"]))
                    hook_count += 1
                    entry = {
                        "type": "command",
                        "command": "${CLAUDE_PLUGIN_ROOT}/hooks/" + h["file"],
                    }
                    if "timeout" in h:
                        entry["timeout"] = h["timeout"]
                    hook_entries.append(entry)
                else:
                    print(f"  Warning: hooks/{h['file']} not found, skipping")
            if hook_entries:
                plugin_hooks[event_name] = [{"matcher": "", "hooks": hook_entries}]
        # Write hooks into plugin.json
        if plugin_hooks:
            plugin_data["hooks"] = plugin_hooks
            with open(os.path.join(plugin_json_dir, "plugin.json"), "w") as f:
                json.dump(plugin_data, f, indent=2)
                f.write("\n")
        print(f"  {dept_name}: {hook_count} hooks synced")

PYEOF

echo "Done. All department plugins generated from shared-skills/ and skills-map.json."
