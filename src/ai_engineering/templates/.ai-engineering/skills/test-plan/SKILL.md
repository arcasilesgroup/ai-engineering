---
name: test-plan
description: "Design test strategy covering what to test, test tiers, and meaningful coverage; use when planning tests for new features, bug fixes, or refactoring."
version: 1.0.0
tags: [testing, coverage, test-design, tdd]
metadata:
  ai-engineering:
    scope: read-only
    token_estimate: 725
---

# Test Strategy

## Purpose

Define what to test, how to structure tests, and how to achieve meaningful coverage. Guides test design decisions for unit, integration, and E2E tests.

## Trigger

- Command: agent invokes test-strategy skill or user asks what/how to test.
- Context: new feature, bug fix, refactoring, coverage gap analysis.

## When NOT to Use

- **Running tests** (executing test suites, collecting results) — use `test-run` instead. Test-plan designs tests; test-run executes them.
- **Coverage metrics** (measuring coverage, auditing gaps) — use `audit` for metrics or `test-gap` for capability mapping.
- **Debugging test failures** — use `debug` instead.

## Procedure

1. **Identify test scope** — determine what needs testing.
   - New behavior: at least one unit or integration test per new function/method.
   - Bug fix: test that reproduces the bug (fails without fix, passes with it).
   - Refactoring: verify existing tests cover the target code first.
   - Governance-critical paths: 100% coverage (install, update, hooks, gates, commands).

2. **Choose test tier** — select appropriate tier per `standards/framework/stacks/python.md` Test Tiers.
   - **Unit** (`@pytest.mark.unit`): isolated logic, pure functions, model validation, state transformations. No I/O. Runs at pre-commit gate.
   - **Integration** (`@pytest.mark.integration`): real filesystem (`tmp_path`), real `git init`, CLI runner, cross-module flows. Runs at pre-push gate.
   - **E2E** (`@pytest.mark.e2e`): full install/doctor cycle on empty and existing repos. Runs at PR gate.
   - **Live** (`@pytest.mark.live`): tests requiring external APIs. Opt-in via `AI_ENG_LIVE_TEST=1`. Not part of standard CI.

3. **Structure tests** — follow AAA pattern.
   - **Arrange**: set up preconditions, fixtures, test data.
   - **Act**: execute the function/operation under test.
   - **Assert**: verify expected outcomes.

4. **Design test cases** — cover meaningful scenarios.
   - Happy path: normal expected behavior.
   - Edge cases: empty inputs, boundary values, max size, special characters.
   - Error paths: invalid inputs, missing files, permission errors, network failures.
   - Cross-OS: paths with separators, shell scripts for Bash and PowerShell.

5. **Write fixtures** — shared setup in `conftest.py`.
   - Use `tmp_path` for filesystem operations.
   - Scope fixtures appropriately (`function`, `module`, `session`).
   - Avoid fixture chains longer than 3 levels.

6. **Name tests** — follow convention: `test_<unit>_<scenario>_<expected_outcome>`.
   - Example: `test_install_empty_repo_creates_full_structure`.
   - Example: `test_gate_precommit_secrets_detected_blocks_commit`.

## Output Contract

- Test file(s) following project structure conventions.
- Tests pass with `pytest -v`.
- Coverage on changed code meets threshold (100%).
- Test names clearly describe what is being validated.

## Governance Notes

- No test should depend on external services or network (mock/stub external deps).
- Tests must be deterministic — same result on every run.
- Never use `time.sleep` for synchronization; use proper async patterns or mocking.
- One test file per module: `test_<module>.py` mirrors `<module>.py`.
- Fixtures are shared via `conftest.py`, never duplicated across test files.

## References

- `standards/framework/stacks/python.md` — testing patterns.
- `standards/framework/quality/core.md` — coverage policy and quality gates.
- `agents/build.md` — implementation agent that writes regression tests.
- `agents/review.md` — review agent that assesses test completeness.
