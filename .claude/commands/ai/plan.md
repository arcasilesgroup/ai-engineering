Orchestrate planning pipeline and work-item dispatch.

Activate the agent persona defined in `.ai-engineering/agents/plan.md`. Follow all behavior steps and boundaries.

MANDATORY PIPELINE RULES:
1. Classify input (raw-idea | structured-request | pre-made-plan) before entering the pipeline.
2. Execute ALL 6 Default Pipeline steps sequentially. NEVER skip steps 2-6.
3. Adapt step depth by input type — but NEVER reduce a step to zero.
4. Skills that MUST participate: ai:discover, ai:arch-review, ai:prompt, ai:risk, ai:test-plan, ai:spec, ai:work-item.
5. Spec creation (step 4) is ALWAYS mandatory for non-trivial work.
6. Pause for user approval between step 3 and step 4 unless input is pre-made-plan with no new risks.

$ARGUMENTS
