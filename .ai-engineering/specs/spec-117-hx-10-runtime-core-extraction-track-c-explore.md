# HX-10 Explore - Runtime Core Extraction Track C

This artifact captures the evidence gathered before writing the feature spec for `HX-10`.

## Scope

Feature: `HX-10` Runtime Core Extraction - Track C.

Question: what must change so CLI command modules become thin adapters and template-executed runtime logic is reduced to the minimum necessary runtime assets without stealing mirror or kernel ownership?

## Evidence Summary

### The CLI Already Has Good Thin-Adapter Examples

- CLI boot and registration are already relatively thin.
- Several command modules already parse input, call one service, and render output cleanly.

This shows the target shape already exists in parts of the repo.

### The Main Pressure Is Concentrated In A Few Large Command Modules

- `cli_commands/core.py`, `gate.py`, `setup.py`, and parts of `maintenance.py` still mix prompting, branching, progress UX, subprocess or file orchestration, persistence, and rendering.
- Those modules are the strongest candidates for adapter extraction.

### Template Runtime Duplication Is Real But Constrained

- Hook runtime helper code duplicates pieces of observability, instincts, event schema, and hash-chain behavior.
- Those template assets are stdlib-only by design and cannot simply import packaged runtime code in fresh installs.
- Not every template hook is duplicate logic; some are truly standalone runtime-native assets.

This means Track C must reduce duplication carefully rather than assuming all template logic can be deleted.

### Some Duplication Belongs To Other Features

- Mirror topology and provider-local path authority belong primarily to `HX-03`.
- Kernel semantics and local execution authority belong to `HX-04`.
- Reconciler convergence belongs to `HX-09`.

Track C should therefore focus on CLI adapter boundaries and the minimum asset/runtime split, not on re-owning earlier slices.

## High-Signal Findings

1. The highest-value boundary is: CLI modules parse, confirm, and render; packaged services own branching, sequencing, and persistence; installed hook assets keep only the minimum stdlib runtime required outside the package.
2. Large command modules are the main adapter debt, not the CLI bootstrap.
3. Template hook duplication cannot be naively replaced with package imports because fresh installs rely on stdlib-only execution.
4. Some duplication families should be left to `HX-03` or `HX-09` rather than being absorbed here.

## Recommended Decision Direction

### Preferred CLI Direction

- Thin out the oversized command modules by moving orchestration and mutation into packaged services.
- Keep parsing, confirmation, and rendering at the CLI edge.
- Preserve good service seams and adapter examples already present.

### Preferred Asset/Runtime Direction

- Keep only the minimum stdlib-only hook runtime that must execute outside the package.
- Reduce duplicated packaged logic in templates where safe and where install/runtime guarantees allow it.
- Classify template assets as runtime-native versus duplicated mirror of packaged logic.

## Migration Hazards

- Replacing stdlib-only hook mirrors with package imports would break fresh installs or standalone execution.
- Pulling mirror-family ownership into Track C would duplicate `HX-03`.
- Pulling reconciler or kernel semantics into Track C would duplicate `HX-09` or `HX-04`.

## Scope Boundaries For HX-10

In scope:

- oversized CLI adapter thinning
- packaged-service extraction from broad command modules
- minimum asset/runtime split for hooks and template assets

Out of scope:

- mirror-family contract from `HX-03`
- kernel semantics from `HX-04`
- reconciler convergence from `HX-09`

## Open Questions

- Which template assets remain permanently runtime-native?
- Which large CLI modules should be split first to maximize value and minimize blast radius?
- How should runtime-native template helpers declare provenance relative to packaged code?

## Source Artifacts Consulted

- `src/ai_engineering/cli.py`
- `src/ai_engineering/cli_factory.py`
- `src/ai_engineering/cli_commands/**`
- `src/ai_engineering/commands/workflows.py`
- `src/ai_engineering/installer/templates.py`
- `src/ai_engineering/hooks/manager.py`
- `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/**`
- `.ai-engineering/specs/spec-117-hx-03-mirror-local-reference-model.md`
- `.ai-engineering/specs/spec-117-hx-04-harness-kernel-unification.md`
- `.ai-engineering/specs/spec-117-hx-09-runtime-core-extraction-track-b.md`