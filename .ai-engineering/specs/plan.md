---
spec: spec-200
slug: local-env-correctness
title: "Execution plan — local-environment correctness: surface-aware stack detection and canonical hook state"
status: approved
pipeline: full
effort: medium
execution_route:
  version: 1
  spec: spec-200
  executor: build
  automation: assisted
  concern_count: 3
  estimated_files: 37
  reason: "Count crosses the autopilot threshold, but the remaining work is one mechanical concern under a hard serialization constraint: every edited hook script must change in byte-lockstep with its template mirror and the hooks manifest re-pinned exactly once afterwards. Wave-parallelizing those pairs is spec Risk 4 (a missed mirror silently disables hooks). Concerns A and B are already implemented in the working tree. Deliberate deviation — override with /ai-autopilot if preferred."
  safe_next_command: "/ai-build"
---

# Execution plan — spec-200

## Design

`--skip-design` applies by nature of the change, logged here with reason: there
is no user-facing surface. Every edit is a path constant, a deleted dead
constant, a test assertion, or a CHANGELOG row. The one operator-visible
behaviour — the stack-drift warning — is held unchanged by Non-Goals: it stops
firing on false evidence and keeps its severity, wording and
`AIENG_STACK_DRIFT_STRICT` contract. No design-intent artifact is written.

## Architecture

Pattern: **ad-hoc**. None of the canonical patterns in
`.ai-engineering/reference/architecture-patterns.md` applies — this is the
retirement of a duplicated path constant, not a structural change.

The structure that matters is already in place and half-adopted.
`_lib/hook_context.py:46` exposes `RUNTIME_DIR(project_root)` as the single
source of truth for the canonical runtime directory, and spec-125 Wave 2b
routed the active helpers in `runtime_state.py` through it. Three kinds of code
never joined:

1. **Standalone stdlib hook modules** — `_lib/trace_context.py`,
   `_lib/audit.py`, `_lib/hook-common.py`, `hooks/runtime-session-start.py`,
   `_lib/observability.py`. These do not import `hook_context` and are
   deliberately import-light for hot-path cost. They keep their own literal
   path constants; the fix corrects the literal and does **not** add a
   `hook_context` import. Routing them through the factory buys nothing — the
   value is a two-segment path — and costs an import on the hot path.
2. **Dead re-exports** — `runtime_state.py` and `risk_accumulator.py` hold nine
   `*_REL` constants that shadow the factory with the old value. Deleted per
   D-200-04.
3. **Package-side installer code** — `cli_commands/core.py`,
   `installer/opa.py`. Never had a hook-side factory to reach for; literal
   paths, corrected in place.

One parity fact drives the whole concern:
`src/ai_engineering/state/trace_context.py:49` already reads
`.ai-engineering/runtime/trace-context.json` while its stdlib hook twin
`_lib/trace_context.py:37` still reads
`.ai-engineering/state/runtime/trace-context.json`. Two writers of one datum
disagree. That is the defect in one line.

### Correction to the spec's failure mechanism

The spec's Summary describes `test_forbidden_dirs_absent` failing because hooks
"recreate it between the test's own cleanup and its assertion" — a race. Reading
the test, it is neither a race nor intermittent.

`tests/unit/specs/test_state_canonical.py:178` gates its own cleanup on an
allowlist of exactly two names:

```python
only_session_artefacts = all(
    entry.name in ("trace-context.json", "event-sidecars")
    for entry in runtime_dir.iterdir()
)
if only_session_artefacts:
    shutil.rmtree(runtime_dir)
```

spec-190 added a third writer to that directory: `session-pointer.json`. Its
presence makes `only_session_artefacts` false, the `rmtree` is skipped, and the
assertion at line 186 fails deterministically. The live directory right now
holds exactly `session-pointer.json` and `trace-context.json`, which is why it
fails every run rather than sometimes.

This changes nothing about the fix — D-200-03 stands, and T-7.1 deletes the
workaround either way — but the failure is hard and reproducible rather than
flaky. Worth knowing before anyone tries to reproduce it by timing.

## Phase 0 — Verify concerns A and B (already in the working tree)

No new implementation. These tasks confirm what is already written so
`/ai-build` does not re-derive settled code.

- [x] T-0.1 — Confirm the `_WALK_EXCLUDE` addition and its regression tests
- Agent: verify
- Files: `src/ai_engineering/installer/autodetect.py:135-146`, `tests/unit/installer/test_autodetect.py`
- Principles applied: §10.5 TDD (the regression tests must fail against the pre-change exclusion set), §10.1 KISS
- Gate: `pytest tests/unit/installer/test_autodetect.py -q` green; the six new cases named in the spec present; `detect_surfaces` assertions unchanged (spec AC 3)

- [x] T-0.2 — Confirm every envelope test reads stdout, not merged output
- Agent: verify
- Files: `tests/integration/test_cli_install_doctor.py`, `tests/integration/test_risk_cli_filters_and_formats.py`, `tests/unit/cli/test_spec_verify.py`, `tests/unit/cli_commands/test_version_upgrade.py`, `tests/unit/test_cli_observability_reset.py`, `tests/unit/test_release_cli.py`, `tests/unit/test_verify_release_cli.py`
- Principles applied: §10.5 TDD, §10.7 Clean Code (one assertion states one contract)
- Gate: `rg 'json\.loads\(result\.output' tests/` returns no hit in the changed files; the induced-drift proof from the spec re-runs green (write a real root `package.json`, run the 107 envelope tests, revert)

## Phase 1 — RED tests for the path retirement

Every test here must fail before Phase 2 lands (§10.5).

- [x] T-1.1 — RED: repo-wide assertion that no live code resolves the forbidden path
- Agent: build
- Files: `tests/unit/specs/test_state_canonical.py` (new test beside the existing guards)
- Principles applied: §10.5 TDD, §10.4 DRY (one canonical location per datum, asserted rather than trusted)
- Patch (deterministic): none — new test, judgment required on scope. Scan `src/` and `.ai-engineering/scripts/` for the two-segment path in every form it appears (`"state" / "runtime"`, `"state", "runtime"`, `state/runtime` inside a string). Exclude `tests/`, `CHANGELOG.md`, and archived specs. This is spec AC 1 as executable code, and it is what stops the path returning after this spec closes.
- Gate: fails now with ten hits; passes after Phase 4

- [x] T-1.2 — RED: the nine dead `*_REL` constants are gone
- Agent: build
- Files: `tests/unit/hooks/test_runtime_state.py`, plus the nearest existing risk-accumulator hook test module
- Principles applied: §10.5 TDD, §13.3 (no compat shims — asserted, not assumed)
- Patch (deterministic): none. Assert each name is absent from the module and from `__all__`: `RUNTIME_DIR_REL`, `TOOL_OUTPUTS_DIR_REL`, `TOOL_HISTORY_REL`, `CHECKPOINT_REL`, `RALPH_RESUME_REL`, `PRECOMPACT_SNAPSHOT_REL`, `EVENT_SIDECARS_DIR_REL` in `runtime_state`; `RUNTIME_DIR_REL`, `RISK_STATE_REL` in `risk_accumulator`.
- Gate: fails now; passes after Phase 3

- [x] T-1.3 — RED: the installer stamps `VERSION` at the canonical path
- Agent: build
- Files: `tests/unit/cli_commands/test_install_cmd_hooks_manifest.py:256`
- Principles applied: §10.5 TDD
- Patch (deterministic):
```diff
-    version_file = tmp_path / ".ai-engineering" / "state" / "runtime" / "VERSION"
+    version_file = tmp_path / ".ai-engineering" / "runtime" / "VERSION"
```
- Gate: fails now; passes after T-4.1. Add an assertion in the same test that `.ai-engineering/state/runtime/` does **not** exist post-install

- [x] T-1.4 — RED: the update path reaches the `VERSION` stamp when an apply mutates files
- Agent: build
- Files: `tests/unit/cli_commands/test_install_cmd_hooks_manifest.py`, or the update-workflow module covering `_finalize_update_hooks_manifest`
- Principles applied: §10.5 TDD, §10.6 SDD (D-200-05's zero-window guarantee is a contract, so it gets a test)
- Patch (deterministic): none. Drive `_finalize_update_hooks_manifest` with a stub result where `status == APPLIED`, `dry_run is False`, `applied_count > 0`, and assert `.ai-engineering/runtime/VERSION` exists afterwards. Also assert the no-op case (`applied_count == 0` and `orphan_count == 0`) writes nothing — that early return is deliberate and must stay.
- Gate: this is the guard that makes a future refactor of `_finalize_hooks_manifest` fail loudly instead of silently reopening the migration window (spec Risk 3)

- [x] T-1.5 — RED: the rotation reaper removes a pre-existing legacy runtime directory
- Agent: build
- Files: `tests/unit/test_runtime_rotate_state_db.py` (extend — same reaper module, same shape as the existing `state.db` cases)
- Principles applied: §10.5 TDD, §10.1 KISS (extend the existing reaper's test module rather than adding one)
- Patch (deterministic): none. Seed `state_dir / "runtime"` with `session-pointer.json` and `trace-context.json`, run the new reaper, assert the directory is gone, assert a second pass is a silent no-op, and assert the live JSON sources of truth at `STATE_DIR` root are untouched — mirror the guarantees `test_removes_stale_state_db_and_siblings` already pins.
- Gate: fails now; passes after T-5.1

## Phase 2 — Move the five live hook-tree resolvers (canonical tree only)

Canonical tree only. The template mirror is Phase 6 in one deliberate sweep, so
no intermediate state leaves a half-mirrored script on disk.

- [x] T-2.1 — `_lib/trace_context.py` writes the canonical trace-context path
- Agent: build
- Files: `.ai-engineering/scripts/hooks/_lib/trace_context.py:37`
- Principles applied: §10.4 DRY (restores parity with the package twin at `src/ai_engineering/state/trace_context.py:49`)
- Patch (deterministic):
```diff
-TRACE_CONTEXT_REL = Path(".ai-engineering") / "state" / "runtime" / "trace-context.json"
+TRACE_CONTEXT_REL = Path(".ai-engineering") / "runtime" / "trace-context.json"
```
- Gate: `pytest tests/unit/hooks/test_lib_trace_context.py -q`

- [x] T-2.2 — `_lib/audit.py` writes event sidecars under the canonical runtime dir
- Agent: build
- Files: `.ai-engineering/scripts/hooks/_lib/audit.py:16`
- Principles applied: §10.4 DRY
- Patch (deterministic):
```diff
-_SIDECAR_DIR_REL = (".ai-engineering", "state", "runtime", "event-sidecars")
+_SIDECAR_DIR_REL = (".ai-engineering", "runtime", "event-sidecars")
```
- Gate: `pytest tests/unit/hooks -k sidecar -q`

- [x] T-2.3 — `_lib/hook-common.py` reads the session pointer from the canonical path
- Agent: build
- Files: `.ai-engineering/scripts/hooks/_lib/hook-common.py:169`
- Principles applied: §10.4 DRY
- Patch (deterministic):
```diff
-_SESSION_POINTER_REL = Path(".ai-engineering") / "state" / "runtime" / "session-pointer.json"
+_SESSION_POINTER_REL = Path(".ai-engineering") / "runtime" / "session-pointer.json"
```
- Gate: `pytest tests/unit/hooks -k session_id -q`

- [x] T-2.4 — `runtime-session-start.py` writes the session pointer to the canonical path
- Agent: build
- Files: `.ai-engineering/scripts/hooks/runtime-session-start.py:92` (docstring), `:108` (write)
- Principles applied: §10.4 DRY, §10.7 Clean Code (the docstring names the path it writes; both change together)
- Patch (deterministic):
```diff
-    env. Stamping ``.ai-engineering/state/runtime/session-pointer.json`` at
+    env. Stamping ``.ai-engineering/runtime/session-pointer.json`` at
```
```diff
-        path = project_root / ".ai-engineering" / "state" / "runtime" / "session-pointer.json"
+        path = project_root / ".ai-engineering" / "runtime" / "session-pointer.json"
```
- Gate: lands together with T-2.3 — writer and reader are one datum, and a split leaves `get_session_id` blind

- [x] T-2.5 — `_lib/observability.py` reads `VERSION` from the canonical path
- Agent: build
- Files: `.ai-engineering/scripts/hooks/_lib/observability.py:311` (docstring), `:326` (read)
- Principles applied: §10.4 DRY, §10.6 SDD (spec-190 D-190-01's resolution order is preserved verbatim; only the address moves)
- Patch (deterministic):
```diff
-    1. the text of ``<root>/.ai-engineering/state/runtime/VERSION`` written
+    1. the text of ``<root>/.ai-engineering/runtime/VERSION`` written
```
```diff
-    version_file = project_root / ".ai-engineering" / "state" / "runtime" / "VERSION"
+    version_file = project_root / ".ai-engineering" / "runtime" / "VERSION"
```
- Gate: `pytest tests/unit/hooks/test_lib_observability_genai.py -q` — the importlib-metadata fallback and the `"0.0.0"` sentinel must still be exercised (spec AC 5). `_read_framework_version` is `functools.cache`d on `project_root`, so no new test may rely on a second call re-reading the file.

## Phase 3 — Delete the nine dead re-exports

- [x] T-3.1 — Delete the seven `*_REL` constants from `_lib/runtime_state.py`
- Agent: build
- Files: `.ai-engineering/scripts/hooks/_lib/runtime_state.py:61-75`, `__all__` at `:880-900`
- Principles applied: §13.3 (hard delete, no deprecation window), §10.2 YAGNI, §10.4 DRY
- Patch (deterministic):
```diff
-# Legacy ``*_REL`` constants retained for backwards-compatible re-export
-# only -- do NOT use these for new code. They reference the pre-Wave-2b
-# ``state/runtime`` location and are kept solely so any external import
-# path keeps resolving. Active path resolution flows through the
-# helper functions below (which use ``RUNTIME_DIR``).
-RUNTIME_DIR_REL = Path(".ai-engineering") / "state" / "runtime"
-TOOL_OUTPUTS_DIR_REL = RUNTIME_DIR_REL / _TOOL_OUTPUTS_NAME
-TOOL_HISTORY_REL = RUNTIME_DIR_REL / _TOOL_HISTORY_NAME
-CHECKPOINT_REL = RUNTIME_DIR_REL / _CHECKPOINT_NAME
-RALPH_RESUME_REL = RUNTIME_DIR_REL / _RALPH_RESUME_NAME
-PRECOMPACT_SNAPSHOT_REL = RUNTIME_DIR_REL / _PRECOMPACT_SNAPSHOT_NAME
-# spec-123 D-123-23: oversized framework events offload to a content-addressed
-# sidecar dir under runtime/ so the inline NDJSON line stays under the
-# POSIX_BUF (4 KB) atomic-append guarantee.
-EVENT_SIDECARS_DIR_REL = RUNTIME_DIR_REL / _EVENT_SIDECARS_NAME
```
  Then drop `CHECKPOINT_REL`, `EVENT_SIDECARS_DIR_REL`, `PRECOMPACT_SNAPSHOT_REL`, `RALPH_RESUME_REL`, `RUNTIME_DIR_REL`, `TOOL_HISTORY_REL`, `TOOL_OUTPUTS_DIR_REL` from `__all__`.
  **Preserve the spec-123 D-123-23 rationale** — move that three-line comment up to `_EVENT_SIDECARS_NAME` at `:55`, which survives. Deleting the constant must not delete why sidecars exist.
  Also refresh the block comment at `:35-47`, which tells the reader the `*_REL` constants exist below.
- Gate: `pytest tests/unit/hooks/test_runtime_state.py -q`; `ruff check` clean — confirm `Path` still has a live use, and drop the import only if this task orphaned it

- [x] T-3.2 — Delete the two `*_REL` constants from `_lib/risk_accumulator.py`
- Agent: build
- Files: `.ai-engineering/scripts/hooks/_lib/risk_accumulator.py:74-79`, `__all__` at `:484-495`
- Principles applied: §13.3, §10.2 YAGNI
- Patch (deterministic):
```diff
-# Spec-125 Wave 2: legacy ``state/runtime`` constants retained for
-# backwards-compatible re-export only. Active path resolution flows through
-# the ``RUNTIME_DIR(project_root)`` factory in ``_lib/hook_context.py``
-# (canonical ``.ai-engineering/runtime/``); see ``_state_path`` below.
-RUNTIME_DIR_REL = Path(".ai-engineering") / "state" / "runtime"
-RISK_STATE_REL = RUNTIME_DIR_REL / "risk-score.json"
 _RISK_STATE_FILENAME = "risk-score.json"
```
  Then drop `RISK_STATE_REL` and `RUNTIME_DIR_REL` from `__all__`.
- Gate: `ruff check` clean (`Path` may be orphaned here too); risk-accumulator tests green; `_state_path` still resolves through `RUNTIME_DIR`

## Phase 4 — Move the three package-side sites

- [x] T-4.1 — The installer stamps `VERSION` at the canonical runtime path
- Agent: build
- Files: `src/ai_engineering/cli_commands/core.py:739`
- Principles applied: §10.4 DRY, §10.6 SDD (this is the write half of the reader moved in T-2.5; splitting them is the silent degradation in spec Risk 2)
- Patch (deterministic):
```diff
-    version_file = root / ".ai-engineering" / "state" / "runtime" / "VERSION"
+    version_file = root / ".ai-engineering" / "runtime" / "VERSION"
```
- Gate: T-1.3 and T-1.4 green. This edit sits inside `_finalize_hooks_manifest`, which D-200-05's zero-window argument depends on — do not relocate the stamp out of that function.

- [x] T-4.2 — The OPA bundle builds into the canonical runtime path
- Agent: build
- Files: `src/ai_engineering/installer/opa.py:164`
- Principles applied: §10.4 DRY
- Patch (deterministic):
```diff
-    bundle_out = project_root / ".ai-engineering" / "state" / "runtime" / "bundle.tar.gz"
+    bundle_out = project_root / ".ai-engineering" / "runtime" / "bundle.tar.gz"
```
- Gate: `pytest -k opa -q`; `ai-eng doctor` reports `opa-bundle-signature` passing (spec AC). The tarball has no reader — `opa_runner.DEFAULT_BUNDLE_PATH` is `.ai-engineering/policies` and `sign_bundle` writes `.signatures.json` into that directory — so only the output address moves. Do not add a reader.

- [x] T-4.3 — Correct the stale bundle path in the gitignore module
- Agent: build
- Files: `src/ai_engineering/installer/gitignore.py:5` (docstring), `:68` (inline comment)
- Principles applied: §10.7 Clean Code (a docstring naming the wrong path is a defect with a long half-life)
- Patch (deterministic):
```diff
-SoTs, the compiled & signed OPA bundle (``state/runtime/bundle.tar.gz``),
+SoTs, the compiled & signed OPA bundle (``runtime/bundle.tar.gz``),
```
- Gate: docs tests green. The ignore rules themselves need no change — the template already carries both `state/runtime/` (line 69) and `runtime/` (line 70), and keeping the former covers consumers whose orphan directory has not been reaped yet. Update the line-68 comment so it points at `runtime/` as the bundle's home.

## Phase 5 — Reap the orphaned directory

- [x] T-5.1 — Extend the rotation reaper to remove a legacy `state/runtime/` directory
- Agent: build
- Files: `.ai-engineering/scripts/runtime_rotate.py` (new `_remove_legacy_runtime_dir` beside `_remove_stale_state_db` at `:147`; wire into the `main()` payload at `:196`)
- Principles applied: §10.1 KISS (the reaper for stale runtime leftovers already exists; this is one more leftover, not a new command), §10.3 SOLID (one function, one artifact class)
- Patch (deterministic): none — new function, judgment required. Mirror `_remove_stale_state_db`: fail-open on `OSError`, idempotent on a clean tree, return `{"deleted": …, "bytes_freed": …}`, and add a `"legacy_runtime_dir"` key to the `main()` payload so the rotation summary reports it. Two constraints the existing reaper does not face:
  - it removes a **directory tree**, so scope must be confirmed before `rmtree` — remove only when every entry is a known transient (`session-pointer.json`, `trace-context.json`, `event-sidecars/`, `VERSION`, `bundle.tar.gz`, `risk-score.json`, `tool-outputs/`, `tool-history.ndjson`, `checkpoint.json`, `ralph-resume.json`, `precompact-snapshot.json`, `error-coalesce.json`) and leave the tree alone otherwise, so an operator's unexpected file is never destroyed;
  - it must never touch `STATE_DIR` root, where the audit ledgers and JSON sources of truth live.
- Gate: T-1.5 green, including the idempotent second pass and the untouched-SoT assertions

## Phase 6 — Mirror lockstep and manifest re-pin (single sweep)

Runs **once**, after Phases 2, 3 and 5 are complete. Running it early or
per-task is the documented way to ship a half-mirrored tree.

- [x] T-6.1 — Mirror all eight edited scripts byte-identically into the installer template
- Agent: build
- Files: `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/{trace_context,audit,hook-common,observability,runtime_state,risk_accumulator}.py`, `.../hooks/runtime-session-start.py`, `.../scripts/runtime_rotate.py`
- Principles applied: §10.4 DRY (the template tree is the install payload; drift ships a fix that never reaches consumers), §13.3
- Patch (deterministic): copy each canonical file over its template counterpart, then prove byte-parity:
```
for f in _lib/trace_context.py _lib/audit.py _lib/hook-common.py \
         _lib/observability.py _lib/runtime_state.py _lib/risk_accumulator.py \
         runtime-session-start.py; do
  diff -q ".ai-engineering/scripts/hooks/$f" \
          "src/ai_engineering/templates/.ai-engineering/scripts/hooks/$f" || echo "DRIFT: $f"
done
diff -q .ai-engineering/scripts/runtime_rotate.py \
        src/ai_engineering/templates/.ai-engineering/scripts/runtime_rotate.py || echo "DRIFT: runtime_rotate.py"
```
- Gate: every `diff -q` silent (spec AC 7). `runtime_rotate.py` is byte-identical across the pair today and must stay so — no CI check guards that file, which makes this diff loop the only gate.

- [x] T-6.2 — Re-pin the hooks manifest
- Agent: build
- Files: `.ai-engineering/state/hooks-manifest.json`
- Principles applied: §10.6 SDD (D-200-07), §13 hard rules
- Patch (deterministic):
```
.venv/bin/python .ai-engineering/scripts/regenerate-hooks-manifest.py
```
- Gate: `ai-eng doctor` reports hook integrity passing (spec AC 8); the regenerator's `--check` reports no drift. Use the project venv interpreter — bare `python3` resolves to 3.9 on this machine and the script uses 3.11+ idioms.

## Phase 7 — Update the tests that encode the old path

- [x] T-7.1 — Delete the `test_forbidden_dirs_absent` tolerance workaround
- Agent: build
- Files: `tests/unit/specs/test_state_canonical.py:154-186`
- Principles applied: §10.7 Clean Code, §13.3 (the workaround is a compat shim living in a test)
- Patch (deterministic): none — remove the `import shutil`, the `only_session_artefacts` allowlist and the conditional `rmtree`, then rewrite the docstring, dropping the paragraph that calls the leftover "tracked separately and out of scope". The assertion at `:186` stands alone once no writer targets the path. **This is the task that makes the guard mean something again**: with the workaround in place, a future writer of an already-allowlisted name would be swept under the rug silently.
- Gate: `pytest tests/unit/specs/test_state_canonical.py -q` green in an interactive session with hooks active, not only in CI (spec AC 6). Reproduce first — the directory currently holds `session-pointer.json` + `trace-context.json`, which fails the allowlist deterministically.

- [x] T-7.2 — Point the remaining path-bearing tests at the canonical location
- Agent: build
- Files: `tests/unit/hooks/test_runtime_state.py:55`, `tests/unit/hooks/test_lib_observability_genai.py:99-100`, `tests/unit/hooks/test_lib_trace_context.py:234`, `tests/unit/state/test_trace_context.py:476`
- Principles applied: §10.5 TDD, §10.7 Clean Code
- Patch (deterministic): none — each needs reading in context. Two risk becoming vacuous rather than failing:
  - `tests/unit/state/test_trace_context.py:476` builds the old path then scans it for `.tmp` leftovers under `if runtime_dir.exists()`. Against the package twin — on the new path since spec-125 — that directory never exists, so the assertion has been silently skipped all along. Repointing it at `.ai-engineering/runtime` makes it assert for the first time; expect it to need a real fix, not just a rename.
  - `tests/unit/hooks/test_runtime_state.py:55` `mkdir`s the old path as setup. Repoint it, and check whether it also imports any constant deleted in T-3.1.
- Gate: `pytest tests/unit/hooks tests/unit/state tests/unit/specs -q` green; no test asserts on a directory that cannot exist

## Phase 8 — Documentation

- [x] T-8.1 — CHANGELOG: the breaking change plus the two fixes
- Agent: build
- Files: `CHANGELOG.md` under `## [Unreleased]` (line 8, currently empty)
- Principles applied: §13.3 (CHANGELOG documents the breakage), §10.6 SDD
- Patch (deterministic): none — prose. Three entries:
  1. **Breaking changes** — spec-200 removes nine `*_REL` constants from the hook library (`runtime_state.RUNTIME_DIR_REL`, `TOOL_OUTPUTS_DIR_REL`, `TOOL_HISTORY_REL`, `CHECKPOINT_REL`, `RALPH_RESUME_REL`, `PRECOMPACT_SNAPSHOT_REL`, `EVENT_SIDECARS_DIR_REL`; `risk_accumulator.RUNTIME_DIR_REL`, `RISK_STATE_REL`). They were backwards-compatible re-exports of the pre-spec-125 path, unused by every helper around them. Out-of-tree code importing them must call `hook_context.RUNTIME_DIR(project_root)` instead. Hard delete per Hard Rule 3.
  2. **Fixed** — the stack detector no longer reads an AI surface directory's own package manifest as a project stack, so a python-configured repo with OpenCode installed stops reporting permanent stack drift (blocking under `AIENG_STACK_DRIFT_STRICT=1`).
  3. **Fixed** — hook state, the installer's pinned `VERSION` and the compiled OPA bundle all move to `.ai-engineering/runtime/`, completing the spec-125 relocation. No migration is needed: hook scripts deploy via `ai-eng install`/`update`, which re-stamps `VERSION` in the same run.
- Gate: `pytest tests/docs -q`; doc gate green

- [x] T-8.2 — Refresh the `state/runtime` references in the guard-test docstrings
- Agent: build
- Files: `tests/unit/specs/test_canonical_structure.py:29`, `tests/unit/specs/test_state_canonical.py` (docstring, alongside T-7.1)
- Principles applied: §10.7 Clean Code
- Patch (deterministic): none. Both describe the old layout as current. Correct them to name `.ai-engineering/runtime/` and drop the "awaiting a proper fix" framing, which stops being true with this spec. `test_canonical_structure.py:29` also claims decisions live in `state.db.decisions`, which spec-148 retired when it went files-only — out of scope here, and worth its own one-line fix rather than a drive-by inside a spec-200 commit. Note it, leave it.
- Gate: docs tests green

## Phase 9 — Full gate

- [x] T-9.1 — Full suite with hooks active and OpenCode installed
- Agent: verify
- Files: —
- Principles applied: §10.5 TDD, Operating Mindset §4 Verification Before Done
- Gate: the whole unit + integration suite green in this session's exact configuration — hooks firing, `.opencode/package.json` present. That configuration produced nineteen failures and is the only environment that proves both concerns closed (spec AC 9). CI cannot substitute: it has neither the hook layer nor `.opencode`.

- [x] T-9.2 — Repo-wide forbidden-path sweep
- Agent: verify
- Files: —
- Principles applied: §10.4 DRY
- Gate: T-1.1 green, plus a manual `rg 'state/runtime|"state", "runtime"|"state" / "runtime"' src/ .ai-engineering/scripts/` returning nothing. Deliberately surviving hits elsewhere: `CHANGELOG.md` history, archived specs, and the `state/runtime/` ignore line in the gitignore template (T-4.3).

- [x] T-9.3 — Pre-push gate
- Agent: verify
- Files: —
- Principles applied: §13 hard rules
- Gate: `ai-eng gate pre-push` green — `semgrep`, `pip-audit`, `gitleaks`, spec lint, mirror parity. Check `git status` before committing: the pre-commit gate reformats source files in this repo, and that reformat must not ride along unnoticed inside a spec-200 commit.

## Open items for the executor

1. **T-1.2's second test module.** A dedicated risk-accumulator hook test module
   may not exist under `tests/unit/hooks/`. Find the nearest existing home
   before creating one.
2. **`Path` imports after Phase 3.** Both files may lose their last `Path` use.
   `ruff check` decides; do not pre-emptively delete the import.
3. **The reaper's transient allowlist (T-5.1)** is enumerated from what the nine
   deleted constants and five moved writers name. If `runtime_rotate.py` already
   holds a canonical list of runtime filenames, reuse it instead of retyping one.

## Quality Outcome

Verdict: **PASS**. Single round, no remediation pass consumed
(`quality_remediation.used: false`). All 27 tasks `[x]`, zero BLOCKED.

Deterministic evidence, full changeset evaluated as one unit:

| Check | Result |
|-------|--------|
| Full suite (hooks active, `.opencode/package.json` present) | 8948 passed, 0 failed, 25 skipped, 1 xfailed (13m46s) |
| `ai-eng gate pre-push` | PASS — 0 findings, 0 blocking; risk acceptances current |
| `ruff check` / `ruff format --check` (41 changed .py) | clean / already formatted |
| Hook mirror byte-parity (8 pairs) | identical |
| `regenerate-hooks-manifest.py --check` | OK, 79 hooks |
| `ai-eng doctor` hook integrity | `hooks-integrity` PASS, `hooks-manifest-sha-drift` PASS |
| `spec_lint --check` | 6/6, 0 blockers, 0 advisories |

Spec acceptance criteria: 15/15 met. Notable proofs rather than assertions:

- The six surface-exclusion cases fail against the pre-change `_WALK_EXCLUDE`
  and pass after it (RED proven by reverting `autodetect.py`, not assumed).
- The 131 envelope tests pass with a real drift warning on stderr, induced by
  writing a genuine root `package.json` — the assertion that matters for
  D-200-02.
- `test_forbidden_dirs_absent` passes in this interactive session with hooks
  firing, and the reaped directory does not return.
- The D-200-03 guard is proven non-vacuous: it fails when either path spelling
  is reintroduced (`Path / "state" / "runtime"` and the tuple form) and passes
  clean.

### First-run failures, all resolved

The first full-suite run reported 6 failures. None was a defect in the
spec-200 change:

1. `test_hook_common_lib` (1) — four hardcoded old paths T-7.2 missed. Repointed.
2. `test_changelog_breaking_keywords` (4) — the topmost `### Breaking changes`
   block must carry a spec-101 keyword-continuity line; 0.13.0 does this
   explicitly and the new Unreleased block did not. Convention followed rather
   than the gate rewritten.
3. `test_tunables_docs_match_code` (1) — **pre-existing, red at clean HEAD.**
   spec-190 documented `AIENG_ERROR_STORM_THRESHOLD` in CLAUDE.md without
   classifying it. Fixed here because it blocks every PR's gate.

### Drive-by fixes carried in this changeset

- `tests/architecture/test_tunables_docs_match_code.py` — classify the spec-190
  tunable (pre-existing main breakage, verified by stashing all local work).
- `tests/unit/hooks/test_runtime_state.py` and `test_lib_trace_context.py` —
  each fixture now prepends the hooks dir to `sys.path`. Both files previously
  passed only because a sibling test left `_lib` in `sys.modules`; run alone,
  `test_runtime_state.py` errored on all 11 tests.

### Deliberately not fixed

- `ai-eng doctor` reports `hooks-executable` FAIL for `governed-git-advisor.py`,
  `injection-read-guard.py`, `runtime-observation-nudge.py`. Pre-existing, none
  of them touched here, and `git diff --summary` shows no mode changes.
- `tests/unit/specs/test_canonical_structure.py` still claims decisions live in
  `state.db.decisions`, retired by spec-148. Noted in T-8.2, left for its own fix.

