#!/usr/bin/env python3
"""Prepare LLM-enrichment task files for the agent (no API key required).

Walks orphan files in the vault, packages each one's body content plus the
list of available wikilink targets into per-file task blocks the agent can
process using its own Claude Code subscription. The agent identifies
synonym and contextual wikilink injection points and writes a review queue.

This replaces the prior `wikilink_enricher_llm.py` which called the
Anthropic API directly.

Output: `Reports/knowledge-graph/wikilink-llm-tasks-YYYY-MM-DD.md`
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

SKIP_DIR_PREFIXES = (".obsidian", ".trash", ".git")
SKIP_DIR_NAMES = {"corpora", "reports", "drafts", "output", "Reports", "Excalidraw", "raw"}
SKIP_FILENAMES = {"CLAUDE.md", "GEMINI.md", "AGENTS.md"}

NOISE_TITLES = {
    "Welcome", "Home", "README", "Readme", "Index", "Untitled",
    "Note", "Notes", "Draft", "Drafts", "INDEX", "Inbox",
    "New File", "Untitled 1", "Untitled 2", "Untitled 3",
    "Untitled 4", "Untitled 5", "Untitled 6", "Untitled 7", "Untitled 8",
    "create a link", "test", "Test",
}

FRONTMATTER_RE = re.compile(r"\A---\n[\s\S]*?\n---\n")

MAX_NOTE_CHARS = 6000


def should_skip_file(md_file: Path, vault: Path) -> bool:
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


def is_useful_title(title: str) -> bool:
    if title in NOISE_TITLES:
        return False
    if len(title) < 4 and not title.isupper():
        return False
    if re.match(r"^\d{4}-\d{2}-\d{2}$", title):
        return False
    if title.isdigit():
        return False
    return True


def collect_titles(vault: Path) -> list[str]:
    titles: set[str] = set()
    for md_file in vault.rglob("*.md"):
        if should_skip_file(md_file, vault):
            continue
        stem = md_file.stem
        if is_useful_title(stem):
            titles.add(stem)
    return sorted(titles)


def split_body(text: str) -> str:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return text
    return text[m.end():]


def is_orphan(body: str) -> bool:
    return "[[" not in body


def collect_candidate_files(vault: Path, only_orphans: bool, max_files: int) -> list[Path]:
    candidates: list[Path] = []
    for md_file in sorted(vault.rglob("*.md")):
        if should_skip_file(md_file, vault):
            continue
        if only_orphans:
            try:
                text = md_file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            body = split_body(text)
            if not is_orphan(body):
                continue
        candidates.append(md_file)
        if len(candidates) >= max_files:
            break
    return candidates


def render_task_file(
    vault: Path,
    candidate_files: list[Path],
    titles: list[str],
    today: str,
    max_suggestions_per_note: int,
) -> str:
    lines: list[str] = []
    lines.append("---")
    lines.append("type: wikilink-llm-enrichment-tasks")
    lines.append(f"date: {today}")
    lines.append("project: Blueprint-OS")
    lines.append("status: ready-for-agent")
    lines.append("tags: [knowledge-graph, wikilinks, enrichment, agent-task, os-evolver]")
    lines.append("---")
    lines.append("")
    lines.append("> [!info] How to process this file")
    lines.append(">")
    lines.append("> Below are orphan files (no inbound or outbound wikilinks) from the vault, plus")
    lines.append("> the list of valid wikilink targets. For each file section, identify up to")
    lines.append(f"> {max_suggestions_per_note} spans of prose where a wikilink to one of the listed targets")
    lines.append("> would make sense as a synonym or contextual reference.")
    lines.append(">")
    lines.append("> **Output file:** `Reports/knowledge-graph/wikilink-llm-enrichment-review-" + today + ".md`")
    lines.append(">")
    lines.append("> **Output format:** review queue grouped by source file. Each suggestion shows")
    lines.append("> the span, the proposed target, and the reason. The operator skims and approves.")
    lines.append(">")
    lines.append("> **Span rules (strict):**")
    lines.append("> - The original span MUST be 5 words or fewer. Prefer 1 to 3 words.")
    lines.append("> - Span MUST NOT contain markdown formatting characters (`*`, `_`, backticks, `#`, `>`).")
    lines.append("> - Span MUST NOT already be inside an existing `[[wikilink]]` or markdown link.")
    lines.append("> - Span MUST be a noun or short noun phrase, not a sentence or clause.")
    lines.append("> - One wikilink per target per file (dedupe).")
    lines.append("> - Skip generic words. When in doubt, skip.")
    lines.append(">")
    lines.append("> **Replacement form:** when approved, the wikilink wraps the original span as")
    lines.append("> `[[Target Title|original span]]`. Display text stays readable; navigation resolves to the target.")
    lines.append(">")
    lines.append("> **Never use em dashes in the review queue.** Periods, commas, or colons only.")
    lines.append("")

    lines.append("## Valid wikilink targets")
    lines.append("")
    lines.append("Only suggest links to titles in this list. Never invent a new title.")
    lines.append("")
    lines.append(", ".join(f"`{t}`" for t in titles))
    lines.append("")
    lines.append("---")
    lines.append("")

    if not candidate_files:
        lines.append("## No candidate files")
        lines.append("")
        lines.append("_No orphan files matched the filters. Re-run without `--only-orphans` to process linked files too._")
        lines.append("")
        return "\n".join(lines) + "\n"

    lines.append(f"## {len(candidate_files)} orphan file(s) to enrich")
    lines.append("")

    for i, md_file in enumerate(candidate_files, 1):
        rel = str(md_file.relative_to(vault))
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        body = split_body(text)
        truncated = len(body) > MAX_NOTE_CHARS
        body_for_agent = body[:MAX_NOTE_CHARS]

        lines.append(f"### File {i}: `{rel}`")
        lines.append("")
        if truncated:
            lines.append(f"_(content truncated to first {MAX_NOTE_CHARS} characters)_")
            lines.append("")
        lines.append("```")
        lines.append(body_for_agent.rstrip())
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--vault", required=True, help="Vault root.")
    parser.add_argument("--output", help="Output task file path.")
    parser.add_argument("--only-orphans", action="store_true", help="Only include files with no existing wikilinks (highest leverage).")
    parser.add_argument("--max-files", type=int, default=30, help="Cap number of files in the task file.")
    parser.add_argument("--max-suggestions-per-note", type=int, default=4)
    args = parser.parse_args(argv)

    vault = Path(args.vault).expanduser().resolve()
    if not vault.is_dir():
        print(f"vault path not a directory: {vault}", file=sys.stderr)
        return 2

    titles = collect_titles(vault)
    print(f"vault titles available as link targets: {len(titles)}", file=sys.stderr)
    candidates = collect_candidate_files(vault, args.only_orphans, args.max_files)
    print(f"candidate files queued for agent review: {len(candidates)}", file=sys.stderr)

    today = date.today().isoformat()
    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else vault / "Reports" / "knowledge-graph" / f"wikilink-llm-tasks-{today}.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_task_file(vault, candidates, titles, today, args.max_suggestions_per_note),
        encoding="utf-8",
    )

    print(f"task file -> {output_path}", file=sys.stderr)
    print("", file=sys.stderr)
    print("NEXT: invoke the agent to read this file and produce the review queue.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
