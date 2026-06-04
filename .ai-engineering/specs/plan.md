---
spec: spec-165
title: Plan — Observation Consolidation Nudge + Scheduled Sweep
status: approved
pipeline: standard
phases: 4
execution_route:
  version: 1
  spec: spec-165
  executor: build
  automation: hitl
  concern_count: 3
  estimated_files: 18
  reason: Three sequential, interdependent concerns (meta schema -> nudge hook -> sweep skill) over high-risk surfaces (hot-path hook integrity, dual-writer meta parity). At the autopilot boundary by concern/file count, but the risk profile warrants controlled per-task TDD over autonomous waves; file count is inflated by mirror/template fan-out. Operator may opt for /ai-autopilot instead.
  safe_next_command: "/ai-build"
---

# Plan — spec-165 Observation Consolidation Nudge + Scheduled Sweep

Fix the System-B (`/ai-session-watch --review`) trigger gap: add a
deterministic SessionStart nudge + a scheduled `/ai-session-watch-sweep`
skill. TDD-first; foundation (meta schema) before consumers (nudge,
sweep).

## Branch / PR

- Working branch: `claude/spec-165-consolidation-trigger` (build branches from `main`).
- Target: `main` via single PR.

## Quality bar

- §10.5 TDD: every behavior RED before code.
- §10.4 DRY: meta keys added to BOTH writers (hook `_lib` + pip twin) — no schema drift.
- Hot-path: nudge is O(1) (stat mtime + small JSON read); never scans the 7 MB NDJSON.
- Hook integrity: any hook edit re-pins `hooks-manifest.json` + keeps template byte-parity.
- No suppression markers; no backwards-compat shims (CONSTITUTION §13).

## Architecture

Pattern: **convention-following** (two established patterns reused):
1. SessionStart `additionalContext` emitter — mirrors
   `runtime-progressive-disclosure.py` (`{"hookSpecificOutput":
   {"hookEventName":"SessionStart","additionalContext":...}}` to stdout).
2. Scheduled wrapper skill + `.sh`/`.ps1` runner + draft PR — mirrors
   `/ai-simplify-sweep` 1:1.

High-risk surfaces flagged by the explore pass:
- Hot-path hook integrity (`regenerate-hooks-manifest.py`) + template
  byte-parity (`test_hook_template_parity.py`).
- Dual-writer meta schema: hook `_lib/instincts.py` `_default_meta()`
  (lines 272-277) AND pip twin `tools/skill_domain/state_models.py`
  `InstinctMeta` (lines 694-701). NOTE pre-existing `deltaThreshold`
  mismatch (hook=10, pydantic=20) is OUT OF SCOPE — new keys land at 10
  in both, do not replicate the drift.
- `meta.json` + `observation-events.ndjson` are GITIGNORED;
  `observations.yml` is TRACKED. So: the nudge marker (`lastReviewedAt`)
  is runtime-only (never in a PR); the sweep PR commits `observations.yml`.

## Design

Resolved in-spec (D-165-03 nudge wording, D-165-04 suppression). No
`/ai-design` routing needed.

## Phase 1 — Meta schema foundation (both writers)

**Anchor:** §10.5 TDD, §10.4 DRY.

### Tasks

- [x] **T-1.1**: RED — assert new meta keys default correctly.
  - Agent: build
  - Files: `tests/unit/hooks/test_instincts_lib_robustness.py` (mirror the existing `_load_meta` default test)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): add to the default-meta assertions —
    ```python
    assert out["lastReviewedAt"] is None
    assert out["reviewDeltaThreshold"] == 10
    ```
  - Gate: `pytest tests/unit/hooks/test_instincts_lib_robustness.py` — RED.

- [x] **T-1.2**: GREEN — add keys to the hook-lib default meta (+ template mirror).
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/_lib/instincts.py:272-277` + `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/instincts.py` (byte-identical)
  - Principles applied: §10.4 DRY
  - Patch (deterministic):
    ```diff
         return {
             "schemaVersion": "1.0",
             "lastExtractedAt": None,
             "deltaThreshold": 10,
    +        "lastReviewedAt": None,
    +        "reviewDeltaThreshold": 10,
         }
    ```
    Then `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py` (re-pin `_lib/instincts.py` sha).
  - Gate: T-1.1 GREEN; `pytest tests/unit/test_hook_template_parity.py` (or broader hook parity) green.

- [x] **T-1.3**: GREEN — add fields to the pip-twin Pydantic model.
  - Agent: build
  - Files: `tools/skill_domain/state_models.py:694-701` (`InstinctMeta`)
  - Principles applied: §10.4 DRY (writer parity)
  - Patch (deterministic):
    ```diff
         delta_threshold: int = Field(default=20, alias="deltaThreshold")
    +    last_reviewed_at: datetime | None = Field(default=None, alias="lastReviewedAt")
    +    review_delta_threshold: int = Field(default=10, alias="reviewDeltaThreshold")
    ```
  - Gate: `pytest tests/ -k "instinct_meta or state_models"`; confirm round-trip alias parity.
  - Note (build): verify whether `src/ai_engineering/state/instincts.py` is a third twin needing the same keys; if so, patch it too (no new test surface, mirror T-1.2).

## Phase 2 — SessionStart nudge

**Anchor:** §10.5 TDD, §10.3 SOLID (single-purpose hook), Hot-Path Discipline.

### Tasks

- [x] **T-2.1**: RED — nudge decision logic (pure, O(1)).
  - Agent: build
  - Files: `tests/unit/hooks/test_observation_nudge.py` (new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic, behavioral spec for the test):
    - pending (NDJSON mtime > `lastReviewedAt`, count signal ≥ `reviewDeltaThreshold` OR `lastReviewedAt` null) → emits `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext": "...pending review..."}}`.
    - fresh (no pending) → emits nothing (silent).
    - missing/corrupt meta or NDJSON → fail-open silent (never raises).
    - MUST NOT read the full NDJSON (assert via a large-file fixture + a read-bytes budget / mtime-only path).
  - Gate: `pytest tests/unit/hooks/test_observation_nudge.py` — RED.

- [x] **T-2.2**: GREEN — implement `runtime-observation-nudge.py` (live + template).
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/runtime-observation-nudge.py` (new) + `src/ai_engineering/templates/.ai-engineering/scripts/hooks/runtime-observation-nudge.py` (byte-identical)
  - Principles applied: §10.3 SOLID, §10.1 KISS
  - Patch: prose — new SessionStart hook. Reads `observations/meta.json` (`lastReviewedAt`, `reviewDeltaThreshold`) + `stat` mtime of `observation-events.ndjson`; if stale, write the `hookSpecificOutput` JSON to stdout (mirror `runtime-progressive-disclosure.py` envelope, `hookEventName="SessionStart"`); else silent. Fail-open on any error (broken store never blocks the IDE). stdlib-only, no full-file read.
  - Gate: T-2.1 GREEN.

- [x] **T-2.3**: GREEN — wire the hook + re-pin manifest + template parity.
  - Agent: build
  - Files: `.claude/settings.json` (SessionStart array, ~line 210) + `src/ai_engineering/templates/project/.claude/settings.json` (parity); `.ai-engineering/state/hooks-manifest.json` (regen)
  - Principles applied: §10.4 DRY
  - Patch (deterministic): append to the SessionStart `hooks` array (both settings files) a `runtime-observation-nudge.py` command entry (`timeout: 5`, same shape as the existing `runtime-session-start.py` entry), then run `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py`.
  - Gate: `pytest tests/unit/test_hook_template_parity.py tests/integration/test_settings_template_narrow.py tests/unit/hooks/test_canonical_events_count.py`; hook-integrity check clean; `ai-eng doctor --check hot-path` within the 5000 ms SessionStart budget.

## Phase 3 — `--review` stamp + scheduled sweep skill

**Anchor:** §10.5 TDD, §10.7 Clean Code.

### Tasks

- [x] **T-3.1**: `--review` stamps `lastReviewedAt`.
  - Agent: build
  - Files: `.claude/skills/ai-session-watch/SKILL.md` (Step 3 WRITE)
  - Principles applied: §10.7 Clean Code
  - Patch: prose — Step 3 explicitly stamps `meta.json.lastReviewedAt` = now (ISO) on a successful review. This is what resets the nudge.
  - Gate: skill body references `lastReviewedAt`; `ai-eng dev sync --check` (mirrors regen).

- [x] **T-3.2**: New `/ai-session-watch-sweep` skill (mirrors `/ai-simplify-sweep`).
  - Agent: build
  - Files: `.claude/skills/ai-session-watch-sweep/SKILL.md` (new)
  - Principles applied: §10.7 Clean Code, §10.1 KISS
  - Patch: prose — frontmatter (`name`, `description`, `effort: cheap`, `model_tier: haiku`, `argument-hint: "[--dry-run] [--no-pr]"`, `tags: [meta, session-watch, scheduled, autonomous]`). Body mirrors simplify-sweep: Step 1 invoke `/ai-session-watch --review` with **work-item creation suppressed** (D-165-04, steps 1-3 + stamp only); empty → emit `session_watch_sweep_no_op`, exit 0. Step 2 gate `ai-eng gate run --mode=local`; fail → `session_watch_sweep_gate_failed`, no PR. Step 3 `/ai-commit` + `/ai-pr --draft` (chore), emit `session_watch_sweep_pr_opened`. Document `/schedule weekly /ai-session-watch-sweep` (never self-cron).
  - Gate: skill renders; `--review` invoked with suppression documented.

- [x] **T-3.3**: Register the skill (registry 53→54) + scheduled wrapper.
  - Agent: build
  - Files: `src/ai_engineering/config/framework_defaults.py:240-312` (`DEFAULT_SKILLS_REGISTRY`); `.ai-engineering/scripts/scheduled/session-watch-sweep.sh` (+ `.ps1`) new, mirror `scheduled/simplify-sweep.sh`
  - Principles applied: §10.4 DRY
  - Patch (deterministic) — registry entry:
    ```python
    "ai-session-watch-sweep": {"type": "meta", "tags": ["meta", "session-watch", "scheduled", "autonomous"]},
    ```
    Wrapper: resolve project root, invoke the sweep path, emit `framework_operation operation=session_watch_sweep_scheduled_run outcome=...`, never raise.
  - Gate: `skills.total` auto-increments to 54.

- [x] **T-3.4**: Regenerate mirrors + template copies.
  - Agent: build
  - Files: `.codex/ .github/ .agents/` skill mirrors + `src/ai_engineering/templates/project/**` copies (all sync-generated)
  - Principles applied: §10.4 DRY
  - Patch: none — run `ai-eng dev sync`.
  - Gate: `ai-eng dev sync --check` clean; `pytest tests/mirrors/test_count_parity.py tests/unit/test_template_skill_parity.py tests/integration/test_skill_mirror_consistency.py`; CANONICAL/CLAUDE "Skills (54)".

## Phase 4 — Docs + final verification

**Anchor:** §10.5 TDD.

### Tasks

- [x] **T-4.1**: CHANGELOG entry.
  - Agent: build
  - Files: `CHANGELOG.md` (Unreleased → Added)
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): add — `- **feat(spec-165)**: observation-consolidation nudge (SessionStart) + scheduled /ai-session-watch-sweep skill — closes the manual --review trigger gap; nudge is O(1) hot-path-safe, sweep opens a draft chore PR (no auto work-items, operator-registered cron).`
  - Gate: docs/changelog tests green.

- [x] **T-4.2**: Full verification gate.
  - Agent: verify
  - Files: (read-only)
  - Principles applied: §10.5 TDD
  - Gate: `pytest tests/unit/hooks tests/mirrors tests/unit/test_hook_template_parity.py tests/unit/test_template_skill_parity.py tests/integration/test_skill_mirror_consistency.py`; `ai-eng dev sync --check`; hook-integrity enforce clean; `ai-eng doctor --check hot-path` within budget; `python -m tools.spec_lint --check .ai-engineering/specs/spec.md`.

## Risk notes (carried from spec)

- Hot-path budget → T-2.1 asserts no full-NDJSON read; T-2.3 gate checks SessionStart budget.
- Hook integrity self-disable → T-1.2 / T-2.3 re-pin manifest after every hook edit.
- Dual-writer meta drift → T-1.2 + T-1.3 patch both writers; do NOT replicate the legacy deltaThreshold mismatch.
- New-skill fan-out → T-3.4 dev sync + parity gates.
- Schedule not wired by default → documented `/schedule weekly`; nudge is the safety net (accepted, per spec Non-Goals).

## Quality Outcome

- **Verdict: PASS.** No blocker/critical/high findings; no remediation pass consumed.
- Tests: 454 passed / 1 deselected across `tests/unit/hooks tests/mirrors`
  + hook/skill/settings parity suites. Nudge contract (7), meta-schema (11),
  count/skill-mirror parity (145) all green.
- Sync: `ai-eng dev sync --check` "Mirrors in sync"; Skills (54) across all surfaces.
- Hooks: manifest re-pinned (76 hooks); SessionStart nudge wired (live+template).
- Lint: `spec_lint --check spec.md` 0 BLOCKERS / 0 ADVISORIES.
- Scope note: built onto `fix/soul-md-install-wiring` / PR #586 per operator
  direction (mixed-scope acknowledged); `report.md` + `spec-166.json` excluded.
