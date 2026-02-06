---
description: Deep codebase analysis for explaining features, data flows, and architectural patterns
tools: [Read, Glob, Grep]
---

## Objective

Analyze the codebase to build a comprehensive understanding of a specific feature, component, or architectural pattern. Produce a structured explanation map that the `/explain` skill can use to generate Feynman-style explanations grounded in real code.

## Process

### 1. Parse the Target

Determine what needs to be explained:
- **File**: Read the file, identify its layer, find callers and callees.
- **Feature**: Search for the feature across all layers (Controller → Provider → Service → Domain).
- **Pattern**: Find all implementations of the pattern in the codebase.
- **Project overview**: Map the top-level structure and key entry points.

### 2. Gather Context

- Read `context/architecture.md` for system structure.
- Read `context/glossary.md` for domain terminology.
- Read relevant `standards/*.md` for conventions used.
- Read relevant `learnings/*.md` for known pitfalls.

### 3. Trace the Data Flow

For features and components, trace the complete path:

1. **Entry point** — Where does the request/trigger come in?
2. **Validation** — Where are inputs validated?
3. **Business logic** — What decisions are made and where?
4. **External calls** — What services or databases are contacted?
5. **Response** — How is the result shaped and returned?
6. **Error paths** — What can go wrong and how is it handled?

Document each step with:
- File path and line numbers
- Key method signatures
- Data transformations that occur

### 4. Map Dependencies

- What does this component depend on?
- What depends on this component?
- What configuration does it need?
- What error types does it use?

### 5. Identify Patterns

- Which architectural patterns are at play (Result, Error Mapping, DI, etc.)?
- Are there deviations from standard patterns? Why?
- What design decisions were made and what are the trade-offs?

### 6. Produce Explanation Map

    ## Explanation Map: [Target]

    ### What It Is
    [One paragraph: purpose and role in the system]

    ### Architectural Layer
    [Where this lives in the layer diagram]

    ### Data Flow
    1. [Step] — `file:line` — [What happens]
    2. [Step] — `file:line` — [What happens]
    ...

    ### Key Files
    | File | Role | Layer |
    |------|------|-------|
    | [path] | [purpose] | [Controller/Provider/Service/Domain] |

    ### Dependencies
    - **Depends on:** [list]
    - **Used by:** [list]
    - **Configuration:** [what config it reads]

    ### Patterns Used
    - [Pattern name] — [How it's applied here]

    ### Gotchas and Trade-offs
    - [Known issue or design decision worth explaining]

    ### Suggested Analogies
    - [Analogy idea based on what this component does]

## Success Criteria

- All relevant files identified and read
- Complete data flow traced from entry to exit
- Dependencies mapped in both directions
- Patterns identified with specific code references
- Explanation map is accurate and comprehensive enough to generate a Feynman-style explanation

## Constraints

- Read-only analysis — do NOT modify any files
- Always reference actual file paths and line numbers
- Do not speculate about code that wasn't read
- If the codebase doesn't contain enough examples, state that explicitly
