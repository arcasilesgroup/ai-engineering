---
description: Generates or updates documentation from code changes
tools: [Read, Write, Glob, Grep]
---

## Objective

Keep documentation in sync with code by generating or updating docs from recent changes.

## Process

1. Identify recently changed files using `git diff --name-only HEAD~1`.
2. For each changed file, check if corresponding documentation exists.
3. Generate or update documentation:
   - API endpoints: update route tables, request/response examples
   - Public interfaces: update method signatures and parameter descriptions
   - Configuration changes: update setup/installation docs
   - Architecture changes: flag for manual ADR review
4. Update table of contents and cross-references if affected.
5. Report what was created or updated.

## Success Criteria

- Documentation reflects current code state
- No orphaned references to removed code
- New public APIs have documentation

## Constraints

- Only update documentation files (`.md`, comments)
- Do NOT modify source code
- Preserve existing manual documentation
- Do NOT generate documentation for internal/private implementations
