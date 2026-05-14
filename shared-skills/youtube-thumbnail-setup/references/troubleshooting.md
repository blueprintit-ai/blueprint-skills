# Setup Troubleshooting

Failure modes specific to the setup flow. For generation-time failures (validation errors, content rejection, fake logos in output, style drift), see the generate skill's `troubleshooting.md`.

## Authentication

| Error | Cause | Fix |
|---|---|---|
| `Session expired` | MCP auth token aged out | Re-authenticate the Higgsfield MCP connector in Claude |
| `Not authenticated` | Never logged in | Authenticate the Higgsfield MCP connector |
| `Stored credentials are for X but current environment is Y` | Workspace mismatch | Call `select_workspace` to align, or re-auth |

## Reference Photo Issues

The thumbnail pipeline uses a reference photo of Ben for identity. Setup must end with at least one `ben_reference_*.jpg` in `Projects/youtube/thumbnails/refs/`.

| Symptom | Cause | Fix |
|---|---|---|
| No Ben photo in `refs/` | User skipped Phase 2 sub-step | Ask the user to drop one recent photo named `ben_reference_{YYYY-QQ}.jpg` |
| Photo is older than 90 days | Identity drift risk | Ask the user for a more recent photo |
| Photo has sunglasses, hat, group, or heavy filter | Won't anchor well at generation time | Reject; ask for a clean portrait |
| Photo resolution < 1024px | Too low for reliable identity transfer | Reject; ask for higher-resolution |

## Style Spec Build Failures

### Interview stalls on a question

The user can't answer (e.g., "not sure what palette to pick"). Two options:

1. **Default and flag.** Use the locked default for that section and mark `auto-default: true` in the YAML. A future setup run can re-ask.
2. **Skip and warn.** Leave the section as `[FILL]` and warn the user the generate skill will fall back to defaults at runtime.

Prefer option 1 for low-risk sections (prohibited extras, voice mood). Use option 2 for high-risk sections (palette, framing library) where a wrong default would propagate into every future thumbnail.

### Validation fails after writing the file

The setup skill's verify step (no `[FILL]`, palette has hex codes, ref photo exists, etc.) caught a bad write.

Fix: re-run only the failing section's interview. Don't restart from Phase 1.

### Em-dash linter overwrote characters

If a vault markdown linter (Prettier, Obsidian Linter plugin) is auto-converting `--` to `—`, the style spec may have em dashes after a save round-trip.

Fix:
1. Locate the linter config.
2. Disable em-dash conversion (typographic-replacements).
3. Manually fix the resulting em dashes in the style spec.
4. Re-verify.

Per `CLAUDE.md` rule 14, em dashes are banned. The setup skill must produce a clean file; if the linter is fighting that, the linter is wrong.

## Brand Kit Failures

| Status / error | Cause | Fix |
|---|---|---|
| `failed: url unreachable` | DNS or 404 | Confirm URL in browser, retry |
| `failed: scrape blocked` | Cloudflare or CAPTCHA on the site | Skip Phase 4; not blocking |
| `failed: no brand assets found` | Site too sparse | Skip Phase 4; revisit when the site is built out |
| Stuck `in_progress` over 5 min | Backend queue | Wait, don't retry |

A failed Brand Kit is terminal. Mark Phase 4 skipped and proceed to Phase 5.

## Folder Structure Failures

### Existing folder with conflicting layout

The vault has an older `wip/` folder or an `Intelligence/youtube-intelligence/thumbnails-*/` archive.

Fix: ask the user before moving files. See the migration section in `folder-structure.md`. Don't auto-merge.

### `published/` is empty

The user said setup is needed but no past thumbnails exist. Two cases:

1. **First channel, no thumbnails ever.** Phase 1 still creates the structure. Phase 2 will only populate the Ben reference photo (no style anchors yet). Use the locked style defaults; the user can add anchor refs after their first few ships.
2. **Past thumbnails exist but in the wrong place.** Locate them and move per migration rules before continuing setup.

Ask the user which case applies.

## Smoke Test Failures (Phase 5)

The Phase 5 smoke test hands off to the generate skill for one thumbnail. If it fails:

1. **Style spec issue.** Re-run validation on `Context/youtube-thumbnail-style.md`. Look for missing or malformed fields.
2. **Reference photo issue.** The face looks wrong because the Ben reference photo is poor. Replace it with a better one and retry.
3. **Prompt issue.** The generate skill built a bad prompt. This is a generate-skill bug, not a setup issue; surface the prompt and ask the user to inspect.
4. **Network or API issue.** Retry once.

Do NOT re-run the full setup on a smoke test failure. Diagnose first.

## Workspace Issues

### Single private workspace, user wants channel-specific isolation

Higgsfield supports multiple workspaces (paid plan dependent). If the user wants Ben's thumbnails isolated from any other use of the account:

1. Call `list_workspaces` to see what exists.
2. If a YT-specific workspace exists, call `select_workspace` with its ID.
3. If not and the plan supports multi-workspace, the user can create one in the Higgsfield UI; this MCP doesn't currently expose workspace creation. Surface the limitation.

For most solo users, the private workspace is fine. Don't push multi-workspace as required.
