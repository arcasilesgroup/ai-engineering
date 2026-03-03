Orchestrate planning pipeline and work-item dispatch.

Activate the agent persona defined in `.ai-engineering/agents/plan.md`. Follow all behavior steps and boundaries.

MANDATORY: Execute the Default Pipeline steps 1-6 sequentially.
After the user approves the plan, you MUST execute step 4 (invoke /ai:spec to create
branch + scaffold spec.md/plan.md/tasks.md) before proceeding to dispatch.
Do NOT skip spec creation — it is required for traceability and governance.

$ARGUMENTS
