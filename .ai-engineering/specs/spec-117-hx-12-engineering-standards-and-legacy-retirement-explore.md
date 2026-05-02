# HX-12 Explore - Engineering Standards and Legacy Retirement

This artifact captures the evidence gathered before writing the feature spec for `HX-12`.

## Scope

Feature: `HX-12` Engineering Standards and Legacy Retirement.

Question: what must change so clean-engineering standards become canonical, reviewable, and verifiable across the refactored harness, and legacy surface families are retired only with parity proof and rollback clarity?

## Evidence Summary

### Several Standards Already Exist, But The Canon Is Incomplete Or Split

- Clean Code, Clean Architecture, SOLID, DRY, KISS, and YAGNI already have a canonical context in `operational-principles.md`.
- TDD is strongly operationalized across constitution, planning, and testing skill flows.
- SDD is strong as governance and workflow discipline but not yet bound into one dedicated review or verify rubric.
- Harness engineering is documented mainly in spec-117 program artifacts, not yet in one canonical reusable context.

The repo already has real standards surfaces, but they are not yet fully bound into one late-wave canonical layer.

### Legacy Families Are Visible, But Their Deletion Depends On Earlier Features

- Dual constitutions and stale control-plane projections depend on `HX-01` and `HX-06`.
- Stale mirror families depend on `HX-03`.
- Dual gate families depend on `HX-04` and `HX-11`.
- State/report residue depends on `HX-05`.
- Template/runtime Python duplication depends on `HX-08` to `HX-10`.

This means `HX-12` cannot be an early cleanup slice; it is the closure layer that consumes the prior runtime contracts.

### Review And Verify Rubrics Still Need Standards Binding

- Review surfaces are strong but do not yet consume one explicit principle-to-rubric mapping.
- Verify surfaces are the clearest gap: they remain evidence/spec oriented without one standards-bound verify rubric.
- Some docs still point at missing standards trees or incomplete canonical homes.

The repo therefore needs a late-wave standards binding layer, not only more prose.

### The Right Closure Layer Is Already Implicit In Earlier Decisions

- Spec-115 already established the principle split.
- Spec-117 already declares engineering principles and replacement-before-deletion.
- The closure work should finish wiring those decisions and define deletion manifests, parity proofs, rollback criteria, and adoption docs.

## High-Signal Findings

1. `HX-12` should consume earlier outputs rather than inventing a new standards architecture.
2. The highest-value boundary is a late-wave closure layer: canonical standards docs, principle-to-rubric mapping, migration/adoption docs, and family-by-family deletion governance.
3. Legacy retirement must remain serialized by family and gated by parity proof.
4. User-facing docs should update only after runtime contracts are real.

## Recommended Decision Direction

### Preferred Standards Direction

- Add one canonical harness-engineering standards context alongside the existing operational principles.
- Bind Clean Code, Clean Architecture, SOLID, DRY, KISS, YAGNI, TDD, SDD, and Harness Engineering into review and verify rubrics.
- Keep README and GETTING_STARTED trailing the implemented runtime contracts.

### Preferred Retirement Direction

- Build one family-by-family deletion manifest with replacement owner, parity proof, and rollback path.
- Retire one legacy family at a time only after its replacement slice is real and validated.
- Keep migration and adoption guidance tied to implemented artifacts, not aspirations.

## Migration Hazards

- Deleting constitutional or mirror surfaces too early will break bootstrap or provider parity.
- Reclassifying projections or reports too early will break downstream consumers.
- Publishing top-level standards prose too early will recreate second-source-of-truth drift.
- Legacy retirement will sprawl if not serialized by surface family.

## Scope Boundaries For HX-12

In scope:

- canonical standards canon
- standards binding into review and verify rubrics
- migration and adoption guide
- deletion manifest, parity proof, and rollback governance

Out of scope:

- reopening control-plane, mirror, kernel, state, capability, context, or eval ownership already assigned to prior HX slices
- premature user-facing doc updates for contracts that do not exist yet

## Open Questions

- What exact canonical home should Harness Engineering use?
- Which review and verify surfaces should consume the standards matrix first?
- Which legacy families should retire first once parity exists?
- How much adoption guidance belongs in root docs versus `.ai-engineering` docs?

## Source Artifacts Consulted

- `CONSTITUTION.md`
- `.ai-engineering/CONSTITUTION.md`
- `.ai-engineering/README.md`
- `.ai-engineering/contexts/operational-principles.md`
- `.ai-engineering/specs/spec-115-cross-ide-entry-point-governance-and-engineering-principles-standard.md`
- `.ai-engineering/specs/spec.md`
- `.ai-engineering/specs/spec-117-harness-engineering-context-pack.md`
- `.ai-engineering/specs/spec-117-hx-01-control-plane-normalization-explore.md`
- `.ai-engineering/specs/spec-117-hx-03-mirror-local-reference-model-explore.md`
- `.ai-engineering/specs/spec-117-hx-04-harness-kernel-unification-explore.md`
- `.ai-engineering/specs/spec-117-hx-05-state-plane-and-observability-normalization-explore.md`
- `.ai-engineering/specs/spec-117-hx-06-multi-agent-capability-contracts-explore.md`
- `.claude/skills/ai-code/SKILL.md`
- `.claude/agents/ai-build.md`
- `.claude/agents/reviewer-architecture.md`
- `.claude/agents/reviewer-correctness.md`
- `.claude/skills/ai-review/SKILL.md`
- `.claude/skills/ai-verify/SKILL.md`