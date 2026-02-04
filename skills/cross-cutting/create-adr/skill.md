# Skill: Create Architecture Decision Record

---
id: cross-cutting/create-adr
name: Create Architecture Decision Record
complexity: low
estimated_time: 15 minutes
---

## Description

Documents an architectural decision using a structured ADR format, capturing context, options considered, decision rationale, and consequences.

## Prerequisites

- Decision to document is finalized
- Stakeholder consensus achieved
- Impact analysis completed

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| Title | Yes | Concise decision title |
| Context | Yes | Problem/situation description |
| Options | Yes | Alternatives considered |
| Decision | Yes | Chosen option |
| Rationale | Yes | Why this option was chosen |
| Consequences | Yes | Positive and negative impacts |

## Outputs

- ADR file (`ADR-NNN-title.md`)
- Updated ADR index (if maintained)

## Execution Steps

### Step 1: Determine ADR Number

Check existing ADRs in `.ai/context/decisions/` and use next sequential number.

### Step 2: Create ADR File

```markdown
# ADR-NNN: [Title]

**Date:** YYYY-MM-DD  
**Status:** Proposed | Accepted | Deprecated | Superseded by ADR-XXX  
**Deciders:** [Team/Role names]

## Context

[Describe the situation, constraints, and forces at play]

What problem are we trying to solve?
What are the constraints?
What are the business/technical drivers?

## Options Considered

### Option 1: [Name]

**Description:** [Brief description]

**Pros:**
- Pro 1
- Pro 2

**Cons:**
- Con 1
- Con 2

**Effort:** Low | Medium | High

### Option 2: [Name]

**Description:** [Brief description]

**Pros:**
- Pro 1
- Pro 2

**Cons:**
- Con 1
- Con 2

**Effort:** Low | Medium | High

### Option 3: [Name]

[Same structure]

## Decision

We will use **Option X: [Name]**.

[One paragraph explaining the core decision]

## Rationale

[Detailed explanation of why this option was chosen over others]

- Key factor 1: [Explanation]
- Key factor 2: [Explanation]
- Key factor 3: [Explanation]

## Consequences

### Positive

- [Benefit 1]
- [Benefit 2]
- [Benefit 3]

### Negative

- [Drawback 1]
- [Drawback 2]

### Risks

- **Risk 1:** [Description] — Mitigation: [How to address]
- **Risk 2:** [Description] — Mitigation: [How to address]

## Implementation Notes

[Practical guidance for implementing this decision]

- Step 1: ...
- Step 2: ...
- Step 3: ...

## Related

- ADR-XXX: [Related decision]
- [External reference](url)
```

## ADR Status Lifecycle

```
Proposed → Accepted → [Deprecated | Superseded]
    ↓
 Rejected
```

| Status | Meaning |
|--------|---------|
| Proposed | Under discussion |
| Accepted | Approved and in effect |
| Deprecated | No longer valid, no replacement |
| Superseded | Replaced by another ADR |
| Rejected | Not approved |

## Common ADR Topics

### Architecture & Design
- Technology stack choices
- Framework selection
- Pattern adoption (Result pattern, CQRS, etc.)
- API design decisions

### Infrastructure
- Cloud service selection
- Database choices
- Caching strategy
- Deployment approach

### Process & Standards
- Coding standards
- Testing strategy
- Documentation approach
- Branching strategy

## Good ADR Practices

### Context Section
- Be specific about constraints
- Include relevant metrics if available
- Reference stakeholder requirements

### Options Section
- Include at least 2-3 realistic options
- Be honest about cons
- Include "do nothing" if applicable

### Decision Section
- Be clear and unambiguous
- One decision per ADR
- Quantify when possible

### Consequences Section
- Be honest about trade-offs
- Include mitigation strategies
- Consider long-term implications

## Checklist

- [ ] Title is concise and descriptive
- [ ] Status is set correctly
- [ ] Context explains the problem clearly
- [ ] At least 2 options considered
- [ ] Each option has pros/cons/effort
- [ ] Decision is clearly stated
- [ ] Rationale explains the "why"
- [ ] Positive consequences listed
- [ ] Negative consequences acknowledged
- [ ] Risks have mitigations
- [ ] Implementation notes included
- [ ] Related decisions linked

## Template Location

`.ai/context/decisions/_template.md`

## Related Skills

- [Create Provider](../dotnet/create-provider/skill.md)
- [Security Review](./security-review/skill.md)

## Example Invocation

```
Create ADR for:
- Title: API Versioning Strategy
- Context: Need to support multiple API versions for clients
- Options: URL segment, header, query param
- Decision: URL segment versioning
- Rationale: Visibility, caching, simplicity
```
