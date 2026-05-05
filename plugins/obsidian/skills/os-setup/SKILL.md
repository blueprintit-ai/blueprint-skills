---
name: os-setup
description: Bootstrap the BenAI OS Plugin vault structure and run personalized onboarding. Creates all directories, system files, Obsidian config, memory system, hooks, and output styles, then interviews the user to personalize everything. Two modes — Solopreneurs/Professionals (default), Business/Teams. Use when user says "set up", "bootstrap", "initialize", "onboarding", or runs /os-setup.
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

Twelve questions. Present them all in a single message. The user can answer one-by-one, paste a doc that covers several, upload files, or skip any individually. Don't ask follow-ups. Extract what's there. The questions differ by mode.

**Tip for the user (include in the message)**: You can paste links (LinkedIn profiles, company websites, blog posts, About pages, intake docs) instead of typing answers. I'll fetch them with WebFetch / WebSearch and pull what's relevant. The more I have, the less generic the assistant will feel on day one.

### Mode-specific Questions

**Solopreneurs/Professionals mode** — present all 12 in one message:

#### IDENTITY

1. **Who you are.**
   - Name, role/title, location, industry
   - When and how you do your best work (mornings? deep blocks? after a walk?)
   - If someone you respected had to introduce you in a room of people you respected, how would you want them to describe you?
   - 5 attributes that describe you (one or two words each)

2. **Origin and point of view.**
   - Why you started or joined what you're doing now
   - A belief or POV you hold strongly, even when it's unpopular
   - The "big idea" your work is built on (the wedge, the thesis)
   - Who or what you're fighting against. Could be a category, a behavior, a competitor archetype, a status quo.

#### WHAT YOU SELL

3. **Business or product lines.**
   For each revenue line (one paragraph each, or skip if none yet):
   - Name, what it does, who it's for, stage
   - Current revenue baseline if applicable
   - How it came to exist. What made you start it.

4. **Offer and promises.**
   - The 1 to 3 problems you solve for customers
   - For each problem: are customers already aware they have it, or do you have to teach them? (this changes everything about how you market)
   - Your value proposition in one sentence
   - The promise or guarantee you make (explicit or implicit)
   - Why customers actually pick you. In their words if you've heard them say it.

#### WHO YOU SERVE

5. **Ideal customer.**
   - Title, role, industry, responsibilities
   - What their day looks like, what tools they live in
   - The language and words *they* use to describe their problem
   - The dream outcome they want
   - The situation they're in *before* they come to you. What triggered the search.
   - How long they typically take to decide to buy
   - The media, podcasts, newsletters, or creators they follow
   - 3 to 5 real examples (names, LinkedIn profiles, or company names)

#### BRAND

6. **Voice and visual identity.**
   - Tone descriptors that fit (direct, warm, dry, technical, playful, serious, supportive, or your own)
   - 5 attributes that describe how you *sound*
   - Signature phrases you actually use
   - Words or phrases you'd never use
   - Topics you love talking about
   - Topics you refuse to discuss publicly
   - Brand colors, fonts, taglines if you have them
   - The feeling people should carry away after reading your stuff
   - Or: paste a writing sample and I'll extract from it

7. **Positioning.**
   - The enemy you're fighting (the category, behavior, or competitor archetype)
   - How you solve the problem *differently* from the obvious alternatives
   - 3 to 4 distinct messages you want associated with your name or brand

#### STRATEGY

8. **This year's priorities (measurable).**
   - 1 to 3 outcomes with a number attached (revenue, audience size, ship date)
   - The *why* behind each
   - What you're explicitly saying no to in order to focus here

#### OPERATIONS

9. **Active projects.**
   For each project:
   - Name, one-line purpose, status, deadline if any
   - Which business it belongs to (if multiple)
   - Who else is involved

10. **People you work with regularly.**
    - Team, contractors, key external contacts
    - For each: name, role, how you work together
    - Skip if fully solo

11. **Tools and infrastructure.**
    - Stack across communication, meetings, CRM, content, finance, dev, automation
    - Source of truth for each main workflow. Where deals live, where decisions live, where writing actually happens, where the calendar lives.

12. **Workflows to automate and what's draining your attention.**
    - Top 1 to 2 painful, repetitive workflows. Use this template:
      When **X** happens → I do **Y** → it takes **Z** time → output is **W** → what I want is **V**
    - What's draining your attention right now. Unclosed loops, decisions sitting unmade, things that should be done but aren't.

**Business mode** — present all 12 in one message:

#### YOU AND THE COMPANY

1. **You. Operator profile.**
   - Name, title, department, who you report to
   - Decision authority (what you can sign off on alone)
   - Location, working style
   - What's draining your attention right now. Unclosed loops, decisions sitting unmade.

2. **Company essentials.**
   - Legal entity name, industry, stage
   - Founded year, headcount (FT + contractors)
   - Headquarters and where the team is based
   - One-sentence mission
   - Why the company started (origin)
   - The belief or POV the company stands for

#### MARKET

3. **Industry and market context.**
   - The broad target industry
   - The specific niche you operate in
   - Trends and hot topics in the industry right now
   - What's not going well in the industry. The inefficiency or broken thing you're betting against.
   - What changed in the last 5 to 10 years
   - The main players (incumbents, competitors, adjacent categories)

#### WHAT YOU SELL

4. **Products, services, or business units.**
   For each revenue line:
   - Name, what it does, who buys it
   - Current revenue baseline, status (active, new, sunsetting)

5. **Offer and promises.**
   - The 1 to 3 problems you solve for customers
   - For each: are customers already aware they have it, or do you teach them?
   - Value proposition in one sentence
   - The promise or guarantee you make
   - Key features and capabilities that deliver the value
   - Why customers actually pick you over alternatives
   - The kind of results you typically deliver. Include a real example if you have one.

#### WHO YOU SERVE

6. **ICP and customer journey.**
   - Who's in charge of buying. Title, role, responsibilities.
   - What their day looks like, what tools they use
   - The language and words *they* use to describe their problem
   - Dream outcome they want
   - Situation before buying. What triggered them to look.
   - How long the buying decision typically takes
   - Market trends affecting them right now
   - Media, podcasts, or creators they follow
   - 3 to 5 real examples (LinkedIn profiles or company names)

#### BRAND

7. **Voice and visual identity.**
   - Tagline and value prop in plain language
   - Voice in a paragraph or as descriptors (direct, warm, dry, technical)
   - 5 attributes that describe how the brand sounds
   - Signature phrases used across your content
   - Words or phrases you'd never use
   - Topics you love covering
   - Topics you avoid publicly
   - Brand colors, fonts, logo notes
   - The feeling readers and customers should carry away

8. **Positioning.**
   - The enemy. The category, status quo, or competitor archetype you're fighting.
   - How you solve the problem *differently* from obvious competitors
   - Brand personality in 5 adjectives
   - The "big concept" the company is built on
   - 3 to 4 distinct messages you want associated with the brand

#### OPERATIONS

9. **Departments and team members getting profiles.**
   - The departments and the lead for each
   - Team members getting their own profile folders. For each: name, role, reports-to, FT or contractor, location.
   - (Profile folders include their own daily notes, tasks, and sub-schedules.)

10. **Annual objectives and key results.**
    - 1 to 3 objectives for the year (or quarter)
    - For each KR: target number, owner, current status
    - The *why* behind each objective
    - What you're explicitly saying no to in order to focus here

11. **Active projects and initiatives.**
    For each project:
    - Name, owner, status, deadline if any
    - Client-facing or internal
    - Which business unit or department it sits under
    - Key collaborators

12. **Tools, workflows, and stakeholders.**
    - Stack across communication, meetings, CRM, PM, content, finance, dev
    - Source of truth for each main workflow. Where deals live, where decisions live, where writing happens, where the calendar lives.
    - Top 3 painful, repetitive workflows. Template:
      When **X** happens → we do **Y** → it takes **Z** → output is **W** → what we want is **V**
    - External stakeholders: investors, partners, vendors, top clients. Name, type, nature of the relationship.

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

**Solopreneurs/Professionals mode** (Q1–Q12 = solo questions):

- **`Context/me.md`** — Always created. Fill from Q1 (identity, role, location, work style, intro phrase, 5 attributes), Q2 (Origin & POV section: why started, belief, big idea, enemy), Q12 (Unclosed Loops section). Read `references/context-me.md` as template.
- **`Context/business.md`** — Only if Q3 had content. Fill name, what it does, who it's for, stage, revenue, origin. Read `references/context-business.md` as template.
- **`Context/services.md`** — Only if Q3 listed multiple revenue lines or named services / products. Read `references/context-services.md` as template.
- **`Context/pain-points.md`** — Only if Q4 had content. Fill from the 1–3 problems with the awareness column (aware vs teach them). Read `references/context-pain-points.md` as template.
- **`Context/icp.md`** — Only if Q5 had content. Fill role, day, language, dream outcome, trigger, decision time, media, real examples. Read `references/context-icp.md` as template.
- **`Context/brand.md`** — Only if Q6 or Q7 had content. From Q4 take value prop, promise, why-pick-you. From Q6 take voice, attributes, signature phrases, words-to-avoid, topics, visual identity, feeling. From Q7 take Positioning section: enemy, differentiation, key messages. Read `references/context-brand.md` as template.
- **`Context/strategy.md`** — Only if Q8 had content. Read `references/context-strategy.md` as template.
- **`Context/team.md`** — Only if Q10 had content. Read `references/context-team.md` as template.
- **`Context/infrastructure.md`** — Only if Q11 listed tools or Q12 listed workflows. Combine tool stack (Q11) with workflows-to-automate template (Q12). Read `references/context-infrastructure.md` as template.

**Business mode** (Q1–Q12 = business questions):

- **`Context/operator.md`** — Always created. Fill from Q1 (role, decision authority, location, working style, unclosed loops). Read `references/context-operator.md` as template.
- **`Context/organization.md`** — Always created. Fill from Q2 (company info, mission, headcount, stage, plus Origin & POV section: why started + belief). Read `references/context-organization.md` as template.
- **`Context/market.md`** — Only if Q3 had content. Fill industry, niche, trends, what's broken, what changed, main players. Read `references/context-market.md` as template.
- **`Context/services.md`** — Only if Q4 had content. Read `references/context-services.md` as template.
- **`Context/pain-points.md`** — Only if Q5 had content. Fill problems with awareness column. Read `references/context-pain-points.md` as template.
- **`Context/icp.md`** — Only if Q6 had content. Fill role, day, language, dream outcome, trigger, decision time, market trends, media, real examples. Read `references/context-icp.md` as template.
- **`Context/brand.md`** — Only if Q7 or Q8 had content. From Q5 take value prop, promise, results. From Q7 take voice + visual. From Q8 take Positioning section: enemy, differentiation, brand personality, big concept, key messages. Read `references/context-brand.md` as template.
- **`Context/team.md`** — Always created. Fill with any team members from Q9. Read `references/context-team.md` as template.
- **`Context/strategy.md`** — Always created. Fill from Q10 (OKRs, KRs, owners, why behind each, what you're saying no to). Read `references/context-strategy-business.md` as template.
- **`Context/infrastructure.md`** — Only if Q12 listed tools or workflows. Combine tool stack with the workflows-to-automate template. Read `references/context-infrastructure.md` as template.
- **`Context/stakeholders.md`** — Only if Q12 mentioned investors, partners, vendors, or top clients. Read `references/context-stakeholders.md` as template.

### Build Step 2: Create Project Folders

Solo: from Q9. Business: from Q11. Intelligently structure each project based on what the user gave you.

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

**Business mode only** — from Q9, also create `Departments/{name}/README.md` for each department with the lead's name, charter placeholder, and `sops/` subfolder.

### Build Step 3: Profile-First Team Scaffolding (Business mode only)

From Q9, scaffold each person's profile workspace. Slug names are kebab-case.

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

If Q9 listed no team members, don't scaffold anything under `Team/{org-slug}/Profiles/`. Leave `Team/` with just the `CLAUDE.md` routing index.

### Build Step 4: Mode-specific Additional Setup

**Business mode only:**
- If Q12 mentioned org-wide processes / SOPs, capture them in `Intelligence/processes/{name}.md`
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
- Phase B is exactly 12 questions, presented together — no follow-ups, no drilling deeper
- Accept any format: numbered answers, pasted docs, uploaded files, links (LinkedIn, websites, blog posts), or skips
- If the user pastes a link, fetch it with WebFetch / WebSearch and extract what's relevant before mapping into the context files
- Extract as much as you can from whatever the user provides
- Only create context files that have real content — don't create empty placeholder files
- Use the user's actual project names and people names, not generic placeholders
- Don't narrate every file you're creating — just build it and summarize at the end
