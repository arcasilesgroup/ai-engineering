---
name: ai-eval
description: "Use when measuring AI system reliability over time: defining pass/fail criteria before implementation, running capability checks, detecting regressions after prompt or model changes, or tracking pass@k metrics. Trigger for 'how reliable is this', 'did my changes break anything', 'measure AI performance', 'define success criteria', 'eval this'. Distinct from /ai-test (code correctness) and /ai-verify (quality gates) — evals measure AI task completion consistency."
effort: max
argument-hint: "define|check|report|regression [feature]"
tags: [quality, evals, improvement]
---



# Eval

## Purpose

Eval-Driven Development (EDD) treats evals as the unit tests of AI development. Define pass/fail criteria before writing code. Measure AI reliability with pass@k metrics. Track regressions across prompt, agent, and model changes. Evals answer the question: "Can the AI do this reliably?"

**Key distinction**: `ai-verify` checks current code quality (linting, coverage, security). `ai-eval` measures AI reliability over time (can the agent complete this task consistently?).

## When to Use

- `define`: defining pass/fail criteria before implementation (EDD principle)
- `check`: running current evals and reporting status mid-implementation
- `report`: generating full eval report after implementation
- `regression`: ensuring changes to prompts, agents, or models don't break existing capabilities

## Process

### Mode: define (Before Coding)

**EDD principle: define pass/fail before code.**

1. Identify the capability being built or changed
2. Write capability evals (can the AI do this new thing?)
3. Write regression evals (do existing things still work?)
4. Set success metrics (pass@k targets)
5. Store eval definition at `.ai-engineering/evals/<feature-name>.md`

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

### Mode: check (During Implementation)

1. Read the eval definition from `.ai-engineering/evals/<feature-name>.md`
2. Run each capability eval, record PASS/FAIL
3. Run regression evals via existing test suites
4. Report current status with pass@k counts
5. Identify which evals still fail and why

### Mode: report (After Implementation)

1. Run all capability and regression evals
2. Calculate pass@k and pass^k metrics
3. Generate structured report

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

4. Store report at `.ai-engineering/evals/<feature-name>.log`

### Mode: regression

Baseline is created automatically on the first `report` run. If `baseline.json` does not exist, the current run becomes the initial baseline.

1. Load baseline from `.ai-engineering/evals/baseline.json`
2. Run all regression evals against current state
3. Compare against baseline results
4. Flag any degradation

```markdown
[REGRESSION EVAL: feature-name]
Baseline: SHA or checkpoint name
Tests:
  - existing-test-1: PASS/FAIL
  - existing-test-2: PASS/FAIL
  - existing-test-3: PASS/FAIL
Result: X/Y passed (previously Y/Y)
```

## Quick Reference

### Eval Types

| Type | Question It Answers | When to Use |
|------|-------------------|-------------|
| Capability | Can the AI do this new thing? | New features, new skills |
| Regression | Do existing things still work? | Prompt changes, model updates, agent refactors |

### Grader Types

| Grader | How It Works | When to Use | Example |
|--------|-------------|-------------|---------|
| Code | Deterministic checks (grep, test runners, build) | Verifiable outputs, structured results | `grep -q "export function handleAuth" src/auth.ts && echo "PASS"` |
| Model | Claude evaluates open-ended output (score 1-5) | Prose quality, code style, creative output | Prompt: "Does it solve the stated problem? Score 1-5" |
| Human | Flag for manual review with risk level | Security decisions, UX judgment, ambiguous cases | `[HUMAN REVIEW REQUIRED] Risk Level: HIGH` |

### Metrics

| Metric | Definition | Typical Target |
|--------|-----------|----------------|
| pass@1 | First attempt success rate | Varies by difficulty |
| pass@3 | At least one success in 3 attempts | > 90% |
| pass@k | At least one success in k attempts | Depends on criticality |
| pass^3 | All 3 trials succeed | 100% for critical paths |
| pass^k | All k trials succeed | Use for regression evals |

### Eval Lifecycle

```
Define --> Implement --> Evaluate --> Report
  |                                    |
  +-------- regression loop -----------+
```

## Storage

```
.ai-engineering/
  evals/
    <feature-name>.md      # Eval definition
    <feature-name>.log     # Eval run history
    baseline.json           # Regression baselines
```

## Best Practices

1. **Define evals BEFORE coding** -- forces clear thinking about success criteria
2. **Run evals frequently** -- catch regressions early
3. **Track pass@k over time** -- monitor reliability trends
4. **Use code graders when possible** -- deterministic > probabilistic
5. **Human review for security** -- never fully automate security checks
6. **Keep evals fast** -- slow evals don't get run
7. **Version evals with code** -- evals are first-class artifacts

## Integration

- **Called by**: user directly, `/ai-dispatch`, `/ai-verify` (can trigger regression evals)
- **Calls**: test runners (code graders), Claude (model graders), stack-specific tools
- **Complements**: `ai-verify` (verify = current quality gates, eval = AI reliability over time), `ai-test` (tests verify code correctness, evals verify AI task completion)
- **See also**: `/ai-test` (write tests first; eval measures reliability of AI outputs)

## Common Mistakes

- Skipping the define phase and writing evals after implementation (same anti-pattern as tests-after)
- Using only model graders when code graders would be deterministic and faster
- Not tracking pass@k over time (you lose the reliability trend data)
- Conflating evals with tests (tests verify code, evals verify AI capability)
- Setting pass@1 targets too high for genuinely hard tasks (use pass@3 instead)
- Not running regression evals after prompt or model changes
- Storing evals outside the project (they should version with the code)

$ARGUMENTS
