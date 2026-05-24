#!/usr/bin/env python3
"""Prepare a bridge-questions task file for the agent (no API key required).

Reads the JSON sidecar produced by `vault_graph.py`, identifies structural
gaps (cluster pairs with no cross-edges), pulls business context from the
vault, and writes a single markdown task file the agent can process.

The agent then generates sharp research questions for each gap using its
own Claude Code subscription. No separate `ANTHROPIC_API_KEY` needed.
This replaces the prior `bridge_questions.py` which called the Anthropic
API directly.

Output: `Reports/knowledge-graph/bridge-question-tasks-YYYY-MM-DD.md`
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path


def load_business_context(vault: Path) -> str:
    snippets: list[str] = []
    for relpath in ("Context/organization.md", "Context/services.md"):
        f = vault / relpath
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        if text.startswith("---"):
            end = text.find("\n---", 4)
            if end != -1:
                text = text[end + 4:]
        lines = [ln for ln in text.splitlines() if ln.strip()][:20]
        snippets.append(f"### From {relpath}\n" + "\n".join(lines))
    return "\n\n".join(snippets) if snippets else "_No business context found._"


def render_task_file(graph: dict, business: str, today: str) -> str:
    communities = graph.get("communities", [])
    gaps = graph.get("gaps", [])
    top_hubs = [n for n, _ in graph.get("top_degree", [])]

    lines: list[str] = []
    lines.append("---")
    lines.append("type: bridge-question-tasks")
    lines.append(f"date: {today}")
    lines.append("project: Blueprint-OS")
    lines.append("status: ready-for-agent")
    lines.append("tags: [knowledge-graph, bridge-questions, agent-task, os-evolver]")
    lines.append("---")
    lines.append("")
    lines.append("> [!info] How to process this file")
    lines.append(">")
    lines.append("> Each gap below is a pair of clusters in the vault graph with no edges between them.")
    lines.append("> For each gap, generate 2 to 3 sharp research questions whose answers would force a")
    lines.append("> useful connection.")
    lines.append(">")
    lines.append("> **Output file:** `Reports/knowledge-graph/bridge-questions-" + today + ".md`")
    lines.append(">")
    lines.append("> **Output format:** a markdown checklist grouped by gap. Each question becomes a")
    lines.append("> `- [ ]` item. The operator copies the keepers into their task list.")
    lines.append(">")
    lines.append("> **Question rules:**")
    lines.append("> - Each question MUST reference specific concepts from BOTH clusters by name.")
    lines.append("> - Each must be answerable by writing one short note or doing one piece of research.")
    lines.append("> - Skip generic 'how does X relate to Y' phrasings.")
    lines.append("> - Phrase as questions the operator would actually want answered.")
    lines.append("> - Never use em dashes. Periods, commas, or colons only.")
    lines.append("")

    lines.append("## Business context (use this to ground the questions)")
    lines.append("")
    lines.append(business)
    lines.append("")
    lines.append("## Vault anchors")
    lines.append("")
    if top_hubs:
        lines.append(f"The most-referenced entities in the vault: {', '.join(top_hubs)}.")
    else:
        lines.append("_No anchors detected._")
    lines.append("")
    lines.append("---")
    lines.append("")

    if not gaps:
        lines.append("## No structural gaps detected")
        lines.append("")
        lines.append(
            "The graph has no fully-disconnected cluster pairs to bridge today. "
            "This can happen when (a) the vault is dominated by a single hub (star topology), "
            "or (b) the corpus is genuinely well-linked. Re-run after the next round of note "
            "drafting or enrichment."
        )
        lines.append("")
        return "\n".join(lines) + "\n"

    lines.append(f"## {len(gaps)} structural gap(s) to bridge")
    lines.append("")

    for i, gap in enumerate(gaps, 1):
        a_members = communities[gap["cluster_a"]]["members"]
        b_members = communities[gap["cluster_b"]]["members"]
        lines.append(f"### Gap {i}")
        lines.append("")
        lines.append(f"**Cluster A ({len(a_members)} nodes):**")
        lines.append("")
        lines.append(", ".join(f"[[{n}]]" for n in a_members))
        lines.append("")
        lines.append(f"**Cluster B ({len(b_members)} nodes):**")
        lines.append("")
        lines.append(", ".join(f"[[{n}]]" for n in b_members))
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--vault", required=True, help="Vault root (for business context).")
    parser.add_argument("--graph-json", required=True, help="JSON sidecar from vault_graph.py.")
    parser.add_argument("--output", help="Output task file path.")
    args = parser.parse_args(argv)

    vault = Path(args.vault).expanduser().resolve()
    if not vault.is_dir():
        print(f"vault path not a directory: {vault}", file=sys.stderr)
        return 2

    graph_path = Path(args.graph_json).expanduser().resolve()
    if not graph_path.is_file():
        print(f"graph JSON not found: {graph_path}", file=sys.stderr)
        return 2

    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    business = load_business_context(vault)
    today = date.today().isoformat()

    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else vault / "Reports" / "knowledge-graph" / f"bridge-question-tasks-{today}.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_task_file(graph, business, today), encoding="utf-8")

    gap_count = len(graph.get("gaps", []))
    print(f"task file -> {output_path}", file=sys.stderr)
    print(f"summary: {gap_count} gap(s) queued for agent question generation", file=sys.stderr)
    if gap_count == 0:
        print("(no gaps to bridge; the agent will note this in the output)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
