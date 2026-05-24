#!/usr/bin/env python3
"""Close the loop: draft canonical notes for dangling references.

Reads the JSON sidecar produced by `vault_graph.py`, picks the top-N
dangling references (concepts cited repeatedly in the vault with no
canonical file behind them), finds the actual excerpts in the vault where
each is referenced, then asks Claude to draft a short canonical note
grounded in those excerpts.

Drafts land in a dated folder under `Projects/blueprint-os/drafts/`. The
operator reviews, edits, and moves each draft to its canonical home. Re-
running `vault_graph.py` after promotion shows the gaps closing.

This is the closing leg of the Karpathy / Nodus self-evolving research
loop: vault -> graph -> gaps -> drafted notes -> vault.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from textwrap import dedent

try:
    from anthropic import Anthropic  # type: ignore
except ImportError:
    Anthropic = None

MODEL_DEFAULT = "claude-sonnet-4-6"

SKIP_DIR_PREFIXES = (".obsidian", ".trash", ".git")
SKIP_DIR_NAMES = {"corpora", "reports", "drafts"}
SKIP_FILENAMES = {"CLAUDE.md", "GEMINI.md", "AGENTS.md"}

WIKILINK_RE = re.compile(r"\[\[([^\]]+?)\]\]")

SYSTEM_PROMPT = (
    "You write canonical concept notes for an operator's Obsidian knowledge vault. "
    "Your output is a single complete markdown file ready to drop into the vault. "
    "Voice: a teammate writing for another teammate. Terse and factual. No marketing fluff. "
    "Never use em dashes. Use periods, commas, or colons instead. "
    "Output ONLY the raw markdown file content. The first line of your output MUST be `---` "
    "(the frontmatter opener), NOT a code fence. Do not wrap the output in ```markdown or any "
    "code fence. No preamble. No explanation."
)


def load_graph(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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
    """Find files referencing the concept; return one short excerpt per file."""
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
    return "\n\n".join(snippets) if snippets else "No business context found."


def build_prompt(
    concept: str,
    refs: list[dict],
    related: list[str],
    business: str,
) -> str:
    refs_block = (
        "\n\n".join(f"From `{r['file']}`:\n{r['excerpt']}" for r in refs)
        if refs
        else "_No references found._"
    )
    related_block = (
        ", ".join(f"[[{r}]]" for r in related)
        if related
        else "_None observed in immediate context._"
    )
    return dedent(f"""\
        ## Business context

        {business}

        ## Concept to canonise

        `{concept}`

        ## Where this concept is referenced in the vault today

        {refs_block}

        ## Concepts that co-occur with this one

        {related_block}

        ## Task

        Draft a short canonical note for `{concept}.md` in this operator's knowledge vault.

        Requirements:
        - Lead with one sentence that defines what the concept IS in this operator's world. Specific, not generic.
        - Body: 2 to 4 short paragraphs. Factual, terse, teammate voice. No marketing fluff.
        - Weave 2 to 5 [[wikilinks]] into prose, drawn from the related-concepts list above.
        - Frontmatter: include `type`, 2 or more `tags`, and `status: draft`.
        - Include a `# {concept}` H1 heading immediately after the frontmatter.
        - Never use em dashes. Periods, commas, or colons only.

        Output the complete markdown file. No preamble. No explanation.
        """)


def call_claude(prompt: str, model: str) -> str:
    if Anthropic is None:
        raise RuntimeError("anthropic SDK not installed. Run: pip install anthropic")
    client = Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    # Defensive strip: if Claude wrapped output in a code fence anyway, peel it off.
    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl + 1:]
        if text.endswith("```"):
            text = text[: text.rfind("```")].rstrip()
    return text


def safe_filename(concept: str) -> str:
    s = re.sub(r'[/\\:*?"<>|]+', "-", concept.strip()).strip()
    return (s[:120] or "Untitled") + ".md"


def suggest_target(concept: str, vault: Path) -> str:
    """Best-guess where the promoted note should live."""
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


def render_dryrun_stub(concept: str, prompt: str) -> str:
    # Plain concatenation; do not dedent here, prompt has its own indentation rules.
    return (
        "---\n"
        "type: concept\n"
        "status: draft\n"
        "tags: [draft, dry-run, knowledge-graph]\n"
        "---\n\n"
        f"# {concept}\n\n"
        "_(dry-run. No LLM call was made. Re-run without `--dry-run` to populate.)_\n\n"
        "## Prompt that would be sent\n\n"
        "```\n"
        f"{prompt}\n"
        "```\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--vault", required=True, help="Vault root.")
    parser.add_argument("--graph-json", required=True, help="JSON sidecar from vault_graph.py.")
    parser.add_argument("--output-dir", help="Where to write drafts. Default: <vault>/Projects/blueprint-os/drafts/<date>/")
    parser.add_argument("--top-n", type=int, default=10, help="How many concepts to draft.")
    parser.add_argument("--min-references", type=int, default=2, help="Skip concepts referenced fewer than N times.")
    parser.add_argument("--model", default=MODEL_DEFAULT)
    parser.add_argument("--dry-run", action="store_true", help="Print prompts and write stubs instead of calling Claude.")
    args = parser.parse_args(argv)

    vault = Path(args.vault).expanduser().resolve()
    if not vault.is_dir():
        print(f"vault path not a directory: {vault}", file=sys.stderr)
        return 2

    graph_path = Path(args.graph_json).expanduser().resolve()
    if not graph_path.is_file():
        print(f"graph JSON not found: {graph_path}", file=sys.stderr)
        return 2

    graph = load_graph(graph_path)
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
        print(
            f"no dangling references with at least {args.min_references} citations",
            file=sys.stderr,
        )
        return 0

    today = date.today().isoformat()
    out_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else vault / "Projects" / "blueprint-os" / "drafts" / today
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    business = load_business_context(vault)

    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set. Either export it or pass --dry-run.", file=sys.stderr)
        return 2

    index_lines = [
        "---",
        "type: drafts-index",
        f"date: {today}",
        "project: Blueprint-OS",
        "status: review",
        "tags: [drafts, knowledge-graph, self-evolving, review-queue]",
        "---",
        "",
        f"## Drafts queue {today}",
        "",
        f"{len(ranked)} concept(s) drafted by `note_drafter.py`, ordered by reference count. "
        "Each is a dangling reference in the current graph: cited repeatedly but with no canonical "
        "file. Review the draft, edit voice or facts as needed, then move to the suggested target. "
        "Re-run [[Projects/blueprint-os/src/vault_graph|the graph engine]] afterwards to confirm the "
        "gap has closed.",
        "",
        "| # | Concept | Refs | Suggested target | Draft |",
        "|---|---|---|---|---|",
    ]

    written = 0
    for i, (concept, refs_count) in enumerate(ranked, 1):
        refs = find_references(concept, vault)
        related = find_related_concepts(refs, concept)
        prompt = build_prompt(concept, refs, related, business)
        target = suggest_target(concept, vault)
        filename = safe_filename(concept)
        draft_path = out_dir / filename

        print(f"  [{i}/{len(ranked)}] {concept} (cited {refs_count}x)", file=sys.stderr)

        if args.dry_run:
            content = render_dryrun_stub(concept, prompt)
        else:
            try:
                content = call_claude(prompt, args.model)
            except Exception as exc:
                print(f"    LLM error: {exc}", file=sys.stderr)
                continue

        draft_path.write_text(content + "\n", encoding="utf-8")
        written += 1
        index_lines.append(
            f"| {i} | [[{concept}]] | {refs_count} | `{target}` | "
            f"[[Projects/blueprint-os/drafts/{today}/{Path(filename).stem}|draft]] |"
        )

    (out_dir / "INDEX.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(
        f"drafts -> {out_dir} ({written} drafts + INDEX.md)"
        + (" (dry-run)" if args.dry_run else ""),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
