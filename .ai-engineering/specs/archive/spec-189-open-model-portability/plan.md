---
plan: spec-189
spec: spec-189
title: "Open-Model Portability — execution plan"
status: draft
execution_route:
  version: 1
  spec: spec-189
  executor: autopilot
  automation: supervised
  concern_count: 10
  estimated_files: 90
  reason: "Whole-fleet content adaptation across 53 skills + 19 agents + specs + canonical + 4 mirror surfaces; 10 concerns; >40 files; includes a structural refactor (split skills, add agents) — autopilot territory per D-189-02."
  safe_next_command: "/ai-autopilot"
---

# Open-Model Portability — execution plan

Architecture pattern: **fleet-wide content transformation gated by static
lints (TDD)**. The gates are built first (Phase 1, RED→GREEN); every downstream
transformation must pass them. Phases 2-3 are structural/deterministic and land
as atomic commits; Phase 4 is the file-scoped bulk (one agent per `.md`, body +
frontmatter together per D-189-02); Phases 5-10 finish content, refactor,
supersession, mirror regen, and the semantic review. Autopilot fans out the
per-file work; this plan sets the phase contracts and gates.

Ownership: `build` = code/`.md` writes; `verify` = read-only checks; `guard` =
advisory. Structural splits (Phase 7) are `/ai-review`-gated per item.

## Phase 1 — Static-gate scaffolding (RED → GREEN)

- [ ] T-1 — RED: test for the front-loading/BLUF check
  - Agent: build
  - Files: `tools/skill_lint/checks/test_frontloading.py` (new)
  - Principles applied: §10.5 TDD
  - Gate: test asserts a skill whose first paragraph (after frontmatter, before the first `##`) is >2 sentences OR contains a numbered/bulleted list → MAJOR finding; a compliant skill → OK. Test RED (no implementation yet).

- [ ] T-2 — GREEN: implement the BLUF check
  - Agent: build
  - Files: `tools/skill_lint/checks/frontloading.py` (new), register in `tools/skill_lint/cli.py`
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): predicate per D-189-08 — first paragraph after frontmatter, before first `##`, must be ≤2 sentences and contain no list line; posture MAJOR/blocking, mirroring `effort.py`/`token_budget.py` shape.
  - Gate: T-1 goes GREEN; full `skill_lint` suite green; check is `required=False` until Phase 4 baseline is clean, then flip (see T-17).

- [ ] T-3 — RED: build-time/runtime boundary regression test
  - Agent: build
  - Files: `tests/conformance/test_no_runtime_reads_at_buildtime.py` (new)
  - Principles applied: §10.5 TDD, §10.8 Hexagonal Architecture
  - Gate: test greps `scripts/sync_mirrors/**/*.py` for `driver.tier`/`driver_tier`; FAILS if any match. Expected to pass immediately — pins the boundary going forward.

- [ ] T-4 — Extend `test_tool_name_map.py` to assert consumption (not inert)
  - Agent: build
  - Files: `tests/unit/config/test_tool_name_map.py`
  - Principles applied: §10.5 TDD
  - Gate: test asserts `core.py` mirror-generation consumes `tool_name_map` for tool-name translation (RED until Phase 6).

## Phase 2 — `model_tier` → `effort` atomic lockstep (ONE commit, D-189-04)

- [ ] T-5 — Delete `model_tier`; promote `effort` as sole skill vocabulary
  - Agent: build
  - Files (the 10-member lockstep, one commit): `tools/skill_lint/checks/effort.py` (`_POLICY_ROW_RE` 3-group→2-group + drop `VALID_MODEL_TIERS`); `.ai-engineering/reference/model-dispatch-policy.md` + its `src/ai_engineering/templates/…` twin (drop the `model_tier` column); all 53 `.claude/skills/*/SKILL.md` frontmatter (remove `model_tier:`); `AgentMeta`/`AGENT_METADATA` in `scripts/sync_mirrors/core.py` (add `effort` key); `tools/skill_lint/cli.py` `--enforce-tier` block; `tools/skill_domain/rubric.py` `_TOLERATED_EXTRA_FIELDS`; `.ai-engineering/scripts/hooks/_lib/observability.py` frozenset/validator + template twin (then regen `hooks-manifest.json`); delete `.ai-engineering/scripts/spec-131/apply_effort_model_tier.py` + its 2 tests; Surface-5 install-template SKILL.md copies (regenerate via `core.py`); rewrite `test_effort.py` + rename `test_model_tier_effort_fields.py`
  - Principles applied: §10.4 DRY, §10.1 KISS
  - Gate: SSOT table column-count and `_POLICY_ROW_RE` change in the SAME commit (else `load_policy().findall()` silently returns 0 rows); `effort` is the sole axis; `skill_lint --check` green; `ai-eng check` 7/7; all 4 mirrors regenerate clean.

## Phase 3 — Agent `model:` build-time validator (D-189-04)

- [ ] T-6 — RED: validator flags `model:` vs `AGENT_METADATA.effort` mismatch
  - Agent: build
  - Files: `scripts/sync_mirrors/test_core.py` (or the existing core test module)
  - Principles applied: §10.5 TDD
  - Gate: test seeds an agent whose hand-typed `model:` disagrees with the Claude-valid mapping of its `effort` → validator raises. RED.

- [ ] T-7 — GREEN: validator in `validate_canonical()`; mirrors derive `model:` from `effort`
  - Agent: build
  - Files: `scripts/sync_mirrors/core.py` — `validate_canonical()` (add cross-check, precedent `effort.py:56-59`); `generate_copilot_agent` (`:936`), `generate_codex_agent` (`:774`), `_generate_translated_agent` (`:822`) derive `model:` from `effort`; leave `generate_install_claude_agent` (`:1354`, byte-copy) untouched
  - Principles applied: §10.3 SOLID (DIP), §10.8 Hexagonal
  - Gate: T-6 GREEN; `.claude/agents/*.md` never rewritten (read-only glob `:59`); mirror `model:` derives correctly; validator runs at build-time/mirror-generation, not the pre-commit hot path.

## Phase 4 — Content hygiene per skill + agent (file-scoped, D-189-08 / M1)

- [ ] T-8 — Adapt each SKILL.md body: BLUF + numbered procedure + flat schemas + reason-in-prose
  - Agent: build (autopilot fans out — one agent per `.md`, body + frontmatter together)
  - Files: all 53 `.claude/skills/*/SKILL.md` (+ their generated mirrors via regen)
  - Principles applied: §10.7 Clean Code, §10.1 KISS
  - Gate (per file): BLUF check (T-2) green; `structure.py` procedure-ratio green; no per-family literal (`kimi|deepseek|qwen|glm|mimo`) in body; reasoning stays prose, gates/verdicts serialize.

- [ ] T-9 — Adapt each agent `.md` body: model-agnostic role/procedure, no Claude-only "only path" prose
  - Agent: build (fan out per agent)
  - Files: all 19 `.claude/agents/*.md`
  - Principles applied: §10.7 Clean Code
  - Gate: per-file structure green; semantic "only path" prose deferred to Phase 10 review.

## Phase 5 — Inline-fallback docs for the 4 dispatch-only skills (D-189-07)

- [ ] T-10 — Document inline-sequential fallback (content, no runtime)
  - Agent: build
  - Files: `.claude/skills/ai-advise/SKILL.md`, `ai-review/SKILL.md`, `ai-verify/SKILL.md`, `ai-simplify/SKILL.md` (+ agent mirrors `ai-review.md`, `ai-verify.md`)
  - Principles applied: §10.2 YAGNI (content only), §10.7 Clean Code
  - Gate: each documents both dispatch modes (Agent-tool primary, inline-sequential fallback); no capability-detection runtime added; portability lint green.

## Phase 6 — Tool-name translation wiring (D-189-06)

- [ ] T-11 — Wire `tool_name_map` name-translation into mirror generation
  - Agent: build
  - Files: `scripts/sync_mirrors/core.py`, `scripts/sync_mirrors/tool_name_map.py`
  - Principles applied: §10.4 DRY
  - Gate: T-4 GREEN (map consumed, not inert); mirror `.md` carry family-correct tool names; per-family runtime quirk fields NOT added (Non-Goal).

## Phase 7 — Structural refactor: split over-broad skills, add specialized agents (D-189-03)

- [ ] T-12 — Identify split candidates (structural gate only)
  - Agent: verify
  - Files: read-only over `.claude/skills/*/SKILL.md`
  - Principles applied: §10.3 SOLID (single responsibility)
  - Gate: produce the candidate list — a skill qualifies ONLY if its `## Workflow` has N independent branches that become N single-purpose skills; each candidate justified; no behavioral bar.

- [ ] T-13 — Execute each split (multi-file atomic op, `/ai-review`-gated per split)
  - Agent: build (one task per split; `/ai-review` sign-off per item)
  - Files: per split — new SKILL.md files, shrunk/deleted original, mirrors, manifest counts
  - Principles applied: §10.3 SOLID, §10.5 TDD
  - Gate (per split): full count-gate set green — `test_manifest`, skill-line-budget exemption, root README stats + alt-text, `ai-eng check`, `tests/mirrors/test_count_parity.py`, `tests/architecture/test_surface_counts.py`, `tests/unit/docs/test_inventory_count_consistency.py`, `.ai-engineering/README` template twin; `/ai-review` approves the split.

## Phase 8 — Supersede PR #639 (D-189-05)

- [ ] T-14 — Close PR #639 as superseded; confirm no driver-tier remnants on main
  - Agent: build
  - Files: N/A (PR close via `gh`); verify `git grep driver_tier` on main = 0
  - Principles applied: §10.1 KISS
  - Gate: PR #639 closed with a superseded note; 0 `driver_tier`/`AIENG_MODEL_TIER` refs; T-3 boundary test green.

## Phase 9 — Mirror regeneration + parity (D-189-02)

- [ ] T-15 — Regenerate all 4 mirror surfaces from canonical; verify parity
  - Agent: build
  - Files: `.codex/`, `.agents/`, `.github/` (via `scripts/sync_mirrors/core.py`; never hand-edited)
  - Principles applied: §10.6 SDD
  - Gate: `tests/mirrors/test_count_parity.py` + surface-parity green; no hand-edited mirror; `ai-eng dev sync` clean.

## Phase 10 — Semantic `/ai-review` pass (verifies the two non-lintable Goals)

- [ ] T-16 — Per-file review for the semantic Goals + value-lens no-collision
  - Agent: verify (`/ai-review`)
  - Files: all adapted `.claude/skills/*/SKILL.md` + `.claude/agents/*.md`
  - Principles applied: §10.7 Clean Code
  - Gate: `/ai-review` confirms (a) no Claude-Code-only assumption stated as the only path, (b) reasoning-in-prose/serialize-gates, (c) BLUF does not duplicate/move the value-lens block. Sign-off recorded.

- [ ] T-17 — Flip the BLUF check and any extended lint to `required=True`
  - Agent: build
  - Files: `src/ai_engineering/policy/checks/stack_runner.py`
  - Principles applied: §10.5 TDD
  - Gate: Phase 4 baseline clean first; then `required=True`; full CI green.
