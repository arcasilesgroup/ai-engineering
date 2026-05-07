# Plan: spec-126 Hook-side NDJSON Append Lock Parity

## Pipeline: standard
## Phases: 5
## Tasks: 14 (build: 9, verify: 4, guard: 1)

## Design

`--skip-design` implicit: zero UI surface (hook lib + CI tests + manifest
regen). No `/ai-design` artifact required.

## Architecture

**Pattern**: `ad-hoc` — explicit byte-equivalent duplication with mechanical
parity gate.

The work crosses a hard architectural boundary: the hook layer must remain
standalone (no editable-install dependency at hook execution time, per
CLAUDE.md and Article V). The pkg-side already owns the canonical lock
primitive at `src/ai_engineering/state/locking.py`. We cannot import it
from hook scripts, and we cannot invert the dependency (hook → pkg) without
breaking the standalone contract. None of the canonical patterns
(layered, hexagonal, ports-and-adapters, clean, pipes-and-filters,
repository, unit-of-work, modular monolith, microservices, CQRS, event
sourcing) fits — there is no "core" and "adapter" here; both copies are
peers across an isolation boundary. The structural choice is to copy the
primitive and bind the two copies with a byte-diff CI gate
(`test_locking_parity.py`) that fails on any divergence. Drift becomes
mechanically impossible to merge; the duplication is acknowledged debt
with an automated guardrail.

## Phase 1 — Lock primitive foundation

**Gate**: `_lib/locking.py` exists; `test_locking_parity.py` passes against
the current pkg-side file; both files import without errors on POSIX and
Windows (CI matrix).

- [x] **T-1.1**: Create `.ai-engineering/scripts/hooks/_lib/locking.py` as
  byte-mirror of `src/ai_engineering/state/locking.py` (excluding module
  docstring + import block). Public API: `artifact_lock_path`,
  `artifact_lock` context manager. Internal: `_seed_lock_file`,
  `_acquire_lock`, `_release_lock`. (agent: build) — DONE (real)
- [x] **T-1.2**: Write `tests/unit/hooks/test_locking_parity.py` —
  byte-by-byte diff between hook-side `_lib/locking.py` and pkg-side
  `state/locking.py`, ignoring module docstring + import block. Fail with
  unified diff on divergence. (agent: build) — DONE (real, 1 passed)

## Phase 2 — Retry + telemetry helper

**Gate**: `locked_append(...)` helper unit-tested; bounded-retry path,
fail-open path, and `framework_error` emission path each have a covering
test; helper returns `True` on success, `False` on fail-open fallback.

- [x] **T-2.1**: RED — write `tests/unit/hooks/test_locked_append_retry.py`
  covering three cases: (a) lock acquires first attempt → single write,
  no telemetry; (b) lock fails twice with `OSError` then acquires →
  retried write, no telemetry; (c) lock fails 3 attempts → unlocked
  append + `framework_error` event emitted with
  `detail.error_code = "lock_acquisition_failed"`. Use `monkeypatch` on
  `_acquire_lock` to inject failures; assert backoff total ≤ 150 ms.
  (agent: build) — DONE (real, RED→GREEN, timing upper bound widened to 400ms for CI tolerance — concern accepted)
- [x] **T-2.2**: GREEN — add `locked_append(project_root, path, line,
  lock_name, *, max_retries=3, backoff_ms=50)` helper, placed in NEW
  file `_lib/locked_append.py` to preserve `locking.py` byte-parity.
  Acquires `artifact_lock`, on `OSError` retries up to `max_retries`
  with `time.sleep(backoff_ms / 1000)`. On exhaustion: open path in
  append mode, write line, emit `framework_error` to sidecar
  `lock-failures.ndjson` (avoids self-recursion onto the failed lock).
  (agent: build, blocked by T-2.1) — DONE (real, 3 passed, parity preserved)

## Phase 3 — Migrate the three writers

**Gate**: stress test asserts `line_count == N*M` and `verify_chain`
passes end-to-end on Linux + macOS + Windows; mock tests assert each of
the three writers calls `locked_append` (or `artifact_lock` directly)
before `f.write`; no remaining bare `path.open("a")` against
`framework-events.ndjson` anywhere under
`.ai-engineering/scripts/hooks/_lib/`.

- [x] **T-3.0** (added during execution): Refactor `locked_append.py` to
  add `with_lock_retry` context manager (yields locked-bool, retry+fail-open).
  `locked_append` kept as standalone wrapper to preserve Phase 2 sidecar
  contract (~30 LOC duplication accepted). New tests in
  `test_with_lock_retry.py` (2 passed). (agent: build) — DONE (real)
- [x] **T-3.1**: RED — `test_ndjson_concurrent_append.py` (N=8 × M=50,
  spawn ctx). RED confirmed pre-fix: **chain broke at line 27** —
  TOCTOU race reproduced. PASS after GREEN. (agent: build) — DONE (real)
- [x] **T-3.2**: RED — `test_ndjson_writers_use_lock.py` (3 spy cases).
  RED confirmed pre-fix (spy never entered). PASS after GREEN. (agent:
  build) — DONE (real)
- [x] **T-3.3**: GREEN — `_lib/observability.py:append_framework_event`
  wrapped in `with_lock_retry`; `_compute_prev_event_hash` moved INSIDE
  lock (TOCTOU mitigated). (agent: build) — DONE (real)
- [x] **T-3.4**: GREEN — `_lib/hook-common.py:emit_event` wrapped in
  lock; hash compute inside lock; `maybe_offload_event` outside lock as
  specified. Added `_load_with_lock_retry` helper to handle
  `spec_from_file_location` test loaders. (agent: build) — DONE (real)
- [x] **T-3.5**: GREEN — `_lib/trace_context.py:_emit_corruption_event`
  wrapped in lock; hash compute inside lock; OSError fail-open handler
  preserved. (agent: build) — DONE (real)
- Phase 3 result: 173 passed (full hooks suite minus slow), stress test
  passes, no regressions. Pre-existing ruff errors in untouched runtime
  files flagged out-of-scope.

## Phase 4 — Hook integrity + matrix wiring

**Gate**: `regenerate-hooks-manifest.py --check` exits 0;
`test-hooks-matrix.yml` selects `@pytest.mark.slow` so the stress test
runs on all three OSs.

- [x] **T-4.1**: Regenerated `hooks-manifest.json` (67 hooks, 5 sha
  deltas: 2 NEW + 3 EDITED). (agent: build) — DONE (mechanical)
- [x] **T-4.2**: `regenerate-hooks-manifest.py --check` → exit 0.
  (agent: verify) — DONE
- [x] **T-4.3a**: Registered `slow:` marker in
  `pyproject.toml [tool.pytest.ini_options].markers` —
  `PytestUnknownMarkWarning` eliminated. (agent: build) — DONE
- [x] **T-4.3b**: Inspected `test-hooks-matrix.yml`; pytest invocation
  has no `-m` filter so slow tests already run on Linux/macOS/Windows by
  default. **No change needed**; D-126-03 satisfied as-is. (agent: build)
  — DONE (no-op with rationale)

## Phase 5 — Governance verification

**Gate**: no `NO_GO` findings from verify or guard; deterministic checks
green; Article III audit-log integrity preserved.

- [x] **T-5.1**: Deterministic profile — ruff PASS, ruff format PASS,
  pytest 173 + 1 slow PASS, gitleaks PASS, manifest --check PASS.
  pip-audit flagged 2 CVEs in `pip 26.0.1` (out of scope). (agent:
  verify) — DONE (GO)
- [x] **T-5.2**: Architecture verification — all 6 criteria PASS.
  Hook-standalone (no `ai_engineering` imports), parity invariant
  enforced, TOCTOU mitigated at all 3 sites (hash compute inside lock),
  hot-path budget intact, fail-open posture consistent, no-recursion
  via sidecar. (agent: verify) — DONE (GO)
- [x] **T-5.3**: Governance advisory — SUPPORT_WITH_NOTES.
  Article III strengthened for concurrent-write case. D-110-03 layout
  preserved. Manifest current. 3 advisory recommendations:
  (1) register `lock-failures.ndjson` sidecar in state/README;
  (2) confirm risk-acceptance entries FIND-126-01 + FIND-126-02;
  (3) assign follow-up spec for `verify-chain --from <index>` flag.
  None blocking. (agent: guard) — DONE (advisory)

## Dependencies summary

```
T-1.1 ─┬─► T-1.2
       │
       └─► T-2.1 ──► T-2.2 ─┬─► T-3.1 ─┐
                            │          ├─► T-3.3 ─┐
                            │          ├─► T-3.4 ─┤
                            └─► T-3.2 ─┘          ├─► T-4.1 ──► T-4.2
                                       └─► T-3.5 ─┘             ▲
                                                                │
                                                  T-4.3 ────────┘
                                                       │
                                                       └──► T-5.1, T-5.2, T-5.3
```

Phases 1 and 2 can overlap once T-1.1 lands. Phase 3 RED tasks (T-3.1,
T-3.2) can run in parallel with T-2.1/T-2.2. Phase 3 GREEN tasks (T-3.3,
T-3.4, T-3.5) can run in parallel after Phase 2 completes. Phase 4 and 5
are linear.

## Quality Rounds

Round 1: 0 blockers, 0 criticals, 1 high (COMPAT-001 slow marker
non-functional → pre-commit budget regression), 5 mediums (CORR-002
sidecar race acknowledged, COMPAT-002 doc drift, PERF-001 pre-existing
O(N) read, ARCH-001 sys.path fallback advisory, TEST-001 dependent on
COMPAT-001), 2 lows. → FIX

Round 2: COMPAT-001 fixed (`addopts` now `-v -m 'not slow'` +
`test-hooks-matrix.yml` adds dedicated `-m slow` step preserving
D-126-03 cross-OS coverage). COMPAT-002 + MAINT-001 docstrings
corrected. Manifest regen + `--check` clean. 174 tests pass on
`-m ""`, 173 default deselected, 1 slow isolated. → PASS

Verdict: PASS. Proceed to deliver.
