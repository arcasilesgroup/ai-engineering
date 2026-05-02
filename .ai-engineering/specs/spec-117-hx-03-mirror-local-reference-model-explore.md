# HX-03 Explore - Mirror Local Reference Model

This artifact captures the evidence gathered before writing the feature spec for `HX-03`.

## Scope

Feature: `HX-03` Mirror Local Reference Model.

Question: what must change so provider mirrors become provider-local, generated, auditable, and explicit about which surfaces are public contracts versus internal orchestration assets?

## Evidence Summary

### Non-Claude Mirrors Still Depend On Claude-Local Paths And Conventions

- Generated non-Claude mirrors still contain `.claude/**` references and Claude-only execution assumptions.
- The current rewrite logic in `scripts/sync_command_mirrors.py` translates only a narrow set of canonical skill and agent paths.
- Handler paths, script-relative notes, and other local references are not normalized consistently for non-Claude mirrors.

This means provider-local mirrors are not actually self-contained yet.

### Provider Compatibility Is Encoded As Exceptions, Not As A Contract

- Compatibility handling is currently ad hoc, especially around Copilot-specific behavior.
- The repo has examples of provider-incompatible skills appearing in Gemini and Codex mirrors anyway.
- Provider-local enrichments such as Copilot metadata injection, slug normalization, and Gemini placeholder handling exist, but they are not modeled as first-class mirror contract rules.

The result is a mixed system where provider-specific behavior is real, but not centrally declared.

### Provenance And Generator Ownership Are Split Across Too Many Surfaces

- The real mirror generator is `scripts/sync_command_mirrors.py`.
- `.ai-engineering/manifest.yml` only partially models root instruction entry points, not the full mirror family universe.
- Installer/template logic, validators, docs, and tests each restate parts of the same mapping.
- Generated outputs do not carry uniform provenance markers or non-editability banners.

The repo therefore lacks one executable inventory that says what artifact family exists, where it comes from, how it is transformed, which providers receive it, and how it is validated.

### Public And Internal Surfaces Are Mixed

- First-class public skills and agents are defined at the governance level.
- Internal specialist review and verify surfaces exist as real files and can leak into public counts, catalogs, or mirrored navigation.
- The current repo does not enforce one explicit rule for what is publicly mirrored versus what remains an internal orchestration detail.

`HX-03` therefore needs to solve two things together: provider-local mirror correctness and a clear public/internal surface boundary.

### Validation And Governance Do Not Yet Protect The Intended Boundary

- `sync` and `validate` do not cover exactly the same mirror universe.
- Existing tests cover selected translation rules and special cases, but they do not assert the full provider-local invariant set.
- Governance prose promises generated, auditable mirrors more strongly than the runtime contract actually enforces today.

This is a drift problem, not only a text-rewrite problem.

## High-Signal Findings

1. `HX-03` cannot be reduced to replacing `.claude` strings in mirrored files.
2. The feature needs one artifact inventory for all governed mirror families, not only root entry points.
3. Provider-local enablement and provenance must become explicit contract fields, not code-only exceptions.
4. Public first-class surfaces and internal specialist surfaces must be split under the same feature or drift will continue.
5. `sync` and validator parity need the same reference model before any broad cleanup of mirrored content can be trusted.

## Recommended Decision Direction

### Preferred Artifact-Inventory Direction

- Define one mirror-family inventory that covers skills, agents, specialist agents, shared handlers, root overlays, generated instruction files, manual instruction files, provider root config files, and install-template projections.
- Model at least: authoritative source, generator, transform, provider, locality, targets, enablement predicate, edit policy, validation invariant, and orphan policy.
- Stop overloading one `canonical_source` field to mean both content source and generator implementation.

### Preferred Provider-Local Direction

- Non-Claude mirrors must have zero `.claude/**` references and zero Claude-only operational assumptions.
- Provider-specific enrichments should be explicitly declared and filtered by provider compatibility.
- Incompatible public surfaces should be omitted from a mirror or rendered as explicit unsupported stubs, never as silently broken copies.

### Preferred Public/Internal Boundary Direction

- Public mirrored surface means only manifest-registered first-class skills, manifest-registered first-class agents, root overlays, and user-facing instruction files.
- Internal review and verify specialists remain orchestration assets and must not inflate public counts or appear as peer public entry points.
- Public counts and parity checks should derive from the filtered public registry, not raw file counts.

## Migration Hazards

- Adding provenance banners or generated markers will churn many generated files and may break byte-equality tests.
- Filtering incompatible files from mirrors will affect public counts, docs, and possibly install flows.
- Normalizing only docs without collapsing duplicated path inventories in code will create another layer of drift.
- Moving too much canonical-placement governance into `HX-03` can bleed scope back into `HX-01` or forward into `HX-12`.
- Hidden edge families such as `_shared`, specialist agents, manual instructions, and provider root config files are easy to drop if the inventory is incomplete.

## Scope Boundaries For HX-03

In scope:

- mirror-family artifact inventory
- provider-local reference and compatibility contract
- provenance and generated/manual classification for mirrored public surfaces
- public versus internal surface boundary for mirrored families
- sync and validator convergence on the same mirror reference model

Out of scope:

- control-plane constitutional cleanup from `HX-01`
- work-plane and task-ledger implementation from `HX-02`
- harness kernel unification from `HX-04`
- broad engineering-standards canon work from `HX-12`
- stale prose cleanup outside mirror-facing surfaces unless it blocks provider-local correctness

## Open Questions

- Should internal specialist prompts remain as files under an internal namespace or be synthesized differently by orchestrators?
- Should incompatible public files be omitted entirely from a mirror or replaced with explicit unsupported stubs?
- Which provenance markers belong in-file versus git-level metadata such as generated classification?
- Should root-entry provenance cleanup for `AGENTS.md`, `GEMINI.md`, and Copilot overlays happen fully in `HX-03` or be split with a later control/documentation slice?
- Which provider-local root files belong under the mirror contract versus separate installer/runtime contracts?

## Source Artifacts Consulted

- `scripts/sync_command_mirrors.py`
- `.ai-engineering/manifest.yml`
- `src/ai_engineering/installer/templates.py`
- `src/ai_engineering/validator/_shared.py`
- `src/ai_engineering/validator/categories/mirror_sync.py`
- `src/ai_engineering/cli_commands/sync.py`
- `.github/workflows/ci-check.yml`
- `CONSTITUTION.md`
- `AGENTS.md`
- `README.md`
- `GETTING_STARTED.md`
- `docs/copilot-subagents.md`
- `.github/skills/ai-dispatch/SKILL.md`
- `.github/skills/ai-review/SKILL.md`
- `.github/skills/ai-verify/SKILL.md`
- `.github/agents/run-orchestrator.agent.md`
- `.gemini/skills/ai-dispatch/SKILL.md`
- `.codex/skills/ai-dispatch/SKILL.md`
- `.github/skills/ai-analyze-permissions/SKILL.md`
- `.gemini/skills/ai-analyze-permissions/SKILL.md`
- `.codex/skills/ai-analyze-permissions/SKILL.md`
- `.github/skills/ai-commit/SKILL.md`
- `.github/skills/ai-governance/SKILL.md`
- `.github/agents/verifier-governance.md`
- `.github/instructions/python.instructions.md`
- `.github/skills/ai-start/SKILL.md`
- `.github/agents/build.agent.md`
- `.codex/config.toml`
- `.codex/hooks.json`