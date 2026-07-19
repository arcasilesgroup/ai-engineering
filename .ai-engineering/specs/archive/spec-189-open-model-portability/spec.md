---
spec: spec-189
slug: open-model-portability
title: "Open-Model Portability — model-agnostic .md across the fleet"
status: approved
effort: large
summary: "Make every fleet .md structurally model-agnostic, deterministic, and front-loaded so any harness's model can follow it without Claude-Code-only assumptions — content-only, zero model-management runtime; deletes model_tier for a neutral effort axis, verified by static lints + review."
---

# Open-Model Portability — model-agnostic .md across the fleet

## Summary

Today the fleet — 53 skills, 19 agents, the spec/plan/brief markdown, and the
canonical instruction files — is authored assuming the driving model is Claude
Opus inside Claude Code. It works, but it is quietly Claude-Code-shaped in prose,
structure, and vocabulary in ways that degrade when a weaker or non-Claude model
(GPT, or open weights like Kimi/GLM/DeepSeek/Qwen/MiMo) reads and executes it.

This spec makes the fleet **content model-agnostic**. The framework does **not**
gain any ability to manage, detect, route, select, or call models — that is the
operator's harness's job. Our job is that every `.md` is written so that Claude,
GPT, and open models can follow it without Claude-Code-only assumptions blocking
the path — this is structural portability, NOT a guarantee that every model
produces identical output: deterministic numbered
procedure, flat schemas, front-loaded bottom-line, reasoning kept in prose while
gates/verdicts serialize to structure, and a neutral `effort` vocabulary in place
of Claude model-family names. Where a skill is too broad to be followed
deterministically by a weaker model, it is split into more specific skills, and
missing specialized agents are added. Verification is entirely static (lints and
conformance tests over the `.md` and generated mirrors) — there is no live-model
eval harness, because that would mean running models, which is out of scope.

This spec draws its research and evidence from
`.ai-engineering/specs/drafts/open-model-portability-brief.md` but **narrows** it:
the brief's model-management milestones (driver-tier telemetry, dispatch/engine
shims, security-guard runtime fallback, the Promptfoo/DeepEval eval harness) are
explicitly out of scope per the content-only directive. The brief's five
milestones map to this spec as: **M0 OUT**, **M1 IN**, **M2 IN** (except the
runtime driver-tier read), **M3 SPLIT** (the inline-fallback docs are IN per
D-189-07; the `openai_compatible` engine-enum + capability-detection runtime are
OUT per Non-Goals), **M4 OUT**. A planner must not pull a brief milestone this
spec excludes.

## Goals

- Every skill and agent body is model-agnostic: no Claude-Code-only assumptions
  stated as the only path in prose; numbered procedure over imperative prose;
  flat tool schemas (no deep nesting); explicit "use EXCLUSIVELY when ..."
  tool/skill descriptions.
- Every skill body is front-loaded: a one-line bottom-line (BLUF) up top, each
  gate/constraint stated before its rationale, reasoning in prose while only
  gates/verdicts serialize to structure.
- The `model_tier` field is deleted fleet-wide and the existing neutral `effort`
  axis (`cheap|mid|high`) is the sole skill dispatch vocabulary; the atomic
  lockstep change lands without reddening the required lint mid-migration.
- Canonical agents keep a valid, hand-authored Claude `model:` (the frontier
  harness's ground truth), cross-checked by a build-time validator; the four
  generated mirror surfaces derive their `model:` from `effort`.
- Over-broad skills are split into more specific skills, and missing specialized
  agents are added, ONLY where a concrete, statically-observable extraction/clarity
  gain exists (e.g. a `## Workflow` with N independent branches becomes N
  single-purpose skills) — never on a behavioral "measurably improves" bar, since
  no model runs to measure it. Each split/addition is justified per-item in the
  plan and gated by an `/ai-review` sign-off. A split is a multi-file atomic op
  (new files, shrunk/deleted original, moved fleet counts) and is planned as its
  own task — it does not fit D-189-02's single-file-in-place model.
- The four dispatch-only skills (`ai-advise`, `ai-review`, `ai-verify`,
  `ai-simplify`) document an inline-sequential fallback path in their `.md`, so a
  harness without a subagent primitive can still execute them.
- Tool-name translation is wired so generated mirror `.md` carry family-correct
  tool names per surface.
- Static conformance lints verify the machine-checkable Goals (extended
  portability, effort, structure, and a new front-loading/BLUF check; optional
  EARS for the machine-checkable subset of acceptance criteria), all green in CI.
  The two SEMANTIC Goals — no Claude-Code-only "only path" framing in prose, and
  reason-in-prose/serialize-gates — plus the value-lens no-collision rule are
  verified by a per-file `/ai-review` pass, not by a lint (a lint cannot classify
  prose intent or reasoning-vs-gate blocks).
- All four mirror surfaces (`.codex/`, `.agents/`, `.github/`) regenerate clean
  from canonical sources; no mirror is hand-edited.

## Non-Goals

- **Any model management.** No runtime that detects, routes, selects, ranks, or
  calls a model; no model access, keys, endpoints, or SDK integration.
- Driver-tier telemetry — PR #639 (`spec-185/open-model-resilience`) is closed as
  superseded and its telemetry is **not** re-implemented (model detection is
  model management).
- A dispatch capability-detection runtime, an `openai_compatible` engine-enum
  shim, or any security-guard fail-open/fail-closed runtime fallback logic.
- A live-model eval harness (Promptfoo / DeepEval), including the brief's
  credential-free CI fixture-replay layer — descoped as eval infra, not `.md`
  authoring (D-189-01), NOT on a credentials basis.
- **Output-quality or execution equivalence.** We do NOT guarantee a non-Claude
  model produces the same output as Claude — only the structural portability
  properties the static lints + `/ai-review` verify. A weaker model may still
  answer worse; portability means the instruction is followable, not that the
  result is identical.
- Per-family runtime quirk fields (temperature, reasoning_content, tool_choice) —
  these describe runtime API behavior the framework does not manage.
- Adopting TOON or any non-YAML/JSON serialization; RAG chunk-retrieval tuning
  (nothing in the repo retrieves skill chunks).
- Removing or de-prioritizing Claude — Claude Code remains the default and the
  frontier tier; this is additive portability, not replacement.

## Decisions

- **D-189-01 — Content-only: the framework never manages, runs, or routes models.**
  Portability means the `.md` are legible and executable by whatever model the
  operator's harness runs; the framework contributes zero model-execution code.
  **Rationale**: operator directive — ai-engineering must stay a pure authoring
  layer. This removes the brief's heaviest, most speculative surface (runtime
  telemetry, dispatch shims, eval infra), which the adversarial reviews flagged as
  the most fragile, and eliminates the "cannot gate live eval in CI" problem.

- **D-189-02 — Whole fleet in one spec, delivered via `/ai-autopilot` with file-scoped decomposition.**
  All 53 skills + 19 agents + specs + canonical `.md` + 4 mirror surfaces are in
  scope for v1.
  **Rationale**: the operator chose full coverage over a pilot; file-scoped passes
  (body + frontmatter together per file) avoid the same-file collision that
  per-milestone waves would cause, and autopilot is the right vehicle for
  >40-file cross-surface work.

- **D-189-03 — Structural refactor is in scope: split over-broad skills and add specialized agents.**
  Granularity is a first-class portability lever, not cleanup. The split gate is
  STRUCTURAL (a statically-observable extraction/clarity gain), never behavioral —
  "measurably" is deliberately excluded because no model runs to measure it; each
  split is per-item justified, `/ai-review`-gated, and is a multi-file atomic task.
  **Rationale**: a narrower, single-purpose skill is followed more deterministically
  by a weaker model than a broad one that requires the model to infer which branch
  applies; more specific agents reduce the reasoning load open models handle worse
  than Claude.

- **D-189-04 — Delete `model_tier`; promote `effort` as the sole skill vocabulary; agents keep a validated hand-authored Claude `model:`; mirrors derive `model:` from `effort`.**
  The neutral `effort` axis already exists and is the portable semantic truth. The
  atomic lockstep set (all in one commit) is: (1) `_POLICY_ROW_RE` +
  `VALID_MODEL_TIERS` in `effort.py`; (2) the `model-dispatch-policy.md` SSOT table
  + its template twin; (3) all 53 skill frontmatter; (4) `AGENT_METADATA`; (5)
  `skill_lint/cli.py --enforce-tier`; (6) `rubric.py` `_TOLERATED_EXTRA_FIELDS`; (7)
  `observability.py` validator + twin, then regen `hooks-manifest.json`; (8) delete
  `spec-131/apply_effort_model_tier.py` + its 2 tests; (9) Surface-5 install-template
  SKILL.md copies; (10) `test_effort.py` + `test_model_tier_effort_fields.py`. The
  agent-`model:` validator runs at build-time / mirror-generation, not the
  pre-commit hot path.
  **Rationale**: `effort` already coexists in the same lint (`effort.py:40`), so
  deleting `model_tier` is a rename-to-sole-authority, not an invention, and the
  same-commit lockstep is the safety argument. `.claude/agents/*.md` is never a
  write target, so the correct mechanism is a build-time validator cross-checking
  the hand-typed `model:` against `AGENT_METADATA.effort`, not a generator; the "no
  Claude model-family name" rule is scoped to skills, not agents.

- **D-189-05 — Supersede and close PR #639 (`spec-185/open-model-resilience`); do not re-implement driver-tier telemetry.**
  Driver-tier is model detection, which is model management (D-189-01), now out of
  scope.
  **Rationale**: closing it makes the `AIENG_MODEL_TIER` collision and the missing
  `kimi` needle moot — one substrate, zero migration debt.

- **D-189-06 — Keep tool-name translation (build-time mirror correctness); drop the per-family runtime quirk fields.**
  Mirror `.md` carry family-correct tool names; the framework does not carry
  temperature/reasoning_content/tool_choice behavior.
  **Rationale**: name translation is static content that makes a mirror correct for
  a family; quirk fields describe runtime API calls the framework does not make.

- **D-189-07 — Add documented inline-sequential fallback instructions to the four dispatch-only skills; do not build capability-detection runtime.**
  The `.md` documents both dispatch modes and the harness selects.
  **Rationale**: content, not runtime — a harness without a subagent primitive can
  follow the inline path from the instructions alone; no framework code chooses the
  path.

- **D-189-08 — Authoring-structure hardening: front-loading/BLUF, reason-in-prose with serialized gates, YAML for extraction; EARS optional for machine-checkable acceptance.**
  The boundary between extraction (structure) and reasoning (prose) is real and
  directional. The new front-loading/BLUF check's predicate: the first paragraph
  after frontmatter, before the first `##` header, must be <=2 sentences and
  contain no numbered/bulleted list (the BLUF); posture MAJOR/blocking, mirroring
  `effort.py`/`token_budget.py`.
  **Rationale**: audited research — Liu et al. (lost-in-the-middle) supports
  front-loading for weaker models, and "Let Me Speak Freely" shows forcing
  reasoning into strict JSON costs 25-63pp while structured extraction gains; EARS
  is more testable (Kiro precedent) but net-new ceremony, so it is opt-in, never
  mandated, and never conflicts with the freeform Goals contract.

- **D-189-09 — Verification is static lints and conformance only; no live-model eval.**
  Extended portability/effort/structure lints plus a new front-loading check are
  the deterministic gate.
  **Rationale**: an eval harness — even the brief's credential-free CI
  fixture-replay — is Promptfoo/eval infra, not `.md` authoring, so it is descoped
  to keep this a pure authoring layer (D-189-01), NOT because it needs credentials
  (the fixture-replay layer does not). Static lints + a per-file `/ai-review` pass
  over the `.md` and generated mirrors are the deterministic gate; they prove
  structural portability, not output equivalence.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Whole-fleet churn breaks 5-surface mirror parity | Med | High | Regenerate mirrors via `core.py` only; count/surface-parity tests gate before merge |
| The `model_tier` deletion is a multi-member atomic lockstep; a partial change silently reds the required lint or returns 0 policy rows | Med | High | Enumerate the full lockstep set; change the SSOT table column and the policy regex in the same commit; land as one commit during the planning phase |
| Structural refactor (split skills, new agents) trips the hardcoded new-skill count gates | Med | Med | Verify the FULL count-gate set before each split lands: `test_manifest`, skill-line-budget exemption, root README stats + alt-text, `ai-eng check`, `tests/mirrors/test_count_parity.py`, `tests/architecture/test_surface_counts.py`, `tests/unit/docs/test_inventory_count_consistency.py`, and the `.ai-engineering/README` template twin |
| Over-splitting skills fragments the fleet without a real portability win | Med | Med | Split only when a concrete extraction/clarity gain exists; the plan justifies each split/addition; net skill count is reviewed |
| "Model-agnostic" is asserted without live proof (no eval harness by design) | Med | Med | Static lints + conformance are the deterministic gate; the operator may spot-run an open model manually against a sample skill, but done-ness is proven by the static checks |
| Front-loading/BLUF rewrite conflicts with the skill-creator description-first contract or the value-lens block placement | Low | Med | BLUF already lives in the `description` field; the body BLUF is additive and must not duplicate or move the value-lens block |
| Scope is large for one spec | Med | Med | `/ai-autopilot` file-scoped decomposition; each file adapted in one pass (body + frontmatter together) |
