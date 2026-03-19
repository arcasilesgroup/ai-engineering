## CLI UX Conventions

### Dual-Output Routing

All user-facing commands support both JSON and Rich output:
- **JSON path**: `emit_success(command, data, [NextAction(...)])` → **stdout**
- **Human path**: `result_header()`, `kv()`, `status_line()`, `suggest_next()` → **stderr**
- Rule: JSON goes to stdout, human messaging goes to stderr (CLIG guideline)
- Use `output()` router from `cli_output.py` for clean branching

### JSON Envelope Contract

```
Success: { ok: true, command: str, result: dict, next_actions: [...] }
Error:   { ok: false, command: str, error: { message, code }, fix: str, next_actions: [...] }
```

HATEOAS `NextAction`: `{ command: str, description: str, params?: dict }` — suggest follow-up commands.
Use `truncate_list(items, max_items=20)` for large collections to protect agent context windows.

### Data Model Convention

Every result model must implement:
- `to_dict()`: JSON-serializable dict for the envelope
- `to_markdown()`: human-readable markdown string

Serialization rules: `Path` → `.as_posix()`, dates → `.isoformat()`, enums → `.value`.

### Color Semantics

| Style | Color | Use |
|-------|-------|-----|
| `[success]` | green | Passed, created, completed |
| `[error]` | red | Failed, blocked, critical |
| `[warning]` | yellow | Degraded, skipped, attention |
| `[info]` | blue | Neutral status, counts |
| `[brand]` | teal `#00D4AA` | Brand accent |
| `[muted]` | dim | Secondary info |
| `[path]` | teal underline | File paths |

Respect `NO_COLOR`, `TERM=dumb`, and non-TTY detection (handled by `get_console()`).

### Progress Indicators

- `spinner(description)`: single-step indeterminate wait
- `step_progress(total, description)`: multi-step tracker with `tracker.step(msg)`
- Auto-suppressed in: JSON mode, non-TTY (CI, piped output)
- Transient by default — spinners disappear when done
- **Gate hooks (pre-commit, commit-msg, pre-push): NEVER add progress indicators**

### Reference Files

| File | Purpose |
|------|---------|
| `cli_envelope.py` | JSON envelope (`SuccessEnvelope`, `ErrorEnvelope`, `NextAction`) |
| `cli_ui.py` | Rich human output (`kv`, `status_line`, `result_header`, `suggest_next`) |
| `cli_output.py` | Dual-mode router (`is_json_mode`, `output`) |
| `cli_progress.py` | Spinner and step_progress context managers |
