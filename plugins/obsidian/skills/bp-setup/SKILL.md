---
name: bp-setup
description: Bootstrap the BenAI OS Plugin vault structure and run personalized onboarding. Creates all directories, system files, Obsidian config, memory system, hooks, and output styles, then interviews the user to personalize everything. Two modes — Solopreneurs/Professionals (default), Business/Teams. Use when user says "set up", "bootstrap", "initialize", "onboarding", or runs /bp-setup.
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

**Six** focused questions, asked **sequentially via AskUserQuestion** — one question per call, never dumped as a wall of text. Six is intentional: cover the highest-leverage essentials only. Anything deeper comes from Phase B+ (file / link drop), where the user shares brand decks, About pages, OKR docs, project briefs, etc.

For each question:
- Put the full prompt into the `question` field
- Provide the listed quick-pick `options` (typically 3 archetype shortcuts + an explicit "Skip" option)
- "Other" is auto-added by the tool — that's where the user types the long-form answer (most users will use this) or pastes a link
- Use the listed `header` (max 12 chars)
- Set `multiSelect: false`
- After each answer, immediately move to the next question — no commentary, recap, or summarization in between
- If the user picks "Skip" or leaves "Other" empty, treat that question as skipped and move on

**Before Q1, send one short orienting message** (no AskUserQuestion yet):
> "Six quick questions to personalize your vault, then I'll ask if you want to drop in extra files or links for deeper context. Each question has shortcut options — pick 'Other' to type or paste a link. Skip any you want. Reply 'skip all' to proceed with defaults."

If the user pastes a link in the "Other" field, fetch it with WebFetch / WebSearch and extract what's relevant before mapping to context files.

If the user replies "skip all" at any point, stop asking and proceed to Phase B+ (still ask once for files / links — that's often where the real personalization comes from).

The questions differ by mode.

### Solopreneurs/Professionals mode — 6 sequential AskUserQuestion calls

For each question below: call `AskUserQuestion` with the listed `question`, `header`, and `options`. The full prompt text goes inside `question`. The options' `description` field is shown under each label.

**Q1 — You.** Header: `You`
- Question: "Quick intro. Name, what you do in one line, where you're based, and how you'd want a respected peer to describe you in a room."
- Options:
  - `Founder / Solopreneur` — "Running my own thing"
  - `Freelancer / Consultant` — "Client work, mostly solo"
  - `Employee + side project` — "Day job plus something on the side"
  - `Skip` — "Skip this question"

**Q2 — What you sell + who buys.** Header: `Offer`
- Question: "Your main offer, the problem it solves, and who buys it (their role / world / a few real examples or LinkedIn profiles if you have them)."
- Options:
  - `One main offer` — "Single product or service"
  - `Multiple offers / lines` — "Two or more revenue lines"
  - `Pre-revenue / building` — "Not selling yet"
  - `Skip` — "Skip this question"

**Q3 — Why you (POV + positioning).** Header: `Why you`
- Question: "Why customers pick you over alternatives. The wedge — your POV, the enemy or status quo you're fighting, what you do differently. In your words or theirs."
- Options:
  - `Clear differentiation / enemy` — "I know what makes me different"
  - `Strong POV / thesis` — "I'll describe my belief"
  - `Still figuring it out` — "Keep this light for now"
  - `Skip` — "Skip this question"

**Q4 — Voice.** Header: `Voice`
- Question: "How you sound. A few descriptors (direct, warm, dry, technical, playful), signature phrases you use, words you'd never use. Or paste a writing sample / link and I'll extract."
- Options:
  - `Paste a writing sample / link` — "Pull voice from my actual writing"
  - `Describe my voice` — "I'll describe it in 'Other'"
  - `Use sensible defaults` — "Pick a reasonable voice for now"
  - `Skip` — "Skip this question"

**Q5 — Right now (priorities + projects).** Header: `Now`
- Question: "What's on your plate this quarter. Top 1–3 priorities (with a number if measurable) and the active projects you're shipping. Just names + a one-line purpose for each project is enough."
- Options:
  - `Revenue / growth focus` — "Money is the main metric"
  - `Build / ship something` — "Building or launching"
  - `Audience / community focus` — "Reach and trust"
  - `Skip` — "Skip this question"

**Q6 — Stack + drains.** Header: `Stack`
- Question: "Tool stack (where deals, decisions, writing, calendar actually live) plus the 1–2 things draining your attention or workflows you'd kill to automate."
- Options:
  - `Walk through stack + drains` — "I'll describe in 'Other'"
  - `Paste from a stack doc` — "I have it somewhere"
  - `Mostly attention drains` — "Focus on what's draining me"
  - `Skip` — "Skip this question"

### Business/Teams mode — 6 sequential AskUserQuestion calls

For each question below: call `AskUserQuestion` with the listed `question`, `header`, and `options`.

**Q1 — Company.** Header: `Company`
- Question: "The company in plain language. Legal name, industry, stage, headcount, one-sentence mission, why it started."
- Options:
  - `Early stage (1–10)` — "Small, early"
  - `Growth (10–50)` — "Scaling"
  - `Established (50+)` — "Mature company"
  - `Skip` — "Skip this question"

**Q2 — What you sell + who buys.** Header: `Offer`
- Question: "Main products / services, the problem each solves, and who buys (their role + world). 3–5 real customer examples or LinkedIn profiles if you can. Paste a sales deck or product page link if it's faster."
- Options:
  - `Single product / service` — "One main offering"
  - `Multiple products / SKUs` — "Several offerings"
  - `Multiple business units` — "Distinct lines of business"
  - `Skip` — "Skip this question"

**Q3 — Brand (voice + positioning).** Header: `Brand`
- Question: "Brand voice + positioning. How it sounds (descriptors, signature phrases, words to avoid). Who you're fighting against and what makes you different. Paste a brand guide / About page if you have one."
- Options:
  - `Paste brand guidelines / About page` — "I have a doc / link"
  - `Describe brand + positioning` — "Walk through prompts in 'Other'"
  - `Use sensible defaults` — "Pick something reasonable for now"
  - `Skip` — "Skip this question"

**Q4 — Team + projects.** Header: `Team`
- Question: "The team and what's in flight. Departments + the lead for each, key people getting their own profile (name, role, FT or contractor), and the active projects / initiatives + owners."
- Options:
  - `List departments + key people` — "I'll list them in 'Other'"
  - `Small team, no formal departments` — "A few key people only"
  - `Paste an org chart / project list` — "I have docs"
  - `Skip` — "Skip this question"

**Q5 — Goals + stack + stakeholders.** Header: `Stack`
- Question: "This year's goals and how the company runs. 1–3 OKRs / objectives (target numbers + owners), the tool stack across comms / CRM / PM / content / finance, the top 2–3 painful workflows, and key external stakeholders (investors, partners, top clients)."
- Options:
  - `Walk me through it` — "I'll describe in 'Other'"
  - `Paste OKRs / stack docs` — "I have docs"
  - `Mostly stakeholders` — "Investors, partners are priority"
  - `Skip` — "Skip this question"

**Q6 — Operator (you).** Header: `Operator`
- Question: "Last one — quick operator profile. Name, title, who you report to, what you can sign off on alone, and what's draining your attention right now."
- Options:
  - `Founder / CEO` — "I run the whole company"
  - `Department head / VP` — "I lead a function or team"
  - `Operator / Chief of Staff` — "Cross-org role"
  - `Skip` — "Skip this question"

The user might respond to any question by:
- Picking a quick-pick option
- Picking "Other" and typing a paragraph or pasting a link / doc
- Picking "Skip"
- Replying "skip all" anywhere — stop asking and move to Phase B Build

**Accept whatever they give.** Don't ask follow-ups inside a question. Extract what you can.

**If the user skips everything** — proceed to build with defaults only.

---

## Phase B+: Additional Context Drop

After Q6 (or "skip all") and **before** Phase B Build, ask one final `AskUserQuestion` to invite extra source material. With only 6 questions answered, this step is where the real depth comes from. Most users have brand decks, About pages, intake forms, LinkedIn URLs, Notion docs, PDFs, slide exports, voice/style guides, OKR docs, org charts, project briefs, etc. Always ask, even if Q1–Q6 looked rich.

**Call AskUserQuestion** (one question, header: `Context`):
- Question: "Anything else I should pull from before building? Upload files (PDFs, MDs, DOCXs), paste links (LinkedIn, websites, Notion pages, Google Docs), point me at a local folder, or paste raw text. The more I have, the more personalized your vault will be — instead of template scaffolds with placeholders."
- Options:
  - `Yes — I'll paste links / upload files` — "Walk me through it"
  - `Yes — point me at a folder on disk` — "I have local files"
  - `No — use just the answers above` — "Build with what we have"
  - `Skip` — "Skip this step"

**If the user picks a "Yes" option** (or pastes content directly):

1. Collect everything they share. Be greedy — accept anything they offer.
2. **For each link**: call `WebFetch` (or `WebSearch` if the URL is a search). Extract the relevant content.
3. **For each uploaded file or local file path**:
   - `.md`, `.txt`, `.json`, `.yaml`, `.csv` → read directly with `Read`
   - `.pdf` → read with `Read` (use `pages` parameter if >10 pages)
   - `.docx`, `.pptx`, `.xlsx` → use Bash with `pandoc` or `textutil` if available; otherwise tell the user to export as PDF or MD and re-share
   - Images / screenshots → read with `Read` (multimodal)
4. **For a local folder path**: use `Glob` to enumerate, then read each file.
5. **Maintain a context corpus** in working memory — every fact, name, number, quote you find. Tag each by likely target (`me.md`, `brand.md`, `icp.md`, `strategy.md`, `projects/{name}`, etc.).
6. After ingestion, briefly tell the user what you pulled (e.g., "Pulled 4 files: brand-guidelines.pdf, about-page.md, okrs-2026.md, team-roster.csv. 18 links fetched."). One sentence. Then proceed to Build.

**If the user picks `No` or `Skip`**: proceed straight to Build with only the Q1–Q12 answers.

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

Behavior depends on selected mode.

For every file below, source data from BOTH the Q answers AND the Phase B+ corpus (uploaded files, fetched links, folder reads). The corpus typically contains the depth — Q answers are anchors.

**Solopreneurs/Professionals mode** (Q1–Q6 = solo questions):

- **`Context/me.md`** — Always created. Fill from Q1 (name, what you do, location, peer-intro line, archetype) + Q3 (POV / wedge / enemy) + Q6 (drains / unclosed loops) + corpus. Read `references/context-me.md` as scaffold.
- **`Context/business.md`** — Only if Q2 had content. Fill from Q2 (offer, problem, who buys) + corpus (About page, business overview docs). Read `references/context-business.md` as scaffold.
- **`Context/services.md`** — Only if Q2 mentioned multiple offers, or corpus has product/service docs. Read `references/context-services.md` as scaffold.
- **`Context/pain-points.md`** — Only if Q2 named a problem or Q3 surfaced one. Include awareness column (aware vs needs education) when the user signaled it. Read `references/context-pain-points.md` as scaffold.
- **`Context/icp.md`** — Only if Q2 mentioned buyers / examples or corpus has ICP / customer docs. Fill role, day, language, dream outcome, trigger, examples. Read `references/context-icp.md` as scaffold.
- **`Context/brand.md`** — Only if Q3 (positioning) or Q4 (voice) had content, or corpus has brand material. From Q2 take value prop + why-pick-you. From Q3 take Positioning section (enemy, differentiation, key messages). From Q4 take voice descriptors, signature phrases, words-to-avoid, feeling. Read `references/context-brand.md` as scaffold.
- **`Context/strategy.md`** — Only if Q5 had content (priorities). Read `references/context-strategy.md` as scaffold.
- **`Context/team.md`** — Only if Q5 mentioned collaborators or corpus has a team / contractor list. Read `references/context-team.md` as scaffold.
- **`Context/infrastructure.md`** — Only if Q6 listed tools or workflows, or corpus has a stack doc. Combine tool stack + workflows-to-automate. Read `references/context-infrastructure.md` as scaffold.

**Business mode** (Q1–Q6 = business questions):

- **`Context/organization.md`** — Always created. Fill from Q1 (company, mission, stage, headcount, origin) + corpus (About page, company deck). Read `references/context-organization.md` as scaffold.
- **`Context/market.md`** — Only if corpus has market / industry material, or Q1/Q2 surfaced industry context. Fill industry, niche, trends, main players. Read `references/context-market.md` as scaffold.
- **`Context/services.md`** — Only if Q2 had content. Fill from Q2 + corpus (sales deck, product pages). Read `references/context-services.md` as scaffold.
- **`Context/pain-points.md`** — Only if Q2 surfaced a problem or corpus has it. Read `references/context-pain-points.md` as scaffold.
- **`Context/icp.md`** — Only if Q2 mentioned buyers / examples or corpus has ICP material. Fill role, day, language, dream outcome, trigger, examples. Read `references/context-icp.md` as scaffold.
- **`Context/brand.md`** — Only if Q3 had content or corpus has brand material. Take voice + positioning from Q3 + brand guide / About page in corpus. Read `references/context-brand.md` as scaffold.
- **`Context/team.md`** — Always created. Fill from Q4 (departments, key people) + corpus (org chart). Read `references/context-team.md` as scaffold.
- **`Context/strategy.md`** — Always created. Fill from Q5 (OKRs, KRs, owners) + corpus (OKR doc). Read `references/context-strategy-business.md` as scaffold.
- **`Context/infrastructure.md`** — Only if Q5 listed tools or workflows, or corpus has a stack / SOPs doc. Combine tool stack with workflows-to-automate. Read `references/context-infrastructure.md` as scaffold.
- **`Context/stakeholders.md`** — Only if Q5 mentioned external stakeholders or corpus has investor / partner / client lists. Read `references/context-stakeholders.md` as scaffold.
- **`Context/operator.md`** — Always created. Fill from Q6 (role, decision authority, drains) + corpus. Read `references/context-operator.md` as scaffold.

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
- Key command: `/assistant` (sessions, daily reviews, tasks, meetings)
- "You can add more context anytime — just tell me and I'll update the right files."
- Suggest a next action based on what they told you

## Guidelines

- Phase 0 is one question — mode selection
- Phase A is fully automated — no user input needed
- Phase B is exactly 6 questions, asked one-at-a-time via AskUserQuestion — no follow-ups, no drilling deeper, no batching into one message. The 6 cover the highest-leverage essentials only; depth comes from Phase B+
- Phase B+ is one final AskUserQuestion inviting additional files / links / folders — always ask, even if Q1–Q6 looked rich. With only 6 questions, this step is where most personalization data comes from
- Accept any format: numbered answers, pasted docs, uploaded files, links (LinkedIn, websites, blog posts), local folder paths, or skips
- For every link the user pastes, fetch it (`WebFetch` / `WebSearch`); for every file or folder, read it (`Read` / `Glob`); merge into a single context corpus before building
- **Templates are scaffolds, not outputs.** Replace every `[bracketed placeholder]` with real user data. If a section has no data after exhausting Q answers + corpus, omit the section — never leave placeholders in the written file
- Preserve specificity: use the user's exact names, numbers, URLs, and phrasing
- Only create context files that have real content — don't create empty placeholder files
- Don't narrate every file you're creating — just build it and summarize at the end
