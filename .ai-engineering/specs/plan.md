---
execution_route:
  version: 1
  spec: spec-156
  executor: autopilot
  automation: hitl
  concern_count: 6
  estimated_files: 17
  reason: >-
    Six concerns (scope-detection model, installer global correctness, updater
    dual-scope re-rooting, update-notice render/throttle, version subsystem,
    doctor polish) across ~17 source + test files, well past the >=10-file /
    >=3-concern autopilot threshold (CLAUDE.md §11). Two blockers corrupt state
    under --global; wave decomposition with a foundational shared-resolver wave
    plus a final quality loop + HITL review at PR is warranted.
  safe_next_command: "/ai-autopilot"
status: draft
pipeline: full
spec: spec-156
title: Scope-Aware CLI — Auto-Detect Global/Local + Dual-Scope Hardening
---

# Plan — spec-156: Scope-Aware CLI + Dual-Scope Hardening

## Design

`--skip-design` (logged): the only user-visible surfaces are (a) the install
scope wizard question — already designed and implemented in the prior `/ai-design`
pass (`installer/wizard.py` `_ask_scope`, brand-teal style, audit-confirmed
correct), and (b) the per-command scope-announce line (D-156-03), which is a
single line of copy, not a design problem. No new design artifact required.

Announce-line copy (fixed here so build is mechanical):
- only-global: `◈ ai-engineering · acting on global install (~/)`
- only-local:  `◈ ai-engineering · acting on local install (./)`
- both:        `◈ ai-engineering · acting on local install (./) · global also present — use --global to target it`
Rendered via `cli_ui` on stderr, suppressed under `is_json_mode()`.

## Architecture

**Pattern: single Scope Resolver chokepoint (hexagonal port) + per-command scope
middleware.** Today scope routing is duplicated and partial: `ide_config._resolve_dest`
routes through `installer.scope.dest`, but the updater (`updater/service.py:783,802`),
the post-pipeline manifest writers and operational/scripts phases
(`installer/service.py:310-316`, `scripts.py`) bypass it and hardcode the repo
`target`. The root-cause fix (D-156-04) is to make ONE resolver the only place
that maps `(surface, scope, target, rel) -> abs path` and `brain_root(scope, target)`,
and have installer + updater + doctor consume it. Scope **detection**
(`only-global / only-local / both / neither`) becomes a small resolver consumed
by every command's entry as middleware (D-156-01..03).

- Anchors: `installer/scope.py` (extend), new `installer/scope_resolution.py`
  (detect + resolve + announce), `installer/phases/ide_config.py:34-58,105-122`
  (reuse), `updater/service.py:764-808` (consume), `cli_commands/core.py`
  (middleware + announce), `doctor/runtime/scope_status.py`.
- Principles: §10.8 Hexagonal (one port for scope→path), §10.4 DRY (kill the
  duplicated routing), §10.3 SOLID (single responsibility per resolver).

## Wave DAG

```
Wave 1 (scope resolver + detection + InstallState.scope)  ── foundational
   ├── Wave 2 (installer global correctness)
   ├── Wave 3 (updater dual-scope re-root)
   └── Wave 6 (doctor dedupe + command announce wiring)
Wave 4 (notice render/throttle + json-mode test isolation)  ── independent (parallel)
Wave 5 (version subsystem: PEP440, live __version__, version-cmd, dead code)  ── independent (parallel)
Wave 7 (integration round-trips + docs)  ── depends Waves 1-3
```

Concurrency: Waves 1/4/5 may start together; 2/3/6 gate on 1; 7 gates on 1-3.

---

## Wave 1 — Scope resolver chokepoint + detection model (foundational)

Concerns D-156-01/02/03/04/07. Blocks Waves 2,3,6.

- [ ] T-1.1 — RED: scope-detection truth table
  - Agent: build
  - Files: `tests/unit/installer/test_scope_resolution.py` (new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — author cases: only-global→`global`,
    only-local→`local`, both→`local` (announce flag set), neither→`None`;
    monkeypatch `Path.home()` + repo marker presence.
  - Gate: `pytest tests/unit/installer/test_scope_resolution.py` fails (no module)

- [ ] T-1.2 — GREEN: scope detection + resolution
  - Agent: build
  - Files: `src/ai_engineering/installer/scope_resolution.py` (new)
  - Principles applied: §10.8 Hexagonal, §10.3 SOLID
  - Patch (deterministic): omit — implement `detect_scopes(target) -> set[str]`
    (marker presence at `target` + `Path.home()`, reuse `scope_status._marker`
    semantics), `resolve_scope(target, explicit) -> ResolvedScope(scope, both,
    announce_line)` honoring D-156-01 (local-wins) + D-156-02 (explicit
    override). Pure, no IO beyond `is_file`.
  - Gate: T-1.1 green

- [ ] T-1.3 — RED: `installer.scope.dest` reused for a single brain-root helper
  - Agent: build
  - Files: `tests/unit/installer/test_scope_resolver.py` (extend)
  - Principles applied: §10.5 TDD, §10.4 DRY
  - Patch (deterministic): omit — assert a `brain_root(scope, target)` helper
    returns `Path.home()` for global, `target` for local (centralizes the
    `Path.home() if scope=='global' else target` idiom duplicated in state.py,
    hooks.py, service.py).
  - Gate: red

- [ ] T-1.4 — GREEN: add `brain_root` to `installer/scope.py`; refactor the 3
        existing call sites to use it
  - Agent: build
  - Files: `src/ai_engineering/installer/scope.py`,
    `src/ai_engineering/installer/phases/state.py:42-49`,
    `src/ai_engineering/installer/phases/hooks.py:94`
  - Principles applied: §10.4 DRY
  - Patch (deterministic): omit — extract helper; replace the inline ternaries
    (behavior-preserving).
  - Gate: T-1.3 green; existing installer suite stays green

- [ ] T-1.5 — RED: `InstallState.scope` persisted + scope-aware `_is_reinstall`
  - Agent: build
  - Files: `tests/unit/installer/test_install_reinstall.py` (extend),
    `tests/unit/cli_commands/test_install_scope_flow.py` (extend)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — assert a global install records `scope:
    "global"` on the home `install-state.json`, and `_is_reinstall` detects a
    prior global install when `--global` is resolved (checks `Path.home()`
    marker).
  - Gate: red

- [ ] T-1.6 — GREEN: add `scope` field to `InstallState`; stamp it in StatePhase;
        make `_is_reinstall` scope-aware
  - Agent: build
  - Files: `src/ai_engineering/state/state_models.py` (InstallState ~1127),
    `src/ai_engineering/installer/phases/state.py:52-66`,
    `src/ai_engineering/cli_commands/core.py:317-325,195`
  - Principles applied: §10.3 SOLID
  - Patch (deterministic): omit (pydantic field add + stamp; `_is_reinstall`
    gains an `explicit_scope` param threaded from `install_cmd`).
  - Gate: T-1.5 green

- [ ] T-1.7 — RED: scope-announce line per state, suppressed in JSON
  - Agent: build
  - Files: `tests/unit/test_cli_scope_announce.py` (new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — assert exact copy (see Design) on stderr for
    only-global / only-local / both; assert empty under `--json`.
  - Gate: red

- [ ] T-1.8 — GREEN: `announce_scope()` in `cli_ui`; call from the scope-resolving
        command entries
  - Agent: build
  - Files: `src/ai_engineering/cli_ui.py`, `src/ai_engineering/cli_commands/core.py`
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): omit — render `ResolvedScope.announce_line` via the
    branded console; gate on `is_json_mode()`.
  - Gate: T-1.7 green

- [ ] T-1.9 — VERIFY: Wave 1 gate
  - Agent: verify
  - Files: (read-only)
  - Principles applied: §10.5 TDD
  - Gate: `pytest tests/unit/installer tests/unit/cli_commands -q` green; `ty
    check src/ai_engineering/installer src/ai_engineering/state`; `ruff check`

---

## Wave 2 — Installer global correctness (depends Wave 1)

Concerns D-156-06/08/15/17(hooks). Fixes blocker 2 + highs 3,7 + guidance.

- [ ] T-2.1 — RED: global install persists operator choices to `~/.ai-engineering/manifest.yml`
  - Agent: build
  - Files: `tests/integration/installer/test_install_global.py` (extend)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — `install_with_pipeline(scope='global', stacks=['rust'],
    surfaces=['codex'])` writes those into the HOME manifest, not repo, and the
    repo gets NO `.ai-engineering/` marker or scripts.
  - Gate: red

- [ ] T-2.2 — GREEN: scope-route post-pipeline writers + operational/scripts phases
  - Agent: build
  - Files: `src/ai_engineering/installer/service.py:309-316`,
    `src/ai_engineering/installer/phases/scripts.py:~103,158`
  - Principles applied: §10.4 DRY, §10.8 Hexagonal
  - Patch (deterministic): omit — compute `brain_root = scope.brain_root(scope,
    target)`; pass to `initialize_manifest_project_name`, `_write_providers`,
    `_write_surfaces`, `_run_operational_phases`, and ScriptsPhase dest.
  - Gate: T-2.1 green; `test_install_global` + `test_cli_command_modules` green

- [ ] T-2.3 — RED: multi-surface global `AGENTS.md` fan-out + per-surface verify
  - Agent: build
  - Files: `tests/integration/installer/test_install_global.py` (extend)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — `--global` with `[codex, antigravity]` yields
    BOTH `~/.codex/AGENTS.md` and `~/.gemini/AGENTS.md`; `verify()` fails if
    either missing.
  - Gate: red

- [ ] T-2.4 — GREEN: fan shared instruction files to every owning surface home
  - Agent: build
  - Files: `src/ai_engineering/installer/phases/ide_config.py:34-58,105-152,206-215`
  - Principles applied: §10.3 SOLID
  - Patch (deterministic): omit — stop deduping shared `dest_rel` to one surface
    under global; iterate per owning surface so each home gets the file; extend
    `verify()` to assert per-surface presence.
  - Gate: T-2.3 green

- [ ] T-2.5 — RED+GREEN: dry-run git-hooks plan guarded for global (D-156-17)
  - Agent: build
  - Files: `tests/unit/installer/` (extend), `src/ai_engineering/installer/phases/hooks.py:68`
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic):
    ```diff
    @@ hooks.py plan()
    -        actions.append(PlannedAction("create", "", ".git/hooks", "install git gate hooks"))
    +        if context.scope != "global":
    +            actions.append(PlannedAction("create", "", ".git/hooks", "install git gate hooks"))
    ```
  - Gate: `install --global --dry-run` plan omits `.git/hooks`

- [ ] T-2.6 — RED: cursor/copilot global guidance is surfaced + hooks-manifest scoped
  - Agent: build
  - Files: `tests/unit/installer/` + `tests/unit/cli_commands/` (extend)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — `install --global --surface cursor` prints the
    `GuidanceSentinel` steps (and includes them in the JSON envelope); the global
    hooks-manifest regenerates under `~/.ai-engineering/`.
  - Gate: red

- [ ] T-2.7 — GREEN: aggregate phase guidance into install output; scope `_finalize_hooks_manifest`
  - Agent: build
  - Files: `src/ai_engineering/cli_commands/core.py:256,_render_install_success`,
    `src/ai_engineering/installer/service.py` (expose `phase.guidance`)
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): omit — thread `IdeConfigPhase.guidance` to the success
    renderer + JSON envelope; pass `brain_root` to `_finalize_hooks_manifest`.
  - Gate: T-2.6 green

- [ ] T-2.8 — VERIFY: Wave 2 gate
  - Agent: verify
  - Gate: `pytest tests/integration/installer tests/unit/installer -q` green; ruff + ty

---

## Wave 3 — Updater dual-scope re-rooting (depends Wave 1) — BLOCKER 1

Concern D-156-05.

- [ ] T-3.1 — RED: `update --global` targets `~/.claude/CLAUDE.md`, never `~/CLAUDE.md`
  - Agent: build
  - Files: `tests/unit/updater/test_update_dual_scope.py` (extend / fix the
    masking test at :74-83)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — assert planned dests for a global update are
    `~/.claude/CLAUDE.md` + `~/.codex/AGENTS.md`; assert NO `~/CLAUDE.md` and no
    orphan flag on the correctly-placed files.
  - Gate: red (currently plans `~/CLAUDE.md`)

- [ ] T-3.2 — GREEN: route updater IDE-surface dests through the shared resolver
  - Agent: build
  - Files: `src/ai_engineering/updater/service.py:764-808` (`_evaluate_project_files`),
    `:811+` (`_detect_orphan_files`)
  - Principles applied: §10.4 DRY, §10.8 Hexagonal
  - Patch (deterministic): omit — thread `scope` into `_evaluate_project_files`
    / `_detect_orphan_files`; replace `dest = target/dest_relative` (and the tree
    form) with the shared `scope.dest(owning_surface, scope, target, rel)` used
    by `ide_config`; keep the brain on `brain_root`.
  - Gate: T-3.1 green

- [ ] T-3.3 — VERIFY: Wave 3 gate
  - Agent: verify
  - Gate: `pytest tests/unit/updater -q` green; ruff + ty

---

## Wave 4 — Update notice render/throttle + json-mode test isolation (independent)

Concerns D-156-09/10/13. Highs 5,6 + medium.

- [ ] T-4.1 — RED: notice never leaks on `--json` (any entry), `internal`, `gate`; never marks shown
  - Agent: build
  - Files: `tests/unit/test_cli_ui_notice.py` (extend), `tests/unit/cli_commands/` (new automation cases)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — assert stdout=='' AND no notice on stderr for
    `check --json`, `gate`, `internal python`; assert `cache.mark_shown` NOT
    called on those paths; assert notice DOES show on human `doctor`.
  - Gate: red

- [ ] T-4.2 — GREEN: gate notice on resolved `is_json_mode()` + `_NOTICE_EXEMPT`; no mark_shown on automation
  - Agent: build
  - Files: `src/ai_engineering/cli_factory.py:192-219`, `src/ai_engineering/cli_ui.py:429-498`
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): omit — add `_NOTICE_EXEMPT >= {version, internal, gate}`
    plus the hook entrypoints; render after mode is resolved (or guard on
    `is_json_mode()` inside `maybe_render_update_notice`).
  - Gate: T-4.1 green

- [ ] T-4.3 — RED+GREEN: json-mode test isolation autouse fixture
  - Agent: build
  - Files: `tests/conftest.py`
  - Principles applied: §10.5 TDD
  - Patch (deterministic):
    ```diff
    @@ tests/conftest.py
    +import pytest
    +from ai_engineering.cli_output import set_json_mode
    +
    +@pytest.fixture(autouse=True)
    +def _reset_json_mode():
    +    yield
    +    set_json_mode(False)
    ```
  - Gate: the 4 notice tests pass regardless of collection order
    (`pytest tests/unit/test_cli_ui_notice.py tests/unit/test_version_lifecycle.py -p no:randomly` AND reversed)

- [ ] T-4.4 — RED+GREEN: refresh spawn throttle on fetch failure
  - Agent: build
  - Files: `tests/unit/version/test_cache.py` + `test_refresh.py` (extend),
    `src/ai_engineering/version/cache.py:70`, `src/ai_engineering/version/refresh.py:26-33`
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — on `fetch_latest()` failure, stamp
    `attempted_at` (or advance `checked_at`) so `is_stale()` suppresses respawn
    within `ttl_hours`; assert spawn called once across two stale invocations
    when offline.
  - Gate: red→green

- [ ] T-4.5 — VERIFY: Wave 4 gate
  - Agent: verify
  - Gate: full `pytest tests/unit/test_cli_ui_notice.py tests/unit/version tests/unit/test_version_lifecycle.py -q` green; stdout-purity assertion holds

---

## Wave 5 — Version subsystem (independent)

Concerns D-156-11/12/14/16.

- [ ] T-5.1 — RED: canonical PEP 440 comparator (rc/dev/post/local/ragged)
  - Agent: build
  - Files: `tests/unit/version/test_compare.py` (new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — `0.9.0rc1>0.8.4`→True, `0.9.0>0.8.4.dev1`→True,
    `0.9`vs`0.9.0` arity, InvalidVersion→False.
  - Gate: red

- [ ] T-5.2 — GREEN: one `version/compare.py` using `packaging.version`; replace 3 hand-rolled parsers
  - Agent: build
  - Files: `src/ai_engineering/version/compare.py` (new),
    `src/ai_engineering/cli_ui.py:400-410`, `src/ai_engineering/version/checker.py:48-60`,
    `src/ai_engineering/doctor/runtime/scope_status.py:45`,
    `src/ai_engineering/templates/.ai-engineering/scripts/session_bootstrap.py:711-721` (template; sync after)
  - Principles applied: §10.4 DRY
  - Patch (deterministic): omit — `is_newer(latest, current) -> bool`; mirror into
    the session_bootstrap template, then `ai-eng dev sync`.
  - Gate: T-5.1 green; `pytest tests/unit/scripts/test_session_bootstrap.py`

- [ ] T-5.3 — RED+GREEN: ai-start sources installed version from live `__version__`
  - Agent: build
  - Files: `tests/unit/scripts/test_session_bootstrap.py` (extend),
    `.../templates/.ai-engineering/scripts/session_bootstrap.py:~1080` (+ sync)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — read installed version from
    `ai_engineering.__version__` (or `install-state.json`), not manifest
    `framework_version`; sync mirror.
  - Gate: red→green

- [ ] T-5.4 — RED: `version`/`version upgrade` error-boundary + JSON envelope + `--json`
  - Agent: build
  - Files: `tests/unit/cli_commands/test_version_upgrade.py` (extend)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — `version upgrade --json` exits 0 with a success
    envelope (mock subprocess rc 0, stdout captured); a raised OSError yields a
    clean JSON error envelope, not a traceback.
  - Gate: red

- [ ] T-5.5 — GREEN: wrap registrations in `_safe`; emit envelope; capture subprocess stdout in json
  - Agent: build
  - Files: `src/ai_engineering/cli_factory.py:375-376`,
    `src/ai_engineering/cli_commands/core.py:1689-1751`
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): omit — `_safe(core.version_cmd)` / `_safe(core.version_upgrade_cmd)`;
    add `--json` option passthrough; in json mode `subprocess.run(..., capture_output=True)`
    + `emit_success` on rc 0.
  - Gate: T-5.4 green

- [ ] T-5.6 — GREEN: delete dead `internal version-refresh` command; fix docstring (D-156-16)
  - Agent: build
  - Files: `src/ai_engineering/cli_commands/internal.py:28-36`,
    `src/ai_engineering/cli_factory.py:586`, `src/ai_engineering/version/refresh.py:12-14` (docstring),
    `tests/integration/test_cli_command_modules.py` (adjust if it asserts the verb)
  - Principles applied: §10.4 DRY (single spawn SoT = `-m`)
  - Patch (deterministic): omit — remove the hidden command + its registration;
    correct the refresh.py docstring to name only the `-m` entrypoint.
  - Gate: `ai-eng internal --help` no longer lists `version-refresh`; spawn path unaffected

- [ ] T-5.7 — VERIFY: Wave 5 gate
  - Agent: verify
  - Gate: `pytest tests/unit/version tests/unit/cli_commands tests/integration/test_cli_command_modules.py -q` green; ruff + ty

---

## Wave 6 — Doctor scope dedupe + command-wide announce wiring (depends Wave 1)

Concern D-156-17(doctor) + D-156-03 fan-out to remaining commands.

- [ ] T-6.1 — RED+GREEN: doctor scope dedupe when repo==home
  - Agent: build
  - Files: `tests/unit/doctor/test_scope_status.py` (extend),
    `src/ai_engineering/doctor/runtime/scope_status.py:26-33`
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — when `target.resolve() == Path.home().resolve()`
    the repo marker and home marker are the same file, so collapse to a single
    `global` scope instead of reporting `local, global`; mirror the dedupe in
    `updater.reconcile_scopes_with_skips` (:582-587) so a no-flag update does not
    process the identical tree twice.
  - Gate: repo==home reports one scope, not `local, global`; no double update

- [ ] T-6.2 — RED+GREEN: `update`/`config` honor the resolved scope + announce
  - Agent: build
  - Files: `tests/unit/cli_commands/` (extend),
    `src/ai_engineering/cli_commands/core.py` (update_cmd path ~1067-1226),
    `src/ai_engineering/cli_commands/config.py`
  - Principles applied: §10.3 SOLID
  - Patch (deterministic): omit — `update`/`config` call `resolve_scope` (Wave 1)
    + announce; `--global`/`--local` override; no-flag both→local-wins.
  - Gate: red→green; no-flag dual reconcile still local-wins

- [ ] T-6.3 — VERIFY: Wave 6 gate
  - Agent: verify
  - Gate: `pytest tests/unit/doctor tests/unit/cli_commands -q` green; ruff + ty

---

## Wave 7 — Integration round-trips + docs (depends Waves 1-3)

- [ ] T-7.1 — RED: real-pipeline global round-trip (install → update → doctor)
  - Agent: build
  - Files: `tests/integration/installer/test_global_roundtrip.py` (new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): omit — drive `install_with_pipeline(scope='global')`
    (NOT hand-rolled phase calls), then `update_scopes(...)` then
    `scope_status.check(...)`: assert no `~/CLAUDE.md`/`~/AGENTS.md` orphans, no
    repo marker, manifest choices preserved, `update` plans zero spurious
    changes, doctor reports `global` only.
  - Gate: red→green (this is the test that would have caught blockers 1-3)

- [ ] T-7.2 — GREEN: docs — CHANGELOG + README scope-model section
  - Agent: build
  - Files: `CHANGELOG.md`, `README.md`
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): omit — document the detection-first model + local-wins
    + flags-as-override (hard-rule #3 breakage note for the old both-scope
    behavior); keep README under the 170-line cap (run `pytest tests/docs`).
  - Gate: `pytest tests/docs -q` green

- [ ] T-7.3 — VERIFY: full-suite + governance gate
  - Agent: verify
  - Files: (read-only)
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Gate: `pytest -q` full green; `ruff check`; `ruff format --check`; `ty check
    src`; `ai-eng spec verify --sections`; mirror parity (`ai-eng dev sync`
    clean); decision-store backfill for D-156-* present

- [ ] T-7.4 — GUARD: governance + ownership advisory
  - Agent: guard
  - Files: (read-only)
  - Principles applied: §10.6 SDD
  - Gate: `/ai-governance` advisory clean; no suppression directives introduced
    (hard-rule #2); risk-accept any residual finding via `ai-eng risk accept`

## Gate summary

- Every GREEN task pairs with a preceding RED (§10.5).
- Per-wave VERIFY tasks (read-only) gate progression; Waves 2/3/6 gate on Wave 1.
- Final Wave 7 runs the full suite + governance before PR.
- Bounded fail-loud quality loop applies at the autopilot Phase-5 round
  (hard-rule #5): one finding-scoped remediation pass, then terminal reassessment.

## Open decisions carried from spec (confirm at build or PR)

D-156-08 (per-surface fan-out), D-156-12 (live `__version__`), D-156-15
(surface guidance), D-156-16 (delete `internal version-refresh`) — defaults
encoded above; reverse in-wave if product intent differs.
