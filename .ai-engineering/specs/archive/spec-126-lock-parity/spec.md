---
spec: spec-126
title: Hook-side NDJSON Append Lock Parity
status: approved
effort: small
---

# Spec 126 — Hook-side NDJSON Append Lock Parity

## Summary

Hook-side appenders to `framework-events.ndjson` write without acquiring the
canonical `artifact_lock`, while the pkg-side writer at
`src/ai_engineering/state/observability.py:173,188` does. Asymmetry creates a
Windows multi-IDE concurrency race: POSIX `O_APPEND` masks the bug locally,
but Windows offers no atomic-append guarantee for concurrent multi-process
writers (Claude Code + Copilot + Gemini + Codex). The pre-existing chain
break at index 105 of `framework-events.ndjson`, surfaced by spec-125 T-3.1
`ai-eng audit verify-chain`, is a probable symptom. Three hook-side writers
target the same chain file unlocked: `_lib/observability.py:217`,
`_lib/hook-common.py:237`, `_lib/trace_context.py:157`. Hash chain detects
post-hoc corruption but does not prevent it; this spec closes the prevention
gap.

## Goals

- All 3 hook-side writers to `framework-events.ndjson` wrap appends in
  `artifact_lock("framework-events")`. Hash computation and write happen
  inside the same critical section (mirrors pkg-side
  `_append_framework_event_locked`).
- New `.ai-engineering/scripts/hooks/_lib/locking.py` exposes
  `artifact_lock(project_root, artifact_name)` with cross-OS branch
  (`msvcrt.locking` on Windows, `fcntl.flock` on POSIX), byte-for-byte
  equivalent to `src/ai_engineering/state/locking.py` (excluding module
  docstring + import block).
- Lock acquisition uses bounded retry: 3 attempts, 50 ms backoff between
  attempts. On final failure, emit a `framework_error` with
  `detail.error_code = "lock_acquisition_failed"` and fall back to an
  unlocked append (preserves existing fail-open posture for telemetry).
- New `tests/unit/hooks/test_locking_parity.py` fails CI on any byte-level
  divergence between hook-side `_lib/locking.py` and pkg-side
  `state/locking.py` (excluding module docstring and import block).
- New `tests/unit/hooks/test_ndjson_concurrent_append.py` (`@pytest.mark.slow`)
  runs N=8 workers × M=50 appends via `multiprocessing`, asserts final line
  count = N×M and `verify_chain` passes end-to-end. Marker wired into
  `test-hooks-matrix.yml` so it executes on Linux + macOS + Windows.
- `.ai-engineering/state/hooks-manifest.json` regenerated for the 3 modified
  hook lib files via `regenerate-hooks-manifest.py`. CI `--check` mode
  catches forgotten regen.
- Hot-path latency budgets preserved: pre-commit < 1 s (CLAUDE.md SLO);
  nominal PostToolUse path adds no measurable regression vs baseline (lock
  held < 2 ms in single-writer steady state, validated in stress test
  timing assertion).

## Non-Goals

- **Repair the existing chain break at index 105** of
  `framework-events.ndjson`. Forensics-preserving repair tool deferred to a
  follow-up spec. Prevention only here.
- **Lock generic NDJSON helpers** (`_lib/instincts.py:112`,
  `_lib/runtime_state.py:213`). These write different files (instincts
  store, runtime state) with no shared race against the events chain.
  Separate concern, separate spec if needed.
- **Lock debug-log writers** in `mcp-health.py`, `observe.py`,
  `instinct-extract.py`, `prompt-injection-guard.py:733`. Non-audit-grade,
  per-script log files; corruption is acceptable.
- **Pkg-side `state/observability.py` changes.** Already correctly locked;
  out of scope.
- **Cross-IDE adapter changes.** Copilot / Gemini / Codex bash + PS1
  wrappers delegate to the canonical Python script unchanged; no
  IDE-specific work.
- **Extract a unified `safe_append_ndjson(...)` chokepoint helper.**
  Tempting but expands LOC and migrates writers to different files (see
  Non-Goal #2). Defer until a second use case justifies the abstraction.

## Decisions

### D-126-01 — Drift-test-enforced duplication of lock primitive

Hook scripts must remain standalone (no editable-install dependency at hook
execution time per CLAUDE.md and Article V). We duplicate
`_acquire_lock` / `_release_lock` / `artifact_lock` into a new
`.ai-engineering/scripts/hooks/_lib/locking.py` (~30 LOC). To mitigate
silent drift on this security-relevant primitive, `test_locking_parity.py`
diffs the two files byte-by-byte (excluding module docstring + import
block) and fails CI on any divergence. **Rationale**: a re-export from
hook → pkg would invert the current dependency direction (pkg → hook) and
violate the hook-standalone contract; pure duplication risks silent drift;
duplication-with-parity-test is the only option that satisfies both
constraints.

### D-126-02 — Prevention only; defer chain repair

The chain break at index 105 is a probable symptom of the bug this spec
prevents, but repairing it requires a separate forensics-preserving tool
(`ai-eng audit repair-chain --from <index>`). **Rationale**: shipping
prevention now stops the bleeding; repair is independent (different files,
different review surface, different risk profile) and benefits from being
shipped after prevention is verified in production. Truncate-and-rotate is
rejected because it destroys audit forensics on an audit-grade artifact.

### D-126-03 — Mock unit test + matrix concurrent stress test

Mock-only assertions (verify `artifact_lock` called before `f.write`) are
insufficient: pkg-side already had a lock and the chain still broke,
indicating the hook-side gap. Mock proves wiring; stress proves behavior.
Stress test marked `@pytest.mark.slow`, runs in `test-hooks-matrix.yml`
across Linux + macOS + Windows. **Rationale**: the bug is invisible
without concurrency on Windows; only a real concurrent test can catch
regressions. Mock layer keeps fast unit signal in pre-commit.

### D-126-04 — Fix all 3 `framework-events.ndjson` writers; defer generic helpers

Three hook-side writers target the same chain file: `_lib/observability.py`,
`_lib/hook-common.py`, `_lib/trace_context.py`. Fixing only one (the note's
target) leaves the race intact. Generic NDJSON helpers
(`_lib/instincts.py`, `_lib/runtime_state.py`) write *different* files and
do not race with the events chain. **Rationale**: scope is the chain file,
not the function; partial fix is no fix.

### D-126-05 — Bounded retry then fail-open with telemetry

Lock acquisition retries 3 times with 50 ms backoff (max 150 ms added
latency). On final failure, emit `framework_error` with
`detail.error_code = "lock_acquisition_failed"` and append unlocked.
**Rationale**: fail-closed risks breaking user sessions on transient lock
errors (NFS hiccup, Windows antivirus scan-lock); pure fail-open throws
away protection unnecessarily on transients. Bounded retry recovers most
transient failures within the PostToolUse SLO; telemetry surfaces
persistent contention for follow-up. Aligns with the existing fail-open
culture in `hook-common.py:233`.

## Risks

- **Drift between pkg-side and hook-side locking copies** — *mitigated* by
  `test_locking_parity.py` byte-diff CI gate (D-126-01).
- **Lock contention adds latency under multi-IDE concurrent load** —
  *mitigated* by bounded retry (D-126-05) and stress-test timing
  assertion (lock held < 2 ms steady state, end-to-end run under N×M
  budget).
- **Hook integrity manifest regen forgotten on edit** — *mitigated* by
  existing `regenerate-hooks-manifest.py --check` CI gate (CLAUDE.md hook
  integrity contract). Three lib files in scope.
- **TOCTOU on `prev_event_hash` compute** — pkg-side reference computes
  hash inside the lock (`_append_framework_event_locked`). Hook-side fix
  must mirror this; computing hash outside the lock would let two writers
  observe the same prev_hash and append two entries with identical
  pointer, perpetuating the same race. Acceptance criteria: hash compute
  and write must be inside the same `with artifact_lock(...)` block.
- **Stress test flakiness on Windows runner** — *mitigated* by tuning
  N=8 M=50 (proven safe in similar fcntl/msvcrt benchmarks); allow one CI
  retry on transient infra flake but **not** on assertion failure.
- **Repair of chain break at index 105 still pending** — *mitigated* by
  documenting in `audit_chain` reader that the existing break is a known
  legacy quirk (`verify-chain` may need a `--from <index>` flag in the
  follow-up spec); does not block this prevention work from shipping.

## References

- doc: .ai-engineering/notes/ndjson-hook-write-windows-lock-gap.md
- doc: src/ai_engineering/state/locking.py (canonical lock impl, mirror source)
- doc: src/ai_engineering/state/observability.py (pkg-side reference at lines 173, 188)
- doc: .ai-engineering/scripts/hooks/_lib/observability.py (gap location, line 217)
- doc: .ai-engineering/scripts/hooks/_lib/hook-common.py (second writer, line 237)
- doc: .ai-engineering/scripts/hooks/_lib/trace_context.py (third writer, line 157)
- doc: CONSTITUTION.md Article III (single immutable append-only audit log)
- doc: .github/workflows/test-hooks-matrix.yml (Linux/macOS/Windows test matrix)
- spec: spec-125 (parent audit; D-125-09 canonical state surface)
- spec: spec-110 D-110-03 (hash chain root-of-object layout)
- spec: spec-122-b D-122-06 (state plane consolidation)

## Open Questions

None. All five interrogation gates resolved (drift-tested duplication,
prevention-only scope, mock + matrix stress, three-writer surface,
bounded-retry fail-open).
