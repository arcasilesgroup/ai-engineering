# Driver-tier posture: Registry-Gated Progressive Enhancement (RGPE) — research brief

> Produced 2026-07-16 by a 16-agent research workflow (3 internal audits, 3 cited
> external research sweeps, 3 independent design proposals, 3-judge panel,
> 4 adversarial claim verifications; 1.43M tokens). Feeds a spec-185 amendment
> via /ai-brainstorm. Judges ranked RGPE first unanimously (8.5 / 8.5 / 8).

## Question

Should ai-engineering be designed floor-first-universal (default posture assumes
a weak open-weight driver; frontier models just run the same rails, no
detection/branching), or tier-adaptive as spec-185 currently plans (detection +
conditional knobs)?

## Answer

Neither pole. The evidence splits the surface cleanly:

1. Everything deterministic and artifact-shaped is best-for-everyone, not merely
   weak-tolerable — ship it always-on with zero detection. A controlled GAIA
   study found frontier models gain MOST from structured scaffolds on hard
   tasks; the repo's own patch-ready-plan mechanism is already floor-first and
   is its most successful robustness feature.
2. The genuinely variable residue (autopilot block, governed-git/Ralph
   enforcement, verification depth, decomposition) varies per MODEL, not per
   tier — so the conditional signal should be a small committed per-model
   capability registry (the aider/OpenHands pattern, dominant across every
   surveyed shipping framework), not a substring heuristic ladder, not runtime
   probes, and not tier-variant prose.
3. Remaining adaptivity is failure-triggered (ADaPT-shaped): deterministic-gate
   failure → decompose finer → escalate → stop. Universal mechanism; naturally
   a no-op on frontier.

Spec-185's ~14-measure conditional framing shrinks to 5 named branch points.
The four-knob dial (D-185-06) becomes: one tier-gated knob (verification
depth), one universal deterministic post-check (action schema), one adaptive
mechanism (granularity), one deletion (prompt density).

## Adversarially verified claims

- REFUTED — "structured output penalizes reasoning MORE on frontier models."
  A format penalty exists (Tam et al. 2024, arxiv 2408.02442, ~10-15%) but the
  dottxt rebuttal shows prompting reverses it, and "The Format Tax" (2026)
  shows the penalty is capability-dependent in the OPPOSITE direction:
  open-weight models pay the tax, frontier pays near-zero. Consequence:
  tightening schemas on weak tiers is exactly backwards; the universal optimum
  is decouple-reasoning-from-format + deterministic extract-then-validate.
  What DOES hold: over-prescriptive procedural prompts hurt strong reasoning
  models (OpenAI + Anthropic vendor guidance; "Mind Your Step": forced CoT
  costs o1-preview up to 36.3pp) — so no maximally-explicit universal prose.
- HOLDS — peer frameworks use STATIC per-model registries with floor-safe
  unknown defaults (aider model-settings: whole-file edits + warning for
  unknown; OpenHands supported-models over litellm; AutoGen ModelInfo).
  Cline/Roo are the natural experiment: XML-universal floor prompting was
  abandoned as a frontier tax. Runtime probes ship in no surveyed framework.
- HOLDS — floor-level verification depth on frontier ≈ waste: self-consistency
  gains collapse to 0.4-1.6% (sometimes negative) at linear cost on modern
  models; weak-verifier ensembles (+14.5%) and repeated sampling are
  compute-optimal for weak models. Intrinsic self-correction degrades ALL
  tiers; deterministic external gates are the universal layer.
- HOLDS — hard capability floors are real: scaffolded Qwen3-8B doubles its
  AppWorld score yet stays ~40pp below GPT-4o ("Three Roles, One Model",
  arxiv 2604.11465); small models have a non-positive generation-verification
  gap (cannot self-check); long-horizon execution is where the gap
  concentrates. Supports hard-block (D-185-04) over degrade-in-place.

## Cost ground truth (this repo's NDJSON, PR #639 session)

Full-roster review = 185.6K tokens / ~7.6 min (8 agents, ~20.6K each);
validators ~10.1K each; whole review chain 245K. Forced `--full` +62K tokens
+3-5 min; second adversarial verifier pass +20-30K tokens +2-4 min SERIAL.
Always-on for a frontier operator: ~87-115K tokens (~2x the LLM-judgment slice
of the quality loop) and +15-30 serial minutes per PR — the real tax is
latency on a fail-loud path, not dollars (~5% of an observed 1.86M-token day).

## Bugs found in landed C0 (fix in the amendment)

1. `AIENG_MODEL_TIER` double-booked across both axes: ai-build SKILL.md step 2c
   passes dispatch tiers through the same env var the driver resolver treats
   as capability override (src/ai_engineering/state/driver_tier.py:30). Benign
   only while the value sets don't overlap. Fix: new `AIENG_DRIVER_TIER`;
   `AIENG_MODEL_TIER` returns exclusively to the dispatch-effort axis.
2. mimo maps to standard-floor, so `is_below_standard_floor()` grants it
   autopilot — contradicts D-185-13 (never autopilot until independently
   benchmarked). Tier alone cannot express "unproven"; needs a flag.
3. Bare-family fallback needles (`glm` → frontier) resolve UPWARD for unknown
   future weak variants — inverts the conservative default. Rule: bare-family
   needles may only resolve downward.
4. The research brief the spec cites ([14][15][S19]) is absent from the entire
   git history — rationale unauditable. Pin the external citations above into
   spec References.
5. Dormant-axis precedent: model_tier dispatch enforcement was shipped
   observe-first and the flip never happened; agent frontmatter (`model: opus`)
   and skill frontmatter (`model_tier: haiku`) already drifted. Lesson: every
   conditional measure needs a deterministic enforcement point (hook/CLI/lint);
   prose is advisory only — weak drivers are exactly the ones that ignore prose.

## RGPE design

### Layer 1 — always-on deterministic core (no detection)

- D-185-07 checkpoint artifacts, D-185-11 explicit-state, D-185-12 security
  plane: as specced, universal.
- FLIP to universal (currently misfiled floor-only): T-3.2 §0 bootstrap digest
  + machine-verifiable ack (~300-800 tokens/session; frontier skips bootstrap
  too); T-4.5 rg/grep -n read steering (token-negative for every tier).
- Knob 2 reframed: ONE fixed action-step schema in ai-plan task blocks for all
  tiers, enforced by deterministic post-parse (extract-then-validate) in the
  gate plane. Kills the format-tax knob.
- D-185-05 cascade respecified universal: on deterministic-gate failure,
  escalate to highest-available configured tier, else stop-and-escalate.
  No-op at frontier; sidecar read only for TARGET selection.
- Knob 1 (prompt density) DELETED. No per-tier prose, no explicit rewrite;
  mirror diet and skill line budgets stand. Universal explicitness lives in
  artifacts (plans, task blocks, digest), the repo's proven floor mechanism.

### Layer 2 — the conditional signal: committed per-model registry

`.ai-engineering/config/driver-registry.json` (canonical config store; the
runtime sidecar becomes its labeled derived cache, rebuilt at SessionStart).
Entry: model-id pattern, `tier` (D-185-01 vocabulary as coarse fallback), and
exactly THREE orthogonal flags: `long_horizon`, `agentic_proven`,
`native_tool_schema`. Rules: unknown model → stretch-floor + all-false flags +
ONE SessionStart warning (warn-and-conservative, never silent, never hard-fail);
bare-family needles resolve downward only. Resolver reads registry first,
keeps a minimal embedded bootstrap fallback, and exposes NAMED predicates
(`blocks_long_horizon()`, `enforces_deterministic_governance()`,
`needs_deep_verification()`) — no skill or hook ever does an inline tier
comparison (lint-guard this). Follow-up spec: `ai-eng driver calibrate`, an
OFFLINE deterministic probe suite (tool-call formatting, patch application,
schema adherence) that writes a registry entry with evidence — the concrete
exit from D-185-13's "until independently benchmarked".

### Layer 3 — five conditional branch points

1. Autopilot/long-horizon refusal: `not long_horizon OR below standard-floor`
   (fixes mimo). Warn-and-route via safe_next_command; operator override
   NDJSON-logged as explicit risk acceptance.
2. Governed-git hard-block + Ralph auto-block: `tier == stretch-floor` only
   (frontier AND standard-floor keep spec-182 advisory; preserves D-182-05).
3. Agentic tool-loop gate: `native_tool_schema == false` (gemma-class) →
   gated off tool loops or in-band synthesis + validation.
4. Verification depth (the one surviving tier knob): second fresh-context
   adversarial pass, forced review --full, self-consistency N>1 — below
   standard-floor only. GRAFT (judges, unanimous): plus an outcome-triggered
   backstop for ANY tier — attestation downgrade or ≥2 changeset-relevant
   deterministic-gate failures in-session arms `needs_deep_verification()`
   for the rest of the session (deterministic signal, cannot misclassify).
5. Decomposition granularity: default = current ai-plan sizing; stretch-floor
   starts one notch finer; further splitting is FAILURE-TRIGGERED (subtask
   fails its gate twice → split → cascade → stop), bounded by the
   AIENG_RALPH_MAX_RETRIES pattern.

Implementation rule: every conditional measure MUST have a deterministic
enforcement point. Prose is advisory only.

### Spec-185 deltas

Keep C0 as landed. Amend resolver: registry loader replaces `_FAMILY_TIERS` as
source of truth + flags + named predicates + `AIENG_DRIVER_TIER` (template-twin
byte parity + hooks-manifest regen + a registry-schema parity test in the same
PR). Plan: T-1.5/T-1.7 re-keyed onto named predicates; T-2.x unchanged
(conditional); T-3.2/T-4.5 flipped universal; knob-1 tasks deleted; knob-2
tasks reshaped to gate-plane post-validation; +2-4 tasks for registry/loader/
`ai-eng driver show|override`. Net build cost ≈ equal or lower than the
current plan. Land measurement rails (per-skill token accounting) alongside,
so the observe-then-enforce loop has data — the model_tier grace window shows
that loop can stall.

## Risks (bounded)

Registry staleness (degrades to floor+warning, never silent upward
misclassification); flag creep (cap at 3, spec decision to add); boundary
drift (named-predicates rule, lint-guarded); serving-flags misclassification
for self-hosted endpoints (OpenHands-documented; conservative defaults +
override + calibrate); failure-triggered decomposition thrash (retry-bounded);
five-surface parity trap (registry schema joins the four known twin surfaces).

## Key sources

- Tam et al. 2024, "Let Me Speak Freely?" — https://arxiv.org/abs/2408.02442
- dottxt rebuttal — https://blog.dottxt.ai/say-what-you-mean.html
- "The Format Tax" (2026): format penalty concentrates on open-weight models
- "Mind Your Step": forced CoT costs o1-preview up to 36.3pp
- OpenAI reasoning-model prompt guidance; Anthropic prompting guidance
  (prefer general instructions; dial back prescriptive scaffolds)
- aider model settings — https://aider.chat/docs/config/adv-model-settings.html
- OpenHands supported-models + serving-flags misclassification tracker
- Cline/Roo migration off XML-universal prompting (frontier tax)
- "Three Roles, One Model" — https://arxiv.org/abs/2604.11465 (scaffolded
  Qwen3-8B stays ~40pp below GPT-4o)
- Self-consistency collapse on modern models — https://arxiv.org/abs/2511.00751
- ADaPT as-needed decomposition (+20-28pp weak executors)
- Controlled GAIA scaffold study: frontier gains most from structure; benefit
  conditions on model family, not tier
- Internal: model-dispatch-policy.md:22-27; ai-build SKILL.md:28-32;
  driver_tier.py:30/:54/:56; test_skill_line_budget.py:63,103; session
  3e77825e NDJSON token rollups
