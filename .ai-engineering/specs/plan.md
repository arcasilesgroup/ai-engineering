---
execution_route:
  version: 1
  spec: spec-157
  executor: build
  automation: assisted
  concern_count: 1
  estimated_files: 30
  reason: "Single concern (re-land version-update-notice scope-free). Mostly mechanical transplant of proven green files + two targeted single-scope rewrites + two rider cherry-picks. One coherent feature, build-routable; not multi-concern, so not autopilot."
  safe_next_command: "/ai-build"
status: approved
---

# Plan — spec-157 Version Update Notice: Clean Re-land

## Design

Re-land is a TRANSPLANT, not a redesign. The version-notice design is proven and
green in PR #556. The plan moves proven artifacts onto a fresh main-cut branch,
rewrites only the two genuinely scope-coupled files back to single-scope, brings
two CI-green riders, and asserts zero scope residue. Source of truth for the
"old" artifacts is the `feat/version-update-notice` branch (PR #556); the build
agent reads files from it via `git show <ref>:<path>` / `git checkout <ref> --
<path>`.

`OLD = feat/version-update-notice` (PR #556 tip). `BASE = main`.

## Architecture

Pattern: **branch-transplant migration** (ad-hoc). Three rails:
1. Verbatim copy of scope-clean source + tests from OLD.
2. Single-scope rewrite of the two coupled files to the BASE shape + KEEP-block
   graft.
3. Rider cherry-pick (security/governance, scope-independent).

No new abstractions. local-always-wins is the only model (it is BASE's model).

## Phases

Order: P0 branch+preserve → P1 riders → P2 verbatim transplant → P3 coupled
rewrites → P4 strip+wire cleanup → P5 gate. RED-before-GREEN does not apply
(tests are transplanted alongside their proven implementations); the gate phase
is the verification contract.

---

### Phase 0 — Branch + preserve briefs

- [ ] T-0a — Preserve the two global briefs before switching branches
  - Agent: build
  - Files: `.ai-engineering/specs/drafts/global-install-work-plane-brief.md`, `.ai-engineering/specs/drafts/global-hook-surface-resilience-brief.md`
  - Principles applied: §10.2 YAGNI (keep the validated artifact, drop the over-built code)
  - Patch (deterministic): none — `git stash push -- .ai-engineering/specs/drafts/global-*-brief.md` OR copy to `/tmp` so they survive the branch cut; restore after T-0b.
  - Gate: both files readable after T-0b.

- [ ] T-0b — Cut the clean branch from main
  - Agent: build
  - Files: (git ref only)
  - Principles applied: §10.1 KISS (D-157-01 fresh branch, zero residue)
  - Patch (deterministic): none — `git fetch origin && git switch -c feat/version-update-notice-clean origin/main` (or local `main` if current).
  - Gate: `git rev-parse --abbrev-ref HEAD` == `feat/version-update-notice-clean`; `git merge-base --is-ancestor main HEAD` true; spec.md + plan.md (spec-157) and both briefs present in the working tree on the new branch.

- [ ] T-0c — Land spec-157 spec.md + plan.md + briefs on the new branch
  - Agent: build
  - Files: `.ai-engineering/specs/spec.md`, `.ai-engineering/specs/plan.md`, `.ai-engineering/specs/drafts/global-*-brief.md`
  - Principles applied: §10.6 SDD (the spec/plan are the contract for this branch)
  - Patch (deterministic): none — ensure the spec-157 spec.md/plan.md (currently working-tree) and the restored briefs are on the new branch; commit them: `docs(spec-157): clean version-notice re-land spec + plan`.
  - Gate: `git show HEAD:.ai-engineering/specs/spec.md` frontmatter `spec: spec-157`.

---

### Phase 1 — Riders (cherry-pick, CI-green-required)

- [ ] T-1a — Cherry-pick `.snyk` CVE-2026-8643 accept
  - Agent: build
  - Files: `.snyk`
  - Principles applied: §13.1 Secrets/CVE gate (Hard Rule 1 — branch must pass the same gate as main)
  - Patch (deterministic): none — `git cherry-pick 5b9b4272`. If it touches more than `.snyk`, instead `git checkout 5b9b4272 -- .snyk` and commit `chore(security): risk-accept CVE-2026-8643 (pip) in Snyk gate`.
  - Gate: `.snyk` contains the CVE-2026-8643 entry; `pip-audit`/Snyk gate green locally if runnable.

- [ ] T-1b — Cherry-pick decision-store tracking
  - Agent: build
  - Files: `.gitignore`, `.ai-engineering/state/decision-store.json`, `CHANGELOG.md`, `docs/persistence-doctrine.md`, `src/ai_engineering/installer/gitignore.py`, `tests/unit/installer/test_project_gitignore.py`
  - Principles applied: §13.7 SSOT per datum (decision-store becomes a tracked canonical store)
  - Patch (deterministic): none — `git cherry-pick d6db3dc7`; resolve any CHANGELOG conflict by keeping both entries.
  - Gate: `git check-ignore .ai-engineering/state/decision-store.json` returns nothing (no longer ignored); `pytest tests/unit/installer/test_project_gitignore.py` green.

---

### Phase 2 — Verbatim transplant (scope-clean source + tests)

- [ ] T-2a — Transplant the `version/` package from OLD
  - Agent: build
  - Files: `src/ai_engineering/version/{cache,compare,install_method,pypi,refresh,__init__,checker}.py`
  - Principles applied: §10.4 DRY (reuse proven green modules; do not rewrite)
  - Patch (deterministic): none — `git checkout OLD -- src/ai_engineering/version/cache.py src/ai_engineering/version/compare.py src/ai_engineering/version/install_method.py src/ai_engineering/version/pypi.py src/ai_engineering/version/refresh.py src/ai_engineering/version/__init__.py src/ai_engineering/version/checker.py` (OLD = `feat/version-update-notice`).
  - Gate: `grep -rE "scope|brain_root|global" src/ai_engineering/version/` returns only benign prose (no module refs); `python -c "import ai_engineering.version.refresh, ai_engineering.version.pypi, ai_engineering.version.cache, ai_engineering.version.compare, ai_engineering.version.install_method"` imports clean.

- [ ] T-2b — Transplant `config/manifest.py` VersionCheckConfig
  - Agent: build
  - Files: `src/ai_engineering/config/manifest.py`
  - Principles applied: §10.3 SOLID (config model isolated)
  - Patch (deterministic): none — if `manifest.py` has no other OLD changes, `git checkout OLD -- src/ai_engineering/config/manifest.py`; else graft only the `VersionCheckConfig` class + `version_check` field (+14 lines). Verify no scope field rode along.
  - Gate: `pytest tests/unit/config/test_manifest.py` green; no `scope` field in the manifest model.

- [ ] T-2c — Transplant `cli_factory.py` (fully scope-clean)
  - Agent: build
  - Files: `src/ai_engineering/cli_factory.py`
  - Principles applied: §10.4 DRY (proven notice wiring + `version_app` sub-typer)
  - Patch (deterministic): none — `git checkout OLD -- src/ai_engineering/cli_factory.py` (agent confirmed zero scope imports).
  - Gate: `grep -E "scope_resolution|installer.*scope|brain_root" src/ai_engineering/cli_factory.py` returns nothing; CLI builds (`python -c "import ai_engineering.cli_factory"`).

- [ ] T-2d — Transplant the 11 version-notice test files
  - Agent: build
  - Files: `tests/unit/version/{__init__,test_cache,test_compare,test_install_method,test_pypi,test_refresh}.py`, `tests/unit/test_cli_ui_notice.py`, `tests/unit/test_cli_notice_exempt.py`, `tests/unit/test_version_lifecycle.py`, `tests/unit/cli_commands/test_version_upgrade.py`, `tests/integration/test_version_checker.py`
  - Principles applied: §10.5 TDD (the proven test contract travels with its implementation)
  - Patch (deterministic): none — `git checkout OLD -- tests/unit/version/ tests/unit/test_cli_ui_notice.py tests/unit/test_cli_notice_exempt.py tests/unit/test_version_lifecycle.py tests/unit/cli_commands/test_version_upgrade.py tests/integration/test_version_checker.py`.
  - Gate: files present; `grep -rE "scope|--global|dual_scope" tests/unit/version/` clean. (Tests will fail to collect until P3 lands cli_ui/core/updater — expected; P5 is the green gate.)

---

### Phase 3 — Coupled-file single-scope rewrites

- [ ] T-3a — Transplant `cli_ui.py` notice block, strip `announce_scope`
  - Agent: build
  - Files: `src/ai_engineering/cli_ui.py:392-528`, `cli_ui.py:416-433`
  - Principles applied: §10.7 Clean Code (D-157-03 no dead scope rider)
  - Patch (deterministic): none (judgment) — start from `git checkout OLD -- src/ai_engineering/cli_ui.py`, then DELETE the `announce_scope` function (`~416-433`) and any `announce_scope` export. Keep `maybe_render_update_notice`, `_render_update_notice`, `_load_version_check_config`.
  - Gate: `grep -n "announce_scope" src/ai_engineering/cli_ui.py` returns nothing; `python -c "import ai_engineering.cli_ui"` clean.

- [ ] T-3b — Rewrite `updater/service.py` to single-scope
  - Agent: build
  - Files: `src/ai_engineering/updater/service.py:122-171,444-446,449-504,507-589,766-790,793-839,842-887,900-912,915-928,931-946,949-965`
  - Principles applied: §10.1 KISS, §10.4 DRY (collapse dual-scope to the BASE shape)
  - Patch (deterministic): none (judgment) — base file is BASE's `updater/service.py`; graft ONLY the version-notice/self-upgrade additions from OLD. DROP: `ScopeNotInstalledError`, `_SCOPE_INSTALL_HINT`, `_scope_is_installed`, `update_scopes`, `reconcile_scopes_with_skips`, `_scope_root`, `_update_dests`, `_orphan_path`, `_merge_update_results`, `UpdateResult.skipped_scopes`. REVERT scope params on `update`, `_evaluate_project_files`, `_detect_orphan_files`, `_provider_orphan_changes`, `_provider_file_orphans`, `_provider_tree_orphans` to BASE signatures. Net: file should differ from BASE only by any genuine version-notice hook (likely none — confirm `git diff main -- src/ai_engineering/updater/service.py` is empty or notice-only).
  - Gate: `grep -nE "scope|brain_root|_update_dests|_orphan_path|ScopeNotInstalled|skipped_scopes" src/ai_engineering/updater/service.py` returns nothing; `pytest tests/unit/updater/ -k "not dual_scope"` green.

- [ ] T-3c — Rewrite `cli_commands/core.py`: keep version block, drop scope
  - Agent: build
  - Files: `src/ai_engineering/cli_commands/core.py:31,151-164,181,196,209,215-219,236,263-268,304,330-345,384-414,451-480,568-581,584-599,1135-1142,1144-1148,1153,1155-1160,1163,1172-1196,1243-1254,1257-1298,1301-1314,1697-1846`
  - Principles applied: §10.3 SOLID, §10.7 Clean Code (one concern per command; no scope contamination)
  - Patch (deterministic): none (judgment) — base file is BASE's `core.py`; graft the KEEP block (`_cached_latest` 1697-1706, `version_cmd` 1709-1738 incl. `ctx`/sub-command guard, `_MANUAL_UPGRADE_COMMANDS` 1741-1746, `_emit_manual_upgrade_guidance` 1749-1773, `version_upgrade_cmd` 1776-1846) and the notice wiring. DROP: `scope_global`/`scope_local` on `install_cmd` + `update_cmd`, `_explicit_install_scope`, `_resolve_update_scope`, `_merge_update_results`, `announce_scope` import (`31`), `brain_root` routing (`263-268`), scope except-block (`1172-1196`). REVERT `_is_reinstall`, `_resolve_install_configuration`, `_resolve_first_install_configuration`, `_run_update_with_spinner`, `_emit_install_dry_run_plan`, `_run_install_pipeline` to BASE signatures (no `scope` param). KEEP `success` import (`42`).
  - Gate: `grep -nE "scope_global|scope_local|_explicit_install_scope|_resolve_update_scope|announce_scope|brain_root|ScopeNotInstalled" src/ai_engineering/cli_commands/core.py` returns nothing; `ai-eng version` and `ai-eng version upgrade --help` run; `pytest tests/unit/cli_commands/test_version_upgrade.py` green.

- [ ] T-3d — Drop scope-announce from `config.py`
  - Agent: build
  - Files: `src/ai_engineering/cli_commands/config.py:57-62`
  - Principles applied: §10.7 Clean Code (remove scope rider)
  - Patch (deterministic): none (judgment) — remove the `announce_scope(resolve_scope(root).announce)` block + the two scope imports; restore `config_cmd` to BASE behavior. Easiest: `git checkout main -- src/ai_engineering/cli_commands/config.py` (config has no version-notice additions).
  - Gate: `grep -nE "scope_resolution|announce_scope" src/ai_engineering/cli_commands/config.py` returns nothing; `pytest tests/unit -k config` green.

---

### Phase 4 — Residue sweep + manifest consistency

- [ ] T-4a — Assert zero scope residue across src/
  - Agent: verify
  - Files: `src/`
  - Principles applied: §10.7 Clean Code (no orphaned scope surface)
  - Patch (deterministic): none — run `grep -rnE "scope_resolution|installer\.scope|brain_root|--global|--local|detect_scopes|scope_status|update_scopes|reconcile_scopes" src/` and confirm ZERO hits. Confirm pure-scope files ABSENT: `installer/scope.py`, `installer/scope_resolution.py`, `doctor/runtime/scope_status.py`.
  - Gate: grep returns nothing; the three pure-scope modules do not exist; `doctor/service.py` has no `scope_status` registration.

- [ ] T-4b — Regenerate hooks-manifest if hook bytes changed
  - Agent: build
  - Files: `.ai-engineering/state/hooks-manifest.json`
  - Principles applied: §13 hook integrity pin
  - Patch (deterministic): none — hooks should be untouched; if `git diff main -- .ai-engineering/scripts/hooks/` is non-empty, regenerate the manifest per the established procedure; else leave as-is.
  - Gate: hook integrity check passes; `git diff main -- .ai-engineering/scripts/hooks/` empty (expected).

---

### Phase 5 — Green gate (the verification contract)

- [ ] T-5a — Full test suite green
  - Agent: verify
  - Files: `tests/`
  - Principles applied: §10.5 TDD, §4 Verification Before Done
  - Patch (deterministic): none — `pytest` (full). Expect the 11 transplanted version tests + BASE suite all green; NO scope tests present.
  - Gate: full suite green; `pytest tests/unit/version tests/unit/test_cli_ui_notice.py tests/unit/test_cli_notice_exempt.py tests/unit/cli_commands/test_version_upgrade.py tests/unit/test_version_lifecycle.py tests/integration/test_version_checker.py` all pass.

- [ ] T-5b — Behavioral parity + notice purity smoke
  - Agent: verify
  - Files: (runtime)
  - Principles applied: §4 Verification Before Done
  - Patch (deterministic): none — confirm: `ai-eng install`/`update`/`config`/`doctor` carry no `--global`/`--local` and no scope announce (parity with main); `ai-eng version` shows the notice; `ai-eng version --json`/`gate`/`internal` are notice-free (stdout pure) and do not advance the throttle.
  - Gate: all acceptance checkboxes in spec-157 satisfiable; ready for `/ai-pr`.

---

## Post-build (operator, not a build task)

- Open the PR for `feat/version-update-notice-clean` via `/ai-pr`.
- Close PR #556 as superseded with a note: "Scope (global/local) abandoned per
  spec-157 + global-viability panel; version-update-notice re-landed clean in
  #NNN. Global briefs preserved under specs/drafts/." (irreversible/outward —
  operator confirms.)

## Risks

- `git checkout OLD -- <file>` brings a stray scope import → mitigated by the
  per-file grep gates in P2/P3 and the T-4a sweep.
- `core.py` / `updater/service.py` graft drifts from BASE → base ON main's file,
  graft only the version block; gate asserts `git diff main` is notice-only.
- Rider cherry-pick conflicts (CHANGELOG) → keep both entries.
- Briefs lost across the branch cut → T-0a preserves before T-0b.

## safe_next_command

`/ai-build`
