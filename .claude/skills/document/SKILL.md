---
name: document
description: Generate or update documentation for code
disable-model-invocation: true
---

## Context

Generates or updates documentation for specified code files, following the project's documentation standards. Creates inline docs, API docs, or markdown documentation as appropriate.

## Inputs

$ARGUMENTS - File paths to document, or "api" for API docs, or "readme" for README update

## Steps

### 1. Analyze Code

- Read the target file(s) to understand public API surface.
- Identify undocumented public methods, classes, and interfaces.
- Check existing documentation for accuracy.

### 2. Generate Documentation

Based on the target:

**Inline Documentation:**
- Add XML docs (.NET), JSDoc (TypeScript), or docstrings (Python) to public members.
- Document parameters, return values, exceptions, and examples.
- Focus on "why" not "what" for implementation comments.

**API Documentation:**
- List all endpoints with HTTP method, route, request/response schemas.
- Include authentication requirements.
- Add example requests and responses.

**README Updates:**
- Update feature lists, setup instructions, or API references.
- Keep the existing structure and tone.

### 3. Verify

- Ensure documentation compiles (e.g., `dotnet build` for XML docs).
- Check for broken references or links.
- Verify examples are accurate.

### 4. Report

    ## Documentation Report

    **Files updated:** X

    ### Documentation Added
    1. **[file]** - [What was documented]
    2. ...

    ### Coverage
    - Public methods documented: X/Y (Z%)

## Verification

- All public APIs have documentation
- Documentation is accurate and matches code behavior
- No broken references
- Examples compile and run correctly
