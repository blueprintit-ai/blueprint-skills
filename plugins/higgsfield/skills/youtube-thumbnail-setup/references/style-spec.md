# Style Spec: Context/youtube-thumbnail-style.md

Full schema and section-by-section guidance for the file the generate skill reads before every render. This is the durable style memory.

The defaults below are NOT generic brand defaults. They are extracted from Ben's 15 published thumbnails in `Projects/youtube/thumbnails/published/`. The visual catalog (recurring motifs, palette rationale, layout patterns) lives in the generate skill's `references/visual-language.md`. Setup writes these locked values into the user's vault; the generate skill reads them at render time.

## File Location

`Context/youtube-thumbnail-style.md` in the active vault. Only the setup skill writes to it. The generate skill only reads.

## Complete Template

```markdown
---
type: thumbnail-style-spec
brand: ben-ai
last_updated: {YYYY-MM-DD}
extracted_from: Projects/youtube/thumbnails/published/
---

# YouTube Thumbnail Style Spec

The locked style memory for every thumbnail generation. Edit this file via /youtube-thumbnail-setup; the generate skill only reads.

These defaults are extracted from Ben's 15 published thumbnails. They are the actual production style, not generic brand defaults from a website.

The thumbnail pipeline uses reference images for character consistency, not a trained Soul Character. Keep one or two current photos of Ben in Projects/youtube/thumbnails/refs/ (named ben_reference_*.jpg) for the generate skill to pull as the identity anchor.

## Palette

Hex codes only. Used in every render.

- Background primary (dominant, ~70% of thumbnails): #1F1F1F deep charcoal with a subtle dot-grid texture overlay
- Background alternate cream (variety, ~20%): #F5E6D8 warm cream / peach
- Background alternate coral (variety, ~10%): #E97B5D solid coral panel
- Signature accent (used on every thumbnail): #E97B5D warm coral, on folders, app icons, asterisk marks, small highlights
- Highlight box only: #FFD93D flat yellow, used ONLY as a marker-highlighter rectangle behind one keyword. Never as a primary background or large fill
- Text on dark: #FFFFFF pure white, bold
- Text on light: #0A0A0A near-black, bold
- UI card fills: #FFFFFF white card surfaces floating on the dark background

Banned colors (do not use unless representing a specific external tool's brand mark):
- navy blue, royal blue, sky blue
- pure red, magenta
- purple (except Obsidian purple #7B68B4 when Obsidian is the topic)
- green (except as a tiny status dot)
- neon / electric variants of anything

## Typography

How any rendered text in the thumbnail looks. Most final text is composited in post; the model still benefits from knowing the style.

- Primary thumbnail text: bold uppercase sans-serif, heavy weight (Inter Black, Anton, or Bebas Neue style). 2 to 3 words per line max, 2 lines max
- Editorial wordmark: black serif (Playfair Display style) used for "Claude Cowork", "Claude Skills", and similar product/feature names
- Body text on UI mockups: medium-weight sans-serif (Inter Medium style)
- White on dark, black on light, always. No outlines, no gradients on text, only subtle shadow when legibility demands

## Layout

The two canonical compositions.

With Ben (default, ~73% of thumbnails)
- Ben on the right third of the frame, chest-up framing, eyes to camera
- Text on the left third, top-anchored
- Supporting visual (folder, app icon, UI mockup, asterisk) below or beside the text
- One hand-drawn white curved arrow arcing from text toward the key element

Without Ben (~27% of thumbnails)
- Text top-centered, 1 to 2 lines
- Icons or visuals stacked or rowed below in an "A + B" or sequential pattern
- One hand-drawn white curved arrow pointing to the rightmost or final element

## Framing Library

Ben's positions on the canvas. The prompt builder picks one per render.

- right-third chest-up: default, Ben on right third, head ~45% of frame height (used in ~10 of 11 with-Ben thumbnails)
- left-third chest-up: mirror, used rarely when the topic visual reads better on the right
- close-up right-third: tighter crop, face fills more of the right third (for celebratory or "big news" topics)

## Expression Library

The expressions actually used in the published archive.

- slight smile: corners up, eyes engaged, no teeth (most common, ~6 of 11)
- focused neutral: mouth closed, intent gaze, very slight smile or none (analytical topics)
- big smile: teeth visible, eyes engaged (for celebratory or impressive-result topics)
- slight forward lean: leaning toward the camera, slight smile (for "you should care" topics)

## Wardrobe

- Default: plain black t-shirt, plain black hoodie
- Never: branded apparel, suits, bright colors, patterned shirts

## Lighting

Used across every Ben thumbnail.

- Key: soft from camera-front-left, slightly above eye level
- Fill: gentle bounce from camera-right
- Rim: subtle from behind on the back of the head and shoulder, separating Ben from the dark background
- Baseline: soft studio quality, no hard shadows, no harsh contrast

## Reference Images for Identity

The thumbnail pipeline uses reference images as the identity anchor, not a trained Soul Character.

- Primary Ben reference: keep 1 or 2 recent photos of Ben in Projects/youtube/thumbnails/refs/, named ben_reference_{YYYY-QQ}.jpg
- The generate skill passes this photo as medias[0] to nano_banana_2 on every new-with-ben thumbnail
- Update the reference photo every quarter or when Ben's look changes meaningfully (haircut, beard, glasses)
- Identity faithfulness with reference-image anchoring: ~75 to 85%. If consistency becomes a problem, Soul training can be added later

## Anchor References

The 5 strongest past thumbnails that define "we look like this." Pulled into prompts as medias[] style references when generating.

- 2026-04-25_LLE6oMh7SxE_claude-routines-99pct.jpg (with-Ben, cleanest UI-mockup composition)
- 2026-03-14_FAEKF-nr3D0_cowork-marketing.jpg (cream-background variant + serif wordmark + list pattern)
- 2026-02-24_X3uum6W2xEI_build-claude-skills-99pct.jpg (folder + arrow + Ben canonical combo)
- 2026-03-09_3cYusISFc9s_claude-skills-2-99pct.jpg (cleanest without-Ben "A then B" composition)
- 2026-04-11_l5Diqeoffa4_7-levels-claude-context.jpg (gradient-strip exception, useful for "N levels / tiers" topics)

When a newly shipped thumbnail clearly nails the brand look, add it here.

## Recurring Motif Vocabulary

These motifs appear across the published archive. Reference them by name in prompts. Full catalog in the generate skill's references/visual-language.md.

- coral starburst: 12-ray asterisk-like icon in coral with a small white center
- coral folder: flat coral file folder with a white tab, often with /skill-name text
- coral app icon: rounded-square coral background with white glyph centered (Cowork-style)
- white hand-drawn curved arrow: thick white sketchy arrow, signature element
- yellow highlight box: flat yellow rectangle behind one keyword, marker-style
- UI mockup card: simplified white card with stylized interface (Claude desktop, browser, dashboard, file manager)

## Logo Handling

The model never renders real logos AND we never instruct it to leave an empty rectangle for one. The thumbnail fills its frame edge-to-edge. Logos are composited on top of the finished thumbnail in Figma or Canva.

## Prohibited Patterns

The model must avoid these. Pulled into every prompt's negative block.

- Real logos rendered by the model (always composited in post)
- Empty rectangles or reserved gaps in the composition
- Any banned color appearing as a primary element
- Centered composition when Ben is in frame (he goes on the right third)
- More than one hand-drawn arrow
- Cartoon or illustrated rendering of Ben (always photoreal)
- Photoreal rendering of supporting visuals (folders, arrows, app icons are flat-stylized)
- Text outlines, gradients on text, drop shadows beyond minimal legibility
- Busy backgrounds that compete with the dot-grid texture
- Multiple accent colors fighting each other
- Em dashes in any rendered text

## Voice and Mood Defaults

How the prompt should sound. Practitioner authority, not hype.

- Banned hype words: amazing, incredible, stunning, mind-blowing, revolutionary, ultimate, supercharged
- Preferred mood: grounded, analytical, curious
- For tutorial topics: confident, clear
- For news/release topics: alert, focused
- For analysis topics: skeptical, intent
- For celebratory topics: confident, big-smile expression
```

## Interview Flow

The setup skill writes this file by starting from the locked Ben AI defaults (above) and asking the user to CONFIRM or OVERRIDE each section. Do NOT ask the user to invent values from scratch; the defaults are extracted from real published thumbnails.

Use `AskUserQuestion` with labeled options. Do not pull from `Context/brand.md` for color defaults; the website brand and the thumbnail brand are intentionally different. Stay with the thumbnail-specific palette.

| Section | Default | What to ask |
|---|---|---|
| Palette | locked (charcoal + coral + cream/yellow accents) | "Confirm the palette or override?" → 2 options: keep locked defaults, change one color (which one) |
| Typography | locked (bold uppercase sans + serif wordmark) | "Confirm or override?" → 2 options: keep, override |
| Layout | locked (Ben right-third + text left-third + arrow) | "Confirm or pick a different default composition?" → 2 options: keep, override |
| Framing library | locked (right-third chest-up + variants) | "Confirm or add/remove?" → multi-select |
| Expression library | locked (4 expressions from published archive) | "Confirm or add/remove?" → multi-select |
| Wardrobe | locked (plain black t-shirt or hoodie) | "Confirm or override?" → 2 options |
| Lighting | locked (soft front-left key + rim) | "Confirm or override?" → 2 options |
| Reference Ben photo | needs user input | "Drop or name 1 or 2 recent photos of Ben for refs/, named ben_reference_*.jpg" |
| Anchor refs | suggested 5 from published archive | "Confirm these 5 or pick different favorites?" → multi-select from `refs/` listing |
| Prohibited | locked banned-colors list + universal rules | "Confirm or add patterns to ban?" → multi-select + free-text |

Each question takes a couple seconds; the user is essentially saying "yes" 10 times unless they want to override. The whole style-spec build should take under 2 minutes.

## Validation Rules

After writing the file, the setup skill must verify:

- [ ] No `[FILL]` blocks remain anywhere.
- [ ] `palette` has 3 to 5 entries, each with a valid hex code.
- [ ] `framing_library` has at least 3 entries.
- [ ] `expression_library` has at least 3 entries.
- [ ] `anchor_references` has at least 3 entries.
- [ ] A Ben reference photo exists in `Projects/youtube/thumbnails/refs/` named `ben_reference_*.jpg`.
- [ ] `prohibited` includes the em-dash rule (universal).

If any validation fails, the setup is incomplete; surface the failure to the user before the smoke test.

## Updating the Spec

The setup skill is the only place to edit this file. If the user wants to update a single section mid-flow, re-invoke the setup skill and have it ask which section to refresh (palette, framing, expressions, etc.), then re-run only that section's interview. For a full refresh, rerun the entire setup flow. Do NOT let the generate skill silently edit this file; it breaks the "single source of truth" property.
