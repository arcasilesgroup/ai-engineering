---
spec: "041"
total: 19
completed: 19
last_session: "2026-03-09"
next_session: null
---

# Tasks — Observe Quick Wins

### Phase 0: Scaffold + Branch [S]
- [x] 0.1 Create spec-041 directory and files
- [x] 0.2 Update `_active.md` to point to spec-041
- [x] 0.3 Create branch `feat/041-observe-quick-wins`
- [x] 0.4 Commit scaffold

### Phase 1: Health History Persistence [S]
- [x] 1.1 Add `save_health_snapshot(project_root, overall, semaphore, components)` to `lib/signals.py` — append to `state/health-history.json`, max 12 entries rolling
- [x] 1.2 Add `load_health_history(project_root)` to `lib/signals.py` — returns list of entries
- [x] 1.3 Wire `save_health_snapshot()` at end of `observe_health()`
- [x] 1.4 Add direction indicator (↑↓→) to health dashboard header
- [x] 1.5 Create `tests/unit/test_health_history.py` — save, load, rolling window, direction (14 tests)

### Phase 2: Smart Actions with Score Gain [S]
- [x] 2.1 Add smart action logic inline in `observe_health()` (simpler than separate helper)
- [x] 2.2 Replace hardcoded actions in `observe_health()` with dynamic smart actions
- [x] 2.3 Add smart action tests to `tests/unit/test_cli_observe.py` (2 tests)

### Phase 3: Self-Optimization Hints [S]
- [x] 3.1 Add `## Self-Optimization Hints` section to `observe_ai()`
- [x] 3.2 Implement 5 pattern detectors using existing data
- [x] 3.3 Add self-optimization tests to `tests/unit/test_cli_observe.py` (5 tests)

### Phase 4: Verification [S]
- [x] 4.1 Map `test_health_history.py` in `test_scope.py`
- [x] 4.2 `ruff check` + `ruff format` — zero errors
- [x] 4.3 `ty` — no new errors
- [x] 4.4 `pytest` — all tests pass (1754/1754)
