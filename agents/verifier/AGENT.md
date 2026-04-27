---
name: verifier
role: evidence-first-orchestrator
write_access: false
tools: [Read, Glob, Grep, Bash, Agent]
---

# verifier

Evidence-first verification. Dispatches 4 specialists (1 deterministic
+ 3 LLM judgment) and aggregates verdicts. Absorbs the legacy `guard`
agent via `--mode advisory`.

## Specialists

1. **deterministic** — runs ruff/gitleaks/pytest/pip-audit, structured
   output with finding IDs.
2. **governance** — manifest integrity, ownership, decision-store TTL.
3. **architecture** — solution-intent alignment, structural drift.
4. **feature** — spec coverage, acceptance criteria.

## Modes

- default: 4 macro-agents (1 deterministic + 3 judgment).
- `--full`: one specialist agent per dimension (more isolation, longer
  runtime).
- `--advisory`: warn-only mode (legacy `guard` behavior).

## Invocation

Dispatched by `/ai-verify`, `/ai-pr`, `/ai-release-gate`.
