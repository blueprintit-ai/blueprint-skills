#!/usr/bin/env python3
"""Auto-enrich a wikilink-sparse vault with [[wikilinks]] to existing notes.

For each note in the vault, find the first whole-word, plain-text mention of
every OTHER note's title and wrap it as a wikilink. Skip text inside code
fences, inline code, existing wikilinks, and markdown links so we never
double-link or corrupt code.

Default mode writes a markdown review queue. Pass `--apply` to actually
modify the files (with .bak backups). Idempotent: a second --apply run
finds nothing new because matches are already wikilinks.

This is the onboarding step for the Karpathy / Nodus self-evolving loop on
a fresh client vault. Without it, vaults that lack wikilinks produce empty
graphs and the loop has nothing to work on.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

SKIP_DIR_PREFIXES = (".obsidian", ".trash", ".git")
SKIP_DIR_NAMES = {"corpora", "reports", "drafts", "output", "Reports", "Excalidraw"}
SKIP_FILENAMES = {"CLAUDE.md", "GEMINI.md", "AGENTS.md"}

# Titles that are too generic to be useful wikilink targets.
NOISE_TITLES = {
    "Welcome", "Home", "README", "Readme", "Index", "Untitled",
    "Note", "Notes", "Draft", "Drafts", "INDEX", "Inbox",
    "New File", "Untitled 1", "Untitled 2", "Untitled 3",
    "Untitled 4", "Untitled 5", "Untitled 6", "Untitled 7", "Untitled 8",
    "create a link", "test", "Test",
}

# Region patterns we must NOT alter or match inside.
# Order: fenced code first (greedy multiline), then inline code, then existing wikilinks, then md links.
PROTECTED_RE = re.compile(
    r"(```[\s\S]*?```|`[^`\n]+`|\[\[[^\]\n]+\]\]|\[[^\]\n]+\]\([^)\n]+\))"
)

# Detect frontmatter so we can leave it alone.
FRONTMATTER_RE = re.compile(r"\A---\n[\s\S]*?\n---\n")

# Headings we will not enrich (the heading IS the topic, no need to link to self/another).
HEADING_RE = re.compile(r"^#{1,6}\s.*$", re.MULTILINE)


@dataclass
class Proposal:
    source_file: str       # relative to vault
    target_title: str
    line_number: int       # 1-indexed line in source_file
    context_before: str    # ~60 chars before match in the line
    matched_text: str      # the actual matched substring (may differ in case if we ever go case-insensitive)
    context_after: str     # ~60 chars after


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
    # Short and not an obvious acronym -> skip.
    if len(title) < 4 and not (title.isupper() or re.match(r"^[A-Z]{2,}$", title)):
        return False
    # Pure number strings or dates (YYYY-MM-DD) are noisy as wikilink targets.
    if re.match(r"^\d{4}-\d{2}-\d{2}$", title):
        return False
    if title.isdigit():
        return False
    return True


def collect_titles(vault: Path) -> list[tuple[str, Path]]:
    titles: list[tuple[str, Path]] = []
    for md_file in vault.rglob("*.md"):
        if should_skip_file(md_file, vault):
            continue
        title = md_file.stem
        if is_useful_title(title):
            titles.append((title, md_file))
    # Longer titles first so "CDF Smart System" matches before "CDF".
    titles.sort(key=lambda x: -len(x[0]))
    return titles


def split_body(text: str) -> tuple[str, str]:
    """Return (frontmatter, body). Frontmatter empty if none."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return "", text
    return text[: m.end()], text[m.end():]


def tokenize_for_enrichment(body: str) -> list[tuple[str, bool]]:
    """Split body into (segment, is_protected) tokens."""
    tokens: list[tuple[str, bool]] = []
    last = 0
    for m in PROTECTED_RE.finditer(body):
        if m.start() > last:
            tokens.append((body[last: m.start()], False))
        tokens.append((m.group(0), True))
        last = m.end()
    if last < len(body):
        tokens.append((body[last:], False))
    return tokens


def find_first_match(
    prose: str, target: str, prose_offset_in_body: int, include_headings: bool
) -> int | None:
    """Return the absolute offset of the first whole-word match in prose, or None."""
    # Whole-word boundary. Title may contain spaces and special chars -> escape.
    pattern = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(target) + r"(?![A-Za-z0-9_])")
    for m in pattern.finditer(prose):
        abs_pos = m.start()
        if not include_headings:
            # Check whether this match falls inside a heading line.
            line_start = prose.rfind("\n", 0, abs_pos) + 1
            line_end = prose.find("\n", abs_pos)
            line_end = line_end if line_end != -1 else len(prose)
            line = prose[line_start:line_end]
            if line.lstrip().startswith("#"):
                continue
        return prose_offset_in_body + abs_pos
    return None


def find_proposals_in_body(
    body: str,
    own_title: str,
    other_titles: list[str],
    include_headings: bool,
    max_per_note: int,
) -> list[tuple[int, str]]:
    """Find (offset_in_body, target_title) proposals.

    Walks the prose tokens (skipping protected regions). One match per target
    per source note (first occurrence). Returns offsets sorted ascending so
    callers can replace right-to-left.
    """
    tokens = tokenize_for_enrichment(body)
    found: list[tuple[int, str]] = []
    seen_targets: set[str] = set()
    for target in other_titles:
        if target == own_title or target in seen_targets:
            continue
        cursor = 0
        chosen_offset: int | None = None
        for segment, protected in tokens:
            if protected:
                cursor += len(segment)
                continue
            offset = find_first_match(segment, target, cursor, include_headings)
            if offset is not None:
                chosen_offset = offset
                break
            cursor += len(segment)
        if chosen_offset is not None:
            found.append((chosen_offset, target))
            seen_targets.add(target)
        if len(found) >= max_per_note:
            break
    found.sort()
    return found


def offset_to_line(body: str, offset: int) -> tuple[int, str]:
    """Return (1-indexed line number, the line content) for an offset in body."""
    line_start = body.rfind("\n", 0, offset) + 1
    line_end = body.find("\n", offset)
    line_end = line_end if line_end != -1 else len(body)
    line = body[line_start:line_end]
    line_number = body.count("\n", 0, offset) + 1
    return line_number, line


def context_window(body: str, offset: int, target_len: int, span: int = 60) -> tuple[str, str, str]:
    start = max(0, offset - span)
    end = min(len(body), offset + target_len + span)
    return (
        body[start:offset].replace("\n", " "),
        body[offset:offset + target_len],
        body[offset + target_len:end].replace("\n", " "),
    )


def apply_proposals(body: str, proposals: list[tuple[int, str]]) -> tuple[str, int]:
    """Apply wikilink wrappings right-to-left. Returns (new_body, count_applied)."""
    out = body
    count = 0
    for offset, target in reversed(proposals):
        end = offset + len(target)
        if out[offset:end] != target:
            # Defensive: the body changed since we computed offsets (shouldn't happen).
            continue
        out = out[:offset] + f"[[{target}]]" + out[end:]
        count += 1
    return out, count


def process_vault(
    vault: Path,
    include_headings: bool,
    max_per_note: int,
    apply: bool,
) -> tuple[list[Proposal], dict[str, int]]:
    titles = collect_titles(vault)
    title_to_path = {t: p for t, p in titles}
    just_titles = [t for t, _ in titles]
    proposals: list[Proposal] = []
    counts: dict[str, int] = defaultdict(int)

    for source_title, source_path in titles:
        rel = str(source_path.relative_to(vault))
        try:
            text = source_path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"  skip {rel}: {exc}", file=sys.stderr)
            continue
        frontmatter, body = split_body(text)

        other_titles = [t for t in just_titles if t != source_title]
        body_proposals = find_proposals_in_body(
            body, source_title, other_titles, include_headings, max_per_note
        )
        if not body_proposals:
            continue

        for offset, target in body_proposals:
            line_num, _ = offset_to_line(body, offset)
            before, matched, after = context_window(body, offset, len(target))
            proposals.append(
                Proposal(
                    source_file=rel,
                    target_title=target,
                    line_number=line_num,
                    context_before=before,
                    matched_text=matched,
                    context_after=after,
                )
            )

        counts[rel] = len(body_proposals)

        if apply:
            new_body, applied = apply_proposals(body, body_proposals)
            if applied:
                backup = source_path.with_suffix(source_path.suffix + ".bak")
                shutil.copy2(source_path, backup)
                source_path.write_text(frontmatter + new_body, encoding="utf-8")

    return proposals, dict(counts)


def render_review_queue(
    vault: Path,
    proposals: list[Proposal],
    counts: dict[str, int],
    titles_count: int,
    applied: bool,
) -> str:
    today = date.today().isoformat()
    total_proposals = len(proposals)
    files_with_proposals = len(counts)

    lines: list[str] = [
        "---",
        "type: wikilink-enrichment-review",
        f"date: {today}",
        "project: Blueprint-OS",
        f"status: {'applied' if applied else 'review'}",
        "tags: [wikilinks, enrichment, knowledge-graph, review-queue]",
        "---",
        "",
        "> [!info] What this is",
        f"> Auto-detected wikilink injection points across the vault, generated by "
        f"`wikilink_enricher.py`. {total_proposals} proposed wikilinks across "
        f"{files_with_proposals} files, drawn from {titles_count} candidate note titles. "
        + (
            "These changes have been APPLIED (backups at `.bak` next to each modified file)."
            if applied
            else "No files have been modified yet. Run with `--apply` to inject the keepers."
        ),
        "",
        "## How to use this",
        "",
        "1. Skim each file's proposed links below.",
        "2. For each file: if all proposals look correct, great. If not, decide whether to apply, edit, or skip.",
        "3. Re-run in `--apply` mode when you trust the suggestions: `python3 src/wikilink_enricher.py --vault '...' --apply`",
        "4. Re-run [[Projects/blueprint-os/src/vault_graph|vault_graph.py]] afterwards. The graph should grow from a wikilink-sparse star into a real network.",
        "",
        "## Proposals by file",
        "",
    ]

    grouped: dict[str, list[Proposal]] = defaultdict(list)
    for p in proposals:
        grouped[p.source_file].append(p)

    for source_file in sorted(grouped.keys()):
        ps = grouped[source_file]
        lines.append(f"### `{source_file}` ({len(ps)} proposed)")
        lines.append("")
        for p in ps:
            arrow_before = p.context_before.strip()
            arrow_after = p.context_after.strip()
            lines.append(
                f"- L{p.line_number}: link [[{p.target_title}]] "
                f"  \n  `…{arrow_before} `**`{p.matched_text}`**` {arrow_after}…`"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--vault", required=True, help="Vault root.")
    parser.add_argument("--output", help="Path to write the review queue markdown. Default: <vault>/Reports/knowledge-graph/wikilink-enrichment-review-<date>.md")
    parser.add_argument("--apply", action="store_true", help="Actually modify the files (with .bak backups). Default: review-only.")
    parser.add_argument("--include-headings", action="store_true", help="Also enrich matches inside headings. Default: skipped.")
    parser.add_argument("--max-per-note", type=int, default=20, help="Cap proposals per note.")
    args = parser.parse_args(argv)

    vault = Path(args.vault).expanduser().resolve()
    if not vault.is_dir():
        print(f"vault path not a directory: {vault}", file=sys.stderr)
        return 2

    titles = collect_titles(vault)
    print(f"candidate titles: {len(titles)}", file=sys.stderr)
    if not titles:
        print("no useful titles to link against", file=sys.stderr)
        return 0

    proposals, counts = process_vault(
        vault,
        include_headings=args.include_headings,
        max_per_note=args.max_per_note,
        apply=args.apply,
    )
    print(f"proposals: {len(proposals)} across {len(counts)} files", file=sys.stderr)

    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else vault / "Reports" / "knowledge-graph" / f"wikilink-enrichment-review-{date.today().isoformat()}.md"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    review_md = render_review_queue(vault, proposals, counts, len(titles), applied=args.apply)
    output.write_text(review_md, encoding="utf-8")
    print(f"review queue -> {output}", file=sys.stderr)
    if args.apply:
        print(f"applied: {sum(counts.values())} wikilinks across {len(counts)} files (.bak backups created)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
