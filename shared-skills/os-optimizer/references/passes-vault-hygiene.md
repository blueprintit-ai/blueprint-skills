# Audit passes — Vault Hygiene

## Contents

1. [D1: Frontmatter compliance](#d1-frontmatter-compliance)
2. [D2: Filename quality](#d2-filename-quality)
3. [D3: Index file presence](#d3-index-file-presence)
4. [D4: Em dash detection](#d4-em-dash-detection)
5. [D5: Generic emphasis pattern](#d5-generic-emphasis-pattern)
6. [D6: Code-style rules in CLAUDE.md](#d6-code-style-rules-in-claudemd)
7. [D7: H1 duplicating filename](#d7-h1-duplicating-filename)
8. [D8: Project README hygiene](#d8-project-readme-hygiene)

Skip list: same as previous pass files.

---

## D1: Frontmatter compliance

**Source:** project root `CLAUDE.md` "Frontmatter" section + `references/anthropic-managed-memory.md` (descriptive metadata).

**What:** notes missing required frontmatter fields.

**How:**
1. Read project rules: every note must have `status:` + 2+ specific `tags:`. Other standard fields: `type`, `date`, `project`, `department`, `priority`.
2. For each `.md` file in content folders (`Context/`, `Departments/`, `Intelligence/`, `Projects/`, `Team/`, `Resources/`, `Daily/`):
   - Parse frontmatter (between `---` markers at top).
   - Check for required fields per project rules.

**Required (per project CLAUDE.md):**
- `status:` — present
- `tags:` — at least 2 specific tags

**Recommended (per project CLAUDE.md, "Most missed: project: and department:"):**
- `type:`
- `date:` (for time-sensitive content)
- `project:` (for project-related)
- `department:` (for department-related)

**Skip:**
- `CLAUDE.md`, `README.md`, `index.md` — meta files don't need full frontmatter
- Files in `.trash/`, `Onboarding/templates/`
- Tasks files — different format

**Finding format (per missing field):**
```
{path} — missing frontmatter: {fields}
Severity: warn
Action: add required fields to frontmatter
```

Group findings: report counts per field (e.g., "12 files missing `status:`, 8 missing `tags:`") rather than listing each individually.

**Auto-fix:** none in v0 — adding correct values requires content understanding.

---

## D2: Filename quality

**Source:** `references/anthropic-managed-memory.md` (*"the agent navigates by name"*) + `references/practitioner-notes.md`.

**What:** ambiguous, non-descriptive filenames that hurt agent navigation.

**How:**
- Glob `**/*.md` with skip list.
- Flag filenames matching:
  - `notes\d*\.md` (`notes.md`, `notes-2.md`, `notes2.md`)
  - `untitled.*\.md`
  - `temp.*\.md`
  - `file-?\d+\.md`
  - `new-document.*\.md`
  - `draft\d*\.md`
  - `document\d*\.md`
  - `copy.*\.md`
  - `final.*\.md`, `final-final.*\.md`
- Flag files with only numeric basename: `1.md`, `123.md`

**Skip:**
- Date-named files: `YYYY-MM-DD.md`, `YYYY-MM-DD-{slug}.md` (these are descriptive in context)
- Profile pages with proper names
- Numbered course/section files: `01-introduction.md`, `lesson.md` in course folders

**Finding format:**
```
{path} — ambiguous filename
Suggested: rename based on actual content (open the file and propose a slug)
Severity: warn
Action: rename to descriptive filename
```

**Auto-fix:** none. Renaming needs the user to choose the new name.

---

## D3: Index file presence

**Source:** `references/anthropic-managed-memory.md` (memory index pattern: top-level INDEX.md or MEMORY.md).

**What:** folders with >5 markdown files but no `index.md`, `README.md`, `CLAUDE.md`, or `MEMORY.md` to navigate by.

**How:**
1. For each folder containing `.md` files (recursively):
   - Count direct-child `.md` files.
   - Skip subfolders' files.
2. If count > 5 AND no index file present (case-insensitive: `index.md`, `README.md`, `CLAUDE.md`, `_index.md`, `MEMORY.md`) → finding.

**Skip:**
- `Daily/` and other date-indexed folders (Obsidian's daily notes plugin handles navigation)
- `Intelligence/meetings/{type}/` — meetings are time-indexed
- `Projects/youtube/youtube-transcripts/` — raw transcripts

**Finding format:**
```
{folder}/ — {N} files, no index file
Severity: warn
Action: create index.md or README.md listing the files in this folder with one-line descriptions
```

**Auto-fix:** none. Creating the index requires reading the files to write descriptions.

---

## D4: Em dash detection

**Source:** project root `CLAUDE.md` Rule 14: *"NEVER use em dashes. Use periods, commas, colons, or restructure."*

**What:** every em dash (`—`, `–`) in vault content. The project explicitly bans them.

**How:**
- Grep across all `.md` files for em dash characters: `—` (U+2014) and en dash `–` (U+2013).
- Skip: code blocks (` ``` ` fences), inline code (` `code` `), URLs.
- Skip files in `Onboarding/templates/` and `.trash/`.
- Skip: `Context/brand.md` if it documents the rule itself.

**Finding format:**
```
{path}:{line} — em dash detected
Context: "{surrounding line}"
Severity: warn
Action: replace with period, comma, colon, or restructure
```

**Auto-fix:** **fixable** with caution — but the right replacement depends on context (period vs comma vs colon). Default: flag-only with example replacements; let user choose.

For v1: present the user with option to bulk-replace em dashes with periods (most conservative substitution). Track in summary as a separate batch the user can opt into.

---

## D5: Generic emphasis pattern

**Source:** `references/anthropic-claude-md.md` (*"If everything is IMPORTANT, nothing is"*).

**What:** `CLAUDE.md` files where >30% of rules use emphasis markers (`IMPORTANT`, `YOU MUST`, all-caps), suggesting no real prioritization.

**How:**
1. For each `CLAUDE.md`, read content.
2. Count occurrences of: `IMPORTANT`, `YOU MUST`, `CRITICAL`, `NEVER`, `ALWAYS` (as standalone words, not in normal prose).
3. Count total numbered rules / bullet points.
4. If ratio > 0.3 → finding.

**Finding format:**
```
{path} — {N} of {total} rules use emphasis markers ({pct}%)
Severity: warn
Action: reserve emphasis for the rules where failure is genuinely costly; if everything is IMPORTANT, nothing is
```

**Auto-fix:** none. Requires editorial decision.

---

## D6: Code-style rules in CLAUDE.md

**Source:** `references/practitioner-notes.md` (camelCase: don't include code style in CLAUDE.md, use linters/formatters with `post tool use` hook).

**What:** code style rules that should live in linter config + `.claude/rules/` instead of CLAUDE.md.

**How:**
- Grep CLAUDE.md files for patterns:
  - `\b(use|prefer)\s+\d+\s+(space|tab)` (indentation rules)
  - `(single|double)\s+quotes` (quote style)
  - `\bcamelCase\b`, `\bsnake_case\b`, `\bkebab-case\b` (naming conventions)
  - `\b(semicolon|trailing comma|line break)\b` (formatting)
  - `\b(eslint|prettier|biome|ruff|black)\b\s+(disable|ignore)` (linter rules)

**Finding format:**
```
{path}:{line} — code style rule in CLAUDE.md
Excerpt: "{matched line}"
Severity: warn
Action: move to linter config (e.g., .eslintrc, .prettierrc) and use post-tool-use hook
```

**Auto-fix:** none. Moving to linter config requires user setup.

---

## D7: H1 duplicating filename

**Source:** project root `CLAUDE.md` Anti-Patterns: *"Put a # Title heading that duplicates the filename"*.

**What:** files where the first `# H1` matches the filename.

**How:**
1. For each `.md` file, read the first non-frontmatter content line.
2. If it's `# {Title}` and `{Title}` (when slugified) matches the filename (without extension, slugified), → finding.

Slugification: lowercase, replace spaces with hyphens, strip special chars.

**Finding format:**
```
{path} — H1 "{title}" duplicates filename
Severity: warn
Action: remove the H1 (filename in Obsidian already serves this purpose)
```

**Auto-fix:** **fixable**. Remove the duplicate H1 line (and the blank line below it if present).

---

## D8: Project README hygiene

**Source:** project root `CLAUDE.md` Anti-Patterns: *"Cram all project info into README.md (route to subdirs)"*.

**What:** project README files that are either too sparse (no overview/status/next-steps) or too dense (everything jammed into README instead of subdirs).

**How:**
1. For each `Projects/{category}/{name}/README.md`:
   - Read content.
   - Check for required sections (case-insensitive headers): "Overview" / "What", "Status", "Next" / "Next steps" / "Roadmap".
   - Check size: < 200 bytes = sparse stub; > 8KB = bloated (likely cramming all project info).

**Finding format (sparse):**
```
{path} — sparse README ({bytes} bytes), missing: {missing-sections}
Severity: warn
Action: add overview, current status, and next steps
```

**Finding format (bloated):**
```
{path} — bloated README ({bytes} bytes)
Severity: warn
Action: extract subtopics into subdir files (specs/, notes/, research/), keep README as the entry point
```

**Auto-fix:** none. Restructuring requires content understanding.

---

## Pass output structure

Same schema as previous pass files. D4 (em dash) and D7 (duplicate H1) findings can be marked `fixable`; D1, D2, D3, D5, D6, D8 are flag-only in v0.
