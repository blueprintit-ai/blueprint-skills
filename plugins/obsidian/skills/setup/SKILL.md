---
name: setup
description: Bootstrap the BenAI Obsidian Plugin vault structure and run personalized onboarding. Creates all directories, system files, Obsidian config, memory system, hooks, and output styles, then interviews the user to personalize everything. Two modes — Solopreneurs/Professionals (default), Business/Teams. Use when user says "set up", "bootstrap", "initialize", "onboarding", or runs /setup.
---

# BenAI Obsidian Plugin — Setup + Onboarding

USE WHEN the user runs `/setup` or asks to set up their vault, bootstrap the assistant, initialize the system, or configure the BenAI Obsidian Plugin.

This is a three-phase process:
- **Phase 0**: Mode Selection — Ask which OS variant to create
- **Phase A**: Bootstrap — Create the directory structure and system files for the selected mode
- **Phase B**: Onboarding — Interview the user and personalize everything

## Pre-flight Check

Check if `claude.md` or `CLAUDE.md` exists **only** in the current working directory (do NOT search subdirectories or parent directories — check only the exact CWD path).

- **If it exists**: The vault is already set up. Ask the user:
  - "This vault is already set up. Would you like to:"
  - **Re-run the interview** — Keep existing structure, update memory files based on new answers
  - **Full reset** — Delete everything and start fresh (confirm twice before proceeding)
  - **Cancel** — Do nothing
- **If it does NOT exist**: Proceed with full setup (Phase 0 + Phase A + Phase B)

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
# Find the references directory; cache the result for the rest of Phase A.
find / -type d -path '*/setup/references' 2>/dev/null | head -1
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
| `references/settings-json-template.md` | `./.claude/settings.json` |
| `references/claudeignore-template.md` | `./.claudeignore` |
| `references/gitignore-template.md` | `./.gitignore` |

**Mode-specific claude.md template:**

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

## Phase B: Onboarding

Ten questions. Present them all in a single message. The user can answer one-by-one, paste a doc that covers several, upload files, or skip any individually. Don't ask follow-ups. Extract what's there. The questions differ by mode.

### Mode-specific Questions

**Solopreneurs/Professionals mode** — present all 10 in one message:

1. **Who are you?** Name, role/title, location, industry, when you do your best work.
2. **What you're building or selling.** One paragraph per business or product line — name, what it does, who it's for, stage, revenue baseline if applicable. Skip if no business.
3. **Who you serve.** Ideal customer / audience: their role, their pain, what they're hiring you to fix.
4. **People you work with regularly.** Team, contractors, key external contacts — name, role, how you work together. Skip if fully solo.
5. **Voice + visual identity.** A paragraph (or paste a writing sample) on how you sound. Brand colors, fonts, taglines if you have them. Skip if N/A.
6. **This year's priorities — measurable.** 1–3 outcomes with a number attached (revenue, audience size, ship date) + the *why* for each.
7. **What you're actively working on.** For each project: name, one-line purpose, status, deadline if any, business it belongs to.
8. **Tools and integrations you use daily.** CRM, calendar, meeting recorder, content platforms, dev stack, automation tools.
9. **Top 1–2 painful, repetitive workflows** you'd offload to Claude first. Be specific about input → output.
10. **What's draining your attention right now?** Unclosed loops: things that should be done but aren't, decisions sitting unmade, commitments overdue.

**Business mode** — present all 10 in one message:

1. **You — operator profile.** Name, title, department, who you report to, decision authority, where you're based, working style, what's draining your attention right now (unclosed loops).
2. **Company essentials.** Legal entity name, industry, stage, founded, headcount (FT + contractors), location, one-sentence mission.
3. **Products / services / business units.** For each revenue line: name, what it does, who buys it, current revenue baseline, status. Multiple lines OK.
4. **Who you serve + key pain points.** Ideal customer + the top 3 pains your product addresses.
5. **Departments and leads.** List the departments and the lead for each.
6. **Team members getting profiles.** For each: name, role, reports-to, FT/contractor, location. These get full profile folders with their own daily notes.
7. **Annual objectives + key results.** 1–3 objectives. For each KR: target number, owner, current status.
8. **Active projects and initiatives.** For each: name, owner, status, client-facing or internal, business unit.
9. **Brand voice + visual identity.** Tagline, value prop, voice in a paragraph, signature phrases, colors / fonts. Skip if N/A.
10. **Tool stack + top 3 workflows to automate first + external stakeholders.** Stack across communication, meetings, CRM, PM, content, finance, dev + 3 painful repetitive workflows + investors / partners / vendors / top clients.

The user might give you:
- One-by-one numbered answers
- A wall of text (wiki, about page, LinkedIn profile, intake doc) that covers several at once
- Uploaded files (PDFs, docs, screenshots)
- "skip" on individual questions or the whole set

**Accept whatever they give.** Don't ask follow-ups. Extract what you can.

**If the user skips everything** — proceed to build with defaults only.

---

## Phase B Build: Personalize the Vault

After the ten questions (or skips), build everything you can from what the user gave you. Work silently — don't narrate each step.

### Build Step 1: Create Context Files

Behavior depends on selected mode.

**Solopreneurs/Professionals mode** (Q1–Q10 = solo questions):

- **`Context/me.md`** — Always created. Fill from Q1 (identity, role, location, work style), Q8 (tools), Q10 (Unclosed Loops section). Read `references/context-me.md` as template.
- **`Context/business.md`** — Only if Q2 had content. Read `references/context-business.md` as template.
- **`Context/services.md`** — Only if Q2 listed multiple revenue lines or named services / products. Read `references/context-services.md` as template.
- **`Context/icp.md`** — Only if Q3 had content. Read `references/context-icp.md` as template.
- **`Context/pain-points.md`** — Only if Q3 mentioned pains or what customers are hiring you to fix. Read `references/context-pain-points.md` as template.
- **`Context/team.md`** — Only if Q4 had content. Read `references/context-team.md` as template.
- **`Context/brand.md`** — Only if Q5 had content. Read `references/context-brand.md` as template.
- **`Context/strategy.md`** — Only if Q6 had content. Read `references/context-strategy.md` as template.
- **`Context/infrastructure.md`** — Only if Q8 listed tools. Read `references/context-infrastructure.md` as template.

**Business mode** (Q1–Q10 = business questions):

- **`Context/operator.md`** — Always created. Fill from Q1 (role, decision authority, responsibilities, location, working style, unclosed loops). Read `references/context-operator.md` as template.
- **`Context/organization.md`** — Always created. Fill from Q2 (company info, mission, headcount, stage). Read `references/context-organization.md` as template.
- **`Context/services.md`** — Only if Q3 had content. Read `references/context-services.md` as template.
- **`Context/icp.md`** — Only if Q4 had content. Read `references/context-icp.md` as template.
- **`Context/pain-points.md`** — Only if Q4 listed pains. Read `references/context-pain-points.md` as template.
- **`Context/team.md`** — Always created. Fill with any team members from Q6. Read `references/context-team.md` as template.
- **`Context/strategy.md`** — Always created. Fill from Q7 (OKRs, KRs, owners). Read `references/context-strategy-business.md` as template.
- **`Context/brand.md`** — Only if Q9 had content. Read `references/context-brand.md` as template.
- **`Context/infrastructure.md`** — Only if Q10 listed tools. Read `references/context-infrastructure.md` as template.
- **`Context/stakeholders.md`** — Only if Q10 mentioned investors, partners, vendors, or top clients. Read `references/context-stakeholders.md` as template.

### Build Step 2: Create Project Folders

Solo: from Q7. Business: from Q8. Intelligently structure each project based on what the user gave you.

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

**Business mode only** — from Q5, also create `Departments/{name}/README.md` for each department with the lead's name, charter placeholder, and `sops/` subfolder.

### Build Step 3: Profile-First Team Scaffolding (Business mode only)

From Q6, scaffold each person's profile workspace. Slug names are kebab-case.

`{org-slug}` is derived from Q2 (company name → kebab-case). If no company name given, default to `team`.

For each FT employee:
```bash
mkdir -p Team/{org-slug}/Profiles/{person-slug}/Daily
mkdir -p Team/{org-slug}/Profiles/{person-slug}/task-list
mkdir -p Team/{org-slug}/Profiles/{person-slug}/sub-schedules
```
Then write:
- Read `references/team-profile-template.md` → write to `./Team/{org-slug}/Profiles/{person-slug}/{Person Name}.md`. Fill frontmatter and sections from Q6 (name, role, reports-to, FT, location).
- Read `references/team-tasks-template.md` → write to `./Team/{org-slug}/Profiles/{person-slug}/task-list/Tasks.md`.

For each contractor / advisor:
```bash
mkdir -p Team/External/contractors/{person-slug}
```
Then write the same `team-profile-template.md` (with `employment: contractor` or `advisor`) → `./Team/External/contractors/{person-slug}/{Person Name}.md`.

If Q6 was skipped, don't scaffold anything under `Team/{org-slug}/Profiles/`. Leave `Team/` with just the `CLAUDE.md` routing index.

### Build Step 4: Mode-specific Additional Setup

**Business mode only:**
- If Q10 mentioned org-wide processes / SOPs, capture them in `Intelligence/processes/{name}.md`
- If user provided onboarding docs, route them to `Onboarding/{name}.md`

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
- Key command: `/assistant` (sessions, daily reviews, tasks, meetings)
- "You can add more context anytime — just tell me and I'll update the right files."
- Suggest a next action based on what they told you

## Guidelines

- Phase 0 is one question — mode selection
- Phase A is fully automated — no user input needed
- Phase B is exactly 10 questions, presented together — no follow-ups, no drilling deeper
- Accept any format: numbered answers, pasted docs, uploaded files, or skips
- Extract as much as you can from whatever the user provides
- Only create context files that have real content — don't create empty placeholder files
- Use the user's actual project names and people names, not generic placeholders
- Don't narrate every file you're creating — just build it and summarize at the end
