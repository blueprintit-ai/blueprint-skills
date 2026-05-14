# Vault Folder Structure

The vault layout the setup skill creates and the generate skill reads. All paths relative to the active vault root.

## Full Tree

```
Projects/Youtube/thumbnails/
├── README.md               (auto-generated index, optional)
├── published/              (archive of past thumbnails, full history)
├── refs/                   (curated style anchors AND current Ben reference photos)
├── logos/                  (real transparent-bg logo PNGs for post-compositing)
└── generated/              (skill output, one folder per batch)
```

There is no `soul-training/` folder. The thumbnail pipeline uses reference images, not a trained Soul Character. The Ben reference photo lives directly inside `refs/` alongside the style anchors.

## Folder Purposes

### `published/`

The complete archive of every shipped YouTube thumbnail. This is the historical record. The setup and generate skills read from here but never write.

**Naming convention:**
```
YYYY-MM-DD_{youtube-id}_{topic-slug}.jpg
```

Example:
```
2026-02-09_0T6q4v8Rb_stop-building-n8n.jpg
2026-02-14_sgSrcSUck7U_cowork-plugins-explained.jpg
```

- `YYYY-MM-DD`: upload date to YouTube
- `youtube-id`: 11-char YouTube video ID
- `topic-slug`: lowercase, hyphenated, 4 to 6 words

If filenames don't match this convention, ask the user to rename before setup proceeds. The generate skill's `variation` mode passes filenames as references and needs them readable.

### `refs/`

Two kinds of files live here:

**A. Style anchor thumbnails** (5 to 10 files): a curated subset of `published/`, the strongest thumbnails that define "we look like this." These are the anchors the prompt builder leans on for style consistency.

Use the same naming convention as `published/`. These are typically copies (or symlinks if the OS supports it) of files in `published/`.

**B. Ben reference photos** (1 to 2 files): current portraits of Ben used as the identity anchor in every `new-with-ben` thumbnail. Replace when Ben's look changes meaningfully.

Naming convention:
```
ben_reference_{YYYY-QQ}.jpg
```

Example:
```
ben_reference_2026-Q2.jpg
ben_reference_2026-Q2_alt.jpg
```

Requirements:
- Clear face, eyes visible, looking roughly at camera
- Plain black t-shirt or hoodie (matching the on-camera wardrobe)
- Soft lighting, no sunglasses or hats
- Resolution ≥ 1024 x 1024
- Shot in the last 90 days

The generate skill picks the most recent `ben_reference_*.jpg` as `medias[0]` on every `new-with-ben` run. When a newly shipped thumbnail clearly nails the brand look, copy it from `published/` to `refs/` and add the filename to `anchor_references:` in `Context/youtube-thumbnail-style.md`.

### `logos/`

Real logo PNGs for post-compositing. Transparent background only.

**Naming convention:**
```
logo_{name}.png
logo_{name}_{variant}.png
```

Example:
```
logo_benai.png
logo_benai_light.png
logo_benai_dark.png
logo_anthropic.png
logo_n8n.png
```

Requirements:
- Transparent background (PNG)
- ≥ 1024px on the longest side
- Light AND dark variants if the brand uses both backgrounds

These files NEVER enter a Higgsfield prompt. The skill reserves a zone; the user composites in Figma or Canva.

### `generated/`

The output of every generate run. One folder per batch.

**Naming convention:**
```
generated/{YYYY-MM-DD}-{topic-slug}/
```

Inside each batch folder:
```
generated/2026-05-13-claude-code-skills/
├── manifest.md             (frontmatter + prompt + job_ids + notes)
├── v1.png
├── v2.png
└── v3.png
```

The setup skill only creates the parent `generated/` folder. Sub-folders are written by the generate skill on each run.

## Creation Order

The setup skill creates folders in this order. Earlier folders block later phases.

1. `published/` — verify exists with 5+ files using correct naming. If empty, ask the user to drop existing thumbnails before continuing.
2. `refs/` — create empty. Populated in Phase 2 with style anchor thumbnails + 1-2 Ben reference photos.
3. `logos/` — create empty. Populated in Phase 2.
4. `generated/` — create empty. Generate skill writes here per run.

## What's NOT in This Tree

These files live elsewhere in the vault:

- **Style spec** → `Context/youtube-thumbnail-style.md` (single source of truth)
- **Brand voice doc** → `Context/brand.md` (read by both setup and generate)
- **Outline / scripts / packaging** for the videos themselves → other YouTube skills (`youtube-outline`, `youtube-scripting`, etc.) in their own folders

Don't conflate thumbnail assets with video production assets. Thumbnails are a downstream output; this folder is dedicated to that.

## Migration From Older Layouts

If the vault has an older structure:

- `Intelligence/youtube-intelligence/thumbnails-{date}/` → move all files to `Projects/Youtube/thumbnails/published/`
- `Resources/thumbnails/refs/` → move to `Projects/Youtube/thumbnails/refs/`
- `Resources/thumbnails/logos/` → move to `Projects/Youtube/thumbnails/logos/`
- `Resources/thumbnails/outputs/` → move to `Projects/Youtube/thumbnails/generated/`

Old `wip/` folders can be deleted after their contents are sorted into `published/` or discarded. Don't keep duplicate locations; the skill assumes one home.

## Verification Step

At the end of setup Phase 1, list every folder and the count of files inside. Report to the user. Example:

```
Folder structure ready:
- published/         17 files
- refs/              0 files (populate in Phase 2 with anchors + Ben reference photos)
- logos/             0 files (populate in Phase 2)
- generated/         0 files (generate skill writes here)
```

This confirms the user has the expected state before moving to Phase 2.
