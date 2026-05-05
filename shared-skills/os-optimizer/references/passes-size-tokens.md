# Audit passes — Size & Token Budget

## Contents

1. [A1: CLAUDE.md size check](#a1-claudemd-size-check)
2. [A2: Per-file size budget](#a2-per-file-size-budget)
3. [A3: Token estimate](#a3-token-estimate)
4. [A4: Position effect — top-of-file lead](#a4-position-effect--top-of-file-lead)

Skip list for every pass: `.claude/worktrees/`, `.git/`, `.trash/`, `node_modules/`, `.obsidian/`, `dist/`, `build/`, `Infrastructure/relay-mcp-server-v2/` and any folder containing compiled artifacts.

---

## A1: CLAUDE.md size check

**Source:** `references/anthropic-claude-md.md` (200-line target).

**What:** every `CLAUDE.md` file in the vault. Flag any over 200 lines (Anthropic's adherence ceiling). Note 80–200 as "approaching limit."

**How:**
- `find . -name "CLAUDE.md"` with skip list
- Read line count via `wc -l`
- Read byte count via `stat`

**Finding format:**
```
{path} — {N} lines, {bytes} bytes (~{tokens} tokens)
Severity: warn (>200) / fail (>300)
Action: flag for manual rewrite — extract lowest-signal section to a `references/` file or split by domain
```

**Auto-fix:** none in v0. Flag-only.

---

## A2: Per-file size budget

**Source:** `references/anthropic-managed-memory.md` (100KB / 25K-token ceiling, <10KB recommended).

**What:** every `.md` file in the vault. Flag files exceeding the per-file budget that Anthropic recommends for memory-style content.

**How:**
- Glob `**/*.md` with skip list
- For each file: byte size and approximate tokens (`bytes / 4`)
- Tier:
  - `> 100KB or > 25K tokens` — **fail**, hard ceiling
  - `> 10KB` — **warn**, split candidate
  - `≤ 10KB` — ok

**Skip:** files in folders that intentionally hold long-form content (e.g. `Projects/youtube/youtube-transcripts/` — raw transcripts are expected to be long; treat as informational, not findings).

**Finding format:**
```
{path} — {KB}KB, ~{tokens} tokens
Severity: warn (>10KB) / fail (>100KB)
Action: split into focused topical files; this file likely holds multiple unrelated topics
```

**Auto-fix:** none in v0. Flag-only.

---

## A3: Token estimate

**Source:** `references/chroma-context-rot.md` (every token competes for attention) + `references/caveman-compression.md` (top-3 reduction targets).

**What:** estimate per-session token load and identify largest reduction targets.

**How:**
1. Root `CLAUDE.md`: byte size, tokens (`bytes / 4`).
2. All folder-level `CLAUDE.md` files: sum of bytes/tokens (this is the on-demand tree, not the always-loaded portion).
3. In root `CLAUDE.md`, identify the **3 largest h2/h3 sections** by byte count. Estimate Caveman compression savings at ~25% per section.
4. Annual savings projection: `(tokens-saved × sessions-per-week × 52)`.

**Output (informational only, no findings):**
```
Per-session auto-load (root CLAUDE.md): {tokens} tokens
Total CLAUDE.md tree (on-demand): {tokens} tokens

Top 3 reduction targets in root:
1. ## {section-name} — {bytes} bytes ({tokens}t), est. -{savings}t after Caveman
2. ## {section-name} — {bytes} bytes ({tokens}t), est. -{savings}t
3. ## {section-name} — {bytes} bytes ({tokens}t), est. -{savings}t
```

**Auto-fix:** none. Pure measurement.

---

## A4: Position effect — top-of-file lead

**Source:** `references/chroma-context-rot.md` (position effect — unique words placed early have higher accuracy) + `references/anthropic-claude-md.md` (most important rules at top).

**What:** for every `CLAUDE.md` and `index.md`/`README.md` in active folders, check that the first ~30% of lines contains the load-bearing content (routing tables, rules, decisions) and not preamble.

**How:**
- Read the first 30% of lines (or first 30, whichever is more).
- Heuristics for "load-bearing":
  - Contains a markdown table
  - Contains a numbered list of rules
  - Contains imperatives (`Run`, `Use`, `Do`, `Never`)
  - Contains specific file paths or commands
- Heuristics for "preamble" (negative):
  - Long descriptive prose without imperatives
  - Phrases like *"This document explains..."*, *"In this guide..."*, *"Welcome to..."*
  - Generic introductions

**Finding format:**
```
{path} — first {N} lines look like preamble, not load-bearing rules
Excerpt: "{first 100 chars}..."
Action: lead with the most important rule/table/decision; move preamble lower or delete
```

**Severity:** warn

**Auto-fix:** none in v0. Flag for manual rewrite.

---

## Pass output structure

Each pass returns to the orchestrator (SKILL.md) a list of findings:

```python
{
  "pass_id": "A1",
  "pass_name": "CLAUDE.md size check",
  "findings": [
    {
      "path": "Departments/CLAUDE.md",
      "severity": "warn",
      "details": "247 lines (target <200)",
      "action": "flag",  # or "fixable"
      "fix_summary": None,  # or a brief description if fixable
    },
    ...
  ]
}
```

The orchestrator uses this structure to render the summary and group fix proposals.
