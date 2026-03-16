---
name: plan
version: 1.0.0
description: 'Advisory planning: discover requirements, assess risks, recommend pipeline.
  Zero writes.'
argument-hint: '[topic]'
tags: [planning, discovery, risk, advisory]
---

# Advisory Planning

## Purpose

Read-only planning skill that analyzes requirements, assesses risks, and recommends a pipeline strategy — without creating specs or modifying any files. Use when you need planning guidance without committing to a spec.

This is the shared planning contract for both:

- `#ai-plan` / `/ai:plan --plan-only` (advisory output only), and
- the planning stages inside `.agents/agents/ai-plan.md` (classify/discover/assess/risk), before spec scaffolding and execution-plan assembly.

## Trigger

- User invokes `/ai:plan --plan-only`
- Copilot prompt `#ai-plan`
- Need to assess scope before deciding whether to create a full spec
- `.agents/agents/ai-plan.md` needs shared planning stages before invoking `.agents/skills/spec/SKILL.md`

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"plan"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## Shared Rules (Canonical)

Use these rules as the single source of truth for planning behavior shared by skill and agent.

- **PLAN-R1 (Classification):** classify using the pipeline matrix in Step 1 (`full|standard|hotfix|trivial`).
- **PLAN-R2 (Discovery evidence):** gather evidence from active spec, code/tests, decision store, and contracts; label findings as `KNOWN`, `ASSUMED`, or `UNKNOWN`.
- **PLAN-R3 (Architecture depth):** for `full`/`standard`, include components, integration points, and cross-cutting concerns.
- **PLAN-R4 (Risk dimensions):** assess complexity, security, compatibility, and governance compliance.
- **PLAN-R5 (Interrogation):** for `full`/`standard` pipelines, explore the codebase and ask clarifying questions ONE AT A TIME before classification. Map all findings as `KNOWN`/`ASSUMED`/`UNKNOWN`. Do not proceed to spec creation with unresolved `UNKNOWN` items.
- **PLAN-B1 (No execution while planning):** planning outputs analysis/plans only; do not execute implementation/release tasks.

## Procedure

### Step 1 — Classify

Analyze the request and classify the pipeline type:

| Pipeline | Criteria                                           |
| -------- | -------------------------------------------------- |
| full     | New feature, refactor, governance change, >3 files |
| standard | Enhancement, 3-5 files                             |
| hotfix   | Bug fix, security patch, <3 files                  |
| trivial  | Typo, comment, single-line change                  |

### Step 2 — Discover

Scan available context to understand the request:

- Active spec and completed specs (prior art)
- Relevant source code and tests
- Decision store (constraints from prior decisions)
- Product and framework contracts

Classify findings as KNOWN, ASSUMED, or UNKNOWN.

### Step 3 — Architecture Assessment

For full/standard pipelines:

- Identify affected components and integration points
- Assess impact on existing architecture
- Note any cross-cutting concerns (security, performance, accessibility)

### Step 4 — Risk Assessment

Evaluate risks across dimensions:

- Technical complexity and unknowns
- Security implications
- Breaking changes or backward compatibility
- Governance compliance gaps

### Step 5 — Recommend

Produce a conversational planning document:

```markdown
## Planning Assessment

### Classification

- **Pipeline**: full | standard | hotfix | trivial
- **Scope**: [files/components affected]
- **Estimated complexity**: low | medium | high

### Key Requirements

- [Confirmed requirements from discovery]

### Risks

- [Risk, likelihood, impact, mitigation]

### Recommended Approach

- [Pipeline steps to execute]
- [Agent assignments]
- [Phase ordering]

### Next Step

- Run `/ai:plan` to create a full spec and execution plan
- Or proceed directly with `/ai:execute` if plan already exists
```

## Examples

### Example 1: Assess scope of a feature request

User says: `/ai:plan --plan-only "add OAuth support"`.
Actions:

1. Classify as full pipeline (new feature, likely >3 files).
2. Discover: scan auth-related code, check decision store for prior auth decisions.
3. Risk: security implications, integration with existing auth flow.
4. Recommend: full pipeline with build + scan + security review.

## Governance Notes

- This skill is **read-only** — it produces analysis, not files.
- Zero writes to disk. No spec creation, no branch creation, no task creation.
- Output is conversational only — presented to the user for decision-making.
- If the user wants to proceed, direct them to `/ai:plan` for full spec creation.
- Enforces shared boundary `PLAN-B1` in advisory mode.
- When the plan agent creates specs, it writes spec.md, plan.md, and tasks.md directly via Write tool. See `.agents/agents/ai-plan.md` Spec-as-Gate Pattern.

## References

- `.agents/agents/ai-plan.md` — full planning agent (creates specs, produces execution plan)
- `.agents/skills/discover/SKILL.md` — detailed discovery interrogation
- `.agents/skills/risk/SKILL.md` — formal risk acceptance lifecycle
