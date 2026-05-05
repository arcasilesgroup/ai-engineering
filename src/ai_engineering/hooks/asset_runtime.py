"""Runtime classification for installed hook template assets."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from ai_engineering.installer.templates import get_ai_engineering_template_root


class HookAssetRuntimeClass(StrEnum):
    """Execution class for a hook template asset."""

    RUNTIME_NATIVE = "runtime-native"
    STDLIB_MIRROR = "stdlib-mirror"


@dataclass(frozen=True)
class HookRuntimeAsset:
    """Governed runtime metadata for one installed hook helper asset."""

    relative_path: Path
    runtime_class: HookAssetRuntimeClass
    import_policy: str
    rationale: str
    packaged_counterpart: str | None = None

    @property
    def is_reducible_duplicate(self) -> bool:
        """Return True when Track C may replace this asset with package imports."""
        return (
            self.runtime_class == HookAssetRuntimeClass.STDLIB_MIRROR
            and self.import_policy != _STDLIB_ONLY
        )


@dataclass(frozen=True)
class HookRuntimeAssetValidation:
    """Validation result for the hook runtime asset registry."""

    missing_classifications: tuple[Path, ...]
    stale_classifications: tuple[Path, ...]

    @property
    def passed(self) -> bool:
        """Return True when packaged helper assets and registry entries match."""
        return not self.missing_classifications and not self.stale_classifications


_HOOK_LIB_REL = Path("scripts") / "hooks" / "_lib"
_STDLIB_ONLY = "stdlib-only"
_SHELL_STDLIB_ONLY = "shell-stdlib-only"
_POWERSHELL_STDLIB_ONLY = "powershell-stdlib-only"

_HOOK_ASSET_REGISTRY: tuple[HookRuntimeAsset, ...] = (
    HookRuntimeAsset(
        relative_path=_HOOK_LIB_REL / "__init__.py",
        runtime_class=HookAssetRuntimeClass.RUNTIME_NATIVE,
        import_policy=_STDLIB_ONLY,
        rationale="Package marker for installed hook helper imports.",
    ),
    HookRuntimeAsset(
        relative_path=_HOOK_LIB_REL / "hook_context.py",
        runtime_class=HookAssetRuntimeClass.RUNTIME_NATIVE,
        import_policy=_STDLIB_ONLY,
        rationale="Discovers hook execution context before packaged runtime is available.",
    ),
    HookRuntimeAsset(
        relative_path=_HOOK_LIB_REL / "injection_patterns.py",
        runtime_class=HookAssetRuntimeClass.RUNTIME_NATIVE,
        import_policy=_STDLIB_ONLY,
        rationale="Prompt-injection pattern data must be available to standalone hooks.",
    ),
    HookRuntimeAsset(
        relative_path=_HOOK_LIB_REL / "copilot-common.sh",
        runtime_class=HookAssetRuntimeClass.RUNTIME_NATIVE,
        import_policy=_SHELL_STDLIB_ONLY,
        rationale="Shell hook support runs outside the Python package in installed workspaces.",
    ),
    HookRuntimeAsset(
        relative_path=_HOOK_LIB_REL / "copilot-runtime.sh",
        runtime_class=HookAssetRuntimeClass.RUNTIME_NATIVE,
        import_policy=_SHELL_STDLIB_ONLY,
        rationale="Shell launcher must remain standalone for fresh installed workspaces.",
    ),
    HookRuntimeAsset(
        relative_path=_HOOK_LIB_REL / "copilot-common.ps1",
        runtime_class=HookAssetRuntimeClass.RUNTIME_NATIVE,
        import_policy=_POWERSHELL_STDLIB_ONLY,
        rationale="PowerShell hook support runs outside the Python package in installed workspaces.",
    ),
    HookRuntimeAsset(
        relative_path=_HOOK_LIB_REL / "copilot-runtime.ps1",
        runtime_class=HookAssetRuntimeClass.RUNTIME_NATIVE,
        import_policy=_POWERSHELL_STDLIB_ONLY,
        rationale="PowerShell launcher must remain standalone for fresh installed workspaces.",
    ),
    HookRuntimeAsset(
        relative_path=_HOOK_LIB_REL / "hook-common.py",
        runtime_class=HookAssetRuntimeClass.STDLIB_MIRROR,
        import_policy=_STDLIB_ONLY,
        rationale="Mirrors event schema and audit-chain behavior for hooks that cannot import the package.",
        packaged_counterpart="ai_engineering.state.event_schema; ai_engineering.state.audit_chain",
    ),
    HookRuntimeAsset(
        relative_path=_HOOK_LIB_REL / "observability.py",
        runtime_class=HookAssetRuntimeClass.STDLIB_MIRROR,
        import_policy=_STDLIB_ONLY,
        rationale="Mirrors framework event emission for installed hooks.",
        packaged_counterpart="ai_engineering.state.observability",
    ),
    HookRuntimeAsset(
        relative_path=_HOOK_LIB_REL / "audit.py",
        runtime_class=HookAssetRuntimeClass.STDLIB_MIRROR,
        import_policy=_STDLIB_ONLY,
        rationale="Mirrors audit helpers needed by installed hook scripts.",
        packaged_counterpart="ai_engineering.state.audit",
    ),
    HookRuntimeAsset(
        relative_path=_HOOK_LIB_REL / "instincts.py",
        runtime_class=HookAssetRuntimeClass.STDLIB_MIRROR,
        import_policy=_STDLIB_ONLY,
        rationale="Mirrors instinct capture needed by installed hook scripts.",
        packaged_counterpart="ai_engineering.state.instincts",
    ),
    HookRuntimeAsset(
        relative_path=_HOOK_LIB_REL / "integrity.py",
        runtime_class=HookAssetRuntimeClass.RUNTIME_NATIVE,
        import_policy=_STDLIB_ONLY,
        rationale="Hook bytes integrity verification must run before packaged runtime is trusted.",
    ),
    HookRuntimeAsset(
        relative_path=_HOOK_LIB_REL / "runtime_state.py",
        runtime_class=HookAssetRuntimeClass.RUNTIME_NATIVE,
        import_policy=_STDLIB_ONLY,
        rationale="Spec-116 runtime layer state (checkpoint, tool history) must be writable from standalone hooks.",
    ),
    HookRuntimeAsset(
        relative_path=_HOOK_LIB_REL / "trace_context.py",
        runtime_class=HookAssetRuntimeClass.RUNTIME_NATIVE,
        import_policy=_STDLIB_ONLY,
        rationale="Spec-120 trace-context propagation must run before the packaged runtime is trusted.",
    ),
    HookRuntimeAsset(
        relative_path=_HOOK_LIB_REL / "transcript_usage.py",
        runtime_class=HookAssetRuntimeClass.RUNTIME_NATIVE,
        import_policy=_STDLIB_ONLY,
        rationale="Spec-120 transcript/token-usage capture runs from standalone hooks before the package is importable.",
    ),
    HookRuntimeAsset(
        relative_path=_HOOK_LIB_REL / "convergence.py",
        runtime_class=HookAssetRuntimeClass.RUNTIME_NATIVE,
        import_policy=_STDLIB_ONLY,
        rationale=(
            "Spec-116 Ralph Loop convergence sweep runs from "
            "runtime-stop.py before the packaged runtime is trusted."
        ),
    ),
    HookRuntimeAsset(
        relative_path=_HOOK_LIB_REL / "hook_http.py",
        runtime_class=HookAssetRuntimeClass.RUNTIME_NATIVE,
        import_policy=_STDLIB_ONLY,
        rationale=(
            "Spec-121 fail-open HTTP sink for opt-in audit telemetry; must "
            "run from standalone hooks before the package is importable."
        ),
    ),
    HookRuntimeAsset(
        relative_path=_HOOK_LIB_REL / "risk_accumulator.py",
        runtime_class=HookAssetRuntimeClass.RUNTIME_NATIVE,
        import_policy=_STDLIB_ONLY,
        rationale=(
            "Spec-120 PRISM-style session risk accumulator runs from "
            "prompt-injection-guard before the packaged runtime is available."
        ),
    ),
)


def list_hook_runtime_assets() -> list[HookRuntimeAsset]:
    """Return governed metadata for installed hook helper assets."""
    return list(_HOOK_ASSET_REGISTRY)


def classify_hook_runtime_asset(relative_path: Path) -> HookRuntimeAsset | None:
    """Return runtime metadata for a hook helper path, if governed."""
    normalized = Path(relative_path.as_posix())
    for asset in _HOOK_ASSET_REGISTRY:
        if asset.relative_path == normalized:
            return asset
    return None


def hook_runtime_template_root() -> Path:
    """Return the packaged template root containing hook helper assets."""
    return get_ai_engineering_template_root()


def validate_hook_runtime_asset_registry(
    template_root: Path | None = None,
) -> HookRuntimeAssetValidation:
    """Validate that packaged hook helper files have runtime classifications."""
    root = template_root or hook_runtime_template_root()
    helper_root = root / _HOOK_LIB_REL
    packaged = {
        path.relative_to(root)
        for path in helper_root.iterdir()
        if path.is_file() and path.suffix in {".py", ".sh", ".ps1"}
    }
    classified = {asset.relative_path for asset in _HOOK_ASSET_REGISTRY}

    return HookRuntimeAssetValidation(
        missing_classifications=tuple(sorted(packaged - classified)),
        stale_classifications=tuple(sorted(classified - packaged)),
    )
