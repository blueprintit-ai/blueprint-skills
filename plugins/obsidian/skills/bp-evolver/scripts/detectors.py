"""Diagnostic detectors for the Blueprint OS knowledge-graph engine.

Each detector examines the graph and the analysis result, returning zero or
more Findings. The output is structured (severity, headline, narrative,
recommendation, evidence) so reports can be both human-readable and
machine-consumable for downstream LLM passes.

Why these specific detectors: they encode the failure modes we have actually
seen in client corpora. Bridge-question generation (the prior LLM pass) is
strong when the graph has multiple healthy clusters with weak inter-cluster
links. It is a no-op when the topology is degenerate. These detectors catch
the degenerate cases.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

import networkx as nx


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

SEVERITY_BADGE = {
    "critical": "🔴 CRITICAL",
    "high": "🟠 HIGH",
    "medium": "🟡 MEDIUM",
    "low": "🔵 LOW",
    "info": "ℹ️ INFO",
}


@dataclass
class Finding:
    id: str
    severity: str
    headline: str
    narrative: str
    recommendation: str
    evidence: dict[str, Any] = field(default_factory=dict)


def detect_star_topology(G: nx.Graph, a: dict) -> list[Finding]:
    """Single node carries the entire graph as its only bridge."""
    if not a["top_central"] or a["main_component_size"] < 5:
        return []
    node, score = a["top_central"][0]
    if score < 0.85:
        return []
    severity = "critical" if score >= 0.95 else "high"
    return [
        Finding(
            id="STAR_TOPOLOGY",
            severity=severity,
            headline=f"The graph is a star: [[{node}]] is the sole bridge (betweenness {score:.2f})",
            narrative=(
                f"Of the {a['main_component_size']} nodes in the main connected component, "
                f"[[{node}]] is the only structural bridge. Remove it and the corpus fractures into "
                f"{a['component_count']} or more islands. The content has no lateral structure; every "
                "page depends on this single hub for discoverability and SEO link equity."
            ),
            recommendation=(
                "Add lateral links between related pages. On retail sites this means a Related Categories "
                "module between sibling collections. In knowledge bases this means cross-references between "
                "related topics. This is typically the single biggest internal-linking lever available."
            ),
            evidence={
                "hub_node": node,
                "betweenness": score,
                "main_component_size": a["main_component_size"],
            },
        )
    ]


def detect_fragmented_graph(G: nx.Graph, a: dict) -> list[Finding]:
    """Too many disconnected components for the corpus size."""
    if a["file_count"] < 10:
        return []
    frag = a["component_count"] / max(a["file_count"], 1)
    if frag < 0.5:
        return []
    severity = "critical" if frag >= 0.8 else "high"
    return [
        Finding(
            id="FRAGMENTED_GRAPH",
            severity=severity,
            headline=(
                f"{a['component_count']} disconnected components in a "
                f"{a['file_count']}-file corpus"
            ),
            narrative=(
                "A healthy corpus has one or a few large components. This one has "
                f"{a['component_count']} components for {a['file_count']} files, meaning most content "
                "exists in tiny isolated islands. Search authority and human discovery cannot flow "
                "between regions."
            ),
            recommendation=(
                "Establish hub-and-spoke topology at minimum: every leaf links back to a category hub, "
                "every hub lists its leaves. Then add lateral links between sibling leaves."
            ),
            evidence={
                "component_count": a["component_count"],
                "file_count": a["file_count"],
                "fragmentation_ratio": frag,
            },
        )
    ]


def detect_high_orphan_rate(G: nx.Graph, a: dict) -> list[Finding]:
    """Many files exist with no links in or out."""
    if a["file_count"] < 20:
        return []
    rate = a["orphan_count"] / a["file_count"]
    if rate < 0.4:
        return []
    severity = "critical" if rate >= 0.7 else "high" if rate >= 0.55 else "medium"
    return [
        Finding(
            id="HIGH_ORPHAN_RATE",
            severity=severity,
            headline=(
                f"{a['orphan_count']} of {a['file_count']} files ({rate:.0%}) are orphans"
            ),
            narrative=(
                f"An orphan file neither links out nor is linked to. {a['orphan_count']} files "
                f"({rate:.0%} of the corpus) sit in isolation. Either they are stale and should be "
                "archived, or they are valuable content that the rest of the corpus fails to reference."
            ),
            recommendation=(
                "Audit each orphan. Archive what is stale; weave the rest into existing topical "
                "clusters. For a retail catalog this typically means adding category cross-links and "
                "breadcrumb-style navigation to every product or collection page."
            ),
            evidence={
                "orphan_count": a["orphan_count"],
                "file_count": a["file_count"],
                "rate": rate,
                "samples": a["orphans"][:10],
            },
        )
    ]


def detect_hub_dependence(G: nx.Graph, a: dict) -> list[Finding]:
    """The top hub participates in most edges in the graph."""
    if a["file_count"] < 20 or not a["top_degree"] or G.number_of_edges() == 0:
        return []
    top_hub, _ = a["top_degree"][0]
    if not G.has_node(top_hub):
        return []
    hub_edges = G.degree(top_hub)
    share = hub_edges / G.number_of_edges()
    if share < 0.5:
        return []
    severity = "high" if share >= 0.7 else "medium"
    return [
        Finding(
            id="HUB_DEPENDENCE",
            severity=severity,
            headline=(
                f"[[{top_hub}]] participates in {share:.0%} of all internal links"
            ),
            narrative=(
                f"The most-connected node, [[{top_hub}]], touches more than half of every internal "
                "link. The corpus relies on a single hub for navigation, which collapses if that page "
                "is removed or deprioritised."
            ),
            recommendation=(
                "Distribute linking responsibility. Sibling pages should link directly to each other "
                "rather than routing every visitor and every search crawler through the hub."
            ),
            evidence={
                "hub": top_hub,
                "hub_share_of_edges": share,
                "total_edges": G.number_of_edges(),
            },
        )
    ]


BLOG_TITLE_PATTERNS = [
    r"\bhow to\b", r"\bwhy\b", r"\bwhen should\b", r"\bvs\b", r"\bvs\.\b",
    r"\bchoosing\b", r"\bbest\b", r"\bguide\b", r"\btips?\b", r"\bmust have\b",
    r"\bcompared\b", r"\bideas?\b", r"\b\d+ (must|ways|things|reasons)\b",
]
_BLOG_RE = re.compile("|".join(BLOG_TITLE_PATTERNS), re.IGNORECASE)


def detect_siloed_content(G: nx.Graph, a: dict) -> list[Finding]:
    """Editorial or buying-guide content appears only as dangling references."""
    candidates: list[str] = []
    for name in a["dangling"]:
        words = name.split()
        if len(words) >= 5 and _BLOG_RE.search(name):
            candidates.append(name)
        elif len(words) >= 8:
            candidates.append(name)
    if len(candidates) < 3:
        return []
    severity = "high" if len(candidates) >= 8 else "medium"
    return [
        Finding(
            id="SILOED_CONTENT_THEMES",
            severity=severity,
            headline=(
                f"{len(candidates)} likely blog or buying-guide titles appear as dangling references"
            ),
            narrative=(
                "These long, content-style titles are referenced from the corpus but no reachable file "
                "carries the matching name. Typically this means editorial or blog content lives in a "
                "separate silo that the main catalog never links to, stranding the content investment."
            ),
            recommendation=(
                "Pair each editorial piece with the catalog page it supports. Every blog post gets a "
                "'shop the article' section. Every category page embeds one or two relevant buying guides."
            ),
            evidence={"candidates": candidates[:15], "count": len(candidates)},
        )
    ]


def detect_empty_hubs(G: nx.Graph, a: dict) -> list[Finding]:
    """Concepts referenced repeatedly that have no canonical file behind them."""
    # Rank dangling nodes by degree; only flag the meaningfully-referenced ones.
    ranked = sorted(
        ((n, G.degree(n)) for n in a["dangling"] if G.has_node(n)),
        key=lambda x: -x[1],
    )
    significant = [(n, d) for n, d in ranked if d >= 3][:10]
    if not significant:
        return []
    severity = "high" if significant[0][1] >= 8 else "medium"
    return [
        Finding(
            id="EMPTY_HUBS",
            severity=severity,
            headline=(
                f"{len(significant)} concept(s) are heavily referenced but have no canonical note"
            ),
            narrative=(
                "These concepts are referenced repeatedly across the corpus but no file with the "
                "matching name exists. In a knowledge base this is content the operator has gestured "
                "at without canonising. On a website it is often a category label that should be a "
                "real landing page but is currently just an unresolved link."
            ),
            recommendation=(
                "Write the canonical note for each, ordered by reference count. The act of giving a "
                "referenced concept its own page usually surfaces structure already implicit in the "
                "references."
            ),
            evidence={
                "hubs": [{"name": n, "degree": d} for n, d in significant],
            },
        )
    ]


DETECTORS: list[Callable[[nx.Graph, dict], list[Finding]]] = [
    detect_star_topology,
    detect_fragmented_graph,
    detect_high_orphan_rate,
    detect_hub_dependence,
    detect_siloed_content,
    detect_empty_hubs,
]


def run_all(G: nx.Graph, analysis: dict) -> list[Finding]:
    findings: list[Finding] = []
    for fn in DETECTORS:
        try:
            findings.extend(fn(G, analysis))
        except Exception as exc:  # detectors should never break the report
            findings.append(
                Finding(
                    id="DETECTOR_ERROR",
                    severity="low",
                    headline=f"detector {fn.__name__} raised {type(exc).__name__}",
                    narrative=str(exc),
                    recommendation="",
                    evidence={},
                )
            )
    findings.sort(key=lambda f: SEVERITY_ORDER.get(f.severity, 99))
    return findings


def _evidence_examples(ev: dict[str, Any]) -> str:
    """Render a one-line 'Examples:' bullet from finding evidence, when shaped as a list."""
    if "candidates" in ev and ev["candidates"]:
        items = ev["candidates"][:6]
        more = len(ev.get("candidates", [])) - len(items)
        rendered = ", ".join(f"[[{c}]]" for c in items)
        return f"**Examples:** {rendered}" + (f" (+{more} more)" if more > 0 else "")
    if "samples" in ev and ev["samples"]:
        items = ev["samples"][:6]
        more = ev.get("orphan_count", 0) - len(items)
        rendered = ", ".join(f"[[{c}]]" for c in items)
        return f"**Examples:** {rendered}" + (f" (+{more} more)" if more > 0 else "")
    if "hubs" in ev and ev["hubs"]:
        items = ev["hubs"][:6]
        rendered = ", ".join(f"[[{h['name']}]] ({h['degree']})" for h in items)
        more = len(ev.get("hubs", [])) - len(items)
        return f"**Top:** {rendered}" + (f" (+{more} more)" if more > 0 else "")
    return ""


def findings_to_markdown(findings: list[Finding]) -> str:
    if not findings:
        return (
            "_No diagnostic findings. The corpus does not exhibit any of the failure modes "
            "the engine knows about._\n"
        )
    lines: list[str] = []
    for f in findings:
        badge = SEVERITY_BADGE.get(f.severity, f.severity.upper())
        lines.append(f"### {badge}  {f.headline}")
        lines.append("")
        lines.append(f.narrative)
        lines.append("")
        examples = _evidence_examples(f.evidence)
        if examples:
            lines.append(examples)
            lines.append("")
        if f.recommendation:
            lines.append("> [!tip] Recommendation")
            lines.append(f"> {f.recommendation}")
            lines.append("")
    return "\n".join(lines)


def findings_to_json(findings: list[Finding]) -> list[dict]:
    return [
        {
            "id": f.id,
            "severity": f.severity,
            "headline": f.headline,
            "narrative": f.narrative,
            "recommendation": f.recommendation,
            "evidence": f.evidence,
        }
        for f in findings
    ]
