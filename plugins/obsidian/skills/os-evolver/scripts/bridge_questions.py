#!/usr/bin/env python3
"""Generate bridge questions from the Phase 1 graph JSON.

Reads the graph report JSON produced by `vault_graph.py`, identifies
structural gaps (cluster pairs with no cross-edges) plus dangling
references, and calls Claude to generate sharp, action-oriented questions
that would close each gap.

Output: a markdown report with checklist-style questions ready to copy
into a task list. Run with `--dry-run` to see the prompt that would be
sent without making any API call.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from textwrap import dedent

try:
    from anthropic import Anthropic  # type: ignore
except ImportError:
    Anthropic = None  # only needed when not in --dry-run

MODEL_DEFAULT = "claude-sonnet-4-6"
SYSTEM_PROMPT = (
    "You generate research questions that bridge structural gaps in a "
    "small-business operator's knowledge base. Be concise, specific, and "
    "action-oriented. Use the operator's own terminology (the concept "
    "names provided). Output strictly valid JSON, nothing else."
)


def load_graph(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_business_context(vault: Path) -> str:
    """Pull short business-context snippets from Context/ files if present."""
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
        lines = [ln for ln in text.splitlines() if ln.strip()][:25]
        snippets.append(f"### From {relpath}\n" + "\n".join(lines))
    return "\n\n".join(snippets) if snippets else "No business context found."


def build_prompt(graph: dict, business_context: str) -> str:
    communities = graph.get("communities", [])
    gaps = graph.get("gaps", [])
    top_hubs = [n for n, _ in graph.get("top_degree", [])]

    if not gaps:
        return ""

    gap_blocks: list[str] = []
    for i, gap in enumerate(gaps):
        a = communities[gap["cluster_a"]]["members"]
        b = communities[gap["cluster_b"]]["members"]
        gap_blocks.append(
            f"GAP {i + 1}:\n"
            f"  Cluster A: {', '.join(a)}\n"
            f"  Cluster B: {', '.join(b)}"
        )

    return dedent(f"""\
        ## Business context

        {business_context}

        ## Vault anchors

        Most-referenced entities (anchors of the knowledge base): {', '.join(top_hubs)}

        ## Structural gaps

        For each gap below, generate 2 to 3 sharp questions whose answers would
        force a useful connection between Cluster A and Cluster B.

        Rules:
        - Each question MUST reference specific concepts from BOTH clusters by name.
        - Each must be answerable by writing one short note or doing one piece of research.
        - Skip generic questions ("how does X relate to Y" type questions).
        - Phrase as questions the operator would actually want answered.

        {chr(10).join(gap_blocks)}

        Return ONLY JSON with this exact shape:
        {{
          "gaps": [
            {{"gap_index": 1, "questions": ["...", "..."]}},
            {{"gap_index": 2, "questions": ["...", "..."]}}
          ]
        }}
        """)


def call_claude(prompt: str, model: str) -> dict:
    if Anthropic is None:
        raise RuntimeError("anthropic SDK not installed. Run: pip install anthropic")
    client = Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        # strip code fences
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.removeprefix("json").strip()
    return json.loads(text)


def render_report(graph: dict, llm_result: dict | None, dry_run: bool) -> str:
    today = date.today().isoformat()
    communities = graph.get("communities", [])
    gaps = graph.get("gaps", [])
    dangling = graph.get("dangling", [])

    lines: list[str] = []
    lines.append("---")
    lines.append("type: bridge-questions")
    lines.append(f"date: {today}")
    lines.append("project: Blueprint-OS")
    lines.append("status: generated")
    lines.append("tags: [knowledge-graph, bridge-questions, research-queue, blueprint-os]")
    lines.append("---")
    lines.append("")
    lines.append("> [!info] What this is")
    lines.append(
        "> Sharp questions generated from the structural gaps surfaced by "
        "[[Projects/blueprint-os/src/vault_graph|the graph engine]]. Each "
        "answered question makes the knowledge base more coherent. Copy items "
        "into [[Team/blueprint-it/Profiles/glenn/task-list/Tasks|Tasks.md]] "
        "as you commit to them."
    )
    lines.append("")

    lines.append("## Bridge questions — connect disconnected clusters")
    lines.append("")
    if gaps:
        if dry_run:
            lines.append("_Dry run — no LLM call made. Re-run without `--dry-run` to populate._")
            lines.append("")
            for i, gap in enumerate(gaps):
                a = communities[gap["cluster_a"]]["members"]
                b = communities[gap["cluster_b"]]["members"]
                a_sample = ", ".join(f"[[{n}]]" for n in a[:4])
                b_sample = ", ".join(f"[[{n}]]" for n in b[:4])
                lines.append(f"### Gap {i + 1}: {a_sample} ↔ {b_sample}")
                lines.append("- [ ] _(pending LLM generation)_")
                lines.append("")
        elif llm_result:
            by_index = {g["gap_index"]: g["questions"] for g in llm_result.get("gaps", [])}
            for i, gap in enumerate(gaps):
                a = communities[gap["cluster_a"]]["members"]
                b = communities[gap["cluster_b"]]["members"]
                a_sample = ", ".join(f"[[{n}]]" for n in a[:4])
                b_sample = ", ".join(f"[[{n}]]" for n in b[:4])
                lines.append(f"### Gap {i + 1}: {a_sample} ↔ {b_sample}")
                lines.append("")
                for q in by_index.get(i + 1, []):
                    lines.append(f"- [ ] {q}")
                if not by_index.get(i + 1):
                    lines.append("- [ ] _(no questions returned for this gap)_")
                lines.append("")
    else:
        lines.append("_No structural gaps detected in current graph._")
        lines.append("")

    lines.append("## Notes to write — dangling references")
    lines.append(
        "Concepts the operator references repeatedly but has not written. "
        "Each is a one-shot note that closes a gap immediately."
    )
    lines.append("")
    if dangling:
        for n in dangling:
            lines.append(f"- [ ] Write [[{n}]] — canonical note for an entity already referenced across the vault.")
    else:
        lines.append("_None._")
    lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--graph-json", required=True, help="Path to the JSON sidecar from vault_graph.py")
    parser.add_argument("--vault", help="Vault root. Used to enrich the prompt with business context from Context/")
    parser.add_argument("--output", help="Markdown report output path. If omitted, prints to stdout.")
    parser.add_argument("--model", default=MODEL_DEFAULT, help=f"Anthropic model (default {MODEL_DEFAULT})")
    parser.add_argument("--dry-run", action="store_true", help="Skip the LLM call. Print the prompt and emit a placeholder report.")
    args = parser.parse_args(argv)

    graph_path = Path(args.graph_json).expanduser().resolve()
    if not graph_path.is_file():
        print(f"graph JSON not found: {graph_path}", file=sys.stderr)
        return 2

    graph = load_graph(graph_path)
    business_context = (
        load_business_context(Path(args.vault).expanduser().resolve())
        if args.vault else "No business context provided."
    )
    prompt = build_prompt(graph, business_context)

    llm_result: dict | None = None

    if args.dry_run:
        if prompt:
            sys.stderr.write("=== PROMPT (dry-run) ===\n\n")
            sys.stderr.write(prompt)
            sys.stderr.write("\n=== END PROMPT ===\n\n")
        else:
            sys.stderr.write("(no gaps to bridge — prompt would be empty)\n")
    else:
        if not prompt:
            sys.stderr.write("No structural gaps in the graph. Skipping LLM call.\n")
        else:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                print("ANTHROPIC_API_KEY not set. Either export it or pass --dry-run.", file=sys.stderr)
                return 2
            try:
                llm_result = call_claude(prompt, args.model)
            except json.JSONDecodeError as exc:
                print(f"LLM returned non-JSON output: {exc}", file=sys.stderr)
                return 3

    report = render_report(graph, llm_result, dry_run=args.dry_run)

    if args.output:
        out = Path(args.output).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"report -> {out}")
    else:
        sys.stdout.write(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
