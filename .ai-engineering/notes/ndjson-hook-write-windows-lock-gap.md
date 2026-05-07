# NDJSON hook-side write lacks Windows-safe lock

**Discovery Date**: 2026-05-06
**Context**: spec-125 cross-OS/IDE/AI provider audit during /ai-dispatch convergence
**Spec**: spec-125 (gap surfaced, NOT in scope) — candidate next-spec

## Problem

Hook-side appender to `framework-events.ndjson` writes without acquiring the canonical `artifact_lock`. Pkg-side writer at `src/ai_engineering/state/observability.py:173,188` correctly wraps writes with `artifact_lock(project_root, "framework-events")`. Hook-side writer at `.ai-engineering/scripts/hooks/_lib/observability.py:215` (`append_framework_event`) does not.

Asymmetry creates Windows multi-IDE concurrency risk:
- POSIX `open("a")` → `O_APPEND` → atomic for writes < `PIPE_BUF` (≈4KB). Single NDJSON line typically <1KB. Safe in practice.
- Windows `open("a")` → no `O_APPEND` semantics → no atomic-append guarantee under concurrent multi-process writers (Claude Code + Copilot + Gemini + Codex sessions running in parallel).

Pre-existing `framework-events.ndjson` chain break at index 105 (surfaced by T-3.1 `ai-eng audit verify-chain`) may be symptom of exactly this race.

## Findings

`append_framework_event` (canonical hook-side writer):
```python
# .ai-engineering/scripts/hooks/_lib/observability.py:215
with path.open("a", encoding="utf-8") as f:
    f.write(line + "\n")
```

Pkg-side counterpart uses lock:
```python
# src/ai_engineering/state/observability.py
with artifact_lock(project_root, "framework-events"):
    # ... append ...
```

`artifact_lock` (`src/ai_engineering/state/locking.py`) already implements cross-OS branch (`msvcrt.locking` for Windows, `fcntl.flock` for POSIX) at `state/locks/framework-events.lock`. Lock file pattern matches REQUIRED_DIRS contract per spec-125 D-125-09.

Hash chain (`prev_event_hash`) detects post-hoc corruption but does NOT prevent it. Detection without prevention shifts cost from write-time (cheap lock) to recovery-time (expensive replay/repair).

## Code Examples

Proposed fix — port pkg-side pattern to hook-side:

```python
# .ai-engineering/scripts/hooks/_lib/observability.py
from _lib.locking import artifact_lock  # new helper, mirror of pkg-side

def append_framework_event(project_root: Path, entry: dict) -> None:
    path = framework_events_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    # ... build payload, hash chain ...
    line = json.dumps(payload, sort_keys=True, default=_json_serializer)
    with artifact_lock(project_root, "framework-events"):
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
```

Hook-side cannot import from `src/ai_engineering/state/locking.py` (cross-layer boundary violation). Either:
- **Option A**: duplicate `_acquire_lock` / `_release_lock` cross-OS branch into `.ai-engineering/scripts/hooks/_lib/locking.py` (~30 LOC). Lowest coupling.
- **Option B**: extract `locking` into shared module under `.ai-engineering/scripts/hooks/_lib/` and re-export from `src/ai_engineering/state/locking.py`. Single SSOT but inverts current dependency direction.

## Pitfalls

- POSIX dev environment will NOT surface this bug — `O_APPEND` masks it. Issue only manifests on Windows multi-IDE concurrent sessions.
- Hash-chain detection creates false confidence: "we'll know if it breaks" ≠ "it won't break".
- Don't import `ai_engineering.state.locking` from hook scripts — hook scripts MUST be standalone (no editable install dependency at hook execution time).
- Lock acquisition adds latency to PostToolUse hook critical path. Pre-commit budget is <1s (CLAUDE.md). Verify lock contention doesn't blow budget under realistic load.
- Hook integrity manifest (`hooks-manifest.json`, `enforce` mode default) requires regen after any edit to `_lib/observability.py` — `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py`.

## Related

- spec-125 D-125-09 — canonical state surface (REQUIRED_DIRS includes `locks/`)
- Article III (CONSTITUTION.md) — single immutable append-only audit log
- spec-122-b D-122-06 — state plane consolidation
- T-3.1 verify finding — chain break at index 105 (potential symptom)
- `src/ai_engineering/state/locking.py` — canonical cross-OS lock helper (msvcrt/fcntl branch)
- `src/ai_engineering/state/observability.py:173,188` — pkg-side reference implementation
- `.ai-engineering/scripts/hooks/_lib/observability.py:198-216` — gap location
