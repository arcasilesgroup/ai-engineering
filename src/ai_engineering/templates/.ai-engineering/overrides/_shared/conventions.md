<!-- source: _shared overrides v1 -->

# Shared Conventions — Cross-Stack Minimums

Conventions applied regardless of stack.

## Naming

- Files and directories: kebab-case (`feature-name.md`).
- Python modules: snake_case (`feature_name.py`).
- TypeScript modules: kebab-case files, camelCase exports.
- Constants: SCREAMING_SNAKE_CASE.

## Structure

- One reason to change per module (SRP).
- Public API surface stays minimal — every export is a maintenance cost.
- Three copies of the same fact → extract a constant. Three copies of the
  same logic → extract a function.

## Per-stack overrides

Stack-specific conventions live in
`.ai-engineering/overrides/<stack>/conventions.md`.
