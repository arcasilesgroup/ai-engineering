---
title: spec-183 — CLI command audit + functional color-grouped help — execution plan
spec: spec-183
status: draft
pipeline: full
execution_route:
  version: 1
  spec: spec-183
  executor: autopilot
  automation: assisted
  concern_count: 5
  estimated_files: 20
  reason: "Distinct concerns (hard-deletes + release-hide, docstring fixes, cli-reference rewrite, Phase-2 visual renderer) across ~20 files, spanning a gated 2-phase boundary. Multi-concern + large surface → autopilot with wave decomposition. (The original deprecation-notice concern was reversed per D-183-04.)"
  safe_next_command: "/ai-autopilot"
---

## Design

Design-intent is PRE-SETTLED in brainstorm (D-183-06 renderer approach, D-183-07
palette, approved mockup `ai-eng-help-mockup.svg`). No new design routing needed
(`--skip-design` rationale: color taxonomy, token choices, and the two-hook
render approach were all decided and operator-approved during /ai-brainstorm).
Phase-2 visual contract:
- 4 panels: **Lifecycle** (brand teal `#00D4AA`), **Governance** (new violet
  `#A78BFA`), **Inspection** (`info` blue), **Maintenance** (`muted` grey).
- Panel TITLE is the primary signal; color is reinforcement only (a11y gate S1).
- `NO_COLOR` / `TERM=dumb` / non-TTY / `--json` paths unchanged.

## Architecture

Pattern: **ad-hoc / additive-interception** (not a canonical hexagonal change).
All changes edit the existing CLI surface or hook one additive renderer into
existing seams — no new architectural layer. Reused seams:
- `_build_removed_handler(old,new)` (`cli_factory.py:370`) — subcommand tombstones.
- `_NOTICE_EXEMPT` + `maybe_render_update_notice` json-gating (`cli_factory.py:69,134`; `cli_ui.py:375`) — deprecation-notice pattern.
- `THEME` dict (`cli_ui.py:31-41`) — palette extension.
- `_app_callback:236` + `SmartTyperGroup` (`cli_factory.py:401,412`) — two render hooks, one shared fn.
- `hidden=True` on `dev`/`internal` — `release` hide.

Gate boundary: **Phase 1 (A–D) MUST be fully green before Phase 2 (E) starts.**

---

## Phase A — Deletions + release hide (Goal 1, 2)

- [ ] T-A1 — RED: assert the 3 removed subcommands print `removed; use '<new>'` and exit 2
- Agent: build
- Files: tests/unit/test_cli_removed_verbs.py (new or extend existing removed-verb test)
- Principles applied: §10.5 TDD
- Patch (deterministic): none — new test asserting `CliRunner` invoke of `spec activate` / `maintenance branch-cleanup` / `maintenance spec-reset` each yields exit_code==2 and stderr contains `removed; use 'spec start'` / `'cleanup branches'` / `'cleanup specs'`.
- Gate: pytest tests/unit/test_cli_removed_verbs.py (RED — commands still alias today)

- [ ] T-A2 — GREEN: register the 3 subcommand tombstones, delete their impls
- Agent: build
- Files: src/ai_engineering/cli_factory.py:594 (spec activate), src/ai_engineering/cli_factory.py (maintenance branch-cleanup/spec-reset registrations); src/ai_engineering/cli_commands/spec_cmd.py:188-191 (delete spec_activate); src/ai_engineering/cli_commands/maintenance.py:141,300 (delete command wrappers)
- Principles applied: §10.1 KISS, §10.4 DRY (reuse `_build_removed_handler`)
- Patch (deterministic): replace the live registrations, e.g.
  ```diff
  -    spec_app.command("activate", hidden=True)(_safe(spec_cmd.spec_activate))
  +    spec_app.command("activate", hidden=True)(_build_removed_handler("spec activate", "spec start"))
  ```
  and analogously `maint_app.command("branch-cleanup", hidden=True)(_build_removed_handler("maintenance branch-cleanup", "cleanup branches"))`, `maint_app.command("spec-reset", hidden=True)(_build_removed_handler("maintenance spec-reset", "cleanup specs"))`. Delete the now-orphaned `spec_activate`, `maintenance_branch_cleanup`, `maintenance_spec_reset` command functions. KEEP `run_spec_reset` (still called by `maintenance all`, maintenance.py:577).
- Gate: pytest tests/unit/test_cli_removed_verbs.py (GREEN)

- [ ] T-A3 — Delete orphaned impl + its unit test; verify no live caller remains
- Agent: build
- Files: src/ai_engineering/maintenance/branch_cleanup.py (delete if `run_branch_cleanup` has no remaining caller — grep first); tests/unit/test_spec_cmd.py::TestSpecActivate (delete); tests referencing maintenance_branch_cleanup/maintenance_spec_reset command wrappers (tests/integration/test_cli_command_modules.py:144,874 — update to assert tombstone)
- Principles applied: §10.7 Clean Code (no dead code)
- Patch (deterministic): none — conditional delete; `run_spec_reset` stays, `run_branch_cleanup` deleted ONLY if `grep -rn run_branch_cleanup src/` shows no non-test caller (maintenance all does NOT use it — confirm).
- Gate: `grep -rn "run_branch_cleanup\|maintenance_branch_cleanup\|spec_activate\|maintenance_spec_reset" src/ tests/` returns only tombstone/removed-verb references; pytest tests/unit tests/integration -k "removed or spec_cmd or command_modules" green

- [ ] T-A4 — RED: assert `release` is hidden from --help + JSON list but still invocable
- Agent: build
- Files: tests/unit/test_cli_release_hidden.py (new)
- Principles applied: §10.5 TDD
- Patch (deterministic): none — assert `release` NOT in `create_app()` help output nor in the `cli_factory.py:220` JSON command list, AND `ai-eng release --help` exit_code==0 (still invocable).
- Gate: pytest tests/unit/test_cli_release_hidden.py (RED)

- [ ] T-A5 — GREEN: hide `release` unconditionally
- Agent: build
- Files: src/ai_engineering/cli_factory.py:431 (registration), src/ai_engineering/cli_factory.py:220 (JSON list)
- Principles applied: §10.1 KISS (mirror dev/internal, no new abstraction — D-183-03)
- Patch (deterministic):
  ```diff
  -    app.command("release")(_safe(release.release_cmd))
  +    app.command("release", hidden=True)(_safe(release.release_cmd))
  ```
  plus remove the `release` entry from the JSON command list at cli_factory.py:220 (prose: locate and drop it).
- Gate: pytest tests/unit/test_cli_release_hidden.py (GREEN); full existing help/JSON-list tests green

- [ ] T-A6 — CHANGELOG: breaking changes + 2 behavior drops
- Agent: build
- Files: CHANGELOG.md (### Breaking changes)
- Principles applied: §10.6 SDD (Hard Rule 3 — document the breakage)
- Patch (deterministic): none — prose entry naming: `spec activate`→`spec start`; `maintenance branch-cleanup`→`cleanup branches` (drops auto base checkout+pull); `maintenance spec-reset`→`cleanup specs` common-case / `maintenance all` full-parity (drops standalone live-buffer reset). MINOR bump note.
- Gate: docs tests green; manual read confirms both dropped behaviors named

## Phase B — Docstring/help-text fixes (Goal 3)

- [ ] T-B1 — RED: assert corrected help/docstrings for the 4 bug sites
- Agent: build
- Files: tests/unit/test_cli_docstrings.py (new or extend)
- Principles applied: §10.5 TDD
- Patch (deterministic): none — assert: `setup` success strings no longer contain `install_state table`; `doctor --check` help/docstring no longer contain `state-db` AND `--check state-db` raises BadParameter (already true — assert it stays); `cleanup branches --reset` help no longer says "Force re-sync to remote state"; `gate pre-push`/`gate risk-check` docstrings disclose Article VII + expiring-soon.
- Gate: pytest tests/unit/test_cli_docstrings.py (RED)

- [ ] T-B2 — GREEN: setup.py install_state strings + comments
- Agent: build
- Files: src/ai_engineering/cli_commands/setup.py:187,194,286,299,376,387
- Principles applied: §10.7 Clean Code (honest messages)
- Patch (deterministic):
  ```diff
  -    success("State saved to install_state table")
  +    success("State saved to .ai-engineering/state (install-state records)")
  ```
  ×3 (lines 194, 299, 387); reword the three `# … (state.db singleton row)` comments (187, 286, 376) to name the files-only store.
- Gate: pytest tests/unit/test_cli_docstrings.py (setup assertions green)

- [ ] T-B3 — GREEN: doctor --check remove dead state-db value
- Agent: build
- Files: src/ai_engineering/cli_commands/core.py:1376-1379 (option help), core.py:1388-1389 (docstring)
- Principles applied: §10.7 Clean Code
- Patch (deterministic): edit the `--check` help to `"Run a focused sub-check: 'hot-path' (SLO budgets, advisory)."` (drop the state-db clause); delete the state-db sentence from the docstring (1388-1389). Dispatcher already supports only hot-path — no logic change.
- Gate: pytest tests/unit/test_cli_docstrings.py (doctor assertions green)

- [ ] T-B4 — GREEN: cleanup --reset accurate help
- Agent: build
- Files: src/ai_engineering/cli_commands/cleanup.py:233
- Principles applied: §10.7 Clean Code
- Patch (deterministic):
  ```diff
  -    reset: Annotated[bool, typer.Option("--reset", help="Force re-sync to remote state.")] = False,
  +    reset: Annotated[bool, typer.Option("--reset", help="Target branches with no upstream (alias of --untracked; no force re-sync).")] = False,
  ```
- Gate: pytest tests/unit/test_cli_docstrings.py (cleanup assertion green)

- [ ] T-B5 — GREEN: gate pre-push / risk-check full-scope docstrings
- Agent: build
- Files: src/ai_engineering/cli_commands/gate.py:124 (pre-push docstring), gate.py:230 (risk-check --strict docstring line), gate.py:224 (--strict option help)
- Principles applied: §10.7 Clean Code (disclose enforcement scope)
- Patch (deterministic): pre-push docstring → `"""Run pre-push gate checks (Article VII suppression scan, risk-acceptance expiry [expired + expiring-soon], semgrep, pip-audit, tests, ty)."""`; risk-check docstring/`--strict` help → state `--strict` also fails on expiring-soon (matching `expired or (strict and expiring)`, gate.py:214). Text-only; no behavior change.
- Gate: pytest tests/unit/test_cli_docstrings.py (gate assertions green)

## Phase C — cli-reference rewrite + parity test (Goal 4)

- [ ] T-C1 — RED: parity test — every non-hidden top-level command appears in cli-reference.md
- Agent: build
- Files: tests/unit/docs/test_cli_reference_parity.py (new)
- Principles applied: §10.5 TDD
- Patch (deterministic): none — enumerate non-hidden top-level names from `create_app()` (exclude `hidden=True` + `_REMOVED_VERBS`), assert each appears ≥1× in `.ai-engineering/reference/cli-reference.md`. RED against today's stale doc (11 missing).
- Gate: pytest tests/unit/docs/test_cli_reference_parity.py (RED — 11 missing)

- [ ] T-C2 — GREEN: rewrite canonical cli-reference.md from the live command tree
- Agent: build
- Files: .ai-engineering/reference/cli-reference.md
- Principles applied: §10.6 SDD (doc = contract), §10.4 DRY (single systematic pass)
- Patch (deterministic): none (synthesis) — add the 11 missing surfaces (verify, status, commit, pr, host, cleanup, decision, ownership, risk, spec, plan); remove 6 phantoms (audit index/query/otel-export, config ide/provider list); fix bare-config desc → `config surface` + `config reconfigure`. Reflect Phase-A deletions (no branch-cleanup/spec-reset/spec activate).
- Gate: pytest tests/unit/docs/test_cli_reference_parity.py (GREEN)

- [ ] T-C3 — GREEN: regenerate template mirror in lockstep (byte-parity)
- Agent: build
- Files: src/ai_engineering/templates/.ai-engineering/reference/cli-reference.md
- Principles applied: §10.4 DRY (installer twin must match — memory: no CI parity guard)
- Patch (deterministic): none — copy the corrected canonical content into the template mirror; ensure the deleted commands (was :110-118) are gone.
- Gate: `diff` canonical vs template (allowing only intended install-path deltas) shows no stale-command residue; docs tests green

## Phase D — (dropped) Deprecation notices

Reversed per operator principle (D-183-04): this framework does not do
soft-deprecation. The 9 low-signal commands are left clean and silent —
no per-invocation notice, no helper, no test. A future spec may
hard-remove any that prove dead. Originally shipped then removed during
delivery; the commands themselves are untouched and fully functional.

## Phase E — Phase-2 renderer + palette + golden test (Goals 7–10) [GATED on A–D green]

- [ ] T-E1 — GREEN: add Governance violet token to THEME
- Agent: build
- Files: src/ai_engineering/cli_ui.py:31-41 (THEME), cli_ui.py:29 (adjacent constant)
- Principles applied: §10.1 KISS (one token, D-183-07)
- Patch (deterministic): add a 10th key, e.g. `"governance": Style(color="#A78BFA")` (violet), alongside the existing 9.
- Gate: pytest tests/unit -k cli_ui green

- [ ] T-E2 — RED: golden test — every visible non-tombstone command in exactly one category
- Agent: build
- Files: tests/unit/test_cli_help_taxonomy.py (new)
- Principles applied: §10.5 TDD, R-183-03 (drift guard)
- Patch (deterministic): none — assert the `{command: category}` map covers every VISIBLE non-tombstone top-level command exactly once; EXCLUDE `hidden=True` groups (dev, internal, release) and `_REMOVED_VERBS`. Any uncovered visible cmd → fail.
- Gate: pytest tests/unit/test_cli_help_taxonomy.py (RED — map not built yet)

- [ ] T-E3 — GREEN: build the {command: category} map + shared 4-panel render fn
- Agent: build
- Files: src/ai_engineering/cli_help_render.py (new module) or cli_ui.py; the map + `render_grouped_help(app, console)` producing 4 titled/colored Rich panels + a dim "Other" catch-all (fail-open)
- Principles applied: §10.2 YAGNI (no framework swap), §10.3 SOLID (one render responsibility)
- Patch (deterministic): none (synthesis) — 4 panels per D-183-08 taxonomy; title text primary, color reinforcement; unmapped visible cmd → "Other" panel.
- Gate: pytest tests/unit/test_cli_help_taxonomy.py (GREEN)

- [ ] T-E4 — RED: golden output tests — bare + --help render 4 panels; NO_COLOR/dumb/non-TTY/--json unchanged
- Agent: build
- Files: tests/unit/test_cli_help_render.py (new, golden snapshots)
- Principles applied: §10.5 TDD, accessibility gate S1
- Patch (deterministic): none — snapshot `ai-eng` (bare) and `ai-eng --help` show the 4 titled panels; assert `NO_COLOR=1`, `TERM=dumb`, non-TTY, and `--json` outputs are byte-identical to pre-change baseline.
- Gate: pytest tests/unit/test_cli_help_render.py (RED)

- [ ] T-E5 — GREEN: hook the renderer at both root paths
- Agent: build
- Files: src/ai_engineering/cli_factory.py:236 (_app_callback bare path), SmartTyperGroup (cli_factory.py:401,412 — override format_help/get_help for the --help path)
- Principles applied: §10.4 DRY (both hooks call the same render fn — D-183-06)
- Patch (deterministic): none (synthesis) — bare path swaps `typer.echo(ctx.get_help())` for the grouped renderer; SmartTyperGroup routes the root `--help` through the same fn. Subcommand `--help` untouched.
- Gate: pytest tests/unit/test_cli_help_render.py (GREEN); subcommand --help golden tests unchanged

## Final gate (autopilot Phase 5)

- [ ] T-F1 — Full verify + review + guard on the complete changeset
- Agent: verify
- Files: (whole diff)
- Principles applied: §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): none
- Gate: full `pytest`, `ai-eng gate pre-push`, `ai-eng check` all green; deterministic help/JSON/NO_COLOR paths proven unaffected; CHANGELOG + both cli-reference copies consistent
