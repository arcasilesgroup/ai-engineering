# Plan: spec-095 — ai-eng install: auto-infer mode, single tree UX

## Pipeline: standard
## Phases: 4
## Tasks: 12 (build: 8, verify: 2, guard: 2)

### Phase 1: Unified tree renderer
**Gate**: New tree renderer passes unit tests; existing update tests adapted.

- [x] T-1.1: Write failing tests for unified tree renderer — DONE (6 tests RED)
- [x] T-1.2: Rewrite `render_update_tree` in `cli_ui.py` — DONE (6/6 GREEN)
- [x] T-1.3: Adapt existing tree tests in `test_cli_ui.py` — DONE (32/32 GREEN)

### Phase 2: Install command — auto-infer + flags
**Gate**: `install_cmd` reinstall path uses auto-infer; `--fresh` and `--reconfigure` flags work; wizard gated correctly. Unit tests pass.

- [x] T-2.1: Write failing tests for new install reinstall flow — DONE (9 tests RED)
- [x] T-2.2: Rewrite `install_cmd` reinstall path in `core.py` — DONE (9/9 GREEN, 147/147 installer GREEN)
- [x] T-2.3: Remove `render_reinstall_options()` from `installer/ui.py`, clean imports — DONE
- [x] T-2.4: Remove redundant mode auto-promotion from `install_with_pipeline` — DONE (e2e tests adapted)

### Phase 3: Update command — eliminate double render
**Gate**: Interactive update shows preview tree + post-apply one-liner (or failure-only tree). Integration tests pass.

- [x] T-3.1: Write failing tests for update post-apply output — DONE (2 RED, 1 guard GREEN)
- [x] T-3.2: Modify `_render_update_result` post-apply: one-liner on success, failure-only tree — DONE
- [x] T-3.3: Adapt 2 pre-existing update integration tests — DONE (25/25 GREEN)

### Phase 4: Verification
**Gate**: All tests green. Ruff clean. Manual smoke test scenarios documented.

- [x] T-4.1: Full test suite (2788 passed), ruff clean, format clean — DONE
- [x] T-4.2: Governance check — pragma:no-cover stub removed, no hardcoded lists, no gates weakened — DONE
