# Workflow: the recurring loop

After a vault is onboarded (see `workflow-onboarding.md`), the recurring weekly loop keeps it self-evolving. This document is the cadence playbook.

## The cadence at a glance

| Frequency | Action | Why |
|---|---|---|
| Weekly | Phase 2 (graph + diagnostics) | Track structural drift. Severity changes over time. |
| Weekly or biweekly | Phase 3 (draft notes) for new dangling references | Every new note added during the week introduces new references. Some will dangle. Draft them while context is fresh. |
| Monthly | Phase 1B (LLM enricher) on `--only-orphans --since=<30d>` | Pick up new notes added in the last 30 days. Cheap, mostly synonym additions. |
| Quarterly | Phase 4 (bridge questions) | Once the vault has multiple healthy clusters, cluster-gap questions become productive research direction. |
| Quarterly | Re-read the diagnostic catalog | Check whether the recommended interventions have moved the metrics. Adjust strategy if not. |

## Weekly Phase 2 run

```sh
TODAY=$(date +%Y-%m-%d)
python3 "${CLAUDE_PLUGIN_ROOT}/skills/bp-evolver/scripts/vault_graph.py" \
  --vault "$PWD" \
  --output "Reports/knowledge-graph/${TODAY}-graph-report.md" \
  --json
```

Compare against last week's report. The relevant deltas:

- **Orphan rate change.** Going down = good. Going up = new orphan notes were added; consider Phase 1B.
- **Dangling-ref count change.** Going up = new concepts being referenced without canonicalisation. Run Phase 3 to fill.
- **Finding severity change.** A finding downgrading (e.g. CRITICAL → HIGH) is a real win. Surface it in the user's morning review.
- **New findings.** Unusual. Investigate. Usually means a big restructuring happened.

The recommended report-back format to the user is a one-paragraph weekly snapshot:

> Vault snapshot 2026-MM-DD: 84 notes (+6), 142 edges (+18), 38% orphan rate (down from 41%), 3 dangling references (up from 1), 2 medium findings. The new dangling refs are [[X]], [[Y]], [[Z]] — recommend running Phase 3 this week.

## Weekly Phase 3 run (agent-driven)

If the latest graph report has `dangling_count > 0`:

```sh
LATEST_JSON=$(ls -t Reports/knowledge-graph/*graph-report.json | head -1)

python3 "${CLAUDE_PLUGIN_ROOT}/skills/bp-evolver/scripts/note_drafter_prep.py" \
  --vault "$PWD" \
  --graph-json "$LATEST_JSON" \
  --top-n 5
```

Then the agent reads the task file at `Reports/knowledge-graph/note-drafting-tasks-YYYY-MM-DD.md` and drafts each note using the user's Claude Code subscription, saving outputs to `drafts/YYYY-MM-DD/`. A weekly run typically produces 2-5 drafts. The user spends 10-15 minutes reviewing, promoting keepers, discarding redundants. No API key needed.

## Monthly LLM enricher refresh (agent-driven)

Once a month, run the LLM enricher on any notes added or substantially edited in the last 30 days.

```sh
python3 "${CLAUDE_PLUGIN_ROOT}/skills/bp-evolver/scripts/wikilink_enricher_llm_prep.py" \
  --vault "$PWD" \
  --only-orphans \
  --max-files 30
```

Agent reads the produced task file, generates a review queue at `Reports/knowledge-graph/wikilink-llm-enrichment-review-YYYY-MM-DD.md`. Operator reviews, approves, agent applies wikilinks via the Edit tool with `.bak` backups. No API key needed.

## Quarterly bridge-questions run (agent-driven)

```sh
LATEST_JSON=$(ls -t Reports/knowledge-graph/*graph-report.json | head -1)

python3 "${CLAUDE_PLUGIN_ROOT}/skills/bp-evolver/scripts/bridge_questions_prep.py" \
  --vault "$PWD" \
  --graph-json "$LATEST_JSON"
```

Agent reads the task file at `Reports/knowledge-graph/bridge-question-tasks-YYYY-MM-DD.md`, generates 2-3 questions per cluster gap, writes the output to `Reports/knowledge-graph/bridge-questions-YYYY-MM-DD.md` as a markdown checklist. Treat each question as a candidate research note. Answer in a new wiki page, link the page to both clusters, then re-graph.

Highest-leverage research-direction generator the system produces. Productive once the vault has 4+ healthy clusters.

## Automating the cadence via `/bp-operator`

Hand off the recurring runs to the operator agent. When setting up the operator, add a `Weekly Vault Graph` schedule with the body:

```
Run /bp-evolver. Recon, then route to Phase 2 by default. If the latest graph
report shows dangling references and the operator has Anthropic credits, run
Phase 3 as well. Append the weekly snapshot paragraph to Daily/YYYY-MM-DD.md
under a 'Vault graph' heading.
```

The operator's idempotence guarantees mean the run is safe to schedule weekly even if no changes have happened in the vault — it will just produce a graph report identical to the previous week's.

## Surfacing in the morning routine

The `/assistant` skill's morning review can include a one-line vault-graph status:

> Vault: 142 edges (+18 this week), 38% orphan rate (-3pp), 3 dangling references to address.

Wire this by adding a line to the assistant's daily-review template that reads the latest `Reports/knowledge-graph/*-graph-report.json` and emits the deltas.

## When to stop the recurring loop

Some vaults reach steady state and the recurring runs produce no useful output. Indicators:

- Orphan rate plateaus below 35% and stops decreasing for 3+ runs.
- Dangling references stay at 0 or 1 for multiple weeks.
- Diagnostic findings are all MEDIUM or below for 4+ weeks.

At that point, drop to a monthly Phase 2 (just to catch regressions) and pause Phase 3 until new dangling references appear. The system is doing its job.

## When to re-run onboarding

If you add a large batch of external content in one go (e.g., ingest a new website via Phase 5, or import a folder of pre-existing markdown), re-run the full onboarding workflow (Phase 1A + 1B) on the new files. Then graph and continue the recurring loop.
