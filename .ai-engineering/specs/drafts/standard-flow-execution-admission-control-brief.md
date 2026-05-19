---
title: Standard Flow Execution Admission Control
status: draft
audience: framework dev + operator
branch: codex/standard-flow-execution-admission-control
length_estimate: medium
authoring_style: research-backed diagnostic
principles_required: ["§10.1 KISS", "§10.5 TDD", "§10.6 SDD", "§10.7 Clean Code", "§10.8 Hexagonal Architecture"]
delivery_mode: spec-brief
mantra: "One command routes, one gate explains, no unsafe fan-out."
---

# Standard Flow Execution Admission Control Brief

## 1. Vision

The standard execution flow should never make an operator follow the documented chain and then discover, step by step, that each next command is invalid. The target state is a deterministic execution-admission layer that reads the approved spec, plan metadata, and host capacity once; chooses the safe route; either executes through the right lane or writes a resumable deferral packet; and always explains the exact gate, threshold, measured value, audit event, and next safe command.

## 2. Scope Boundary

In scope:

- Add an execution route contract to the active plan surface so `plan.md` states whether the next executor is direct build, no-HITL build, autopilot fan-out, autopilot serial, or deferred execution.
- Replace heading-shape inference in no-HITL eligibility with a deterministic route classifier based on plan metadata, concern count, estimated file count, and host admission.
- Align host capacity semantics across `HostProbe.ok_to_dispatch`, `resolve_wave_cap`, `/ai-build`, and `/ai-autopilot` so "unsafe to fan out" is distinct from "unsafe to do any work".
- Improve operator recovery UX with one structured envelope: `Reason`, `Measured`, `Threshold`, `Decision`, `Safe next command`, `Resume state`.
- Preserve the existing single-round quality loop, no hidden auto-retry, hard audit trail, and no bypass of security gates.

Out of scope:

- Running spec-144 implementation as part of this brief.
- Weakening host-safety thresholds to force work through a swap-heavy machine.
- Introducing a new public command (e.g. `/ai-execute`) or renaming `/ai-build` / `/ai-autopilot`; the public command surface stays at `/ai-build` and `/ai-autopilot`, with `/ai-plan` printing the recommended one.
- Adding a compatibility alias for renamed commands or stale route fields.
- Changing the regulated quality gates, risk-acceptance ledger, or the canonical NDJSON audit chain.
- Rewriting the entire canonical chain unless the spec phase explicitly approves a chain wording update.

## 3. Diagnostic Snapshot

The current documented chain says `/ai-build` executes the plan and `/ai-autopilot` wraps the chain for specs with at least three concerns or ten file changes, but the operator has to discover that route only after a build refusal rather than from the plan itself (`src/ai_engineering/templates/project/CANONICAL.md:49-60`, `AGENTS.md:49-60`).

The active spec is approved while the active plan is still `status: draft`, so the state model can present "approved spec" and "draft plan" at the same time (`.ai-engineering/specs/spec.md:1-10`, `.ai-engineering/specs/plan.md:1-9`). This is valid by schema because plan lifecycle says `draft` is first emission and `approved` is the build-executable state (`.ai-engineering/reference/plan-schema.md:85-91`). The plan linter accepts `draft` as an active status with checkbox tasks; it validates shape rather than approval intent (`tools/spec_lint/checks/plan.py:20-31`, `tools/spec_lint/checks/plan.py:151-163`).

The active plan identifies itself as full, cross-surface work and still declares `pipeline: standard`, leaving the executor choice ambiguous (`.ai-engineering/specs/plan.md:1-8`, `.ai-engineering/specs/plan.md:17-30`). The parent spec deliberately groups multiple waves under one large spec because splitting would duplicate sync, test, changelog, and review work (`.ai-engineering/specs/spec.md:43-48`).

The `/ai-plan` skill stops after writing the plan and states that the operator must approve before build execution (`.claude/skills/ai-plan/SKILL.md:19-32`, `.claude/skills/ai-plan/SKILL.md:101-103`). That is sound governance, but the plan frontmatter does not record the route or the approval transition that later executors need.

The no-HITL handler requires an approved plan, a single-concern plan, and absence of an active autopilot manifest (`.claude/skills/ai-build/handlers/no-hitl.md:18-29`). Its documented single-concern gate relies on `## Task Group`, `### Phase`, and manifest signals (`.claude/skills/ai-build/handlers/no-hitl.md:31-60`). The active plan uses `## Phase` headings, so a shape-only gate can misclassify semantically multi-concern work unless the executor performs extra judgment (`.ai-engineering/specs/plan.md:32-76`).

The no-HITL failure contract is explicit: exit `78`, report `Reason`, `Detected`, `Recovery`, and `Then retry`, and do not silently fall back to HITL (`.claude/skills/ai-build/handlers/no-hitl.md:62-72`, `.claude/skills/ai-build/handlers/no-hitl.md:128-147`, `.claude/skills/ai-build/handlers/no-hitl.md:149-165`). That protects governance, but it still leaves the operator doing command routing manually.

Autopilot is the intended route for large work because its skill says to use it for at least three concerns, at least ten touched files, or context-overflowing multi-concern execution (`.claude/skills/ai-autopilot/SKILL.md:26-33`). Its Step 0 currently runs `ai-eng host probe` and aborts when `ok_to_dispatch == False` (`.claude/skills/ai-autopilot/SKILL.md:42-45`).

Host capacity code has a semantic split that the skill does not honor. `HostProbe.ok_to_dispatch` requires at least 2 GiB free RAM, memory pressure below 50%, and swap below 20% (`src/ai_engineering/config/concurrency.py:100-117`). But the same module documents and implements an auto-tune path where memory pressure at or above 50% collapses the wave cap to serial `1` rather than always blocking all work (`src/ai_engineering/config/concurrency.py:145-166`). Integration tests pin that high pressure returns `cap == 1` while `ok_to_dispatch` is false (`tests/integration/test_host_preflight.py:75-116`).

The host probe CLI exposes the exact measured fields plus `recommended_cap`, but it deliberately does not emit an audit event; only skill-side callers should emit host capacity into the audit chain (`src/ai_engineering/cli_commands/host_cmd.py:31-65`, `src/ai_engineering/cli_commands/host_cmd.py:11-16`). The package-side audit helper already records caller, probe payload, `ok_to_dispatch`, and `recommended_cap` into a `host_capacity` event, and the event kind is allowed by schema (`src/ai_engineering/state/observability.py:839-884`, `tools/skill_domain/event_schema.py:65-69`).

The current behavior is therefore three stacked gates, not one isolated bug: plan approval/status is separate from spec approval, no-HITL refuses multi-concern work, and autopilot refuses stressed-host fan-out. The failure is that the routing and admission decisions are late, split across skills, and expressed as "try a different command" instead of a single governed execution decision.

## 4. Architecture

Split the decision in two layers along the timeline:

- **Plan-time classification** (lives in `/ai-plan`): given an approved spec, decide whether execution belongs to `/ai-build` or `/ai-autopilot`, count concerns and estimated files, and write the recommendation into `plan.md` frontmatter. The operator reads the recommendation as part of plan approval and invokes the named command. No runtime router needed for this layer — the plan IS the contract.
- **Runtime admission** (lives in `/ai-build` and `/ai-autopilot` Step 0): consult `HostProbe`, validate that the invoked command matches `plan.md`'s `route:` field, and resolve host admission to `fanout | serial | deferred`. Refusal uses the existing structured envelope with a concrete next command.

This keeps the routing decision visible (frontmatter), keeps the host decision late (where capacity is actually known), and keeps the existing command surface intact. The shared **decision object** below is what `/ai-plan` writes and what the runtime handlers read:

```yaml
execution_route:
  spec: spec-NNN
  plan_status: draft|approved|in-progress
  approval: pending|approved
  route: build|autopilot|deferred
  automation: hitl|no-hitl
  concern_count: 1
  estimated_files: 1
  host_admission: fanout|serial|deferred
  recommended_cap: 1
  reason: "short stable code"
  safe_next_command: "/ai-build --resume"
```

Module boundaries:

- `src/ai_engineering/execution/classifier.py` — pure function `classify(spec, plan) -> ExecutionRoute`. Called from `/ai-plan` at plan-time; counts concerns, estimates files, decides `route: build|autopilot`. Deterministic, unit-tested, no side effects.
- `src/ai_engineering/execution/admit.py` — pure function `admit(probe, route) -> HostAdmission`. Called from `/ai-build` and `/ai-autopilot` Step 0; consumes `HostProbe` and returns `fanout|serial|deferred`. Deterministic, unit-tested.
- `src/ai_engineering/cli_commands/execution_cmd.py` exposes `ai-eng execution classify --json` and `ai-eng execution admit --json` as diagnostics for skills and humans (not the main path; the main path is plan frontmatter).
- `src/ai_engineering/config/concurrency.py` remains the source of host thresholds; `admit.py` consumes its `HostProbe` and `resolve_wave_cap` outputs instead of duplicating thresholds.
- `.claude/skills/ai-plan/SKILL.md` calls `classify()`, writes the `execution_route` object into `plan.md` frontmatter, and prints the recommended command at exit alongside the standard approval prompt.
- `.claude/skills/ai-build/handlers/no-hitl.md` reads `plan.md` frontmatter; refuses when `route != build` (with envelope pointing to the recommended command), not via heading heuristics.
- `.claude/skills/ai-autopilot/SKILL.md` reads `plan.md` frontmatter; treats `host_admission=fanout` as normal autopilot, `serial` as one-sub-spec-at-a-time, and `deferred` as a safe non-executing state with a resumable packet.
- `src/ai_engineering/state/observability.py` records `execution_classified` (plan-time) and `execution_admitted` (runtime) as `framework_operation` events plus the existing `host_capacity` event, preserving schema allowlists.

Admission states:

| State | Meaning | Action |
| --- | --- | --- |
| `fanout` | RAM, pressure, and swap clear fan-out thresholds. | Run autopilot waves with `recommended_cap`. |
| `serial` | Fan-out is unsafe, but one bounded worker is safe. | Run one sub-spec or one build task at a time; no parallel agents. |
| `deferred` | Any execution is unsafe or approval is missing. | Write route/defer packet, emit audit event, print one resume command. |

This keeps the safety invariant: resource pressure cannot produce unbounded fan-out. It also removes the UX dead end: the system says "deferred with resume state" or "serial mode selected", not "not possible".

## 5. Evidence Catalog

| Evidence | Why it matters |
| --- | --- |
| `src/ai_engineering/templates/project/CANONICAL.md:49-60` | Canonical chain names `/ai-build` and `/ai-autopilot` but does not surface a plan-time route classification the operator can read. |
| `.ai-engineering/specs/spec.md:1-10` | Current spec is approved. |
| `.ai-engineering/specs/plan.md:1-9` | Current plan remains draft and lacks explicit execution-route metadata. |
| `.ai-engineering/reference/plan-schema.md:85-91` | Plan approval is a lifecycle state separate from draft emission. |
| `tools/spec_lint/checks/plan.py:20-31` | `draft` is valid and active, so lint can pass without execution approval. |
| `.ai-engineering/specs/plan.md:17-30` | Active plan is full, cross-surface work despite `pipeline: standard`. |
| `.claude/skills/ai-plan/SKILL.md:19-32` | Plan skill stops before execution and requires operator approval. |
| `.claude/skills/ai-build/handlers/no-hitl.md:18-29` | no-HITL prerequisites require approved, single-concern, non-autopilot work. |
| `.claude/skills/ai-build/handlers/no-hitl.md:31-60` | no-HITL single-concern gate relies on heading and manifest signals. |
| `.claude/skills/ai-build/handlers/no-hitl.md:149-165` | no-HITL correctly prohibits prompts, auto-retry, and silent fallback. |
| `.claude/skills/ai-autopilot/SKILL.md:26-33` | Autopilot is the intended multi-concern route. |
| `.claude/skills/ai-autopilot/SKILL.md:42-45` | Autopilot currently aborts when host probe says dispatch is unsafe. |
| `src/ai_engineering/config/concurrency.py:100-117` | Host readiness combines RAM, pressure, and swap thresholds. |
| `src/ai_engineering/config/concurrency.py:145-166` | High pressure can resolve to serial cap `1`, which conflicts with unconditional abort. |
| `tests/integration/test_host_preflight.py:75-116` | Tests pin high-pressure false dispatch plus serial cap behavior. |
| `src/ai_engineering/cli_commands/host_cmd.py:31-65` | CLI already exposes measured capacity and recommended cap. |
| `src/ai_engineering/state/observability.py:839-884` | Host-capacity audit event already has the needed payload shape. |
| `tools/skill_domain/event_schema.py:65-69` | `host_capacity` is an allowed top-level event kind. |

## 6. Roadmap

### Milestone 1 — RED: route contract tests

Acceptance gates:

- Unit test: approved spec + draft plan returns `route=deferred`, `reason=plan_not_approved`.
- Unit test: multi-concern plan returns `route=autopilot`, not no-HITL build.
- Unit test: high pressure with low swap returns `host_admission=serial` and cap `1`.
- Unit test: high swap or low RAM returns `host_admission=deferred`.
- Contract test: route envelope includes `Reason`, `Measured`, `Threshold`, `Decision`, `Safe next command`, and `Resume state`.

### Milestone 2 — Implement deterministic classifier and admit

Acceptance gates:

- `classifier.classify(spec, plan) -> ExecutionRoute` is a pure function over spec/plan inputs; `admit.admit(probe, route) -> HostAdmission` is a pure function over `HostProbe` inputs. Neither imports LLM code nor reads agent memory.
- `ai-eng execution classify --json` and `ai-eng execution admit --json` emit stable JSON with no human prose (diagnostics surface; the main path is plan frontmatter).
- Classification consumes spec size signals and plan body; admission consumes `HostProbe` and `resolve_wave_cap` thresholds — neither duplicates the other's responsibility.

### Milestone 3 — Plan metadata and approval state

Acceptance gates:

- `/ai-plan` writes `execution_route` metadata and leaves `approval: pending` or `status: draft` until approval.
- Plan approval path updates a single field, not a second store.
- `ai-eng spec verify` continues to verify counters but does not imply approval.

### Milestone 4 — Build/no-HITL integration

Acceptance gates:

- `/ai-build` and `/ai-build --no-hitl` read `plan.md` frontmatter `route:` field as authoritative; eligibility is no longer derived from heading shape.
- A `/ai-build` invocation against a `route: autopilot` plan refuses with the structured envelope and prints the recommended command (`/ai-autopilot`) — no silent delegation, no auto-retry.
- Heading-shape checks remain available as a fallback diagnostic when the frontmatter is missing (legacy plans), never as the authoritative gate for new plans.

### Milestone 5 — Autopilot host-admission integration

Acceptance gates:

- `fanout` runs current wave behavior with bounded cap.
- `serial` writes the autopilot manifest and runs one sub-spec at a time.
- `deferred` writes no implementation changes, emits `execution_deferred`, and prints `/ai-autopilot --resume` plus the measured host blockers.

### Milestone 6 — Audit, docs, and UX

Acceptance gates:

- `host_capacity` records every skill-side host gate.
- `framework_operation/detail.operation=execution_routed` records route decisions.
- README/canonical skill docs describe one standard recovery model.
- CLI and skill outputs avoid "not possible" phrasing when a governed deferral or serial lane exists.

## 7. Definition of Done

- Operators read the recommended command at the end of `/ai-plan` and invoke it directly — no trial-and-error escalation.
- The plan-time route decision is reproducible by `ai-eng execution classify --json`; the runtime host decision is reproducible by `ai-eng execution admit --json`.
- Approved multi-concern work routes to autopilot automatically or is deferred with resume state; it does not require trial-and-error command escalation.
- A host with unsafe fan-out never launches parallel agents.
- A host with unsafe execution writes no implementation changes and preserves a resumable state.
- no-HITL remains unattended, non-interactive, audited, and single-round on quality blockers.
- All route, host, deferral, override, and quality outcomes are present in the audit chain.
- `pytest tests/integration/test_host_preflight.py -q`, new route tests, `ai-eng spec verify`, `ai-eng verify --full`, and full `pytest -q` pass.

## 8. Quality Stamps

- §10.1 KISS: two pure functions (`classify` plan-time, `admit` runtime), one decision object written into `plan.md`, one operator-facing recovery envelope. No central runtime router.
- §10.5 TDD: route and admission behavior starts with RED tests for the exact failure modes observed.
- §10.6 SDD: this brief becomes the problem statement for `/ai-brainstorm`; no implementation should start from this draft directly.
- §10.7 Clean Code: route names are business terms (`fanout`, `serial`, `deferred`) rather than overloaded booleans.
- §10.8 Hexagonal Architecture: host probing remains an adapter; route classification is deterministic domain logic; skills are thin wrappers.
- SSOT-PD: approval, route, and admission decisions have one writable store each; derived CLI JSON is a projection, not a second source of truth.
- Security: no host-pressure override without audit evidence and explicit risk acceptance when thresholds say unsafe.

## 9. Open Decisions

1. Should `/ai-plan` print the recommended command at exit and let the operator invoke it manually, or should it exit with a structured prompt that requires explicit confirmation of the recommended command before terminating? (Plan-time classification means the public command surface stays as-is: `/ai-build` for single-concern, `/ai-autopilot` for multi-concern — no `/ai-execute` rename needed.)
2. Should `ok_to_dispatch` keep its current name and gain a companion `host_admission` field, or should a future breaking migration rename it to `ok_to_fanout`?
3. What exact threshold separates `serial` from `deferred` when pressure is high but swap is low?
4. Should plan approval be represented by `status: approved` only, or by separate `status` and `approval` fields?
5. Should deferred execution use a heartbeat/reminder, or only print a manual `/ai-autopilot --resume` command?
6. Should an operator override of host deferral require `ai-eng risk accept`, a lighter local confirmation, or be forbidden in regulated mode?

## 10. Migration

This should be a hard migration, not a compatibility shim.

- Extends spec-139 M2 host preflight (`HostProbe`, `_auto_tune_from_probe`, `host_capacity` audit event); does not redefine its thresholds or introduce a parallel host gate.
- Update plan schema to require route metadata for newly generated plans.
- Add a one-time active-plan migration task for existing in-flight plans: re-run `/ai-plan` or `ai-eng execution route --write` to populate route metadata and approval state.
- Update no-HITL tests to assert frontmatter-driven eligibility (`route:` field) instead of heading-count eligibility.
- Update autopilot tests to assert three host-admission states: fanout, serial, deferred.
- Document any CLI JSON field change in `CHANGELOG.md` under `### BREAKING` if `ok_to_dispatch` is renamed or removed.
- Do not preserve stale route fields or command aliases after the migration; generated mirrors must be regenerated via `ai-eng dev sync`.

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| `classify` and `admit` grow into a parallel orchestration layer that duplicates skill logic. | Medium | High | Keep both as pure functions; skills call them instead of reimplementing thresholds. No state, no side effects, no branching by mode. |
| Serial autopilot under pressure still worsens a stressed host. | Medium | High | Make high swap and low RAM absolute deferral blockers; audit every serial admission. |
| Hidden auto-delegation surprises operators. | Medium | Medium | Print route decision before dispatch and write it to `plan.md` plus audit. |
| Route metadata becomes stale after plan edits. | Medium | Medium | Recompute route during `ai-eng spec verify --fix` or fail when metadata/body drift. |
| no-HITL semantics become too broad. | Low | High | no-HITL still means no prompts and no auto-retry; it does not mean bypassing host or quality gates. |
| Audit schema drift. | Low | Medium | Use existing `host_capacity` and `framework_operation` kinds unless a separate schema spec is approved. |
| Operator frustration remains if deferred is the only safe answer. | Medium | Medium | Deferral must include measured blockers, safe resume command, and optional wait/reminder path. |

## 12. References

External evidence:

- Google SRE, [Handling Overload](https://sre.google/sre-book/handling-overload/): use direct resource signals, graceful degradation, and cheap rejection instead of overload amplification.
- AWS Builders' Library, [Timeouts, retries, and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/): retries can amplify overload; cap retries, use backoff/jitter, and preserve idempotency.
- Kubernetes, [Admission Control](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/): admission runs before persistence and rejects invalid requests immediately with an end-user error.
- Kubernetes, [Resource Quotas](https://kubernetes.io/docs/concepts/policy/resource-quotas/): aggregate resource constraints reject requests with constraint-specific messages when limits would be violated.
- GitHub Docs, [Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments): deployment protection rules combine manual approvals, wait timers, branch restrictions, and third-party readiness checks.
- NIST AI RMF Core, [Govern/Map/Measure/Manage](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/): governance, measurement, documentation, and risk treatment should be continuous across the AI lifecycle.
- OWASP, [Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html): application logs should consistently capture security and operational events with enough context to reconstruct what happened.
- CLI Guidelines, [Command Line Interface Guidelines](https://clig.dev/): CLIs should suggest next commands, expose state, be recoverable, and provide stable JSON for scripts.
- Microsoft Learn, [Error Message Guidelines](https://learn.microsoft.com/en-us/windows/win32/debug/error-message-guidelines): useful errors explain what happened, the result, and what the user can do next.

Internal evidence is consolidated in §5 Evidence Catalog.

## 13. Glossary

- **Admission**: The deterministic go/no-go decision made before agent dispatch or filesystem mutation.
- **Fan-out**: Parallel agent dispatch in autopilot planning, implementation, or quality waves.
- **Serial mode**: A degraded autonomous route that runs one sub-spec or task at a time with no parallel agents.
- **Deferred execution**: A safe stop that writes route/resume state but dispatches no implementation agent.
- **Route metadata**: Plan frontmatter that records the intended executor, automation mode, and admission state.
- **no-HITL**: Unattended mode: no prompts, no hidden fallback, no auto-retry; blockers become terminal structured outcomes.
- **Host capacity**: The measured free RAM, pressure, swap, cores, and recommended cap used to admit or defer execution.

## 14. Acceptance

- [ ] `/ai-brainstorm --consume standard-flow-execution-admission-control-brief.md` produces a spec with explicit route/admission decisions.
- [ ] The spec defines a deterministic `ExecutionRoute` schema and its single source of truth.
- [ ] The plan schema requires route metadata for new active plans.
- [ ] no-HITL no longer relies on heading-count shape as its authoritative multi-concern gate.
- [ ] Autopilot distinguishes fan-out, serial, and deferred host states.
- [ ] Host-pressure deferral writes no implementation changes and emits an audit event.
- [ ] Operator-facing errors include measured value, threshold, decision, and safe next command.
- [ ] Route/admission tests cover the spec-144 failure sequence.
- [ ] Full verification passes before PR handoff.
