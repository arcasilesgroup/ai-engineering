---
spec: spec-117-hx-03
title: Mirror Local Reference Model
status: done
effort: large
---

# Spec 117 HX-03 - Mirror Local Reference Model

## Summary

ai-engineering currently treats mirrors as a partial generation system rather than one explicit contract. Non-Claude mirrors still leak `.claude` paths and Claude-only execution assumptions, provider compatibility is handled as scattered exceptions, provenance and ownership are split across generator code, manifest metadata, installer logic, validators, tests, and prose docs, and public first-class surfaces are mixed with internal review and verify specialists. This feature defines one provider-local mirror contract, one artifact inventory for governed mirror families, one clear public/internal surface boundary, and one provenance model that `sync`, validators, installer/template logic, and tests can share.

## Goals

- Define one governed inventory for all mirror families that matter to provider-local operation.
- Make non-Claude mirrors self-contained and free of `.claude` path leaks or Claude-only operational assumptions.
- Turn provider compatibility and provider-local enrichments into explicit contract fields instead of code-only exceptions.
- Distinguish public mirrored surfaces from internal orchestration assets so counts, catalogs, and navigation reflect the real supported contract.
- Make provenance, generated/manual classification, and edit policy explicit and consistent across mirrored public surfaces.
- Converge `sync`, validator logic, installer/template logic, and tests on the same mirror reference model.
- Preserve compatibility while mirror families, counts, and generated outputs change under a controlled migration.

## Non-Goals

- Reworking constitutional authority or broader control-plane ownership from `HX-01`.
- Implementing work-plane or task-ledger behavior from `HX-02`.
- Unifying the harness kernel or broader check engine from `HX-04`.
- Performing broad stale-doc cleanup outside mirror-facing surfaces unless it is required for provider-local correctness.
- Treating internal specialist prompts as new user-facing public entry points.
- Adding more mirror families or providers without a concrete runtime or install consumer.

## Decisions

### D-117-24: Mirror governance is modeled by artifact family, not only by root entry point

`HX-03` introduces one explicit inventory for governed mirror families, including at minimum skills, agents, internal specialist assets, shared handlers, root overlays, generated instruction files, manual instruction files, provider-local root config files, and install-template projections.

**Rationale**: the current contract only partially models root entry points, while the actual mirror universe is much larger and is already spread across generator code, installer logic, validators, tests, and docs.

### D-117-25: Provider-local mirrors must be self-contained and filtered by compatibility

Every mirrored public surface must be valid for its target provider. Non-Claude mirrors cannot depend on `.claude/**` paths or Claude-only execution assumptions. Provider-specific enrichments and exclusions must be expressed as explicit compatibility rules.

**Rationale**: today non-Claude mirrors still ship broken local references and incompatible skills because compatibility lives in scattered exceptions rather than an auditable contract.

### D-117-26: Public mirrored surface is a filtered first-class registry, not a raw file tree

Public mirrored surface means only first-class registered skills, first-class registered agents, root overlays, and user-facing instruction files. Internal review and verify specialists remain orchestration assets and must not appear as peer public entry points or inflate public counts.

**Rationale**: the repo already distinguishes first-class public contract from specialist orchestration internals conceptually, but the mirror system does not enforce that boundary.

### D-117-27: Generated provenance and edit policy must be explicit and uniform

Generated mirrored outputs must declare provenance, generator identity, target/provider locality, and non-editability in a consistent way. Manual instruction files and provider-local handwritten files must remain clearly classified as manual.

**Rationale**: generated status is currently promised more strongly in governance prose than it is enforced in generated files and runtime validation.

### D-117-28: `sync`, installer/template logic, validators, and tests must consume one mirror reference model

The runtime reference model for mirrors must converge so generator mappings, template destinations, validator path inventories, parity rules, CI checks, and tests all derive from the same contract.

**Rationale**: today mirror families and path mappings are restated in multiple places, which is the main reason mirror drift survives local fixes.

### D-117-29: `HX-03` is compatibility-first and keeps mirror sequencing explicit

Mirror cleanup lands behind compatibility support and deterministic sequencing. Sync generation completes before mirror validation or parity checks, and public-count or provider-filter changes must update the downstream docs/tests they affect in the same slice.

**Rationale**: mirror and validation drift already causes transient or confusing failures when generation, parity checks, and documentation counts move out of order.

## Risks

- **Generated-surface churn**: provenance banners and filtered outputs will change many generated files at once. **Mitigation**: make tests contract-aware before flipping broad generated output.
- **Count and catalog drift**: filtering internal specialists or incompatible files can break docs and tests that assume raw file counts. **Mitigation**: derive counts from the filtered public registry and update generated overlays in the same slice.
- **Hidden family loss**: `_shared`, specialist prompts, manual instruction files, and provider-local root files are easy to miss. **Mitigation**: complete the artifact-family inventory before aggressive cleanup.
- **Scope bleed into governance cleanup**: root overlay provenance and canonical-placement prose overlap with earlier and later features. **Mitigation**: keep `HX-03` focused on mirror correctness, public/internal boundary, and executable provenance, not all documentation cleanup.
- **Installer/runtime divergence**: normalizing only checked-in mirrors without template/install parity would recreate source-vs-installed drift. **Mitigation**: move live and template mirror contracts together.

## Deferred Cleanup From HX-03

- `HX-04` owns any future kernel-level serialization of mirror-affecting local flows. `HX-03` now requires ordered `sync`, updater, and validation behavior, but it does not turn that sequencing into one unified harness authority.
- `HX-06` owns the capability-level policy that is still implicit in mirror helpers: provider compatibility, public versus internal topology role, and generated/manual mutation authority for mirror-mutating tasks must become machine-readable capability data there rather than mirror-specific conventions here.
- `HX-12` owns the long-term retirement or canonical preservation policy for intentionally retained manual instruction families such as `testing.instructions.md`, `markdown.instructions.md`, and `sonarqube_mcp.instructions.md`, plus any remaining compatibility-only loader semantics once all runtime callers are fully strict.

## Deferred Cleanup From HX-01

- `HX-01` normalized constitutional authority but intentionally left root-first plus workspace-charter fallback guidance in mirrored runbooks, provider-local skills, and template/manual instruction families. `HX-03` owns the eventual rewrite or retirement of that mirrored alias guidance once provider-local surfaces no longer need migration-time fallback instructions.

## References

- doc: .ai-engineering/specs/spec-117-hx-03-mirror-local-reference-model-explore.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-refactor-roadmap.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-feature-portfolio.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-task-catalog.md
- doc: scripts/sync_command_mirrors.py
- doc: .ai-engineering/manifest.yml
- doc: src/ai_engineering/installer/templates.py
- doc: src/ai_engineering/validator/_shared.py
- doc: src/ai_engineering/validator/categories/mirror_sync.py
- doc: src/ai_engineering/cli_commands/sync.py
- doc: .github/workflows/ci-check.yml
- doc: CONSTITUTION.md
- doc: AGENTS.md
- doc: README.md
- doc: GETTING_STARTED.md
- doc: docs/copilot-subagents.md

## Open Questions

- Should incompatible public artifacts be omitted entirely from a mirror or represented as explicit unsupported stubs?
- Should internal specialist prompts remain as files under an internal namespace or be synthesized differently behind the public agents?
- Which provenance signals belong in-file versus git-level generated classification?
- Should root-overlay provenance cleanup for `AGENTS.md`, `GEMINI.md`, and Copilot instructions land fully inside `HX-03` or remain partially deferred?
- Which provider-local root files should be governed by the mirror contract versus a later installer/runtime contract?