# Phase 0 Extension-Point Notes (spec-101, T-0.2)

Read-only exploration. Documents exact line numbers, current shapes, and
ownership patterns subsequent Phase 0 + Phase 1 tasks must respect.

All paths are relative to the repository root unless otherwise noted.

---

## 1. `src/ai_engineering/state/models.py`

**Library**: `pydantic.BaseModel` (NOT `@dataclass`). All models derive from
`BaseModel` with `model_config = {"populate_by_name": True}` where camelCase
aliases exist. The plan T-0.4 phrasing of "frozen dataclass" is informal -- match
the existing **Pydantic** convention: `class X(BaseModel)` + `Field(...)` for
defaults/aliases.

### Existing models (in declaration order)

| Line | Class | Kind |
|---|---|---|
| 26  | `OwnershipLevel` | `StrEnum` |
| 36  | `FrameworkUpdatePolicy` | `StrEnum` |
| 44  | `GateHook` | `StrEnum` (PRE_COMMIT, COMMIT_MSG, PRE_PUSH) |
| 52  | `AiProvider` | `StrEnum` |
| 61  | `RiskCategory` | `StrEnum` |
| 69  | `RiskSeverity` | `StrEnum` |
| 78  | `DecisionStatus` | `StrEnum` |
| 91  | `UpdateMetadata` | BaseModel |
| 104 | `OwnershipEntry` | BaseModel |
| 114 | `OwnershipMap` | BaseModel |
| 193 | `Decision` | BaseModel (schema 1.1) |
| 220 | `DecisionStore` | BaseModel |
| 257 | `AuditEntry` | BaseModel (legacy) |
| 288 | `FrameworkEvent` | BaseModel |
| 313 | `CapabilityDescriptor` | BaseModel |
| 322 | `FrameworkCapabilitiesCatalog` | BaseModel |
| 342 | `InstinctObservation` | BaseModel |
| 357 | `InstinctMeta` | BaseModel |
| 370 | `ToolEntry` | BaseModel (installed/authenticated/integrity_verified/mode/scopes) |
| 384 | `CredentialRef` | BaseModel |
| 395 | `PlatformEntry` | BaseModel |
| 408 | `BranchPolicyState` | BaseModel |
| 417 | `OperationalState` | BaseModel |
| 424 | `ReleaseState` | BaseModel |
| 431 | `InstallState` | BaseModel (schema_version="2.0") |
| 512 | `_extract_tooling_from_dict` | helper |
| 555 | `_extract_platforms_from_dict` | helper |

### Where T-0.4 / T-0.10 / T-0.12 / T-0.14 must add new models

Plan tasks add: `ToolSpec`, `StackSpec`, `SdkPrereq`, `PythonEnvMode` enum,
`ToolInstallRecord`, plus extend `InstallState` with two fields
(`required_tools_state`, `python_env_mode_recorded`).

Recommended insertion point: **between line 363 (end of `InstinctMeta`) and
line 366 (`# --- InstallState (spec-068: state unification) ---` section
header)**, OR fold inside the existing `# --- InstallState` section just above
`class InstallState` at line 430.

Style requirements -- inferred from the existing module:

- Use `class X(BaseModel)` (NOT `@dataclass`).
- Enums use `StrEnum`. New `PythonEnvMode` should follow the existing
  `class PythonEnvMode(StrEnum): UV_TOOL = "uv-tool"; VENV = "venv"; SHARED_PARENT = "shared-parent"`.
- Use `Field(default_factory=...)` for collections.
- Add docstrings (one-liner OK, the file is heavily documented).
- Imports already cover `BaseModel`, `Field`, `StrEnum`, `datetime`, `UTC`,
  `Any` -- no new imports needed unless `Literal` is used.
- `from __future__ import annotations` is set; forward refs OK.

### Ordering hint for T-0.14

`InstallState.required_tools_state: dict[str, ToolInstallRecord]` -- key is the
tool name, **not** the stack. Plan T-0.13 enumerates ToolInstallRecord enum
states: `installed`, `skipped_platform_unsupported`,
`skipped_platform_unsupported_stack`, `not_installed_project_local`,
`failed_needs_manual`. Use a separate `StrEnum` (e.g.
`ToolInstallState`) and reference from `ToolInstallRecord.state`.

Preserve `schema_version: str = "2.0"` -- bumping is a separate concern
(handled implicitly by the legacy migration in T-0.16, which renames
`install-state.json` to `.legacy-<ts>` rather than bumping the version).

---

## 2. `src/ai_engineering/state/service.py`

### How `InstallState` is loaded/saved (free functions, not class methods)

- **Load**: `load_install_state(state_dir: Path) -> InstallState` at line 66.
  - Reads `state_dir / "install-state.json"`.
  - File-absent path returns `InstallState()` (defaults). 
  - Validates via `InstallState.model_validate(data)` at line 82.
- **Save**: `save_install_state(state_dir: Path, state: InstallState) -> None`
  at line 86.
  - Creates `state_dir` if missing (line 95).
  - Writes pretty JSON via `state.model_dump_json(indent=2)`.
- **Class facade** `StateService` at line 25 covers DecisionStore,
  OwnershipMap, FrameworkEvent, FrameworkCapabilities **but NOT InstallState**
  -- InstallState uses free functions instead. Honor this convention; do NOT
  add `load_install_state` to the class.

### Where T-0.16 legacy migration hooks in

Inject migration logic **inside `load_install_state`** (lines 66-83). The
plan's R-10 / T-0.15 spec is: when the file exists but is missing the new
required fields (`required_tools_state` or `python_env_mode_recorded`), rename
to `install-state.json.legacy-<ts>` and return a fresh `InstallState()`.
Implementation outline: parse JSON, peek at top-level keys, detect missing,
rename, return defaults.

There is also `from_legacy_dict` at line 450 of `state/models.py` -- that is a
**different** legacy path (manifest+tools.json migration from spec-068) and is
NOT relevant to T-0.16.

---

## 3. `src/ai_engineering/cli_commands/validate.py`

### `validate_cmd` signature -- line 31

```python
def validate_cmd(
    target: Annotated[Path | None, typer.Argument(...)] = None,
    category: Annotated[str | None, typer.Option("--category", "-c", ...)] = None,
    output_json: Annotated[bool, typer.Option("--json", ...)] = False,
) -> None:
```

Categories enum lives at `validator/service.py` (`IntegrityCategory`); the CLI
maps user-facing names via `_CATEGORY_NAMES` dict at line 28.

### Where the new `required_tools` lint plugs in (T-0.8)

The validator architecture is: `validator/service.py::validate_content_integrity`
returns a report whose categories are enumerated by `IntegrityCategory` -- a
StrEnum. Sub-checks live under `validator/categories/*.py` (`manifest_coherence.py`
already exists -- this is the natural extension target).

**Minimal plug-in path**:
1. Add a new check function inside `validator/categories/manifest_coherence.py`
   (or a sibling `required_tools.py` module if size warrants).
2. The new check is automatically picked up if it follows the existing
   category-registration pattern -- VERIFY by reading
   `validator/service.py` and `validator/categories/__init__.py` before T-0.8.
3. The CLI surface (`validate_cmd`) does NOT need editing -- the new check
   appears under an existing or new `IntegrityCategory` value. T-0.8 must
   either reuse `manifest-coherence` or extend `IntegrityCategory` and update
   `_CATEGORY_NAMES`. The plan task description says "Extend
   `cli_commands/validate.py`" -- interpret as "ensure the CLI surfaces the
   new category" (one-line addition to the enum + map if a new category is
   added; otherwise zero edits to the CLI file).

Open question: does Phase 0 plan want a new `required-tools` category or a
fold-in under `manifest-coherence`? Plan does not specify. **Recommend
fold-in** to keep the CLI flag surface stable.

---

## 4. `src/ai_engineering/installer/phases/tools.py`

### Module shape

`PhasePlan` / `PhaseResult` / `PhaseVerdict` / `PlannedAction` /
`InstallContext` are imported from the parent package (`from . import ...`).
The class `ToolsPhase` (line 24) implements `name`, `plan`, `execute`, `verify`
methods.

### Helpers imported from `installer/tools.py`

```python
from ai_engineering.installer.tools import ensure_tool, manual_install_step, provider_required_tools
```

These are the surfaces being **replaced** by T-2.2 (rewrite phase to use
`user_scope_install`).

### Critical line references for plan T-2.2

- **Line 37** `required = provider_required_tools(context.vcs_provider)` --
  the VCS-only scope.
- **Line 57** -- same call, in the `execute` method.
- **Line 60** `ensure_tool(tool_name, allow_install=True)` -- single-tool
  install path; replace with the registry-driven mechanism resolution.
- **`installer/tools.py:47`** is where `_PIP_INSTALLABLE` lives (NOT in
  `phases/tools.py`); plan task description says "line 47" -- that refers to
  the parent `installer/tools.py` module.
- **`installer/tools.py:220`** `provider_required_tools(provider)` returns
  `list[str]` from `_VCS_PROVIDER_TOOLS` dict at line 40 (`{"github": ["gh"],
  "azure_devops": ["az"]}`). VCS-only -- it does NOT consider stacks.

### Functions to replace in T-2.2

1. `ToolsPhase.plan` (lines 35-49) -- rebuild from `load_required_tools(stacks)`.
2. `ToolsPhase.execute` (lines 55-67) -- delegate to `user_scope_install`.
3. `ToolsPhase.verify` (lines 73-78) is currently a stub; plan does not
   directly require changes but EXIT-80 surfacing happens via this layer.

### Where to obtain `resolved_stacks`

`InstallContext` (imported at line 13 from `from . import InstallContext`)
**must surface `resolved_stacks`**. Today, only `vcs_provider` is read
(line 37). T-2.2 will need to add `context.resolved_stacks` access -- verify
the field exists on `InstallContext` before T-2.2 (it likely does because
`cli_commands/core.py:238+` already builds `resolved_stacks` and threads them
through pipeline construction).

---

## 5. `src/ai_engineering/doctor/phases/tools.py`

### Hardcoded `_REQUIRED_TOOLS` -- line 20

```python
_REQUIRED_TOOLS: list[str] = ["ruff", "ty", "gitleaks", "semgrep", "pip-audit"]
```

5 tools, baseline-only, no stack awareness. **T-3.2 must replace this** with
`load_required_tools(resolved_stacks)`.

### Functions to refactor in T-3.2

| Function | Lines | Action |
|---|---|---|
| `_check_tools_required` | 28-47 | Replace `_REQUIRED_TOOLS` literal with `load_required_tools(stacks).names()`. Use `is_tool_available()` from `detector/readiness.py`. |
| `_check_tools_vcs` | 50-86 | KEEP -- still valid for `_VCS_TOOL_MAP`. |
| `_check_venv_health` | 105-139 | T-3.4: branch on `python_env.mode`; return `not_applicable` when mode is `uv-tool`. |
| `_check_venv_python` | 142-183 | Same `python_env.mode` branch likely required. |
| `check` | 186-193 | Aggregator; no signature change. |
| `_fix_tools_required` | 223-293 | Rewrite to delegate to `user_scope_install` instead of `RemediationEngine.remediate_missing_tools`. |
| `_fix_venv_health` | 296-340 | Branch on `python_env.mode`. |

**DoctorContext** (line 16) is the access point for `install_state`. The new
modes will require `DoctorContext` to expose `python_env_mode` -- verify
elsewhere (likely in `doctor/models.py`).

---

## 6. `src/ai_engineering/hooks/manager.py`

### Bash hook generator -- lines 83-88

```python
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
if [ -d "$ROOT_DIR/.venv/bin" ]; then
  export PATH="$ROOT_DIR/.venv/bin:$PATH"
elif [ -d "$ROOT_DIR/.venv/Scripts" ]; then
  export PATH="$ROOT_DIR/.venv/Scripts:$PATH"
fi
```

Plain string interpolation inside the f-string returned by
`generate_bash_hook` (lines 56-91).

### PowerShell hook generator -- lines 113-115

```python
$RootDir = (Resolve-Path "$PSScriptRoot/../..").Path
$VenvBin = Join-Path $RootDir '.venv/Scripts'
if (Test-Path $VenvBin) {{ $env:PATH = "$VenvBin;$env:PATH" }}
```

### D-101-12 mode-handling branch points (T-2.22)

For each mode the preamble must change as follows:

| `python_env.mode` | Bash (lines 83-88) | PowerShell (lines 113-115) |
|---|---|---|
| `uv-tool` | OMIT venv-prepend block entirely | OMIT venv-prepend block |
| `venv` (current default behaviour) | KEEP existing block | KEEP existing block |
| `shared-parent` | EXPORT `UV_PROJECT_ENVIRONMENT="$(git rev-parse --git-common-dir)/../.venv"` | EXPORT `$env:UV_PROJECT_ENVIRONMENT = ...` |

T-2.22 must thread `python_env.mode` into `generate_bash_hook` /
`generate_powershell_hook` -- their current signatures take only `hook:
GateHook`. Adding a `mode` parameter is the cleanest path; callers (line 138
`generate_dispatcher_hook`, line 221 `install_hooks`) need updating.

`install_hooks` (line 180) reads/writes `InstallState` via
`_record_hook_hashes` (line 327). The mode value should be sourced from
manifest at install time and recorded in `InstallState.python_env_mode_recorded`
(T-0.14) so subsequent `verify_hooks` can detect drift.

---

## 7. `src/ai_engineering/policy/checks/stack_runner.py`

### `PRE_COMMIT_CHECKS` -- lines 115-133

`dict[str, list[CheckConfig]]`. Keys: `common`, `python`, `dotnet`, `nextjs`.
4 stacks total. Hardcoded.

### `PRE_PUSH_CHECKS` -- lines 136-178

Same shape. Same 4 stacks. Hardcoded check `cmd` lists.

### `CheckConfig` dataclass -- lines 16-21

```python
@dataclass
class CheckConfig:
    name: str
    cmd: list[str]
    required: bool = True
    timeout: int = 300
```

### `run_tool_check` `shutil.which` -- line 288

```python
tool_name = cmd[0]
if not shutil.which(tool_name):
    if required:
        ...
        f"{tool_name} not found — required. "
        "Run 'ai-eng doctor --fix --phase tools' to install."
```

### Plan T-2.24 hook points

The data-driven refactor must:
1. Replace `PRE_COMMIT_CHECKS` and `PRE_PUSH_CHECKS` literals with a runtime
   build from `load_required_tools(stacks)` -- each tool spec contributes its
   verify cmd into the appropriate hook stage.
2. Where a tool is `scope=project_local`, dispatch through
   `installer/launchers.py::resolve_project_local` (T-1.14) instead of direct
   PATH invocation at line 288.
3. `run_checks_for_stacks` (line 243) is the entry point -- only its registry
   construction changes; the iteration shape stays.
4. `_resolve_python_checks` (line 181) is python-stack-specific path
   resolution -- KEEP. The new registry must still pass through it for the
   python stack.

Stage classification: spec-101 manifest must declare per-tool which gate stage
the verify cmd belongs to (pre-commit, pre-push, both). Likely a new field on
`ToolSpec` -- VERIFY in T-0.4 design.

---

## 8. Cross-cutting concerns

### `resolved_stacks` -- `cli_commands/core.py` lines 238-272

Plan-stated location confirmed. Built in three branches:

- **Reconfigure wizard branch** (line 238): `wizard_result.stacks`.
- **Reinstall branch** (line 245): `resolved.get("stacks", config.providers.stacks or ["python"])`.
- **First install branch** (lines 256, 268): from CLI flags, detection, or
  wizard.

After resolution, `resolved_stacks` flows into pipeline construction (further
down `core.py`) and ultimately into `InstallContext`. **T-2.2 must not
recompute `resolved_stacks` -- read from `InstallContext`.**

### `manifest.yml` parsing

- Loader: `from ai_engineering.config.loader import load_manifest_config` at
  `config/__init__.py:3`.
- **Function**: `load_manifest_config(root: Path) -> ManifestConfig` at
  `config/loader.py:31`.
- **Mutator**: `update_manifest_field(root, field_path, value)` at
  `config/loader.py:100`. Used elsewhere for staged updates.
- `ManifestConfig` is a Pydantic model exposing `providers.stacks`,
  `ai_providers.enabled`, `providers.ides`, `providers.vcs` (etc.).

T-0.6 / T-0.10 / T-0.12 (`state/manifest.py`) is a NEW module distinct from
`config/loader.py`. Naming is confusing -- the plan says "state/manifest.py"
(spec-101 own loader for `required_tools` / `prereqs.sdk_per_stack` /
`python_env.mode`). DO NOT collide with `config/loader.py`.
**Recommendation**: read `manifest.yml` via existing `load_manifest_config`
inside the new `state/manifest.py` and project the typed sub-blocks
(`required_tools`, `prereqs.sdk_per_stack`, `python_env.mode`) onto the new
models. This avoids duplicate YAML I/O.

### Import patterns

- `from __future__ import annotations` is universal in this codebase.
- Models -> `from ai_engineering.state.models import X`.
- Avoid wildcard imports.
- Prefer free functions for state I/O (matches `state/service.py:66/86`
  convention).

---

## 9. Open questions for subsequent tasks

1. **OQ-T0.4-Pydantic-vs-dataclass**: plan task wording ("frozen dataclass")
   conflicts with the actual codebase convention (Pydantic BaseModel).
   Recommendation: BaseModel + `model_config = {"frozen": True}` for the
   registry-style structures (`ToolSpec`, `StackSpec`, `SdkPrereq`); regular
   BaseModel for the runtime state record (`ToolInstallRecord`).

2. **OQ-T0.8-validate-category-extension**: should `required_tools` lint be a
   new `IntegrityCategory` value (visible via `ai-eng validate -c
   required-tools`) OR fold under `manifest-coherence`? Plan does not
   specify. **Recommend new category** -- governance owners need a way to
   re-run only this check.

3. **OQ-T0.16-state-rename-strategy**: rename to
   `install-state.json.legacy-<ts>` -- which timestamp format? Plan says
   `<ts>` -- recommend ISO-8601 basic (`20260424T093000Z`) or unix epoch.
   Document in T-0.16 implementation.

4. **OQ-T2.2-InstallContext-shape**: confirm `InstallContext` exposes
   `resolved_stacks` AND `python_env_mode` BEFORE writing T-2.2 GREEN code.
   Likely an `installer/__init__.py` or `installer/context.py` change is
   needed; plan does not call this out explicitly.

5. **OQ-T2.22-mode-source**: the hook generator currently has no manifest
   access. Threading a `mode: PythonEnvMode` parameter requires the caller
   (`install_hooks` at line 180) to load manifest -- where does manifest
   loading happen? Likely already done by `cli_commands/core.py` and threaded
   into the install pipeline; verify before T-2.22.

6. **OQ-T2.24-stage-classification**: each ToolSpec needs to declare which
   gate stage(s) its verify cmd belongs in. Plan T-0.4 lists ToolSpec fields
   (`name`, `scope`, `platform_unsupported`, `unsupported_reason`) but NOT
   stage. Add `gate_stages: list[Literal["pre-commit", "pre-push"]]` (or
   similar) to ToolSpec at T-0.4 to unblock T-2.24.

7. **OQ-validator-categories-registry**: plan does not say where new validator
   categories register. Read `validator/categories/__init__.py` and
   `validator/service.py` BEFORE T-0.8 -- the registration mechanism is
   load-bearing.

---

## Quick-reference table for downstream tasks

| Task | Target file | Primary line/anchor |
|---|---|---|
| T-0.4 (ToolSpec/StackSpec) | `state/models.py` | insert at line ~366 |
| T-0.6 (load_required_tools) | NEW `state/manifest.py` | -- |
| T-0.8 (validate lint) | `validator/categories/<file>.py` | -- |
| T-0.14 (InstallState extend) | `state/models.py` | line 431 |
| T-0.16 (legacy migration) | `state/service.py` | line 66-83 |
| T-2.2 (installer phase) | `installer/phases/tools.py` | lines 35-67 |
| T-2.22 (hook mode) | `hooks/manager.py` | lines 83-88, 113-115 |
| T-2.24 (data-driven runner) | `policy/checks/stack_runner.py` | lines 115-178 |
| T-3.2 (doctor refactor) | `doctor/phases/tools.py` | lines 20, 28-47 |
| T-3.4 (venv health branch) | `doctor/phases/tools.py` | lines 105-139 |

End of phase-0-notes.md.
