---
name: bp-audit
description: Shop OS vault health check. Scores the vault across four dimensions — Context (does it know the shop?), Connections (can it reach real data?), Capabilities (are skills being used?), Cadence (is it running without being asked?) — out of 100. Surfaces top 3 gaps with concrete next steps and shows the Automation Ladder so owners know where each workflow sits and what the next level up looks like. Run monthly or when onboarding a new customer. TRIGGERS: audit vault, score my vault, shop os audit, how is my vault set up, vault health, audit my shop os, bp audit, how am I doing, is my vault working.
---

# Shop OS Audit

Score the vault across four dimensions. Read only. Report the score, strengths, top 3 gaps, and Automation Ladder. Offer to save the report. Done.

## Pre-flight

Verify `CLAUDE.md` exists at vault root. If not: stop and tell the user to `cd` into the vault root and re-run.

Read the vault's root `CLAUDE.md` to understand the routing conventions and shop context before scoring.

## The Four Dimensions (25 pts each = 100 total)

| Dimension | Question |
|---|---|
| **Context** | Does the vault know this shop? |
| **Connections** | Can it reach real business data? |
| **Capabilities** | Are the right workflows active and being used? |
| **Cadence** | Is it running without being asked? |

---

## Scoring

### Context (25 pts)

Does the vault have a real picture of who this shop is and how they operate? Placeholder files and empty templates score 0 on every criterion they would otherwise satisfy.

| Criterion | Pts | How to detect |
|---|---|---|
| Shop identity exists (`Context/organization.md` or equivalent — shop name, owner, location, trade focus, years in business) | 5 | Read the file. Generic text or `{{placeholders}}` = 0. |
| Services defined (`Context/services.md` — cabinet types, materials, lead times, pricing model, what they will and won't do) | 5 | "We do cabinets" = 1. Specific door styles, box material, finish options, lead times = 5. |
| Customer profile exists (`Context/icp.md` or `Context/customers/` — who they sell to, job size, geography) | 5 | File exists with specific detail, not placeholder. |
| Pricing resources exist (`Resources/pricing/` has at least one supplier price list, material cost sheet, or estimate template) | 5 | `find Resources/pricing -name "*.md" 2>/dev/null \| wc -l` ≥ 1 |
| Team defined (`Context/team.md` — who does what, contact info, roles) | 5 | File exists with actual names and roles. |

### Connections (25 pts)

Can the vault reach real business data, or is it disconnected from what actually runs the shop?

Cabinet shop data domains:

| Domain | Examples |
|---|---|
| Estimating | Cabinet Vision, Microvellum, SketchList, Excel-based quote sheets |
| Suppliers | Hardware, lumber, finish materials — price lists imported into vault |
| Customers | Project files, job history, signed contracts |
| Financials | QuickBooks, Wave, spreadsheet P&L, invoice records |
| Job photos | Completed work, inspiration images, in-progress shots |
| Communications | Call notes, email summaries, site visit notes |

| Criterion | Pts | How to detect |
|---|---|---|
| Estimating tool or process referenced in vault (tool named in Context, or quote template exists) | 5 | grep for estimating tool names; or pricing/quote templates in `Resources/` |
| Supplier price lists in vault (at least one imported and readable) | 5 | `find Resources/pricing -name "*.md" 2>/dev/null \| wc -l` ≥ 1 |
| Customer/project files exist (`Projects/` has ≥1 real job folder with content) | 5 | `find Projects -maxdepth 1 -type d 2>/dev/null \| wc -l` ≥ 2 |
| Financial data referenced or imported (invoices, P&L notes, revenue records) | 5 | grep vault for: invoice, revenue, QuickBooks, P&L, profit |
| Job communication in vault (call notes, email summaries, site visit notes) | 5 | `find . -name "*.md" -path "*/calls/*" 2>/dev/null \| wc -l` ≥ 1, or similar communication logs in Projects/ |

### Capabilities (25 pts)

Are the right workflows active and being used? Installed but never run = 0 on usage criteria.

| Criterion | Pts | How to detect |
|---|---|---|
| bp-digest has been run (`Raw/processed/` exists and contains files) | 8 | `find Raw/processed -name "*.md" 2>/dev/null \| wc -l` ≥ 1 |
| bp-digest used regularly (processed files dated within 30 days) | 7 | Check modification dates on files in `Raw/processed/` — any modified in the last 30 days? |
| bp-setup completed (Context/ files are filled, not placeholder) | 5 | Read `Context/organization.md` — `{{...}}` or blank = 0 |
| Custom skills or workflows defined (beyond the default Shop OS skills) | 5 | `find .claude/skills -name "SKILL.md" 2>/dev/null \| wc -l` — count above 6 (the default installs) |

### Cadence (25 pts)

Is the vault running on a rhythm, or only touched when something breaks?

| Criterion | Pts | How to detect |
|---|---|---|
| Daily or weekly notes written recently (any profile daily note in the last 14 days) | 8 | `find . -name "*.md" -path "*/Daily/*" -newer /tmp/bp-audit-14d 2>/dev/null \| wc -l` ≥ 1 (create the sentinel: `touch -t $(date -v-14d '+%Y%m%d%H%M') /tmp/bp-audit-14d`) |
| bp-operator configured (recurring schedule or hook active) | 7 | `find .claude -name "settings.json" 2>/dev/null \| xargs grep -l "hook\|schedule\|cron" 2>/dev/null` returns a result; or `Intelligence/` has a recurring-tasks note |
| Decision log has entries (`Intelligence/decisions/log.md` exists with ≥3 real entries) | 5 | Read the file — count `## ` headers (each is one decision entry) |
| Intelligence/ is populated (meetings, competitor notes, or market intel beyond placeholders) | 5 | `find Intelligence -name "*.md" -not -name "CLAUDE.md" 2>/dev/null \| wc -l` ≥ 3 |

---

## Execution

Run all checks silently via Bash and Read. No mid-audit commentary. Then:

1. Compute total score and identify stage.
2. Find the top 3 gaps: rank by points lost, break ties by business impact for a cabinet shop.
3. Build the Automation Ladder (see below).
4. Output the full report in chat.
5. Offer to save: "Save this to `Intelligence/decisions/audit-{date}.md`?" Write if yes.

---

## Automation Ladder

After scoring, assess where each active workflow currently sits on the autonomy ladder. Include this table in the report.

| Level | Name | What it means |
|---|---|---|
| L0 | Manual | Done entirely by hand — no AI involvement |
| L1 | Suggested | AI surfaces options; owner decides every step |
| L2 | Drafted | AI drafts (quotes, summaries, call notes); owner reviews before anything goes out |
| L3 | Supervised | AI handles routine work; owner spot-checks weekly |
| L4 | Autonomous | AI runs end-to-end; owner reviews exceptions only |

For each workflow below, detect the current level from the vault state and note the next step up. Default recommendation: move one level at a time.

| Workflow | How to detect current level |
|---|---|
| Inbox digesting | L0 if Raw/ has unprocessed files sitting >14 days; L2+ if processed/ is regularly populated |
| Job notes and call summaries | L0 if absent; L1-L2 if notes exist in Projects/; L3 if bp-operator is scheduling reminders |
| Supplier price list updates | L0 if prices are in someone's head; L2 if imported via bp-digest; L3 if refreshed on a schedule |
| Estimate drafting | L0 if no template exists; L1-L2 if a template lives in Resources/; L3+ if estimates are triggered automatically from job intake |
| Customer communication | L0 if no call notes or email summaries; L2 if summaries appear in Projects/ regularly |

---

## Report Format

Print this exactly — specific to this shop's data, not generic:

```
# Shop OS Audit — {date}
**Score: {total}/100** — {stage}

Stages: 0-39 Foundation | 40-69 Active | 70-89 Productive | 90-100 Leveraged

## Scoreboard

Context        {████░░░░░░}  {n}/25  {label}
Connections    {████░░░░░░}  {n}/25  {label}
Capabilities   {████░░░░░░}  {n}/25  {label}
Cadence        {████░░░░░░}  {n}/25  {label}

(█ per 5pts; Strong ≥20 | Solid 15-19 | Thin 8-14 | Missing <8)

## Strengths
- {specific finding from highest-scoring criteria, named to this shop's actual data}
- {specific finding}

## Top 3 Gaps

1. **{gap name}** (-{pts} pts)
   → {one concrete next step — name the file to create, the skill to run, or the action to take}

2. **{gap name}** (-{pts} pts)
   → {one concrete next step}

3. **{gap name}** (-{pts} pts)
   → {one concrete next step}

## Automation Ladder

| Workflow | Current Level | Next Step |
|---|---|---|
| Inbox digesting | L{n} — {description} | {what to do next} |
| Job notes | L{n} — {description} | {what to do next} |
| Supplier prices | L{n} — {description} | {what to do next} |
| Estimate drafting | L{n} — {description} | {what to do next} |
| Customer comms | L{n} — {description} | {what to do next} |

---
Run /bp-audit monthly to track progress. Next: {single most leveraged action from Gap 1}.
```

---

## Hard Rules

- Read-only except the optional saved report.
- Be honest. Placeholder files = 0 on every criterion they fail. A freshly set-up vault should score 15-35.
- Be specific to this shop. "Add more files" is a failing output. Name the missing supplier, the specific project folder, the actual workflow that's at L0.
- Never inflate scores to be encouraging. A 40 that's real is more useful than a 70 that isn't.
- Never write to the vault except the single optional audit report.
