---
spec: spec-132
slug: cli-ux-overhaul
title: spec-132 — CLI UX & Architecture Overhaul (single-PR full-brief delivery)
status: approved
approved_at: 2026-05-12
approved_by: operator
effort: large
branch: spec-128/context-overrides-refactor
pr: arcasilesgroup/ai-engineering#509
target_dispatch: /ai-autopilot
source_brief: .ai-engineering/specs/drafts/cli-ux-overhaul-brief.md
chains_after: spec-131 (DX excellence refactor — same PR aggregate)
---

## Summary

The `ai-eng` CLI fails the **"self-describing, observable, idempotent, honest"** bar across every public command surface verified on HEAD of `spec-128/context-overrides-refactor` (PR #509). Concretely:

1. **Spam on every connect()**: `_warn_on_deprecated_fallbacks` at `src/ai_engineering/state/state_db.py:172-194` fires unconditionally, no dedup set, generating ~34 warning lines during a single `ai-eng install` because the installer itself writes the JSON files it then warns about (`installer/phases/state.py:120` `write_json_model` for `_OWNERSHIP` + `_DECISIONS`).
2. **Installer hangs on Engram prompt**: `installer/engram.py` (383 lines) still wires interactive `[y/N]` prompt at `maybe_install_engram()` line 304-360 with subprocess calls to brew/winget that deadlock; `--engram`/`--no-engram` flags wired at `cli_commands/core.py:176,187`. Engram is a third-party product — should not live in our installer surface.
3. **Help-on-empty anti-pattern across the entire CLI**: `verify`, `release`, `stack {add,remove}`, `ide {add,remove}`, `gate commit-msg`, `provider add`, `spec activate` all use `typer.Argument(...)` with no default → error "Missing argument" instead of printing help. No `@no_args_help` decorator exists.
4. **Surface duplication and naming drift**: `validate` (should be `check`); `work-item` (should be `issue`); separate `stack`/`ide`/`provider`/`vcs` mutator verbs (should collapse to `config`); `workflow` is a 112-line shim duplicating `gate all` + `release` (should be deleted); `sync` is consumer-facing top-level (should be `dev sync`, hidden in non-source-repos).
5. **Output is ad-hoc**: 4 modules (`cli_envelope`, `cli_ui`, `cli_progress`, `cli_output`) called directly by every command, no centralised Renderer, no consistent "before/action/after" narrative, no diff summary, no "next steps" footer.
6. **Architecture is not hexagonal**: domain logic, I/O, Typer command definitions, file copy, network calls, and platform shells all live in the same modules. `core/` does not exist; `adapters/` does not exist; no import-linter contract.
7. **Validator false-positives**: `_should_skip_reference_path` in `validator/categories/file_existence.py` does not exclude `src/ai_engineering/...` refs (LLM implementation notes that don't ship to consumers), and `_record_spec_buffer_result` (line 228-256) hard-fails when `_history.md` is missing despite spec-131 D-131-04 making `/ai-cleanup` the lifecycle owner of that file.
8. **Duplicate CONSTITUTION.md**: 4 copies on HEAD (root 197 / `.ai-engineering/` 113 stub / `templates/project/` 197 / `templates/.ai-engineering/` 79). The `.ai-engineering/CONSTITUTION.md` 113-line stub is divergent and serves no architectural role; installer ships the project-charter template to BOTH consumer root and `.ai-engineering/` (`templates.py:171-184`).

The North Star (brief §1): *a first-time engineer runs `ai-eng install` on an empty repo and never feels confused, never sees noise, never hits a hidden failure mode. Every command shows what it is doing, why, and what changed.*

This spec delivers the full brief (M0–M6) inside the existing PR #509 (4-spec aggregate: spec-128 / spec-129 / spec-131 / spec-132), under deterministic `/ai-autopilot` dispatch. No new branch. No new PR. Hard renames with zero deprecation aliases per CANONICAL.md §13 rule 3.

## Goals

### Functional goals (acceptance-verifiable)

1. **Zero-noise install on empty repo**: `ai-eng install` on a fresh `mktemp -d` invocation produces 0 warning lines, 0 error lines, 0 hangs, ≤ 30s wall-clock. Verified by golden-snapshot test `tests/integration/installer/test_install_zero_noise.py`.
2. **Idempotent update**: immediately after `ai-eng install`, `ai-eng update --check` reports `0 changes`. Verified by golden test `tests/integration/installer/test_update_post_install_idempotent.py`.
3. **Full validation success on fresh install**: `ai-eng check` (renamed from `validate`) + `ai-eng doctor` + `ai-eng verify` (default profile) all PASS with score ≥ 95 on a fresh install. Verified by `tests/integration/check_doctor_verify_fresh.py`.
4. **Help-on-empty universal contract**: every command and every subcommand invoked with no arguments prints help and exits 0. Verified by parametrised test that iterates `app.registered_commands` and `app.registered_groups` recursively.
5. **Renderer is single source of truth for output**: zero direct calls to `cli_envelope`, `cli_ui`, `cli_progress`, `cli_output` from any module under `cli_commands/`. Verified by `ruff` custom rule `AIENG-OUT-001` (banned-import).
6. **Final command tree locked** (per brief §8.3, hard renames, no aliases): `install`, `update`, `status`, `doctor`, `check`, `verify`, `audit`, `config`, `gate`, `spec`, `issue`, `release`, `setup`, `decision`, `risk`, `guide`, `version`, `dev`, `commit`, `pr` (the last two are off-chain WIP helpers labelled as such in help text). Verified by golden snapshot of `ai-eng --help`.
7. **Hexagonal seam enforced**: `core/` (governance, state mutations, spec lifecycle, output Renderer) has zero imports from `adapters/` (`cli`, `installer`, `vcs`, `ide`). `import-linter` contract green; CI fails on direction violation. Verified by `pyproject.toml` `[tool.importlinter]` config + `tests/architecture/test_hexagonal.py`.
8. **Single CONSTITUTION.md per install**: only ONE `CONSTITUTION.md` ships to a consumer (root). Source-repo `.ai-engineering/CONSTITUTION.md` (113-line stub) deleted. Verified by `tests/integration/installer/test_constitution_single.py` (`subprocess` `find`).
9. **State warner deduped**: warn at most ONCE per orphan JSON file per `state.db` lifetime. The dedup set lives at module level inside `state_db.py`. Verified by `tests/unit/state/test_state_db_fallback_warning_dedup.py`.
10. **Engram fully removed from installer**: zero references to `engram` in `installer/`, `cli_commands/core.py`, `manifest.yml`, CANONICAL.md / AGENTS.md / CLAUDE.md / GEMINI.md / `.github/copilot-instructions.md` install steps. Standalone optional integration doc lives at `docs/integrations/engram.md`. Verified by repo-wide `rg` golden test.
11. **No `# noqa`, `# nosec`, `# type: ignore`, `# pragma: no cover`, `// NOSONAR` introduced** anywhere in this PR. Existing instances unaffected (separate concern). Verified by `tools/skill_lint/checks/no_suppression.py` (re-uses spec-131 D-131-08 lint pipeline).
12. **Hot-path budgets preserved**: pre-commit < 1s, pre-push < 5s — Renderer must not regress this. Verified by `tests/perf/test_hotpath_budgets.py` (already exists; spec re-runs).

### Quality goals

13. **TDD throughout**: every code change lands RED → GREEN → REFACTOR. New test count ≥ 80 (state.db dedup 6 / installer phases state UPSERT 8 / engram removal 0 (deletion + 1 import-test) / help-on-empty parametrised 35+ / Renderer methods 18 / surface rename golden 12 / hex import-linter 3).
14. **`/ai-review --full` clean**: zero BLOCKER findings, zero unresolved CRITICAL after one converge round.
15. **`/ai-verify --full` ≥ 95**: governance + architecture + feature dimensions.
16. **CHANGELOG documents every breaking rename**: §[Breaking changes] section lists `validate→check`, `work-item→issue`, `stack/ide/provider/vcs (mutators)→config`, `workflow→deleted`, `sync→dev sync`, Engram removed, CONSTITUTION single-location.

## Non-Goals

The following are explicitly OUT OF SCOPE for spec-132 (PR #509). Capture them as follow-ups if/when value justifies.

1. **No Engram replacement memory layer.** Engram is removed; no in-house substitute. CANONICAL.md "Optional: Engram" section is rewritten to point to `docs/integrations/engram.md`.
2. **No backwards-compat aliases.** Hard rename per CANONICAL.md §13 rule 3. Old verbs do not soft-redirect; they print `removed; use <new>` and exit 1. CHANGELOG documents the breakage.
3. **No `workflow` revival under another name.** Its responsibilities map cleanly to `release --pr` / `/ai-pr` / `/ai-commit` (D-131-07 chain). Nothing replaces it.
4. **No new Typer-incompatible CLI framework.** Stay on Typer; add a thin wrapper, do not migrate to Click or argparse.
5. **No additional IDE adapters.** Claude Code / Copilot / Gemini / Codex set is frozen for this PR. New IDEs are a separate spec.
6. **No new third-party integrations** (analytics, telemetry vendors, secret managers). Removing Engram is the only third-party touch.
7. **No GitHub Projects v2 board redesign.** `issue` rename is naming + label-handling only; board sync semantics unchanged.
8. **No on-disk schema migration beyond what spec-125 already plans for `state.db`.** `_OWNERSHIP` / `_DECISIONS` JSON files are deleted via one-shot installer cleanup; no separate migration entry-point.
9. **No new languages or stacks** added to the install picker. Existing matrix (python, typescript, go, rust, swift, csharp, kotlin per spec-128 D-128-09) is fixed.
10. **No documentation portal redesign.** `docs/integrations/engram.md` is a single new file; surrounding docs/ structure unchanged.

## Decisions

Every decision below carries `choice → rationale`. All locked at brainstorm approval time (2026-05-12).

### D-132-01 — Branch & PR locking

**Choice**: All work lands on existing branch `spec-128/context-overrides-refactor` and rides existing PR `arcasilesgroup/ai-engineering#509`. No new branch. No new PR.
**Rationale**: PR #509 is already a 4-spec aggregate (spec-128 + spec-129 + spec-131 + this spec-132). Operator explicit instruction during brainstorm: "hacer todo en la rama actual donde estamos … no crear nuevo branch, no crear nuevo pr, usar la que tenemos abierta." Brief header lines 4-5 reference obsolete branch `feat/spec-126-...` / PR #506 — superseded by the current branch state. CHANGELOG entry must reflect spec-132 alongside spec-128/129/131.

### D-132-02 — `validate` → `check`, hard rename, zero alias

**Choice**: Top-level command renames from `validate` to `check`. The old `validate` is removed entirely. Old invocation prints `error: command 'validate' was removed; use 'check'` (Typer `unknown command` handler with custom message) and exits 2 (Typer convention for unknown command).
**Rationale**: Brief §2.2 + §8.3 lock; operator confirmation "A" during brainstorm. CANONICAL.md §13 rule 3 forbids backwards-compat shims for renamed verbs. CHANGELOG `### Breaking changes` documents.

### D-132-03 — `work-item` → `issue`, hard rename, zero alias

**Choice**: Top-level subcommand renames from `work-item` to `issue`. Subcommand surface (`sync`, etc.) preserved under new name. `src/ai_engineering/work_items/` module renames to `src/ai_engineering/issues/` (deferred to follow-up only if rename collides; otherwise renamed in same PR).
**Rationale**: Brief §8.3. `issue` matches GitHub primary mental model (PR #509 origin: arcasilesgroup/ai-engineering). `board` rejected because it implies UI navigation rather than item-level operations.

### D-132-04 — `stack` / `ide` / `provider` / `vcs` mutator verbs → `config`, hard collapse, zero alias

**Choice**: Mutating subcommands (`stack add/remove`, `ide add/remove`, `provider add/remove`, `vcs set-primary`) collapse to a single `ai-eng config` interactive flow that wraps the install wizard reconfigure path. Inspection verbs (`stack list`, `ide list`, `provider list`, `vcs status`) move under `ai-eng config <resource> list|status`. Top-level `stack`/`ide`/`provider`/`vcs` removed.
**Rationale**: Brief §2.2 + §8.3. Reduces top-level surface from 4 redundant resource verbs to 1 unified entry. `config` matches `git config` mental model (operator preference). KISS / YAGNI per CANONICAL.md §10.1 §10.2.

### D-132-05 — `workflow` deleted entirely

**Choice**: `workflow.py` (112-line shim) and its Typer registration are deleted. The three previous verbs (`workflow commit`, `workflow pr`, `workflow pr-only`) map respectively to: `/ai-commit` skill, `ai-eng pr` (or `/ai-pr` skill), `ai-eng release --pr` (M3 sub-flag). Old `workflow` invocation prints `removed; use 'ai-eng pr' or '/ai-pr' skill` and exits 2.
**Rationale**: Brief §8.3 lock. Duplicates `gate all` + `release`. spec-131 D-131-07 already removed `/ai-commit` from canonical chain; `workflow.py` predated that decision and is now redundant.

### D-132-06 — Engram removed from installer, doc-only optional integration

**Choice**: Delete `src/ai_engineering/installer/engram.py`. Delete `--engram` / `--no-engram` flags from `cli_commands/core.py`. Remove install-time prompt. Remove engram references from `manifest.yml`, AGENTS.md / CLAUDE.md / GEMINI.md / `.github/copilot-instructions.md` install steps. Add `docs/integrations/engram.md` (standalone doc, marked third-party, official Engram install + `engram setup claude_code` instructions). `ai-eng doctor` MAY detect Engram if present and report status; never installs or prompts.
**Rationale**: Brief §2.1 B2. Bundling third-party installs creates unmaintainable dependency surface (brew formula drift, subprocess deadlock, version skew). Removal eliminates the install-hang root cause. Operator-validated during brainstorm.

### D-132-07 — State warner dedup at module level

**Choice**: Introduce `_WARNED_FALLBACKS: set[Path] = set()` at module scope in `src/ai_engineering/state/state_db.py`. `_warn_on_deprecated_fallbacks` (line 172-194) gates emission on `path not in _WARNED_FALLBACKS`, then adds. Reset hook for tests via `_reset_fallback_warnings()`.
**Rationale**: Brief §2.1 B1. Minimum-diff fix; preserves existing warning content; eliminates spam without altering log behaviour for users who legitimately have stale state JSON outside of install context.

### D-132-08 — Installer state phase UPSERTs to state.db instead of writing JSON

**Choice**: `src/ai_engineering/installer/phases/state.py` stops calling `write_json_model` for `_OWNERSHIP` (`ownership_map.json`) and `_DECISIONS` (`decisions.json`). Instead, UPSERT directly to `ownership_map` and `decisions` tables in state.db inside the same transaction. Plus a one-shot cleanup step: if legacy JSON files exist on a previously-installed repo, delete them after successful state.db UPSERT.
**Rationale**: Brief §2.1 B1 + §2.4 architecture-hygiene goal "one source of truth for state: state.db". Removes the self-inflicted source of the warning loop. One-shot cleanup respects existing installs without leaving orphans.

### D-132-09 — Validator `src/ai_engineering/...` skip + `_history.md` WARN downgrade

**Choice**: `_should_skip_reference_path` (file_existence.py:138-147) gains an early-return for path patterns starting with `src/ai_engineering/` when the reference originates from a `.claude/skills/*.md` or `.github/skills/*.md` (these are LLM implementation notes, not consumer-shipped paths). `_record_spec_buffer_result` (line 228-256) downgrades missing `_history.md` from FAIL to WARN when both `spec.md` and `plan.md` exist in the same directory. Adds `IOCS_ATTRIBUTION.md` to `src/ai_engineering/templates/.ai-engineering/references/`.
**Rationale**: Brief §2.1 B4. spec-131 D-131-04 already established `/ai-cleanup` as the lifecycle owner of `_history.md`; installer must not ship a stub. WARN preserves observability without blocking fresh install.

### D-132-10 — `sync` moves to `dev sync`, hidden in consumer projects

**Choice**: Top-level `sync` command removed. New `dev` Typer group created (`Hidden=True` when running from a consumer install — detected via absence of `pyproject.toml` `[tool.aiengineering.source_repo] = true` marker). `dev sync` is the only verb under `dev` initially. Script `scripts/sync_command_mirrors.py` registered to spec-131 D-131-12 trusted-script lane so hook integrity passes.
**Rationale**: Brief §2.1 B6. The command was internal-only by design but accidentally exposed; moving it under `dev` makes the visibility explicit and protects consumers from a useless top-level verb.

### D-132-11 — Universal `@no_args_help` decorator at command registration

**Choice**: New helper `core/cli/decorators.py:no_args_help` wraps Typer command callbacks. Behaviour: if the parsed Click context has no provided args AND the command has at least one required argument with no default, the wrapper invokes `ctx.get_help()` and exits 0 instead of letting Typer raise `MissingParameter`. Applied at registration time inside `cli_factory.py:create_app()` for every public command and subcommand. Internal `dev` commands opt out.
**Rationale**: Brief §2.1 B6/B9/B10/B11 + §2.3 "No bare `--help` exit on no args is acceptable in 2026". Universal application avoids per-command opt-in drift. Internal commands keep strict argument requirements because they have no human users.

### D-132-12 — Renderer is single source of truth for human + JSON output

**Choice**: New `src/ai_engineering/core/output/renderer.py` with the contract from brief §8.2. `Renderer(command, *, json, quiet)` instance per command invocation. Verb taxonomy = `Literal["Installing", "Updating", "Removing", "Moving", "Creating", "Verifying", "Skipping", "Restoring"]` (closed). Methods: `header / step / action / progress / record / diff_summary / error / next / ok`. Modes: `human` (default Rich-backed), `json` (envelope accumulation), `quiet` (errors only). Wraps existing `cli_envelope`, `cli_ui`, `cli_progress`, `cli_output` — does not replace them yet (deletion deferred). After this PR, every command under `cli_commands/` calls Renderer; direct calls to the legacy 4 modules from `cli_commands/` raise a `ruff` `AIENG-OUT-001` ban.
**Rationale**: Brief §2.3 narrative output contract + §2.4 "output formatting is one module". DRY per CANONICAL.md §10.4. Closed Verb taxonomy enforces consistency at type-check time. Wrapper (not replacement) prevents big-bang risk; legacy modules retire in a follow-up cleanup spec.

### D-132-13 — Hexagonal split: core/ vs adapters/

**Choice**: Repo reorganises:
- `src/ai_engineering/core/` — pure domain. Governance rules, state mutations (via repository ports), spec lifecycle, Renderer, decisions engine, risk register, ownership map. **Zero imports from adapters/.** Zero imports of `requests`, `httpx`, `psycopg`, `boto3`, `subprocess`, `os.path` direct file I/O outside of repository ports.
- `src/ai_engineering/adapters/cli/` — Typer commands. Thin: parse args → call core use-case → render result.
- `src/ai_engineering/adapters/installer/` — phase orchestration, file copy, manifest sync.
- `src/ai_engineering/adapters/vcs/` — gh, ado.
- `src/ai_engineering/adapters/ide/` — claude, copilot, gemini, codex.
- `import-linter` contract pins direction: `core` must not import `adapters`. Test: `tests/architecture/test_hexagonal.py` runs `lint-imports --config pyproject.toml`.
**Rationale**: Brief §2.4 architecture-hygiene + CANONICAL.md §10.8. Single-PR refactor accepts risk; the new layout is the long-term seam every subsequent feature lives behind.

### D-132-14 — CONSTITUTION.md single-location ship policy

**Choice**: Delete source-repo `.ai-engineering/CONSTITUTION.md` (113-line divergent stub). Installer ships project-charter template (the spec-131 D-131-04 project-identity shape: 10 sections) to consumer ROOT only, not to consumer `.ai-engineering/`. Drop `templates/.ai-engineering/CONSTITUTION.md` (79-line stub) entirely; the templates/ directory no longer carries a `.ai-engineering/CONSTITUTION.md`. CI invariant test `tests/unit/installer/test_constitution_single_location.py` asserts exactly one `CONSTITUTION.md` per consumer install.
**Rationale**: Brief §2.1 B3 + spec-131 D-131-04 chain. The 4-copy state is purely accidental drift; one canonical template at one canonical destination is the SDD-correct shape.

### D-132-15 — Final command tree (locked)

**Choice**: `ai-eng --help` after this PR shows exactly:
```
install / update / status / doctor / check / verify / audit / config / gate /
spec / issue / release / setup / decision / risk / guide / version / dev / commit / pr
```
20 top-level verbs total. `dev` is hidden in consumer projects. `commit` and `pr` carry help-text label `WIP / standalone — not part of the canonical chain (use /ai-pr skill for orchestrated PR open).`
**Rationale**: Brief §8.3. Reduces surface from ~30+ scattered verbs to 20 with explicit visibility tiers. Lifecycle / Inspection / Maintenance taxonomy reflected in help-text grouping.

### D-132-16 — Dogfood drift policy: source-repo configs sync to template

**Choice**: Source-repo `.gitleaks.toml` (currently 31 lines) and `.semgrep.yml` (currently older than template) sync UP to match the stricter `src/ai_engineering/templates/project/` versions on commit. CI test `tests/integration/test_dogfood_parity.py` enforces sha256 equivalence unless a `# AIENG_DOGFOOD_DRIFT_OK: <reason>` marker is present in both files (with matching reason text).
**Rationale**: Brief §2.1 B16. Source repo must dogfood its own consumer-facing rules; weaker source-repo gates make it possible for the source-repo to pass while a consumer install would fail.

### D-132-17 — `contexts/team` deprecation cleanup

**Choice**: `src/ai_engineering/templates/.ai-engineering/contexts/team/` directory (currently contains only a stub README.md) deleted. `ai-eng update` learns to detect this orphan in existing consumer installs and includes it in the update-preview "Removed" list with explicit user confirmation when interactive (auto-removed when `--yes`).
**Rationale**: Brief §2.1 B13. Previously deprecated, never removed; this is the cleanup beat.

### D-132-18 — `_OWNERSHIP` / `_DECISIONS` JSON cleanup in update flow

**Choice**: `ai-eng update` (not just `install`) gains a one-shot cleanup step: if `_OWNERSHIP` or `_DECISIONS` JSON sidecar files exist alongside a populated `state.db`, the update preview lists them in "Removed" and removes them after user confirmation. Per spec-131 D-131-12, this cleanup runs in the trusted-script lane to avoid prompt-injection-guard interaction.
**Rationale**: Brief §2.1 B1 cleanup beat for already-installed consumers. Ensures the state-warner dedup (D-132-07) becomes "warn at most once, then disappear forever after `ai-eng update`."

### D-132-19 — Sub-spec decomposition target for `/ai-autopilot`

**Choice**: spec-132 decomposes into **6 sub-specs** for autopilot Phase 1:
- **sub-132.001** — P0 Stop-The-Bleeding (D-132-06, D-132-07, D-132-08, D-132-09, D-132-14, D-132-17, D-132-18). No surface changes.
- **sub-132.002** — Renderer Module (D-132-12). New `core/output/renderer.py` + ban-import lint. Existing commands NOT yet migrated.
- **sub-132.003** — Help-First Discipline (D-132-11). Universal `@no_args_help` decorator + per-command application + golden snapshots.
- **sub-132.004** — Surface Consolidation (D-132-02, D-132-03, D-132-04, D-132-05, D-132-10, D-132-15). Hard renames + final tree. **Depends on sub-132.002 + sub-132.003** because new commands must wire to Renderer + help-first wrapper.
- **sub-132.005** — Hexagonal Refactor (D-132-13). `core/` vs `adapters/` split + import-linter contract. **Depends on sub-132.001 + sub-132.002** (Renderer becomes part of core/; state warner fix simplifies the layer split).
- **sub-132.006** — Dogfood + Polish (D-132-16 + final-quality-loop fixes). **Depends on sub-132.001–005**.
**Rationale**: Mirrors brief §3 milestone shape (M1=001, M2=002, M3=003, M4=004, M5=005, M6=006). Autopilot DAG: 001 → (002 ‖ 003) → 004 → 005 → 006. Wave 1: 001 alone (highest urgency). Wave 2: 002 + 003 in parallel. Wave 3: 004 (renames). Wave 4: 005 (hex). Wave 5: 006 (polish + final quality loop).

### D-132-20 — Final-quality-loop policy

**Choice**: spec-131 D-131-05 single-round fail-loud policy stands. After all 6 sub-specs land, `/ai-autopilot` Phase 5 runs ONE round of `/ai-verify` + `/ai-guard` + `/ai-review --full`. Any BLOCKER stops and escalates; no auto-retry. Closure sweep (brief §3 M6) lands in a SINGLE follow-up commit per spec-131 pattern (`bc37ce2f` precedent).
**Rationale**: CANONICAL.md §13 rule 5. Telemetry from spec-131 (≈9.1% post-trim ratio) confirms the policy works at this scale.

### D-132-21 — `pr_lifecycle` event taxonomy unchanged

**Choice**: Renames do NOT extend the framework-events.ndjson schema. Old event names (`workflow.commit_start`, `validate.completed`) deprecated in-place; new emits use `pr.commit_start`, `check.completed`. spec-132 ships a one-shot back-compat reader in `audit index` so historical events remain queryable but writers only emit new names.
**Rationale**: Audit trail observability per spec-120; minimum impact to consumers running `ai-eng audit query` against historical data.

### D-132-22 — No new suppression introduced

**Choice**: Zero new `# noqa`, `# nosec`, `# type: ignore`, `# pragma: no cover`, `// NOSONAR`, `// nolint` anywhere in spec-132 diff. Pre-existing instances unaffected (separate concern); new code follows refactor-or-risk-accept rule from CANONICAL.md §13 rule 2.
**Rationale**: Hard-rule restatement; CI gate `tools/skill_lint/checks/no_suppression.py` already exists (spec-131 D-131-08). Re-runs at sub-spec close.

### D-132-23 — `commit` and `pr` top-level survive with explicit WIP label

**Choice**: `ai-eng commit` and `ai-eng pr` remain top-level (already shipped). Help text gains explicit label: `WIP / standalone — not part of the canonical chain. For orchestrated commit+push+PR open, use the /ai-pr skill instead.` per brief §9.2 soft alignment.
**Rationale**: spec-131 D-131-07 made `/ai-commit` off-chain; CLI command stays so operators can still drive commits from terminal. Labelling prevents confusion about chain vs standalone.

### D-132-24 — Schema documentation for `.ai-engineering/specs/` and `.ai-engineering/state/`

**Choice**: New `docs/architecture/dir-schemas.md` documents the canonical file-tree shape of `.ai-engineering/specs/` and `.ai-engineering/state/` after install. Golden-file test `tests/integration/installer/test_install_dir_schema.py` snapshots a fresh-install listing and fails if diff drifts without spec.
**Rationale**: Brief §2.1 B14. Closes the unknown ("needs explore" line in brief).

### D-132-25 — Branch / PR metadata in CHANGELOG

**Choice**: CHANGELOG `### [unreleased]` section gains a spec-132 block under "Breaking changes" listing each rename in D-132-02 through D-132-05 + D-132-06 + D-132-10 + D-132-14. CHANGELOG also updates PR #509 title (via `gh pr edit`) to include spec-132 alongside the existing 128/129/131 mention.
**Rationale**: Operator-stated PR scope inclusion. CHANGELOG required for `/ai-pr` final-quality-loop gate.

## Risks

### R-CLI-01 — PR #509 size & review fatigue

**Risk.** PR #509 already has ~+159k / -74k / 2206 files changed before spec-132. Adding 6 sub-specs of CLI work could push it past human-reviewable bounds (estimated +6k / -4k / ~200 more files).
**Mitigation.** (a) Sub-spec commits land atomically with descriptive messages (`refactor(spec-132 sub-001): P0 bug sweep`, etc.). (b) Use `gh pr review --request-review` per sub-spec wave so reviewers can review incrementally. (c) If review feedback indicates the PR is too large at sub-132.004 boundary, **escalation criterion: pause and call operator** rather than force-merging.

### R-CLI-02 — Hexagonal refactor regression risk (D-132-13)

**Risk.** Moving ~50+ modules from `src/ai_engineering/` flat layout to `core/` + `adapters/` invites import drift, test path drift, IDE adapter wiring breakage.
**Mitigation.** (a) Use `git mv` for every relocation, preserving blame. (b) Run full `pytest` + `ruff` + `mypy` + `import-linter` after each module move. (c) `tests/architecture/test_hexagonal.py` runs in pre-push gate so drift surfaces immediately. (d) Sub-132.005 is the LAST sub-spec wave so prior changes (renames, Renderer) settle before the move.

### R-CLI-03 — Hard rename breaks consumer muscle memory

**Risk.** Operators downstream who scripted `ai-eng validate` or `ai-eng work-item sync` in CI pipelines will see immediate failure on the next `pip install --upgrade` of `ai-engineering`.
**Mitigation.** (a) CHANGELOG `### Breaking changes` (D-132-25) is the contract. (b) Old-verb invocation prints `removed; use <new>` with the new verb on the SAME line — no need to consult docs. (c) Major-version bump (likely `0.5.0`) communicates breakage. (d) Release notes / blog post follow-up (not in spec-132 scope but flagged for `/ai-gtm`).

### R-CLI-04 — Engram removal breaks the (very small) population of users who installed via the prompt

**Risk.** Anyone who answered `y` to the engram prompt and depends on `engram setup claude_code` having been run will see no install path next time.
**Mitigation.** (a) `docs/integrations/engram.md` carries the manual install commands per OS. (b) CHANGELOG `### Breaking changes` references the doc. (c) `ai-eng doctor` is taught to detect installed Engram and print "Engram detected; no install action needed" so users can verify status post-upgrade.

### R-CLI-05 — Renderer JSON-mode drift from existing `cli_envelope` consumers

**Risk.** External tooling that parses `ai-eng --json` output may depend on the exact envelope shape produced by `cli_envelope.py`.
**Mitigation.** (a) Renderer JSON mode delegates to existing `cli_envelope.emit_*` functions for the actual JSON write — Renderer only orchestrates field accumulation. (b) Golden-file tests freeze the current `--json` schema for `install`, `update`, `doctor`, `check`, `verify`. (c) Schema bump signalled in JSON envelope with `schema_version: 1.1` (was 1.0); tooling can branch.

### R-CLI-06 — `import-linter` performance on hot path

**Risk.** Adding `import-linter` to pre-push gate could slow the < 5s budget if not configured carefully.
**Mitigation.** (a) `import-linter` runs against the static contract file only, not whole-tree analysis on each push. (b) Benchmark in sub-132.005 as part of acceptance; if >500ms, move to pre-merge CI only (warn-locally instead of block-locally). (c) Hot-path budget test re-runs after sub-132.005 close.

### R-CLI-07 — State.db UPSERT vs JSON write transactional semantics (D-132-08)

**Risk.** Crashes mid-install could leave state.db with new rows but orphan JSON still on disk (or vice versa).
**Mitigation.** (a) UPSERT + JSON cleanup happen inside the same SQLite transaction; cleanup uses a deferred `Path.unlink()` triggered only after `connection.commit()`. (b) If unlink fails (permission, ENOENT), warn at most once via D-132-07 dedup and continue. (c) Idempotency: re-run of `install` with both state.db and JSON present runs the same UPSERT + cleanup path harmlessly.

### R-CLI-08 — `dev sync` invisibility regresses developer ergonomics

**Risk.** Source-repo contributors used to typing `ai-eng sync` now have to type `ai-eng dev sync`; hidden in consumer projects but visible in source repo — risk of muscle-memory friction during transition.
**Mitigation.** (a) Source-repo `pyproject.toml` ships with `[tool.aiengineering.source_repo] = true` so `dev` is always visible in source repo. (b) CHANGELOG documents the move. (c) `ai-eng dev --help` lists `sync` first.

## References

- doc: .ai-engineering/specs/drafts/cli-ux-overhaul-brief.md
- doc: .ai-engineering/specs/drafts/dx-excellence-refactor-brief.md (cross-brief coordination per brief §9)
- pr: arcasilesgroup/ai-engineering#509
- doc: CANONICAL.md (§10 engineering principles + §13 hard rules)
- doc: .ai-engineering/contexts/spec-schema.md
- doc: .ai-engineering/specs/_history.md (lifecycle precedent: spec-128/129/131)
- doc: .ai-engineering/specs/archive/spec-131-dx-excellence-refactor.md (predecessor archived 2026-05-12)
- doc: .claude/skills/ai-autopilot/SKILL.md (target dispatch contract)
- doc: src/ai_engineering/state/state_db.py (B1 root-cause line 172-194)
- doc: src/ai_engineering/installer/engram.py (B2 deletion target)
- doc: src/ai_engineering/cli_factory.py:222 (B6 sync registration)
- doc: src/ai_engineering/validator/categories/file_existence.py (B4 patch site)
- doc: src/ai_engineering/installer/phases/state.py (B1 secondary site + D-132-08 UPSERT target)
- doc: src/ai_engineering/templates/.ai-engineering/contexts/team/ (B13 deletion target)
- doc: src/ai_engineering/cli_envelope.py / cli_ui.py / cli_progress.py / cli_output.py (D-132-12 wrappee surfaces)
- doc: docs/getting-started.md (spec-131 D-131 onboarding doc — must stay coherent after renames)

## Open Questions

None at brainstorm close (2026-05-12). The remaining brief §6 open decisions were resolved during interrogation:
- §6.1 (final names): resolved by D-132-02 / D-132-03 / D-132-04.
- §6.2 (workflow keep/delete): resolved by D-132-05 (delete).
- §6.3 (AGENTS.md ship policy): resolved by spec-131 D-131-03 (already in HEAD).
- §6.4 (Engram opt-in vs prompt): resolved by D-132-06 (remove).
- §6.5 (deprecation aliases): resolved by D-132-02..05 ("hard rename, zero aliases" per operator confirmation A).

Any further question discovered during `/ai-plan` decomposition must be raised as a `### Open Question` in `plan.md` and either resolved inline (cheap) or escalated back to `/ai-brainstorm` (expensive).
