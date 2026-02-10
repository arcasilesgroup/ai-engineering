# Test Strategy

## Purpose

Define what to test, how to structure tests, and how to achieve meaningful coverage. Guides test design decisions for unit, integration, and E2E tests.

## Trigger

- Command: agent invokes test-strategy skill or user asks what/how to test.
- Context: new feature, bug fix, refactoring, coverage gap analysis.

## Procedure

1. **Identify test scope** — determine what needs testing.
   - New behavior: at least one unit or integration test per new function/method.
   - Bug fix: test that reproduces the bug (fails without fix, passes with it).
   - Refactoring: verify existing tests cover the target code first.
   - Governance-critical paths: ≥90% coverage (install, update, hooks, gates, commands).

2. **Choose test level** — select appropriate test type.
   - **Unit tests**: isolated logic, pure functions, model validation, state transformations.
   - **Integration tests**: real filesystem (`tmp_path`), real `git init`, CLI runner, cross-module flows.
   - **E2E tests**: full install/doctor cycle on empty and existing repos.

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
- Coverage on changed code meets threshold (≥80% overall, ≥90% governance-critical).
- Test names clearly describe what is being validated.

## Governance Notes

- No test should depend on external services or network (mock/stub external deps).
- Tests must be deterministic — same result on every run.
- Never use `time.sleep` for synchronization; use proper async patterns or mocking.
- One test file per module: `test_<module>.py` mirrors `<module>.py`.
- Fixtures are shared via `conftest.py`, never duplicated across test files.

## References

- `standards/framework/stacks/python.md` — testing patterns.
- `standards/framework/quality/python.md` — coverage policy.
- `standards/framework/quality/core.md` — quality gates.
