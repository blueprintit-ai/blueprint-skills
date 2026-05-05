# Audit passes — Wiki Linting

## Contents

1. [B1: Dead wikilinks](#b1-dead-wikilinks)
2. [B2: Orphan notes](#b2-orphan-notes)
3. [B3: Same-role duplicate files](#b3-same-role-duplicate-files)
4. [B4: Routing compliance](#b4-routing-compliance)
5. [B5: Stub notes](#b5-stub-notes)

Skip list: same as size passes. Plus `Daily/` for orphan detection (daily notes are intentional roots).

---

## B1: Dead wikilinks

**Source:** `references/karpathy-llm-wiki.md` (lint operation: dead links are failures).

**What:** every `[[wikilink]]` whose target doesn't resolve to a real file.

**How:**
- Glob `**/*.md` with skip list.
- Extract every `[[wikilink]]` target via regex: `\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]`. Strip section anchors (`#`) and display aliases (`|`).
- Build vault filename index: every `.md` file's basename (with and without extension), case-insensitive.
- For each wikilink target, check the index. If no match → dead link.
- For each dead link, compute the top 3 closest filenames by Levenshtein distance for the "repoint" suggestion.

**Finding format:**
```
{file}:{line} → [[{target}]]
Context: "{surrounding line}"
Closest matches: {top-3 by Levenshtein}
Severity: warn
Action: (a) remove link keep text, (b) repoint to {best match}
```

**Auto-fix:** **fixable**. The `Edit` tool replaces `[[Old]]` with the chosen replacement. Preserve surrounding text exactly.

---

## B2: Orphan notes

**Source:** `references/karpathy-llm-wiki.md` (*"orphan pages with no inbound links"* are lint failures).

**What:** every `.md` file with **zero inbound `[[wikilinks]]`** from anywhere else in the vault.

**How:**
1. Build the vault filename index (same as B1).
2. For each `.md` file, count inbound wikilinks:
   - Grep the entire vault for `\[\[{filename-without-ext}(\||\]|#)`
   - Count distinct files that reference it
3. Files with zero inbound references = orphans.

**Skip (intentional orphans — exclude from findings):**
- `Daily/*.md` — daily notes are time-indexed, not linked
- `**/index.md`, `**/README.md`, `**/CLAUDE.md` — index files are nav, not content
- `**/Tasks.md`, `**/task-list/*.md` — task files reached via Obsidian Task Board, not wikilinks
- Files in `Projects/youtube/youtube-transcripts/` — raw transcripts
- Files in `Intelligence/archive/` — archived content
- Profile root files (`Team/*/Profiles/*/{Name}.md`) — reached via routing, not wikilinks
- `.trash/`, `Plugins & Skills/` — non-content folders

**Finding format:**
```
{path} — orphan (no inbound wikilinks)
Severity: warn
Action: (a) link from a parent/index note, (b) move to archive if obsolete, (c) delete if redundant
```

**Auto-fix:** none. Orphans require human judgment (link, archive, or delete).

---

## B3: Same-role duplicate files

**Source:** `references/karpathy-llm-wiki.md` (*"contradictions between pages"*) + `references/anthropic-managed-memory.md` (focused files, not topic-overlap).

**What:** files whose names suggest they cover the same role and likely contain overlapping or contradictory content.

**How:** filename-pattern heuristics, scoped to specific folders:

In `Context/` folder:
- `voice.md` + `brand.md` + `tone.md` → flag as voice/tone overlap candidates
- `icp.md` + `customer-profile.md` + `audience.md` → ICP overlap
- `services.md` + `offers.md` + `products.md` + `what-we-do.md` → offer overlap
- `me.md` + `profile.md` + `operator.md` + `background.md` → identity overlap
- `strategy.md` + `goals.md` + `okrs.md` + `vision.md` → strategy overlap

In any folder:
- Two files with similar names where the Levenshtein distance ≤ 3 (e.g., `notes.md` + `note.md`, `decisions.md` + `decisions-old.md`).

**Scope:** flag candidates for human review. Don't auto-merge — these may be intentionally separate.

**Finding format:**
```
Potential overlap detected:
  - {path1} ({bytes} bytes)
  - {path2} ({bytes} bytes)
Both appear to cover: {inferred role}
Severity: warn
Action: review and either consolidate, differentiate clearly with frontmatter, or rename to disambiguate
```

**Auto-fix:** none. Requires user judgment.

---

## B4: Routing compliance

**Source:** `references/karpathy-llm-wiki.md` (schema doc defines folder routing) + project root `CLAUDE.md` "Knowledge Routing" table + Rule 17 ("Never create files/folders in vault root").

**What:** files that violate the project's routing rules.

**How:**
1. Read root `CLAUDE.md`. Extract the "Knowledge Routing" table (or equivalent schema doc).
2. Build the set of approved top-level folders.
3. List every top-level entry in the vault (folders and files).
4. Two checks:
   - **Vault-root file violation:** any `.md` file directly in the vault root that is NOT `CLAUDE.md`, `README.md`, or a documented exception. Project rule 17 forbids this.
   - **Unmapped folder:** any top-level folder not in the routing table.

**Finding format (vault-root file):**
```
./{filename} — file in vault root violates Rule 17 (every file lives in an existing folder)
Severity: fail
Action: move to correct folder per routing table, or delete if obsolete
```

**Finding format (unmapped folder):**
```
./{folder}/ — top-level folder not in routing table
Severity: warn
Action: either add to routing table in root CLAUDE.md or relocate contents to an approved folder
```

**Auto-fix:** none. Moving files needs user approval.

---

## B5: Stub notes

**Source:** `references/karpathy-llm-wiki.md` (undigested sources = lint failure) + practitioner field notes.

**What:** notes that are empty, near-empty, or contain only placeholder content.

**How:**
- Glob `**/*.md` with skip list.
- For each: check size and content patterns:
  - **Hard stub:** byte size < 200 (after stripping frontmatter)
  - **Placeholder stub:** content matches any of:
    - Just a `# H1` and nothing else
    - Just frontmatter
    - `TODO`, `WIP`, `Coming soon`, `Placeholder`, `{{owner}}`, `Lorem ipsum`
    - Just a date/timestamp without body
- Skip: legitimately small files like `index.md` stubs that just route, files in `Onboarding/` templates.

**Finding format:**
```
{path} — stub ({bytes} bytes, {n} content lines)
Content excerpt: "{first 80 chars}"
Severity: warn
Action: (a) fill in, (b) delete if no longer needed, (c) move to drafts/
```

**Auto-fix:** none. Stubs need human decision.

---

## Pass output structure

Each pass returns to the orchestrator a list of findings using the same schema as `passes-size-tokens.md`. Findings with `action: "fixable"` are eligible for the auto-apply path; others go to the manual-review section of the report.
