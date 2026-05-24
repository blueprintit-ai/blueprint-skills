---
name: os-evolver
description: Karpathy + Nodus self-evolving research loop for any markdown vault. Runs deterministic graph analysis (betweenness centrality, Louvain communities, structural-hole detection), surfaces failure-mode diagnostics (star topology, fragmentation, high orphan rate, hub dependence, siloed content, empty hubs), bulk-injects [[wikilinks]] across the vault (mechanical and LLM-based), and uses the agent to draft canonical notes for dangling references. Closes the loop, so the vault literally fills its own gaps and gets structurally healthier on each pass. All LLM work runs through the user's Claude Code subscription, no separate API key required. Outputs persist inside the vault under `Reports/knowledge-graph/` and `drafts/` for review. TRIGGERS: os evolver, evolve my vault, graph my vault, graph my knowledge, knowledge graph audit, strategic knowledge audit, self-evolving wiki, wikilink enrich, fill dangling notes, draft missing notes, bridge questions. Run from the vault root.
---

# OS Evolver

The closed self-evolving loop for a Karpathy-style LLM Wiki, with deterministic graph metrics on top. All LLM work happens through the user's Claude Code subscription. No separate `ANTHROPIC_API_KEY` ever required.

## Architecture (important: subscription, not API)

Every LLM-driven phase splits into two parts:

1. **A Python "prep" script** that walks the vault deterministically and emits a single markdown task file. This step is free, fast, and reusable. It needs no API key.
2. **An agent step** where Claude (running under the user's Claude Code subscription) reads the prep file and produces the actual deliverable (drafts, questions, suggestions).

This means the entire skill runs on the customer's existing Claude Code subscription. There is never a moment where the user is prompted for an Anthropic API key, exports an environment variable, or wires up a separate billing surface.

## Pre-flight Check

1. The current working directory MUST be a vault root. Verify `CLAUDE.md` or `claude.md` exists in cwd. If missing: tell the user *"This is not a vault root. `cd` into your vault and re-run."* Stop.
2. Read the `os-mode` field in the vault's root `CLAUDE.md` frontmatter to detect mode (`professional` or `business`).
3. Verify Python 3.10+ is available: `python3 --version`. If absent, ask the user to install Python.
4. Install / verify dependencies once per machine: `python3 -m pip install --user -r "${CLAUDE_PLUGIN_ROOT}/skills/os-evolver/scripts/requirements.txt"`. The requirements are `networkx`, `requests`, `beautifulsoup4`, `markdownify`. No `anthropic` package — the agent handles all LLM work.

## Path conventions

- **Scripts** live at `${CLAUDE_PLUGIN_ROOT}/skills/os-evolver/scripts/`. Invoke them with absolute paths.
- **Reference files** (`references/foo.md`) live next to **this SKILL.md** — read them with absolute paths relative to the SKILL.md location.
- **Vault outputs** land under the user's cwd:
  - Graph reports: `Reports/knowledge-graph/YYYY-MM-DD-graph-report.{md,json}`
  - Mechanical enrichment review queue: `Reports/knowledge-graph/wikilink-enrichment-review-YYYY-MM-DD.md`
  - LLM enrichment task file: `Reports/knowledge-graph/wikilink-llm-tasks-YYYY-MM-DD.md`
  - LLM enrichment review queue (agent-produced): `Reports/knowledge-graph/wikilink-llm-enrichment-review-YYYY-MM-DD.md`
  - Note-drafting task file: `Reports/knowledge-graph/note-drafting-tasks-YYYY-MM-DD.md`
  - Drafted notes (agent-produced): `drafts/YYYY-MM-DD/` plus an `INDEX.md`
  - Bridge-question task file: `Reports/knowledge-graph/bridge-question-tasks-YYYY-MM-DD.md`
  - Bridge questions (agent-produced): `Reports/knowledge-graph/bridge-questions-YYYY-MM-DD.md`
  - External content corpora (audit engagements only): `corpora/<slug>/`

Create these directories on first run; do not ask permission.

## Phase 0 — Reconnaissance (always run first)

Survey the vault before deciding what to do.

```sh
VAULT="$PWD"
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/os-evolver/scripts"
TODAY=$(date +%Y-%m-%d)

# Count knowledge markdown files
FILES=$(find "$VAULT" -name "*.md" \
  ! -path "*/.obsidian/*" ! -path "*/.trash/*" ! -path "*/.git/*" \
  ! -path "*/corpora/*" ! -path "*/Reports/*" ! -path "*/reports/*" \
  ! -path "*/drafts/*" ! -path "*/output/*" \
  ! -name "CLAUDE.md" ! -name "GEMINI.md" ! -name "AGENTS.md" | wc -l | tr -d ' ')

# Count wikilinks
WIKILINKS=$(grep -rhoE '\[\[[^\]]+\]\]' "$VAULT" --include="*.md" 2>/dev/null | wc -l | tr -d ' ')

# Latest graph report (if any)
LATEST_REPORT=$(ls -t "$VAULT/Reports/knowledge-graph/"*graph-report.json 2>/dev/null | head -1)
```

Compute:
- `density = WIKILINKS / FILES`
- If `LATEST_REPORT` exists, parse its `dangling`, `orphan_count`, `findings` fields
- `days_since_graph` = age of `LATEST_REPORT` in days, or `Inf`

Tell the user in one paragraph what you found. Numbers, not adjectives.

## Phase routing decision

Apply this decision tree. Pick the FIRST matching phase.

| Condition | Phase |
|---|---|
| `FILES < 10` | Stop and explain the vault is too small |
| `density < 0.5` and no recent enrichment | **Phase 1A — mechanical enrich** |
| `density < 1.5` and Phase 1A applied, no LLM enrichment yet | **Phase 1B — LLM enrich (agent-driven)** |
| `days_since_graph > 7` or no graph | **Phase 2 — graph + diagnostics** |
| `dangling_count > 0` from latest report | **Phase 3 — draft notes (agent-driven)** |
| Otherwise | Status report |
| User explicitly asked | Override the tree |

Confirm the chosen phase with the user before writing to the vault. Use `AskUserQuestion` if multiple phases could apply.

## Phase 1A — Mechanical wikilink enrichment

Deterministic title-matcher. No API or agent calls. Free.

```sh
# Step 1: review queue.
python3 "$SCRIPTS/wikilink_enricher.py" --vault "$VAULT" --max-per-note 20

# Step 2 (after user skims): apply with .bak backups.
python3 "$SCRIPTS/wikilink_enricher.py" --vault "$VAULT" --apply
```

Then immediately recommend Phase 2 so the user sees the structural improvement.

## Phase 1B — LLM wikilink enrichment (agent-driven)

Catches synonyms and contextual references the mechanical pass cannot see. **No API key required.** Splits into prep + agent steps.

### Step 1: prep (Python, deterministic, no LLM)

```sh
python3 "$SCRIPTS/wikilink_enricher_llm_prep.py" \
  --vault "$VAULT" \
  --only-orphans \
  --max-files 30 \
  --max-suggestions-per-note 4
```

Writes `Reports/knowledge-graph/wikilink-llm-tasks-YYYY-MM-DD.md` containing the orphan files with content + the valid wikilink targets + the rules for proposing suggestions.

### Step 2: agent processes the task file

Read the task file you just generated. For each orphan file section:

1. Read the content shown.
2. Identify up to 4 spans of prose that are synonyms or contextual references for one of the listed valid targets.
3. Validate each span against the strict span rules in the task file (≤ 5 words, no markdown chars, dedupe per target).
4. Output suggestions to a review queue at `Reports/knowledge-graph/wikilink-llm-enrichment-review-YYYY-MM-DD.md`, grouped by source file.

When done, surface the suggestion count to the user. Ask them to skim the review queue. When they approve, apply the keepers as display-text wikilinks: `[[Target|original phrase]]`. Use the Edit tool against each source file with the exact span as `old_string` and the wrapped version as `new_string`. Create `.bak` backups before editing.

After applying, recommend Phase 2 again.

## Phase 2 — Graph + diagnostics

```sh
python3 "$SCRIPTS/vault_graph.py" \
  --vault "$VAULT" \
  --output "$VAULT/Reports/knowledge-graph/${TODAY}-graph-report.md" \
  --json
```

Reads every markdown file, builds an undirected weighted graph from `[[wikilinks]]`, runs:

- **Betweenness centrality** → the bridges
- **Degree** → the hubs
- **Louvain community detection** → the clusters
- **Six diagnostic detectors** (see `references/detector-catalog.md`)

Findings are emitted with severity, narrative, and recommendation each. Read the report back to the user. Emphasise the highest-severity finding. The JSON sidecar is the input to Phase 3 and 4.

## Phase 3 — Draft canonical notes (agent-driven)

Closes the loop. For each dangling reference, the agent reads the actual excerpts where it is referenced and drafts a short canonical note grounded in that real context.

### Step 1: prep (Python, deterministic, no LLM)

```sh
LATEST_JSON=$(ls -t "$VAULT/Reports/knowledge-graph/"*graph-report.json | head -1)

python3 "$SCRIPTS/note_drafter_prep.py" \
  --vault "$VAULT" \
  --graph-json "$LATEST_JSON" \
  --top-n 10 \
  --min-references 2
```

Writes `Reports/knowledge-graph/note-drafting-tasks-YYYY-MM-DD.md` with: business context, top-N dangling concepts, real excerpts per concept, related concepts per concept, suggested target locations, full drafting rules.

### Step 2: agent processes the task file

Read the task file. For each numbered concept section:

1. **Convention-drift check first.** Look for a file with a normalised version of the concept name (kebab-case, lowercase, etc.) anywhere in the vault. Use Glob or Bash `find`. If a canonical file already exists under a different naming convention, SKIP drafting. Note in the INDEX.md that the dangling reference should be fixed by updating the source wikilink to display-text form (e.g., `[[claims-decision-process|Claims Decision Process]]`), not by promoting a draft.
2. **If no normalised match exists**, draft the canonical note following the rules in the task file:
   - Frontmatter with `type`, 2+ `tags`, `status: draft`
   - `# {Concept Name}` heading
   - 2-4 short paragraphs, factual teammate voice
   - 2-5 wikilinks woven into prose from the related-concepts list
   - No em dashes
3. Save the draft to `drafts/YYYY-MM-DD/{Concept Name}.md`.
4. After all concepts processed, write `drafts/YYYY-MM-DD/INDEX.md` listing each draft with its suggested promotion target and a one-line summary of what each draft covers. For convention-drift skips, log the wikilink-fix recommendation instead of a draft path.

Report the count of drafted vs skipped concepts to the user. Recommend promotion review.

## Phase 4 — Bridge questions for cluster gaps (agent-driven)

For graphs with multiple healthy clusters where some pairs have no edges between them.

### Step 1: prep

```sh
python3 "$SCRIPTS/bridge_questions_prep.py" \
  --vault "$VAULT" \
  --graph-json "$LATEST_JSON"
```

Writes `Reports/knowledge-graph/bridge-question-tasks-YYYY-MM-DD.md` with business context, vault anchors, and each cluster-pair gap with its members.

### Step 2: agent processes

Read the task file. For each gap section:

1. Generate 2-3 sharp questions that reference specific concepts from BOTH clusters by name.
2. Each question must be answerable by writing one short note or doing one piece of research.
3. Skip generic phrasings like "how does X relate to Y".
4. Phrase as questions the operator would actually want answered.

Write the output to `Reports/knowledge-graph/bridge-questions-YYYY-MM-DD.md` as a markdown checklist grouped by gap. Each question is a `- [ ]` item the operator can copy into their task list.

A no-op for star-topology vaults. Productive once the vault has multiple healthy clusters.

## Phase 5 (audit engagements only) — Ingest external content

For a Strategic Knowledge Audit on a client's public website:

```sh
python3 "$SCRIPTS/ingest_site.py" \
  --start "https://client.example.com/" \
  --output "$VAULT/corpora/<client-slug>" \
  --max-depth 2 \
  --max-pages 100 \
  --site-name "Client Name"
```

Polite same-origin crawler with internal-link → wikilink conversion. Skips faceted-filter URLs, product detail pages, account flows. The resulting corpus drops into the vault for the rest of the loop to act on.

## Recurring cadence

Once a vault is enriched and producing useful drafts:

| Cadence | Action |
|---|---|
| Weekly | Phase 2 (graph + diagnostics). Track metrics over time. |
| Weekly or biweekly | Phase 3 (draft notes) for new dangling references. |
| Monthly | Phase 1B (LLM enricher) on newly-added orphan files. |
| Quarterly | Phase 4 (bridge questions) once the vault has healthy clusters. |

Schedule the recurring runs via `/os-operator`. See `references/workflow-recurring.md`.

## Cross-references to other skills

- `/os-setup` — bootstrap a fresh vault. Run BEFORE this skill.
- `/os-optimizer` — judgment-based 7-framework audit. Run F1 (CLAUDE.md), F3 (compression), F4 (context rot), F5 (memory), F6 (progressive disclosure), G7 (hygiene). F2 (Karpathy Wiki) overlaps with this skill on dead-link / orphan detection: this skill provides the deterministic graph metrics and bulk auto-fix, while F2 provides per-finding judgment and HTML reporting. Run both; they complement.
- `/os-operator` — schedules everything. Add Phase 2 + Phase 3 to its weekly cadence.
- `/assistant` — surfaces graph-report headlines in the morning review.
- `/vault-mcp` — provides remote read/write. No direct dependency.

## Output discipline

Do NOT inline the graph report, task files, or review queue contents in chat unless the user specifically asks. Always report:

1. One-sentence headline (highest severity finding or the key metric delta).
2. The saved path so the user can open the artifact in Obsidian.
3. A clear "next action" — which phase to run next, or what to review before moving on.

The artifacts are the deliverable; the chat is the navigator.

## Triggers and intent mapping

| User says | Run |
|---|---|
| "evolve my vault", "/os-evolver" | Phase 0 then routing decision |
| "graph my vault" | Phase 2 directly |
| "draft missing notes", "fill the gaps" | Phase 3 (Phase 2 first if no graph in 7+ days) |
| "enrich wikilinks", "link the vault" | Phase 1A, then Phase 1B if mechanical was applied |
| "bridge questions", "research questions" | Phase 4 directly |
| "ingest the client's site" or a URL | Phase 5 |
| "knowledge audit", "Strategic Knowledge Audit" | Full pipeline as a one-shot: Phase 5 (if URL) → 1A → 1B → 2 → 3 → 2 again. Show before/after metrics. |

## Verbatim hard rules

- Never write to a file in `.git/`, `.obsidian/`, `.trash/`, `corpora/<existing client>/`, or `node_modules/`.
- Never apply enrichment without first showing the review queue.
- Always check for normalised-name file collisions before promoting a draft. A convention-drift collision means the right fix is a wikilink update, not a new file.
- Always make `.bak` backups before mutating source files. The mechanical enricher does this automatically; for agent-driven edits in Phase 1B and 3, create `.bak` copies before using the Edit tool.
- Always re-graph after applying enrichment or promoting drafts. The user needs to see structural improvement.
- All LLM work runs through the agent (Claude Code subscription). Never reach for `ANTHROPIC_API_KEY` or the `anthropic` Python package.
