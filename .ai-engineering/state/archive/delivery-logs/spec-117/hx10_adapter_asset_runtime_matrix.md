# HX-10 Adapter And Asset Runtime Matrix

## Scope

`HX-10` owns the first Track C proof that CLI command modules can delegate branching and sequencing to packaged runtime code while installed hook helpers carry an explicit runtime classification.

This matrix is intentionally narrow. It proves the boundary with `update_cmd` and the packaged hook helper registry, while leaving mirror family governance, kernel execution semantics, and reconciler convergence with `HX-03`, `HX-04`, and `HX-09`.

## CLI Adapter Boundary

| Surface | Current Role | Track C Boundary | Status |
| --- | --- | --- | --- |
| `src/ai_engineering/cli_commands/core.py::update_cmd` | Typer adapter for `ai-eng update`; previously mixed preview/apply branching with prompting and rendering. | CLI owns target resolution, JSON mode detection, spinner text, confirmation, result rendering, and exit behavior. | Implemented in Track C. |
| `src/ai_engineering/commands/update_workflow.py::run_update_workflow` | New packaged workflow seam for update preview/apply sequencing. | Packaged runtime owns interactive/non-interactive branching, dry-run/apply sequencing, no-change detection, decline handling, and update runner injection. | Implemented in Track C. |
| `src/ai_engineering/updater/service.py::update` | Existing mutation service for framework-managed update planning and apply. | Remains the mutation engine consumed by the workflow; no reconciler semantics reopened. | Preserved from Track B. |
| `src/ai_engineering/cli_commands/gate.py` | Large command module with gate orchestration. | Candidate for future adapter thinning, not owned by this slice. | Deferred. |
| `src/ai_engineering/cli_commands/setup.py` | Platform credential setup adapter. | Candidate for future extraction only if credential lifecycle needs packaged workflow ownership. | Deferred. |

## Hook Asset Runtime Boundary

| Asset Family | Runtime Class | Import Policy | Packaged Counterpart | Track C Rule |
| --- | --- | --- | --- | --- |
| `scripts/hooks/_lib/__init__.py` | `runtime-native` | `stdlib-only` | None | Keep standalone for hook package layout. |
| `scripts/hooks/_lib/hook_context.py` | `runtime-native` | `stdlib-only` | None | Keep standalone; fresh installs cannot assume package imports. |
| `scripts/hooks/_lib/injection_patterns.py` | `runtime-native` | `stdlib-only` | None | Keep standalone; prompt injection checks run from installed hooks. |
| `scripts/hooks/_lib/copilot-common.sh` | `runtime-native` | `shell-stdlib-only` | None | Keep shell-native helper. |
| `scripts/hooks/_lib/copilot-runtime.sh` | `runtime-native` | `shell-stdlib-only` | None | Keep shell-native helper. |
| `scripts/hooks/_lib/copilot-common.ps1` | `runtime-native` | `powershell-stdlib-only` | None | Keep PowerShell-native helper. |
| `scripts/hooks/_lib/copilot-runtime.ps1` | `runtime-native` | `powershell-stdlib-only` | None | Keep PowerShell-native helper. |
| `scripts/hooks/_lib/hook-common.py` | `stdlib-mirror` | `stdlib-only` | `ai_engineering.state.audit_chain`, `ai_engineering.state.event_schema` | Duplicates packaged concepts but is not reducible in this slice because installed hooks must remain stdlib-only. |
| `scripts/hooks/_lib/observability.py` | `stdlib-mirror` | `stdlib-only` | `ai_engineering.state.observability` | Classified as a mirror with provenance; no package import cutover. |
| `scripts/hooks/_lib/audit.py` | `stdlib-mirror` | `stdlib-only` | `ai_engineering.state.audit` | Classified as a mirror with provenance; no package import cutover. |
| `scripts/hooks/_lib/instincts.py` | `stdlib-mirror` | `stdlib-only` | `ai_engineering.state.instincts` | Classified as a mirror with provenance; no package import cutover. |

## Compatibility Boundary

- Public `ai-eng update` flags and output modes stay unchanged.
- Interactive update still previews first, prompts once, applies on confirmation, and leaves preview-only state on decline.
- Non-interactive update still runs once and uses `dry_run=not --apply`.
- JSON output remains an adapter concern in `core.py`.
- Hook helper installation paths remain unchanged.
- Stdlib-only hook helpers are classified before any reduction decision.
- No Track C change reopens mirror authority, execution kernel semantics, or reconciler lifecycle behavior.

## Validation Hooks

- `tests/unit/test_update_workflow.py` proves workflow-owned sequencing.
- `tests/integration/test_cli_command_modules.py` proves public update command parity.
- `tests/unit/test_hook_asset_runtime.py` proves every packaged hook helper is explicitly classified and that stdlib mirrors are not treated as safe deletions.
- `validate_hook_runtime_asset_registry()` is the reusable package-level invariant for missing or stale hook helper classifications.