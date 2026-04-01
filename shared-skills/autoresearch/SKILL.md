---
name: autoresearch
description: Autonomous goal-directed iteration loop that continuously improves prompts, templates, configs, or code. Uses four-way separation — eval agent writes eval.py (judge script), test runner produces outputs, judge script scores them, main agent edits the prompt. Inspired by Karpathy's autoresearch.
---

# AutoResearch — Autonomous Optimization Loop

USE WHEN the user runs `/autoresearch`, says "autoresearch", "optimize this prompt", "improve this overnight", "run an optimization loop", "iterate on this", "auto-improve", or wants to autonomously refine a file against measurable criteria.

---

## Architecture: Four-Way Separation

This skill enforces strict separation between four roles:

| Role | Who | Knows Eval Code? | Knows Prompt History? | Knows Assertions? |
|------|-----|-----------------|----------------------|-------------------|
| **Optimizer** | You (main agent) | **NO** — reads metric number + assertion names only | Yes — reads logs, plans changes | Names only, not implementation |
| **Eval Agent** | `autoresearch-eval-agent` sub-agent | Yes — it writes eval.py | No | Yes — translates them to code |
| **Test Runner** | `autoresearch-test-runner` sub-agent | **NO** — fresh context | **NO** — only sees current prompt | **NO** |
| **Judge Script** | `eval.py` (Python script) | IS the eval | No — just reads files and counts | IS the assertions |

- The **optimizer** never writes eval.py, never generates outputs, never sees eval code
- The **eval designer** writes eval.py once, then is never called again during the loop
- The **test runner** never sees the eval — fresh context every time
- The **judge** is deterministic code with no AI

This mirrors Karpathy's original pattern: the AI edits code but a fixed, externally-written eval function measures the result.

---

## User Interaction: Always Use AskUserQuestion

**Whenever you need user input or confirmation, use the `AskUserQuestion` tool.** This shows an interactive popup in Cowork rather than a plain text message. Use it for:
- Confirming assertions ("Do these assertions look right?")
- Confirming eval.py ("Does this eval script capture what you mean?")
- Asking whether to continue after errors
- Any decision point that requires the user's approval

---

## When the User Pastes Content

1. Save it to a file in the working directory (e.g., `target-skill.md`)
2. Analyze the content and propose 5-7 binary assertions that define "good output"
3. Use `AskUserQuestion` to ask the user to confirm, adjust, or add assertions
4. Once confirmed, **spawn the `autoresearch-eval-agent` sub-agent** to generate the eval system:
   - Pass it: the target prompt/skill path, the confirmed assertions list, and the working directory
   - It generates `eval.py` and `test_cases.json`
   - **You (the optimizer) do NOT read eval.py code.** You only read its output when you run it.
5. Show the user the generated eval.py (read it for them) and use `AskUserQuestion` to confirm it looks right
6. Mark `eval.py` and `test_cases.json` as **READ-ONLY** — you MUST NOT modify them during the loop
7. Run baseline (iteration 0): generate outputs via test runner sub-agent, run `python eval.py`, record the score
8. Start the loop

If the user says "improve this" without assertions, suggest 5 reasonable ones and use `AskUserQuestion` to confirm.
If the user says "go" or "start", spawn the eval agent and begin the loop immediately.

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

### Step 4 — Generate Outputs (via Sub-Agent)
- **Spawn the `autoresearch-test-runner` sub-agent** with:
  ```
  Generate outputs using the prompt at [path to target skill].
  Test cases are at [path to test_cases.json].
  Save each output to outputs/output_00.txt through outputs/output_[N].txt.
  Follow the prompt exactly. One output per test case. No commentary.
  ```
- The sub-agent has **fresh context** — it does not know:
  - What the eval checks for
  - What iteration we're on
  - What changes were made
  - What the optimization goal is
- It simply follows the prompt and generates outputs
- **You (the optimizer) MUST NOT generate outputs yourself. Always use the sub-agent.**

### Step 5 — Evaluate
- Run: `python eval.py outputs/`
- Parse the `METRIC pass_rate=X.XXXX` line
- If eval.py crashes, mark this iteration as "crash"

### Step 6 — Guard Check (if guard is set)
- Run the guard check
- If the guard fails, this iteration is automatically "discard"

### Step 7 — Decide
| Condition | Action |
|-----------|--------|
| Metric improved | **KEEP** — the change stays, update `.backup` to the new version |
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

**Rule 1: You are the optimizer. You NEVER generate outputs or write eval code.**
- You edit the prompt, read metrics, decide keep/discard
- You spawn the test runner sub-agent to produce outputs
- You spawn the eval agent sub-agent to write eval.py (Phase 1 only)
- You do NOT read eval.py source code — only its stdout output

**Rule 2: The eval agent writes eval.py once, then disappears.**
- It receives the assertions and the prompt
- It generates eval.py and test_cases.json
- It is NEVER called again during the loop
- The optimizer never sees how the heuristics are implemented

**Rule 3: The test runner sub-agent NEVER sees the eval.**
- It gets fresh context each time
- It only receives: the prompt file path + test cases path
- It does not know what assertions exist or what the eval checks for

**Rule 4: eval.py is the judge. It is READ-ONLY.**
- You run `python eval.py outputs/` and read the number
- You NEVER modify eval.py or test_cases.json during the loop

---

## State Files

All state lives in the working directory:

| File | Modifiable? | Purpose |
|------|------------|---------|
| Target skill/prompt file | **YES** | The file being optimized |
| `eval.py` | **NO — READ-ONLY** | The external judge script |
| `test_cases.json` | **NO — READ-ONLY** | Test inputs |
| `outputs/` | Overwritten each iteration (by sub-agent) | Generated outputs for eval |
| `autoresearch-session.md` | No | Session config |
| `autoresearch-log.jsonl` | Append-only | Machine-readable log |
| `autoresearch-worklog.md` | Append-only | Human-readable narrative |
| `autoresearch-dashboard.html` | Rewritten each iteration | Live visual dashboard |
| `autoresearch-ideas.md` | Yes | Backlog of ideas |

### JSONL Log Format

```json
{"iteration": 1, "timestamp": "2026-04-01T10:30:00Z", "hypothesis": "Add urgency word to subject line", "metric_name": "pass_rate", "metric_value": 0.70, "baseline": 0.50, "best_so_far": 0.70, "delta": "+0.20", "assertion_breakdown": {"word_count": 10, "no_buzzwords": 9, "has_question": 7, "curiosity": 6, "relevance": 8}, "guard_pass": true, "status": "keep"}
```

The `assertion_breakdown` shows how many outputs passed each individual assertion (out of total test cases). This helps target the weakest assertion.

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
5. **eval.py is READ-ONLY.** Never modify the eval script during the loop.
6. **test_cases.json is READ-ONLY.** Never modify test cases during the loop.
7. **Always revert on discard.** Never accumulate failed changes.
8. **Log everything.** Even crashes and no-ops get logged.
9. **Don't ask permission mid-loop.** Only pause if the user messages you.
10. **Respect the modifiable files list.** Only the target skill/prompt can be edited.
11. **Stuck detection.** After 3 consecutive discards on similar ideas, pivot radically.
12. **No cherry-picking.** Run the full eval every time, not a subset of test cases.
13. **Read the failure details.** Use the per-output assertion breakdown to target your next change.
