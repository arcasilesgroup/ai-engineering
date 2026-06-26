---
title: Exclude sha-pinned hook scripts from framework formatters
spec: spec-179
status: approved
execution_route:
  version: 1
  spec: spec-179
  executor: build
  automation: assisted
  concern_count: 2
  estimated_files: 13
  reason: >
    Two tightly-coupled concerns around one defect (formatter exclusion +
    doctor self-heal). The high file count is dominated by TDD-paired
    regression tests; the production surface is 4 files. A single /ai-build
    context keeps the exclusion and the self-heal coherent. /ai-autopilot is a
    viable alternative if wave decomposition is preferred.
  safe_next_command: "/ai-build"
---

# Plan — spec-179: Exclude sha-pinned hook scripts from framework formatters

Pipeline: **full**. Architecture pattern: **ad-hoc** (surgical guards on two
existing formatter paths + one new doctor check/fixer; no new module
boundaries). Executor route: **/ai-build**.

## Context (from parallel exploration — workflow w5ahlxq54)

- **Gate formatter** lives in `policy/orchestrator.py::run_wave1`, NOT in
  `gate.py`/`stack_runner.py`. The `py_paths` partition (line 323) feeds
  `ruff format`/`ruff check --fix` with explicit file args — ruff's own
  `extend-exclude` is bypassed for explicit args, so the exclusion MUST be in
  `py_paths`. `resolved_staged_files` entries are absolute Paths. One fix
  covers both call sites (pre-commit + `gate run`); convergence re-run reuses
  the same `fixer_specs`.
- **PostToolUse formatter** is `auto-format.py::main`; guard goes between the
  extension compute (line 313) and the `formatter_fn` lookup (line 315). The
  template twin `src/ai_engineering/templates/.ai-engineering/scripts/hooks/auto-format.py`
  is currently byte-identical and MUST receive the identical edit
  (`test_hook_template_parity.py` does a `read_bytes()` equality check).
- **Doctor** uses phase modules exposing `check(ctx)` + `fix(ctx, failed, *, dry_run)`.
  Add to the existing `scripts` phase (`doctor/phases/scripts.py`) — no new
  phase. Bundled reference via `installer/templates.py::get_ai_engineering_template_root()`.
  Re-pin via `regenerate-hooks-manifest.py` (subprocess, `sys.executable`,
  atomic whole-tree walk). The `hooks` manifest section pins every
  `scripts/hooks/**` file (the 76 that broke); CRLF-normalize before hashing.
- **Integrity stays unchanged** (D-179-05) — the fix removes the formatter
  cause; `_lib/integrity.py` is not touched.

---

## Phase 1 — Prevention: gate formatter exclusion (D-179-01)

- [x] T-1 — RED: gate skips `.ai-engineering/scripts/` paths from ruff
  - Agent: build
  - Files: tests/unit/test_orchestrator_wave1.py
  - Principles applied: §10.5 TDD
  - Patch (deterministic): none — model on `test_wave1_passes_only_python_files_to_ruff_for_mixed_staged_set` (~line 695). Stage `<root>/.ai-engineering/scripts/hooks/auto-format.py` alongside `<root>/src/main.py`; patch `subprocess.run` to capture argv; assert the scripts path is ABSENT from the `ruff-format` and `ruff-check` argv while `src/main.py` is PRESENT. Add a second test: when ONLY `.ai-engineering/scripts/*.py` are staged, ruff is not invoked at all (empty `py_paths` guard). Cover posix/relative/backslash-separator variants (R4).
  - Gate: `pytest tests/unit/test_orchestrator_wave1.py -k scripts_exclusion` fails RED

- [x] T-2 — GREEN: filter pinned scripts out of `py_paths`
  - Agent: build
  - Files: src/ai_engineering/policy/orchestrator.py:322
  - Principles applied: §10.1 KISS, §10.4 DRY
  - Patch (deterministic):
    ```diff
    @@ orchestrator.py run_wave1
         fixer_specs: list[tuple[str, list[str]]] = []
         if has_python:
    -        py_paths = [str(path) for path in resolved_staged_files if path.suffix == ".py"]
    -        fixer_specs.append(("ruff-format", ["ruff", "format", *py_paths]))
    -        fixer_specs.append(("ruff-check", ["ruff", "check", "--fix", *py_paths]))
    +        py_paths = [
    +            str(path)
    +            for path in resolved_staged_files
    +            if path.suffix == ".py" and not _is_pinned_script(path)
    +        ]
    +        if py_paths:
    +            fixer_specs.append(("ruff-format", ["ruff", "format", *py_paths]))
    +            fixer_specs.append(("ruff-check", ["ruff", "check", "--fix", *py_paths]))
    ```
    Add the module-level helper near the other path helpers:
    ```python
    def _is_pinned_script(path: Path) -> bool:
        """True when ``path`` is under ``.ai-engineering/scripts/`` (sha-pinned in
        hooks-manifest.json, so byte-stable — a formatter must never touch it).
        spec-179 D-179-01. ``as_posix`` normalizes separators for R4."""
        return ".ai-engineering/scripts/" in path.as_posix()
    ```
  - Gate: T-1 tests GREEN; `pytest tests/unit/test_orchestrator_wave1.py`

---

## Phase 2 — Prevention: PostToolUse hook exclusion + twin parity (D-179-01, D-179-04)

- [x] T-3 — RED: auto-format skips `.ai-engineering/scripts/` + twin carries guard
  - Agent: build
  - Files: tests/unit/hooks/test_auto_format_scripts_exclusion.py (new), tests/unit/test_hook_template_parity.py
  - Principles applied: §10.5 TDD
  - Patch (deterministic): none — new file loads `auto-format.py` via `importlib` (afmt-fixture pattern from `test_auto_format_debounce.py`); drive `main()` with `tool_input.file_path = "/proj/.ai-engineering/scripts/hooks/x.py"` and assert ruff is NOT invoked (patch `_format_python`), passthrough returns; assert `/proj/src/foo.py` DOES proceed. Cover absolute/relative/backslash inputs (R4). In `test_hook_template_parity.py` add a guard-TEXT assertion: both live and template `auto-format.py` contain `".ai-engineering/scripts/"` (catches a one-sided edit even if byte sizes coincide).
  - Gate: `pytest tests/unit/hooks/test_auto_format_scripts_exclusion.py` fails RED

- [x] T-4 — GREEN: add the skip guard to canonical hook
  - Agent: build
  - Files: .ai-engineering/scripts/hooks/auto-format.py:313
  - Principles applied: §10.1 KISS
  - Patch (deterministic):
    ```diff
    @@ auto-format.py main()
         file_path_obj = Path(file_path)
         extension = file_path_obj.suffix.lower()

    +    # spec-179 D-179-01: never reformat sha-pinned framework hook scripts.
    +    # They are byte-locked in hooks-manifest.json; reformatting with the
    +    # consumer's ruff width would break hook integrity for the whole tree.
    +    resolved = file_path_obj.resolve() if file_path_obj.exists() else file_path_obj
    +    if ".ai-engineering/scripts/" in resolved.as_posix():
    +        passthrough_stdin(data)
    +        return
    +
         formatter_fn = _EXTENSION_FORMATTERS.get(extension)
    ```
  - Gate: T-3 exclusion test GREEN

- [x] T-5 — GREEN: apply the byte-identical guard to the template twin
  - Agent: build
  - Files: src/ai_engineering/templates/.ai-engineering/scripts/hooks/auto-format.py:313
  - Principles applied: §10.4 DRY (twin parity)
  - Patch (deterministic): identical hunk to T-4 (same bytes). Then verify byte-equivalence: `diff .ai-engineering/scripts/hooks/auto-format.py src/ai_engineering/templates/.ai-engineering/scripts/hooks/auto-format.py` must be empty.
  - Gate: `pytest tests/unit/test_hook_template_parity.py` GREEN (byte + guard-text)

- [x] T-6 — Re-pin hooks-manifest after the hook edit
  - Agent: build
  - Files: .ai-engineering/state/hooks-manifest.json (regenerated, not hand-edited)
  - Principles applied: §10.7 Clean Code (SSOT cache rebuild)
  - Patch (deterministic): run `.venv/bin/python .ai-engineering/scripts/regenerate-hooks-manifest.py` (editing auto-format.py changed its sha; without re-pin, enforce mode disables the hook).
  - Gate: `python .ai-engineering/scripts/regenerate-hooks-manifest.py --check` exits 0

---

## Phase 3 — Self-heal: doctor drift detection (D-179-02)

- [x] T-7 — RED: doctor scripts phase detects pinned-script sha drift
  - Agent: build
  - Files: tests/unit/test_doctor_phases_scripts.py (new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): none — mirror `test_doctor_phases_hooks.py`. Fixture writes `.ai-engineering/state/hooks-manifest.json` with known pins + matching on-disk hook → `check` returns OK; mutate one on-disk hook's bytes → `check` returns `WARN` with `fixable=True` naming the drifted path.
  - Gate: `pytest tests/unit/test_doctor_phases_scripts.py -k drift` fails RED

- [x] T-8 — GREEN: add `_check_hooks_manifest_sha_drift` to the scripts phase
  - Agent: build
  - Files: src/ai_engineering/doctor/phases/scripts.py
  - Principles applied: §10.2 YAGNI (reuse existing phase, no new phase), §10.8 Hexagonal (check is pure inspection)
  - Patch (deterministic): none (judgment). New private `_check_hooks_manifest_sha_drift(ctx)`: load `ctx.target/.ai-engineering/state/hooks-manifest.json`; for every key in `hooks` (and `trustedScripts`), CRLF-normalize the on-disk file bytes (match `compute_file_sha256`), sha256, compare to pin; collect drifted relative paths; return `CheckResult(name="hooks-manifest-sha-drift", status=WARN, fixable=True, message="<n> pinned scripts drifted: [...]")` or `OK`. Append it to the `check()` return list. Guard missing manifest/file with OK-skip (fail-open on plumbing).
  - Gate: T-7 GREEN

- [x] T-9 — Update doctor phase-count guard
  - Agent: build
  - Files: tests/unit/test_doctor_phase_parity.py
  - Principles applied: §10.5 TDD (keep guards honest)
  - Patch (deterministic): none — if the test asserts a per-phase check count for `scripts`, bump the expected count by 1. If it does not, no change (verify only).
  - Gate: `pytest tests/unit/test_doctor_phase_parity.py` GREEN

---

## Phase 4 — Self-heal: safe-by-default re-pin (D-179-03)

- [x] T-10 — RED: fixer re-pins reflow-only drift, refuses AST divergence
  - Agent: build
  - Files: tests/integration/doctor/test_doctor_fix_stack_drift.py, tests/unit/test_doctor.py
  - Principles applied: §10.5 TDD
  - Patch (deterministic): none. Integration (mirror `test_doctor_phase_scripts_fix_redeploys`): (1) on-disk hook reflowed (whitespace-only, AST-equal to bundled reference) → `fix` re-pins manifest, returns `FIXED`; (2) on-disk hook with a real logic change (AST differs) → `fix` returns `WARN`, manifest sha UNCHANGED (fail-closed); (3) bundled reference absent → `fix` returns `WARN`, no re-pin (R2). Unit (`test_doctor.py` TestDiagnose): inject hooks-phase `WARN`+`fixable=True` → `diagnose()` `passed=True`; `diagnose(fix=True)` surfaces a `FIXED` check; `dry_run=True` returns `FIXED` WITHOUT invoking the regenerator.
  - Gate: new tests fail RED

- [x] T-11 — GREEN: `_fix_hooks_manifest_sha_drift` with AST-equivalence gate
  - Agent: build
  - Files: src/ai_engineering/doctor/phases/scripts.py
  - Principles applied: §10.8 Hexagonal (pure decision + isolated subprocess side-effect), gate-policy fail-closed
  - Patch (deterministic): none (judgment). Add a `fix()` branch on `cr.name == "hooks-manifest-sha-drift"`. Re-scan drift on entry (do not trust message). For each drifted `.py`: load bundled reference at `get_ai_engineering_template_root()/"scripts"/<rel>`; compare `ast.dump(ast.parse(b), include_attributes=False)` of on-disk vs reference. For `.sh`/`.ps1`: CRLF-normalized byte-equality vs reference instead of AST. If ALL drifted files are provably benign (equivalent) and not `dry_run`: re-pin once via `regenerate-hooks-manifest.py` (subprocess, `sys.executable`, `cwd=ctx.target`) — atomic whole-tree walk → `FIXED`. If `dry_run`: report `FIXED` without the subprocess. If ANY file diverges or its reference is missing: `WARN` (`fixable=False`), manifest untouched.
  - Gate: T-10 GREEN; `pytest tests/integration/doctor/test_doctor_fix_stack_drift.py tests/unit/test_doctor.py`

- [x] T-12 — RED→GREEN: end-to-end format-induces-drift → re-pin recovers
  - Agent: build
  - Files: tests/unit/hooks/test_integrity_default.py
  - Principles applied: §10.5 TDD
  - Patch (deterministic): none. Write an 88-col reflow of a hook on disk + a manifest pinned to the 100-col sha → `verify_hook_integrity` returns `ok=False`. Update the manifest sha to the on-disk value → `verify_hook_integrity` returns `ok=True`. Proves the defect + the recovery in one test. (Integrity code itself unchanged — D-179-05.)
  - Gate: `pytest tests/unit/hooks/test_integrity_default.py` GREEN

---

## Phase 5 — Docs + final gates

- [x] T-13 — CHANGELOG entry
  - Agent: build
  - Files: CHANGELOG.md
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): none — under the Unreleased `Fixed` heading add: "Hook scripts under `.ai-engineering/scripts/` are now excluded from the pre-commit gate and PostToolUse auto-formatters, so installing onto a project with a different ruff width no longer breaks hook integrity (spec-179). `ai-eng doctor --fix` re-pins formatter-induced reflow drift safely (AST-equivalent to the bundled reference only)."
  - Gate: `pytest tests/docs` (CHANGELOG gate) GREEN

- [x] T-14 — Full suite + spec_lint + manifest finalize
  - Agent: verify
  - Files: (read-only verification)
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): none. Run `pytest tests/unit tests/integration -q`; `python -m tools.spec_lint --check .ai-engineering/specs/spec.md .ai-engineering/specs/plan.md`; `python .ai-engineering/scripts/regenerate-hooks-manifest.py --check` exits 0; `ai-eng check`.
  - Gate: all green; no blocker/critical/high findings

---

## Risk coverage map

- R1 (framework dev loses auto-format on its own scripts) → in-repo no-op: bytes already match 100-col pins; CI `ruff format --check .` still enforces. No task needed.
- R2 (bundled reference absent) → T-10 case 3 + T-11 fail-closed `WARN`.
- R3 (twin parity no CI guard) → T-3 guard-text assertion + T-5 byte-equivalence.
- R4 (path separators) → T-1/T-3 posix/relative/backslash coverage; `as_posix()` in both guards.

## Notes

- No new dependency: `ast` is stdlib (already used in `verify/service.py`).
- Single-concern coupling: Phases 1-2 (prevention) and 3-4 (self-heal) can land
  in one PR; they share the `.ai-engineering/scripts/` boundary and the manifest.
- Already remediated out-of-band (NOT in this plan): ai-engineering-web manifest
  re-pin; global `~/.claude/settings.json` node-path fix.

## Quality Outcome

All 14 tasks complete (TDD RED→GREEN per phase). Deterministic gates green:

- **Tests**: 2394 passed / 0 failed (targeted regression over policy/gate/orchestrator/
  doctor/installer/hooks/manifest/integrity) + 645 passed in the focused touched-area
  suite + 55 doctor tests after the security-1 remediation. 16 new tests added.
- **Lint/format**: `ruff check` + `ruff format --check` clean on all changed files.
- **Manifest**: `regenerate-hooks-manifest.py --check` exits 0 (auto-format re-pin holds).
- **spec_lint**: 6/6, 0 blockers / 0 advisories.
- **ai-eng check**: 7/7 content-integrity categories pass.

Quality loop (1 bounded remediation pass):

- **Correctness review** (`reviewer-correctness`): `findings: []` — no defects across all
  five focus areas. CRLF normalization consistent across detector/classifier/regenerator;
  `fix()` dispatch robust to unfiltered callers; fail-closed `_is_benign_reflow` confirmed.
  2 informational notes (comment-only AST invisibility; non-existent-file relative-path
  false-negative) — both within D-179-01/03 intent, no action.
- **Security review** (`reviewer-security`): fail-closed posture HOLDS; integrity.py
  unchanged (D-179-05); formatter exclusion bypasses no security scan (Wave 1 is
  autoformat, not the gitleaks/semgrep gate). Two MINOR findings:
  - **security-1** (path-traversal in `_bundled_reference`) — **REMEDIATED**: added a
    `resolve()` + `relative_to(root)` containment check so a `..` manifest key resolves
    no trusted reference (→ WARN, never auto-pinned). Covered by 2 new regression tests.
  - **security-2** (TOCTOU between drift validation and the regen re-walk) — accepted
    residual: operator-local `--fix` window, requires local write access, grants no
    privilege beyond already owning the manifest trust root. Documented; not remediated.

No blocker/critical/high findings remain. Ready for `/ai-pr`.
