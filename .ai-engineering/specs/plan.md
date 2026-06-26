---
title: Normalize spec-state ledger and dogfood template parity
spec: spec-180
status: draft
execution_route:
  version: 1
  spec: spec-180
  executor: autopilot
  automation: assisted
  concern_count: 3
  estimated_files: 30
  reason: >
    Three concerns (ledger reconcile+guard, sweep safety, template parity) over
    ~30 files including a one-time reconcile of ~19 tracked sidecars. Phases 1-3
    all edit the same stdlib-only spec_lifecycle.py (sequential, no parallel file
    conflict); Phase 4 runs the reconcile; Phase 5 re-syncs the template twin and
    guards parity. Breadth + the autonomous data mutation route this through
    /ai-autopilot multi-wave rather than a single /ai-build.
  safe_next_command: "/ai-autopilot"
---

# Plan — spec-180: Normalize spec-state ledger and dogfood template parity

Pipeline: **full**. Architecture: **ad-hoc** (three new/changed verbs in one
stdlib script + a one-time data reconcile + parity guards). Executor: **/ai-autopilot**.

## Context (from parallel exploration — workflow wncan0p4j)

- **`spec_lifecycle.py`** (canonical `.ai-engineering/scripts/`, 1716 lines,
  **stdlib-only**) holds every verb. A **byte-identical template twin** lives at
  `src/ai_engineering/templates/.ai-engineering/scripts/spec_lifecycle.py` with
  **no CI parity guard today** — every edit to the canonical MUST be mirrored
  (Phase 5 adds the guard). Constraints: use `timezone.utc` NOT `UTC`
  (`test_spec_lifecycle_python_compat` forbids it); do NOT import
  `ai_engineering.git.operations` — reimplement protected-branch detection inline
  via the existing `_git_stdout` helper.
- **Sweep** abandons at `sweep()` ~line 657 (`transition(..., ABANDONED)` then
  `_write_state`) with NO shipped-detection and writes in place — the churn
  mechanism. Existing signal helpers: `_pr_merged_via_gh` (~1128),
  `_resolve_merged_pr` (~1089), `_resolve_via_archive_dir` (~1257),
  `_history_spec_ids`, `_spec_id_in_ledger`, `reconcile_merged` (~1166),
  `mark_shipped`/`_snapshot_and_reset` (449-497, archive write).
- **Bundle-PR reality** (critical for reconcile): `gh pr list --head <branch>`
  returns EMPTY for specs merged in a bundle PR — spec-129/131/132/133 → PR#509
  (branch `spec-128/...`); 144/145/146 → `codex/spec-145-...`; 136 → PR#514
  (`claude/combined-spec-136-137`); 166 → PR#586 (branch null). The reconcile
  must fall back to **`_history.md` ledger row** + **archive dir** + **live
  `D-NNN-*` decision refs** (scoped to CLAUDE.md, CONSTITUTION.md, SOUL.md,
  `reference/*.md`, `docs/*.md`, CHANGELOG.md, solution-intent.md, LESSONS.md,
  `src/`, `.github/`). Likely-abandoned (zero evidence): spec-155, spec-171
  (parked drafts only), antigravity, skills-agents-excellence-v2, spec-135
  (ledger says approved, superseded by spec-139).
- **Guard** (`check_ledger`): 4 rules — (1) non-terminal but archive/live-ref
  shipped, (2) shipped + null PR + no archive, (3) shipped + no archive entry,
  (4) id↔slug numeric mismatch (real case: `spec-158.json` slug=`spec-159`). Must
  TOLERATE in-flight (draft/approved/in_progress null PR), ABANDONED (null
  PR/shipped), the idle `# No active spec` slot, and SHIPPED specs absent from
  `_history.md` (rows pre-128 predate sidecars — not a violation).
- **Template parity**: 9 top-level `.ai-engineering/scripts/*.py` are NOT
  byte-guarded. Exclude project-specific: `specs/spec.md`+`plan.md` (live slot),
  `state/`, `scripts/spec-131/` (migration subdir), `manifest.yml`/`LESSONS.md`/
  `suppression-allowlist.yml`/`solution-intent.md` (intentionally diverged),
  `observations/`/`cache/`/`evals/`/`schemas/`/`team/`/`specs/archive`+`drafts`.

---

## Phase 1 — Engine: `check_ledger` guard verb (D-180-04)

- [x] T-1 — RED: ledger-consistency guard tests
  - Agent: build
  - Files: tests/unit/specs/test_spec_lifecycle.py
  - Principles applied: §10.5 TDD
  - Patch (deterministic): none — add `class TestLedgerConsistencyGuard` (end of file, tmp_path-isolated like `TestConsolidateShipped`; add `_seed_shipped_sidecar` helper). Assert `check_ledger(project_root)` returns violations for: shipped+null-PR+no-archive; non-terminal whose `archive/<spec>-<slug>/` exists; id↔slug numeric mismatch (`spec-158`/`spec-159`). Assert ZERO violations for: in-flight draft/approved/in_progress (null PR), ABANDONED (null PR/shipped), shipped+archive present, shipped absent from `_history.md`.
  - Gate: `pytest tests/unit/specs/test_spec_lifecycle.py -k LedgerConsistency` fails RED

- [x] T-2 — GREEN: `check_ledger()` verb + CLI
  - Agent: build
  - Files: .ai-engineering/scripts/spec_lifecycle.py
  - Principles applied: §10.1 KISS, §10.8 Hexagonal (pure read-only inspection)
  - Patch (deterministic): none (judgment). Add `check_ledger(project_root) -> dict` after `consolidate_shipped`: iterate `state/specs/*.json`, apply the 4 rules (reuse `_resolve_via_archive_dir`, slug numeric-prefix extraction), return `{"violations": [{spec_id, rule, detail}], "checked": N}`. Register `check_ledger` in `_build_parser()` + `main()` (stdlib-only; `timezone.utc`).
  - Gate: T-1 GREEN; `pytest tests/unit/specs/test_spec_lifecycle.py`

---

## Phase 2 — Engine: `reconcile_all` 3-signal verb (D-180-03)

- [x] T-3 — RED: full-ledger reconcile tests (3 signals + bundle fallback + dry_run)
  - Agent: build
  - Files: tests/unit/specs/test_spec_lifecycle.py
  - Principles applied: §10.5 TDD
  - Patch (deterministic): none — `class TestReconcileAll` (mirror `TestReconcileMerged`, `_FakeGit`): shipped when ANY signal (gh PR, `_history.md` ledger row done/shipped, archive dir, live `D-NNN-*` ref) holds; abandoned ONLY when all absent AND superseded/old; terminal states never downgraded; `dry_run=True` returns the report with zero mutation; the report lists per-spec evidence. Cover a bundle-PR sidecar (branch resolves empty via gh → ledger/archive signal wins).
  - Gate: `pytest ... -k ReconcileAll` fails RED

- [x] T-4 — GREEN: `reconcile_all()` + signal helpers + id-map
  - Agent: build
  - Files: .ai-engineering/scripts/spec_lifecycle.py
  - Principles applied: §10.4 DRY (reuse existing resolvers), §10.8 Hexagonal
  - Patch (deterministic): none (judgment). Add `reconcile_all(project_root, *, default_branch=_DEFAULT_BRANCH, dry_run=False) -> dict` after `reconcile_merged`: for each stale (non-terminal) sidecar gather the 4 signals (extend with `_live_decision_refs(spec_id)` grep over the scoped surfaces + `_history` ledger-row lookup); classify shipped/abandoned/keep; on non-dry-run call `mark_shipped`/transition; emit a `framework_operation` event; return a report dict. Add `_EXPLICIT_ID_MAP` entry `ai-engineering-release-version-cicd-pypi → spec-143`. Register `reconcile_all` CLI verb.
  - Gate: T-3 GREEN

---

## Phase 3 — Engine: sweep safety (D-180-05)

- [x] T-5 — RED: sweep is mislabel-safe + protected-branch-safe
  - Agent: build
  - Files: tests/unit/specs/test_spec_lifecycle.py
  - Principles applied: §10.5 TDD
  - Patch (deterministic): none — extend `TestSweep`: a stale DRAFT whose branch/ledger/archive classifies SHIPPED is NOT abandoned (routed to shipped or skipped, `skipped_shipped` counter ++); on a protected branch (`main`/`master`/`default_branch`) sweep refuses in-place writes (returns `{"protected_branch": ..., "skipped": "on-protected-branch"}`, no sidecar mutation); `dry_run=True` mutates nothing.
  - Gate: `pytest ... -k Sweep` fails RED

- [x] T-6 — GREEN: sweep shipped-detection gate + protected-branch guard
  - Agent: build
  - Files: .ai-engineering/scripts/spec_lifecycle.py
  - Principles applied: §10.1 KISS, gate-policy fail-closed (no write on protected)
  - Patch (deterministic): none (judgment). `sweep(project_root, *, default_branch=_DEFAULT_BRANCH, dry_run=False)`: at top, detect current branch via `_git_stdout(... 'rev-parse','--abbrev-ref','HEAD')`; if in `{"main","master",default_branch}` → return refusal summary without writing. Before the abandon at ~line 657, run shipped-detection (`_pr_merged_via_gh`/`_branch_is_merged` when branch set, else the reconcile signals); if shipped → mark_shipped/skip, else abandon. Add `skipped_shipped` counter.
  - Gate: T-5 GREEN; full `pytest tests/unit/specs/test_spec_lifecycle.py`

---

## Phase 4 — Apply: reconcile the live ledger + spot-fixes (D-180-03 apply, D-180-07)

- [x] T-7 — Run `reconcile_all` against the live corpus (feature branch)
  - Agent: build
  - Files: .ai-engineering/state/specs/*.json (mutated to truth), .ai-engineering/runtime/reconcile-report.md (artifact)
  - Principles applied: §10.7 Clean Code (one clearly-scoped data commit)
  - Patch (deterministic): none. Run `python .ai-engineering/scripts/spec_lifecycle.py reconcile_all --dry-run` first, attach the report; then run non-dry on the feature branch (NOT main — D-180-05 guard enforces). Reconciles the ~19 stale sidecars (bundle-merged → shipped; zero-evidence → abandoned). Verify each result against the per-spec evidence in the plan Context.
  - Gate: report emitted; `git status` shows only intended sidecar state flips

- [x] T-8 — Spot-fixes + zero-violation verification (D-180-07)
  - Agent: build
  - Files: .ai-engineering/state/specs/spec-158.json, .ai-engineering/specs/archive/spec-152-github-actions-supply-chain-hardening/ (backfilled), .ai-engineering/scripts/spec_lifecycle.py (`_EXPLICIT_ID_MAP`)
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): none. Resolve `spec-158.json` id↔slug mismatch (slug `spec-159`); backfill spec-152's missing `archive/` snapshot from its archived spec/plan (or the merge commit). Then run `check_ledger` → MUST return zero violations.
  - Gate: `spec_lifecycle.py check_ledger` → 0 violations

---

## Phase 5 — Template parity (D-180-06)

- [x] T-9 — RED: top-level scripts byte-parity guard
  - Agent: build
  - Files: tests/unit/test_template_parity.py
  - Principles applied: §10.5 TDD, §10.4 DRY (one parametrized test, not 9 files)
  - Patch (deterministic): none — add `class TestTopLevelScriptsParity` parametrized over the 9 top-level `.ai-engineering/scripts/*.py` (branch_slug, commit_compose, doc_gate, plan_tasks, pr_body_compose, regenerate-hooks-manifest, runtime_rotate, session_bootstrap, spec_lifecycle): CRLF-normalized `read_bytes()` (or SHA-256) equality live vs `templates/`. Add the explicit EXCLUSION list (live slot, state/, `scripts/spec-131/`, intentionally-diverged manifest/LESSONS/suppression/solution-intent). This FAILS now because Phases 1-3 edited canonical `spec_lifecycle.py` but not the twin.
  - Gate: `pytest tests/unit/test_template_parity.py -k TopLevelScripts` fails RED (twin drift)

- [x] T-10 — GREEN: re-sync the spec_lifecycle twin (+ optional Surface 11)
  - Agent: build
  - Files: src/ai_engineering/templates/.ai-engineering/scripts/spec_lifecycle.py, scripts/sync_mirrors/core.py
  - Principles applied: §10.4 DRY (dev sync becomes the single regen)
  - Patch (deterministic): copy canonical `spec_lifecycle.py` over the template twin byte-for-byte (carries the Phase 1-3 edits). Optionally add Surface 11 to `sync_mirrors/core.py` to propagate top-level scripts (excluding `spec-131/`) so `ai-eng dev sync` keeps parity going forward. Verify all 9 scripts byte-match.
  - Gate: T-9 GREEN; `pytest tests/unit/test_template_parity.py`

---

## Phase 6 — CI wiring + final gates

- [x] T-11 — Wire the guard into the live-corpus CI check
  - Agent: build
  - Files: tests/unit/specs/test_state_canonical.py
  - Principles applied: §10.5 TDD
  - Patch (deterministic): none — add a test reading the live `state/specs/` corpus and asserting `check_ledger(PROJECT_ROOT)["violations"] == []`, so CI fails on any future ledger drift (the D-180-04 contract). Must pass after Phase 4.
  - Gate: `pytest tests/unit/specs/test_state_canonical.py`

- [x] T-12 — CHANGELOG + full suite + spec_lint + manifest
  - Agent: verify
  - Files: CHANGELOG.md
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): none. CHANGELOG Unreleased entry (ledger reconcile + guard + sweep safety + template parity). Run `pytest tests/unit tests/integration -q`; `python -m tools.spec_lint --check .ai-engineering/specs/spec.md`; `python .ai-engineering/scripts/regenerate-hooks-manifest.py --check`; `ai-eng check`; `spec_lifecycle.py check_ledger` → 0.
  - Gate: all green; no blocker/critical/high

---

## Dependency notes (for autopilot DAG)

- Phases 1→2→3 edit the SAME file (`spec_lifecycle.py`) — **sequential**, no parallel wave (file conflict).
- Phase 4 depends on 1-3 (needs `reconcile_all` + `check_ledger`).
- Phase 5 depends on 1-3 (twin re-sync must carry the engine edits) — and on nothing in Phase 4.
- Phase 6 depends on all.

## Risk coverage map

- R1 (autonomous mislabel) → T-3/T-4 3-signal + T-7 dry-run report + T-1/T-11 guard (zero-violation CI).
- R2 (large reconcile diff) → T-7 lands it as one scoped data commit + report artifact.
- R3 (parity guard too strict) → T-9 explicit exclusion list, CRLF-normalized.
- R4 (false-positive live-ref) → T-4 scopes refs to `D-NNN-*` anchors over a fixed surface list.

## Notes

- Engine is stdlib-only: `timezone.utc` not `UTC`; no `git.operations` import; protected-branch via `_git_stdout`.
- Every `spec_lifecycle.py` edit (Phases 1-3, T-8) must propagate to the template twin (T-10) — the new parity guard (T-9) enforces it.
- The reconcile (T-7) mutates tracked sidecars; it runs on the feature branch, never main (D-180-05 guard).

## Quality Outcome

All 12 tasks complete (TDD RED→GREEN; engine via dispatched build agent, data
reconcile + parity/guard driven directly with hand-verification of every
edge-case classification).

- **Tests**: 597 passed / 0 failed across affected areas (specs, scripts, sync,
  installer, template-parity); engine suite 180 passed; live-corpus
  `test_spec_state_ledger_is_consistent` green.
- **Ledger**: reconciled 40 sidecars → 34 shipped (PRs backfilled), 3 abandoned,
  spec-180 in_progress, spec-155 draft + spec-171 approved kept (zero-evidence,
  not auto-abandoned), spec-158→spec-159 + cicd-pypi→spec-143 renamed, spec-152
  archive backfilled. `check_ledger` → 0 violations (exit 0).
- **Hand-verified edge cases**: spec-154 shipped (D-154-03 in resolve-python.sh),
  spec-135 abandoned (ledger `approved`, no ship, superseded by spec-139),
  spec-143 shipped (#517 via id-map), spec-158=spec-159 (#561 + archive).
- **Reconcile↔guard integration fix** (caught in dry-run review): reconcile now
  backfills PR from the ledger row; `check_ledger` accepts ledger-row/decision-ref
  as evidence — so freshly-reconciled shipped specs are not false-flagged.
- **Parity**: spec_lifecycle twin re-synced; new byte-parity guard over all 9
  top-level scripts. `ruff` clean · `spec_lint` 0 blockers · manifest `--check` 0
  · `ai-eng check` 7/7.
