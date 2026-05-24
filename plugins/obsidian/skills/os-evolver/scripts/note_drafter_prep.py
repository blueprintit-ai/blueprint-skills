#!/usr/bin/env python3
"""Prepare a note-drafting task file for the agent (no API key required).

Reads the JSON sidecar produced by `vault_graph.py`, picks the top-N dangling
references (concepts cited repeatedly in the vault with no canonical file
behind them), finds the actual excerpts in the vault where each is
referenced, and writes a single markdown task file the agent can process.

The agent then drafts each canonical note using its own Claude Code
subscription (no separate `ANTHROPIC_API_KEY` needed). This replaces the
prior `note_drafter.py` which called the Anthropic API directly.

Output: `Reports/knowledge-graph/note-drafting-tasks-YYYY-MM-DD.md`
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SKIP_DIR_PREFIXES = (".obsidian", ".trash", ".git")
SKIP_DIR_NAMES = {"corpora", "reports", "drafts", "output", "Reports"}
SKIP_FILENAMES = {"CLAUDE.md", "GEMINI.md", "AGENTS.md"}

WIKILINK_RE = re.compile(r"\[\[([^\]]+?)\]\]")


def should_skip(md_file: Path, vault: Path) -> bool:
    try:
        rel = md_file.relative_to(vault).parts
    except ValueError:
        return True
    if any(p.startswith(SKIP_DIR_PREFIXES) for p in rel):
        return True
    if any(p in SKIP_DIR_NAMES for p in rel):
        return True
    if md_file.name in SKIP_FILENAMES:
        return True
    return False


def count_references_in_vault(vault: Path, candidates: list[str]) -> dict[str, int]:
    patterns = {
        name: re.compile(r"\[\[\s*" + re.escape(name) + r"\s*(\||#|\])")
        for name in candidates
    }
    counts: dict[str, int] = {name: 0 for name in candidates}
    for md_file in vault.rglob("*.md"):
        if should_skip(md_file, vault):
            continue
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for name, pat in patterns.items():
            counts[name] += len(pat.findall(text))
    return counts


def find_references(concept: str, vault: Path, max_files: int = 6) -> list[dict]:
    pattern = re.compile(r"\[\[\s*" + re.escape(concept) + r"\s*(\||#|\])")
    refs: list[dict] = []
    for md_file in sorted(vault.rglob("*.md")):
        if should_skip(md_file, vault):
            continue
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if not pattern.search(text):
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if pattern.search(line):
                start = max(0, i - 1)
                end = min(len(lines), i + 2)
                excerpt = "\n".join(ln for ln in lines[start:end] if ln.strip())
                refs.append(
                    {
                        "file": str(md_file.relative_to(vault)),
                        "excerpt": excerpt[:400],
                    }
                )
                break
        if len(refs) >= max_files:
            break
    return refs


def find_related_concepts(refs: list[dict], concept: str) -> list[str]:
    counter: dict[str, int] = {}
    for ref in refs:
        for m in WIKILINK_RE.finditer(ref["excerpt"]):
            raw = m.group(1).split("|", 1)[0].split("#", 1)[0].strip()
            target = raw.split("/")[-1]
            if not target or target == concept:
                continue
            counter[target] = counter.get(target, 0) + 1
    return [t for t, _ in sorted(counter.items(), key=lambda x: -x[1])][:8]


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


def suggest_target(concept: str, vault: Path) -> str:
    infra = vault / "Context/infrastructure.md"
    if infra.is_file():
        try:
            if f"[[{concept}]]" in infra.read_text(encoding="utf-8", errors="ignore"):
                return f"Resources/tools/{concept}.md (referenced in Context/infrastructure)"
        except OSError:
            pass
    if re.match(r"^[A-Z][a-z]+( [A-Z][a-z]+)+$", concept):
        return f"Team/External/contacts/{concept}.md (looks like a person name)"
    if "-" in concept and concept.islower():
        return f"Projects/{concept}/README.md (looks like a project slug)"
    return f"Resources/concepts/{concept}.md (default; move if a better home applies)"


def render_task_file(
    vault: Path,
    ranked: list[tuple[str, int]],
    today: str,
    business: str,
) -> str:
    lines: list[str] = []
    lines.append("---")
    lines.append("type: note-drafting-tasks")
    lines.append(f"date: {today}")
    lines.append("project: Blueprint-OS")
    lines.append("status: ready-for-agent")
    lines.append("tags: [knowledge-graph, drafts, agent-task, os-evolver]")
    lines.append("---")
    lines.append("")
    lines.append("> [!info] How to process this file")
    lines.append(">")
    lines.append("> Each section below is a dangling reference: a concept cited repeatedly in the vault")
    lines.append("> but with no canonical file behind it. For each section, draft a short canonical note")
    lines.append("> grounded in the actual excerpts shown.")
    lines.append(">")
    lines.append("> **Output path for each draft:** `drafts/" + today + "/{Concept Name}.md`")
    lines.append(">")
    lines.append("> **Frontmatter for every draft:**")
    lines.append("> ```yaml")
    lines.append("> ---")
    lines.append("> type: concept")
    lines.append("> tags: [...]  # 2+ relevant tags")
    lines.append("> status: draft")
    lines.append("> ---")
    lines.append("> ```")
    lines.append(">")
    lines.append("> **Then:** a `# {Concept Name}` H1 heading, then 2-4 short paragraphs.")
    lines.append(">")
    lines.append("> **Drafting rules:**")
    lines.append("> - Lead sentence defines what the concept IS in this operator's world. Specific, not generic.")
    lines.append("> - Body: 2 to 4 short paragraphs. Factual, terse, teammate voice. No marketing fluff.")
    lines.append("> - Weave 2 to 5 `[[wikilinks]]` into prose, drawn from the related-concepts list in each section.")
    lines.append("> - Never use em dashes. Periods, commas, or colons only.")
    lines.append("> - When a draft would duplicate an existing canonical file under different casing or slug, SKIP it and note that in the INDEX instead. Check by listing the target folder first.")
    lines.append(">")
    lines.append("> **When done:** write `drafts/" + today + "/INDEX.md` listing each draft with the suggested target location (shown per section below).")
    lines.append("")

    lines.append("## Business context (use this to ground every draft)")
    lines.append("")
    lines.append(business)
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, (concept, refs_count) in enumerate(ranked, 1):
        refs = find_references(concept, vault)
        related = find_related_concepts(refs, concept)
        target = suggest_target(concept, vault)

        lines.append(f"## {i}. `{concept}` (cited {refs_count} times)")
        lines.append("")
        lines.append(f"**Suggested target after promotion:** `{target}`")
        lines.append("")
        lines.append("**Where this concept appears in the vault today:**")
        lines.append("")
        if refs:
            for r in refs:
                lines.append(f"From `{r['file']}`:")
                lines.append("")
                lines.append("> " + r["excerpt"].replace("\n", "\n> "))
                lines.append("")
        else:
            lines.append("_No references found in the indexed vault. Skip this concept._")
            lines.append("")

        if related:
            related_block = ", ".join(f"[[{r}]]" for r in related)
            lines.append(f"**Related concepts (use 2-5 of these as wikilinks in the draft):** {related_block}")
        else:
            lines.append("**Related concepts:** _None observed in immediate context. Use your judgment._")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--vault", required=True, help="Vault root.")
    parser.add_argument("--graph-json", required=True, help="JSON sidecar from vault_graph.py.")
    parser.add_argument("--output", help="Output task file path. Default: <vault>/Reports/knowledge-graph/note-drafting-tasks-<date>.md")
    parser.add_argument("--top-n", type=int, default=10, help="How many top dangling concepts to include.")
    parser.add_argument("--min-references", type=int, default=2, help="Skip concepts referenced fewer than N times.")
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
    candidates = graph.get("dangling", [])
    if not candidates:
        print("no dangling references in graph; nothing to draft", file=sys.stderr)
        return 0

    print(f"counting references for {len(candidates)} dangling concepts...", file=sys.stderr)
    ref_counts = count_references_in_vault(vault, candidates)
    ranked = sorted(
        [(n, c) for n, c in ref_counts.items() if c >= args.min_references],
        key=lambda x: -x[1],
    )[: args.top_n]

    if not ranked:
        print(f"no dangling references with >= {args.min_references} citations", file=sys.stderr)
        return 0

    today = date.today().isoformat()
    business = load_business_context(vault)
    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else vault / "Reports" / "knowledge-graph" / f"note-drafting-tasks-{today}.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_task_file(vault, ranked, today, business), encoding="utf-8")

    print(f"task file -> {output_path}", file=sys.stderr)
    print(f"summary: {len(ranked)} concepts queued for agent drafting", file=sys.stderr)
    print("", file=sys.stderr)
    print("NEXT: invoke the agent to read this file and draft each concept.", file=sys.stderr)
    print(f"      Drafts will land in {vault / 'drafts' / today}/", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
