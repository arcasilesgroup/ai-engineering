---
description: "Relentless requirements discovery through structured interrogation; use"
mode: "agent"
---


# Discovery Interrogation

## Purpose

Structured requirements elicitation skill that drives exhaustive discovery before planning begins. Surfaces hidden assumptions, missing requirements, edge cases, and risks through systematic interrogation across 8 completeness dimensions.

## Trigger

- Before planning any non-trivial feature or spec.
- User request is ambiguous, under-specified, or has implicit assumptions.
- Orchestrator DISCOVERY mode needs requirements clarification.
- Scope creep detected during implementation.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"discover"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## Procedure

### Step 1 — Context Harvest

Read all available context and classify information into three categories:

- **KNOWN**: facts confirmed by existing artifacts (specs, contracts, decision-store, code).
- **ASSUMED**: information inferred but not explicitly confirmed.
- **UNKNOWN**: gaps where no information is available.

Sources to scan:

- Active spec (`_active.md` → `spec.md` → `plan.md` → `tasks.md`).
- Product contract and framework contract.
- Decision store (prior decisions that constrain the current work).
- Relevant source code and tests.
- User's initial request.

### Step 2 — Structured Interrogation

For each ASSUMED and UNKNOWN item, probe using AskUserQuestion. Organize probes by category:

1. **Scope**: What is in/out of scope? What are the boundaries?
2. **Success criteria**: How do we know this is done? What does "working" look like?
3. **Constraints**: Time, budget, technology, backward compatibility, governance.
4. **Dependencies**: What must exist before this work starts? What does this unblock?
5. **Risks**: What could go wrong? What are the failure modes?
6. **Non-functional requirements**: Performance, security, accessibility, scalability.
7. **Edge cases**: Boundary conditions, error states, concurrent access, empty states.
8. **Integration points**: APIs, data flows, external systems, user touchpoints.

**Interrogation rules**:

- Ask one focused question at a time via AskUserQuestion.
- If an answer is shallow or vague, apply the 5 Whys — ask "why?" or "what specifically?" up to 5 times to reach concrete requirements.
- Never accept "it should just work" — demand specific acceptance criteria.
- Record each answer immediately as a confirmed requirement or constraint.

### Step 3 — Completeness Check

Verify coverage across all 8 dimensions:

| Dimension                        | Status      | Evidence |
| -------------------------------- | ----------- | -------- |
| Functional requirements          | COVERED/GAP | ...      |
| Non-functional requirements      | COVERED/GAP | ...      |
| Security implications            | COVERED/GAP | ...      |
| Integration points               | COVERED/GAP | ...      |
| Migration/backward compatibility | COVERED/GAP | ...      |
| Testing strategy                 | COVERED/GAP | ...      |
| Documentation impact             | COVERED/GAP | ...      |
| Governance compliance            | COVERED/GAP | ...      |

If any dimension has a GAP, return to Step 2 for targeted probing.

### Step 4 — Requirements Summary

Produce a structured output:

```markdown
## Discovery Summary

### Confirmed Requirements

- [Numbered list of concrete, testable requirements]

### Confirmed Constraints

- [Numbered list of boundaries and limitations]

### Assumptions (accepted)

- [Items moved from ASSUMED to accepted after user confirmation]

### Open Questions

- [Remaining items that could not be resolved — with owner and deadline]

### Risks Identified

- [Risk description, likelihood, impact, mitigation]

### Recommended Next Steps

- [Specific actions to proceed to planning phase]
```

## Examples

### Example 1: Clarify an ambiguous feature request

User says: "Add enterprise onboarding support".
Actions:

1. Classify known/assumed/unknown requirements and interrogate gaps across the 8 discovery dimensions.
2. Produce confirmed requirements, constraints, risks, and remaining open questions.
   Result: Planning starts with explicit, testable requirements instead of assumptions.

## Governance Notes

- This skill is read-only — it produces analysis, not code.
- All confirmed requirements become inputs to the planning phase.
- Open questions must be resolved before implementation begins.
- Risk items should be tracked in the decision store if they require formal acceptance.

## References

- `.github/prompts/ai-spec.prompt.md` — spec creation follows discovery.
- `.github/agents/plan.agent.md` — planning agent invokes this skill for discovery.
