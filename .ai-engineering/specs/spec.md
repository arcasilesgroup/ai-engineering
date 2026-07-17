---
spec: spec-185
title: "Open-Model Resilience, amended: observe-first driver-tier telemetry"
status: draft
effort: small
summary: "Amendment (D-185-15): spec-185 collapses to the landed driver-tier telemetry plus two one-line fixes (AIENG_DRIVER_TIER split, mimo to stretch-floor); all adaptive behavior is removed, re-entering only when the sidecar observes a real non-frontier driver."
---

## Summary

spec-185 originally planned a detection-and-adaptation layer: a tier
resolver, four adaptation knobs, hard gates below a capability floor, an
escalation cascade, and five delivery concerns (C0-C4). C0 (resolver,
SessionStart sidecar, additive enum widening, parity gates) is merged.
Post-approval research (16-agent workflow: 3 internal audits, 3 cited
external sweeps, 3 design proposals, 3-judge panel, 4 adversarial
verifications; brief at
`.ai-engineering/specs/drafts/driver-tier-rgpe-brief.md`) plus a
KISS/YAGNI review changed the verdict: every adaptive measure targets a
driver class the operator does not run today, and the framework's own
history (the dispatch-effort axis shipped observe-only and its enforcement
flip never happened) shows speculative conditional machinery goes stale.
This amendment cuts spec-185 to what is real: the landed telemetry
substrate, two one-line correctness fixes, and an explicit written trigger
for the future spec that adaptation actually deserves. Every session
already records `{model_id, tier}` to
`.ai-engineering/runtime/driver-tier.json`; when that file one day names a
non-frontier driver in real use, the follow-up spec starts from observed
failure data, not projections.

## Goals

- Driver-tier telemetry per session (LANDED, C0): vendor-neutral tier
  vocabulary, resolver with conservative unknown default, atomic
  SessionStart sidecar, hook/package/template parity gates, `driver_tier`
  stamped into the `session_started` audit event.
- Dedicated `AIENG_DRIVER_TIER` override for the driver-capability axis;
  `AIENG_MODEL_TIER` returns exclusively to the dispatch-effort axis
  (closes the double-booking latent bug: `driver_tier.py:30` vs the
  ai-build step-2c dispatch convention).
- Unproven-agentic models resolve to the conservative floor: mimo demoted
  `standard-floor` -> `stretch-floor` in all three map copies (honors the
  original D-185-13 intent: never trust self-reported agentic strength).
- Ship PR #639 and consolidate the spec.

## Non-Goals

- NO adaptation knobs (prompt density, output-schema constraint,
  decomposition granularity, verification depth). Deleted, not deferred.
- NO tier-gated blocks (autopilot refusal, governed-git hard-block, Ralph
  auto-on) and NO escalation cascade. The `is_below_standard_floor`
  predicate stays in the codebase as landed, unconsumed.
- NO per-model capability registry, flags, or `ai-eng driver calibrate`.
- NO universal-hardening measures inside this spec (bootstrap digest,
  rg-steering, action-schema post-validation, checkpoint-artifact
  hardening). Each is an independent improvement that earns its own small
  spec on its own evidence — none needs the tier system.
- NO C1-C4 concern waves and no `/ai-autopilot` delivery; the amended
  scope is a single small concern.

## Decisions

- **D-185-15 — Observe-first amendment; adaptive scope removed.** The
  adaptive/conditional program of the original spec (former D-185-04
  autopilot hard-block, D-185-05 cascade, D-185-06 four knobs, D-185-07/08
  quality conditionals, D-185-09 governance flips, D-185-10 tier-aware
  context delivery, D-185-11 as a tier measure, D-185-13 gating, D-185-14
  autopilot delivery) is superseded and removed from scope. The written
  re-entry trigger: when `.ai-engineering/runtime/driver-tier.json`
  records a non-frontier driver in real working sessions, a new spec is
  brainstormed FROM the failures those sessions actually exhibit.
  **Rationale**: no non-frontier driver exists in this repo's usage today,
  so every conditional branch would ship as dead code; the repo's own
  dispatch-axis precedent (observe-only flip never happened,
  `model-dispatch-policy.md:22-27`) shows speculative enforcement
  machinery stalls; adversarially-verified research (RGPE brief) found the
  only tier-conditional measure with strong evidence is verification
  depth, which is worthless without a weak driver to apply it to.
  Observation costs one JSON write per session and is already paid.

- **D-185-16 — Dedicated `AIENG_DRIVER_TIER` env override.** The
  driver-capability resolver override moves off `AIENG_MODEL_TIER` (which
  the dispatch-effort axis already uses in ai-build step 2c) onto its own
  `AIENG_DRIVER_TIER` variable, in the package resolver, hook mirror, and
  template twin, with the hooks-manifest sha regenerated.
  **Rationale**: one env var serving two axes the spec itself forbids
  conflating is a latent silent-bypass bug — benign today only because the
  value sets do not overlap; a one-line rename closes it permanently.

- **D-185-17 — Unproven models map to the conservative floor.** mimo
  demotes to `stretch-floor` in `_FAMILY_TIERS` (package, hook, template).
  **Rationale**: the original D-185-13 said unproven agentic claims are
  never trusted, yet the landed map granted mimo `standard-floor`, which
  the below-floor predicate would translate into full trust; with tiers as
  the only signal, "unproven" and "floor" must coincide — one line
  enforces the stated policy.

- **D-185-01/02/03 — Landed C0 substrate, kept as-is.** Vendor-neutral
  ordered tier vocabulary (additive enum widening), strict auto-detection
  persisted to the disk sidecar with escape-hatch override, and the single
  vendor-agnostic model-id map with conservative unknown default — all
  merged with parity gates and wiring tests in PR #639.
  **Rationale**: sunk, correct, hot-path-cheap (one JSON write at
  SessionStart), and the telemetry is precisely what makes the D-185-15
  re-entry trigger observable.

- **D-185-12 — Security boundary tier-invariant.** Unchanged and now
  trivially satisfied: no behavior conditions on tier anywhere, so
  deny/CRITICAL gates cannot weaken by construction.
  **Rationale**: the amendment's strongest property — removing all
  conditional behavior removes the entire class of tier-downgrade attack
  surface the original spec had to defend against.

## Risks

- **A weak driver is used before the future spec exists.** Telemetry-only
  means no guardrails adapt. Accepted: the sidecar plus the
  `session_started` audit event make this visible immediately, and the
  conservative default (`stretch-floor` for unknown ids) means
  misclassification errs downward, never upward.
- **Observe-then-act stalls (in-repo precedent).** The dispatch axis's
  enforcement flip never happened. Mitigation: D-185-15 writes the
  re-entry trigger into the spec record itself, and the trigger is a
  concrete observable artifact (sidecar content), not a policy review.
- **PR #639's body promises C1-C4.** The draft PR's integrity report
  names follow-on concerns this amendment deletes. Mitigation: update the
  PR body before marking ready; the amendment supersedes the plan.
- **Deleted research value.** The RGPE brief's universal-hardening
  findings (digest, rg-steering, schema post-validation) are evidence-backed
  and now homeless. Mitigation: the brief stays committed in
  `specs/drafts/`; each item is a candidate future micro-spec.
