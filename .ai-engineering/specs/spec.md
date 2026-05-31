---
spec: spec-157
title: Version Update Notice — Clean Re-land (scope-free)
status: approved
effort: medium
summary: Re-land ONLY the version-update-notice + self-upgrade feature on a fresh branch cut from main, transplanting the proven scope-clean modules verbatim, rewriting the two scope-coupled files (updater/service.py, cli_commands/core.py) to single-scope, cherry-picking the two CI-green riders (.snyk CVE accept, decision-store tracking), and dropping ALL global/local scope machinery. PR #556 (spec-156) is abandoned.
---

# spec-157 — Version Update Notice: Clean Re-land

## Summary

PR #556 (`feat/version-update-notice`, spec-156) bundled two concerns into one
branch: (A) a cross-surface PyPI **update-available notice + `ai-eng version
upgrade`** self-upgrade, and (B) a **global/local scope** install/update system.
A strategy judge-panel (8 agents) and an atom census found global-as-install is
an architectural impedance mismatch: ~64% of ai-engineering's atoms (specs,
decision-store, audit chain, ownership, install-state, hooks-manifest) are
per-repo singletons that are incoherent shared, and spec-156 writes a global
brain the runtime resolvers (`paths.py`, `config.py` — untouched) can never read
back. Concern A is genuinely valuable and ships green (Sonar Quality Gate
passed, 92.7% coverage on new code). Concern B fights the architecture.

This spec re-lands ONLY Concern A, scope-free, on a fresh branch cut from
`main`. The design is already proven in code; this is a transplant + targeted
single-scope rewrite, not a new feature. Concern B is dropped entirely. PR #556
is closed as superseded; the two global briefs
(`global-install-work-plane-brief.md`, `global-hook-surface-resilience-brief.md`)
are preserved for a future, properly-scoped effort.

## Current State (boundary evidence)

Two adversarial `ai-explore` passes mapped the exact cut (`git diff main...HEAD`):

**Scope-clean — transplant verbatim (zero scope refs, confirmed):**
- `src/ai_engineering/version/cache.py` (net-new, 112), `compare.py` (25),
  `install_method.py` (93), `pypi.py` (77), `refresh.py` (60),
  `__init__.py` (+5 re-exports), `checker.py` (+6/-26, uses `compare.is_newer`).
- `src/ai_engineering/config/manifest.py` (+14, `VersionCheckConfig`).
- `src/ai_engineering/cli_factory.py` (+81/-4, notice wiring + `version_app`
  sub-typer) — fully scope-clean (`cli_factory.py`).
- `src/ai_engineering/cli_ui.py` (+135) version-notice block
  (`maybe_render_update_notice`, `_render_update_notice`,
  `_load_version_check_config`) is clean; it ALSO carries `announce_scope`
  (`cli_ui.py:416-433`) which is scope infra — strip it on re-land (dead
  otherwise).

**Scope-coupled — rewrite single-scope:**
- `src/ai_engineering/updater/service.py` — DROP `ScopeNotInstalledError`
  (`507-512`), `_SCOPE_INSTALL_HINT` (`515-518`), `_scope_is_installed`
  (`521-524`), `update_scopes` (`527-566`), `reconcile_scopes_with_skips`
  (`569-589`), `_scope_root` (`444-446`), `_update_dests` (`766-790`),
  `_orphan_path` (`915-928`), `_merge_update_results`, `skipped_scopes` field
  (`122-124,171`); REVERT `scope` param on `update` (`449-504`),
  `_evaluate_project_files` (`793-839`), `_detect_orphan_files` (`842-887`),
  `_provider_orphan_changes` (`900-912`), `_provider_file_orphans` (`931-946`),
  `_provider_tree_orphans` (`949-965`) to the `main` shape.
- `src/ai_engineering/cli_commands/core.py` — KEEP `_cached_latest`
  (`1697-1706`), `version_cmd` (`1709-1738`), `_MANUAL_UPGRADE_COMMANDS`
  (`1741-1746`), `_emit_manual_upgrade_guidance` (`1749-1773`),
  `version_upgrade_cmd` (`1776-1846`); DROP `scope_global`/`scope_local` params
  on `install_cmd` (`151-164`) + `update_cmd` (`1135-1142`),
  `_explicit_install_scope` (`568-581`), `_resolve_update_scope` (`1243-1254`),
  `_merge_update_results` (`1301-1314`), `announce_scope` import (`31`),
  `brain_root` routing (`263-268`); REVERT `_is_reinstall` (`330-345`),
  `_resolve_install_configuration` (`384-414`),
  `_resolve_first_install_configuration` (`451-480`), `_run_update_with_spinner`
  (`1257-1298`) to the `main` shape.
- `src/ai_engineering/cli_commands/config.py` — DROP scope-announce block
  (`57-62`).

**Tests — transplant verbatim (all scope-free, confirmed):**
`tests/unit/version/{__init__,test_cache,test_compare,test_install_method,test_pypi,test_refresh}.py`,
`tests/unit/test_cli_ui_notice.py`, `tests/unit/test_cli_notice_exempt.py`,
`tests/unit/test_version_lifecycle.py` (+62, `TestUpgradeVerbAndNotice`),
`tests/unit/cli_commands/test_version_upgrade.py`,
`tests/integration/test_version_checker.py` (+3/-21).

**Riders — cherry-pick (scope-independent, CI-green-required):**
- `5b9b4272` `.snyk` risk-accept CVE-2026-8643 (pip). Load-bearing: the Snyk
  gate reds CI without it.
- `d6db3dc7` decision-store tracking: `decision-store.json`, `.gitignore`,
  `CHANGELOG.md`, `docs/persistence-doctrine.md`,
  `src/ai_engineering/installer/gitignore.py`, `test_project_gitignore.py`.

**Leave behind — pure scope (must NOT come to the clean branch):**
`installer/scope.py`, `installer/scope_resolution.py`,
`doctor/runtime/scope_status.py`, `installer/wizard.py` scope additions,
installer phases scope routing (governance/hooks/ide_config/state/scripts),
`doctor/service.py` scope_status registration, and all scope tests
(`test_scope_*`, `test_install_scope_flow`, `test_cli_scope_announce`,
`test_update_dual_scope`, `test_install_guidance`, `test_global_roundtrip`,
`test_install_global`).

**Import-edge danger (the one real trap):** `cli_commands/core.py` is the only
KEEP-candidate that directly imports drop modules; its four version functions
import only `version.install_method` and are clean, but live beside
scope-contaminated code — surgically extract, never transplant verbatim. No
version module back-depends on scope; `scope_status.py` imports version modules
(reverse edge) and is left behind, so the edge vanishes.

## Goals

- A fresh branch `feat/version-update-notice-clean` cut from `main` carries the
  version-update-notice + `ai-eng version upgrade` feature with ZERO scope code.
- `install`/`update`/`config`/`doctor` behave exactly as `main` today (no
  `--global`/`--local`, no scope announce, no dual-scope update).
- The PyPI update-available notice renders only for interactive human commands
  (stdout-pure, automation/`--json`/hook hot paths exempt, throttle honored) —
  the proven behavior from #556.
- `ai-eng version` and `ai-eng version upgrade` work, wrapped in the CLI error
  boundary, with JSON envelopes — the proven behavior from #556.
- The two CI-green riders (`.snyk`, decision-store tracking) are present so the
  branch is green.
- The two global briefs survive onto the new branch (or main) — not lost with
  the dying PR.
- Full test suite green; `hooks-manifest.json` regenerated if any hook bytes
  changed (they should not).

## Non-Goals

- ANY global/local scope feature (dropped wholesale — that is the point).
- Fixing the runtime resolver `$HOME` ceiling or hooks exit-127 (tracked in the
  two preserved briefs; separate future specs).
- Re-deriving the version-notice design (it is proven in #556; this is a
  transplant, not a redesign).
- Migrating PR #556 commit history (squash-merge makes it moot; #556 is closed).
- Touching `paths.py` / `config.py` runtime resolution.

## Decisions

- **D-157-01 — Fresh branch from main, not surgical revert.** Cut
  `feat/version-update-notice-clean` from `main`. Rationale: the six installer
  phases carry interwoven scope-routing (+14..+166 each); a fresh branch leaves
  them prístine by construction (scope never arrives) — zero residue — whereas
  reverting them in-place risks leftover scope fragments. Squash-merge yields a
  single clean main commit either way, so history is not the deciding factor.

- **D-157-02 — Transplant proven modules verbatim; rewrite only the two coupled
  files.** The 13 scope-clean source files + 11 test files are copied as-is from
  the #556 branch (they carry zero scope refs). Only `updater/service.py` and
  `cli_commands/core.py` are rewritten to the single-scope (main) shape, plus the
  3-line scope-announce drop in `config.py`. Rationale: §10.4 DRY / §10.1 KISS —
  do not rewrite tested, green code; minimize the rewrite surface to the genuine
  coupling.

- **D-157-03 — Strip `announce_scope` from `cli_ui.py` on transplant.** The
  notice block is clean but `announce_scope` (`cli_ui.py:416-433`) is scope infra
  that happened to land there. Remove it during the copy so no dead scope rider
  ships. Rationale: §10.7 Clean Code — no dead code; §13.3 no orphaned scope
  surface.

- **D-157-04 — Cherry-pick the two riders; they are load-bearing for green CI.**
  `.snyk` (CVE-2026-8643 accept) and the decision-store tracking change are
  scope-independent and cherry-pick clean onto main. The `.snyk` accept is NOT
  optional — the Snyk gate reds CI without it. Rationale: Hard Rule 1 (secrets/
  CVE gate) — the branch must pass the same gate `main` does.

- **D-157-05 — Preserve the two global briefs.** Move
  `global-install-work-plane-brief.md` and
  `global-hook-surface-resilience-brief.md` onto the new branch (they are
  untracked working-tree files). Rationale: they are the validated foundation for
  a future correct global-defaults effort; they must not die with PR #556.

- **D-157-06 — Close PR #556 as superseded.** After the clean branch opens its
  PR, close #556 with a note linking the successor and the abandoned-scope
  decision. It has zero human reviews, so nothing is lost. Rationale: §10.2
  YAGNI — abandon the over-built scope concern rather than carry it.

## Acceptance

- [ ] `feat/version-update-notice-clean` exists, cut from `main`.
- [ ] `grep -rE "scope_resolution|brain_root|--global|--local|detect_scopes|scope_status|update_scopes" src/` returns ZERO hits on the new branch.
- [ ] None of the pure-scope files exist on the new branch
      (`installer/scope.py`, `scope_resolution.py`, `doctor/runtime/scope_status.py`, scope tests).
- [ ] `ai-eng install`, `update`, `config`, `doctor` have no scope flags and
      behave as `main` (no scope announce).
- [ ] `ai-eng version` shows the update notice; `ai-eng version upgrade` works
      and emits a JSON envelope under `--json`.
- [ ] Update notice is stdout-pure: absent on `--json`, `internal`, `gate`/hook
      paths; throttle not burned by automation.
- [ ] `.snyk` CVE-2026-8643 accept present; Snyk gate green.
- [ ] decision-store tracking change present (`.gitignore` no longer ignores it).
- [ ] Both global briefs present under `.ai-engineering/specs/drafts/`.
- [ ] Full test suite green; `hooks-manifest.json` consistent.
- [ ] PR #556 closed as superseded with a linking note.
