---
name: bp-setup
description: Bootstrap the BluePrint OS Plugin vault structure and run personalized onboarding. Creates all directories, system files, Obsidian config, memory system, hooks, and output styles, then interviews the user to personalize everything. Two modes — Solopreneurs/Professionals (default), Business/Teams. Use when user says "set up", "bootstrap", "initialize", "onboarding", or runs /bp-setup.
---

# BluePrint Obsidian Plugin — Setup + Onboarding

USE WHEN the user runs `/setup` or asks to set up their vault, bootstrap the assistant, initialize the system, or configure the BluePrint Obsidian Plugin.

This is a three-phase process:
- **Phase 0**: Mode Selection — Ask which OS variant to create
- **Phase A**: Bootstrap — Create the directory structure and system files for the selected mode
- **Phase B**: Onboarding — Interview the user and personalize everything

## Pre-flight Check

Check if `claude.md` or `CLAUDE.md` exists **only** in the current working directory (do NOT search subdirectories or parent directories — check only the exact CWD path).

- **If it does NOT exist** → fresh setup. Proceed to Phase 0 + Phase A + Phase B.
- **If it exists, read the frontmatter**:
  - **`bp-setup-state: pending`** → **installer-seeded, not yet onboarded.** This is a fresh Shop OS install where the installer dropped a stub CLAUDE.md but the user has not run onboarding yet. Skip Phase 0 (use the `os-mode` already in the frontmatter). Proceed to Phase A — but in Step A.2 **preserve the installer's frontmatter fields** (see the note in Step A.2). Then proceed to Phase B normally.
  - **`bp-setup-state: complete`** (or no `bp-setup-state` field at all — legacy hand-built vault) → the vault is already onboarded. Before asking what to do, run a skills staleness check:

    ```bash
    FETCH_HEAD="$HOME/.claude/plugins/marketplaces/blueprint-skills/.git/FETCH_HEAD"
    if [ -f "$FETCH_HEAD" ]; then
      LAST=$(date -r "$FETCH_HEAD" +%s 2>/dev/null || stat -c %Y "$FETCH_HEAD" 2>/dev/null)
      NOW=$(date +%s)
      echo $(( (NOW - LAST) / 86400 ))
    else
      echo 999
    fi
    ```

    If the result is **30 or more**, show this notice before the options (one line, no drama):

    > Your Shop OS skills haven't been updated in a while. Run `npx -y --package=@blueprintit/shop-os-install shop-os-update` in Terminal, then restart Claude Code to get the latest improvements.

    Then ask the user:
    - "This vault is already set up. Would you like to:"
    - **Re-run the interview** — Keep existing structure, update memory files based on new answers
    - **Full reset** — Delete everything and start fresh (confirm twice before proceeding)
    - **Cancel** — Do nothing

At the end of Phase B Build Step 6, update the root `CLAUDE.md` frontmatter:
- Set `bp-setup-state: complete`
- Add `bp-setup-completed-at: YYYY-MM-DD` (today)

---

## Phase 0: Mode Selection

Ask the user to pick a mode using AskUserQuestion with these exact `label` and `description` values:

- Question: `What type of vault do you want?`
- Option 1 label: `Solopreneurs/Professionals` — description: `Blends work and personal. Best for solo founders, freelancers, consultants.`
- Option 2 label: `Business/Teams` — description: `Org structure with departments, processes, stakeholders. Best for teams and companies.`

**CRITICAL**: You MUST pass both `label` AND `description` for each option in AskUserQuestion. The `description` field is what explains each mode to the user. Never leave `description` empty.

Mode mapping:
- Solopreneurs/Professionals → `os-mode: professional`
- Business/Teams → `os-mode: business`

Accept any clear signal: "solo", "professional", "freelancer", "business", "org", "team", etc.

If the user skips or says "I don't know", use **Solopreneurs/Professionals** (professional mode).

Store the selected mode. It will be written to `CLAUDE.md` frontmatter as `os-mode: professional | business`.

---

## Phase A: Bootstrap

Create the directory structure and write all system files for the selected mode.

### Resolving reference file paths

Every `references/<file>.md` mentioned below lives in the `references/` subdirectory next to **this SKILL.md** — not in the user's working directory. Two conventions matter:

- **Read paths** (`references/foo.md`) → resolve relative to this SKILL.md's directory.
- **Write paths** (`./Foo/CLAUDE.md`) → resolve relative to the user's current working directory (the vault root).

If the Read tool can't open a `references/...` path directly (some harnesses mount the skill at a path that differs between Read and Bash), run a quick discovery step **once** before Step A.2:

```bash
# Search only the plugin cache — fast and unambiguous.
find "$HOME/.claude/plugins" -type d -name "references" -path "*/bp-setup/references" 2>/dev/null | head -1
```

Use that absolute path as the prefix for every reference read in Phase A and Phase B. Don't retry path resolution per-file — do it once and reuse.

### Step A.1: Create Directory Structure

**All modes** share this base:

```bash
mkdir -p .claude
mkdir -p Context
mkdir -p Projects
mkdir -p Daily
mkdir -p Resources
mkdir -p Skills
```

**Solopreneurs/Professionals mode** adds:

```bash
mkdir -p Intelligence/meetings/team-standups
mkdir -p Intelligence/meetings/client-calls
mkdir -p Intelligence/meetings/one-on-ones
mkdir -p Intelligence/meetings/general
mkdir -p Intelligence/competitors
mkdir -p Intelligence/market
mkdir -p Intelligence/decisions
mkdir -p Intelligence/archive
```

**Business mode** adds:

```bash
mkdir -p Intelligence/meetings/team-standups
mkdir -p Intelligence/meetings/client-calls
mkdir -p Intelligence/meetings/one-on-ones
mkdir -p Intelligence/meetings/board-reviews
mkdir -p Intelligence/meetings/all-hands
mkdir -p Intelligence/meetings/cross-team
mkdir -p Intelligence/meetings/general
mkdir -p Intelligence/competitors
mkdir -p Intelligence/market
mkdir -p Intelligence/decisions
mkdir -p Intelligence/processes
mkdir -p Intelligence/archive
mkdir -p Departments
mkdir -p Team
mkdir -p Onboarding
mkdir -p Resources/templates
```

`Team/` is created empty here. Profile-first subfolders (`Team/{org}/Profiles/{person}/...`) are scaffolded in Phase B once Q6 answers are in.

### Step A.2: Write System Files from References

Read each reference file and write it to the corresponding local path. The reference files contain the complete content for each system file.

**All modes** — shared system files:

| Reference File | Creates at Local Path |
|---|---|
| `references/settings-json-template.md` | `./.claude/settings.json` — **skip if file already exists** (installer pre-seeded it with plugin permissions; overwriting would break the install) |
| `references/claudeignore-template.md` | `./.claudeignore` |
| `references/gitignore-template.md` | `./.gitignore` |

**Mode-specific root CLAUDE.md template:**

| Mode | Reference File | Creates at Local Path |
|---|---|---|
| Solopreneurs/Professionals | `references/claude-md-template.md` | `./CLAUDE.md` |
| Business | `references/claude-md-template-business.md` | `./CLAUDE.md` |

**Per-folder routing indexes** (every major folder gets its own `CLAUDE.md` — matches production vault convention):

| Mode | Reference File | Creates at Local Path |
|---|---|---|
| Solopreneurs/Professionals | `references/claude-md-context.md` | `./Context/CLAUDE.md` |
| Solopreneurs/Professionals | `references/claude-md-projects.md` | `./Projects/CLAUDE.md` |
| Solopreneurs/Professionals | `references/claude-md-daily.md` | `./Daily/CLAUDE.md` |
| Solopreneurs/Professionals | `references/claude-md-intelligence.md` | `./Intelligence/CLAUDE.md` |
| Solopreneurs/Professionals | `references/claude-md-resources.md` | `./Resources/CLAUDE.md` |
| Solopreneurs/Professionals | `references/claude-md-skills.md` | `./Skills/CLAUDE.md` |
| Business | `references/claude-md-context.md` | `./Context/CLAUDE.md` |
| Business | `references/claude-md-projects.md` | `./Projects/CLAUDE.md` |
| Business | `references/claude-md-daily.md` | `./Daily/CLAUDE.md` |
| Business | `references/claude-md-intelligence.md` | `./Intelligence/CLAUDE.md` |
| Business | `references/claude-md-resources.md` | `./Resources/CLAUDE.md` |
| Business | `references/claude-md-skills.md` | `./Skills/CLAUDE.md` |
| Business | `references/claude-md-departments.md` | `./Departments/CLAUDE.md` |
| Business | `references/claude-md-team.md` | `./Team/CLAUDE.md` |
| Business | `references/claude-md-onboarding.md` | `./Onboarding/CLAUDE.md` |
| Business | `references/claude-md-processes.md` | `./Intelligence/processes/CLAUDE.md` |

For each row applicable to the selected mode: read the reference file, then write its content to the local path.

> When overwriting `./CLAUDE.md`, if the existing file's frontmatter contains `bp-setup-state: pending`, **merge its fields** (`license-customer`, `license-product`, `installed-at`, and any other fields not in the template) into the new template's frontmatter before writing. The installer-seeded body content is discarded — the routing template body is what the vault needs from here on. Drop `bp-setup-state: pending` from the merged frontmatter; it gets re-set to `complete` at the end of Phase B Build Step 6.

### Step A.3: Initialize Starter Context Files

**All modes** — create placeholder skill folders:

```bash
mkdir -p Skills/linkedin-writer/references
mkdir -p Skills/newsletter-writer/references
```

Then write placeholder files from references:
- Read `references/skills-placeholder-linkedin-notes.md` → write to `./Skills/linkedin-writer/notes.md`
- Read `references/skills-placeholder-linkedin-example.md` → write to `./Skills/linkedin-writer/references/example-post.md`
- Read `references/skills-placeholder-newsletter-strategy.md` → write to `./Skills/newsletter-writer/strategy.md`
- Read `references/skills-placeholder-newsletter-example.md` → write to `./Skills/newsletter-writer/references/example-edition.md`

**Solopreneurs/Professionals mode:**
- Read `references/context-me.md` → write to `./Context/me.md`

**Business mode:**
- Read `references/context-operator.md` → write to `./Context/operator.md`
- Read `references/context-organization.md` → write to `./Context/organization.md`
- Read `references/context-team.md` → write to `./Context/team.md`
- Read `references/context-strategy-business.md` → write to `./Context/strategy.md`

**Business mode — `Team/` is created empty in Phase A.** Profile-first scaffolding (`Team/{org}/Profiles/{person}/...`) happens in Phase B Build Step 3 once Q6 answers identify the actual people.

### Step A.4: Make Hooks Executable

```bash
chmod +x .claude/hooks/*.sh
```

### Step A.5: Confirm Bootstrap

Tell the user:
- "Vault structure created successfully in **[mode]** mode."
- List the main folders created (varies by mode), including `Skills/`
- Recommend opening this folder as a vault in Obsidian
- Recommend installing **TaskNotes** community plugin if they want task management features
- Note that **Bases** (native database views) are built into Obsidian — no plugin needed for queries
- Mention `Resources/` for storing prompts, frameworks, swipe files, and templates
- "Now let's personalize it for you."

Then proceed to Phase B.

---

## Phase B: Interview

Phase B replaces fixed onboarding questions with a grill-me-style interview. The interview goes deeper than six one-liners — it extracts what the owner actually knows so the vault reflects their real business, not a template with placeholders.

### Setup (before the first question)

Create the capture file at `brainstorms/YYYY-MM-DD-shop-os-setup.md` in the vault root:

```markdown
# Shop OS Setup: Discovery Notes
Date: YYYY-MM-DD · Goal: Build a personalized Shop OS brain for [shop name]

## Summary
(updated as we go)

## Interview log

## Open flags (to fill in later with /grill-me)
```

Then send this orientation message (no question yet):

> "Before I build your vault, I'm going to interview you about your shop. The more you share, the more your brain will know your business — instead of a generic template with your name swapped in. We'll cover 9 topics. I'm saving everything as we go to `brainstorms/YYYY-MM-DD-shop-os-setup.md` so nothing is lost. Say **next** any time to move to the next topic, or **done** to wrap up early and I'll build with what we have. Let's go."

### Interview discipline

Follow these rules for every question without exception:

- Ask **one question at a time**. Never stack multiple questions in one message.
- **First question per topic**: open-ended, no recommended answer (owner hasn't given signal yet).
- **Every follow-up within a topic**: carry your best inferred answer based on what they've said — "My guess is X — is that right?" — so they can confirm, correct, or redirect. Never make them re-explain context you already hold.
- After **every answer**, before asking the next question: append a checkpoint entry to the capture file (topic, key facts in their words, any flags). One answer, one write. Never batch.
- After every **2nd question** (count resets per topic): append to your message — *(Say **next** to move to the next topic, or **done** to wrap up.)*
- **"next"**: capture an open flag for that topic ("Owner moved on — run /grill-me to go deeper") and proceed.
- **"done"**: stop the interview and go straight to the pre-routing summary.
- **Can't answer**: capture as a flag — "Not answered during setup — run /grill-me to fill this in" — and move on. Never stall.
- **Plain language throughout**: "Who are your best customers?" not "describe your ICP." "Why do customers pick you over the guy across town?" not "what's your differentiation." Topics are identical to the Context/ file structure — vocabulary adapts to the audience; routing maps silently.

### The 9 topics

Work through in order. Resolve each topic to minimum useful depth before moving on. Cover what's needed to personalize the relevant Context/ file — not every possible branch.

**Topic 1 — The Shop**
Cover: shop name, location, how long in business, headcount, physical size.
Opening question: "Let's start with the basics. What's the name of your shop, where are you located, and how long have you been running it?"

**Topic 2 — What You Build and Who Buys It**
Cover: job types (residential vs commercial, custom vs production, millwork, other), who the typical customer is (homeowner, general contractor, designer, developer).
Opening question: "What kind of work do you take on — and who's typically hiring you?"

**Topic 3 — How Work Flows Through the Shop**
Cover: process from first contact to delivered job (estimating, design, production, install, handoff), where the bottlenecks are.
Opening question: "Walk me through how a job moves through your shop from the first call to the final walkthrough."

**Topic 4 — Pricing and Estimating**
Cover: how they price jobs, tools or methods they use, typical job size, what's hard or inconsistent about it.
Opening question: "How do you price your work? Walk me through how you put together an estimate."

**Topic 5 — Where Customers Come From**
Cover: lead sources (referrals, contractors, designers, Google, word of mouth), what drives repeat business, ratio of new vs returning customers.
Opening question: "Where do your customers come from? What's been your best source of new work?"

**Topic 6 — Why Customers Pick You**
Cover: what makes them different from the shop across town, what customers say when they refer them, what they're known for.
Opening question: "Why do customers come to you instead of someone else? What do they say when they refer you?"

**Topic 7 — How You Sound**
Cover: communication style (formal vs casual), shop personality, words they'd never use, what they want customers to feel.
Opening question: "How would you describe the way your shop communicates — in emails, on your website, in person with customers?"

**Topic 8 — What's on Your Plate Right Now**
Cover: top 1–3 priorities this quarter, active projects or initiatives, anything with a deadline.
Opening question: "What are you most focused on right now? What are the 1–3 things you're trying to move forward this quarter?"

**Topic 9 — Tools and What's Draining You**
Cover: software and tools used day-to-day (estimating, project management, accounting, communication), the 1–2 workflows they'd most like to automate or stop doing.
Opening question: "What tools do you use to run the business? And what's the one thing you wish you could stop doing or hand off?"

### Pre-routing summary

After all 9 topics (or owner says "done"):

1. Write a plain-language summary back to the owner — "Here's what I learned about your shop:" — covering the key facts from each topic. Use their words where the wording matters. Flag anything you're uncertain about.
2. Ask: "Does this look right? Correct anything before I build your vault."
3. Wait for confirmation or corrections. Update the capture file with any corrections before proceeding.
4. Proceed to Phase B Build.

---

## Phase B Build: Personalize the Vault

After Q6 + the additional-context drop (or skips), build everything you can from what the user gave you. Work silently — don't narrate each step.

### CRITICAL: real personalization, not template scaffolds

The reference files in `references/` are **scaffolds** — they show the section structure to use. They are **not** the output. Do not copy a template verbatim with placeholders intact.

For every file you write:

1. **Read the reference template** to learn the section structure (headings, frontmatter shape, section order).
2. **Replace every placeholder** (anything in `[brackets]` or marked as TBD) with real data extracted from Q1–Q12 answers + the additional-context corpus.
3. **If a section has zero supporting data** after exhausting both Q answers and the corpus: **omit the entire section** rather than writing `[name]` or `TBD`. The output should never contain bracketed placeholders.
4. **If only some bullets in a section have data**: keep the section, drop the empty bullets.
5. **Use the user's actual words, names, numbers, URLs, and quotes** wherever the corpus contains them. Don't paraphrase facts — preserve specificity (exact company names, exact dollar figures, exact dates, exact phrases the user uses).
6. **Cross-reference**: a single fact may belong in multiple files (e.g., "we sell to RevOps leaders at Series B SaaS" belongs in both `icp.md` and `brand.md` positioning). Place it in each file where it's relevant.
7. **Frontmatter `updated:`** = today's date.

A finished context file should read as a real human-written document about the user. If it reads like a fillable form, you did it wrong — go back and fill it.

### Build Step 1: Create Context Files

Behavior depends on selected mode. Source all data from the interview capture file (`brainstorms/YYYY-MM-DD-shop-os-setup.md`). Read it before building — it is the source of truth.

The 9 interview topics map to Context/ files as follows. Use this as your routing guide:

| Topic | Primary Context/ target |
|---|---|
| T1 — The Shop | `me.md` (solo) / `organization.md` (business) |
| T2 — What you build + who buys | `services.md`, `icp.md` |
| T3 — How work flows | `infrastructure.md` |
| T4 — Pricing + estimating | `services.md` (pricing section), `pain-points.md` |
| T5 — Where customers come from | `icp.md` (acquisition section) |
| T6 — Why customers pick you | `brand.md` (positioning section) |
| T7 — How you sound | `brand.md` (voice section) |
| T8 — What's on your plate | `strategy.md` |
| T9 — Tools + drains | `infrastructure.md` |

**Solopreneurs/Professionals mode:**

- **`Context/me.md`** — Always created. Fill from T1 (name, location, how long, size) + T8 (priorities, drains). Read `references/context-me.md` as scaffold.
- **`Context/services.md`** — Always created for Shop OS. Fill from T2 (job types, who buys) + T4 (pricing method, typical job size). Read `references/context-services.md` as scaffold.
- **`Context/pain-points.md`** — Only if T3 or T4 surfaced bottlenecks or estimating pain. Read `references/context-pain-points.md` as scaffold.
- **`Context/icp.md`** — Always created for Shop OS. Fill from T2 (customer types) + T5 (lead sources, what drives repeat business). Read `references/context-icp.md` as scaffold.
- **`Context/brand.md`** — Always created for Shop OS. From T6 take positioning (why pick you, what they're known for). From T7 take voice (style, personality, words to avoid). Read `references/context-brand.md` as scaffold.
- **`Context/strategy.md`** — Only if T8 had content (priorities, active projects). Read `references/context-strategy.md` as scaffold.
- **`Context/infrastructure.md`** — Always created for Shop OS. From T3 take work flow (estimate to delivery, bottlenecks). From T9 take tool stack + workflows-to-automate. Read `references/context-infrastructure.md` as scaffold.
- **`Context/team.md`** — Only if T1 mentioned employees or collaborators. Read `references/context-team.md` as scaffold.

**Business mode:**

- **`Context/organization.md`** — Always created. Fill from T1 (shop name, location, history, headcount, physical size). Read `references/context-organization.md` as scaffold.
- **`Context/services.md`** — Always created for Shop OS. Fill from T2 (job types, who buys) + T4 (pricing method, typical job size). Read `references/context-services.md` as scaffold.
- **`Context/pain-points.md`** — Only if T3 or T4 surfaced bottlenecks or estimating pain. Read `references/context-pain-points.md` as scaffold.
- **`Context/icp.md`** — Always created for Shop OS. Fill from T2 (customer types) + T5 (lead sources, what drives repeat business). Read `references/context-icp.md` as scaffold.
- **`Context/brand.md`** — Always created for Shop OS. From T6 take positioning. From T7 take voice. Read `references/context-brand.md` as scaffold.
- **`Context/team.md`** — Always created. Fill from T1 (headcount, key roles). Read `references/context-team.md` as scaffold.
- **`Context/strategy.md`** — Always created. Fill from T8 (priorities, active projects, any targets mentioned). Read `references/context-strategy-business.md` as scaffold.
- **`Context/infrastructure.md`** — Always created for Shop OS. From T3 take work flow. From T9 take tool stack + workflows-to-automate. Read `references/context-infrastructure.md` as scaffold.
- **`Context/operator.md`** — Always created. Fill from T1 (owner name, role) + T8 (priorities, what's draining them). Read `references/context-operator.md` as scaffold.

**For any topic captured as a flag** (owner said "next" or couldn't answer): write the relevant Context/ file anyway, add a placeholder section at the bottom:

```markdown
> [!todo] Not captured during setup
> Run `/grill-me` on this topic to fill it in.
```

### Build Step 2: Create Project Folders

Solo: from Q5. Business: from Q4. Plus any project briefs / Notion exports / project lists in the corpus. Intelligently structure each project based on what the user gave you.

**Analyze the info and decide the right structure:**
- Simple mention ("working on a podcast") → just a `README.md`
- Moderate detail (scope, deadlines, people) → `README.md` + relevant subdirs
- Rich info (briefs, specs, research, multiple workstreams) → full structure with subdirs and files

**Create subdirectories only when the content justifies them:**

| Content type | Goes to |
|---|---|
| Overview, status, deadlines, contacts | `README.md` |
| Research, competitor analysis, references | `research/{topic}.md` |
| Specs, requirements, briefs | `specs/{name}.md` or `briefs/{name}.md` |
| Drafts, scripts, written content | `drafts/{name}.md` |
| Ideas, brainstorms | `ideas/{name}.md` |
| Notes, working docs | `notes/{name}.md` |

**README.md is always the index:**
```markdown
---
type: project
status: active
owner: [name]
business: [business unit if applicable]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
## Overview
[What this project is]

## Current Status
[Where things stand]

## Key Resources
[Links, tools, contacts]

## Next Steps
[What needs to happen]
```

Don't create empty subdirs. Don't cram everything into the README. Distribute content into the right files based on what it actually is.

**Business mode only** — from Q4 + corpus, also create `Departments/{name}/README.md` for each department with the lead's name, charter placeholder, and `sops/` subfolder.

### Build Step 3: Profile-First Team Scaffolding (Business mode only)

From Q4 + corpus (org chart, team roster), scaffold each person's profile workspace. Slug names are kebab-case.

`{org-slug}` is derived from Q1 (company name → kebab-case). If no company name given, default to `team`.

For each FT employee:
```bash
mkdir -p Team/{org-slug}/Profiles/{person-slug}/Daily
mkdir -p Team/{org-slug}/Profiles/{person-slug}/task-list
mkdir -p Team/{org-slug}/Profiles/{person-slug}/sub-schedules
```
Then write:
- Read `references/team-profile-template.md` → write to `./Team/{org-slug}/Profiles/{person-slug}/{Person Name}.md`. Fill frontmatter and sections from Q4 (name, role, reports-to, FT, location) + corpus.
- Read `references/team-tasks-template.md` → write to `./Team/{org-slug}/Profiles/{person-slug}/task-list/Tasks.md`.

For each contractor / advisor:
```bash
mkdir -p Team/External/contractors/{person-slug}
```
Then write the same `team-profile-template.md` (with `employment: contractor` or `advisor`) → `./Team/External/contractors/{person-slug}/{Person Name}.md`.

If Q4 + corpus list no team members, don't scaffold anything under `Team/{org-slug}/Profiles/`. Leave `Team/` with just the `CLAUDE.md` routing index.

### Build Step 4: Mode-specific Additional Setup

**Business mode only:**
- If Q5 or corpus mentioned org-wide processes / SOPs, capture them in `Intelligence/processes/{name}.md`
- If user provided onboarding docs in the corpus, route them to `Onboarding/{name}.md`

### Build Step 5: Create First Daily Note

Create `Daily/YYYY-MM-DD.md` (today's date):
```markdown
---
type: daily-note
date: YYYY-MM-DD
---
# YYYY-MM-DD

## Session
- **Focus**: Initial vault setup and onboarding
- **Completed**: Full vault bootstrap + personalized onboarding
- **Next Steps**: [based on what was discussed]
```

### Build Step 6: Confirm Completion

Tell the user:
- Quick summary of what was created (which context files, how many projects, any departments, any team profiles)
- "Open this folder in Obsidian to see your vault"
- "You can add more context anytime — just tell me and I'll update the right files."
- Suggest a next action based on what they told you

## Guidelines

- Phase 0 is one question — mode selection
- Phase A is fully automated — no user input needed
- Phase B is a grill-me-style interview across 9 topics. One question at a time. Checkpoint the capture file after every single answer before asking the next. Never batch.
- The capture file (`brainstorms/YYYY-MM-DD-shop-os-setup.md`) is the source of truth for Phase B Build. Read it before routing.
- First question per topic is open. Every follow-up carries an inferred recommended answer based on prior signal. By mid-interview, run ahead — propose answers the owner confirms or tweaks.
- Remind owner of controls ("next" / "done") every 2nd question. Orientation message sets the full context before Q1.
- Plain language throughout. Topics are identical to Context/ file structure — vocabulary adapts, routing maps silently.
- When an owner can't answer: flag it, move on, never stall. Flagged topics get a `/grill-me` callout in the relevant Context/ file.
- Two-stage close: plain-language summary → owner confirms → routing pass runs silently → final confirmation with files created + next step.
- **Templates are scaffolds, not outputs.** Replace every `[bracketed placeholder]` with real data from the capture file. If a section has no data, omit it — never leave placeholders.
- Preserve specificity: use the owner's exact words, names, numbers, and phrasing.
- Don't narrate every file you're creating — build silently, summarize at the end.
