# Workflow: onboarding a fresh vault

Use this walkthrough when running `/os-evolver` on a vault for the first time. It assumes `/os-setup` has already bootstrapped the directory structure and `CLAUDE.md` is in place.

## When to use this workflow

- A newly-created vault with mostly empty or wikilink-sparse notes.
- A client engagement where you have ingested their public content via Phase 5 and need to enrich the resulting corpus.
- A long-existing vault that has never been graph-analysed before.

The recurring weekly cadence lives in `workflow-recurring.md` instead. That assumes the onboarding has already happened.

## Step 0: Reconnaissance

Always start with Phase 0 (SKILL.md). Surface the numbers, then route. The typical first-time onboarding has these signals:

| Signal | Implication |
|---|---|
| `density < 0.5` wikilinks per file | Vault is wikilink-sparse. Mechanical enricher is the next move. |
| No `Reports/knowledge-graph/` directory | Graph has never run. Create the directory; no historical data to compare against. |
| `FILES > 50` | Worth the full pipeline. Smaller and you can hand-link in less time than running this. |

Show the user the recon numbers in one paragraph, then propose Phase 1A.

## Step 1: Mechanical wikilink enrichment

Free, deterministic, idempotent. Run twice: once in review mode, once with `--apply`.

```sh
# Review pass.
python3 "${CLAUDE_PLUGIN_ROOT}/skills/os-evolver/scripts/wikilink_enricher.py" \
  --vault "$PWD"

# The review queue lands at:
#   Reports/knowledge-graph/wikilink-enrichment-review-YYYY-MM-DD.md
```

Tell the user to skim the review queue. The proposals are grouped by source file, each shows the candidate replacement in context. Quality is usually 85-95% — the noise is mostly common-word collisions and generic-titled files.

If the user finds noise patterns (e.g., a generic title like `Pagination` is getting linked everywhere), edit `NOISE_TITLES` in `scripts/wikilink_enricher.py` and re-run the review.

When the user is satisfied:

```sh
python3 "${CLAUDE_PLUGIN_ROOT}/skills/os-evolver/scripts/wikilink_enricher.py" \
  --vault "$PWD" \
  --apply
```

This injects every approved wikilink and creates `.bak` backups next to each modified file. Idempotent: a second run finds nothing because the matches are already inside `[[...]]`.

**Expected impact**: orphan rate typically drops from 80-90% to 50-65%. Disconnected components shrink by 50-70%. The vault gains its first real structure.

## Step 2: Graph + diagnostics (first run)

```sh
TODAY=$(date +%Y-%m-%d)
python3 "${CLAUDE_PLUGIN_ROOT}/skills/os-evolver/scripts/vault_graph.py" \
  --vault "$PWD" \
  --output "Reports/knowledge-graph/${TODAY}-graph-report.md" \
  --json
```

Read the report aloud (paraphrased) to the user. Lead with the highest-severity finding. Common findings after mechanical enrichment but before LLM enrichment:

- 🟠 HIGH `FRAGMENTED_GRAPH` — 50-65% of files still in their own components. Normal for wikilink-sparse vaults.
- 🟠 HIGH `STAR_TOPOLOGY` — usually fires because one central entity (like an operator name or a primary platform) is the only bridge.
- 🟡 MEDIUM `EMPTY_HUBS` — concepts referenced multiple times but no canonical file. These become Phase 3 drafts.

Tell the user this is the baseline. The metrics get better in the next steps.

## Step 3: LLM wikilink enrichment (synonyms and context, agent-driven)

Catches what the mechanical pass cannot: synonyms (`"the ERP"` → `[[STORIS]]`), partial names (`"Scott"` → `[[Scott — Goals & Priorities]]`), and contextual references. **No API key required** — the agent does the LLM work through the user's Claude Code subscription.

**Step 3a: prep (Python, deterministic, free)**

```sh
python3 "${CLAUDE_PLUGIN_ROOT}/skills/os-evolver/scripts/wikilink_enricher_llm_prep.py" \
  --vault "$PWD" \
  --only-orphans \
  --max-files 30 \
  --max-suggestions-per-note 4
```

Produces a task file at `Reports/knowledge-graph/wikilink-llm-tasks-YYYY-MM-DD.md` containing orphan files with their content + the valid wikilink targets + the span rules.

**Step 3b: agent processes the task file**

Read the task file. For each orphan file section, propose up to 4 wikilink injections, validate against the strict span rules (≤ 5 words, no markdown chars, dedupe per target). Write proposals to a review queue at `Reports/knowledge-graph/wikilink-llm-enrichment-review-YYYY-MM-DD.md`, grouped by source file.

Quality is typically 70-80% solid. Common patterns to watch for and discard:

- **Wrong targets**: a span that semantically matches multiple files; the agent picks the wrong one. These need a manual fix before applying.
- **Suboptimal targets**: the agent links a specific term to an index page because no dedicated page exists. Not wrong, one hop away from optimal.

When the user approves the keepers, apply the changes using the Edit tool on each source file. The applied form is **display-text wikilink**: `[[Target|original phrase]]`. The prose reads exactly the same as before; only navigation changes. Create `.bak` backups before mutating any file.

**Expected impact**: orphan rate drops another 5-15 percentage points. `STAR_TOPOLOGY` often resolves at this stage because linking gets distributed across multiple bridges.

## Step 4: Graph again, see the delta

```sh
python3 "${CLAUDE_PLUGIN_ROOT}/skills/os-evolver/scripts/vault_graph.py" \
  --vault "$PWD" \
  --output "Reports/knowledge-graph/${TODAY}-graph-report.md" \
  --json
```

Tell the user the before/after metrics in a table. Specific numbers, not adjectives:

| Metric | Before | After |
|---|---|---|
| Unique edges | X | Y (Z× more) |
| Orphan rate | A% | B% |
| Disconnected components | M | N |
| Critical findings | P | Q |

If a finding downgraded from CRITICAL → HIGH → MEDIUM, name it explicitly. The user wants to see severity dropping.

## Step 5: Draft notes for dangling references (agent-driven)

**Step 5a: prep (Python, deterministic, free)**

```sh
LATEST_JSON=$(ls -t Reports/knowledge-graph/*graph-report.json | head -1)

python3 "${CLAUDE_PLUGIN_ROOT}/skills/os-evolver/scripts/note_drafter_prep.py" \
  --vault "$PWD" \
  --graph-json "$LATEST_JSON" \
  --top-n 10 \
  --min-references 2
```

Produces a task file at `Reports/knowledge-graph/note-drafting-tasks-YYYY-MM-DD.md` with each dangling concept's real excerpts from the vault, related concepts, suggested target locations, and drafting rules.

**Step 5b: agent processes the task file**

Read the task file. For each numbered concept section:

1. **Convention-drift check first.** Search the vault for any file with a normalised version of the concept name. If `[[Claims Decision Process]]` is dangling but `claims-decision-process.md` already exists, the draft is REDUNDANT. The right fix is updating the source wikilink to display-text form (`[[claims-decision-process|Claims Decision Process]]`), not promoting a new draft. Log this in the INDEX.md as a wikilink-fix recommendation.
2. **Otherwise, draft the note** following the rules in the task file: frontmatter (type, 2+ tags, status: draft), H1 heading, 2-4 short paragraphs in teammate voice, 2-5 wikilinks woven into prose, no em dashes.
3. Save to `drafts/YYYY-MM-DD/{Concept Name}.md`.
4. Write `drafts/YYYY-MM-DD/INDEX.md` listing each draft and each convention-drift skip with its recommended fix.

Promote keepers manually. Edit voice and structure as needed.

## Step 6: Final graph + status

Re-run Phase 2 one more time. Confirm `dangling: 0` (or close to it). The vault is now onboarded. Hand the user the recurring cadence (see `workflow-recurring.md`).

## Total time and cost for onboarding

| Vault size | Wall clock | Anthropic API spend |
|---|---|---|
| 30-50 notes | 15-30 min | **$0** (runs on the user's Claude Code subscription) |
| 50-100 notes | 30-60 min | **$0** (uses subscription tokens, not API credits) |
| 100-200 notes | 60-90 min | **$0** (one auth surface only) |

The agent does the LLM work inside the user's existing Claude Code session. No separate `ANTHROPIC_API_KEY`, no per-token billing surface, no env var to configure.

The bulk of the time is human review of the two enrichment queues. The compute itself is fast.
