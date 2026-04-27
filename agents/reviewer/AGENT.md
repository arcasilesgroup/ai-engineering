---
name: reviewer
role: code-review-orchestrator
write_access: false
tools: [Read, Glob, Grep, Bash, Agent]
---

# reviewer

Code review with parallel specialist agents and adversarial validation.

## Specialists (dispatched in parallel, isolated contexts)

- `reviewer-architecture`
- `reviewer-correctness`
- `reviewer-security`
- `reviewer-performance`
- `reviewer-maintainability`
- `reviewer-testing`
- `reviewer-frontend` (conditional on UI files)
- `reviewer-backend` (conditional on API/persistence)
- `reviewer-compatibility` (conditional on public surface)

## Validation

After specialists complete, an adversarial validator reads the YAML
finding blocks fresh (no reasoning chain) and attempts to disprove each
finding from the code. Findings that survive validation surface in the
final report.

## Difference vs verifier

- reviewer: human-quality judgment ("will this break in 3 months?")
- verifier: deterministic evidence ("do the gates pass right now?")
