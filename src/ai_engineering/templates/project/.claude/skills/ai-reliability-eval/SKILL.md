---
name: ai-reliability-eval
description: "Measures AI system reliability over time by defining pass/fail criteria before implementation, running capability checks, and tracking regression via pass@k metrics. Trigger for 'how reliable is this', 'did my changes break anything', 'measure AI performance', 'define success criteria', 'eval this feature', 'check skill regression'. Not for code correctness; use /ai-test instead. Not for quality gates; use /ai-verify instead — evals measure AI task completion consistency."
effort: mid
argument-hint: "define|check|report|regression|--skill-set [feature]"
tags: [quality, evals, improvement]
---

# Reliability Eval

Eval-Driven Development (EDD): define pass/fail criteria before writing code, then measure AI
reliability with pass@k metrics and track regressions across prompt, agent, and model changes.
Evals answer "Can the AI do this reliably?" — distinct from `/ai-verify`, which checks current
code quality (linting, coverage, security).

## Workflow

Principles applied: §10.5 TDD — EDD mirrors TDD: define the pass/fail criteria BEFORE the
code, then let evals drive iteration; writing evals after implementation is the same
anti-pattern as tests-after.

| Mode | When | Action |
| --- | --- | --- |
| `define` | before implementation | write capability + regression evals, set pass@k targets |
| `check` | during implementation | run current evals, report pass@k, list failures |
| `report` | after implementation | run all evals, compute pass@k + pass^k, render report |
| `regression` | prompt/agent/model change | run regression evals vs baseline, flag degradation |
| `--skill-set` | PR touching `.claude/skills/**` | optimizer over each `.ai-engineering/evals/<skill>.jsonl`, gate pass@1 vs `baseline.json` |

`--skill-set` combined with `--regression` fails on >5 pp pass@1 drop (sub-007 M6, D-127-07). Wired into `.github/workflows/skill-evals.yml`.

### Mode: define (before coding)

1. Identify the capability being built or changed.
2. Write capability evals (can the AI do this new thing?).
3. Write regression evals (do existing things still work?).
4. Set success metrics (pass@k targets).
5. Store at `.ai-engineering/evals/<feature-name>.md`:

```markdown
## EVAL DEFINITION: feature-xyz

### Capability Evals
1. Can create new user account
2. Can validate email format
3. Can hash password securely

### Regression Evals
1. Existing login still works
2. Session management unchanged
3. Logout flow intact

### Success Metrics
- pass@3 > 90% for capability evals
- pass^3 = 100% for regression evals
```

### Mode: check (during implementation)

1. Read the eval definition from `.ai-engineering/evals/<feature-name>.md`.
2. Run each capability eval; record PASS/FAIL.
3. Run regression evals via existing test suites.
4. Report current status with pass@k counts.
5. Identify which evals still fail and why.

### Mode: report (after implementation)

Run all capability + regression evals (per `check`), compute pass@k + pass^k, render, then store at `.ai-engineering/evals/<feature-name>.log`:

```markdown
EVAL REPORT: feature-xyz
========================

Capability Evals:
  create-user:     PASS (pass@1)
  validate-email:  PASS (pass@2)
  hash-password:   PASS (pass@1)
  Overall:         3/3 passed

Regression Evals:
  login-flow:      PASS
  session-mgmt:    PASS
  logout-flow:     PASS
  Overall:         3/3 passed

Metrics:
  pass@1: 67% (2/3)
  pass@3: 100% (3/3)

Status: READY FOR REVIEW
```

### Mode: regression

Baseline is created automatically on the first `report` run — if `baseline.json` does not exist, the current run becomes the initial baseline.

1. Load baseline from `.ai-engineering/evals/baseline.json`.
2. Run all regression evals against current state.
3. Compare against baseline results.
4. Flag any degradation:

```markdown
[REGRESSION EVAL: feature-name]
Baseline: SHA or checkpoint name
Tests:
  - existing-test-1: PASS/FAIL
  - existing-test-2: PASS/FAIL
  - existing-test-3: PASS/FAIL
Result: X/Y passed (previously Y/Y)
```

## Grader Types

| Grader | How it works | When to use | Example |
| --- | --- | --- | --- |
| Code | Deterministic checks (grep, test runners, build) | Verifiable / structured outputs | `grep -q "export function handleAuth" src/auth.ts && echo "PASS"` |
| Model | Claude evaluates open-ended output (score 1-5) | Prose quality, code style, creative output | Prompt: "Does it solve the stated problem? Score 1-5" |
| Human | Flag for manual review with risk level | Security decisions, UX judgment, ambiguous cases | `[HUMAN REVIEW REQUIRED] Risk Level: HIGH` |

## Metrics

| Metric | Definition | Typical target |
| --- | --- | --- |
| pass@1 | First attempt success rate | Varies by difficulty |
| pass@3 | At least one success in 3 attempts | > 90% |
| pass@k | At least one success in k attempts | Depends on criticality |
| pass^3 | All 3 trials succeed | 100% for critical paths |
| pass^k | All k trials succeed | Use for regression evals |

## Storage

```
.ai-engineering/evals/
  <feature-name>.md      # Eval definition
  <feature-name>.log     # Eval run history
  baseline.json          # Regression baselines
```

## Best Practices

- Use code graders when possible — deterministic > probabilistic.
- Human review for security — never fully automate security checks.
- Keep evals fast — slow evals don't get run.
- Version evals with code — evals are first-class artifacts.

## Common Mistakes

- Skipping `define` and writing evals after implementation (tests-after anti-pattern).
- Setting pass@1 targets too high for genuinely hard tasks (use pass@3 instead).

## Examples

### Example — define evals before implementing

User: "I'm about to add a new auth flow. Define evals first."

```
/ai-reliability-eval define auth-flow
```

Walks through capability evals (can-create-account, can-validate-email, can-hash-password) and regression evals (login-still-works), sets pass@3 targets, writes `.ai-engineering/evals/auth-flow.md`.

## Integration

Called by: user directly, `/ai-build`, `/ai-verify` (regression mode). Calls: test runners (code graders), the model (model graders), stack-specific tools. See also: `/ai-test` (code correctness), `/ai-verify` (current quality gates).

$ARGUMENTS
