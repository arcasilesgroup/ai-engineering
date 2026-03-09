---
spec: "041"
total: 16
completed: 0
last_session: "2026-03-09"
next_session: "2026-03-09"
---

# Tasks — Observe Quick Wins

### Phase 0: Scaffold + Branch [S]
- [x] 0.1 Create spec-041 directory and files
- [x] 0.2 Update `_active.md` to point to spec-041
- [x] 0.3 Create branch `feat/041-observe-quick-wins`
- [x] 0.4 Commit scaffold

### Phase 1: Health History Persistence [S]
- [ ] 1.1 Add `save_health_snapshot(project_root, overall, semaphore, components)` to `lib/signals.py` — append to `state/health-history.json`, max 12 entries rolling
- [ ] 1.2 Add `load_health_history(project_root)` to `lib/signals.py` — returns list of entries
- [ ] 1.3 Wire `save_health_snapshot()` at end of `observe_health()`
- [ ] 1.4 Add direction indicator (↑↓→) to health dashboard header
- [ ] 1.5 Create `tests/unit/test_health_history.py` — save, load, rolling window, direction

### Phase 2: Smart Actions with Score Gain [S]
- [ ] 2.1 Add `_smart_actions(components, component_names, scores)` helper to `observe.py`
- [ ] 2.2 Replace hardcoded actions in `observe_health()` with dynamic smart actions
- [ ] 2.3 Add smart action tests to `tests/unit/test_cli_observe.py`

### Phase 3: Self-Optimization Hints [S]
- [ ] 3.1 Add `## Self-Optimization Hints` section to `observe_ai()`
- [ ] 3.2 Implement 5 pattern detectors using existing data
- [ ] 3.3 Add self-optimization tests to `tests/unit/test_cli_observe.py`

### Phase 4: Verification [S]
- [ ] 4.1 Map `test_health_history.py` in `test_scope.py`
- [ ] 4.2 `ruff check` + `ruff format` — zero errors
- [ ] 4.3 `ty` — no new errors
- [ ] 4.4 `pytest` — all tests pass
