---
execution_route:
  version: 1
  spec: spec-151
  executor: autopilot
  automation: autonomous-no-hitl
  concern_count: 6
  estimated_files: 90
  reason: >
    Large cross-surface refactor: remove the retired gemini-cli surface and
    generated GEMINI/.gemini assets, promote antigravity to the sole Google
    surface, rename generated Antigravity layout from .agent to .agents, add
    agy CLI diagnostics, update validators/docs/tests, and regenerate mirrors.
    This crosses registry, installer, updater, mirror generation, docs, and CI
    tests, so /ai-autopilot is the executor.
  safe_next_command: "/ai-autopilot"
spec: spec-151
title: "Plan — Antigravity-only Google surface after Gemini CLI retirement"
status: approved
pipeline: full
total: 18
completed: 17
---

# Plan — Antigravity-only Google surface after Gemini CLI retirement

> Contract for autonomous execution. Operator already approved no-HITL execution in
> this thread. Spec: `.ai-engineering/specs/spec.md` (D-151-01..07, AC1..7).

## Architecture

- **Pattern**: Ports and Adapters / Hexagonal. `src/ai_engineering/domain/surface.py`
  remains the inner domain registry; installer, updater, mirror sync, validation,
  and doctor/diagnostics are adapters that consume the registry contract.
- **Key invariant**: one Google surface id: `antigravity`. No `gemini-cli` alias,
  no `antigravity-cli` split, no dual-write `GEMINI.md` + `AGENTS.md` root context.
- **Generated mirror invariant**: `.agents/` and install templates are derived from
  canonical `.claude/` sources via `scripts/sync_mirrors/core.py`; do not hand-copy
  generated mirror content except through deterministic generator output.
- **Audit honesty invariant**: Antigravity can be first-class for workspace layout
  and CLI diagnostics while `audit_capability` remains `partial` until hook payload
  fixtures are public and tested.

## Design

No UI design artifact required. This is a CLI/configuration governance migration.
The user-facing design is the install/status/doctor wording: Google support is now
"Antigravity" and CLI availability is reported as `agy` runtime diagnostics.

## Phase 1 — RED tests for the new surface contract

Gate: `pytest tests/unit/domain/test_surface.py tests/unit/config/test_manifest_surface_schema.py tests/integration/test_install_matrix.py -q` fails before implementation, then passes after Phase 2.

- [x] T-1.1 — RED: update domain surface tests for six canonical surfaces plus Antigravity first-class posture
  - Agent: build
  - Files: `tests/unit/domain/test_surface.py:14`
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): replace seven-id expectation with six ids excluding `gemini-cli`; assert `get_surface("gemini-cli")` raises; assert Antigravity uses `AGENTS.md`, `.agents/`, `hook_engine != "none"` only if fixture-backed else `audit_capability == "partial"`.
  - Gate: test fails against current registry.

- [x] T-1.2 — RED: update manifest schema tests to reject `gemini-cli` and accept `antigravity`
  - Agent: build
  - Files: `tests/unit/config/test_manifest_surface_schema.py:30`
  - Principles applied: §10.5 TDD
  - Patch (deterministic): remove `gemini-cli` examples; add invalid-manifest assertion for `gemini-cli` if loader exposes validation, or assert unknown surface fails in the consuming resolver.
  - Gate: schema/config tests fail before implementation.

- [x] T-1.3 — RED: update install matrix for Antigravity-only output
  - Agent: build
  - Files: `tests/integration/test_install_matrix.py:11`
  - Principles applied: §10.5 TDD
  - Patch (deterministic): remove gemini single/multi-provider cases; add Antigravity GitHub/Azure cases expecting `AGENTS.md` + `.agents`; assert `GEMINI.md`, `.gemini`, `.agent` are absent for Antigravity installs.
  - Gate: install matrix fails before implementation.

## Phase 2 — GREEN registry, manifest, installer, autodetect, and ownership

Gate: Phase 1 tests green plus `pytest tests/unit/config tests/unit/domain tests/integration/test_install_matrix.py -q`.

- [x] T-2.1 — Remove `gemini-cli` and promote Antigravity in the surface registry
  - Agent: build
  - Files: `src/ai_engineering/domain/surface.py:1`
  - Principles applied: §10.1 KISS, §10.8 Hexagonal Architecture
  - Patch (deterministic): delete `gemini-cli` registry entry; change Antigravity to `instruction_files=("AGENTS.md",)`, `tree_dir=".agents/"`, `hook_engine="native"` only if fixture-backed else a conservative non-full posture, `audit_capability="partial"`, `autodetect_marker=(".agents/",)`; update docstring count.
  - Gate: T-1.1 green.

- [x] T-2.2 — Update dogfood manifest and CLI help text
  - Agent: build
  - Files: `.ai-engineering/manifest.yml:28`, `src/ai_engineering/cli_commands/core.py:105`
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Patch (deterministic): remove `gemini-cli` from enabled/default lists and prose; keep `antigravity`.
  - Gate: manifest/config tests green.

- [x] T-2.3 — Update installer template maps
  - Agent: build
  - Files: `src/ai_engineering/installer/templates.py:35`
  - Principles applied: §10.1 KISS, §10.8 Hexagonal Architecture
  - Patch (deterministic): remove `_SURFACE_FILE_MAPS["gemini-cli"]`; change Antigravity file map to `AGENTS.md` only; remove `.gemini` tree map; change Antigravity tree map from `.agent` to `.agents`.
  - Gate: install matrix green.

- [x] T-2.4 — Update autodetect and ownership/write-scope/control-plane defaults
  - Agent: build
  - Files: `src/ai_engineering/installer/autodetect.py:222`, `src/ai_engineering/config/framework_defaults.py:71`, `src/ai_engineering/state/capabilities.py:293`, `src/ai_engineering/state/control_plane.py:25`, `src/ai_engineering/updater/service.py:1247`
  - Principles applied: §10.3 SOLID, §10.7 Clean Code
  - Patch (deterministic): remove `GEMINI.md`/`.gemini` detection for current surfaces; detect `.agents/`; classify `.agents/` as mirror/framework-owned; remove `.agent/**` as current generated ownership.
  - Gate: targeted unit tests plus grep for stale current-support references.

## Phase 3 — CLI diagnostics for `agy`

Gate: new `agy` probe unit tests green.

- [x] T-3.1 — RED: add deterministic tests for `agy` runtime probe
  - Agent: build
  - Files: `tests/unit/installer/test_antigravity_cli_probe.py` or nearest existing doctor/status test
  - Principles applied: §10.5 TDD
  - Patch (deterministic): test missing binary returns unavailable fail-soft; fake `agy --version` returns available/version; Windows `agy.exe` lookup is considered.
  - Gate: tests fail before probe exists.

- [x] T-3.2 — GREEN: implement `agy` probe behind a small adapter
  - Agent: build
  - Files: `src/ai_engineering/installer/antigravity.py` or nearest diagnostics module, `src/ai_engineering/cli_commands/core.py`/doctor integration if needed
  - Principles applied: §10.8 Hexagonal Architecture, §10.2 YAGNI
  - Patch (deterministic): use `shutil.which("agy")`/`agy.exe` and bounded `subprocess.run([binary, "--version"], timeout=...)`; return a dataclass/dict with available/version/reason; no auth or network calls.
  - Gate: T-3.1 green.

## Phase 4 — Mirror generator and generated surface cleanup

Gate: `python scripts/sync_mirrors/core.py --check` or equivalent mirror check passes after regeneration, plus mirror tests green.

- [x] T-4.1 — RED: update mirror target tests for `.agents` and no Gemini current surface
  - Agent: build
  - Files: `tests/integration/sync_mirrors/test_new_surface_targets.py:96`, mirror inventory tests if present
  - Principles applied: §10.5 TDD
  - Patch (deterministic): assert Antigravity generator docs mention `.agents`; add stale `gemini-cli` current-surface guard.
  - Gate: tests fail before generator update.

- [x] T-4.2 — Update Antigravity generator constants and target module
  - Agent: build
  - Files: `scripts/sync_mirrors/core.py:1809`, `scripts/sync_mirrors/antigravity_target.py:1`
  - Principles applied: §10.4 DRY, §10.7 Clean Code
  - Patch (deterministic): route Antigravity output to `.agents/skills` and `.agents/agents`; update comments/docstrings from mirror-only/Gemini-shaped to Antigravity-native; remove `.gemini` surface generation from supported targets.
  - Gate: mirror target tests green.

- [x] T-4.3 — Regenerate/delete derived mirrors and templates
  - Agent: build
  - Files: `.gemini/**`, `GEMINI.md`, `src/ai_engineering/templates/project/.gemini/**`, `src/ai_engineering/templates/project/GEMINI.md`, `.agent/**`, `src/ai_engineering/templates/project/.agent/**`, `.agents/**`, `src/ai_engineering/templates/project/.agents/**`
  - Principles applied: §10.1 KISS, §10.6 SDD
  - Patch (deterministic): `git rm -r` retired generated `.gemini`, `GEMINI.md`, and `.agent`; run mirror sync to create `.agents`; verify no hand-edited generated drift.
  - Gate: mirror sync check green.

## Phase 5 — Validators, IDE audit, docs, and CHANGELOG

Gate: validator/doc tests green; stale-reference grep only allows historical/migration references.

- [x] T-5.1 — Update mirror inventory and validators
  - Agent: build
  - Files: `src/ai_engineering/config/mirror_inventory.py:94`, `src/ai_engineering/validator/_shared.py:194`, `src/ai_engineering/validator/categories/mirror_sync.py:59`, `src/ai_engineering/validator/categories/file_existence.py:170`, `src/ai_engineering/validator/categories/manifest_coherence.py:471`
  - Principles applied: §10.3 SOLID, §10.7 Clean Code
  - Patch (deterministic): remove Gemini current inventory; add Antigravity `.agents/skills` and `.agents/agents`; update root instruction parity from `GEMINI.md` to `AGENTS.md` where Google/Antigravity is concerned.
  - Gate: validator tests green.

- [x] T-5.2 — Update canonical docs and generated mirror prose
  - Agent: build
  - Files: `AGENTS.md`, `CLAUDE.md`, `src/ai_engineering/templates/project/CANONICAL.md`, `.claude/skills/ai-ide-audit/**`, `README.md`, `docs/**` if referenced
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Patch (deterministic): remove current support claims for Gemini CLI/GEMINI.md/.gemini; describe Antigravity as `AGENTS.md` + `.agents` + `agy` diagnostics.
  - Gate: doc grep and mirror lint green.

- [x] T-5.3 — Update CHANGELOG and spec brief if needed
  - Agent: build
  - Files: `CHANGELOG.md`, `.ai-engineering/specs/drafts/antigravity-app-cli-support-brief.md`
  - Principles applied: §10.6 SDD
  - Patch (deterministic): add Unreleased breaking-change note for `gemini-cli`, `GEMINI.md`, `.gemini`, `.agent` removal and `.agents` Antigravity migration.
  - Gate: doc gate green.

## Phase 6 — Final verification, quality loop, and PR delivery

Gate: all local verification green; pushed PR CI green.

- [x] T-6.1 — Run targeted tests
  - Agent: verify
  - Files: `tests/unit/domain/test_surface.py`, `tests/unit/config/test_manifest_surface_schema.py`, `tests/integration/test_install_matrix.py`, `tests/integration/sync_mirrors/test_new_surface_targets.py`, validator/doctor tests touched
  - Principles applied: §10.5 TDD
  - Patch (deterministic): none.
  - Gate: targeted pytest green.

- [x] T-6.2 — Run repository gates
  - Agent: verify
  - Files: `pyproject.toml`, `.semgrep.yml`, `.gitleaks.toml`
  - Principles applied: §10.6 SDD
  - Patch (deterministic): none.
  - Gate: `ruff format --check`, `ruff check`, `pytest` relevant/full suite as feasible, `ai-eng spec verify`, `ai-eng check`/`ai-eng verify` as available.

- [ ] T-6.3 — Commit, push, open/update PR, and watch CI
  - Agent: build
  - Files: full changeset
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Patch (deterministic): conventional commit `feat(surfaces): replace gemini cli with antigravity`; push branch; create PR; poll GitHub checks; remediate failures in one bounded loop until green.
  - Gate: PR checks all green for manual merge.
