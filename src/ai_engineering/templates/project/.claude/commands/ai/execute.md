Execute an approved plan by dispatching specialized agents.

Activate the agent persona defined in `.ai-engineering/agents/execute.md`. Follow all behavior steps and boundaries.

PRECONDITIONS:
1. Active spec must exist (`.ai-engineering/context/specs/_active.md` points to valid spec)
2. Plan must have agent assignments in plan.md
3. If no active spec: STOP → "No active plan. Run `/ai:plan` first."

$ARGUMENTS
