# Generation Troubleshooting

Real failure modes during a thumbnail generation. For setup-time issues (folder structure, style spec build, Brand Kit fetches), see the setup skill's `troubleshooting.md`.

## Authentication

| Error | Cause | Fix |
|---|---|---|
| `Session expired` | MCP auth token aged out | Re-authenticate the Higgsfield MCP connector in Claude |
| `Not authenticated` | Never logged in | Authenticate the Higgsfield MCP connector |

## Preflight Failures

These happen before any generation call.

| Symptom | Cause | Fix |
|---|---|---|
| `Context/youtube-thumbnail-style.md` does not exist | Setup never run | Run `/youtube-thumbnail-setup` first (or fall back to locked visual-language defaults and flag at the end) |
| Style spec has `[FILL]` blocks | Setup interrupted | Re-run `/youtube-thumbnail-setup` to finish the interview |
| `new-with-ben` mode but no Ben reference photo | No `ben_reference_*.jpg` in `refs/` AND user didn't attach one | Ask the user once for a recent photo of Ben |
| Multiple `ben_reference_*.jpg` files, ambiguous which to use | Pipeline picks most recent by `YYYY-QQ` suffix automatically | None; note the chosen filename in the manifest |

## Validation Errors

| Error | Cause | Fix |
|---|---|---|
| `Missing required params: prompt` | No prompt sent | Provide one |
| `Missing required params: medias` | Mode needs a reference (variation, new-with-ben, ben-plus-other) | Pass `medias[]` with at least one ref |
| `Invalid values: aspect_ratio=99:99 (allowed: ...)` | Not in the model's enum | Pick from the model's enum in `models.md` |
| `Invalid values: resolution=8k` | nano_banana_2 caps at 4k | Use `resolution: "2k"` or `"4k"` |
| `Unknown params: <name>` | Param doesn't exist on this model | Call `models_explore` for that model's schema |
| `Model accepts only one image reference` | Single-ref model (`gpt_image_2`) got multiple | Drop to 1 ref, or switch to `nano_banana_2` for multi-ref |
| `Unknown media role "<role>"` | Wrong role label | We only use `image` for thumbnails; check the call |

## Job Lifecycle Failures

| Status | What it means | Action |
|---|---|---|
| `failed` | Server-side failure, usually prompt content | Rephrase, try again |
| `nsfw` | Content policy rejection | Rephrase, remove anything suggestive |
| `ip_detected` | Trademark, brand mark, or public figure detected | Remove the brand name or celebrity reference. Composite real logos in post |
| `timeout` | Model is slow today | Retry with a longer wait, or try `nano_banana_flash` |

## Rate Limits

`HTTP 429 Too Many Requests`: back off 30 seconds, then retry. If persistent across the day, the user has hit a plan quota; check `balance`.

## CloudFlare / DataDome

If the response body contains `captcha-delivery` HTML, anti-bot fired. Wait 30 seconds, retry. If it persists for 5+ minutes, ping the Higgsfield team.

## Cost Surprises

Always preflight when `count > 3` or model is `gpt_image_2`. If cost looks wrong:

- `params.get_cost: true` returns the estimate without burning credits
- See cost-per-variant table in `models.md`

If a generation returned 0 credits debited but no image, the job failed silently. Check `job_display` for the actual status.

## Model Rendered a Fake Logo

The model dropped a fake logo, watermark, or branded mark somewhere in the frame despite the negative prompt.

Fixes in order:

1. Tighten the negatives at the end of the prompt: `no real or rendered logos of any kind, no watermarks, no fake brand marks, no Anthropic logo, no Claude logo, no YouTube logo`. Naming specific brands helps.
2. If a brand mark keeps appearing, the prompt is probably referencing the brand by name in Block 1 or 2. Rephrase to describe the tool without naming it (`a coding assistant interface` instead of `the Claude Code interface`), then composite the real logo in post.

## Model Left an Empty Rectangle in the Frame

The model rendered an awkward blank rectangle, usually because the prompt told it to "reserve a logo zone" or "leave a clean empty area."

Fix: never instruct the model to leave a gap. The thumbnail should fill its frame edge-to-edge. If the current prompt has reservation language, strip it and regenerate. The negatives in `prompt-builder.md` Block 4 already explicitly ban "empty rectangles or reserved gaps."

## Ben Looks Like "AI Ben" Not Ben

Symptoms: face shape is off, age is wrong, eyes don't feel like Ben.

Diagnostics in order:

1. Confirm a Ben reference photo was passed as `medias[0]` in the call (`new-with-ben` mode must always have one).
2. Confirm the reference photo is recent (under 90 days). Older photos drift in feel.
3. Confirm the reference photo is high-quality: clear face, eyes visible, no sunglasses or hats, ≥1024px.
4. Confirm the prompt doesn't fight the reference with conflicting facial descriptions. Let the photo carry the face; the prompt should only describe expression and framing.
5. Increase the reference's prominence in the prompt: add `the subject must match the provided reference image (medias[0]) exactly; same person, same face shape, same hair`.
6. If still off, ask the user to replace the reference photo with a fresher one.

## Style Drift Across Batches

Symptom: each batch looks fine on its own, but week-3 thumbnails look different from week-1.

Causes ranked by likelihood:

1. **Style spec drifted.** `Context/youtube-thumbnail-style.md` got edited or new framing categories slipped in. Read it; compare to anchor references.
2. **Prompt is freelancing.** The prompt builder template wasn't followed; blocks got merged or reordered. Re-read `prompt-builder.md`.
3. **Reference photo changed without a manifest note.** A newer `ben_reference_*.jpg` got dropped in. Verify which file was used by reading recent manifests.
4. **Lighting block drifted from the spec.** Pin it back.
5. **Model switched silently.** Confirm the model in the manifest matches what's expected for that mode.

Fix: revert to a known-good prompt from a past `manifest.md`, regenerate, compare side-by-side with the anchor references.

## Variation Mode Drifts From Source

Using `nano_banana_2` with a past thumbnail as reference, but the output ignores the reference.

Fixes:

1. Confirm the reference is the FIRST entry in `medias[]`. Order matters.
2. Make sure the prompt describes the CHANGE, not the source. See "Image-to-Image Prompts" in `prompt-builder.md`.
3. Try passing the prior thumbnail's `job_id` instead of a re-uploaded `media_id`. Higgsfield treats prior jobs as stronger anchors than fresh uploads.
4. If the user is varying an older thumbnail that's not in the system, upload as a fresh `media_id` and pass via `medias[]`.

## Multi-Reference Mode Confuses Subjects

Using `nano_banana_2` with two `medias[]` (Ben + another subject), but the output blends them weirdly.

Fixes:

1. In the prompt, explicitly say "Ben is the person on the right, the second subject is the {description} on the left." Position language helps disambiguate.
2. Keep Ben as `medias[0]` (the strongest anchor slot).
3. Reduce `count` to 1 and iterate; multi-ref renders vary more between variants.

## Higgsfield Returns A Non-Image Result

| Symptom | Cause | Fix |
|---|---|---|
| Returns text or a report URL | Wrong model (likely `brain_activity` Virality Predictor) | Confirm model is `nano_banana_2`, `nano_banana_flash`, `gpt_image_2`, or `flux_kontext` |
| Returns multiple URLs when `count: 1` | Some models return preview + final | Take the highest-resolution URL |

## Workspace Mismatch

If a generation succeeds but doesn't show up in the user's expected workspace:

1. Call `list_workspaces` to see which one is active.
2. Confirm the active workspace matches the user's expectation.
3. Call `select_workspace` to switch if needed.

## Adding a Failure Mode to This File

When a new failure surfaces in real runs, add it here with:

- Symptom (what the user sees)
- Cause (the underlying reason)
- Fix (concrete steps)

Don't add hypothetical failures. Only document what actually happened so this file stays a triage tool, not a brainstorm.
