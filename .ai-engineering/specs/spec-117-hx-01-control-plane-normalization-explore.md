# HX-01 Explore - Control Plane Normalization

This artifact captures the evidence gathered before writing the feature spec for `HX-01`.

## Scope

Feature: `HX-01` Control Plane Normalization.

Question: what must be normalized so ai-engineering has one deterministic control plane instead of split constitutional authority, mixed manifest ownership, and duplicated provenance assumptions?

## Evidence Summary

### Constitutional Authority Is Split

- Root governance treats `CONSTITUTION.md` as the hard-rule authority and `AGENTS.md` as the shared startup contract.
- The workspace runtime also loads `.ai-engineering/CONSTITUTION.md` as an active constitution through `.ai-engineering/manifest.yml` and records it in the event stream.
- This is not a dormant duplication. It is an active dual-authority problem affecting bootstrap, runbooks, and runtime state.

### Manifest Authority Is Mixed By Field, Not By File

- `.ai-engineering/manifest.yml` contains both operator-authored inputs and framework-managed/generated sections.
- Some manifest regions are operationally consumed at runtime, while other fields are effectively descriptive only.
- The repo currently lacks a per-field authority table, which causes confusion over what is canonical and what is projection or lineage metadata.

### Ownership Enforcement Does Not Come From One Source

- Ownership is described in the manifest.
- Ownership is enforced by state defaults and updater/doctor logic.
- Ownership is persisted in `.ai-engineering/state/ownership-map.json` as a generated projection.
- These three layers can drift because they do not share one authoritative resolver.

### Provenance Is Duplicated And Sometimes Contradictory

- Root-surface provenance for `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, and provider overlays is encoded across manifest metadata, sync scripts, validators, templates, tests, and prose docs.
- `AGENTS.md` and `GEMINI.md` already have conflicting provenance stories depending on which surface is consulted.
- Generated-vs-source semantics are therefore not deterministic.

### Validation Covers Only Parts Of The Problem

- `manifest_coherence` checks structural basics but does not validate real ownership/provenance authority.
- `mirror_sync` is the strongest current control-plane validator, but it still encodes hard-coded parity assumptions.
- Many control-plane invariants are enforced only indirectly through tests or doctor phases rather than one explicit contract.

### Generated Projections Already Drift

- `.ai-engineering/state/framework-capabilities.json` is stale relative to the manifest.
- `.ai-engineering/state/ownership-map.json` retains legacy patterns that are no longer aligned with current defaults.
- README counts and control-plane descriptions have already drifted from manifest truth.

## High-Signal Findings

1. `HX-01` cannot be framed as a simple rename or doc cleanup.
2. The first hard decision is constitutional: root `CONSTITUTION.md` vs workspace `.ai-engineering/CONSTITUTION.md` must stop behaving as peer constitutions.
3. The second hard decision is authority modeling: manifest, generated projections, and descriptive docs need a deterministic canonical/projection split.
4. The third hard decision is execution safety: readers, validators, updater logic, and tests need a compatibility-first migration path before any naming or path cutover.

## Recommended Decision Direction

### Preferred Constitutional Direction

- Make root `CONSTITUTION.md` the sole constitutional authority for this repository.
- Rename, reduce, or demote `.ai-engineering/CONSTITUTION.md` into a workspace charter or project-policy artifact.
- Keep downstream workspace customization possible, but remove dual sovereignty.

### Preferred Authority Direction

- Introduce a per-field control-plane authority table.
- Treat operator-authored manifest inputs as canonical.
- Treat `ownership-map.json` and `framework-capabilities.json` as generated projections, not peer authorities.
- Keep README and runbooks descriptive only.

### Preferred Enforcement Direction

- Build a single ownership/provenance resolver used by validator, updater, doctor, sync, observability, and tests.
- Add compatibility-first dual-read support before renaming or deleting any live field or path.

## Migration Hazards

- Tests are likely to break before validators because current integration coverage asserts exact governance keys and provenance fields.
- Renaming constitutions or control-plane fields without a compatibility resolver will break observability, audit, updater, and doctor flows.
- Changing live manifest semantics without updating the template manifest in lockstep will split source repo and installed workspace behavior.
- File-existence and cross-reference coverage are not yet broad enough to protect all control-plane paths.

## Scope Boundaries For HX-01

In scope:

- Constitutional authority resolution.
- Canonical vs generated control-plane classification.
- Ownership/provenance single-source contract.
- Compatibility-first migration and validator/test hardening.

Out of scope:

- Mirror-local reference rewrites beyond the minimum control-plane provenance needed for this feature.
- Work-plane and task-ledger implementation.
- Runtime extractions unrelated to control-plane resolvers.

## Open Questions

- Should the demoted workspace constitution keep the `CONSTITUTION.md` name, or must the rename happen in `HX-01` itself?
- Should `framework-capabilities.json` remain committed, become a generated snapshot, or move to runtime residue?
- Which manifest fields are truly operator-owned vs discovered/generated state, especially under `work_items`?
- Should prompt-only bootstrap fields remain in manifest or move to skill/context contracts?

## Source Artifacts Consulted

- `CONSTITUTION.md`
- `AGENTS.md`
- `CLAUDE.md`
- `.github/copilot-instructions.md`
- `.ai-engineering/CONSTITUTION.md`
- `.ai-engineering/manifest.yml`
- `.ai-engineering/README.md`
- `.ai-engineering/state/ownership-map.json`
- `.ai-engineering/state/framework-capabilities.json`
- `src/ai_engineering/config/manifest.py`
- `src/ai_engineering/state/defaults.py`
- `src/ai_engineering/state/models.py`
- `src/ai_engineering/updater/service.py`
- `src/ai_engineering/doctor/phases/state.py`
- `src/ai_engineering/validator/categories/manifest_coherence.py`
- `src/ai_engineering/validator/categories/mirror_sync.py`
- `scripts/sync_command_mirrors.py`
