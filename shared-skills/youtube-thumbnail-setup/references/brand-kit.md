# Higgsfield Brand Kit (Optional)

Higgsfield's native Brand Kit feature auto-extracts brand identity from a website URL. Captures: brand name, logo, hero images, color palette, fonts, tagline, business overview, industry.

## Why Optional

The four core thumbnail modes (`variation`, `new-with-ben`, `ben-plus-other`, `no-face`) do NOT consume Brand Kit inputs. That's a Marketing Studio feature. For thumbnails, the vault is the source of truth.

The Brand Kit is still worth creating because:

1. **Sanity check against `Context/youtube-thumbnail-style.md`.** If Higgsfield's extracted palette differs from the spec, one of them is stale.
2. **Required for Marketing Studio image variants** (a separate workflow for ad creative).
3. **Free, deterministic snapshot of the brand's web identity** at the time of setup.

The logos in the Brand Kit are NOT used at render time. The model still cannot reliably render real logos. The compositing-in-post rule stands.

## When to Skip

- The brand has no public website yet.
- The user only wants thumbnails (not ads). Skip to save 2 minutes of setup.
- A Brand Kit already exists and the website hasn't materially changed.

## Create From URL

Call `show_marketing_studio` with:

```
action: "create"
type: "brand_kit"
url: "https://benai.co"      (or whichever site represents the brand)
```

Response includes:
- `id` (the kit's UUID)
- `status: "queued"` (initial state)

Fetch runs async on Higgsfield's side, typically 30 to 90 seconds.

## Poll for Completion

Call `show_marketing_studio` with:

```
action: "get"
type: "brand_kit"
id: "<kit_id from create>"
```

Status flow:
- `queued` → `in_progress` → `completed` (success path)
- Or any state → `failed` (terminal failure)

Poll every 5 seconds. Stop when status is `completed` or `failed`.

## Completed Kit Contents

When `status: completed`, the response includes:

```yaml
data:
  brand_name: "Ben AI"
  logo: <url to extracted logo>
  hero_images: [<url>, ...]
  palette:
    primary: "#hex"
    secondary: "#hex"
    accent: "#hex"
  fonts: ["Inter", "Source Serif", ...]
  tagline: "..."
  business_overview: "..."
  industry: "AI"
```

Capture the `id` and store it in `Context/youtube-thumbnail-style.md` under:

```yaml
higgsfield_brand_kit_id: <kit_id>
```

The generate skill ignores this field; it's metadata for cross-checking and future Marketing Studio runs.

## Failure Modes

| Status | Cause | Fix |
|---|---|---|
| `failed` with `fail_reason: "url unreachable"` | DNS or 404 | Confirm URL works in a browser, retry |
| `failed` with `fail_reason: "scrape blocked"` | Site has anti-bot protection (Cloudflare, CAPTCHA) | Skip the Brand Kit; thumbnails work without it |
| `failed` with `fail_reason: "no brand assets found"` | Site is too sparse (single-page landing, no logos detected) | Skip; revisit when the site is built out |
| Stuck in `in_progress` over 5 minutes | Backend queue depth | Wait, do not retry. Polling continues |
| `Minimum Basic plan required` | Brand Kit is a paid feature | Skip if user is on free tier |

A failed Brand Kit is terminal. Do not retry the same URL repeatedly. If the kit fails, mark this section skipped and move on; the thumbnail pipeline does not depend on it.

## Listing and Inspecting Later

```
action: "list", type: "brand_kit"     → all kits on the account
action: "get",  type: "brand_kit", id → one kit by id
```

Useful when the user later asks "do we have a Brand Kit for benai.co already?" Check the list before creating a duplicate; the server doesn't dedupe.

## Don't

- Don't pass a Brand Kit URL to `generate_image` in any of the four thumbnail modes. It's silently ignored and adds noise to the request.
- Don't try to upload custom logos to a Brand Kit. Brand Kits are URL-fetch only.
- Don't retry a `failed` kit repeatedly. Investigate the URL or skip.
- Don't treat the Brand Kit's logo URL as canonical for compositing. The PNGs in `Projects/Youtube/thumbnails/logos/` are the truth.
