# Detector catalog

Six diagnostic detectors run inside `scripts/detectors.py`. Each scans the graph and the analysis result, emitting findings with severity, narrative, and a recommendation. This document is the canonical reference: what fires, when, and what to do about it.

Use this when interpreting a graph report for a user. Read the finding, then read the relevant section here so the recommendation is grounded.

## Severity levels

| Badge | Meaning |
|---|---|
| 🔴 CRITICAL | Catastrophic structural failure. Fix this first; nothing else will help. |
| 🟠 HIGH | Major structural issue. Fix soon; degrades search authority, discoverability, AI ingestion. |
| 🟡 MEDIUM | Real issue but not blocking. Schedule a fix in the next cadence cycle. |
| 🔵 LOW | Minor. Acknowledge in the report. |
| ℹ️ INFO | Informational. No action required. |

## 1. `STAR_TOPOLOGY`

**Fires when:** the top node by betweenness centrality has score ≥ 0.85 and the main connected component has ≥ 5 nodes.

**Severity ramp:** HIGH if 0.85–0.94, CRITICAL if ≥ 0.95.

**What it means:** A single node is the only bridge in the graph. Remove it and the corpus fractures into many islands. Every page depends on this single hub for discoverability, SEO link equity, and AI navigation.

**Typical examples:**
- A website with a homepage and category pages but no lateral cross-linking. The homepage is the sole bridge.
- A personal knowledge base where every note links back to a single daily index but never to sibling notes.

**Recommended fix:** Add lateral links between related pages. On retail sites this means a Related Categories module between sibling collections. In knowledge bases this means cross-references between related topics. This is typically the single biggest internal-linking lever available.

**How `/os-evolver` resolves it:** Phase 1A (mechanical enricher) usually does not resolve it because it only matches exact titles. Phase 1B (LLM enricher with `--only-orphans`) typically does, because it adds synonym-aware links that spread bridging across multiple nodes.

## 2. `FRAGMENTED_GRAPH`

**Fires when:** `component_count / file_count ≥ 0.5` and `file_count ≥ 10`.

**Severity ramp:** HIGH if 0.5–0.79, CRITICAL if ≥ 0.8.

**What it means:** A healthy corpus has one or a few large components. This vault has so many components that most content exists in tiny isolated islands. Search authority and human discovery cannot flow between regions.

**Typical examples:**
- Newly-ingested website content where each page only links to the homepage.
- A blog where every post is standalone with no cross-references.
- A team wiki where each subject-matter expert owns a folder but no one links across folders.

**Recommended fix:** Establish hub-and-spoke topology at minimum: every leaf links back to a category hub, every hub lists its leaves. Then add lateral links between sibling leaves.

**How `/os-evolver` resolves it:** Phase 1A + 1B together typically halve the component count. Phase 3 (note_drafter) adds new connector notes that further reduce fragmentation. Re-run Phase 2 to confirm.

## 3. `HIGH_ORPHAN_RATE`

**Fires when:** `orphan_count / file_count ≥ 0.4` and `file_count ≥ 20`. An orphan is a file with no inbound or outbound wikilinks.

**Severity ramp:** MEDIUM if 0.4–0.54, HIGH if 0.55–0.69, CRITICAL if ≥ 0.7.

**What it means:** Many files exist in the vault but are not woven into any topical cluster. Either the content is stale and should be archived, or it is valuable but the rest of the corpus fails to reference it.

**Typical examples:**
- Fresh ingest of an existing markdown folder with no internal linking convention.
- Operator's daily notes that legitimately don't reference any other concept (these will stay orphan; that is fine).
- "I'll write this later" stub notes that never got woven in.

**Recommended fix:** Audit each orphan. Archive what is stale. Weave the rest into existing topical clusters by adding cross-links from the orphan to related concepts and from existing notes to the orphan. For a retail catalog this means category cross-links. For a knowledge base it means linking each note to its parent topic.

**How `/os-evolver` resolves it:** Phase 1A + 1B both target orphans (Phase 1B has `--only-orphans` as default). After enrichment, the remaining orphans are usually genuinely standalone (daily notes, scratch notes) and should be left alone or archived.

**Inline evidence:** The finding lists the first 6 orphan filenames in the report body for at-a-glance triage.

## 4. `HUB_DEPENDENCE`

**Fires when:** the top hub by degree participates in ≥ 50% of all internal edges, and `file_count ≥ 20`.

**Severity ramp:** MEDIUM if 0.5–0.69, HIGH if ≥ 0.7.

**What it means:** A single concept touches more than half of every internal link. The corpus relies on it for navigation, which collapses if that page is removed, renamed, or deprioritised.

**Typical examples:**
- An enterprise vault where every note links to the company's primary platform (e.g., STORIS at a furniture retailer, Salesforce at a B2B SaaS).
- A personal vault where every project page links back to the operator's profile.

**Recommended fix:** Distribute linking responsibility. Sibling pages should link directly to each other rather than routing every visitor and every search crawler through the hub.

**How `/os-evolver` resolves it:** Phase 1B's synonym-aware enrichment spreads linking across multiple concepts (e.g., it will add links to `[[Supabase]]`, `[[Podium API]]`, `[[Renew]]` instead of routing everything through `[[STORIS]]`). This usually pulls the hub's edge share from 60-80% down to 40-55%, which clears the threshold.

## 5. `SILOED_CONTENT_THEMES`

**Fires when:** 3 or more dangling references look like editorial / buying-guide titles. The detector matches against title patterns: "how to", "why", "when should", "vs", "choosing", "best", "guide", "tips", "must have", "compared", "ideas", and "N must / ways / things / reasons" patterns.

**Severity ramp:** MEDIUM if 3-7 matches, HIGH if ≥ 8.

**What it means:** Editorial or blog content lives in a separate silo that the catalog or main content never links to. The content investment is stranded. This is the single most common conversion-rate failure on small business marketing sites.

**Typical examples:**
- A retailer with great buying guides ("How to Choose the Perfect Sofa") but no link from product category pages to those guides.
- A SaaS site with detailed feature comparisons that never get linked from the homepage or pricing page.

**Recommended fix:** Pair each editorial piece with the catalog (or feature, or pricing) page it supports. Every blog post gets a "Shop the article" or "See the related feature" section. Every catalog page embeds 1-2 relevant buying guides.

**How `/os-evolver` resolves it:** This is mostly a human / SEO-strategy fix, not a wikilink fix. The detector surfaces it for human attention. The finding lists the candidate titles inline for quick action.

## 6. `EMPTY_HUBS`

**Fires when:** at least one dangling reference is cited 3+ times in the vault (i.e., highly referenced but no canonical file exists).

**Severity ramp:** MEDIUM if top empty hub has degree 3-7, HIGH if ≥ 8.

**What it means:** These concepts are referenced repeatedly across the corpus but no file with the matching name exists. In a knowledge base this is content the operator has gestured at without canonising. On a website it is often a category label that should be a real landing page but is currently just an unresolved link.

**Typical examples:**
- A personal vault where `[[Anthropic]]` is referenced 8 times but no `Anthropic.md` exists.
- A client vault where `[[Renew Staging & Design]]` is referenced as a service line but the service has no detail page.

**Recommended fix:** Write the canonical note for each empty hub, ordered by reference count. The act of giving a referenced concept its own page usually surfaces structure already implicit in the references.

**How `/os-evolver` resolves it:** Phase 3 (`note_drafter_prep.py` + agent) drafts a canonical note for each empty hub grounded in the actual excerpts where it is referenced. The agent uses the user's Claude Code subscription, no separate API key. Drafts land in `drafts/YYYY-MM-DD/` with an INDEX. The operator reviews, promotes keepers.

**Caveat — convention drift**: An "empty hub" detection may actually be a casing mismatch where a canonical file already exists under a different name (e.g., `[[Claims Decision Process]]` is dangling but `claims-decision-process.md` exists). Always check for normalised-name file collisions before promoting a draft. The right fix in that case is to update the source wikilink to display-text form, not promote the draft.

**Inline evidence:** The finding lists the top empty hubs with their reference counts: `Top: [[Anthropic]] (8), [[Airtable]] (6), [[n8n]] (5)`.

## Future detectors (v3 candidates)

Captured for future work, not yet implemented:

- `INSUFFICIENT_CORPUS` — fires when the ingester produces fewer than N pages or the body is empty. Catches SPA-only sites that JavaScript-render their content. Currently the pipeline silently produces a hollow report.
- `CONVENTION_DRIFT` — fires when a dangling reference has a normalised-name match in the vault (e.g., title-case dangling, kebab-case file exists). Avoids prompting the operator to promote a redundant draft.
- `WIKILINK_DENSITY_LOW` — fires when wikilinks-per-note is below 0.5. Pre-runs the diagnostic before Phase 2, so the recommendation can be Phase 1A immediately.

If you implement any of these, append the catalog entry here and reference it in the SKILL.md routing table.
