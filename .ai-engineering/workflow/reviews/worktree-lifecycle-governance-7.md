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
