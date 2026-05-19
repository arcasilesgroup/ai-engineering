---
spec: spec-145
title: Standard Flow Executor Routing
status: approved
effort: medium
summary: Add deterministic executor routing so plans state whether the next command is /ai-build or /ai-autopilot, remove host-capacity admission from the standard flow, and add one bounded quality-remediation pass for executor quality loops.
---

# Spec 145 - Standard Flow Executor Routing

## Summary

The governed chain currently makes the operator discover the right executor late: a multi-concern plan can be tried with `/ai-build --no-hitl`, refused, then retried through `/ai-autopilot`. The first part is a framework routing problem and belongs in ai-engineering: the plan must say whether the next command is `/ai-build` or `/ai-autopilot`. The host-capacity admission layer proposed earlier is out of scope because local resource telemetry is not reliable enough to be a framework execution gate and ai-engineering must not own local machine resource control. The same standard-flow fix also needs a bounded recovery path after the final quality loop: executor quality gates may repair quality-loop blocker/critical/high findings once, but must fail loud after the terminal reassessment.

## Goals

- Add deterministic executor metadata to newly generated `plan.md` files so `/ai-plan` records exactly one next executor: `build` or `autopilot`.
- Print the recommended command at the end of `/ai-plan` and stop; the operator remains the approval gate and manually invokes the command.
- Use `plan.md` frontmatter `status` as the single source of truth for plan approval; do not add a duplicate approval field.
- Update `/ai-build` and `/ai-build --no-hitl` so new plans use `execution_route.executor` as the authoritative single-concern/multi-concern gate; heading-shape checks become legacy diagnostics only.
- Update `/ai-autopilot` Step 0 so host probe data does not block execution; local host capacity is not an ai-engineering admission-control responsibility.
- Keep bounded execution/concurrency configuration as implementation mechanics, but remove host-admission states (`fanout`, `serial`, `deferred`) and any host-capacity go/no-go decision from the standard flow.
- Add tests for the spec-144 failure sequence: multi-concern work receives `executor: autopilot`, `/ai-build --no-hitl` refuses with the recommended command, and `/ai-autopilot` no longer aborts solely because host telemetry reports unsafe fan-out.
- Record executor-route decisions in the audit chain using existing `framework_operation` events; do not add new top-level event kinds.
- Add one bounded quality-remediation pass to `/ai-build` and `/ai-autopilot` quality loops: fix only blocker/critical/high findings that are concrete, scoped, and attributable to the current quality-loop evidence; then run one terminal final reassessment.
- Require cross-platform reproducers for quality remediation evidence: prefer Python/pytest/uv/ai-eng commands, avoid POSIX-only pipelines unless a Windows PowerShell equivalent is reported.
- Persist `/ai-autopilot` quality remediation state in the runtime manifest so `--resume` can tell whether the single remediation budget has already been consumed.

## Non-Goals

- Do not introduce `/ai-execute` or any new public execution command.
- Do not auto-dispatch from `/ai-plan`.
- Do not implement host-admission states, host deferral packets, manual host overrides, heartbeats, or background retries.
- Do not hard-rename `ok_to_dispatch` to `ok_to_fanout`; the host predicate no longer participates in the standard flow gate.
- Do not make ai-engineering responsible for deciding whether the operator machine has enough RAM, swap, or pressure headroom.
- Do not mutate historical audit/state records solely to remove old host-probe wording.
- Do not implement the parked spec-144 README/rename plan as part of this spec.
- Do not add infinite retry, multi-round quality chasing, automatic full-suite reruns, or a second remediation pass.
- Do not let `/ai-autopilot` re-decompose, re-plan, or reopen all waves as part of quality remediation.
- Do not repair broad baseline debt or cross-repo findings unless the quality-loop finding is a concrete gate-owned artifact required for the current source-tree gate.

## Decisions

### D-145-01 — Scope the fix to executor routing only

This spec fixes only the framework decision between `/ai-build` and `/ai-autopilot`. Host-capacity admission, `fanout`/`serial`/`deferred` states, host deferral packets, and host telemetry overrides are removed from scope.

**Rationale**: The user explicitly rejected host admission as over-engineering. Local host telemetry can be inaccurate, and ai-engineering does not block work based on resource-control data it does not own.

### D-145-02 — Keep the public command surface unchanged

The public commands remain `/ai-plan`, `/ai-build`, and `/ai-autopilot`. `/ai-plan` prints the recommended next command and stops.

**Rationale**: A new `/ai-execute` command would add orchestration surface area without solving the actual problem. The missing piece is visible route metadata, not another command.

### D-145-03 — Store executor metadata in `plan.md`

New plans include an `execution_route` object with `version`, `spec`, `executor`, `automation`, `concern_count`, `estimated_files`, `reason`, and `safe_next_command`. `executor` is limited to `build` or `autopilot`.

**Rationale**: The plan is the execution contract and the right place for a reviewable next-command recommendation. Runtime host measurements do not belong in this metadata.

### D-145-04 — Use `status` as the only plan approval source

Plan approval is represented only by `plan.md` frontmatter `status`: `draft` means not executable; `approved` means execution may proceed through the recorded executor.

**Rationale**: SSOT-PD forbids duplicate writable truth. A second approval field inside `execution_route` would drift from plan lifecycle state.

### D-145-05 — Make route metadata authoritative for no-HITL

For newly generated plans, `/ai-build --no-hitl` reads `execution_route.executor` and plan `status` first. If `executor: autopilot`, it refuses loudly and prints `/ai-autopilot`. Heading-count checks remain only as legacy diagnostics when route metadata is missing.

**Rationale**: Heading shape can misclassify semantically multi-concern work. Plan-time metadata is explicit, deterministic, and reviewed before execution.

### D-145-06 — Remove host probe as an autopilot hard gate

`/ai-autopilot` Step 0 no longer aborts solely because `ai-eng host probe` returns `ok_to_dispatch: false`. Host probe may remain a diagnostic command, but it is not a standard-flow admission gate.

**Rationale**: The current host gate blocked spec-145 itself on data the user considers unreliable and outside framework responsibility. ai-engineering can bound its own orchestration mechanics, but it does not own local resource admission.

### D-145-07 — Keep route audit evidence simple

Executor classification emits or records a `framework_operation` detail such as `execution_routed`; no new top-level event kind is required.

**Rationale**: The existing audit schema already supports lifecycle and operation evidence. Adding event kinds for a simple route recommendation creates unnecessary schema churn.

### D-145-08 — Treat spec-144 as the routing regression

Tests and examples encode the observed spec-144 route problem: multi-concern work belongs to `/ai-autopilot`, and `/ai-build --no-hitl` must refuse with the correct next command.

**Rationale**: The concrete failure was late executor discovery. Tests tied to that case prevent the fix from drifting back into heuristic heading checks.

### D-145-09 — Allow exactly one bounded quality-remediation pass

`/ai-build` and `/ai-autopilot` may fix quality-loop blocker/critical/high findings once when the finding has concrete evidence, a narrow reproducer, and a localized patch. The final reassessment is terminal: remaining blocker/critical/high findings STOP and escalate.

**Rationale**: A single bounded pass improves speed for obvious quality blockers without reintroducing open-ended auto-retry loops.

### D-145-10 — Make autopilot remediation manifest-aware

`/ai-autopilot` records `quality_remediation.max_attempts: 1`, `used`, finding owners, reproducers, and final reassessment status in `.ai-engineering/runtime/autopilot/manifest.md`.

**Rationale**: Autopilot spans sub-specs and waves, so recovery state must survive `--resume` and cannot live only in agent memory.

### D-145-11 — Require multi-IDE and cross-OS propagation

Quality remediation contract text is authored in canonical `.claude/` skills, regenerated into root IDE mirrors and installer templates, and requires platform-neutral reproducers or Windows PowerShell equivalents when POSIX shell pipelines are used.

**Rationale**: The framework supports multiple IDE surfaces and operating systems. Recovery guidance that only works in one IDE or shell creates hidden drift.

## Risks

- **Route metadata drift after plan edits**: Plan content can change after route classification. Mitigation: validate route metadata during plan verification or require `/ai-plan` regeneration when concern/file signals change.
- **Autopilot resource use becomes operator-managed**: Removing host admission means ai-engineering no longer blocks based on local pressure/swap telemetry. Mitigation: keep ordinary bounded concurrency knobs and let the operator/OS manage local capacity.
- **Route-only scope is mistaken for less governance**: Removing host admission could be read as weakening all gates. Mitigation: keep spec approval, plan approval, no-HITL refusal, single-round quality, secrets, and policy gates unchanged.
- **Legacy plans lack route metadata**: Older plans still need understandable behavior. Mitigation: keep legacy heading-shape diagnostics only for plans without `execution_route`.
- **Audit schema misuse**: Implementers can accidentally add route-specific top-level event kinds. Mitigation: tests assert `framework_operation/detail.operation=execution_routed` or equivalent existing-kind usage.
- **Remediation becomes an infinite retry loop**: A quality fix pass can drift into repeated patching. Mitigation: tests and docs require `max_attempts: 1`, final reassessment, and no second remediation pass.
- **Autopilot remediation loses ownership**: Multi-concern fixes can patch the wrong sub-spec. Mitigation: Phase 5b maps findings to `sub-NNN`, `integration`, or `shared` before editing.
- **Cross-OS reproducers are shell-specific**: POSIX-only commands can fail on Windows. Mitigation: require platform-neutral commands or a Windows PowerShell equivalent in reports.

## References

- doc: `.ai-engineering/specs/drafts/standard-flow-execution-admission-control-brief.md`
- doc: `.ai-engineering/specs/archive/spec-144-readme-rewrite-and-branch-cleanup-rename/spec.md` documents the README Rewrite and Branch Cleanup Rename case that exposed late executor discovery.
- doc: `CONSTITUTION.md` requires deterministic gates before probabilistic execution and forbids compatibility shims for renamed content.
- doc: `docs/persistence-doctrine.md` defines SSOT-PD and the Markdown/state/audit storage split.
- doc: `.ai-engineering/reference/plan-schema.md` defines `plan.md` lifecycle states.
- doc: `src/ai_engineering/templates/project/CANONICAL.md:47-60` documents `/ai-build` as executor and `/ai-autopilot` as large-work wrapper.
- doc: `.claude/skills/ai-plan/SKILL.md:19-32` writes `plan.md` and stops before execution.
- doc: `.claude/skills/ai-build/handlers/no-hitl.md:18-29` restricts no-HITL to approved single-concern plans.
- doc: `.claude/skills/ai-autopilot/SKILL.md:26-44` routes large work to autopilot but currently blocks on host probe.
- doc: `.claude/skills/ai-build/handlers/quality.md` defines the bounded build quality-remediation pass.
- doc: `.claude/skills/ai-autopilot/handlers/phase-quality.md` defines manifest-aware Phase 5b remediation.

## Open Questions

None. The scope correction removes host admission, leaves executor routing as the admission decision, and bounds quality-loop remediation to one finding-scoped pass.
