---
name: plan
description: "Advisory planning: discover requirements, assess risks, recommend pipeline. Zero writes."
metadata:
  version: 1.0.0
  tags: [planning, discovery, risk, advisory]
  ai-engineering:
    scope: read-only
    token_estimate: 1500
---

# Advisory Planning

## Purpose

Read-only planning skill that analyzes requirements, assesses risks, and recommends a pipeline strategy — without creating specs or modifying any files. Use when you need planning guidance without committing to a spec.

## Trigger

- User invokes `/ai:plan --plan-only`
- Copilot prompt `#ai-plan`
- Need to assess scope before deciding whether to create a full spec

## Procedure

### Step 1 — Classify

Analyze the request and classify the pipeline type:

| Pipeline | Criteria |
|----------|----------|
| full | New feature, refactor, governance change, >3 files |
| standard | Enhancement, 3-5 files |
| hotfix | Bug fix, security patch, <3 files |
| trivial | Typo, comment, single-line change |

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

## References

- `agents/plan.md` — full planning agent (creates specs, produces execution plan)
- `agents/execute.md` — execution agent (reads plan, dispatches agents)
- `skills/discover/SKILL.md` — detailed discovery interrogation
- `skills/risk/SKILL.md` — formal risk acceptance lifecycle
