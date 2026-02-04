---
name: blast-radius
description: Analyze the impact of a code change across the codebase
---

## Context

Analyzes the blast radius of a proposed or actual code change. Identifies all files, tests, and systems affected by modifying specified code.

## Inputs

$ARGUMENTS - File path and optional method/class name, or "staged" for staged changes

## Steps

### 1. Identify the Change

- If $ARGUMENTS is "staged": analyze `git diff --cached`.
- If file path: read the file and identify the changed/target code.
- Extract: changed methods, interfaces, types, exports.

### 2. Trace Dependencies

For each changed symbol, find all references:

- **Direct callers**: Files that call the changed method/function.
- **Interface implementations**: Classes implementing a changed interface.
- **Type consumers**: Code using changed types/DTOs.
- **Configuration**: Files referencing changed config keys.
- **Tests**: Test files that test the changed code.
- **DI registrations**: Startup/DI files registering changed services.

### 3. Assess Impact

Categorize affected files:
- **Direct impact**: Files that directly use the changed code.
- **Indirect impact**: Files that use code affected by the change.
- **Test impact**: Tests that need updating.
- **No impact**: Files that reference the same names but are unrelated.

### 4. Report

    ## Blast Radius Analysis

    **Changed:** [file:method/class]
    **Total affected files:** X

    ### Direct Impact (must review)
    - [file:line] - [How it's affected]

    ### Indirect Impact (should review)
    - [file:line] - [How it's affected]

    ### Tests Affected
    - [test file] - [Which tests need attention]

    ### Risk Assessment
    - **Breaking change:** Yes/No
    - **Requires migration:** Yes/No
    - **Estimated scope:** Small/Medium/Large

## Verification

- All direct callers identified
- Interface implementations tracked
- Test files identified
- No false positives from name-only matches
