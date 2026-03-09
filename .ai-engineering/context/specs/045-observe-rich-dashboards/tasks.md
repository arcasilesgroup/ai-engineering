---
spec: "045"
total: 14
completed: 14
last_session: "2026-03-10"
next_session: "Phase 5 — Integration + Polish"
---

# Tasks — Observe Rich Dashboards + Dual-Output

## Phase 0: Scaffold [S]
- [x] 0.1 Create spec files and activate
- [x] 0.2 Commit scaffold

## Phase 1: Dashboard Primitives [S]
- [x] 1.1 Add `section(title)` to cli_ui.py — styled section header
- [x] 1.2 Add `progress_bar(label, value, max_val, threshold?)` to cli_ui.py
- [x] 1.3 Add `score_badge(score, label?)` to cli_ui.py — semaphore badge
- [x] 1.4 Add `metric_table(rows)` to cli_ui.py — aligned metric rows with coloring

## Phase 2: Dual-Output Infrastructure [S]
- [x] 2.1 Add `--json` flag to `observe_cmd`
- [x] 2.2 Refactor mode functions to return structured dict
- [x] 2.3 Wire through `output()` router from cli_output.py

## Phase 3: Rich Rendering — Health + Engineer [M]
- [x] 3.1 Refactor `observe_health()` — score badge, progress bars, suggest_next
- [x] 3.2 Refactor `observe_engineer()` — sections, kv, status_line, progress_bar

## Phase 4: Rich Rendering — Team + AI + DORA [M]
- [x] 4.1 Refactor `observe_team()` — metric_table, kv, noise ratio bar
- [x] 4.2 Refactor `observe_ai()` — context kv, decision bars, status_lines
- [x] 4.3 Refactor `observe_dora()` — rating badges, benchmark table

## Phase 5: Integration + Polish [S]
- [ ] 5.1 End-to-end test all 5 modes (human + JSON)
- [ ] 5.2 Verify NO_COLOR/non-TTY degradation
