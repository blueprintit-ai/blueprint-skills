# Audit passes — Skills (Progressive Disclosure)

## Contents

1. [C1: Skill-vault duplication](#c1-skill-vault-duplication)
2. [C2: SKILL.md size](#c2-skillmd-size)
3. [C3: SKILL.md frontmatter validation](#c3-skillmd-frontmatter-validation)
4. [C4: Reference depth](#c4-reference-depth)
5. [C5: Reference TOC](#c5-reference-toc)

Source: `references/progressive-disclosure.md` (Anthropic's skill best practices).

Skip list: `.claude/worktrees/`, `.git/`, `.trash/`, `node_modules/`, `dist/`, `build/`.

---

## C1: Skill-vault duplication

**What:** skills that bundle their own copies of content the vault already has in `Context/`.

**How:**
1. Find every `SKILL.md` in the vault. Patterns:
   - `Skills/*/SKILL.md`
   - `**/skills/*/SKILL.md`
   - `Plugins\ \&\ Skills/**/SKILL.md`
2. For each skill that has a `references/` folder (or equivalent), list filenames.
3. Match against vault `Context/` filenames:
   - `icp*.md`, `ideal-customer*.md`, `customer-profile*.md`, `audience*.md` → `Context/icp.md`
   - `voice*.md`, `tone*.md`, `brand*.md` → `Context/brand.md`
   - `offers*.md`, `services*.md`, `what-we-do*.md`, `products*.md` → `Context/services.md`
   - `me.md`, `profile*.md`, `operator*.md`, `background*.md` → `Context/operator.md` (if exists)
   - `strategy*.md`, `goals*.md`, `okrs*.md` → `Context/strategy.md` (if exists)
   - `team*.md`, `org*.md` → `Context/team.md` or `Context/organization.md` (if exists)
4. Confirm the skill's `SKILL.md` actually references the duplicate ref file (else it's a stale orphan).

**Finding format:**
```
Skill: {skill-name}
Duplicate: {skill}/references/{file} ({bytes} bytes)
Vault file: Context/{vault-file}
Severity: warn
Action: rewrite SKILL.md to read Context/{vault-file}; delete the duplicate ref file
```

**Auto-fix:** **fixable**. Rewrite the skill's `SKILL.md` to point at the vault path, then delete the duplicate ref file (only after grepping the skill folder to confirm the ref isn't referenced elsewhere).

---

## C2: SKILL.md size

**What:** SKILL.md files exceeding Anthropic's 500-line guidance.

**How:**
- For each `SKILL.md` found, count lines.
- `> 500 lines` → fail
- `> 400 lines` → warn (approaching limit)

**Finding format:**
```
{path} — {N} lines (target <500)
Severity: warn (>400) / fail (>500)
Action: extract the lowest-signal sections to references/, then re-link from SKILL.md
```

**Auto-fix:** none. Splitting a SKILL.md requires understanding what to extract.

---

## C3: SKILL.md frontmatter validation

**What:** validate the YAML frontmatter against Anthropic's hard limits.

**How:**
For each `SKILL.md`, parse the frontmatter and check:

| Field | Check | Severity |
|---|---|---|
| `name` | Exists, max 64 chars | fail if missing or >64 |
| `name` | Lowercase letters, numbers, hyphens only | fail otherwise |
| `name` | No reserved words: `anthropic`, `claude` | fail if matched |
| `name` | No spaces, no XML tags, no special chars | fail |
| `description` | Exists, non-empty, max 1024 chars | fail if missing or >1024 |
| `description` | No XML tags | fail |
| `description` | Third person (no `I can`, `Use me`, `You can`) | warn |
| `description` | Includes triggers (`when`, `TRIGGERS`, `Use this skill`) | warn if missing |

**Finding format (per violation):**
```
{path} — frontmatter violation: {field} {issue}
Detail: {actual value or measurement}
Severity: {fail|warn}
Action: {specific remediation}
```

Common fixes:
- `name` >64 chars → suggest a tighter gerund-form name
- `description` >1024 chars → suggest converting `description: >` folded scalar to single-line `description: "..."` (the bloat is usually indentation overhead)
- Missing triggers → suggest adding a `TRIGGERS:` clause

**Auto-fix:** none in v0 (frontmatter rewrites are sensitive). Flag-only.

---

## C4: Reference depth

**Source:** `references/progressive-disclosure.md` (*"Keep references one level deep from SKILL.md"*).

**What:** detect references reachable only via 2+ hops from `SKILL.md`. Anthropic explicitly warns this causes Claude to use partial reads (`head -100`) and miss content.

**How:**
1. For each `SKILL.md`, parse all markdown links: `\[([^\]]+)\]\(([^\)]+)\)`.
2. For each linked path that's a relative `.md` file:
   - Hop 1: directly linked from SKILL.md → ok
   - Hop 2+: linked from a hop-1 reference → fail
3. Walk the graph one extra level to detect 2-hop references.

**Finding format:**
```
{skill}/SKILL.md → {ref-1}.md → {ref-2}.md
Severity: fail
Action: link {ref-2}.md directly from SKILL.md, or merge it into {ref-1}.md
```

**Auto-fix:** none. Restructuring references requires editorial judgment.

---

## C5: Reference TOC

**Source:** `references/progressive-disclosure.md` (*"For reference files longer than 100 lines, include a table of contents at the top"*).

**What:** reference files >100 lines without a TOC at the top.

**How:**
1. For each `references/*.md` file linked from a SKILL.md, count lines.
2. If `> 100 lines`:
   - Read the first 30 lines.
   - Check for a TOC: a numbered or bulleted list of internal anchor links (`[Section](#section)`).
   - If absent → finding.

**Finding format:**
```
{path} — {N} lines, no TOC at top
Severity: warn
Action: add a "## Contents" section at the top with anchor links to each H2
```

**Auto-fix:** none in v0. (Could auto-generate a TOC, but adding it correctly without breaking the file requires care.)

---

## Pass output structure

Same schema as previous pass files. C1 findings have `action: "fixable"`; C2-C5 are flag-only in v0.
