---
name: youtube-thumbnail-setup
description: >
  One-time setup for the YouTube thumbnail pipeline. Builds the locked style spec
  at Context/youtube-thumbnail-style.md, sets up vault folders for refs, logos,
  generated outputs, and optionally creates a Higgsfield Brand Kit. Use when the
  user says set up youtube thumbnails, init thumbnails, configure thumbnail
  pipeline, onboard thumbnail skill, or the generate skill reports the style
  spec is missing or has FILL blocks. Run this once before the first generation.
  The generate skill uses reference images (a photo of Ben, past thumbnails,
  style anchors), not a trained Soul model, so no Soul training step is needed.
---

# YouTube Thumbnail Setup

One-time onboarding for the YouTube thumbnail pipeline. After this skill finishes, `youtube-thumbnail-generate` can produce on-brand thumbnails on every call without re-prompting for setup info.

## What This Skill Does

In one guided run:

1. Creates the vault folder structure for refs, logos, generated outputs, and the published archive.
2. Helps the user pick 5 to 10 reference thumbnails from the published archive into `refs/`.
3. Helps the user drop real logo PNGs into `logos/`.
4. Builds `Context/youtube-thumbnail-style.md` from the locked Ben AI thumbnail visual language defaults, confirming or overriding each section with the user.
5. Optionally creates a Higgsfield Brand Kit from a website URL as a secondary identity record.
6. Smoke-tests by handing off to `youtube-thumbnail-generate` with a known topic.

This is the only skill that writes to `Context/`. The generate skill only reads it.

## When to Run This

- First-time setup, before any thumbnail has ever been generated.
- The vault structure has changed and refs/logos need to be re-curated.
- Style drift across three or more recent batches; refresh the style spec from the latest anchor thumbnails.
- The generate skill reports `Context/youtube-thumbnail-style.md` is missing or contains `[FILL]` placeholders.

Do NOT run this skill just to make a thumbnail. That's what `youtube-thumbnail-generate` is for.

## UX Rules

1. **One question at a time.** Don't batch-ask for palette, framing, refs, and logos in a single message.
2. **Use AskUserQuestion with labeled options.** Open-ended questions slow setup.
3. **Be concise.** No raw `media_id` or `job_id` in chat. Report success per phase.
4. **Detect the user's language** from their first message and reply in it. Technical args (hex codes, model names) stay English.
5. **Don't proceed past a phase until the phase succeeds.** If a folder can't be created or a file can't be written, stop and triage.

## Setup Flow

Run phases in order. Each phase has its own reference file or section.

### Phase 1: Vault folder structure

Create the folder layout in `Projects/Youtube/thumbnails/`. See `references/folder-structure.md` for the full tree and naming conventions.

Required folders:

```
Projects/Youtube/thumbnails/
├── published/              (existing past thumbnails, archive reference)
├── refs/                   (curated style anchors, hand-picked subset)
├── logos/                  (real transparent-bg logo PNGs)
└── generated/              (skill output goes here)
```

Confirm `published/` already has 5+ thumbnails using the existing convention `YYYY-MM-DD_{youtube-id}_{slug}.jpg`. If not, ask the user to drop them in before continuing.

### Phase 2: Reference thumbnails and logos

Walk the user through selecting:
- 5 to 10 strongest past thumbnails for `refs/` (the curated style anchor set, different from `published/` which is the full archive)
- Real logo PNGs (transparent background) into `logos/`

See `references/folder-structure.md` for naming conventions.

### Phase 3: Build the style spec

Build `Context/youtube-thumbnail-style.md` starting from the locked Ben AI thumbnail visual language defaults, then confirming or overriding each section with the user.

Full schema and every section: `references/style-spec.md`.

The skill asks the user (one question at a time, labeled options) to confirm or override:
- Palette (locked: charcoal `#1F1F1F` + coral `#E97B5D` + supporting palette)
- Typography (locked: bold uppercase sans + black serif wordmark)
- Layout (locked: Ben right-third + text-left)
- Framing library, expression library
- Wardrobe (locked: plain black t-shirt or hoodie)
- Lighting
- Anchor references (3 to 5 strongest past thumbnails from `refs/`)
- Prohibited patterns

Most sections should be "keep the locked default." The whole style-spec build should take under 2 minutes if the user agrees with the production-style defaults.

### Phase 4: Optional Brand Kit

Ask whether to create a Higgsfield Brand Kit from a website URL. This auto-extracts logo, palette, fonts, tagline at the Higgsfield account level. Useful as a secondary identity record but not required for thumbnail generation.

If yes: see `references/brand-kit.md` for the MCP flow. Brand Kit is NOT used at thumbnail render time; the thumbnail pipeline uses reference images and the locked style spec only.

If no: skip and proceed to Phase 5.

### Phase 5: Verify

Run a one-thumbnail smoke test by handing off to `youtube-thumbnail-generate` with a known topic. Default mode: `new-with-ben` with a photo of Ben passed as a reference image, 1 variant.

If the output looks like Ben and matches the palette/framing/layout, setup is done.

If the smoke test fails: do not re-run setup. Triage with `references/troubleshooting.md` first.

## When Things Break

See `references/troubleshooting.md` for the full catalog (auth, folder structure issues, style spec build issues, Brand Kit failures).

Quick triage:
- **Style spec interview stalled**: skip to defaults for that section, mark `auto-default: true` in the YAML so future setup runs can re-ask.
- **Brand Kit fetch returns `status: failed`**: terminal. The URL is invalid or blocked. Skip Phase 4; thumbnails work without it.
- **`published/` is empty**: ask the user to drop past thumbnails in before continuing, or proceed with the locked defaults and add anchor refs after the first few ships.

## Output

When setup completes, the skill reports a short summary to the user:

```
Setup complete.

Vault folders:       Projects/Youtube/thumbnails/{published, refs, logos, generated}/
Reference thumbnails: N curated in refs/
Logos:               M real PNGs in logos/
Style spec written:  Context/youtube-thumbnail-style.md
Brand Kit:           ✓ created (optional) | skipped
Smoke test:          ✓ 1 thumbnail generated and looks correct

You can now run /youtube-thumbnail-generate to make thumbnails.
```

## Generation Approach (for context)

The thumbnail pipeline uses **reference images** for character and style consistency, not a trained Higgsfield Soul Character. Every `new-with-ben` thumbnail expects a photo of Ben passed as a `medias[]` reference; the model (`nano_banana_2` by default) uses it as the identity anchor.

This means:
- No Soul training step. The user keeps one or two recent photos of Ben in `refs/` (named `ben_reference_*.jpg`) and the generate skill picks one as the face anchor on each run.
- No paid plan requirement for Soul features.
- Identity consistency is good (~75-85%) without training. Acceptable for most thumbnails. If consistency becomes a problem, Soul training can be added back as a future enhancement.

## Core Rules

1. **Never run setup just to generate a thumbnail.** Use the generate skill.
2. **Never leave `[FILL]` blocks in the style spec.** The generate skill falls back to locked defaults, but a clean spec is the goal.
3. **Never use em dashes** in any file this skill writes. Per `CLAUDE.md` project rule.
4. **Detect the user's language and respond in it.** Hex codes, model names, YAML keys stay English.
5. **Reference images are the identity anchor**, not a Soul. The user keeps current photos of Ben in `refs/` so the generate skill always has a face to anchor to.
