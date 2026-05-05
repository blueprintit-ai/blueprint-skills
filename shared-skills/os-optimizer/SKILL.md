---
name: os-optimizer
description: "Discovery-first audit and optimizer for any markdown-based second brain / OS vault. Walks the entire vault, classifies every .md file by role (root CLAUDE.md, folder CLAUDE.md, index/README, SKILL.md, daily, meeting, transcript, decision, template, context, note), flags missing folder leaders, prioritizes the audit by load weight, then runs 22 passes across 4 groups (size & tokens, wiki linting, skills/progressive disclosure, vault hygiene) applying the right framework per file role. Approves fixes per category via AskUserQuestion, applies what's approved, renders a brand-aware HTML dashboard saved to a discovered decisions folder. Encodes 5 frameworks (Anthropic CLAUDE.md, Karpathy Wiki lint, Caveman compression, Chroma context rot, Anthropic Memory). TRIGGERS: os optimizer, optimize vault, vault audit, lint vault, vault health check, audit my brain, second brain audit, clean up vault. Run from the user's vault root."
---

# Vault Audit

Comprehensively scan a second brain vault. Run 22 passes across 4 groups. Present findings, let the user approve fixes per group, apply only what's approved, save a dated audit report.

## Reference files

This skill ships with 11 reference files. Read each on demand.

### Framework references (the *why*)

| File | Read when |
|---|---|
| `references/anthropic-claude-md.md` | Pass A1, D5, D6 — full CLAUDE.md rules and rationale |
| `references/karpathy-llm-wiki.md` | Pass B1, B2, B3 — lint operation rules |
| `references/caveman-compression.md` | Pass A3 — compression targets and protected zones |
| `references/chroma-context-rot.md` | Pass A3, A4 — token cost and position effect |
| `references/anthropic-managed-memory.md` | Pass A2, D2, D3 — file-size and naming rules |
| `references/progressive-disclosure.md` | Pass C1–C5 — skill structure rules |
| `references/practitioner-notes.md` | When user asks "why does this matter" — production friction context |

### Pass-implementation references (the *how*)

| File | Passes | What |
|---|---|---|
| `references/passes-size-tokens.md` | A1–A4 | CLAUDE.md size, per-file budget, token estimate, position effect |
| `references/passes-wiki-lint.md` | B1–B5 | Dead wikilinks, orphans, same-role duplicates, routing compliance, stubs |
| `references/passes-skills.md` | C1–C5 | Skill-vault duplication, SKILL.md size, frontmatter validation, reference depth, reference TOC |
| `references/passes-vault-hygiene.md` | D1–D8 | Frontmatter, filename quality, index presence, em dashes, generic emphasis, code-style rules, H1=filename, README hygiene |

When running a pass, **read the relevant `passes-*.md` file** for the exact regex/heuristic/finding format. Don't paraphrase from this SKILL.md — the implementation files are authoritative.

When surfacing a finding to the user, cite the framework reference so they can verify the rule.

## Flow

1. **Verify the cwd looks like a vault** — light check, no hardcoded folder names (Step 0)
2. **Discover and classify every `.md` file** across the whole vault (Step 1)
3. **Run all 4 pass groups** against the classified map — prioritized by what gets loaded most (Step 2)
4. **Render a clean markdown summary** with what was found and what's flagged (Step 3)
5. **Ask what to do per category** with `AskUserQuestion` (Step 4)
6. **Apply approved fixes** (Step 5)
7. **Render the HTML dashboard, save to `{decisions-folder}/{YYYY-MM-DD}-vault-audit.html`, show inline** (Step 6)

### Why discovery comes first

Different vaults have different shapes. We can't assume `Context/`, `Intelligence/`, or any specific folder layout exists. The skill **discovers** what's there, **classifies** every file by role, **prioritizes** the audit by load weight (root `CLAUDE.md` first, folder `CLAUDE.md`s next, index/README files, then content notes), then **applies the right framework per file role.**

A `CLAUDE.md` is checked against Anthropic's CLAUDE.md rules. A `SKILL.md` is checked against progressive-disclosure rules. An `index.md` / `README.md` is checked against routing/hygiene rules. A daily note is checked for freshness. We don't apply CLAUDE.md rules to skill files or vice versa.

---

## Step 0 — Verify the cwd looks like a vault (light check, no hardcoded shape)

Don't require any specific folder layout. Different vaults have different shapes.

Check (any one of these is sufficient):

```bash
# Workable vault if ANY of these are true:
test -f CLAUDE.md || test -f claude.md         # has a brain file at root
[ "$(find . -maxdepth 4 -name 'CLAUDE.md' | head -1)" ]  # has at least one CLAUDE.md anywhere
[ "$(find . -maxdepth 1 -name '*.md' | wc -l)" -gt 0 ]   # has markdown content at the cwd
```

If **none** are true, stop and tell the user:

> This doesn't look like a markdown-based vault — I couldn't find any `.md` files or a `CLAUDE.md` here. `cd` into your vault root and re-run.

Otherwise, proceed. Tell the user one line:

> Scanning your vault. Discovering, classifying, and auditing every markdown file. Back in a moment with the results.

Proceed silently into Step 1.

---

## Step 1 — Discovery & classification (build the map)

The optimizer's first real job is to figure out **what files exist** and **what role each one plays**. The audit prioritizes what's loaded most often.

### 1.1 — Glob the whole vault

```bash
# every .md file, with the universal skip list applied
find . -name '*.md' -not -path '*/.git/*' -not -path '*/.obsidian/*' \
  -not -path '*/.trash/*' -not -path '*/.claude/worktrees/*' \
  -not -path '*/node_modules/*' -not -path '*/dist/*' -not -path '*/build/*'
```

Cache the full file list. Every later pass operates against this list, not against fresh globs.

### 1.2 — Classify every file by role

Walk the file list and tag each entry with one of these roles. **Order matters** — first match wins.

| Role | Detection |
|---|---|
| `root-claude` | `./CLAUDE.md` or `./claude.md` (cwd root only) |
| `folder-claude` | any other `CLAUDE.md` / `claude.md` in any subfolder |
| `skill` | `SKILL.md` inside a folder also containing `references/` or matching `**/skills/*/SKILL.md` |
| `index` | `index.md` |
| `readme` | `README.md` (case-insensitive) |
| `daily` | matches `Daily/YYYY-MM-DD.md` or `**/Daily/YYYY-MM-DD.md` patterns |
| `meeting` | inside a `meetings/` folder, or filename matches `YYYY-MM-DD - {title}.md` outside `Daily/` |
| `transcript` | inside `*transcripts*/` folders, or files >100KB that look like transcripts |
| `decision` | inside `*decisions*/` folders |
| `template` | inside `*templates*/` folders or filename ends in `-template.md` |
| `context` | inside any `Context/` folder (case-insensitive) |
| `note` | everything else |

Build a structure like:

```json
{
  "root_claude": "./CLAUDE.md",
  "folder_claudes": ["./Projects/CLAUDE.md", "./Team/CLAUDE.md", ...],
  "skills": ["./Skills/foo/SKILL.md", ...],
  "indexes": ["./Projects/index.md", ...],
  "readmes": ["./Projects/talent-signals/README.md", ...],
  "dailies": [...],
  "meetings": [...],
  "transcripts": [...],
  "decisions": [...],
  "templates": [...],
  "context_files": [...],
  "notes": [...],
  "by_folder": {"./Projects": [...files...], ...},
  "stats": {"total_files": N, "total_bytes": B, "folders": F}
}
```

### 1.3 — Presence check (flag missing leaders)

For every folder containing >5 markdown files (excluding skip-listed roles like `daily`, `meeting`, `transcript`):

- If the folder has **no `CLAUDE.md` AND no `index.md` AND no `README.md`**, flag it as **leaderless**.
- If the folder has >15 files and no `CLAUDE.md`, flag it harder ("missing folder-level CLAUDE.md — large folder needs LLM guidance").

For the vault root:

- If `root_claude` is missing entirely, this is a hard finding ("vault has no root CLAUDE.md — Claude has no anchor to start from").

### 1.4 — Prioritization order

The audit checks files in this priority order — most loaded / most blast-radius first:

1. **`root_claude`** — checked against full Anthropic CLAUDE.md rules (size, position, anti-patterns, code-style violations, signature lines, etc.).
2. **`folder_claudes`** — same rules as root but with adjusted size budgets (folder-level CLAUDE.mds can be smaller).
3. **`indexes` + `readmes`** — routing rules: are they actually routing, or are they prose?
4. **`skills`** — progressive-disclosure rules (SKILL.md size, frontmatter, reference depth, reference TOC).
5. **`context_files`** — frontmatter compliance, em-dash, voice match.
6. **`notes`** — wiki-lint (dead links, orphans, stubs), frontmatter, hygiene.
7. **`dailies` / `meetings` / `transcripts` / `decisions`** — surface-level hygiene only (em-dash, duplicate H1). Don't flag size or structure.
8. **`templates`** — skip most checks. Templates are by-design skeletons.

### 1.5 — Show the discovery summary first

Before running any audit pass, render a one-block summary so the user sees what was found:

```markdown
## 📋 Discovery — {N} markdown files across {F} folders

| Role | Count | Notes |
|---|---:|---|
| Root CLAUDE.md | 1 | ✅ found |
| Folder CLAUDE.mds | 14 | covering: Projects, Team, Departments, Resources, ... |
| Indexes / READMEs | 23 | |
| Skills | 6 | |
| Context files | 8 | |
| Notes | 412 | |
| Dailies | 187 | |
| Meetings | 42 | |
| Transcripts | 19 | |
| Decisions | 31 | |
| Templates | 12 | |

**Presence check:**
- ⚠️ {N} folders are leaderless (no CLAUDE.md / index.md / README.md)
- ⚠️ {N} large folders (>15 files) missing a CLAUDE.md
- ✅ Root CLAUDE.md present

Auditing now using the right framework per file role — Anthropic CLAUDE.md rules for CLAUDE.mds, progressive-disclosure for skills, routing rules for indexes, wiki-lint + hygiene for notes.
```

This block goes into the chat once, before any per-pass output. It's how the user knows we actually scanned everything they have, not just the BenAI-shaped subset.

---

## Step 2 — Run the 4 pass groups against the classified map

For each group, **read the corresponding pass-implementation file**, then run every pass it describes — but operate on the classified map from Step 1, applying the right framework per file role.

### Group A — Size & Token Budget

Read: `references/passes-size-tokens.md`. Run A1, A2, A3, A4.

### Group B — Wiki Linting

Read: `references/passes-wiki-lint.md`. Run B1, B2, B3, B4, B5.

> [!important] B1 (dead wikilinks) and B2 (orphans) require building a vault filename index. Build it once and reuse across all B passes.

### Group C — Skills

Read: `references/passes-skills.md`. Run C1, C2, C3, C4, C5.

### Group D — Vault Hygiene

Read: `references/passes-vault-hygiene.md`. Run D1, D2, D3, D4, D5, D6, D7, D8.

### Universal skip list

Every pass skips: `.claude/worktrees/`, `.git/`, `.trash/`, `node_modules/`, `.obsidian/`, `dist/`, `build/`, and any folder containing compiled artifacts (e.g., `Infrastructure/relay-mcp-server-v2/` if it exists).

### Pass-specific exceptions

Some passes have additional skip rules (e.g., B2 orphan detection skips `Daily/`, `index.md`, profile root files). The pass-implementation files document these — follow them exactly.

---

## Step 3 — Render the markdown summary

Output a single clean markdown block grouped by pass group. Use emoji as visual anchors. Format:

```markdown
## 🔍 Vault Audit — {YYYY-MM-DD}

**Score: {score} / 100**

Scanned {N} markdown files across {M} folders. Ran 22 passes.

---

### 📏 A. Size & Token Budget

#### A1 — CLAUDE.md size ({n} flagged)
{table or "✅ All under 200 lines"}

#### A2 — Per-file size budget ({n} flagged)
{table of files >10KB or >100KB}

#### A3 — Token estimate (informational)
- Per-session auto-load: {tokens}
- Total CLAUDE.md tree: {tokens}
- Top 3 reduction targets: {list}

#### A4 — Position effect ({n} flagged)
{table of files with buried critical info}

---

### 🔗 B. Wiki Linting

#### B1 — Dead wikilinks ({n} flagged)
{list, max 10 shown, "...and N more" if truncated}

#### B2 — Orphan notes ({n} flagged)
{list, max 10 shown}

#### B3 — Same-role duplicates ({n} flagged)
{list of overlap candidates}

#### B4 — Routing compliance ({n} flagged)
{vault-root files + unmapped folders}

#### B5 — Stub notes ({n} flagged)
{list, max 10 shown}

---

### 🛠️ C. Skills (Progressive Disclosure)

#### C1 — Skill-vault duplication ({n} flagged)
{table: skill | duplicate ref | vault file}

#### C2 — SKILL.md size ({n} flagged)
{list of skills >500 lines}

#### C3 — Frontmatter validation ({n} flagged)
{list of frontmatter violations}

#### C4 — Reference depth ({n} flagged)
{list of 2-hop references}

#### C5 — Reference TOC ({n} flagged)
{list of refs >100 lines without TOC}

---

### 🧹 D. Vault Hygiene

#### D1 — Frontmatter compliance
- Missing `status:`: {n} files
- Missing `tags:`: {n} files
- Missing `type:`: {n} files
- Missing `project:` / `department:`: {n} files

#### D2 — Filename quality ({n} flagged)
{list of ambiguous filenames}

#### D3 — Index file presence ({n} flagged)
{list of folders >5 files without index}

#### D4 — Em dashes ({n} occurrences across {f} files)
{summary count}

#### D5 — Generic emphasis ({n} flagged)
{list of CLAUDE.md files with overuse}

#### D6 — Code-style rules in CLAUDE.md ({n} flagged)
{list with line excerpts}

#### D7 — H1 duplicating filename ({n} flagged)
{list, max 10 shown}

#### D8 — Project README hygiene ({n} flagged)
{list, max 10 shown}

---

### 📊 Summary

- **Auto-fixable now:** {n} items (dead wikilinks, skill-vault duplicates, em dashes, duplicate H1s)
- **Needs review:** {n} items (orphans, duplicates, routing, READMEs, frontmatter)
- **Manual rewrite needed:** {n} items (oversized CLAUDE.md, oversized files, sparse/bloated READMEs)
- **Informational:** token estimate
```

### Score formula

```
score = 100
  - (A1 size-flagged CLAUDE.md * 5)
  - (A2 oversized files * 2 each, capped at 20)
  - (A4 buried-info files * 1)
  - (B1 dead wikilinks * 1, capped at 30)
  - (B2 orphan notes * 1, capped at 20)
  - (B3 duplicate roles * 3)
  - (B4 routing violations * 5)
  - (B5 stubs * 1, capped at 10)
  - (C1 skill-vault duplicates * 3)
  - (C2 oversized SKILL.md * 2)
  - (C3 frontmatter violations * 1, capped at 20)
  - (C4 reference depth violations * 5)
  - (C5 missing TOC * 1)
  - (D1 missing required fields * 1, capped at 30)
  - (D2 ambiguous filenames * 1, capped at 10)
  - (D3 missing indexes * 1, capped at 10)
  - (D4 em dashes * 1, capped at 20)
  - (D5 generic emphasis * 2)
  - (D6 code-style rules in CLAUDE.md * 2)
  - (D7 duplicate H1 * 1, capped at 20)
  - (D8 README hygiene * 1, capped at 10)
```

Cap at 0.

| Score | Interpretation |
|---|---|
| 90–100 | Well-tuned. Run audit monthly. |
| 70–89 | Visible drift. Address top findings, then re-run. |
| 50–69 | Bloat is hurting per-session performance. Fix before adding more skills. |
| <50 | Vault rot. Major cleanup needed; possibly split or restructure. |

After rendering the block, go directly to Step 4.

---

## Step 4 — Ask what to do (use `AskUserQuestion`)

Use `AskUserQuestion` with **one question, four options.** The summary above gave the full picture; the question is what to do across the audit.

**Question:** *"What should I do with these findings?"*

**Options:**

1. **Apply all auto-fixable items** — wikilink fixes, skill-vault rewrites, em dash replacements (period substitution), duplicate H1 removal. Everything else gets logged for manual review.
2. **Review and choose per category** — separate `AskUserQuestion` calls for each fixable category (wikilinks, skill-vault, em dashes, duplicate H1s).
3. **Just save the report, don't change anything** — write the audit report and exit. Useful for first-time runs or when the user wants to review changes manually.
4. **Show me one item per category before deciding** — render a representative diff for each fixable category, then re-prompt with options 1–3.

If the user picks option 4: show one example diff per fixable category, then re-ask 1–3.

If the user picks option 2: ask one follow-up `AskUserQuestion` per category. Each option: Yes / No / Skip and save report.

---

## Step 5 — Apply approved fixes

Apply in this order (smallest blast radius first):

### Em dash substitution (D4)
- Replace `—` with `. ` (period + space) and `–` with `, ` (comma + space) — most conservative substitutions per project Rule 14.
- Skip lines that are inside code fences or inline code.
- Use `Edit` with `replace_all: true` per file.

### Duplicate H1 removal (D7)
- Remove the matching `# {Title}` line and any blank line immediately following it.
- Use `Edit`.

### Wikilink fixes (B1)
- Replace `[[Old Target]]` with chosen replacement (new `[[match]]` or plain text).
- Preserve surrounding text exactly. Use `Edit`.

### Skill-vault rewrites (C1)
- Update the skill's `SKILL.md` to point at the vault `Context/` path.
- Then `grep` the rest of the skill folder for the duplicate ref filename to confirm it's no longer used.
- If still referenced anywhere → surface the conflict and skip the deletion.
- Otherwise → delete the duplicate ref file via `rm`.

### Failures
If any change fails (file not found, edit conflict, ambiguous match), stop, report which item failed, and ask the user how to proceed. Never silently skip a failure.

### Always preserve
- Files in skip list (`.claude/worktrees/`, `.git/`, `.trash/`, `node_modules/`, `.obsidian/`)
- Code fences (` ``` ` blocks)
- URLs, file paths, frontmatter keys
- Inline code spans

---

## Step 6 — Render and save the HTML dashboard (single output)

The optimizer's single output is one HTML dashboard saved to the vault. No markdown report — the dashboard is the report.

### 6.1 — Compute the metrics

Before applying fixes (Step 5), snapshot per-section token counts. After applying, snapshot again. Compute:

| Variable | Source |
|---|---|
| `{{TOTAL_BEFORE}}`, `{{TOTAL_AFTER}}`, `{{TOTAL_SAVED}}`, `{{TOTAL_PCT}}` | sum across all four groups |
| `{{SCORE_BEFORE}}`, `{{SCORE_AFTER}}` | scoring formula run before & after |
| `{{SCORE_DELTA}}` and `{{SCORE_DELTA_SIGN}}` (`+` or `−`) | `after − before` |
| Per-section: `{{BEFORE}}`, `{{AFTER}}`, `{{SAVED}}`, `{{PCT}}`, `{{WHAT_CHANGED}}` | per A/B/C/D group; if no fixes applied for a group, set `{{SAVED}}=0`, `{{PCT}}=0.0`, `{{WHAT_CHANGED}}="No fixes applied this run"` |
| `{{SESSION_BEFORE}}`, `{{SESSION_AFTER}}`, `{{SESSION_PCT}}` | tokens loaded into auto-context on session start (CLAUDE.md tree) |
| `{{ANNUAL_SAVINGS}}` | `{{TOTAL_SAVED}} × SESSIONS_PER_WEEK × WEEKS_PER_YEAR`, formatted with K/M suffix |
| `{{SESSIONS_PER_WEEK}}` | default `50`, override if user specifies |
| `{{WEEKS_PER_YEAR}}` | default `50` |
| `{{FILES_SCANNED}}`, `{{FOLDERS_COVERED}}` | from Step 1 |
| `{{ORG_NAME}}` | read from `Context/business.md` or `Context/organization.md` (title or `name:` frontmatter); fallback: cwd folder name |
| `{{DATE}}` | `{YYYY-MM-DD}` |
| `{{TIMESTAMP}}` | ISO UTC |
| `{{TOTAL_SUMMARY}}` | one short phrase summarising the run, e.g. `"22 passes · 4 groups touched · score +17"` |

Format integers with thousands separators (e.g. `12,400`). Format percentages to one decimal (`20.7%`).

### 6.2 — Build the HTML

1. Read the template: `${CLAUDE_PLUGIN_ROOT}/skills/os-optimizer/references/report-template.html`.
2. Read the row fragment: `${CLAUDE_PLUGIN_ROOT}/skills/os-optimizer/references/report-row-template.html`.
3. For each of the four groups (A, B, C, D), render one row from the row fragment with the per-section metrics. Concatenate the four rendered rows.
4. Substitute `{{ROWS}}` in the main template with that concatenated string.
5. Substitute every other `{{PLACEHOLDER}}` with its computed value.
6. **Sanity pass:** scan the rendered HTML for any `{{...}}` strings still left. If any remain, fix them or fail loudly — never save a half-rendered file.

### 6.3 — Save to the brain (path is dynamic — discover, don't hardcode)

Pick the save folder using this priority:

1. If `Intelligence/decisions/` exists → use it.
2. Else if `Intelligence/` exists → create `Intelligence/decisions/`.
3. Else if any folder matching `*decisions*/` was found in Step 1's discovery map → use the first one.
4. Else create `audits/` at the cwd root.

Save the path as `{decisions-folder}` and write to `{decisions-folder}/{YYYY-MM-DD}-vault-audit.html`.

Read the file back to confirm content present (not just file present). On mismatch, retry once, then fail loudly.

### 6.4 — Show in chat

After saving, output the HTML directly in the chat response so the user sees the dashboard inline. Use a markdown HTML block (no escaping). The user should see the full styled dashboard, not just a "saved" message.

End with one short line below the dashboard:

> Saved to `{decisions-folder}/{YYYY-MM-DD}-vault-audit.html`. Open in a browser to share or print.

Stop. Do not propose follow-up actions.

---

## Rules — what to never do

- **Never** apply a change the user didn't approve through `AskUserQuestion`.
- **Never** rewrite a CLAUDE.md file automatically (Pass A1 is flag-only).
- **Never** auto-rename files, even if the filename is ambiguous (D2 is flag-only).
- **Never** auto-add frontmatter (D1 is flag-only — values need content understanding).
- **Never** delete a file before grepping the rest of the vault for references to its filename.
- **Never** modify files in skip list folders.
- **Never** invent a fix you can't show as a diff. If you can't show before/after, surface it as a flag for manual review.
- **Never** skip the dashboard. Saving `{decisions-folder}/{YYYY-MM-DD}-vault-audit.html` (path discovered per Step 6.3, not hardcoded) and showing it in chat is the single sanctioned output.
- **Never** assume a vault shape. Step 0 must be a light "is there markdown here?" check; Step 1 must discover and classify before any pass runs.
- **Never** ship a half-rendered template. If any `{{placeholder}}` survives the substitution pass, fail loudly instead of saving.
- **Never** paraphrase a framework rule from memory when the user asks why something is flagged. Read the relevant file in `references/` and cite it.
- **Never** apply em dash substitutions inside code blocks, URLs, or inline code.

---

## Why this skill exists

Five frameworks plus practitioner field notes converge on one conclusion: vaults rot without active maintenance. Karpathy calls it the **lint** operation. Anthropic calls it the **pruning test**. Chroma calls it **context rot**. Caveman calls it **token discipline**. The 22 passes encode all of them in one run, ask what to do via `AskUserQuestion`, and apply only what the user approves.

Run weekly while the vault is growing. Monthly once stable. Each run appends a dated decision file so the user can watch the score climb.

For the deep rules behind each pass, read the relevant framework file and pass-implementation file. Each is complete on its own — TOC at the top, full rules, dos, don'ts, verbatim quotes, audit signals, and source URLs.
