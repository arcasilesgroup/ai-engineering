---
name: verify
description: Use when verification with evidence is needed — not assumptions. Trigger for "check my code", "is this ready to merge", "run the tests", "is coverage good enough", "scan for security issues", "prove it works". Runs 4 specialists with `normal` implicit and `--full` explicit.
effort: max
tier: core
capabilities: [tool_use]
---

# /ai-verify

Evidence-first verification. Dispatches 4 specialists:

1. **deterministic** — runs ruff/gitleaks/pytest/pip-audit/bun test;
   structured pass/fail with finding IDs.
2. **governance** — manifest integrity, ownership boundaries, decision
   store TTL freshness.
3. **architecture** — solution-intent alignment, structural drift.
4. **feature** — spec coverage, acceptance criteria completion.

> **Difference vs `/ai-review`**: review = human-quality judgment;
> verify = deterministic evidence + LLM judgment for what tools cannot
> detect.

## Modes

- `verify` (default): macro-agents — 1 deterministic + 3 LLM judgment.
- `verify --full`: one agent per specialist (maximum context isolation,
  longer runtime).

## Output

Structured report with: gate verdicts, finding IDs (stable for risk
acceptance), severity distribution, recommended actions.

## Used by

- `/ai-commit` — pre-push gate
- `/ai-pr` — pre-merge gate
- `/ai-release-gate` — input to GO/NO-GO aggregation
