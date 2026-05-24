#!/usr/bin/env python3
"""LLM-based wikilink enricher. Catches synonyms and contextual references.

The mechanical enricher (`wikilink_enricher.py`) only matches exact note
titles. This script asks Claude to read each note in the context of the
vault's full title list and propose wikilinks for spans that:

  - Use a synonym ("the ERP" -> [[STORIS]])
  - Use a partial / informal name ("Scott" -> [[Scott — Goals & Priorities]])
  - Make a contextual reference an exact-match scan would miss

Output goes to a review queue. `--apply` injects the changes using the
display-text wikilink form `[[Target|original phrase]]` so the prose stays
readable.

Run the mechanical enricher first; this script is for the gap that remains.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from textwrap import dedent

try:
    from anthropic import Anthropic  # type: ignore
except ImportError:
    Anthropic = None

MODEL_DEFAULT = "claude-sonnet-4-6"

# Same skip rules as the mechanical enricher and the graph engine.
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

PROTECTED_RE = re.compile(
    r"(```[\s\S]*?```|`[^`\n]+`|\[\[[^\]\n]+\]\]|\[[^\]\n]+\]\([^)\n]+\))"
)
FRONTMATTER_RE = re.compile(r"\A---\n[\s\S]*?\n---\n")

# Trim long notes to keep prompts bounded. Most useful context is at the top.
MAX_NOTE_CHARS = 6000

SYSTEM_PROMPT = (
    "You identify places in a markdown note where the prose mentions another concept "
    "in the operator's knowledge vault by synonym or contextual reference, and could "
    "be enriched with an Obsidian wikilink. You output strictly valid JSON. You are "
    "conservative: only propose links you are confident about. Never propose to wrap "
    "text that is already inside a wikilink or code block. Never use em dashes."
)


@dataclass
class Suggestion:
    source_file: str
    line_number: int
    original_text: str
    target_title: str
    reason: str
    confidence: str  # high | medium | low


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


def split_body(text: str) -> tuple[str, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return "", text
    return text[: m.end()], text[m.end():]


def tokenize_for_search(body: str) -> list[tuple[str, bool, int]]:
    """Split body into (segment, is_protected, body_offset) triples."""
    out: list[tuple[str, bool, int]] = []
    last = 0
    for m in PROTECTED_RE.finditer(body):
        if m.start() > last:
            out.append((body[last: m.start()], False, last))
        out.append((m.group(0), True, m.start()))
        last = m.end()
    if last < len(body):
        out.append((body[last:], False, last))
    return out


def find_first_prose_occurrence(body: str, phrase: str) -> int | None:
    """Find the first occurrence of `phrase` in prose (skipping protected regions)."""
    tokens = tokenize_for_search(body)
    for segment, protected, offset in tokens:
        if protected:
            continue
        idx = segment.find(phrase)
        if idx != -1:
            return offset + idx
    return None


def offset_to_line(body: str, offset: int) -> int:
    return body.count("\n", 0, offset) + 1


def build_prompt(note_path: str, body: str, titles: list[str], own_title: str, max_suggestions: int) -> str:
    body_for_prompt = body[:MAX_NOTE_CHARS]
    titles_block = "\n".join(f"- {t}" for t in titles if t != own_title)
    truncated_note = "\n\n(note continues; truncated for prompt)" if len(body) > MAX_NOTE_CHARS else ""
    return dedent(f"""\
        ## Vault concept titles you can link to

        {titles_block}

        ## Note being reviewed

        Path: `{note_path}`

        ```
        {body_for_prompt}{truncated_note}
        ```

        ## Task

        Identify up to {max_suggestions} places in the note's prose where a span of text would benefit from an Obsidian wikilink to one of the vault concept titles above.

        Only propose a link if:
        - The span is a synonym or contextual reference for the target title (not just an exact title match. Those have already been handled.)
        - The span is in prose, NOT inside a code block, NOT inside an existing `[[wikilink]]`, NOT inside a markdown `[link](url)`.
        - You are confident the link is correct. When in doubt, skip.
        - The target title is in the list above. Never invent a title.

        Span rules (strict):
        - The `original_text` span MUST be 5 words or fewer. Prefer 1 to 3 words.
        - NEVER wrap a full sentence or clause.
        - The span MUST NOT include markdown formatting characters such as `**`, `*`, `_`, backticks, `#`, `>`, or hyphen list markers. If the candidate phrase is formatted, choose the inner plain text, not the formatted span.
        - The span MUST be a noun or noun phrase that names the target concept. Skip verbs and full clauses.

        For each suggestion, return the EXACT verbatim span of text from the note (case and punctuation preserved) so it can be located precisely.

        Output strictly valid JSON in this shape, nothing else:

        {{
          "suggestions": [
            {{
              "original_text": "the exact span from the note",
              "target_title": "Exact Title From The List Above",
              "reason": "one short sentence",
              "confidence": "high"
            }}
          ]
        }}

        If no suggestions apply, return `{{"suggestions": []}}`.
        """)


def call_claude(prompt: str, model: str) -> dict:
    if Anthropic is None:
        raise RuntimeError("anthropic SDK not installed.")
    client = Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl + 1:]
        if text.endswith("```"):
            text = text[: text.rfind("```")].rstrip()
    return json.loads(text)


def apply_suggestions_to_body(body: str, located: list[tuple[int, str, str]]) -> tuple[str, int]:
    """Apply suggestions right-to-left. located is [(offset, original_text, target)]."""
    out = body
    count = 0
    # Sort by offset descending so earlier offsets are still valid after right-edge replacements.
    for offset, original, target in sorted(located, key=lambda x: -x[0]):
        end = offset + len(original)
        if out[offset:end] != original:
            continue
        out = out[:offset] + f"[[{target}|{original}]]" + out[end:]
        count += 1
    return out, count


def process_file(
    md_file: Path,
    vault: Path,
    titles: list[str],
    model: str,
    max_suggestions_per_note: int,
    dry_run: bool,
) -> tuple[list[Suggestion], list[tuple[int, str, str]]]:
    """Return (suggestions for review queue, located edits for apply)."""
    rel = str(md_file.relative_to(vault))
    text = md_file.read_text(encoding="utf-8", errors="ignore")
    _, body = split_body(text)
    if not body.strip():
        return [], []

    prompt = build_prompt(rel, body, titles, md_file.stem, max_suggestions_per_note)

    if dry_run:
        return [], []

    try:
        result = call_claude(prompt, model)
    except json.JSONDecodeError as exc:
        print(f"    LLM JSON parse error on {rel}: {exc}", file=sys.stderr)
        return [], []
    except Exception as exc:
        print(f"    LLM call error on {rel}: {exc}", file=sys.stderr)
        return [], []

    raw_suggestions = result.get("suggestions", []) or []
    suggestions: list[Suggestion] = []
    located: list[tuple[int, str, str]] = []
    seen_targets: set[str] = set()
    titles_set = set(titles)
    dropped_reasons: dict[str, int] = defaultdict(int)

    BAD_MARKDOWN_CHARS = ("**", "*", "_", "`", "#", ">")

    for s in raw_suggestions:
        original = s.get("original_text", "").strip()
        target = s.get("target_title", "").strip()
        reason = s.get("reason", "").strip()
        confidence = s.get("confidence", "medium").strip().lower()
        if not original or not target:
            dropped_reasons["empty"] += 1
            continue
        if target not in titles_set:
            dropped_reasons["unknown_target"] += 1
            continue
        # Span hygiene: max 5 words, no markdown formatting characters.
        word_count = len(original.split())
        if word_count > 5:
            dropped_reasons["span_too_long"] += 1
            continue
        if any(ch in original for ch in BAD_MARKDOWN_CHARS):
            dropped_reasons["markdown_chars"] += 1
            continue
        # First occurrence in prose only.
        offset = find_first_prose_occurrence(body, original)
        if offset is None:
            dropped_reasons["not_in_prose"] += 1
            continue
        # Dedupe within this file: one wikilink per target.
        if target in seen_targets:
            dropped_reasons["dup_target"] += 1
            continue
        seen_targets.add(target)
        line_num = offset_to_line(body, offset)
        suggestions.append(
            Suggestion(
                source_file=rel,
                line_number=line_num,
                original_text=original,
                target_title=target,
                reason=reason,
                confidence=confidence,
            )
        )
        located.append((offset, original, target))

    if raw_suggestions:
        kept = len(suggestions)
        dropped = len(raw_suggestions) - kept
        if dropped:
            reasons = ", ".join(f"{k}={v}" for k, v in dropped_reasons.items())
            print(f"    raw={len(raw_suggestions)} kept={kept} dropped={dropped} ({reasons})", file=sys.stderr)
    return suggestions, located


def file_relative_orphan_priority(md_file: Path, body: str) -> int:
    """Heuristic: rank files for processing. Larger bodies, fewer existing wikilinks, processed first."""
    existing_links = body.count("[[")
    return len(body) - existing_links * 200


def render_review_queue(
    vault: Path,
    suggestions: list[Suggestion],
    files_processed: int,
    applied: bool,
) -> str:
    today = date.today().isoformat()
    grouped: dict[str, list[Suggestion]] = defaultdict(list)
    for s in suggestions:
        grouped[s.source_file].append(s)

    lines: list[str] = [
        "---",
        "type: wikilink-llm-enrichment-review",
        f"date: {today}",
        "project: Blueprint-OS",
        f"status: {'applied' if applied else 'review'}",
        "tags: [wikilinks, enrichment, llm, knowledge-graph, review-queue]",
        "---",
        "",
        "> [!info] What this is",
        f"> LLM-proposed wikilinks for synonyms and contextual references that the "
        f"mechanical enricher cannot catch. {len(suggestions)} suggestions across "
        f"{len(grouped)} files (out of {files_processed} files processed). "
        + (
            "These changes have been APPLIED (`.bak` backups next to each modified file)."
            if applied
            else "No files have been modified. Run with `--apply` to inject keepers."
        ),
        "",
        "Each suggestion proposes wrapping the original text as a display-text wikilink: "
        "`[[Target Title|original text]]`. The prose stays readable; the link resolves to "
        "the target.",
        "",
        "## How to use",
        "",
        "1. Review each suggestion. Filter aggressively. False positives are expensive.",
        "2. Edit `NOISE_TITLES` in the script if you find generic targets to skip globally.",
        "3. Re-run with `--apply` when you trust the suggestions.",
        "4. Re-run `vault_graph.py` afterwards to see the orphan rate drop.",
        "",
        "## Suggestions by file",
        "",
    ]

    for source_file in sorted(grouped.keys()):
        ss = grouped[source_file]
        lines.append(f"### `{source_file}` ({len(ss)} suggestion(s))")
        lines.append("")
        for s in ss:
            badge = {"high": "🟢", "medium": "🟡", "low": "🔵"}.get(s.confidence, "")
            lines.append(
                f"- {badge} L{s.line_number}: wrap `{s.original_text}` as "
                f"`[[{s.target_title}|{s.original_text}]]`  \n"
                f"  *Why:* {s.reason}"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--vault", required=True)
    parser.add_argument("--output", help="Path for the review queue markdown. Default: <vault>/Reports/knowledge-graph/wikilink-llm-enrichment-review-<date>.md")
    parser.add_argument("--apply", action="store_true", help="Inject suggestions into the source files with .bak backups.")
    parser.add_argument("--max-suggestions-per-note", type=int, default=5)
    parser.add_argument("--max-files", type=int, default=50, help="Cap files processed in one run (cost guard).")
    parser.add_argument("--only-orphans", action="store_true", help="Process only files that have no incoming or outgoing wikilinks. Highest leverage.")
    parser.add_argument("--model", default=MODEL_DEFAULT)
    parser.add_argument("--dry-run", action="store_true", help="Skip LLM calls, just enumerate candidate files.")
    args = parser.parse_args(argv)

    vault = Path(args.vault).expanduser().resolve()
    if not vault.is_dir():
        print(f"vault path not a directory: {vault}", file=sys.stderr)
        return 2

    titles = collect_titles(vault)
    print(f"vault titles available as targets: {len(titles)}", file=sys.stderr)

    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set. Either export it or pass --dry-run.", file=sys.stderr)
        return 2

    # Enumerate candidate files; optionally filter to orphans for cost focus.
    candidates: list[Path] = []
    for md_file in sorted(vault.rglob("*.md")):
        if should_skip_file(md_file, vault):
            continue
        if args.only_orphans:
            try:
                text = md_file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            _, body = split_body(text)
            if "[[" in body:
                continue
        candidates.append(md_file)

    candidates = candidates[: args.max_files]
    print(f"candidate files: {len(candidates)}", file=sys.stderr)

    if args.dry_run:
        print("(dry run: would have called Claude for each of the above)", file=sys.stderr)
        # Still produce a stub review queue so the workflow is observable.
        review_md = render_review_queue(vault, [], len(candidates), applied=False)
        output = (
            Path(args.output).expanduser().resolve()
            if args.output
            else vault / "Reports" / "knowledge-graph" / f"wikilink-llm-enrichment-review-{date.today().isoformat()}.md"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(review_md, encoding="utf-8")
        print(f"review queue (dry-run, empty) -> {output}", file=sys.stderr)
        return 0

    all_suggestions: list[Suggestion] = []
    files_touched = 0
    total_applied = 0

    for i, md_file in enumerate(candidates, 1):
        rel = str(md_file.relative_to(vault))
        print(f"  [{i}/{len(candidates)}] {rel}", file=sys.stderr)
        suggestions, located = process_file(
            md_file, vault, titles, args.model, args.max_suggestions_per_note, dry_run=False
        )
        if not suggestions:
            continue
        all_suggestions.extend(suggestions)
        files_touched += 1
        if args.apply:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
            frontmatter, body = split_body(text)
            new_body, applied = apply_suggestions_to_body(body, located)
            if applied:
                backup = md_file.with_suffix(md_file.suffix + ".bak")
                shutil.copy2(md_file, backup)
                md_file.write_text(frontmatter + new_body, encoding="utf-8")
                total_applied += applied
                print(f"    applied: {applied} wikilinks (backup at {backup.name})", file=sys.stderr)

    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else vault / "Reports" / "knowledge-graph" / f"wikilink-llm-enrichment-review-{date.today().isoformat()}.md"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    review_md = render_review_queue(vault, all_suggestions, len(candidates), applied=args.apply)
    output.write_text(review_md, encoding="utf-8")
    print(
        f"review queue -> {output}\n"
        f"summary: {len(all_suggestions)} suggestions across {files_touched} files"
        + (f"; applied {total_applied} wikilinks" if args.apply else ""),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
