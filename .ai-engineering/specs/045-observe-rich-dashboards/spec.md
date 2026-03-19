---
id: "045"
slug: "observe-rich-dashboards"
status: "in-progress"
created: "2026-03-09"
size: "M"
tags: ["cli", "ux", "observe", "rich", "dashboard"]
branch: "feat/045-observe-rich-dashboards"
pipeline: "standard"
decisions: []
---

# Spec 045 — Observe Rich Dashboards + Dual-Output

## Problem

The 5 `ai-eng observe` dashboards (engineer, team, ai, dora, health) output raw markdown strings via `typer.echo()`. The output is plain text — no colors, no visual hierarchy, no progress bars, no semantic indicators. This contrasts with other CLI commands (doctor, gate, install) that use Rich primitives (`cli_ui.py`) for branded, color-coded output with clear visual structure.

Additionally, observe is the only major command that lacks `--json` support, breaking the dual-output pattern established by `cli_output.py` and the `ai-cli` skill contract.

## Solution

1. **Rich human output**: Replace raw markdown string rendering with Rich-formatted output using `cli_ui.py` primitives (headers, kv, status_line, suggest_next) plus new dashboard-specific primitives (progress bars, score badges, section panels).

2. **Dual-output routing**: Add `--json` flag to observe, routing through `cli_output.py`'s `output()` function. Each mode returns a structured dict for JSON and a human rendering function for Rich.

3. **New cli_ui primitives**: Add reusable dashboard primitives to `cli_ui.py`:
   - `progress_bar(label, value, max_val, threshold?)` — colored bar with percentage
   - `score_badge(score, label?)` — semaphore badge (GREEN/YELLOW/RED)
   - `metric_table(rows)` — aligned metric table with semantic coloring
   - `section(title)` — styled section header (lighter than `header()`)

## Scope

### In Scope

- Refactor all 5 observe mode functions to use Rich output
- Add `--json` flag with SuccessEnvelope response
- Add 3-4 new cli_ui primitives for dashboard rendering
- Maintain identical data/metrics — only rendering changes
- Respect NO_COLOR, TERM=dumb, non-TTY (auto-suppressed via existing `get_console()`)

### Out of Scope

- Changing metric calculation logic (signals.py)
- Adding new metrics or data sources
- Changing the `observe_cmd` entry point signature beyond adding `--json`
- Rich Tables with borders (too heavy for CLI dashboards — prefer aligned KVs)
- Sparkline trends (requires historical data infrastructure not yet available)

## Acceptance Criteria

1. All 5 observe modes render with Rich formatting (colors, bars, icons)
2. `ai-eng observe health --json` outputs valid SuccessEnvelope JSON
3. All 5 modes support `--json` with structured data
4. Existing cli_ui primitives are reused (header, kv, status_line, suggest_next)
5. New primitives follow cli_ui conventions (stderr, theme, NO_COLOR safe)
6. Output is visually consistent with doctor/gate commands
7. No regression in metric data accuracy
8. Tests pass for both human and JSON output modes

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | Use progress bars for percentages, not Rich Tables | Tables add border noise in terminal; bars are more scannable |
| D2 | Route human output to stderr per CLIG | Consistent with cli_ui.py and cli skill contract |
| D3 | Score badge uses emoji semaphore (colored circle) | Terminal-universal, works in TTY and non-TTY |
| D4 | New primitives go in cli_ui.py, not a new module | Single shared module, avoids fragmentation |
