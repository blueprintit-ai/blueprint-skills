---
name: bp-optimizer
description: "Framework-driven audit and optimizer for any markdown vault. Discovers and classifies every .md file, then applies 7 frameworks one-by-one — Anthropic CLAUDE.md (F1), Karpathy LLM Wiki (F2), Caveman Compression (F3), Chroma Context Rot (F4), Anthropic Memory (F5), Progressive Disclosure (F6), General Hygiene (G7). Each framework's auditable signals run as judgment-based checks: triggers surface candidates, the agent reads context and reasons, and every finding includes a reasoning sentence specific to the case. Audits every file (only technical skips: .git, .obsidian, .trash, node_modules, dist, build). Asks per-framework what to fix via AskUserQuestion, applies approved fixes, saves a comprehensive HTML dashboard grouped by framework, opens it in the browser, and surfaces it as a renderable artifact. TRIGGERS: os optimizer, optimize vault, vault audit, lint vault, vault health check, audit my brain, second brain audit, clean up vault, framework audit. Run from the user's vault root."
---

# Vault Optimizer

Apply 6 frameworks + general hygiene to every markdown file in the vault. For each framework, read its pass-implementation file, run every check the framework defines, log findings, ask per-framework what to fix, apply approved fixes. Save one comprehensive HTML report grouped by framework. **Do not inline the HTML in chat — only the saved path and a one-paragraph summary.**

## Frameworks

| # | Framework | Reference (the *why*) | Pass file (the *how*) | Applies to |
|---|---|---|---|---|
| F1 | Anthropic CLAUDE.md | `references/anthropic-claude-md.md` | `references/passes-anthropic-claude-md.md` | every `CLAUDE.md` |
| F2 | Karpathy LLM Wiki | `references/karpathy-llm-wiki.md` | `references/passes-karpathy-wiki.md` | wiki content notes |
| F3 | Caveman compression | `references/caveman-compression.md` | `references/passes-caveman.md` | instruction-layer files |
| F4 | Chroma context rot | `references/chroma-context-rot.md` | `references/passes-chroma-context-rot.md` | every `.md` |
| F5 | Anthropic Memory | `references/anthropic-managed-memory.md` | `references/passes-anthropic-memory.md` | every `.md` |
| F6 | Progressive Disclosure | `references/progressive-disclosure.md` | `references/passes-progressive-disclosure.md` | every `SKILL.md` |
| G7 | General Hygiene | (project rules + practitioner notes) | `references/passes-general-hygiene.md` | every `.md` |

When running a check, **read the pass-implementation file** and follow its regex / heuristic / finding format exactly. Don't paraphrase. Cite the framework reference in every finding.

## Flow

1. **Verify the cwd looks like a vault** — light check (Step 0)
2. **Discover & classify every `.md` file** — only technical skips (Step 1)
3. **Iterate frameworks F1 → G7**, applying each framework's lens with judgment to its scoped files; every finding includes reasoning specific to the case (Step 2)
4. **Aggregate findings, compute health score** (Step 3)
5. **Ask per-framework what to fix via AskUserQuestion** (Step 4)
6. **Apply approved fixes** (Step 5)
7. **Render HTML dashboard, save, open in browser, emit as artifact** (Step 6)

---

## Step 0 — Verify the cwd looks like a vault

Don't require any specific folder layout. Check (any one is sufficient):

```bash
test -f CLAUDE.md || test -f claude.md
[ "$(find . -maxdepth 4 -name 'CLAUDE.md' | head -1)" ]
[ "$(find . -maxdepth 1 -name '*.md' | wc -l)" -gt 0 ]
```

If none are true → stop:

> This doesn't look like a markdown vault — no `.md` files or `CLAUDE.md` found. `cd` into your vault root and re-run.

Otherwise tell the user one line:

> Auditing your vault against 6 frameworks. Every file gets every check that applies to its role. Saving the report when done.

Proceed silently into Step 1.

---

## Step 1 — Discover & classify every `.md` file

### 1.1 — Universal glob (every file audited)

```bash
find . -name '*.md' \
  -not -path '*/.git/*' \
  -not -path '*/.obsidian/*' \
  -not -path '*/.trash/*' \
  -not -path '*/.claude/worktrees/*' \
  -not -path '*/node_modules/*' \
  -not -path '*/dist/*' \
  -not -path '*/build/*'
```

**No role-based skips.** No "templates skipped", no "Daily skipped", no "Onboarding skipped". Every `.md` outside the technical skip list above gets audited against every framework rule that applies to its role. Classification routes the right rules to the right files; classification does NOT exclude files.

### 1.2 — Classify each file by role (first match wins)

| Role | Detection |
|---|---|
| `root-claude` | `./CLAUDE.md` or `./claude.md` (cwd root only) |
| `folder-claude` | any other `CLAUDE.md` / `claude.md` in subfolders |
| `claude-rules` | files inside `.claude/rules/` |
| `skill` | `SKILL.md` files (anywhere) |
| `index` | `index.md` (case-insensitive) |
| `readme` | `README.md` (case-insensitive) |
| `daily` | matches `\d{4}-\d{2}-\d{2}\.md` inside any `Daily/` |
| `meeting` | inside `*meetings*/` or filename matches `\d{4}-\d{2}-\d{2} - .+\.md` outside `Daily/` |
| `transcript` | inside `*transcripts*/` or files >100KB |
| `decision` | inside `*decisions*/` |
| `template` | inside `*templates*/` or filename ends `-template.md` |
| `context` | inside any `Context/` (case-insensitive) |
| `note` | everything else |

Build the classification map:

```json
{
  "root_claude": "./CLAUDE.md",
  "folder_claudes": [...],
  "claude_rules": [...],
  "skills": [...],
  "indexes": [...],
  "readmes": [...],
  "dailies": [...],
  "meetings": [...],
  "transcripts": [...],
  "decisions": [...],
  "templates": [...],
  "context_files": [...],
  "notes": [...],
  "by_folder": {...},
  "stats": {"total_files": N, "total_bytes": B, "folders": F}
}
```

### 1.3 — Build supporting indexes (used by F2/F4)

| Index | Built from | Used by |
|---|---|---|
| `vault_filename_index` | every `.md` basename, lowercased, with and without extension | F2.2, F2.4 |
| `inbound_link_index` | grep across vault for `\[\[name(\||\]|#)` | F2.3, F2.4 |
| `routing_table` | root CLAUDE.md routing/knowledge-routing section | F2.6 |
| `top_level_entries` | `find . -maxdepth 1` | F2.6 |
| `headers_index` | per-file H2/H3 list with line numbers + byte sizes | F3.6, F5.2 |
| `protected_zones_map` | per-file map of code/URL/path/frontmatter/wikilink spans | F3.x, G7.1 |

### 1.4 — Show classification summary in chat (one block, before any framework runs)

```markdown
## 📋 Discovery — {N} markdown files across {F} folders, {B-formatted} total

| Role | Count |
|---|---:|
| Root CLAUDE.md | 1 |
| Folder CLAUDE.mds | {n} |
| Skills (SKILL.md) | {n} |
| .claude/rules | {n} |
| Indexes / READMEs | {n} |
| Context files | {n} |
| Notes | {n} |
| Dailies | {n} |
| Meetings | {n} |
| Transcripts | {n} |
| Decisions | {n} |
| Templates | {n} |

**Framework targets (every file in scope is audited):**
- F1 Anthropic CLAUDE.md → {n} CLAUDE.md files
- F2 Karpathy Wiki → {n} content notes (notes + context + decision + meeting + index + readme) + 1 schema doc check
- F3 Caveman → {n} instruction-layer files (CLAUDE.md + SKILL.md + .claude/rules + skill references)
- F4 Chroma Context Rot → {N} files (every `.md`)
- F5 Anthropic Memory → {N} files (every `.md`)
- F6 Progressive Disclosure → {n} skills
- G7 General Hygiene → {N} files

Running F1 now…
```

---

## Step 2 — Iterate frameworks F1 → G7 with judgment

**This is not a regex pass.** For each framework, read its pass-implementation file, then apply every check it defines to the files in that framework's scope. Triggers in the pass files surface candidates; the agent reads context and judges each candidate before producing a finding. Every finding includes `reasoning` specific to the case.

Why: a regex match on `\bjust\b` flags "just run X" (where "just" is doing real work — contrasting with running multiple) the same as "It's just a quick check" (where it's filler). Only an agent reading the line in context can tell which is which. The same applies to "be careful" (sometimes a closing reminder, sometimes a vague platitude), `IMPORTANT:` (sometimes earned, sometimes inflation), `voice.md` + `brand.md` (sometimes overlapping, sometimes intentionally separated), and most other framework signals.

### 2.1 — For each framework F1, F2, F3, F4, F5, F6, G7 (in this order)

For each framework:

1. **Read the pass-implementation file** for that framework (e.g., `references/passes-anthropic-claude-md.md` for F1). Cache it for the duration of the framework run.
2. **Determine the file scope** from the table at the top of this SKILL.md (e.g., F1 = every CLAUDE.md; F6 = every SKILL.md; F4/F5/G7 = every `.md`).
3. **For each check in the pass file**:
   - Apply the **trigger heuristic** (regex / metric / structural pattern) to surface candidates fast. Some checks have no trigger — the file itself is the candidate.
   - For each candidate, **read the surrounding 5–15 lines** with the `Read` tool, then apply the **agent-judgment criteria** the pass file lists. Read other files (linked targets, sibling clusters, the file's index) when judgment requires it.
   - Decide: does this case actually violate the framework rule **in this file's specific context**? Or is it a false positive (the pass file lists common ones to skip)?
   - If real → produce a finding. If not → drop it; the trigger was a candidate, not a verdict.
   - **Every finding includes a `reasoning` field** (1–2 sentences specific to this case, not a generic restatement of the rule).
4. **Run the framework's vault-wide checks** (using indexes from Step 1.3): orphan detection, dead wikilinks, distractor pairs, schema compliance, etc. — see each pass file's "vault-wide" sections.
5. **Emit one progress line** when the framework completes:

   > F1 Anthropic CLAUDE.md — read 14 CLAUDE.md files, judged 312 candidates → 22 findings (5 fail · 17 warn)

   The `judged` count vs `findings` count is a sanity check: if they're roughly equal, the run was lazy (regex candidates became findings without judgment); if `judged` ≫ `findings`, judgment is filtering false positives — that's the intended behavior.

### 2.2 — Finding schema (every framework, every path)

```json
{
  "framework": "F1",
  "check_id": "F1.2",
  "check_name": "Specificity heuristic",
  "path": "./Projects/foo/CLAUDE.md",
  "line": 42,
  "severity": "warn",
  "excerpt": "Be careful with auth",
  "reasoning": "This rule sits in the top half of a CLAUDE.md that's otherwise a routing index — there's no specific auth boundary, file path, or function named anywhere else. As a primary rule it falls into the 35%-compliance bucket; either anchor it to a specific path/function or remove it.",
  "action": "Either delete or rewrite as 'All /api/admin/* routes must call requireAdmin() from src/auth/middleware.ts'.",
  "fixable": false,
  "fixed": false,
  "citation": "anthropic-claude-md.md → Specificity beats vagueness"
}
```

The `reasoning` field is mandatory. Every finding has it.

The `fixable` field marks whether the check supports an auto-fix (set by the pass file).
The `fixed` field is set by **Step 5** after a fix lands successfully. It starts `false`. The HTML render uses these two flags to display three states:
- `fixable: false` → grey FLAG-ONLY pill (manual review)
- `fixable: true && fixed: false` → yellow FIXABLE pill (could be fixed; user skipped or denied)
- `fixable: true && fixed: true` → green FIXED pill (applied this run)

---

## Step 3 — Aggregate findings + compute score

For each framework F1–G7, count: total findings, severity breakdown (fail/warn/info), fixable count, files touched.

### Score formula (framework-weighted)

```
For each framework:
  deduction = (fail_count × 5) + (warn_count × 1)
  capped_deduction = min(deduction, 25)
score = max(0, 100 - sum(capped_deduction for F1..G7))
```

| Score | Interpretation |
|---|---|
| 90–100 | Well-tuned. Run audit monthly. |
| 70–89 | Visible drift. Address top findings. |
| 50–69 | Bloat is hurting performance. |
| <50 | Vault rot. Major cleanup needed. |

After scoring, **do not render a long markdown summary in chat**. Emit one short block:

```
✅ All 7 frameworks applied.

| Framework | Files | Checks | Findings | Fail | Warn | Fixable |
|---|---:|---:|---:|---:|---:|---:|
| F1 Anthropic CLAUDE.md | … | … | … | … | … | … |
| F2 Karpathy Wiki | … | … | … | … | … | … |
| F3 Caveman | … | … | … | … | … | … |
| F4 Chroma Context Rot | … | … | … | … | … | … |
| F5 Anthropic Memory | … | … | … | … | … | … |
| F6 Progressive Disclosure | … | … | … | … | … | … |
| G7 Hygiene | … | … | … | … | … | … |
| **TOTAL** | … | … | … | … | … | … |

Score: {score_before}/100. Asking per-framework what to fix…
```

---

## Step 4 — Ask per-framework what to fix (AskUserQuestion) — STRICT

**The most common failure mode of this skill is the agent batching the asks or skipping frameworks.** Don't. Every framework with a fixable finding fires its own `AskUserQuestion`. No batching. No skipping because the count is small.

**Fixable check IDs (the only IDs that produce `fixable: true`):**

| Framework | Fixable IDs |
|---|---|
| F2 | F2.2 (dead wikilinks), F2.4 (missing cross-refs — opt-in) |
| F3 | F3.1–F3.4 (caveman substitutions — opt-in) |
| F6 | F6.11 (skill-vault duplication) |
| G7 | G7.1 (em dashes), G7.3 (H1 = filename; deduplicates F1.10) |

F1, F4, F5 never have fixable findings — every check is flag-only. Don't prompt; surface under manual review in the report.

**Loop:**

```
for framework in [F2, F3, F6, G7]:
    if fixable_count[framework] == 0: continue
    fire AskUserQuestion("{Framework name} ({Fx}) — {N} fixable. What should I do?")
    options:
      1. Apply all fixable items in this framework
      2. Show me one example diff first (renders diff, re-prompts 1/3/4)
      3. Skip this framework (findings stay flag-only in report)
      4. Pick item-by-item (sub-AskUserQuestion per finding: Yes/No/Skip-rest)
    record per-finding approval status
```

Failing to fire one of these prompts when `fixable_count > 0` is a bug, not a feature.

**Per-item confirmation required for these checks (bulk-apply is unsafe):**
- **F2.2 dead wikilinks**: each needs the right repoint target. Bulk = apply agent top-1; low-confidence = log as skipped. Walk = pick per item.
- **F2.4 missing cross-refs**: same — confidence drives bulk vs walk; default walk.
- **F3.1–F3.4 caveman**: bulk-safe per file (agent filtered candidates via reasoning), but user opts in per file. Prompt: "Apply to all N files" / "pick files".

**Track approvals** in a per-framework structure (`{choice, approved_finding_ids, skipped_finding_ids}`); drives Step 5 and the per-finding `fixed:` flag.

---

## Step 5 — Apply approved fixes (and mark `fixed:true` per finding)

Apply in this order (smallest blast radius first). For every finding the agent fixes, **set `fixed: true` on the finding object**. The HTML render uses this flag to show FIXED vs FIXABLE pills. A finding with `fixable: true && fixed: false` got skipped or denied — the report makes that visible.

### 5.1 — Em dashes (G7.1)
- For each approved finding: replace `—` → `. `, `–` → `, ` in stripped body only.
- Re-strip protected zones after; if any code/URL/wikilink was touched → revert that file's change AND keep `fixed: false`.
- Use `Edit` with `replace_all: true` per file.
- Mark `fixed: true` on every G7.1 finding whose file was successfully fixed.

### 5.2 — Duplicate H1 (G7.3 / F1.10)
- Remove the H1 line and any blank line immediately following.
- Use `Edit`. Mark `fixed: true`.

### 5.3 — Wikilink fixes (F2.2)
- For each finding the user approved (bulk = top-1 suggestion, walk = chosen target): replace `[[Old Target]]` with the picked replacement.
- Preserve surrounding text byte-for-byte.
- Mark `fixed: true` per finding fixed; `fixed: false` for any skipped or low-confidence ones the user said no to.

### 5.4 — Skill-vault rewrites (F6.11)
- Update SKILL.md to read the vault `Context/` path instead of the duplicate ref.
- Grep the rest of the skill folder for the duplicate ref filename.
- If still referenced → surface conflict, skip deletion, mark `fixed: false`.
- Otherwise → `rm` the duplicate, mark `fixed: true`.

### 5.5 — Caveman substitutions (F3.1, F3.2, F3.3, F3.4) — only if user opted in per file
- Apply substitution table from `references/passes-caveman.md` to the stripped body.
- Re-strip protected zones; if any was modified → abort the fix on that file, report, mark `fixed: false` for that file's findings.
- Mark `fixed: true` on every F3.x finding for files the agent successfully substituted.

### 5.6 — Verify fixed-counts add up

After applying:
- `total_fixed` (all frameworks) = sum of findings with `fixed: true`.
- `total_fixable_not_fixed` = sum of findings with `fixable: true && fixed: false`.
- `total_flag_only` = sum of findings with `fixable: false`.

These three should equal `total_findings`. If not, the orchestrator has a bookkeeping bug — log the mismatch and continue (HTML still renders correctly from per-finding flags).

### Failure handling
If any fix fails (file missing, edit conflict, ambiguous match, protected-zone violation) → stop, report which item failed, ask the user how to proceed. Never silently skip a failure.

### Always preserve
- Files in technical skip list (`.git`, `.obsidian`, `.trash`, `node_modules`, `dist`, `build`).
- Code fences, inline code, URLs, file paths, frontmatter keys, wikilinks, table delimiters, headings, dates, version numbers.

---

## Step 6 — Render, save, open, and surface the HTML

### 6.1 — Compute per-framework metrics

Snapshot before/after per framework:

| Variable | Source |
|---|---|
| `{{F1_FILES}}`, `{{F1_CHECKS}}`, `{{F1_FINDINGS}}`, `{{F1_FAIL}}`, `{{F1_WARN}}`, `{{F1_FIXABLE}}`, `{{F1_FIXED}}`, `{{F1_DETAILS}}` | F1 bucket |
| same for F2, F3, F4, F5, F6, G7 | each bucket |
| `{{TOTAL_FIXABLE}}` | count of all findings with `fixable: true` |
| `{{TOTAL_FIXED}}` | count of all findings with `fixed: true` |
| `{{TOTAL_FIXABLE_NOT_FIXED}}` | count of findings with `fixable: true && fixed: false` (skipped/denied) |
| `{{TOTAL_BEFORE}}`, `{{TOTAL_AFTER}}`, `{{TOTAL_SAVED}}`, `{{TOTAL_PCT}}` | sum across all frameworks |
| `{{SCORE_BEFORE}}`, `{{SCORE_AFTER}}`, `{{SCORE_DELTA}}`, `{{SCORE_DELTA_SIGN}}` | scoring formula before & after |
| `{{SESSION_BEFORE}}`, `{{SESSION_AFTER}}`, `{{SESSION_PCT}}` | root CLAUDE.md token count before & after |
| `{{ANNUAL_SAVINGS}}` | `{{TOTAL_SAVED}} × SESSIONS_PER_WEEK × WEEKS_PER_YEAR`, K/M suffix |
| `{{SESSIONS_PER_WEEK}}` (default 50) | user override if specified |
| `{{WEEKS_PER_YEAR}}` (default 50) | — |
| `{{FILES_SCANNED}}`, `{{FOLDERS_COVERED}}` | from Step 1 |
| `{{ORG_NAME}}` | `Context/business.md` or `Context/organization.md` title or `name:` frontmatter; fallback cwd folder name |
| `{{DATE}}`, `{{TIMESTAMP}}` | today (YYYY-MM-DD) and ISO UTC |

For each framework's `{{Fx_DETAILS}}`: render the findings list as HTML (severity pills, paths, excerpts, actions, framework citation). Cap at top-25 findings per framework — if more, append "and N more flagged in {decisions-folder}/{date}-vault-audit-findings.json".

Format integers with thousands separators. Format percentages to one decimal.

### 6.2 — Build the HTML

Templates (read once, substitute many times):

| File | Used as |
|---|---|
| `references/report-template.html` | main shell |
| `references/report-row-template.html` | one row per framework in the summary table |
| `references/report-section-template.html` | one detail section per framework |
| `references/report-finding-template.html` | one card per finding inside a detail section |

Steps:
1. Read all four templates.
2. For each framework F1..G7:
   - Render one row from `report-row-template.html` with the framework's metrics → append to `{{ROWS}}` accumulator.
   - For each finding (cap at top-25 per framework, ranked: fixed first, then fail before warn, then by check ID): render one card from `report-finding-template.html` → append to that section's `{{FINDINGS_HTML}}`. **HTML-escape** `EXCERPT`, `REASONING`, and `ACTION` (`<`, `>`, `&`, `"`). The `REASONING` field is mandatory — if the finding has no reasoning text, the skill is bugged; fail loudly.
   - Compute `{{STATUS_PILL}}` per finding:
     - `fixable: false` → `<span class="pill flag">FLAG-ONLY</span>`
     - `fixable: true && fixed: false` → `<span class="pill fixable">FIXABLE · NOT APPLIED</span>`
     - `fixable: true && fixed: true` → `<span class="pill fixed">FIXED THIS RUN</span>`
   - If 0 findings: leave `{{FINDINGS_HTML}}` empty and substitute `{{CLEAN_STATE}}` with `<div class="clean">✅ All checks passed. No findings for this framework.</div>`.
   - If total findings > 25: substitute `{{MORE_NOTE}}` with `<p class="more">…and {N} more findings logged in {YYYY-MM-DD}-vault-audit-findings.json.</p>`. Otherwise leave empty.
   - Render the section from `report-section-template.html` → append to `{{DETAILS}}` accumulator.
3. Substitute `{{ROWS}}` and `{{DETAILS}}` in the main template.
4. Substitute every other `{{PLACEHOLDER}}` (header stats, score, session impact, etc.).
5. **Sanity pass:** scan the rendered HTML for any leftover `{{...}}` or `{{ }}`. If any remain → fail loudly, never save a half-rendered file.

The `{{FRAMEWORK_WHY}}` for each section comes from the matching framework reference's "Core thesis" — one short paragraph max. Fixed strings:

- F1: "Anthropic guidance: keep CLAUDE.md the smallest concrete set of instructions that survives the pruning test. Specific rules earn ~89% compliance; vague rules get ~35%."
- F2: "Karpathy's LLM Wiki: knowledge is compiled once and kept current. Lint catches dead links, orphans, contradictions, missing cross-references, and undigested sources."
- F3: "Caveman compression: every token competes for attention. Strip filler, hedging, pleasantries, and verbose connectors from the agent-facing instruction layer."
- F4: "Chroma context rot: every model degrades with length; distractors hurt; position matters. Lead with the load-bearing rule and keep the auto-load budget tight."
- F5: "Anthropic Memory: per-file ≤100KB / ~25K tokens (recommended <10KB). Multiple focused files beat one mega-file. The agent navigates by name."
- F6: "Progressive Disclosure: the context window is a public good. Skill metadata loads always; bodies on relevance; references on demand. Keep references one hop deep."
- G7: "Project rules and practitioner field notes: em-dash discipline, frontmatter compliance, no H1 duplicating filename, README hygiene."

### 6.3 — Save (path discovered, not hardcoded)

Pick the save folder using this priority:
1. `Intelligence/decisions/` exists → use it.
2. `Intelligence/` exists → create `Intelligence/decisions/`.
3. Any folder matching `*decisions*/` was discovered in Step 1 → use the first one.
4. Else create `audits/` at the cwd root.

Save HTML to `{decisions-folder}/{YYYY-MM-DD}-vault-audit.html`.
Save the raw findings JSON to `{decisions-folder}/{YYYY-MM-DD}-vault-audit-findings.json` (so users can mine the full list).

Read the HTML back to confirm content present (not just file present). On mismatch → retry once → fail loudly.

### 6.4 — Open + render + summarize (final response, in this order)

**Part 1 — open in browser.** `Bash`: `open "{path}"` (macOS) / `xdg-open` (Linux) / `start` (Windows).

**Part 2 — emit the full saved HTML inside an `html` code fence.** Runtimes with artifact support (claude.ai, Claude Desktop) render it as a side panel; CLI shows it as a code block (browser already opened in Part 1). This is the only place HTML appears in chat — don't dump fragments mid-run, don't paste it twice, don't wrap commentary around it.

**Part 3 — summary (after the HTML, no commentary in between):**

```
✅ Audit complete.
File: {decisions-folder}/{YYYY-MM-DD}-vault-audit.html
JSON sidecar: {decisions-folder}/{YYYY-MM-DD}-vault-audit-findings.json
Score: {score_before} → {score_after} ({delta_sign}{delta})
{N} files audited · {fail_total} fail · {warn_total} warn · {fixed_total} of {fixable_total} fixable applied
Tokens saved: {total_saved}/session (~{annual_savings}/year at {sessions}/week)
```

Stop. Do not propose follow-up actions.

---

## Rules — what to never do

- **Never** apply a change the user didn't approve via `AskUserQuestion`.
- **Never** auto-rewrite a CLAUDE.md (F1 is flag-only).
- **Never** auto-rename files (F5.3 / F5.5 are flag-only — renames need user input).
- **Never** auto-add frontmatter (G7.2 is flag-only).
- **Never** delete a file before grepping for references.
- **Never** modify files in the technical skip list (`.git`, `.obsidian`, `.trash`, `node_modules`, `dist`, `build`).
- **Never** apply caveman substitutions (F3) without user opt-in per file.
- **Never** apply caveman/em-dash substitutions inside protected zones (code, URLs, paths, frontmatter, wikilinks, headings, table delimiters, dates).
- **Never** skip a file because of its role. The classification routes rules; it never excludes files.
- **Never** skip a framework. F1–G7 all run every audit.
- **Never** paraphrase a framework rule from memory when surfacing a finding. Read the relevant pass-implementation file when running its checks; cite the framework in the finding.
- **Never** ship a half-rendered template. If any `{{placeholder}}` survives → fail.
- **Never** dump partial HTML mid-run. The full HTML appears once, at the end (Step 6.4 Part 2), so the runtime can render it as an artifact / side panel. The browser also opens via `Bash open`. Don't paste HTML twice; don't paste partial fragments while findings are still being collected.

---

## Related skills

- `/bp-audit` — operational health check. Scores the vault across Context, Connections, Capabilities, and Cadence. Also surfaces the Automation Ladder (L0-L4) showing where each shop workflow currently sits and what the next step up looks like. Run `/bp-audit` first if the vault is new or underused — it tells you what to fix at a business level. `/bp-optimizer` tells you what to fix at a file quality level. They are complementary, not redundant.

## Why this skill exists

Six frameworks plus practitioner field notes converge on one conclusion: vaults rot without active maintenance. Karpathy calls it **lint**. Anthropic calls it the **pruning test** + the **memory budget**. Chroma calls it **context rot**. Caveman calls it **token discipline**. Progressive disclosure calls it **layering**. The audit encodes every auditable signal from each framework as a discrete check, applies them all on every run, asks per-framework what to fix, and saves a categorized HTML dashboard.

Run weekly while the vault is growing. Monthly once stable. Each run appends a dated dashboard so the user can watch the score climb.

For the deep rules behind each pass, read the relevant `references/{framework}.md` and `references/passes-{framework}.md`. Each is complete on its own — TOC, full rules, exact regex, finding format, source URLs.
