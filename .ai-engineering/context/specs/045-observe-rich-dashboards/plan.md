---
spec: "045"
approach: "serial-phases"
---

# Plan — Observe Rich Dashboards + Dual-Output

## Architecture

### Modified Files

| File | Purpose |
|------|---------|
| `src/ai_engineering/cli_ui.py` | Add dashboard primitives: progress_bar, score_badge, metric_table, section |
| `src/ai_engineering/cli_commands/observe.py` | Refactor 5 modes to Rich output + dual-output routing |
| `tests/test_observe.py` | Update tests for new output format + add JSON tests |

### New Files

None — all changes are modifications to existing files.

## File Structure

```
src/ai_engineering/
  cli_ui.py              # +4 primitives (~40 lines)
  cli_commands/
    observe.py           # Refactor rendering (~720 lines, same size)
tests/
  test_observe.py        # Update + extend
```

## Session Map

### Phase 0: Scaffold [S]
- Create spec files, activate, commit.

### Phase 1: Dashboard Primitives [S]
- Add `progress_bar()`, `score_badge()`, `metric_table()`, `section()` to cli_ui.py.
- Unit tests for new primitives.

### Phase 2: Dual-Output Infrastructure [S]
- Add `--json` flag to `observe_cmd`.
- Refactor each mode function to return both `dict` (for JSON) and render (for human).
- Wire through `cli_output.py` `output()` router.

### Phase 3: Rich Rendering — Health + Engineer [M]
- Refactor `observe_health()` and `observe_engineer()` to use Rich primitives.
- Health: score badge, progress bars for components, semaphore, suggest_next for actions.
- Engineer: section headers, kv pairs, status_lines for gate health, progress_bar for coverage.

### Phase 4: Rich Rendering — Team + AI + DORA [M]
- Refactor `observe_team()`, `observe_ai()`, `observe_dora()` to use Rich primitives.
- Team: event distribution as metric_table, kv for adoption, noise ratio bar.
- AI: context efficiency kv, decision continuity bars, optimization hints as status_lines.
- DORA: rating badges, benchmark table, velocity kv.

### Phase 5: Integration Test + Polish [S]
- End-to-end test: all 5 modes in both human and JSON.
- Verify NO_COLOR/non-TTY graceful degradation.
- Visual review of all dashboards.

## Patterns

- **Data-first**: each mode function computes a result dict first, then renders.
- **Render-last**: human rendering is a closure passed to `output()`.
- **Primitives-only**: all visual output goes through cli_ui.py — no inline Rich markup in observe.py.
