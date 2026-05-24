#!/usr/bin/env python3
"""Build a knowledge graph from an Obsidian-style vault and surface gaps.

Walks a vault directory, parses [[wikilinks]] from every markdown file,
constructs an undirected graph, then runs:

  - degree + betweenness centrality (hubs and bridges)
  - Louvain community detection (clusters)
  - orphan detection (files with no links in or out)
  - dangling reference detection (links pointing at missing files)
  - structural-hole detection (cluster pairs with no cross-edges)

Outputs a markdown report (wikilink-native, drops into the vault) and
optionally a JSON sidecar for downstream LLM consumption.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import networkx as nx
from networkx.algorithms import community as nx_community

from detectors import findings_to_json, findings_to_markdown, run_all as run_detectors

WIKILINK_RE = re.compile(r"\[\[([^\]]+?)\]\]")

# Filenames that are instructions to the assistant, not knowledge content.
SKIP_FILENAMES = {"CLAUDE.md", "GEMINI.md", "AGENTS.md"}

# Directories that are scaffolding or generated output, not knowledge.
SKIP_DIR_PREFIXES = (".obsidian", ".trash", ".git")

# Directory NAMES (matched anywhere in the path) that are treated as engine
# working data rather than knowledge. Override with --exclude.
DEFAULT_EXCLUDE_DIRS = ("corpora", "reports", "drafts", "output")


def parse_vault(
    vault_root: Path,
    exclude_dirs: tuple[str, ...] = DEFAULT_EXCLUDE_DIRS,
) -> tuple[dict[str, list[str]], dict[str, Path]]:
    """Return ({note_title: [link_targets]}, {note_title: source_path}).

    Note titles are the file stem (filename without .md). This matches
    Obsidian's default linking behaviour where `[[Foo]]` resolves to `Foo.md`
    wherever it sits in the vault.
    """
    notes: dict[str, list[str]] = {}
    sources: dict[str, Path] = {}
    exclude_set = {d.casefold() for d in exclude_dirs}

    for md_file in vault_root.rglob("*.md"):
        rel_parts = md_file.relative_to(vault_root).parts
        if any(p.startswith(SKIP_DIR_PREFIXES) for p in rel_parts):
            continue
        if any(p.casefold() in exclude_set for p in rel_parts):
            continue
        if md_file.name in SKIP_FILENAMES:
            continue

        title = md_file.stem
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        links: list[str] = []
        for match in WIKILINK_RE.finditer(text):
            raw = match.group(1)
            # [[Note|Display]] -> Note ; [[Note#Heading]] -> Note ;
            # [[folder/Note]] -> Note (Obsidian resolves by basename).
            target = raw.split("|", 1)[0].split("#", 1)[0].strip()
            if not target:
                continue
            target_name = target.split("/")[-1]
            if target_name and target_name != title:
                links.append(target_name)

        notes[title] = links
        sources[title] = md_file

    return notes, sources


def build_graph(notes: dict[str, list[str]], sources: dict[str, Path]) -> nx.Graph:
    """Construct undirected weighted graph. Weight = link occurrence count."""
    G = nx.Graph()
    for title in notes:
        G.add_node(title, has_file=True)

    edge_weights: dict[tuple[str, str], int] = defaultdict(int)
    for title, links in notes.items():
        for target in links:
            if target not in G:
                G.add_node(target, has_file=False)
            key = tuple(sorted((title, target)))
            edge_weights[key] += 1

    for (u, v), w in edge_weights.items():
        G.add_edge(u, v, weight=w)
    return G


def analyze(G: nx.Graph) -> dict:
    file_nodes = {n for n, d in G.nodes(data=True) if d.get("has_file")}

    components = sorted(nx.connected_components(G), key=len, reverse=True)
    main_nodes = components[0] if components else set()
    main = G.subgraph(main_nodes).copy() if main_nodes else G

    betweenness = nx.betweenness_centrality(main, weight=None) if main.number_of_nodes() else {}
    degree = dict(G.degree())

    top_central = sorted(betweenness.items(), key=lambda x: -x[1])[:10]
    top_degree = sorted(
        ((n, d) for n, d in degree.items() if n in file_nodes),
        key=lambda x: -x[1],
    )[:10]

    if main.number_of_edges() > 0:
        communities_raw = nx_community.louvain_communities(main, seed=42, weight="weight")
    else:
        communities_raw = []
    communities = sorted(
        ({"members": sorted(c)} for c in communities_raw),
        key=lambda c: -len(c["members"]),
    )

    orphans = sorted(n for n in file_nodes if G.degree(n) == 0)
    dangling = sorted(
        n for n, d in G.nodes(data=True)
        if not d.get("has_file") and G.degree(n) > 0
    )

    gaps: list[dict] = []
    for i in range(len(communities)):
        for j in range(i + 1, len(communities)):
            ci = communities[i]["members"]
            cj = communities[j]["members"]
            if min(len(ci), len(cj)) < 3:
                continue
            cross = sum(1 for u in ci for v in cj if G.has_edge(u, v))
            if cross == 0:
                gaps.append({"cluster_a": i, "cluster_b": j, "cross_edges": 0})

    return {
        "file_count": len(file_nodes),
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "component_count": len(components),
        "main_component_size": len(main_nodes),
        "dangling_count": len(dangling),
        "orphan_count": len(orphans),
        "top_central": top_central,
        "top_degree": top_degree,
        "communities": communities,
        "orphans": orphans,
        "dangling": dangling,
        "gaps": gaps,
    }


def render_report(result: dict, vault_root: Path) -> str:
    today = date.today().isoformat()
    lines: list[str] = []
    lines.append("---")
    lines.append("type: graph-report")
    lines.append(f"date: {today}")
    lines.append("project: Blueprint-OS")
    lines.append("status: generated")
    lines.append("tags: [knowledge-graph, vault-analysis, blueprint-os]")
    lines.append("---")
    lines.append("")
    lines.append("> [!info] Vault snapshot")
    lines.append(
        f"> {result['file_count']} notes, "
        f"{result['edge_count']} unique links, "
        f"{result['component_count']} disconnected components "
        f"(largest: {result['main_component_size']} nodes), "
        f"{result['orphan_count']} orphan notes, "
        f"{result['dangling_count']} dangling references."
    )
    lines.append("")

    lines.append("## Diagnostics")
    lines.append(
        "Automated pattern detection over the graph. Severity ordered. See the detail sections "
        "below for the raw metrics behind each finding."
    )
    lines.append("")
    lines.append(findings_to_markdown(result.get("findings_md_source", [])))

    lines.append("## Bridges: top concepts by betweenness centrality")
    lines.append(
        "Removing these fractures the graph. These are the ideas the rest of the vault is organised around."
    )
    lines.append("")
    if result["top_central"]:
        for name, score in result["top_central"]:
            lines.append(f"- [[{name}]] : {score:.4f}")
    else:
        lines.append("_No bridges detected (vault too small or fully disconnected)._")
    lines.append("")

    lines.append("## Hubs: top concepts by degree")
    lines.append("Most-referenced entities. Anchor concepts of the vault.")
    lines.append("")
    if result["top_degree"]:
        for name, deg in result["top_degree"]:
            lines.append(f"- [[{name}]] : {deg} connections")
    else:
        lines.append("_No hubs detected._")
    lines.append("")

    lines.append("## Clusters")
    lines.append(
        f"Louvain community detection over the largest connected component. "
        f"{len(result['communities'])} clusters found."
    )
    lines.append("")
    for i, c in enumerate(result["communities"][:10]):
        members = c["members"]
        sample = ", ".join(f"[[{n}]]" for n in members[:8])
        more = f" (+{len(members) - 8} more)" if len(members) > 8 else ""
        lines.append(f"### Cluster {i + 1}: {len(members)} nodes")
        lines.append(f"{sample}{more}")
        lines.append("")

    lines.append("## Structural gaps")
    lines.append(
        "Cluster pairs with **no shared edges**. These are bridge candidates: "
        "new content or research connecting them would make the knowledge base more coherent."
    )
    lines.append("")
    if result["gaps"]:
        for gap in result["gaps"][:15]:
            ci = result["communities"][gap["cluster_a"]]["members"]
            cj = result["communities"][gap["cluster_b"]]["members"]
            ci_sample = ", ".join(f"[[{n}]]" for n in ci[:3])
            cj_sample = ", ".join(f"[[{n}]]" for n in cj[:3])
            lines.append(
                f"- Cluster {gap['cluster_a'] + 1} ({ci_sample} …) ↔ "
                f"Cluster {gap['cluster_b'] + 1} ({cj_sample} …)"
            )
    else:
        lines.append("_No fully disconnected cluster pairs. Graph is densely linked._")
    lines.append("")

    lines.append("## Orphan notes")
    lines.append(
        "Files in the vault with no incoming or outgoing wikilinks. "
        "Likely stale, miscategorised, or written without weaving into existing context."
    )
    lines.append("")
    if result["orphans"]:
        for n in result["orphans"][:25]:
            lines.append(f"- [[{n}]]")
        if len(result["orphans"]) > 25:
            lines.append(f"- … and {len(result['orphans']) - 25} more")
    else:
        lines.append("_None._")
    lines.append("")

    lines.append("## Dangling references")
    lines.append(
        "Wikilinks pointing at notes that do not exist. Either typos or "
        "concepts the operator has already gestured at but never written up."
    )
    lines.append("")
    if result["dangling"]:
        for n in result["dangling"][:25]:
            lines.append(f"- [[{n}]]")
        if len(result["dangling"]) > 25:
            lines.append(f"- … and {len(result['dangling']) - 25} more")
    else:
        lines.append("_None._")
    lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--vault", required=True, help="Path to vault root.")
    parser.add_argument("--output", help="Path for the markdown report. If omitted, prints to stdout.")
    parser.add_argument("--json", action="store_true", help="Also emit a JSON sidecar next to the report.")
    parser.add_argument(
        "--exclude",
        action="append",
        default=None,
        help=(
            f"Directory name to skip (any depth). Repeatable. "
            f"Defaults: {', '.join(DEFAULT_EXCLUDE_DIRS)}. "
            "Pass --exclude '' to disable defaults."
        ),
    )
    args = parser.parse_args(argv)

    if args.exclude is None:
        exclude_dirs = DEFAULT_EXCLUDE_DIRS
    else:
        exclude_dirs = tuple(d for d in args.exclude if d)

    vault = Path(args.vault).expanduser().resolve()
    if not vault.is_dir():
        print(f"vault path not a directory: {vault}", file=sys.stderr)
        return 2

    notes, sources = parse_vault(vault, exclude_dirs=exclude_dirs)
    if not notes:
        print(f"no markdown notes found under {vault}", file=sys.stderr)
        return 1

    G = build_graph(notes, sources)
    result = analyze(G)
    findings = run_detectors(G, result)
    # render_report reads findings via this key; keeping it out of the JSON-shaped result.
    result["findings_md_source"] = findings
    report = render_report(result, vault)

    if args.output:
        out = Path(args.output).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"report -> {out}")
        if args.json:
            json_path = out.with_suffix(".json")
            payload = {
                **{k: v for k, v in result.items() if k != "findings_md_source"},
                "communities": [{"members": c["members"]} for c in result["communities"]],
                "findings": findings_to_json(findings),
            }
            json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
            print(f"json   -> {json_path}")
    else:
        sys.stdout.write(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
