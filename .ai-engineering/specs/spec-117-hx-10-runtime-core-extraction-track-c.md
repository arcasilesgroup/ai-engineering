---
spec: spec-117-hx-10
title: Runtime Core Extraction - Track C
status: done
effort: large
---

# Spec 117 HX-10 - Runtime Core Extraction - Track C

## Summary

ai-engineering already has thin CLI seams in parts of the repo, but several large command modules still mix parsing, prompting, branching, progress UX, persistence, and rendering. At the same time, some template-executed hook helpers duplicate packaged runtime logic, while still needing to remain stdlib-only for fresh installs. This feature thins CLI adapters, extracts orchestration and mutation into packaged services, and defines the minimum asset/runtime split for installed hook assets without stealing mirror ownership, kernel ownership, or reconciler ownership from adjacent tracks.

## Goals

- Thin oversized CLI command modules into parse/confirm/render adapters.
- Move branching, sequencing, and persistence into packaged services.
- Define which template assets are runtime-native versus duplicated packaged logic.
- Reduce duplicated executable logic where safe while preserving stdlib-only hook execution guarantees.
- Preserve existing good adapter seams.

## Non-Goals

- Re-owning mirror-family contract or provenance from `HX-03`.
- Re-owning kernel semantics from `HX-04`.
- Re-owning reconciler convergence from `HX-09`.
- Replacing runtime-native template assets that must stay standalone.

## Decisions

### D-117-66: CLI modules become thin adapters over packaged services

Command modules should keep parsing, confirmation, and rendering at the edge while packaged services own branching, sequencing, and mutation.

**Rationale**: the main debt is concentrated in a few broad command modules, while other CLI surfaces already show the target pattern.

### D-117-67: Asset/runtime split is based on execution constraints, not aesthetics

Template assets that must run stdlib-only outside the package remain runtime-native. Duplicated packaged logic should be reduced only where those execution constraints allow it.

**Rationale**: some hook helpers cannot simply import package code in fresh installs.

### D-117-68: Track C consumes earlier ownership boundaries

Mirror-family authority remains with `HX-03`, kernel execution semantics remain with `HX-04`, and reconciler convergence remains with `HX-09`.

**Rationale**: Track C should reduce adapter and asset-runtime debt without reopening earlier ownership decisions.

## Risks

- **Standalone-runtime risk**: replacing stdlib-only assets with package imports can break fresh installs. **Mitigation**: classify assets before deletion or merge.
- **Boundary-drift risk**: adapter cleanup can sprawl into mirror or kernel ownership. **Mitigation**: keep explicit out-of-scope boundaries.
- **Large-module risk**: broad command modules often mix several concerns and are easy to over-split. **Mitigation**: split by existing service seams and owned domains.

## Implementation Notes

- Added `src/ai_engineering/commands/update_workflow.py` as the packaged workflow seam for `ai-eng update` preview/apply sequencing.
- Routed `src/ai_engineering/cli_commands/core.py::update_cmd` through `run_update_workflow(...)` while preserving CLI parse, confirm, render, JSON envelope, spinner, and exit behavior at the adapter edge.
- Extracted residual adapter complexity in `src/ai_engineering/cli_commands/core.py` after SonarQube touched-file analysis flagged the module: install flow, pipeline step rendering, plan replay, update diff rendering, doctor rendering, and interactive doctor fix prompting now route through smaller helpers while preserving public command signatures.
- Added `src/ai_engineering/hooks/asset_runtime.py` with explicit hook helper runtime classifications and `validate_hook_runtime_asset_registry(...)` for missing or stale classification detection.
- Classified runtime-native hook helper assets separately from stdlib-only mirrors that have packaged counterparts but cannot safely import package code from fresh installed workspaces.
- Kept `gate.py` and `setup.py` as deferred candidates rather than widening Track C beyond the owned proof slice.
- Mirror-family authority from `HX-03`, kernel semantics from `HX-04`, and reconciler convergence from `HX-09` remain consumed rather than reopened.

## Verification

- Focused Ruff import/syntax checks passed for touched source and test files.
- Focused workflow/classifier/CLI integration tests passed: `36 passed in 0.35s`.
- Broader adjacent CLI/install/doctor/updater tests passed: `164 passed in 74.07s`.
- SonarQube for IDE touched-file analysis returned `findingsCount: 0`.
- Editor diagnostics reported no errors for touched source and test files before closeout.

## References

- doc: .ai-engineering/specs/spec-117-hx-10-runtime-core-extraction-track-c-explore.md
- doc: .ai-engineering/specs/spec-117-hx-03-mirror-local-reference-model.md
- doc: .ai-engineering/specs/spec-117-hx-04-harness-kernel-unification.md
- doc: .ai-engineering/specs/spec-117-hx-09-runtime-core-extraction-track-b.md
- doc: src/ai_engineering/cli_commands/
- doc: src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/

## Open Questions

- Runtime-native template helpers are listed in `.ai-engineering/specs/spec-117-progress/hx10_adapter_asset_runtime_matrix.md` and preserved when they require stdlib-only standalone execution.
- `update_cmd` was split first because it had clear preview/apply sequencing debt and strong existing integration coverage. `gate.py` and `setup.py` remain deferred candidates.
- Runtime-native helpers and stdlib mirrors declare provenance through `HookRuntimeAsset` metadata; stdlib mirrors list packaged counterparts but remain non-reducible while their import policy is `stdlib-only`.