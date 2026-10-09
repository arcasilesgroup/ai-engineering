# Checkpoint 7 review

Goal: After the human approves the brainstorm, the generated plan opens in the checkpoint viewer and implementation starts without a second plan-approval stop; final app review remains required.

Acceptance:
- A human-approved brainstorm remains the start gate; the generated checkpoint plan opens in the existing viewer and the orchestrator proceeds without asking for a second plan approval.
- New plans use phase implementation, plan_approval approved, app_review not-started, and null reviewed refs; malformed or contradictory lifecycle state still fails closed.
- The final human app review and all existing reviewed-ref, merge, and removal protections remain required.
- Generated skill assets match their sources and focused lifecycle, workflow-handoff, typecheck, lint, and architecture checks pass.

Changed files:
- skills/ai-orchestrator/SKILL.md
- scripts/checkpoint-gate.py
- tests/test_checkpoint_gate.py
- tests/workflow-handoff.spec.ts

Verify:
- python3 tests/test_checkpoint_gate.py
- bun test ./tests/skills.spec.ts
- bun test ./tests/workflow-handoff.spec.ts
- bun scripts/gen-assets.ts
- bun test ./tests/embed-canon.spec.ts
- bun run build
- bun run typecheck
- bun run lint
- bun test ./tests/arch.spec.ts

## Debate mode — round 1

### F1 — High — New implementation lifecycle does not prove brainstorm approval
**Files:** `scripts/checkpoint-gate.py:525-542`, `tests/test_checkpoint_gate.py:317-320`

The hook accepts a first-write lifecycle with `phase: implementation` and `plan_approval: approved` solely from caller-supplied JSON. Neither lifecycle creation nor implementation dispatch checks `.ai-engineering/brainstorm.html` for the matching feature slug, `complete` status, explicit approval, and a fresh approval date. Thus a plan can be created with the accepted lifecycle while the brainstorm is absent, stale, or for another feature, and `[checkpoint ... implement]` is then authorized. The skill's prose gate does not make this persisted-state guard fail closed. U33 does not cover the new-plan branch: it first writes `initial_plan` (pending approval) to `selected_path`, then tests the approved state as a transition from that existing lifecycle. Require the new-plan approval path to be bound to a validated approved brainstorm and test a first write, plus absent/stale/wrong-slug brainstorm cases.

### F2 — Medium — The no-plan-stop contract conflicts and its regression check misses the prompt form
**Files:** `skills/ai-orchestrator/SKILL.md:13-16, 142-144, 238-239`, `tests/workflow-handoff.spec.ts:254-255`

The skill still says checkpoint review is a universal stop at the end of Phase 1 and its Lifecycle says `Stop` confirms the checkpoint plan, while the new-plan path says to proceed directly and only the resumed-legacy path should retain that stop. This leaves conflicting instructions in the orchestrator/resume contract. U34's negative check searches for `askuserquestion`, but the plan prompt is written as `ask_user_question`; its normalization also leaves underscores in `human _stop_ 1`, so these assertions cannot detect the actual legacy prompt form or a regression that adds it to the new-plan path. Scope the top-level stop contract to pending legacy plans and test that the fresh approved-brainstorm path has no approval prompt while preserving the legacy prompt.

## Debate mode — round 2

### F1 — High — A fresh plan can enter the legacy pending path and bypass brainstorm validation
**Status:** Open
**Files:** `scripts/checkpoint-gate.py:578-625`, `scripts/checkpoint-gate.py:500-530`, `tests/test_checkpoint_gate.py:295-320, 470-480`

The direct first-write bypass is fixed: the initial `implementation`/`approved` state now requires one matching feature stamp, a valid approval date within 14 days, and a matching `complete · <date>` status. The absent, stale, wrong-slug, and incomplete-status first-write cases are covered. But `check_lifecycle` still accepts `awaiting-plan-approval` as the first lifecycle state for any plan with no prior lifecycle, including a just-created plan. The transition from that state to approved implementation then succeeds without checking the brainstorm. I reproduced both calls in memory with no brainstorm file: `check_lifecycle(pending, {}, root)` followed by `check_lifecycle(approved, pending, root)` returns successfully. The current U17/U10 cases exercise those permissive steps separately. A new plan can therefore impersonate a resumed legacy plan and bypass the fresh brainstorm gate; distinguish a truly pre-existing legacy plan from a new plan before allowing the pending first-write route.

### F2 — Medium — Resolved in the orchestrator contract
**Status:** Resolved

The universal Phase 1 stop and lifecycle description are now scoped to resumed pending legacy plans. U18 checks the exact `ask_user_question` prompt in that legacy branch and its absence from the fresh-plan branch; U34 checks the approved brainstorm → viewer → implementation sequence and retained app review before merge. The focused `skills.spec.ts` and `workflow-handoff.spec.ts` run passed: 35 tests, 0 failures.

### F3 — Medium — The brainstorm skill still promises a second human stop
**Files:** `skills/ai-brainstorm/SKILL.md:303-304`, `tests/workflow-handoff.spec.ts:215-265`

The upstream brainstorm handoff still says “the plan approval downstream is STOP 1” and “One idea, two stops, both human.” That directly contradicts the new orchestrator contract, which says a fresh approved brainstorm proceeds without another plan-approval question. U34 only checks the orchestrator skill, so the cross-skill contradiction remains undetected. Update that handoff contract and add a cross-skill regression assertion; this round was restricted from changing docs.

F1’s wrong-slug and stale direct-initialization attempts are blocked by the new checks; F1 remains open solely for the pending-first-write route. Contradictory initial app-review state remains rejected, legacy plans with existing pending lifecycle retain their approval transition, and the final human app review/reviewed-ref protections remain intact. The source asset references for `skills/ai-orchestrator/SKILL.md` and `scripts/checkpoint-gate.py` resolve to bytes identical to both sources; no code, tests, checkpoint JSON, or learning logs were changed.

## Debate mode — round 3

### F1 — High — Legacy fallback is not bound to a valid same-slug prior plan
**Status:** Open
**Files:** `scripts/checkpoint-gate.py:758-790`, `scripts/checkpoint-gate.py:578-625`, `tests/test_checkpoint_gate.py:389-405`

The first-write self-approval from an absent file is now blocked, and the valid same-slug legacy continuation is tested. However, `had_plan` is true for any parsed object whose `checkpoints` member is a list; the prior plan’s slug and checkpoint validity are not checked before that boolean is passed as `has_prior_plan`. `lifecycle_plan_path_error` validates only the new plan. I reproduced a prior plan with `slug: other` and a checkpoint list authorizing a pending lifecycle for `slug: demo`, followed by an approved implementation transition with no brainstorm. Bind the legacy exception to a valid pre-existing plan for the same slug/path, and test a wrong-slug (and malformed) prior plan.

### F3 — Medium — Resolved in skill text; cross-skill wording is now aligned
**Status:** Resolved

The brainstorm handoff now states that a new plan proceeds without a second approval and preserves the legacy checkpoint and final app-review stops. A search found no remaining “plan approval downstream,” “two stops,” or “STOP 1” claim in the skills. The updated U34 assertion checks the cross-skill handoff.

### F4 — Medium — Cross-skill regression test would allow the old contradiction back
**Status:** Open
**Files:** `tests/workflow-handoff.spec.ts:215-275`

U34 asserts that the brainstorm handoff contains the corrected positive statements, but it never asserts that the old STOP 1 / “two stops” statement is absent. Reintroducing the old sentence alongside the new one would still satisfy every new assertion, leaving the exact F3 contradiction undetected. Add a negative assertion against that obsolete plan-approval stop language in the normalized handoff section.

Round 3 checks: `bun test ./tests/skills.spec.ts ./tests/workflow-handoff.spec.ts` passed (35 tests, 0 failures); the checkpoint records all nine Gate 1 commands passing after the fix. In-memory probes confirmed no-prior pending initialization is denied and exposed the wrong-slug legacy classification above. Current embedded references for both skills and `checkpoint-gate.py` resolve to bytes identical to their source files. Final app review/ref assertions remain present; only this review thread was changed.
