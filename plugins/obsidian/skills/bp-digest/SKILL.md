---
name: bp-digest
description: Process every file in the vault's Raw/ inbox. For each file, read its contents, decide where it belongs in the vault based on CLAUDE.md routing conventions, write a structured summary note in the right place, and move the original to Raw/processed/ so the inbox stays clean. Report back what was done. TRIGGERS: os digest, digest raw, digest inbox, process raw, process inbox, ingest files, file my materials, what is in raw, empty the inbox, clean up raw, digest my files. Run from the vault root.
---

# OS Digest

Sweep the vault's `Raw/` inbox. Read every file, decide where it belongs, summarize, file, archive. Report back.

This is the workflow customers run to feed materials into their vault. A cabinet shop drops a supplier price list, a customer contract, photos of a finished job, a phone-call transcript into `Raw/`. They type `/bp-digest`. The agent reads each file, classifies it against the vault's CLAUDE.md routing, writes a structured note in the right folder, moves the original to `Raw/processed/`, and surfaces a report.

## Pre-flight

1. Verify the current working directory is a vault root: `CLAUDE.md` or `claude.md` must exist. If missing: tell the user *"This is not a vault root. `cd` into your vault and re-run."* Stop.
2. Verify `Raw/` exists at the vault root. If missing: create it (`mkdir -p Raw/processed`) and tell the user *"Created your `Raw/` inbox at vault root. Drop files there and re-run `/bp-digest`."* Stop.
3. Read the vault's root `CLAUDE.md` to learn the routing conventions. The customer's routing rules live there.

## Phase 0 — Inventory

List the contents of `Raw/` excluding the `processed/` subdirectory and excluding `README.md`. Use `ls Raw/` or equivalent.

If empty, tell the user *"Your Raw/ inbox is empty. Drop files there and run /bp-digest again."* Stop.

Otherwise, show the user the file list and confirm: *"Found N files in Raw/. About to process. Proceed?"* Use `AskUserQuestion` if more than 10 files. For small batches (≤10) just announce and proceed.

## Phase 1 — Classify and route each file

For each file, in alphabetical order:

1. **Read the file.**
   - Plain text, markdown, images: use the `Read` tool directly.
   - PDFs: follow the **PDF reading protocol** below.
   - Audio files (`.m4a`, `.mp3`, `.wav`): invoke the `audio-transcriber` skill via the `Skill` tool to get a transcript first. If `audio-transcriber` is not installed, skip the file and flag it in the report.
   - Spreadsheets (`.xlsx`, `.csv`): follow the **xlsx reading protocol** below. For `.csv`, use the `Read` tool directly.
   - Word docs (`.docx`): try the `Read` tool; if it returns binary garbage, flag in the report and skip.
   - Anything else: skip and flag.

**PDF reading protocol.** The `Read` tool requires a `pages` parameter for files over 10 pages. Always check first:

1. Run `pdfinfo "Raw/{filename}"` via Bash. Parse the `Pages:` line to get the page count.
   - If `pdfinfo` is not installed (command not found), default to reading pages `"1-10"` and note the assumption.
2. If page count is 10 or fewer: use `Read` with no `pages` parameter.
3. If page count is over 10: read in chunks — `pages: "1-10"`, then `"11-20"`, etc. — up to a maximum of 50 pages. Combine the content across chunks. If the file exceeds 50 pages, note in the report: "First 50 of N pages read — remainder not processed."
4. If the `Read` tool returns blank or no meaningful text (image-only PDF with no text layer): note in the report that it is image-based, describe what you can infer from the filename and any visible headers, and leave the original in `Raw/`.

**xlsx reading protocol.** The `Read` tool cannot parse binary `.xlsx` format. Use Python to extract the data:

1. Run via Bash:
   ```
   python3 -c "
   import openpyxl
   wb = openpyxl.load_workbook('Raw/{filename}', read_only=True, data_only=True)
   for name in wb.sheetnames:
       print('=== ' + name + ' ===')
       for row in wb[name].iter_rows(values_only=True):
           if any(c is not None for c in row):
               print(row)
   "
   ```
2. If `openpyxl` is not installed (ImportError), run `python3 -m pip install openpyxl -q` and retry step 1 once.
3. If Python3 is unavailable or the install fails: flag in the report and leave in `Raw/` with the note: "binary .xlsx — open in Excel and paste key data into a .md or .csv file, then re-run /bp-digest."

2. **Classify the content.** Based on what you read, decide what the file IS:
   - Customer contract or quote → goes into `Projects/{Customer Name}/`
   - Supplier price list → goes into `Resources/pricing/{supplier}-{period}.md`
   - Job photo → goes into `Projects/{Job Name}/photos/` with tags for material, style, room type
   - Phone call (transcript) → goes into `Projects/{Customer}/calls/{YYYY-MM-DD}.md`
   - SOP / training doc → goes into `Resources/sops/{topic}.md`
   - Internal financial doc → goes into `Resources/financials/` or similar
   - Anything else: use your judgment based on the routing table in the vault's `CLAUDE.md`.

3. **Write a structured note** to the chosen target path. The note should:
   - Have YAML frontmatter with `type`, `source` (the original filename), `ingested-at` (current date), and 2+ relevant `tags`.
   - Lead with a one-paragraph summary of what the source file is and why it matters.
   - Extract the key facts (prices, dates, names, terms, decisions) into a structured list or table.
   - Include `[[wikilinks]]` to related concepts the operator has already canonised in their vault (customers, suppliers, jobs, staff).
   - Reference the source file by name at the bottom: *"Source: `Raw/processed/{filename}`"*.

4. **Move the original file** from `Raw/` to `Raw/processed/`. Use `mv` via Bash or the appropriate filesystem operation. Do not delete; archive.

5. **Skip the file** (leaving it in Raw/) if any of these apply, and note in the report:
   - Cannot classify with confidence (multiple plausible homes, no clear winner)
   - File is corrupted, empty, or unreadable
   - File is a format we cannot process (e.g., a `.dwg` cabinet design file) — flag it as "needs human attention"

6. **Watch for collisions.** If the target path already exists:
   - If the existing file is on the same topic, append to it or create a dated suffix (`{name}-2026-05-25.md`)
   - Never silently overwrite an existing note

## Phase 2 — Report

Once all files are processed, write a summary report to chat. Use this exact shape so the customer can scan it quickly:

```
Processed N files from Raw/:

  ✓ {filename}  →  {target path}
  ✓ {filename}  →  {target path}
  ⚠ {filename}  →  left in Raw/, could not classify ({reason})
  ⚠ {filename}  →  left in Raw/, unsupported format ({extension})

{summary sentence about what was added to the vault}
```

Then ask: *"Anything land in the wrong place? Tell me which file and where it should have gone — I'll fix and learn the pattern."*

If the customer corrects a routing decision, remember it for this session and apply the same logic to the next batch.

## Hard rules

- Never delete a source file. Only move it to `Raw/processed/`.
- Never overwrite an existing vault note silently. Append, version, or pick a different filename.
- Never invent facts. If a price, date, or name is unclear in the source, write `(unclear from source)` in the note rather than guessing.
- Never skip the report. The customer needs to see what changed.
- Never use em dashes. Use periods, commas, or colons.

## After the digest

Recommend the user verify a couple of the new notes in Obsidian and approve. Once they trust the routing, future `/bp-digest` runs are largely autonomous.

If the inbox had ≥5 files of the same type (e.g., a batch of phone-call transcripts), point out the pattern and suggest the customer commit to a recurring habit: *"You added five phone-call transcripts this week. Want me to set up `/bp-operator` to remind you to drop new ones every Friday afternoon?"*

## Cross-references

- `/bp-setup` — bootstrap the vault. Run before this skill on a fresh vault.
- `/bp-operator` — schedule a recurring agent. Can be configured to remind the user to run `/bp-digest` weekly.
- `/bp-optimizer` — monthly vault audit. Catches files that ended up in the wrong place over time.
- The `audio-transcriber` skill — invoked automatically by `/bp-digest` when an audio file is in Raw/.

## Triggers

| User says | Run |
|---|---|
| `/bp-digest`, "digest raw", "digest the inbox" | Full digest workflow |
| "what's in Raw/" | List inventory, do not process |
| "process the X file in Raw/" | Digest only that file |
| "empty the inbox" | Full digest workflow with stronger autonomy (do not prompt on small batches) |
