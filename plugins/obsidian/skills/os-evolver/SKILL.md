---
name: os-evolver
description: Karpathy + Nodus self-evolving research loop for any markdown vault. Runs deterministic graph analysis (betweenness centrality, Louvain communities, structural-hole detection), surfaces failure-mode diagnostics (star topology, fragmentation, high orphan rate, hub dependence, siloed content, empty hubs), bulk-injects [[wikilinks]] across the vault (mechanical and LLM-based), and uses Claude to draft canonical notes for dangling references. Closes the loop, so the vault literally fills its own gaps and gets structurally healthier on each pass. Outputs persist inside the vault under `Reports/knowledge-graph/` and `drafts/` for review. TRIGGERS: os evolver, evolve my vault, graph my vault, graph my knowledge, knowledge graph audit, strategic knowledge audit, self-evolving wiki, wikilink enrich, fill dangling notes, draft missing notes, bridge questions. Run from the vault root.
---

# OS Evolver

The closed self-evolving loop for a Karpathy-style LLM Wiki, with deterministic graph metrics on top.

## What this is

Where `/os-optimizer` runs a judgment-based 7-framework audit and produces an HTML dashboard of findings, `/os-evolver` runs a deterministic pipeline that *measures the shape* of the vault, then *acts* on it: bulk-enriches wikilinks across every note, drafts new canonical notes for dangling references, and re-measures to confirm structural improvement.

Five scripts ship inside the skill. The SKILL.md routes between them based on the vault's current state.

## Pre-flight Check

1. The current working directory MUST be a vault root. Verify a file named `CLAUDE.md` or `claude.md` exists in cwd. If missing: tell the user *"This is not a vault root. `cd` into your vault and re-run."* Stop.
2. Read the `os-mode` field in the vault's root `CLAUDE.md` frontmatter to detect mode (`professional` or `business`). Output routing is identical for graph purposes; only narrative framing changes.
3. Verify Python 3.10+ is available: `python3 --version`. If absent, ask the user to install Python.
4. Install / verify dependencies once per machine: `python3 -m pip install --user -r "${CLAUDE_PLUGIN_ROOT}/skills/os-evolver/scripts/requirements.txt"`. The requirements are `networkx`, `anthropic`, `requests`, `beautifulsoup4`, `markdownify`. Run quietly; do not report success unless there were errors.
5. For phases that need Claude (LLM enricher, note drafter, bridge questions): check `$ANTHROPIC_API_KEY`. If absent, tell the user to either export it or `echo 'sk-ant-...' > ~/.anthropic_key && chmod 600 ~/.anthropic_key`, then this skill will read it via `$(cat ~/.anthropic_key)`.

## Path conventions

- **Scripts** live at `${CLAUDE_PLUGIN_ROOT}/skills/os-evolver/scripts/`. Invoke them with absolute paths.
- **Reference files** (`references/foo.md`) live next to **this SKILL.md** — read them with absolute paths relative to the SKILL.md location.
- **Vault outputs** land under the user's cwd:
  - Graph reports: `Reports/knowledge-graph/YYYY-MM-DD-graph-report.{md,json}`
  - LLM enrichment review queue: `Reports/knowledge-graph/wikilink-llm-enrichment-review-YYYY-MM-DD.md`
  - Mechanical enrichment review queue: `Reports/knowledge-graph/wikilink-enrichment-review-YYYY-MM-DD.md`
  - Drafted notes: `drafts/YYYY-MM-DD/` plus an `INDEX.md`
  - Bridge questions: `Reports/knowledge-graph/YYYY-MM-DD-bridge-questions.md`
  - External content corpora (audit engagements only): `corpora/<slug>/`

Create these directories on first run; do not ask permission.

If a `references/...` read fails, locate the references directory once with `find / -type d -path '*/os-evolver/references' 2>/dev/null | head -1` and reuse the absolute path. Do not retry per-file.

## Phase 0 — Reconnaissance (always run first)

Survey the vault before deciding what to do.

```sh
VAULT="$PWD"
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/os-evolver/scripts"
TODAY=$(date +%Y-%m-%d)

# Count markdown files (excluding scaffolding)
FILES=$(find "$VAULT" -name "*.md" \
  ! -path "*/.obsidian/*" ! -path "*/.trash/*" ! -path "*/.git/*" \
  ! -path "*/corpora/*" ! -path "*/Reports/*" ! -path "*/reports/*" \
  ! -path "*/drafts/*" ! -path "*/output/*" \
  ! -name "CLAUDE.md" ! -name "GEMINI.md" ! -name "AGENTS.md" | wc -l | tr -d ' ')

# Count wikilinks (a proxy for current network density)
WIKILINKS=$(grep -rhoE '\[\[[^\]]+\]\]' "$VAULT" --include="*.md" 2>/dev/null \
  | grep -v "^\[\[CLAUDE" | wc -l | tr -d ' ')

# Latest graph report (if any)
LATEST_REPORT=$(ls -t "$VAULT/Reports/knowledge-graph/"*graph-report.json 2>/dev/null | head -1)
```

Compute:
- `density = WIKILINKS / FILES` (0.0 if FILES is 0)
- If `LATEST_REPORT` exists, parse its `dangling`, `orphan_count`, `findings` fields for the latest-known state
- `days_since_graph` = age of `LATEST_REPORT` in days, or `Inf`

Tell the user, in one paragraph, what you found. Numbers, not adjectives.

## Phase routing decision

Apply this decision tree. Pick the FIRST matching phase. Do not run multiple phases without asking.

| Condition | Phase | Why |
|---|---|---|
| `FILES < 10` | Stop and explain | The vault is too small for graph analysis to be informative. Suggest the user write more notes first. |
| `density < 0.5` and no recent enrichment review | **Phase 1A — mechanical enrich** | Vault is wikilink-sparse. Start with the free, deterministic title-match pass. |
| `density < 1.5` and `Phase 1A applied` and no LLM enrichment yet | **Phase 1B — LLM enrich** | Catch synonyms and contextual refs the mechanical pass missed. Costs ~$0.40 per 30 files on Sonnet. |
| `days_since_graph > 7` or no graph at all | **Phase 2 — graph + diagnostics** | Surface failure modes (star topology, fragmentation, hub dependence, siloed content, empty hubs). |
| `dangling_count > 0` from latest report | **Phase 3 — draft notes** | Use Claude to fill canonical notes for the dangling references. |
| Vault is healthy | **Status report** | Read the latest graph report, summarise current state, suggest the cadence. |
| User explicitly asked for a specific phase | Run that phase | Override the decision tree. |

Confirm the chosen phase with the user before running anything that writes to the vault. Use `AskUserQuestion` if more than one phase could apply.

## Phase 1A — Mechanical wikilink enrichment

Run the deterministic title-matcher. Free. No API key needed.

```sh
# Step 1: review (writes a queue, modifies nothing).
python3 "$SCRIPTS/wikilink_enricher.py" \
  --vault "$VAULT" \
  --max-per-note 20

# Step 2 (after the user has skimmed the queue): apply.
python3 "$SCRIPTS/wikilink_enricher.py" \
  --vault "$VAULT" \
  --apply
```

Tell the user where the review queue landed, ask them to skim it. Each modified file gets a `.bak` backup next to it.

After `--apply`, immediately recommend Phase 2 so they see the structural improvement.

See `references/workflow-onboarding.md` for the full onboarding walkthrough.

## Phase 1B — LLM wikilink enrichment

Catches synonyms (`"the ERP"` → `[[STORIS]]`), partial names (`"Scott"` → `[[Scott — Goals & Priorities]]`), and contextual references the mechanical pass cannot see. Uses Claude. Approximately $0.015 per file processed on Sonnet.

```sh
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-$(cat ~/.anthropic_key 2>/dev/null)}"

# Default: only process orphan files (highest leverage, lowest cost).
python3 "$SCRIPTS/wikilink_enricher_llm.py" \
  --vault "$VAULT" \
  --only-orphans \
  --max-files 50
```

Always run in review mode first; show the user the suggestion count and hit-rate hint from the script's stderr (`raw=N kept=M dropped=K (reasons)` per file). When they say go, repeat with `--apply`.

The applied form is the **display-text wikilink**: `[[Target Title|original phrase]]`. The prose stays readable; the link resolves to the target. Backups at `.bak` next to each modified file.

If the suggestion count is low or quality looks weak, relax the prompt by editing `scripts/wikilink_enricher_llm.py` (the 5-word-span rule and the markdown-character blocklist are the main levers).

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
- **Six diagnostic detectors** (see `references/detector-catalog.md`):
  - `STAR_TOPOLOGY` (single node carries the graph)
  - `FRAGMENTED_GRAPH` (many disconnected components)
  - `HIGH_ORPHAN_RATE` (>40% of files orphaned)
  - `HUB_DEPENDENCE` (one hub touches >50% of edges)
  - `SILOED_CONTENT_THEMES` (blog-style danglings)
  - `EMPTY_HUBS` (heavily-referenced concepts with no canonical file)

Findings are emitted with severity, narrative, and a one-line recommendation each. Read the report back to the user. Emphasise the highest-severity finding and its recommended action. The JSON sidecar is the input to Phase 3.

## Phase 3 — Draft canonical notes

Closes the loop. For each dangling reference (a concept cited but with no file), Claude reads the actual excerpts where it is referenced in the vault and drafts a short canonical note grounded in that real context.

```sh
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-$(cat ~/.anthropic_key 2>/dev/null)}"
LATEST_JSON=$(ls -t "$VAULT/Reports/knowledge-graph/"*graph-report.json | head -1)

python3 "$SCRIPTS/note_drafter.py" \
  --vault "$VAULT" \
  --graph-json "$LATEST_JSON" \
  --output-dir "$VAULT/drafts/${TODAY}" \
  --top-n 10 \
  --min-references 2
```

Each drafted note lands in `drafts/YYYY-MM-DD/`. An `INDEX.md` lists every draft with a suggested promotion target. The user reviews, edits, then moves each draft to its canonical home in the vault. Re-run Phase 2 afterwards to confirm the dangling reference is gone and the graph has gained edges.

**Important note on promotion**: if the operator already has a canonical file under a different naming convention (kebab-case vs title-case, etc.), the draft is REDUNDANT. The right fix in that case is to update the referencing wikilink to display-text form (e.g. `[[claims-decision-process|Claims Decision Process]]`), not promote the draft. Always check for normalised-name file collisions before promoting.

## Phase 4 (optional) — Bridge questions for cluster gaps

When the graph reveals two clusters with no edges between them, Claude can generate sharp research questions that would force a useful connection.

```sh
python3 "$SCRIPTS/bridge_questions.py" \
  --graph-json "$LATEST_JSON" \
  --vault "$VAULT" \
  --output "$VAULT/Reports/knowledge-graph/${TODAY}-bridge-questions.md"
```

A no-op for star-topology vaults (no cluster pairs to bridge). Productive once the vault has multiple healthy clusters.

## Phase 5 (audit engagements only) — Ingest external content

For a Strategic Knowledge Audit engagement on a client's public website, prepopulate their vault with a wikilink-rich corpus of their content:

```sh
python3 "$SCRIPTS/ingest_site.py" \
  --start "https://client.example.com/" \
  --output "$VAULT/corpora/<client-slug>" \
  --max-depth 2 \
  --max-pages 100 \
  --site-name "Client Name"
```

Polite same-origin crawler. Skips faceted-filter URLs, product detail pages, account/checkout flows. Converts each page to markdown with internal anchors preserved as Obsidian `[[wikilinks]]`. Result is a structured catalog mirror you can then run the rest of the loop against.

## The recurring cadence

Once a vault is enriched and producing useful drafts, the recurring loop is:

| Cadence | Action |
|---|---|
| Weekly | Phase 2 (graph + diagnostics). Track orphan rate, dangling-ref count, finding severity over time. |
| Weekly or biweekly | Phase 3 (draft notes) for any new dangling references. |
| Monthly | Phase 1B (LLM enricher) on any newly-added notes that haven't been enriched. |
| Quarterly | Re-read the diagnostic catalog. Decide whether the recommended interventions have moved the metrics. |

Schedule the recurring runs via `/os-operator`. See `references/workflow-recurring.md`.

## Cross-references to other skills

- `/os-setup` — bootstrap a fresh vault. Run BEFORE this skill.
- `/os-optimizer` — judgment-based 7-framework audit. Run F1 (CLAUDE.md), F3 (compression), F4 (context rot), F5 (memory), F6 (progressive disclosure), G7 (hygiene). F2 (Karpathy Wiki) overlaps with this skill on dead-link / orphan detection: this skill gives you the deterministic graph metrics and bulk auto-fix, while F2 gives you per-finding judgment and HTML reporting. Run both; they complement.
- `/os-operator` — schedules everything. Add Phase 2 + Phase 3 to its weekly cadence.
- `/assistant` — surfaces graph-report headlines in the morning review.
- `/vault-mcp` — provides remote read/write. No direct dependency.

## Output discipline

Do NOT inline the graph report or the review queue contents in chat unless the user specifically asks. Always report:

1. One-sentence headline (highest severity finding or the key metric delta).
2. The saved path so the user can open the artifact in Obsidian.
3. A clear "next action" — which phase to run next, or what to review before moving on.

Bias for terse output. The artifacts are the deliverable; the chat is the navigator.

## Triggers and intent mapping

| User says | Run |
|---|---|
| "evolve my vault", "/os-evolver" | Phase 0 reconnaissance, then routing decision |
| "graph my vault", "graph my knowledge" | Phase 2 directly |
| "draft missing notes", "fill the gaps" | Phase 3 directly (Phase 2 first if no graph in 7+ days) |
| "enrich wikilinks", "link the vault" | Phase 1A, then Phase 1B if mechanical was applied |
| "bridge questions", "research questions" | Phase 4 directly |
| "ingest the client's site" or names a URL | Phase 5 |
| "knowledge audit", "Strategic Knowledge Audit" | The full pipeline as a one-shot engagement: Phase 5 (if URL given) → 1A → 1B → 2 → 3 → 2 again. Show before/after metrics. |

## Verbatim hard rules

- Never write to a file in `.git/`, `.obsidian/`, `.trash/`, `corpora/<existing client>/`, or `node_modules/`.
- Never apply enrichment without first showing the review queue.
- Never run Phase 1B, 3, or 4 without checking for `ANTHROPIC_API_KEY` first.
- Always make `.bak` backups before mutating files. The scripts handle this; verify.
- Always re-graph after applying enrichment or promoting drafts. The user needs to see structural improvement.
- Never silently drop suggestions in `--apply` mode. The post-filter logs `raw / kept / dropped (reasons)` per file. Surface that count in the report.
