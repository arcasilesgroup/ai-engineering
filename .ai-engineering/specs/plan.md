---
status: approved
spec: spec-162
title: "Eliminate instinct-store timestamp churn"
execution_route:
  version: 1
  spec: spec-162
  executor: build
  automation: supervised
  concern_count: 1
  estimated_files: 4
  reason: >
    Single concern — kill the per-session timestamp churn on the instinct
    store. One behavioural code change (content-idempotent corpus write) in
    the hook lib plus its byte-identical installer-template mirror, one
    .gitignore line + git rm --cached to untrack the runtime watermark file,
    one unit test, and a working-tree reset. Single-concern, <5 files →
    executor build.
  safe_next_command: "/ai-build"
pipeline: hotfix
architecture_pattern: ad-hoc (guard-clause idempotency)
design_routed: skipped (no UI surface; hook-lib + gitignore + test work)
---

# Plan — spec-162 Eliminate instinct-store timestamp churn

Contract for execution. `/ai-plan` is planning-only — no code written here.
Pipeline `hotfix`. Executor route `build`. Architecture: a guard-clause
idempotency check inside the existing `_save_instincts_document` writer; no new
modules, no schema change. The hook lib edit lands on the canonical
`.ai-engineering/scripts/hooks/_lib/instincts.py` and is mirrored byte-identical
into the installer template (no CI guard enforces this parity — D-162-05).

## Decision → Phase map

| Decision | Phase | Independent? |
|---|---|---|
| D-162-01 idempotent corpus write | P1 | yes (TDD) |
| D-162-05 mirror parity | P1 (T-3) | depends T-2 |
| D-162-02 / D-162-03 / D-162-04 untrack meta.json | P2 | yes |
| D-162-06 reset dirty tree | P3 | depends P1, P2 |

## Phase 1 — Content-idempotent corpus write (D-162-01, TDD)

- [x] T-1 — RED: no-op session must not rewrite observations.yml
- Agent: build
- Files: `tests/unit/test_lib_instincts.py`
- Principles applied: §10.5 TDD
- Patch (deterministic): none — judgment required. Add a test using the
  existing `project` fixture + `instincts` module import. Build a document via
  `instincts._default_instincts_document()` with one correction entry, call
  `instincts._save_instincts_document(project, doc)`, read back the file and
  capture `updatedAt`. Call `_save_instincts_document` again with a freshly
  built document carrying the *same* corpus, re-read, and assert `updatedAt` is
  unchanged (no rewrite). Add a sibling positive test: mutate the corpus
  (append a correction) → assert `updatedAt` advances and the new entry is
  persisted. Use `monkeypatch` on `instincts._iso_now` to return distinct
  stamps per call so an unchanged `updatedAt` proves the write was skipped.
- Gate: `pytest tests/unit/test_lib_instincts.py -k idempotent` fails RED
  (current writer always bumps `updatedAt`).

- [x] T-2 — GREEN: make `_save_instincts_document` content-idempotent
- Agent: build
- Files: `.ai-engineering/scripts/hooks/_lib/instincts.py:381`
- Principles applied: §10.7 Clean Code, §10.1 KISS
- Patch (deterministic):
  ```diff
  --- a/.ai-engineering/scripts/hooks/_lib/instincts.py
  +++ b/.ai-engineering/scripts/hooks/_lib/instincts.py
  @@ def _save_instincts_document(project_root: Path, document: dict[str, Any]) -> None:
   def _save_instincts_document(project_root: Path, document: dict[str, Any]) -> None:
       ensure_instinct_artifacts(project_root)
       document["schemaVersion"] = INSTINCTS_SCHEMA_VERSION
  -    document["updatedAt"] = _iso_now()
  -    _dump_yaml_or_json(_instincts_path(project_root), document)
  +    # spec-162 D-162-01: content-idempotent write. Compare the candidate to
  +    # the on-disk corpus with the volatile ``updatedAt`` excluded; skip the
  +    # write entirely when the corpus is unchanged so no-op sessions do not
  +    # churn the tracked file. Only a genuine corpus change advances updatedAt.
  +    existing = _load_instincts_document(project_root)
  +    candidate = {k: v for k, v in document.items() if k != "updatedAt"}
  +    baseline = {k: v for k, v in existing.items() if k != "updatedAt"}
  +    if candidate == baseline:
  +        return
  +    document["updatedAt"] = _iso_now()
  +    _dump_yaml_or_json(_instincts_path(project_root), document)
  ```
- Gate: T-1 idempotent + positive tests pass GREEN; full
  `pytest tests/unit/test_lib_instincts.py` green (no regression).

- [x] T-3 — Mirror the edit byte-identical into the installer template
- Agent: build
- Files: `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/instincts.py`
- Principles applied: §10.4 DRY
- Patch (deterministic): apply the identical T-2 hunk, then prove parity:
  `cp .ai-engineering/scripts/hooks/_lib/instincts.py src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/instincts.py`
- Gate: `diff -q .ai-engineering/scripts/hooks/_lib/instincts.py src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/instincts.py` reports identical.

## Phase 2 — Untrack the runtime watermark (D-162-02/03/04)

- [x] T-4 — gitignore `observations/meta.json`
- Agent: build
- Files: `.gitignore:166`
- Principles applied: §10.1 KISS
- Patch (deterministic):
  ```diff
  --- a/.gitignore
  +++ b/.gitignore
  @@
   .ai-engineering/state/observation-events.ndjson
  +# spec-162 D-162-02: instinct extraction watermark is per-session runtime
  +# state, not a tracked datum — regenerated by ensure_instinct_artifacts.
  +.ai-engineering/observations/meta.json
  ```
- Gate: `git check-ignore .ai-engineering/observations/meta.json` exits 0.

- [x] T-5 — Untrack the file from the index (retain on disk)
- Agent: build
- Files: `.ai-engineering/observations/meta.json` (index only)
- Principles applied: §10.1 KISS
- Patch (deterministic): `git rm --cached .ai-engineering/observations/meta.json`
- Gate: `git ls-files .ai-engineering/observations/meta.json` is empty AND the
  file still exists on disk (`test -f`).

## Phase 3 — Reset the dirty tree + verify convergence (D-162-06)

- [x] T-6 — Discard the in-flight timestamp diff on observations.yml
- Agent: build
- Files: `.ai-engineering/observations/observations.yml` (working tree)
- Principles applied: §10.1 KISS
- Patch (deterministic): `git checkout -- .ai-engineering/observations/observations.yml`
- Gate: `git status --short .ai-engineering/observations/observations.yml` is
  empty (corpus is unchanged from HEAD; only the timestamp diff is discarded).

- [x] T-7 — VERIFY: confirm no second per-session writer re-introduces churn
- Agent: verify
- Files: `src/ai_engineering/state/instincts.py:58,139,476` (read-only)
- Principles applied: §10.3 SOLID (single-writer boundary)
- Patch (deterministic): none — read-only audit. Trace whether
  `src/ai_engineering/state/instincts.py` (the pip-package twin that also bumps
  `updatedAt`) writes `observations.yml` on any per-session hot path (Stop hook,
  SessionStart, context-pack refresh). If it does, flag for the same idempotency
  guard as a scope note; if it is CLI/`--review`-only (cold path), confirm
  out-of-scope.
- Gate: written finding — either "cold path, no churn" or an explicit
  scope-expansion flag back to `/ai-plan`.

- [x] T-8 — VERIFY: no-op-session convergence (the acceptance gate)
- Agent: verify
- Files: `.ai-engineering/observations/` (read-only)
- Principles applied: §10.5 TDD (acceptance)
- Patch (deterministic): none. Simulate / replay a no-op extraction
  (`extract_instincts` with raw observations but no corpus delta) against a tmp
  project, then assert `git status` for `.ai-engineering/observations/` is clean
  (meta.json ignored, observations.yml untouched).
- Gate: clean `git status` for the observations dir after a simulated no-op
  session — the Goal in spec-162.

## Phase ordering & gates summary

| Phase | Depends | Exit gate |
|---|---|---|
| P1 (T-1→T-3) | — | idempotent tests green + mirror byte-identical |
| P2 (T-4→T-5) | — | meta.json ignored + untracked, on disk |
| P3 (T-6→T-8) | P1, P2 | clean observations/ tree; verify findings clear |

TDD pairing: T-1 (RED) precedes T-2 (GREEN). P1 and P2 are independent and may
run in either order; P3 reset/verify runs last. Final quality loop (verify +
review) runs in `/ai-build` Phase 5 before `/ai-pr`. CHANGELOG note (meta.json
untrack — existing clones drop it from the index on pull) lands via `/ai-docs`
in the PR pipeline.

## T-7 finding (resolved, in-scope extension)

The per-session churn source is the Stop hook → `_lib/instincts.py:extract_instincts`
(now idempotent). `instinct-observe.py` writes only the gitignored NDJSON, not
the corpus. The pip-twin `src/ai_engineering/state/instincts.py` is a CLI/`--review`
cold-path library — NOT the reported symptom's source — but carries the identical
unconditional-bump writer. Applied the same guard + parity tests there
(D-162-01 intent applies to both copies; closes the latent re-churn gap).

## Quality Outcome

- **Verify (deterministic)**: 536 passed / 0 failed across instincts + installer +
  hooks + state + doctor suites; ruff lint + format clean on all changed Python;
  `gitleaks protect --staged` → no leaks; hooks-manifest re-pinned (sha matches).
- **Review (correctness specialist, empirical probes)**: 0 blocker/critical/high.
  Verified no false-"unchanged" data-loss vector (incl. v1→v2 migration baseline +
  confidence-rescore), watermark advances independent of the corpus-write skip
  (no infinite rescan), both twins identical, hook-lib mirror byte-identical,
  meta.json untracking safe (every reader tolerates absence). Two non-actionable
  `info` notes (pre-existing twin write-atomicity divergence; in-place dict
  mutation with single discard-after caller).
- **Verdict**: PASS — no remediation pass consumed.
