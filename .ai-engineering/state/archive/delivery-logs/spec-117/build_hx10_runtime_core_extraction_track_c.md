# Build Packet: HX-10 Runtime Core Extraction - Track C

## Summary

Implemented the Track C adapter and asset/runtime proof with a bounded slice, then completed Sonar-driven adapter thinning in the touched CLI module:

- Added `src/ai_engineering/commands/update_workflow.py` so packaged runtime code owns update preview/apply sequencing.
- Routed `src/ai_engineering/cli_commands/core.py::update_cmd` through the workflow while keeping parse, confirm, render, JSON, spinner, and exit behavior at the CLI edge.
- Extracted helper seams in `src/ai_engineering/cli_commands/core.py` for install flow, pipeline step rendering, plan replay, update diff rendering, doctor rendering, and interactive doctor fix prompting after touched-file Sonar analysis surfaced residual adapter complexity.
- Added `src/ai_engineering/hooks/asset_runtime.py` with explicit hook helper runtime classifications and a reusable registry validator.
- Added focused unit coverage for workflow sequencing and hook helper classification.

## Files Changed

| Path | Change |
| --- | --- |
| `src/ai_engineering/commands/update_workflow.py` | New packaged workflow for `ai-eng update` preview/apply branching and sequencing. |
| `src/ai_engineering/cli_commands/core.py` | `update_cmd` now delegates sequencing to `run_update_workflow`; install, pipeline rendering, plan replay, update diff rendering, doctor rendering, and interactive fix prompting now use smaller adapter helpers. |
| `src/ai_engineering/hooks/asset_runtime.py` | New governed hook helper classification registry and validation surface. |
| `tests/unit/test_update_workflow.py` | New workflow sequencing tests for non-interactive preview/apply, interactive no-change, decline, and confirm paths. |
| `tests/unit/test_hook_asset_runtime.py` | New classification invariant tests for all packaged hook helpers and stdlib mirror provenance. |
| `.ai-engineering/specs/spec-117-progress/hx10_adapter_asset_runtime_matrix.md` | New Track C boundary matrix for adapter ownership and hook asset runtime classes. |

## Implementation Notes

### CLI Adapter Extraction

`run_update_workflow(...)` owns the behavior that previously made `update_cmd` more than an adapter:

- non-interactive dry-run versus apply selection,
- interactive preview-first sequencing,
- no-change short-circuit,
- confirmation callback requirement,
- decline versus apply status selection,
- injectable update runner for deterministic tests.

`update_cmd(...)` still owns the user interface contract:

- target resolution,
- JSON mode and TTY detection,
- spinner messages,
- confirmation prompt text,
- human rendering,
- JSON envelope rendering,
- Typer exit behavior.

`core.py` also received bounded helper extraction for residual command-adapter complexity detected by SonarQube for IDE. The public Typer command signatures stayed in place, while branching-heavy internals moved into narrow helper functions for install mode/configuration resolution, install execution and success rendering, pipeline step display, replay action handling, update diff display, doctor output, and interactive doctor fix prompts.

### Hook Asset Classification

`HookAssetRuntimeClass` separates installed helper assets into:

- `runtime-native`: assets that are part of the standalone installed hook runtime.
- `stdlib-mirror`: assets that mirror packaged runtime concepts but must remain stdlib-only in installed hooks.

`validate_hook_runtime_asset_registry(...)` verifies that every helper under `templates/.ai-engineering/scripts/hooks/_lib` is classified and that registry entries do not point at missing template files.

## Deferred Work

- `gate.py` and `setup.py` remain candidates for future adapter thinning; this slice avoids broad CLI churn.
- Runtime-native hook helpers are not replaced with package imports because installed hooks must run in fresh workspaces without assuming package availability.
- Mirror provenance remains governed by `HX-03`.
- Kernel semantics remain governed by `HX-04`.
- Reconciler lifecycle behavior remains governed by `HX-09`.

## Local Evidence

- Focused Ruff import/syntax check passed for touched Python files.
- Focused workflow/classifier/CLI integration tests passed: `36 passed in 0.35s`.
- Broader adjacent CLI/install/doctor/updater tests passed: `164 passed in 74.07s`.
- SonarQube for IDE touched-file analysis returned `findingsCount: 0`.
- Editor diagnostics reported no errors for touched source and test files before closeout.