---
spec: "041"
phases: 5
agents: [build]
---

# Plan — Observe Quick Wins

## Architecture

### Health History Schema
```json
{
  "entries": [
    {
      "date": "2026-03-09",
      "overall": 59,
      "semaphore": "RED",
      "components": {
        "gate_pass_rate": 84.6,
        "delivery_velocity": 100,
        "dora_frequency": 25,
        "test_confidence": 26.4
      }
    }
  ]
}
```

### Smart Actions Logic
```
For each component with score < 80:
  compute estimated_gain = (100 - score) / num_components
  map component to specific action + command
Sort by estimated_gain descending
Show top 3
```

### Self-Optimization Hints
```
Pattern detectors (from existing data):
  - decision_reuse_low:  cache_hit_rate < 50%  → "Save decisions to decision-store"
  - gate_failures_high:  pass_rate < 80%       → "Run ruff format before committing"
  - no_checkpoints:      no checkpoint found    → "Use checkpoint save for session recovery"
  - token_waste:         utilization > 90%      → "Sessions nearing context limit"
  - session_idle:        0 session events       → "No session data — emit via checkpoint save"
```

## Data Flow
```
signals.py:save_health_snapshot()  ← called by observe_health()
signals.py:load_health_history()   ← called by observe_health()
    ↓
observe.py:observe_health()  ← direction indicator + smart actions
observe.py:observe_ai()      ← self-optimization hints
```

## Session Map

| Phase | Agent | Tasks | Gate |
|-------|-------|-------|------|
| 0 | execute | Scaffold spec, create branch | Branch ready |
| 1 | build | Health history persistence | History tests pass |
| 2 | build | Smart actions with score gain | Action tests pass |
| 3 | build | Self-optimization hints | Hints tests pass |
| 4 | build | Verification | ruff + ty + pytest green |

## Execution Order

- Phase 1 → Phase 2 (smart actions use history for direction)
- Phase 3 independent (AI dashboard, no dependency on health changes)
- Phase 4 last (verification)

## Files (6)

| # | File | Action |
|---|------|--------|
| 1 | `src/ai_engineering/lib/signals.py` | Edit — `save_health_snapshot()`, `load_health_history()` |
| 2 | `src/ai_engineering/cli_commands/observe.py` | Edit — direction indicator, smart actions, self-optimization hints |
| 3 | `tests/unit/test_health_history.py` | Create — history persistence tests |
| 4 | `tests/unit/test_cli_observe.py` | Edit — smart actions + hints assertions |
| 5 | `src/ai_engineering/policy/test_scope.py` | Edit — map new test file |
| 6 | `.ai-engineering/context/specs/041-observe-quick-wins/tasks.md` | Edit — progress tracking |
