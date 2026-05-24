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

## Step 3: LLM wikilink enrichment (synonyms and context)

Catches what the mechanical pass cannot: synonyms (`"the ERP"` → `[[STORIS]]`), partial names (`"Scott"` → `[[Scott — Goals & Priorities]]`), and contextual references.

Pre-flight: confirm `ANTHROPIC_API_KEY` is set. If not, walk the user through creating one at `console.anthropic.com → API Keys` and either exporting it or saving it to `~/.anthropic_key` with `chmod 600`.

```sh
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-$(cat ~/.anthropic_key 2>/dev/null)}"

# Review mode (default). Cost: roughly $0.015 per orphan file.
python3 "${CLAUDE_PLUGIN_ROOT}/skills/os-evolver/scripts/wikilink_enricher_llm.py" \
  --vault "$PWD" \
  --only-orphans \
  --max-files 50
```

The script's stderr shows per-file `raw=N kept=M dropped=K (reasons)` so the user can see whether the post-filter is over- or under-aggressive.

Quality is typically 70-80% solid. Read the review queue, look for patterns of bad suggestions:

- **Over-broad spans**: Claude wrapped a whole sentence. Already filtered out by the 5-word post-filter, but check for leftovers.
- **Wrong targets**: Claude linked `"CDF systems"` to `[[CDF Smart System]]` when the prose meant `[[Capital Discount Furniture]]`. These need to be edited manually before applying.
- **Suboptimal targets**: Claude linked `"Traefik"` to `[[actual-tech-stack]]` (the parent index) because no Traefik.md exists. Not wrong, just one hop away from optimal.

When the user is satisfied, apply:

```sh
python3 "${CLAUDE_PLUGIN_ROOT}/skills/os-evolver/scripts/wikilink_enricher_llm.py" \
  --vault "$PWD" \
  --only-orphans \
  --apply
```

The applied form is **display-text wikilink**: `[[Target|original phrase]]`. The prose reads exactly the same as before; only navigation changes. Backups at `.bak`.

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

## Step 5: Draft notes for dangling references

```sh
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-$(cat ~/.anthropic_key 2>/dev/null)}"
LATEST_JSON=$(ls -t Reports/knowledge-graph/*graph-report.json | head -1)

python3 "${CLAUDE_PLUGIN_ROOT}/skills/os-evolver/scripts/note_drafter.py" \
  --vault "$PWD" \
  --graph-json "$LATEST_JSON" \
  --output-dir "drafts/${TODAY}" \
  --top-n 10 \
  --min-references 2
```

Each draft is a short canonical note grounded in the actual excerpts where the concept is referenced in the vault. The `INDEX.md` lists every draft with a suggested promotion target.

**Critical check before promoting**: search the vault for a file with the same name under different casing or slug. If `[[Claims Decision Process]]` is dangling but `claims-decision-process.md` already exists, the draft is REDUNDANT. The right fix is to update the source wikilink to display-text form (`[[claims-decision-process|Claims Decision Process]]`), not promote the draft. Always check first.

Promote keepers manually. Discard redundant drafts. Edit voice and structure as needed.

## Step 6: Final graph + status

Re-run Phase 2 one more time. Confirm `dangling: 0` (or close to it). The vault is now onboarded. Hand the user the recurring cadence (see `workflow-recurring.md`).

## Total time and cost for onboarding

| Vault size | Wall clock | Anthropic spend |
|---|---|---|
| 30-50 notes | 15-30 min | $0.30-$0.80 |
| 50-100 notes | 30-60 min | $0.80-$1.50 |
| 100-200 notes | 60-90 min | $1.50-$3.00 |

The bulk of the time is human review of the two enrichment queues. The compute itself is fast.
