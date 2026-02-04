---
name: create-adr
description: Create an Architecture Decision Record
disable-model-invocation: true
---

## Context

Creates a new Architecture Decision Record (ADR) following the project's ADR template. ADRs document important architectural decisions, their context, and consequences.

## Inputs

$ARGUMENTS - Decision title and optional context (e.g., "Use Redis for caching because we need sub-ms latency")

## Steps

### 1. Determine ADR Number

- List existing ADRs in `context/decisions/`.
- Assign the next sequential number (e.g., ADR-003).

### 2. Read Template

- Read `context/decisions/_template.md` for the standard format.

### 3. Generate ADR

Create the ADR file with:

    # ADR-{NNN}: {Title}

    **Date:** {today's date}
    **Status:** Proposed

    ## Context

    [What is the issue that we're seeing that is motivating this decision?]

    ## Decision

    [What is the change that we're proposing and/or doing?]

    ## Consequences

    ### Positive
    - [What becomes easier or possible?]

    ### Negative
    - [What becomes harder or is a trade-off?]

    ### Risks
    - [What could go wrong?]

    ## Alternatives Considered

    ### {Alternative 1}
    - **Pros:** ...
    - **Cons:** ...

    ### {Alternative 2}
    - **Pros:** ...
    - **Cons:** ...

    ## References

    - [Links to relevant resources, discussions, or documentation]

### 4. Ask for Review

Present the generated ADR content and ask the user to confirm or modify before saving.

### 5. Save

Save as `context/decisions/ADR-{NNN}-{kebab-case-title}.md`.

## Verification

- ADR number is unique and sequential
- All sections are filled with relevant content
- Decision is clearly stated
- Alternatives are documented with trade-offs
