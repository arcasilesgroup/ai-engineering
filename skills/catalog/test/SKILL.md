---
name: test
description: Use when working with tests — writing new tests, enforcing TDD (RED-GREEN-REFACTOR), analyzing coverage gaps, defining test strategy.
effort: high
tier: core
capabilities: [tool_use]
---

# /ai-test

TDD enforcement and test strategy. Pairs with `/ai-debug` for failures
where the fix is not obvious.

## RED-GREEN-REFACTOR (strict)

1. **RED** — write the failing test. Run it. Confirm it fails for the
   right reason.
2. **GREEN** — write the minimum code to make the test pass. No
   speculation, no future-proofing.
3. **REFACTOR** — clean structure with all tests still green.

## Test strategy (dual pyramid)

- **Deterministic pyramid** (gate `pytest` / `bun test`):
  pure domain ≥80% coverage, adapters with contract tests, ports always
  mockable.
- **Probabilistic pyramid** (evals, dashboard NOT gate):
  golden datasets per critical skill via `promptfoo` + `deepeval`.
  Hard gate only on `commit`, `release-gate`, `security`, `verify` skills
  if score drops 2 runs in a row.

## Coverage targets

- Domain (pure logic): **≥80%** required
- Application (use cases): **≥70%**
- Adapters: contract tests required (no coverage threshold)
- E2E: smoke flows only (5-10 tests)

## Property-based testing

Use `fast-check` (TS) or `hypothesis` (Python) for invariants such as:

- "any valid id format is accepted"
- "expiresAt - issuedAt always equals TTL[severity] in days"
- "state machine never reaches an illegal state"

## Common mistakes

- Writing tests that pass without the implementation
- Mocking the system under test instead of its dependencies
- Skipping REFACTOR
- Asserting on implementation details
