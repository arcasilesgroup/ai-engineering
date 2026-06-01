---
execution_route:
  version: 1
  spec: spec-159
  executor: autopilot
  automation: assisted
  concern_count: 6
  estimated_files: 18
  reason: >
    Six concerns across four subsystems (packaging, updater CLI, sync_mirrors
    generation, CI). (1) P0 wheel-include gap — 52 .sh/.ps1/.ts/.rego launchers
    absent from the wheel break every external install. (2) update_cmd must
    finalize hooks-manifest. (3) sync_mirrors parity: hook-scripts sync step +
    specialist-agent verbatim split + hooks.json generator. (4) drop cursor from
    manifest. (5) fail-loud CI wheel + drift guards. (6) 0.9.1 release. ~18
    authored files plus a large mechanical `ai-eng dev sync` resync. >=3
    concerns + a release step -> autopilot wraps the chain (sub-specs, DAG,
    waves, single quality loop).
  safe_next_command: "/ai-autopilot"
spec: spec-159
title: Installer source-of-truth parity — wheel content + sync_mirrors drift + fail-loud guards
status: approved
pipeline: full
---

# spec-159 — Execution Plan

## Architecture

**Pattern: Pipeline parity + fail-loud guard ring.**

The framework keeps two copies of every installable surface: the **canonical**
authoring copy at the repo root (`.claude/`, `.ai-engineering/scripts/hooks/`,
`.github/hooks/hooks.json`, …) and the **packaged install template** under
`src/ai_engineering/templates/`. `scripts/sync_mirrors/core.py` is the
generation pipeline that must keep template == canonical; the wheel build
(`pyproject.toml`) is what ships the template tree to external users; the
updater (`cli_commands/core.py`) compares an installed project against the
packaged template.

Every bug in this spec is a **missing pipeline edge**: a surface flows into one
node but not the next. The fix set closes each edge and then wraps the whole
pipeline in a **fail-loud guard ring** (CI) so a future missing edge turns the
build red instead of silently drifting.

> **Empirical correction (mid-build).** The original "P0" framing — that the
> wheel `include` excluded the 52 `.sh/.ps1/.ts/.rego` launchers — was
> **disproven by building the wheel**: `packages = ["src/ai_engineering"]` ships
> them regardless of `include`, with and without the launcher globs (`run-hook.sh`
> present both times). The **real** external-install reliability bug is
> `update_cmd` not finalizing `hooks-manifest.json` (T-6) → stale sha256 → the
> default `enforce` integrity mode kills hooks after every `ai-eng update`. T-5
> (include globs) + T-1 (wheel-content test) are retained as a defensive
> allowlist + regression guard, not as the fix.

Implementation boundaries:
- **Packaging** (`pyproject.toml`) — pure declarative allowlist; no logic.
- **Updater CLI** (`cli_commands/core.py`) — add one idempotent post-apply call;
  must run on apply, NOT on `--preview`/dry-run.
- **sync_mirrors** (`scripts/sync_mirrors/core.py`) — three generation edges
  (hook-scripts copy step, specialist-agent `.claude` verbatim split, hooks.json
  generator + dual-write). `ai-eng dev sync` then materializes the resync.
- **Guards** (CI + tests) — inspect the *built artifact* and run
  `sync_mirrors --check`; both blocking.

## Design

UI/UX: none (backend packaging + CI). Design routing: **ad-hoc** — no surface
affordances. `--skip-design` rationale: pure build-system / generation-pipeline
work with no user-facing rendering.

## Pipeline classification

`full` — >5 files, multi-subsystem, new generation logic + new CI guards.

## Phases & Tasks

### Phase 0 — RED tests first (§10.5 TDD)

All four assert the bug as it exists today; they MUST fail before any GREEN task.

- [ ] T-1 — RED: wheel-content test (built artifact)
  - Agent: build
  - Files: `tests/unit/packaging/test_wheel_content.py` (new)
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch (deterministic): none — judgment (build wheel into tmp, `python -m build --wheel` or `hatch build`, unzip, assert every `_lib/run-hook.sh`, `_lib/resolve-python.sh`, each `copilot-*.sh`/`.ps1`, the `.ts` bridge, and all three `.rego` exist under `ai_engineering/templates/`). Enumerate expected set from the repo's `templates/**` `.sh/.ps1/.ts/.rego` listing.
  - Gate: test FAILS on current `pyproject.toml` (launchers absent from wheel).

- [ ] T-2 — RED: surface-drift guard
  - Agent: build
  - Files: `tests/unit/sync/test_surface_drift.py` (new or extend existing sync test)
  - Principles applied: §10.5 TDD, §10.4 DRY
  - Patch (deterministic): none — judgment (invoke `sync_mirrors.sync_all(check_only=True)` and assert returns 0 / no diffs; the canonical fail-loud signal).
  - Gate: test FAILS now (16 hook files + specialist agents + hooks.json drift).

- [ ] T-3 — RED: hooks-manifest finalized after update
  - Agent: build
  - Files: `tests/unit/cli/test_update_finalizes_manifest.py` (new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): none — judgment (install into tmp project, mutate a hook's bytes via an `update` apply, assert `hooks-manifest.json` sha256 matches deployed bytes; today it stays stale).
  - Gate: test FAILS now (`update_cmd` never calls `_finalize_hooks_manifest`).

- [ ] T-4 — RED: hooks.json single-source parity
  - Agent: build
  - Files: `tests/unit/sync/test_hooks_json_parity.py` (new)
  - Principles applied: §10.5 TDD, §10.4 DRY
  - Patch (deterministic): none — judgment (assert `.github/hooks/hooks.json` == `src/.../templates/project/.github/hooks/hooks.json` byte-for-byte, and that both equal the generator output).
  - Gate: test FAILS now (122 vs 101 lines).

### Phase 1 — P0 packaging (D-159-01)

- [ ] T-5 — GREEN: ship launcher/policy extensions in the wheel
  - Agent: build
  - Files: `pyproject.toml:274-279` (`[tool.hatch.build.targets.wheel].include`)
  - Principles applied: §10.2 YAGNI (explicit allowlist, no `**/*`), §10.6 SDD
  - Patch (deterministic):
    ```diff
     include = [
       "src/ai_engineering/templates/**/*.md",
       "src/ai_engineering/templates/**/*.yml",
       "src/ai_engineering/templates/**/*.json",
    +  "src/ai_engineering/templates/**/*.sh",
    +  "src/ai_engineering/templates/**/*.ps1",
    +  "src/ai_engineering/templates/**/*.ts",
    +  "src/ai_engineering/templates/**/*.rego",
       "src/ai_engineering/version/registry.json",
     ]
    ```
  - Gate: T-1 passes; `python -m build --wheel` then unzip shows the 52 files.

### Phase 2 — updater finalizes manifest (D-159-03)

- [ ] T-6 — GREEN: `update_cmd` calls `_finalize_hooks_manifest`
  - Agent: build
  - Files: `src/ai_engineering/cli_commands/core.py:1071` (after `result = workflow_result.result`, on the apply path only — NOT under `--preview`/dry-run/`json_requested` early returns)
  - Principles applied: §10.3 SOLID (parity with `install_cmd:237`), §10.9 autonomous-fix
  - Patch (deterministic): none — judgment (guard so it runs only when an apply actually mutated hook bytes; mirror the `install_cmd` call but gated on `result` indicating applied changes, not preview).
  - Gate: T-3 passes; hooks survive `AIENG_HOOK_INTEGRITY_MODE=enforce` after update.

### Phase 3 — sync_mirrors parity (D-159-04, 05, 06)

- [ ] T-7 — GREEN: add hook-scripts sync step (new Surface 10)
  - Agent: build
  - Files: `scripts/sync_mirrors/core.py` (after Surface 9, ~line 1927)
  - Principles applied: §10.4 DRY (single regen path), §10.3 SOLID
  - Patch (deterministic): none — judgment (model on Surface 9: walk `ROOT/.ai-engineering/scripts/hooks/**/*.py` incl. `_lib/`, skip `__pycache__`, `_generate_surface` into `templates/.ai-engineering/scripts/hooks/<relative>`).
  - Gate: `sync_mirrors --check` no longer reports the 16 hook files.

- [ ] T-8 — GREEN: specialist-agent `.claude` template written verbatim
  - Agent: build
  - Files: `scripts/sync_mirrors/core.py:956-963` (`_specialist_agent_output_paths`) + `:1606-1607` (sync loop)
  - Principles applied: §10.7 Clean Code, §10.4 DRY
  - Patch (deterministic): none — judgment. Today `generate_specialist_agent()` (provenance-injected) is written to ALL targets including `TPL_CLAUDE_AGENTS / name`. Split: the `.claude` install-template target must receive `generate_install_claude_agent(specialist_path)` (raw verbatim copy, matching canonical `.claude/agents/*`); the non-claude copilot mirror targets (`repo_rel`/`template_rel`) keep the provenance-injected string. Do NOT strip provenance from the copilot mirrors.
  - Gate: dogfood `ai-eng update --preview` reports `.claude/agents/*` as `unchanged`.

- [ ] T-9 — GREEN: generate `.github/hooks/hooks.json` from one source + dual-write
  - Agent: build
  - Files: `scripts/sync_mirrors/core.py` (new `generate_copilot_hooks_json()`, add to the dual-write tuple list near `:1596` alongside the codex `(ROOT/".codex"/"hooks.json", TPL_CODEX_HOOKS)` pattern)
  - Principles applied: §10.4 DRY (eliminate dual hand-maintenance), §10.3 SOLID
  - Patch (deterministic): none — judgment (build from the canonical hook event→script mapping; MUST reproduce the current 122-line repo content incl. the `copilot-runtime-stop` block; dual-write `ROOT/.github/hooks/hooks.json` + `TPL_PROJECT/.github/hooks/hooks.json`). See R2 — golden snapshot before replacing either copy.
  - Gate: T-4 passes; both copies byte-identical to generator output.

- [ ] T-10 — materialize resync (mechanical churn, isolated commit)
  - Agent: build
  - Files: regenerated under `src/ai_engineering/templates/**` + any repo-root mirror (run `python scripts/sync_mirrors/core.py` / `ai-eng dev sync`)
  - Principles applied: §10.4 DRY, §10.7 Clean Code (separate mechanical churn from logic — R6)
  - Patch (deterministic): none — run the regen command; commit the byte-mechanical diff separately from T-7/T-8/T-9 logic.
  - Gate: `git diff` shows only template-tree resync; `sync_mirrors --check` clean.

### Phase 4 — drop cursor from dogfood manifest (D-159-07)

- [ ] T-11 — GREEN: remove `cursor` from `surfaces.enabled`
  - Agent: build
  - Files: `.ai-engineering/manifest.yml:34`
  - Principles applied: §10.2 YAGNI (dogfood doesn't run Cursor), §10.6 SDD
  - Patch (deterministic):
    ```diff
       - opencode
    -  - cursor
       - antigravity
    ```
  - Gate: dogfood `ai-eng update --preview` reports zero `.cursor/**` changes; `.cursor` templates still present in tree.

### Phase 5 — fail-loud CI guard ring (D-159-08)

- [ ] T-12 — wire wheel-content + surface-drift guards into CI as blocking
  - Agent: build
  - Files: the CI workflow under `.github/workflows/*` (the lint/test job), plus ensure T-1/T-2 run there
  - Principles applied: §10.6 SDD, Hard-Rule fail-loud doctrine
  - Patch (deterministic): none — RESOLVED with NO new CI YAML. The drift guard already exists and is blocking: `ci-check.yml:601` "Mirror sync integrity: uv run ai-eng dev sync --check" (now covers the WAVE-1 hook-scripts + hooks.json sync). The wheel-content guard + the three sync/manifest guards ship as unit tests under `tests/unit/**`, collected by the blocking `test-unit` job (`ci-check.yml:327`). Editing CI YAML was rejected as redundant + risky (Actions allowlist / actionlint / SHA-pinning governance).
  - Gate: an unsynced surface edit (drift) fails `dev sync --check`; a packaging regression that drops launchers (e.g. an `exclude` rule) fails `test_wheel_content`. NOTE: reverting the T-5 `include` globs alone does NOT drop launchers (hatchling ships them via `packages`), so the wheel guard is proven against a real `exclude`-style regression, not against T-5 reversion.

### Phase 6 — verify + release (D-159-09)

- [ ] T-13 — full verification of parity
  - Agent: verify
  - Files: read-only across the changeset
  - Principles applied: §10.6 SDD (Verification Before Done)
  - Gate: `ai-eng update --preview` in dogfood = 0 Available / 0 Orphan (only protected operator files); all Phase-0 tests green; `sync_mirrors --check` clean.

- [ ] T-14 — CHANGELOG + 0.9.1 release
  - Agent: build
  - Files: `CHANGELOG.md`, `pyproject.toml` version, `src/ai_engineering/version/registry.json`
  - Principles applied: §10.6 SDD
  - Patch (deterministic): none — follow the release runbook (staged/resume flow; R5 release gotchas: local-tag bug, TestPyPI propagation rerun, gate `ty` blind spot, Snyk pip-CVE gate). Release is the FINAL step, after merge — not mid-build.
  - Gate: 0.9.1 published; a fresh external `uv tool install ai-engineering` (non-editable) deploys `run-hook.sh` and hooks fire.

## TDD pairing

- T-1 → T-5 (wheel content)
- T-2 → T-7/T-8/T-9/T-10 (surface drift)
- T-3 → T-6 (manifest finalize)
- T-4 → T-9 (hooks.json parity)

## Dependency DAG

```
T-1 ─┐
T-2 ─┤
T-3 ─┼─(RED, parallel)
T-4 ─┘
T-5  ← T-1                         (packaging)
T-6  ← T-3                         (updater)
T-7,T-8,T-9 ← T-2,T-4              (generation; parallel to each other)
T-10 ← T-7,T-8,T-9                 (resync — barrier on all three)
T-11                              (manifest — independent)
T-12 ← T-5,T-10                    (CI guards need the artifacts green)
T-13 ← T-5,T-6,T-10,T-11,T-12      (verify — barrier)
T-14 ← T-13 (+ merge)              (release — terminal)
```

## Gate criteria (plan-level)

1. All Phase-0 RED tests written and failing before any GREEN task.
2. `sync_mirrors --check` exits clean after Phase 3.
3. Dogfood `ai-eng update --preview` = 0 Available / 0 Orphan after Phase 4.
4. CI fails on injected drift / missing wheel content (Phase 5 proven).
5. 0.9.1 published and external-install hook smoke-test passes (Phase 6).
