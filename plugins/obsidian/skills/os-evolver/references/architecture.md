# Architecture and core thesis

The `/os-evolver` skill implements the Karpathy LLM Wiki idea with the Nodus Labs Portable GraphRAG enhancement on top. Both ideas land in markdown, where Obsidian already maintains the substrate. This document explains the *why* behind the pipeline so the agent can reason about edge cases rather than mechanically running steps.

## The core thesis

A markdown knowledge base is an LLM's external brain. RAG lets the LLM retrieve from it, but the LLM cannot see the *shape* of the brain. A knowledge graph layer exposes:

1. **Central concepts** via betweenness centrality. The bridges between clusters. The load-bearing ideas.
2. **Clusters** via community detection. The natural topics the corpus has organised itself into.
3. **Structural holes** between clusters. The gaps that, if bridged, would make the brain more coherent.

The LLM uses gap-detection to generate research questions and to draft canonical notes. It writes those back into the vault. The vault re-graphs and exposes the next layer of gaps. The brain self-improves over time. **That is the loop.**

## Why this complements `/os-optimizer`

`/os-optimizer` runs seven judgment-based frameworks. Its F2 (Karpathy LLM Wiki) catches per-finding issues — a dead wikilink here, an orphan there, a stub note somewhere. Excellent for spot-checks.

`/os-evolver` runs deterministic measurement plus deterministic and LLM-based bulk action. It does not produce per-finding judgment — it produces:

- Quantitative graph metrics that change measurably across runs
- Bulk auto-injection of wikilinks across the entire vault in a single pass
- Auto-drafted canonical notes for every dangling concept

The two skills answer different questions:

| Question | Skill |
|---|---|
| "What specific issues exist in this file?" | `/os-optimizer` |
| "What is the structural shape of the vault right now, and how do I close the biggest gap fastest?" | `/os-evolver` |

Run both. They are complementary, not redundant.

## The closed loop, end to end

```
                                     ┌─ Phase 1A (mechanical) ──┐
                                     │                          │
                                     ▼                          │
A vault with markdown notes ──► [enricher pass] ──► wikilinks woven into prose
                                     │
                                     ▼
                                  Phase 1B (LLM, synonym-aware)
                                     │
                                     ▼
                          [vault_graph.py] ──► graph + diagnostics
                                     │
                                     ▼
                          dangling refs + cluster gaps
                                     │
                  ┌──────────────────┴──────────────────┐
                  ▼                                     ▼
            [note_drafter.py]                  [bridge_questions.py]
                  │                                     │
                  ▼                                     ▼
            drafted notes                     research questions
                  │                                     │
                  ▼                                     ▼
        operator reviews and promotes      operator answers as new notes
                  │                                     │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                          re-run vault_graph.py
                                     │
                                     ▼
                          new gaps surface ──► loop
```

This is the diagram the agent should hold in its head when explaining the skill to a user.

## Source ideas

- **Karpathy LLM Wiki (April 2026)** — the LLM owns the wiki, the human owns the schema, the wiki is a structured cross-linked markdown brain. Lint, ingest, query are the three operations. The schema (CLAUDE.md) tells the LLM how the vault is organised.
- **Nodus Labs Portable GraphRAG (2024)** — knowledge graph metrics (betweenness, communities, structural holes) applied to a markdown corpus reveal what RAG alone hides. Bridging questions generated from cluster gaps drive the self-evolution.
- **Practitioner extensions** — the six diagnostic detectors (star topology, fragmentation, high orphan rate, hub dependence, siloed content themes, empty hubs) come from running this on real client vaults and noticing the recurring failure modes that judgment-based linting misses.

## Three failure modes the engine consistently surfaces on real vaults

1. **Star topology.** One node (usually the homepage on a website mirror, or the operator's daily/profile note in a personal vault) is the only bridge in the entire graph. Removing it fractures the corpus into hundreds of islands. Fix: lateral linking between sibling pages.
2. **Hub dependence.** A single concept (a core entity like a primary tool or platform) touches more than half of every internal link. The vault depends on it for navigation. Fix: distribute linking so sibling concepts cross-reference each other.
3. **Siloed content themes.** Editorial or blog content (long buying-guide titles, "How to X", "Why Y", "X vs Y") appears as dangling references but the catalog never links to it. The content investment is stranded. Fix: pair each editorial piece with the catalog page it supports.

The skill's diagnostic catalog (see `detector-catalog.md`) catches all three automatically.

## Two ceilings the engine cannot break alone

1. **Truly standalone notes.** Daily journals, one-off scratch notes that legitimately don't reference any other concept. They will always be orphans. Don't try to fix; archive what is stale.
2. **Convention drift.** If the vault uses kebab-case file names but operators write title-case wikilinks (`[[Claims Decision Process]]` referencing `claims-decision-process.md`), Obsidian treats them as different files and they show as dangling. The fix is wikilink normalisation, not new drafts. Always check for normalised-name file collisions before promoting a draft.

The agent should be aware of both ceilings so it does not over-promise on the orphan-rate drop.
