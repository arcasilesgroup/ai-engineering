---
description: Validates that the project builds and all tests pass
tools: [Bash, Read, Glob]
---

## Objective

Verify the project compiles without errors and all tests pass.

## Process

1. Detect project type by checking for `.sln`/`.csproj`, `package.json`, `pyproject.toml`, or `*.tf` files.
2. Run the appropriate build command:
   - .NET: `dotnet build --no-restore`
   - TypeScript: `npm run build`
   - Python: `python -m py_compile` on changed files
3. Run the test suite:
   - .NET: `dotnet test --no-build`
   - TypeScript: `npm test`
   - Python: `pytest`
4. Parse output and report: build status, test count (passed/failed/skipped), coverage if available.

## Success Criteria

- Build exits with code 0
- All tests pass
- No compiler warnings on new/changed files

## Constraints

- Do NOT modify source files
- Do NOT install or restore packages
- Report failures with file paths and error messages, don't attempt fixes
