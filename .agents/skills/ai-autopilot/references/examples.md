# /ai-autopilot — Examples and detail

> Progressive disclosure (spec-131 closure H2): the SKILL.md body
> stays under the 120-line ceiling per spec-127 contract. Long-form
> examples and the failure-recovery / telemetry detail live here.

## Example 1 — autonomous end-to-end delivery

User: "implement spec-127 end to end"

```
/ai-autopilot "implement spec-127"
```

This is the correct executor when `.ai-engineering/specs/plan.md`
records `execution_route.executor: autopilot` and
`safe_next_command: "/ai-autopilot"`.

Phase 1 decomposes the spec into sub-specs, Phase 2 deep-plans them in
parallel, Phase 3 builds the dependency DAG, Phase 4 implements in
waves, Phase 5 runs the single quality loop (verify + guard + review
on full changeset), Phase 5b may consume one bounded
quality-remediation pass for finding-scoped blocker/critical/high
issues, and Phase 6 delivers via PR.

## Example 2 — resume after interruption

User: "resume the autopilot run that crashed yesterday"

```
/ai-autopilot --resume
```

Reads `.ai-engineering/runtime/autopilot/manifest.md`, identifies the
last completed phase, and re-enters at the correct state without
re-doing finished work.

## Example 3 — backlog run from GitHub Issues

User: "run all open issues with the ready-to-work label, no human
checkpoints"

```
/ai-autopilot --backlog --source github "label:ready-to-work is:open"
```

Normalises issues into the run model, performs baseline `ai-explore`
of the repo, builds an overlap-aware DAG, dispatches bounded
`ai-build` packets per item, runs per-item + integration gates, and
delivers via `ai-pr` (D-127-12; replaces the legacy `/ai-run` skill).

## Failure recovery and telemetry

| Scenario | Recovery |
| --- | --- |
| Phase 2 agent fails | Retry once → mark `plan-failed`; evaluate subset viability. |
| Build agent fails in Phase 4 | Mark sub-spec `blocked`; cascade-block dependents; continue wave. |
| Initial quality assessment finds blocker/critical/high | Enter Phase 5b once if findings are scoped and `quality_remediation.max_attempts: 1` is unused. |
| Final reassessment still has blocker/critical/high | STOP. Do NOT create PR. Escalate to user. |
| Plan routes to `/ai-build` | STOP and run `/ai-build`; the plan route is the framework executor contract. |
| Mid-pipeline crash | Run `/ai-autopilot --resume`. |
| Final cleanup fails | Warn but do not block — PR is already delivered. |

Rollback: `git reset --soft HEAD~N` where `N = wave + quality-fix
commits`. Telemetry events fire per phase transition:
`autopilot.{started,decompose_complete,deep_plan_complete,dag_built,subspec_complete,quality_round,quality_remediation,subspec_failed,final_verify,pr_created,done}`.

## Common mistakes

Do not run on draft or under-scoped specs, cross repositories, carry
context between sub-specs, hand-edit mirrors, use POSIX-only
reproducers without a Windows PowerShell equivalent, or keep patching
after the final reassessment says escalate.
