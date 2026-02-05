# doc-generator Agent

> Keeps documentation in sync with code by generating or updating docs from recent changes.

## Purpose

Automatically generate or update documentation when code changes. Use this agent after implementing features or refactoring to ensure docs stay current.

## When to Use

- After implementing a new feature or endpoint
- After refactoring that changes public APIs
- When configuration or setup steps change
- Before a release to ensure docs reflect current state

## How to Invoke

```
Run the doc-generator agent to update documentation for the recent changes.
```

```
Dispatch doc-generator to check if documentation matches the current code.
```

## What It Does

### 1. Identify Changed Files

Uses `git diff --name-only HEAD~1` to find recently modified files.

### 2. Check Documentation Coverage

For each changed file, checks if corresponding documentation exists:
- API endpoints → route tables, request/response examples
- Public interfaces → method signatures and parameter descriptions
- Configuration changes → setup/installation docs
- Architecture changes → flags for manual ADR review

### 3. Generate or Update Documentation

- Creates or updates documentation files (`.md`, comments)
- Updates table of contents and cross-references if affected
- Preserves existing manual documentation

### 4. Report

Reports what was created or updated, and flags items needing manual review.

## Output Format

```markdown
## Documentation Update Report

### Updated
- `docs/api/users.md` — Added new endpoint documentation
- `README.md` — Updated setup instructions

### Needs Manual Review
- Architecture change detected in `src/services/` — consider creating an ADR

### No Changes Needed
- `src/utils/` — Internal implementation, no public API changes
```

## Constraints

- Only updates documentation files (`.md`, code comments)
- Does NOT modify source code
- Preserves existing manual documentation
- Does NOT generate documentation for internal/private implementations

---
**See also:** [Agents Overview](Agents-Overview) | [/document skill](Skills-Documentation#document)
