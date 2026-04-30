---
name: vault-audit
description: "Comprehensive multi-pass audit on a second brain vault. 22 passes across 4 groups: size & tokens, wiki linting (dead links, orphans, duplicates, stubs), skills (vault duplication, frontmatter, references depth), and vault hygiene (frontmatter compliance, filename quality, em dashes, CLAUDE.md code-style, README hygiene). Presents a markdown summary, approves fixes per category via AskUserQuestion, applies what's approved, saves a dated report to Intelligence/decisions/. Encodes 5 frameworks (Anthropic CLAUDE.md, Karpathy Wiki lint, Caveman compression, Chroma context rot, Anthropic Memory). TRIGGERS: vault audit, lint vault, vault health check, audit my brain, second brain audit, clean up vault, vault dead links, find duplicate context, find orphan notes, frontmatter compliance, em dash audit. Run from the user's vault root."
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

1. **Verify the cwd is a vault** (Step 0)
2. **Run all 4 pass groups** silently — collect findings (Step 1)
3. **Render a clean markdown summary** (Step 2)
4. **Ask what to do per category** with `AskUserQuestion` (Step 3)
5. **Apply approved fixes** (Step 4)
6. **Save the dated report** to `Intelligence/decisions/{YYYY-MM-DD}-vault-audit.md` (Step 5)

---

## Step 0 — Verify the working directory is a vault

Check:

```
test -f CLAUDE.md && test -d Context
```

If either is missing, stop and tell the user:

> This skill needs to run from your vault's root directory. I expected to find a `CLAUDE.md` file and a `Context/` folder here. `cd` into your vault and re-run.

Otherwise, tell the user:

> Auditing your vault. Running 22 passes across 4 groups (size & tokens, wiki lint, skills, vault hygiene). Back in a moment with a summary.

Proceed silently.

---

## Step 1 — Run the 4 pass groups (collect, don't render)

For each group, **read the corresponding pass-implementation file**, then run every pass it describes.

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

## Step 2 — Render the markdown summary

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

After rendering the block, go directly to Step 3.

---

## Step 3 — Ask what to do (use `AskUserQuestion`)

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

## Step 4 — Apply approved fixes

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

## Step 5 — Save the dated report

Save to `Intelligence/decisions/{YYYY-MM-DD}-vault-audit.md`. Create the folder if needed.

```markdown
---
type: decision
date: {YYYY-MM-DD}
status: completed
tags: [vault-audit, vault-health, token-efficiency, lint, frontmatter, hygiene]
---

# Vault Audit — {YYYY-MM-DD}

## Score
- Before: {score-before} / 100
- After:  {score-after} / 100

## Scope
- Files scanned: {N}
- Folders covered: {M}
- Passes run: 22 across 4 groups (A: size/tokens, B: wiki lint, C: skills, D: hygiene)

## Token impact
- Per-session auto-load: {before-tokens} → {after-tokens} tokens ({delta-pct}%)
- Annual savings (50 sessions/week): ~{annual} tokens

## Applied ({count})
Group A: {n}
Group B: {n}  (e.g., wikilink fixes, em dash substitutions)
Group C: {n}  (e.g., skill-vault rewrites)
Group D: {n}  (e.g., duplicate H1 removals)

- {one line per applied change with file path and brief description}

## Skipped ({count})
- {one line per skipped change with reason}

## Flagged for manual review ({count})
Grouped by severity:
- **Fail:** {n} (oversized files, routing violations, frontmatter limit failures)
- **Warn:** {n} (orphans, stubs, generic emphasis, sparse READMEs, etc.)

- {one line per item with file path and recommended action}

## Frameworks encoded
- Anthropic CLAUDE.md best practices → `references/anthropic-claude-md.md`
- Karpathy LLM Wiki lint → `references/karpathy-llm-wiki.md`
- Caveman compression → `references/caveman-compression.md`
- Chroma context rot → `references/chroma-context-rot.md`
- Anthropic Managed Memory → `references/anthropic-managed-memory.md`
- Progressive disclosure → `references/progressive-disclosure.md`
- Practitioner field notes → `references/practitioner-notes.md`

## Pass implementations
- `references/passes-size-tokens.md` — A1–A4
- `references/passes-wiki-lint.md` — B1–B5
- `references/passes-skills.md` — C1–C5
- `references/passes-vault-hygiene.md` — D1–D8

## Next run
- Suggested cadence: weekly while the vault is growing, monthly once stable.
- Re-run by invoking the `vault-audit` skill from the vault root.
```

After writing the report, tell the user **one line**:

> ✅ Audit complete. Applied {n} fixes across {g} groups. {m} skipped. {k} flagged for manual review. Full report at `Intelligence/decisions/{YYYY-MM-DD}-vault-audit.md`.

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
- **Never** skip the dated report. The decision file is the audit trail.
- **Never** paraphrase a framework rule from memory when the user asks why something is flagged. Read the relevant file in `references/` and cite it.
- **Never** apply em dash substitutions inside code blocks, URLs, or inline code.

---

## Why this skill exists

Five frameworks plus practitioner field notes converge on one conclusion: vaults rot without active maintenance. Karpathy calls it the **lint** operation. Anthropic calls it the **pruning test**. Chroma calls it **context rot**. Caveman calls it **token discipline**. The 22 passes encode all of them in one run, ask what to do via `AskUserQuestion`, and apply only what the user approves.

Run weekly while the vault is growing. Monthly once stable. Each run appends a dated decision file so the user can watch the score climb.

For the deep rules behind each pass, read the relevant framework file and pass-implementation file. Each is complete on its own — TOC at the top, full rules, dos, don'ts, verbatim quotes, audit signals, and source URLs.
