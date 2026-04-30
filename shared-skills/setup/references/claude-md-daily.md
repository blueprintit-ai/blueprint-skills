This folder contains org-level daily notes. In business mode these are AGGREGATED views compiled from individual profile dailies. In professional mode this is the operator's primary daily journal.

## Critical Rule (Business mode)

Do NOT write directly to this folder during profile sessions. All session output goes to the active profile's daily folder at `Team/{org}/Profiles/{name}/Daily/YYYY-MM-DD.md`.

This folder is populated by aggregation schedules in `Team Schedules/` (when configured) that scan all profile dailies and compile them into a single org-level view.

## When You CAN Write Here

- **Professional mode**: Always. This is the operator's daily journal.
- **Business mode**: Only when running a team schedule that explicitly aggregates profile dailies, or when no active profile session is in progress.

## Daily Note Frontmatter

```yaml
---
type: daily-note
date: YYYY-MM-DD
---
```
