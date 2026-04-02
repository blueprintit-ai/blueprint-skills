---
name: autoresearch
description: Autonomous goal-directed iteration loop that continuously improves prompts, templates, configs, or code. Uses four-way separation — eval agent writes eval.py (judge script), test runner produces outputs, judge script scores them, main agent edits the prompt. Inspired by Karpathy's autoresearch.
---

# AutoResearch — Autonomous Optimization Loop

USE WHEN the user runs `/autoresearch`, says "autoresearch", "optimize this prompt", "improve this overnight", "run an optimization loop", "iterate on this", "auto-improve", or wants to autonomously refine a file against measurable criteria.

---

## Architecture: Separation of Roles

This skill supports two evaluation modes:

### Deterministic Mode (default) — Four-Way Separation

| Role | Who | Knows Eval Code? | Knows Prompt History? |
|------|-----|-----------------|----------------------|
| **Main Agent** | You (optimizer) | **NO** — reads metric number only | Yes — reads logs, plans changes |
| **Eval Agent** | `autoresearch-eval-agent` sub-agent | Yes — writes eval.py | No |
| **Test Runner** | `autoresearch-test-runner` sub-agent | **NO** — fresh context | **NO** |
| **Judge Script** | `eval.py` (deterministic Python) | IS the eval | No |

### Hybrid Mode (opt-in) — Five-Way Separation

For creative/subjective tasks, the user can opt into an additional LLM judge tier:

| Role | Who | Knows Eval? | Knows Rubric? | Knows Iterations? |
|------|-----|------------|---------------|-------------------|
| **Main Agent** | You (optimizer) | Metric numbers only | Criteria names only | Yes |
| **Eval Agent** | `autoresearch-eval-agent` | Writes eval.py + rubric.md | — | No |
| **Test Runner** | `autoresearch-test-runner` | No | No | No |
| **Judge Script** | `eval.py` (deterministic) | IS eval | No | No |
| **Judge Agent** | `autoresearch-judge` sub-agent | **No** | **Follows rubric** | **No** |

In hybrid mode:
- **Tier 1** (always runs): `eval.py` → deterministic `pass_rate`
- **Tier 2** (LLM judge): Judge Agent scores outputs against `rubric.md` → `quality_score`
- **Combined**: `combined_score = (0.6 × pass_rate) + (0.4 × quality_score)` (weights adjustable)
- Keep/discard decision is based on `combined_score`

Key isolation:
- The **optimizer** never writes eval.py, never generates outputs, never sees eval code
- The **eval agent** writes eval.py (and rubric.md if hybrid) once, then disappears
- The **test runner** never sees the eval or rubric — fresh context every time
- The **judge script** is deterministic code with no AI
- The **judge agent** never sees eval.py, iteration history, or optimizer intent — only the rubric

---

## User Interaction: Always Use AskUserQuestion

**Whenever you need user input or confirmation, use the `AskUserQuestion` tool.** This shows an interactive popup in Cowork.

**CRITICAL: Keep popup text SHORT.** The popup is small — long text becomes unreadable. Follow this pattern:

1. **Write details in chat FIRST** (assertions list, eval code, explanations)
2. **Then use AskUserQuestion with ONLY a short question** — one sentence max

**Good:**
```
[In chat]: Here are 7 proposed assertions:
1. Covers all 4 search clusters
2. Each entry has title, channel, views
3. Contains opportunity mapping
...

[AskUserQuestion]: "Do these assertions look right?"
Options: "These look good" / "Adjust some" / [free text]
```

**Bad:**
```
[AskUserQuestion]: "Here are 7 proposed assertions for what a 'good' output looks like: 1. Covers all 4 search clusters (Core, Tools, Niche, Competitors)... [giant paragraph]"
```

Never put lists, explanations, or details inside AskUserQuestion. The popup is for the QUESTION only.

---

## When the User Pastes Content

1. Save it to a file in the working directory (e.g., `target-skill.md`)

2. Analyze the content and propose 5-7 binary assertions. **Write the list in chat** (not in the popup).

3. Use `AskUserQuestion` — short text only:
   - Question: `"Do these assertions look right?"`
   - Options: `"These look good"` / `"Adjust some"`

4. **SEPARATE STEP — always ask this.** Use `AskUserQuestion`:
   - Question: `"Which evaluation mode?"`
   - Options: `"Deterministic only"` / `"Hybrid (deterministic + LLM judge)"`
   - In chat before the question, briefly explain: "Deterministic checks things mechanically (word count, keywords, format). Hybrid adds an LLM judge for creative quality (tone, authenticity, narrative) — best for creative content like emails, copy, and marketing."

5. **SEPARATE STEP — always ask this.** Use `AskUserQuestion`:
   - Question: `"How many iterations? (Recommended: 5)"`
   - Options: `"5 (recommended)"` / `"10"` / `"20"`
   - In chat before the question, briefly explain: "Each iteration edits the prompt, generates outputs with real tools, and evaluates. 5 iterations is a good starting point — you can always run more later."
   - Store the chosen iteration count for the loop's stop condition.

6. **Spawn the `autoresearch-eval-agent` sub-agent** to generate the eval system:
   - Pass it: the target prompt/skill path, the confirmed assertions list, the working directory, and **whether hybrid mode is enabled**
   - It generates `eval.py` and `test_cases.json` (always)
   - If hybrid: it also generates `rubric.md` with subjective scoring criteria
   - **You (the optimizer) do NOT read eval.py code.** You only read its output when you run it.

7. Show the user the generated eval.py (and rubric.md if hybrid) in chat. Then use `AskUserQuestion`:
   - Question: `"Does this eval look right?"`
   - Options: `"Looks good"` / `"Adjust"`

8. Mark `eval.py`, `test_cases.json`, and `rubric.md` (if hybrid) as **READ-ONLY** — you MUST NOT modify them during the loop

9. Run baseline (iteration 0): generate outputs via test runner (always live — using real tools and data), run eval.py (and judge agent if hybrid), record the score

10. Start the loop — stop after the chosen iteration count

If the user says "improve this" without assertions, suggest 5 reasonable ones and use `AskUserQuestion` to confirm.
If the user says "go" or "start", default to deterministic mode + 5 iterations, spawn the eval agent, and begin immediately.

---

## Phase 0: Session Setup

When the user pastes a skill, prompt, or template:

1. Save it to a file (e.g., `target-skill.md`)
2. Analyze the content and propose 5-7 binary assertions
3. Ask the user to confirm or adjust
4. Confirm the session config:

| Field | Description | Example |
|-------|-------------|---------|
| **Goal** | What are we optimizing? | "Improve cold email reply-rate signals" |
| **Metric** | Always `pass_rate` for prompt/skill optimization | `pass_rate` |
| **Direction** | Higher is better | `higher` |
| **Assertions** | The binary checks (confirmed by user) | "Under 150 words", "Contains a question CTA" |
| **Modifiable File** | The prompt/skill file ONLY | `target-skill.md` |
| **Guard** | Optional regression check | None |

---

## Phase 1: Generate the Eval System (via Eval Designer Sub-Agent)

Before any optimization begins, spawn the `autoresearch-eval-agent` sub-agent:

```
Design an eval system for the prompt/skill at [path to target skill].

Assertions (confirmed by user):
1. [assertion 1]
2. [assertion 2]
...

The prompt expects these inputs: [list input fields from the prompt].
Save eval.py and test_cases.json to [working directory path].
```

The eval agent will:
1. Generate `test_cases.json` — 10+ realistic, diverse test inputs
2. Generate `eval.py` — deterministic Python with proxy heuristics for each assertion
3. Verify eval.py has no syntax errors

**IMPORTANT: You (the optimizer) MUST NOT read the eval.py source code.** The eval agent writes it. You only interact with eval.py by running it and reading its stdout output (the metric number and assertion names). This prevents you from knowing the exact heuristics and gaming them.

After the eval agent finishes:
- Show the user eval.py (read it for them to review) and ask: "Does this eval capture what you mean?"
- If the user wants changes, spawn the eval agent again with adjustments
- Once the user confirms, **eval.py and test_cases.json are READ-ONLY for the rest of the session**

See `references/example-eval.py` for what a generated eval.py looks like.

---

## Phase 2: Baseline (Iteration 0)

1. Create the `outputs/` directory
2. **Spawn the `autoresearch-test-runner` sub-agent** with this prompt:
   ```
   Generate outputs using the prompt at [path to target skill].
   Test cases are at [path to test_cases.json].
   Save each output to outputs/output_00.txt through outputs/output_09.txt (zero-padded index matching test case order).
   Follow the prompt exactly. One output per test case. No commentary — just the raw output in each file.
   ```
   **IMPORTANT: Output file naming must be `output_XX.txt` (zero-padded index).** Both the eval agent (when writing eval.py) and the test runner must use this convention. If eval.py uses a different naming scheme, the files won't be found.
3. Run: `python eval.py outputs/`
4. Parse the `METRIC pass_rate=X.XXXX` line from stdout
5. Record as the baseline in `autoresearch-log.jsonl`
6. Create the initial `autoresearch-dashboard.html` (use template from `references/dashboard-template.html`)

---

## Phase 3: The Loop (Repeat)

Each iteration follows this exact sequence:

### Step 1 — Review
- Read the current state of the modifiable file
- Read the last 5 entries from `autoresearch-log.jsonl`
- Read `autoresearch-ideas.md` if it exists
- Read the per-output failure details from the last eval run
- Identify patterns: which assertions fail most? Which test cases are hardest?

### Step 2 — Ideate
- Pick ONE idea to try this iteration
- The idea must be atomic — one change, one hypothesis
- Write the hypothesis in plain English before making the change
- Target the most common failure mode from the last eval

### Step 3 — Modify
- Save a backup: copy the modifiable file to `[filename].backup`
- Make exactly ONE change to the modifiable file

### Step 4 — Execute Prompt (via Test Runner Sub-Agent)
- **Before spawning**, scan the target skill file for any references to other files (e.g., `references/`, linked files, imported data). List all file paths the skill depends on.
- **Spawn the `autoresearch-test-runner` sub-agent** with:
  ```
  Execute the prompt at [path to target skill].
  Test cases are at [path to test_cases.json].
  The working project is at [project path].

  Reference files the prompt depends on (read these first):
  - [path to references/file1.md]
  - [path to references/file2.md]
  - [... list ALL referenced files]

  Use all available tools (web search, file access, APIs) to produce real outputs.
  Save each output to outputs/output_00.txt through outputs/output_[N].txt.
  Follow the prompt exactly. One output per test case. No commentary.
  ```
- **IMPORTANT: Always pass reference file paths explicitly.** The test runner has fresh context — it cannot resolve relative paths or guess where files are. Scan the skill for patterns like `references/`, `see also`, file paths, `[[wikilinks]]`, or any mentions of other files, and pass their full absolute paths.
- The sub-agent runs the prompt **live with real tools** — not mocked
- It has **fresh context** — it does not know:
  - What the eval checks for
  - What iteration we're on
  - What changes were made
  - What the optimization goal is
- **You (the optimizer) MUST NOT generate outputs yourself. Always use the sub-agent.**

### Step 5 — Evaluate (Tier 1: Deterministic)
- Run: `python eval.py outputs/`
- Parse the `METRIC pass_rate=X.XXXX` line
- If eval.py crashes, mark this iteration as "crash"

### Step 5b — Evaluate (Tier 2: LLM Judge — hybrid mode only)
If hybrid mode is enabled:
- **Spawn the `autoresearch-judge` sub-agent** with:
  ```
  Score the outputs in [path to outputs/] against the rubric at [path to rubric.md].
  Save your scores to judge-scores.json in the working directory.
  ```
- The judge agent has **fresh context** — it does not know eval.py, iteration count, or prompt changes
- Parse `quality_score` from the resulting `judge-scores.json`
- Compute the combined score:
  ```
  combined_score = (0.6 × pass_rate) + (0.4 × quality_score)
  ```
  Use `combined_score` for the keep/discard decision instead of `pass_rate` alone.

### Step 6 — Guard Check (if guard is set)
- Run the guard check
- If the guard fails, this iteration is automatically "discard"

### Step 7 — Decide
| Condition | Action |
|-----------|--------|
| Metric improved (pass_rate or combined_score) | **KEEP** — the change stays, update `.backup` to the new version |
| Metric same or worse | **DISCARD** — restore from `.backup` |
| Eval crashed | **CRASH** — restore from `.backup`, note the error |

### Step 8 — Log
- Append a line to `autoresearch-log.jsonl` (see JSONL format below)
- Update `autoresearch-worklog.md` with a human-readable entry
- Update `autoresearch-dashboard.html` with current stats

### Step 9 — Repeat
- Go back to Step 1
- If stuck (3+ discards in a row on similar ideas), try a radically different approach
- If the user sends a message, pause the loop, respond, then resume

---

## The Separation Rules

**Rule 1: You are the optimizer. You NEVER generate outputs, write eval code, or score quality.**
- You edit the prompt, read metrics, decide keep/discard
- You spawn the test runner sub-agent to produce outputs
- You spawn the eval agent sub-agent to write eval.py and rubric.md (Phase 1 only)
- You spawn the judge agent to score quality (hybrid mode, each iteration)
- You do NOT read eval.py source code — only its stdout output

**Rule 2: The eval agent writes eval.py (and rubric.md) once, then disappears.**
- It receives the assertions and the prompt
- It generates eval.py, test_cases.json, and rubric.md (if hybrid)
- It is NEVER called again during the loop
- The optimizer never sees how the heuristics are implemented

**Rule 3: The test runner sub-agent NEVER sees the eval or rubric.**
- It gets fresh context each time
- It only receives: the prompt file path + test cases path
- It does not know what assertions exist, what the eval checks for, or what the rubric scores on

**Rule 4: eval.py is the deterministic judge. It is READ-ONLY.**
- You run `python eval.py outputs/` and read the number
- You NEVER modify eval.py or test_cases.json during the loop

**Rule 5: The judge agent NEVER sees eval.py or iteration history (hybrid mode).**
- It gets fresh context each time
- It only receives: the output files + rubric.md
- It does not know what eval.py checks, what iteration we're on, or what changes were made
- It scores purely against the rubric
- rubric.md is READ-ONLY during the loop

---

## State Files

All state lives in the working directory:

| File | Modifiable? | Purpose |
|------|------------|---------|
| Target skill/prompt file | **YES** | The file being optimized |
| `eval.py` | **NO — READ-ONLY** | The deterministic judge script |
| `test_cases.json` | **NO — READ-ONLY** | Test inputs |
| `rubric.md` | **NO — READ-ONLY** (hybrid only) | LLM judge scoring rubric |
| `outputs/` | Overwritten each iteration (by test runner) | Generated outputs for eval |
| `judge-scores.json` | Overwritten each iteration (hybrid only) | LLM judge scores |
| `autoresearch-session.md` | No | Session config (includes eval mode) |
| `autoresearch-log.jsonl` | Append-only | Machine-readable log |
| `autoresearch-worklog.md` | Append-only | Human-readable narrative |
| `autoresearch-dashboard.html` | Rewritten each iteration | Live visual dashboard |
| `autoresearch-ideas.md` | Yes | Backlog of ideas |

### JSONL Log Format

**Deterministic mode:**
```json
{"iteration": 1, "timestamp": "2026-04-01T10:30:00Z", "hypothesis": "Add urgency word to subject line", "metric_name": "pass_rate", "metric_value": 0.70, "baseline": 0.50, "best_so_far": 0.70, "delta": "+0.20", "eval_mode": "deterministic", "assertion_breakdown": {"word_count": 10, "no_buzzwords": 9, "has_question": 7}, "guard_pass": true, "status": "keep"}
```

**Hybrid mode:**
```json
{"iteration": 1, "timestamp": "2026-04-01T10:30:00Z", "hypothesis": "Add personal story opener", "metric_name": "combined_score", "metric_value": 0.72, "pass_rate": 0.80, "quality_score": 0.60, "baseline": 0.50, "best_so_far": 0.72, "delta": "+0.22", "eval_mode": "hybrid", "assertion_breakdown": {"word_count": 10, "no_buzzwords": 9}, "rubric_breakdown": {"emotional_resonance": 3.8, "authenticity": 3.2}, "guard_pass": true, "status": "keep"}
```

The `assertion_breakdown` shows per-assertion pass counts. The `rubric_breakdown` (hybrid only) shows average scores per rubric criterion. Both help target the weakest areas.

Status values: `baseline`, `keep`, `discard`, `crash`, `no-op`

---

## Dashboard

Use the template at `references/dashboard-template.html`. On every iteration, rewrite the full HTML file with updated values:

1. **Header stats** — goal, iterations count, current best, baseline, improvement %
2. **Status counts** — keep/discard/crash totals
3. **Progress bar** — visual fill based on current best vs 1.0
4. **Assertion breakdown** — which assertions are passing/failing
5. **Iteration history table** — last 10 iterations with hypothesis, metric, delta, status
6. **Status badge colors** — green for keep, red for discard, orange for crash

---

## Git Integration

### If Git Is Available
- Create branch `autoresearch/[goal-slug]-[date]` before starting
- Commit on every "keep" iteration
- `git checkout -- [file]` on every "discard" iteration

### If Git Is NOT Available
- Before each modification, copy the file to `[filename].backup`
- On discard, restore from `.backup`
- On keep, update `.backup` to the new version

---

## Stopping

The loop runs until:
- The user says "stop" or "pause"
- A maximum iteration count is reached (if set in session config)
- The metric plateaus (no improvement in 10+ consecutive iterations)

When stopping, write a final summary to `autoresearch-worklog.md` with:
- Total iterations run
- Best metric achieved vs baseline
- Top 3 most impactful changes
- Which assertions improved most
- Ideas that were never tried (saved to `autoresearch-ideas.md`)

---

## Critical Rules

1. **ONE change per iteration.** Never bundle multiple ideas.
2. **NEVER generate outputs yourself.** Always use the `autoresearch-test-runner` sub-agent.
3. **NEVER write eval.py yourself.** Always use the `autoresearch-eval-agent` sub-agent.
4. **NEVER read eval.py source code.** You only run it and read its stdout (metric + assertion names).
5. **NEVER score quality yourself.** In hybrid mode, always use the `autoresearch-judge` sub-agent.
6. **eval.py is READ-ONLY.** Never modify the eval script during the loop.
7. **test_cases.json is READ-ONLY.** Never modify test cases during the loop.
8. **rubric.md is READ-ONLY.** (Hybrid mode) Never modify the rubric during the loop.
9. **Always revert on discard.** Never accumulate failed changes.
10. **Log everything.** Even crashes and no-ops get logged. Include both pass_rate and quality_score in hybrid mode.
11. **Don't ask permission mid-loop.** Only pause if the user messages you.
12. **Respect the modifiable files list.** Only the target skill/prompt can be edited.
13. **Stuck detection.** After 3 consecutive discards on similar ideas, pivot radically.
14. **No cherry-picking.** Run the full eval every time, not a subset of test cases.
15. **Read the failure details.** Use assertion breakdown + rubric breakdown (hybrid) to target your next change.
