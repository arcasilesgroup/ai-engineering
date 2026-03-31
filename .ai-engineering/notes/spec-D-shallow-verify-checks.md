# Madurar checks superficiales de ai-eng verify

**Discovery Date**: 2026-03-31
**Context**: Quality gate checks report misleading PASS 100/100 scores
**Spec**: spec-D

## Problem

Two verify checks (performance, a11y) report PASS with 100/100 scores but perform no real validation. This creates false confidence in quality gates.

## Findings

1. **Performance check** -- solo busca `*benchmark*` con `rglob` y entra en `.venv` contando benchmarks de terceros. No mide rendimiento real del proyecto.

2. **Accessibility (a11y) check** -- solo detecta presencia de `.html`/`.tsx`/`.jsx` sin ejecutar checks reales de accesibilidad. Encontrar archivos frontend no prueba que sean accesibles.

Ambos son "applicability gates" que reportan PASS 100/100 de forma misleading. Un score de 100/100 implica que se verifico algo y paso perfectamente, cuando en realidad solo se detecto que el check es aplicable.

## Code Examples

Two options for resolution:
1. Implement real checks (actual performance benchmarks, actual a11y scanning with axe-core or similar)
2. Rename to "applicability detection" and change scoring to reflect that only applicability was checked (e.g., "APPLICABLE" instead of "PASS 100/100")

## Pitfalls

- Do not just suppress the checks -- they correctly identify that the project has frontend files and benchmark-related files
- The `.venv` traversal in performance check is a concrete bug: it counts third-party benchmarks as project benchmarks
- Fixing scoring without fixing the `.venv` traversal still leaves a bug

## Related

- `ai-eng verify` command
- Quality gates thresholds in CLAUDE.md
- `/ai-verify` skill
