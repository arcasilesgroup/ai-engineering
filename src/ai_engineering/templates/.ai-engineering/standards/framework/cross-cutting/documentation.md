# Cross-Cutting Standard: Documentation

## Scope

Applies to all stacks. Governs documentation practices for code, APIs, and project-level documentation.

## Principles

1. **Divio system**: four documentation types — tutorials, how-to guides, explanation, reference.
2. **Code as documentation**: well-named functions, types, and variables reduce the need for comments.
3. **Proximity**: documentation lives near the code it describes. API docs in code, guides in repo.
4. **Accuracy over completeness**: wrong documentation is worse than missing documentation.
5. **Audience-aware**: know who reads each document. Adjust depth and terminology accordingly.

## Patterns

- **README**: every project has a README with: what it is, how to install, how to use, how to contribute.
- **API documentation**: generated from code annotations (Javadoc, JSDoc, docstrings, `///` comments).
- **Architecture Decision Records**: significant decisions documented in decision-store with context and rationale.
- **Changelog**: maintained per Keep a Changelog format. Updated with every user-facing change.
- **Inline comments**: explain "why", not "what". Code explains what it does; comments explain why.

## Anti-patterns

- Documentation that restates the code (`// increment i` above `i++`).
- Stale documentation that contradicts current behavior.
- Documentation in external wikis disconnected from the codebase.
- No documentation on public APIs.
- Comments left as TODOs without tracking (use work items instead).

## Update Contract

This file is framework-managed and may be updated by framework releases.
