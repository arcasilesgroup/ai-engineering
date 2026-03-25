# Autopilot Manifest: spec-075

## Split Strategy
By-test-domain: VCS CLI (sub-001), stack operations (sub-002), install pipeline e2e (sub-003). All independent — each creates a new test file.

## Sub-Specs

| # | Title | Status | Depends On | Files |
|---|-------|--------|------------|-------|
| sub-001 | VCS CLI Tests | planning | None | `tests/unit/test_vcs_cmd.py` |
| sub-002 | Stack Operation Tests | planning | None | `tests/unit/test_stack_operations.py` |
| sub-003 | Install Pipeline E2E Tests | planning | None | `tests/e2e/test_install_pipeline.py` |

## Totals
- Sub-specs: 3
- Dependency chain depth: 0 (all independent)
