---
name: learn
description: Record a new learning or pattern for future AI sessions
---

## Context

Records a new learning, pattern, or gotcha that should be remembered across AI sessions. Writes to the appropriate learnings file so future interactions benefit from accumulated knowledge.

## Inputs

$ARGUMENTS - The learning to record (e.g., "dotnet: Always use Bind<T>() with explicit type parameter to avoid CS0411")

## Steps

### 1. Parse the Learning

Extract from $ARGUMENTS:
- **Stack**: Which technology stack (global, dotnet, typescript, python, terraform)
- **Category**: Pattern, gotcha, best practice, or tool tip
- **Description**: The actual learning

### 2. Determine Target File

Map to the correct learnings file:
- General/cross-stack → `learnings/global.md`
- .NET specific → `learnings/dotnet.md`
- TypeScript/React → `learnings/typescript.md`
- Python → `learnings/python.md`
- Terraform/IaC → `learnings/terraform.md`

### 3. Check for Duplicates

Read the target file and check if a similar learning already exists. If so, update the existing entry rather than adding a duplicate.

### 4. Format and Append

Add the learning in this format:

    ### [Short Title]

    **Context:** [When does this apply?]
    **Learning:** [What should be done?]
    **Example:**
    ```[language]
    // Good
    [correct code]

    // Bad
    [incorrect code]
    ```

### 5. Confirm

Report what was recorded and where.

## Verification

- Learning is recorded in the correct file
- No duplicate entries
- Format is consistent with existing learnings
- Learning is actionable and specific
