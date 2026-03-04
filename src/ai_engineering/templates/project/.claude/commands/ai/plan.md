Orchestrate planning pipeline.

MODE SELECTION:
- `--plan-only`: Read and execute `.ai-engineering/skills/plan/SKILL.md` (advisory only, zero writes)
- Default: Activate agent persona in `.ai-engineering/agents/plan.md` (full planning, creates spec, STOPS before execution)

PIPELINE RULES (default mode):
1. Auto-classify pipeline (full | standard | hotfix | trivial) from change scope.
   User override: `--pipeline=<type>`.
2. Execute ALL steps for the classified pipeline sequentially. NEVER skip steps.
3. Skills that MUST participate: ai:discover, ai:risk, ai:spec.
4. For full/standard: spec creation is MANDATORY.
5. STOP after producing execution plan. Do NOT dispatch or execute.
   Tell user: "Plan ready. Run `/ai:execute` to begin."

$ARGUMENTS
