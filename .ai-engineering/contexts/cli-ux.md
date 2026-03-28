# CLI UX Conventions

Framework-managed guidance for human-facing CLI behavior and machine-safe output.

## Dual-Output Routing

All user-facing commands support both JSON and Rich output:
- **JSON path**: `emit_success(command, data, [NextAction(...)])` -> **stdout**
- **Human path**: `result_header()`, `kv()`, `status_line()`, `suggest_next()` -> **stderr**
- Rule: JSON goes to stdout, human messaging goes to stderr (CLIG guideline)
- Use `output()` from `cli_output.py` for clean branching

## JSON Envelope Contract

```json
Success: { "ok": true, "command": "str", "result": {}, "next_actions": [] }
Error:   { "ok": false, "command": "str", "error": { "message": "", "code": "" }, "fix": "", "next_actions": [] }
```

Use HATEOAS-style `NextAction` suggestions for follow-up commands. Use
`truncate_list(items, max_items=20)` for large collections to protect agent
context windows.

## Data Model Convention

Every result model should implement:
- `to_dict()` for JSON-safe output
- `to_markdown()` for human-readable reporting

Serialization rules:
- `Path` -> `.as_posix()`
- dates -> `.isoformat()`
- enums -> `.value`

## Color Semantics

| Style | Color | Use |
|-------|-------|-----|
| `[success]` | green | Passed, created, completed |
| `[error]` | red | Failed, blocked, critical |
| `[warning]` | yellow | Degraded, skipped, attention |
| `[info]` | blue | Neutral status, counts |
| `[brand]` | teal `#00D4AA` | Brand accent |
| `[muted]` | dim | Secondary info |
| `[path]` | teal underline | File paths |

Respect `NO_COLOR`, `TERM=dumb`, and non-TTY detection via `get_console()`.

## Progress Indicators

- `spinner(description)` for single-step indeterminate waits
- `step_progress(total, description)` for multi-step trackers
- Auto-suppressed in JSON mode and non-TTY environments
- Transient by default
- **Gate hooks** (`pre-commit`, `commit-msg`, `pre-push`) never use progress UI

## Reference Files

| File | Purpose |
|------|---------|
| `cli_envelope.py` | JSON envelope (`SuccessEnvelope`, `ErrorEnvelope`, `NextAction`) |
| `cli_ui.py` | Rich human output (`kv`, `status_line`, `result_header`, `suggest_next`) |
| `cli_output.py` | Dual-mode router (`is_json_mode`, `output`) |
| `cli_progress.py` | Spinner and step-progress helpers |
