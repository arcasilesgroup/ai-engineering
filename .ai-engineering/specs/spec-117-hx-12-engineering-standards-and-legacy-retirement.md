---
spec: spec-117-hx-12
title: Engineering Standards and Legacy Retirement
status: done
effort: large
---

# Spec 117 HX-12 - Engineering Standards and Legacy Retirement

## Summary

The refactor already establishes engineering principles and replacement-first discipline, but the standards canon, review/verify binding, adoption guidance, and deletion governance are still incomplete. This feature turns the completed refactor into a stable late-wave closure layer: canonical engineering standards including Harness Engineering, standards-bound review and verify rubrics, migration and adoption guidance, and family-by-family legacy retirement with parity proofs and rollback criteria. It consumes earlier HX outputs instead of reopening their ownership.

## Goals

- Finalize canonical engineering standards surfaces for Clean Code, Clean Architecture, SOLID, DRY, KISS, YAGNI, TDD, SDD, and Harness Engineering.
- Bind those standards into review and verify rubrics.
- Provide migration and adoption guidance for the new harness model.
- Define a family-by-family legacy deletion manifest with parity proof and rollback criteria.
- Keep user-facing docs trailing implemented runtime contracts.

## Non-Goals

- Reopening ownership already assigned to earlier HX slices.
- Prematurely deleting surfaces without replacement proof.
- Publishing user-facing adoption docs for runtime contracts that do not yet exist.

## Decisions

### D-117-69: `HX-12` is a closure layer, not a new architecture pass

The feature consumes earlier HX outputs and turns them into standards canon, rubrics, adoption docs, and deletion governance. It does not redefine control-plane, mirror, kernel, state, capability, context, or eval architecture.

**Rationale**: those ownership decisions are already distributed across earlier slices and should not be reopened late.

### D-117-70: Standards must bind into review and verify, not remain prose-only

Clean-engineering principles and harness-engineering rules must map into review and verify rubrics so later agents can apply them consistently.

**Rationale**: standards that live only in prose drift quickly and stop shaping runtime behavior.

### D-117-71: Legacy retirement is family-by-family and parity-first

Each legacy family needs a replacement owner, parity proof, and rollback path before retirement. Deletions serialize by surface family.

**Rationale**: replacement-before-deletion is already a core refactor rule and needs a concrete closure mechanism.

### D-117-72: User-facing docs trail implemented runtime truth

Root docs such as README and GETTING_STARTED update only after runtime contracts, commands, and artifacts are real.

**Rationale**: otherwise top-level docs become a second speculative truth source.

## Risks

- **Premature-retirement risk**: deleting surfaces too early can break bootstrap or parity. **Mitigation**: enforce family-by-family parity proofs.
- **Rubric-drift risk**: review/verify surfaces can keep drifting if the standards matrix is not bound explicitly. **Mitigation**: connect standards to concrete rubrics and validations.
- **Documentation-drift risk**: top-level docs can outrun reality. **Mitigation**: make them late-wave only.

## Implementation Notes

- Added `src/ai_engineering/standards.py` as the executable standards matrix and legacy retirement manifest.
- Added live and install-template contexts for engineering standards, Harness Engineering, and harness adoption guidance.
- Bound verification check families in `src/ai_engineering/verify/taxonomy.py` to standards metadata without changing verify execution or scoring behavior.
- Added unit coverage for required standards, review/verify consumers, context availability, and parity-first deletion validation.
- Kept README and GETTING_STARTED deferred as trailing user-facing docs.
- Earlier HX owners remain consumed rather than reopened.

## Verification

- RED proof failed on missing `ai_engineering.standards`, as expected.
- Focused standards and taxonomy tests passed: `11 passed in 0.08s`.
- Adjacent verify tests passed after Sonar cleanup: `102 passed in 0.45s`.
- Ruff import/syntax checks passed for touched Python files.
- SonarQube for IDE touched-file analysis returned `findingsCount: 0`.

## Deferred Cleanup From HX-03

- `HX-03` intentionally kept several instruction families manual even after the mirror-contract cutover, including `testing.instructions.md`, `markdown.instructions.md`, and `sonarqube_mcp.instructions.md`. `HX-12` must decide whether each family is canonically preserved as manual, standardized into a generated family, or retired with parity proof.
- Any low-level compatibility affordance that survives after the strict `HX-03` caller cutovers, such as loader semantics retained only for transitional API stability, should be retired here family-by-family once replacement proof exists.

## References

- doc: .ai-engineering/specs/spec-117-hx-12-engineering-standards-and-legacy-retirement-explore.md
- doc: .ai-engineering/contexts/operational-principles.md
- doc: .ai-engineering/specs/spec-115-cross-ide-entry-point-governance-and-engineering-principles-standard.md
- doc: .ai-engineering/specs/spec.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-feature-portfolio.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-task-catalog.md
- doc: .claude/skills/ai-review/SKILL.md
- doc: .claude/skills/ai-verify/SKILL.md

## Open Questions

- Harness Engineering uses `.ai-engineering/contexts/harness-engineering.md` as its canonical context, with a template copy for new installs.
- Review and verify consumers bind through `ai_engineering.standards`; verify taxonomy entries now carry standards metadata.
- Legacy families are serialized in `build_legacy_retirement_manifest()` and all current families keep `delete_allowed=False` until future parity proof flips one family at a time.
- Adoption guidance belongs first in `.ai-engineering/contexts/harness-adoption.md`; root docs trail implemented runtime truth.