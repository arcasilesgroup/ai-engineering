"""spec-101 manifest projections: required_tools, sdk_per_stack, python_env.mode.

This module is a NEW spec-101-specific loader -- distinct from
``ai_engineering.config.loader``. It reads ``.ai-engineering/manifest.yml``
once and projects the typed sub-blocks needed by the installer, doctor,
and policy stack-runner consumers:

* :func:`load_required_tools` -- baseline + per-stack tool union, with
  stack-level platform skips applied (D-101-13).
* :func:`load_sdk_prereqs` -- SDK prerequisites for the 9 SDK-required
  stacks (D-101-14). Falls back to canonical defaults from spec.md when
  the manifest does not declare the block.
* :func:`load_python_env_mode` -- the ``python_env.mode`` flag with safe
  default of :class:`PythonEnvMode.UV_TOOL` (D-101-12).

``UnknownStackError`` is raised when a caller passes a stack name that is
not present in the canonical 14-stack registry.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import platform as _platform_mod
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from ai_engineering.state.models import (
    Platform,
    PythonEnvMode,
    RequiredToolsBlock,
    SdkPrereq,
    StackSpec,
    ToolSpec,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from collections.abc import Iterable

__all__ = [
    "SDK_REQUIRED_STACKS",
    "LoadResult",
    "PythonEnvMode",
    "StackSkip",
    "UnknownStackError",
    "compute_tool_spec_hash",
    "load_python_env_mode",
    "load_required_tools",
    "load_sdk_prereqs",
]


# Canonical 9 SDK-required stacks (spec.md D-101-14).
SDK_REQUIRED_STACKS: frozenset[str] = frozenset(
    {"java", "kotlin", "swift", "dart", "csharp", "go", "rust", "php", "cpp"}
)

# Canonical 14 declared stack names (spec.md D-101-01); used for unknown-stack
# detection when the manifest's required_tools block is absent.
_CANONICAL_STACKS: frozenset[str] = frozenset(
    {
        "python",
        "typescript",
        "javascript",
        "java",
        "csharp",
        "go",
        "php",
        "rust",
        "kotlin",
        "swift",
        "dart",
        "sql",
        "bash",
        "cpp",
    }
)

# Canonical SDK prereqs from spec.md D-101-14 -- used as fallback when the
# manifest does not declare ``prereqs.sdk_per_stack``.
_CANONICAL_SDK_PREREQS: dict[str, dict[str, str]] = {
    "java": {
        "name": "JDK",
        "min_version": "21",
        "install_link": "https://adoptium.net/",
    },
    "kotlin": {
        "name": "JDK",
        "min_version": "21",
        "install_link": "https://adoptium.net/",
    },
    "swift": {
        "name": "Swift toolchain",
        "install_link": "https://www.swift.org/install/",
    },
    "dart": {
        "name": "Dart SDK",
        "install_link": "https://dart.dev/get-dart",
    },
    "csharp": {
        "name": ".NET SDK",
        "min_version": "9",
        "install_link": "https://dotnet.microsoft.com/download",
    },
    "go": {
        "name": "Go toolchain",
        "install_link": "https://go.dev/dl/",
    },
    "rust": {
        "name": "Rust toolchain",
        "install_link": "https://rustup.rs/",
    },
    "php": {
        "name": "PHP",
        "min_version": "8.2",
        "install_link": "https://www.php.net/downloads",
    },
    "cpp": {
        "name": "clang/LLVM",
        "install_link": "https://llvm.org/builds/",
    },
}


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class UnknownStackError(ValueError):
    """Raised when a stack name is not present in the canonical registry."""


@dataclasses.dataclass(frozen=True)
class StackSkip:
    """Skip-reason marker for a stack filtered out by ``platform_unsupported_stack``.

    ``tool_names`` carries the names of every tool the skipped stack WOULD have
    contributed -- the installer needs this list so it can record per-tool
    ``skipped_platform_unsupported_stack`` entries in :class:`InstallState`
    (D-101-13). The list is empty when the stack declared no tools.
    """

    stack: str
    reason: str
    tool_names: tuple[str, ...] = ()


class LoadResult:
    """Container for ``load_required_tools`` output.

    Iterating yields the resolved :class:`ToolSpec` instances (so callers can
    write ``for tool in result``); ``skipped_stacks`` carries the per-stack
    skip-reason markers for stacks dropped via ``platform_unsupported_stack``
    (D-101-13).
    """

    __slots__ = ("skipped_stacks", "tools")

    def __init__(self, tools: list[ToolSpec], skipped_stacks: list[StackSkip]) -> None:
        self.tools = tools
        self.skipped_stacks = skipped_stacks

    def __iter__(self) -> Iterator[ToolSpec]:
        return iter(self.tools)

    def __len__(self) -> int:
        return len(self.tools)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _PythonEnvWrapper(BaseModel):
    """Schema wrapper that surfaces ``ValidationError`` for invalid modes."""

    mode: PythonEnvMode = PythonEnvMode.UV_TOOL


def _read_raw_manifest(root: Path) -> dict[str, Any]:
    """Return the raw manifest dict, or ``{}`` when absent / unreadable."""
    # Delayed to keep projection imports acyclic while the repository wraps this module.
    from ai_engineering.state.repository import ManifestRepository

    return ManifestRepository(root).load_raw()


def _normalise_os(current_os: str | None) -> Platform | None:
    """Map a ``platform.system()``-style string onto :class:`Platform`.

    Returns ``None`` for unknown OS names so callers can treat missing OS as
    "no platform skip applies".
    """
    name = (current_os or _platform_mod.system() or "").strip().lower()
    if not name:
        return None
    try:
        return Platform(name)
    except ValueError:
        return None


def _resolve_required_tools_block(data: dict[str, Any]) -> RequiredToolsBlock | None:
    """Validate and return the ``required_tools`` sub-block, or ``None``."""
    raw = data.get("required_tools")
    if not isinstance(raw, dict):
        return None
    return RequiredToolsBlock.model_validate(raw)


# ---------------------------------------------------------------------------
# Public loaders
# ---------------------------------------------------------------------------


def load_required_tools(
    stacks: Iterable[str],
    *,
    root: Path | None = None,
    current_os: str | None = None,
) -> LoadResult:
    """Resolve the union of baseline + per-stack tools for the given stacks.

    Parameters
    ----------
    stacks:
        The stack names the project has declared (``providers.stacks``).
    root:
        Repository root containing ``.ai-engineering/manifest.yml``. When
        ``None``, the current working directory is used.
    current_os:
        Optional OS override (defaults to ``platform.system()``); mostly
        useful for tests. Compared case-insensitively against
        :class:`Platform`.

    Returns
    -------
    LoadResult
        ``tools`` carries the resolved :class:`ToolSpec` instances (baseline
        first, then per-stack in the order requested). ``skipped_stacks``
        carries :class:`StackSkip` markers for stacks dropped via
        ``platform_unsupported_stack`` on the current OS (D-101-13).

    Raises
    ------
    UnknownStackError
        If a stack name is not declared in either the manifest's
        ``required_tools`` block or the canonical 14-stack registry.
    """
    project_root = (root or Path.cwd()).resolve()
    data = _read_raw_manifest(project_root)
    block = _resolve_required_tools_block(data)
    os_platform = _normalise_os(current_os)

    requested = list(stacks)
    if block is None:
        # No required_tools block -- still validate stack names against the
        # canonical 14-stack registry so unknown stacks fail loudly.
        for name in requested:
            if name not in _CANONICAL_STACKS:
                msg = f"unknown stack: {name}"
                raise UnknownStackError(msg)
        return LoadResult(tools=[], skipped_stacks=[])

    tools: list[ToolSpec] = list(block.baseline.tools)
    skipped: list[StackSkip] = []

    for name in requested:
        stack_spec = _stack_from_block(block, name)
        if stack_spec is None:
            msg = f"unknown stack: {name}"
            raise UnknownStackError(msg)

        if _stack_is_skipped(stack_spec, os_platform):
            skipped.append(
                StackSkip(
                    stack=name,
                    reason=stack_spec.unsupported_reason or "",
                    tool_names=tuple(t.name for t in stack_spec.tools),
                )
            )
            continue

        tools.extend(stack_spec.tools)

    return LoadResult(tools=tools, skipped_stacks=skipped)


def _stack_from_block(block: RequiredToolsBlock, name: str) -> StackSpec | None:
    """Return the named ``StackSpec`` from the block, or ``None`` if absent."""
    if name not in _CANONICAL_STACKS:
        return None
    return getattr(block, name, None)


def _stack_is_skipped(stack: StackSpec, os_platform: Platform | None) -> bool:
    """Return True when the stack's ``platform_unsupported_stack`` covers OS."""
    unsupported = stack.platform_unsupported_stack
    if not unsupported or os_platform is None:
        return False
    return os_platform in unsupported


def load_sdk_prereqs(
    stacks: Iterable[str],
    *,
    root: Path | None = None,
) -> list[SdkPrereq]:
    """Return SDK prerequisites for SDK-required stacks (D-101-14).

    Filters the input stack list to the 9 SDK-required stacks. For each, the
    canonical :class:`SdkPrereq` is sourced from
    ``manifest.prereqs.sdk_per_stack`` when present, otherwise from the
    spec.md canonical defaults. Non-SDK stacks (python, typescript, etc.)
    are silently dropped -- the framework ships with their toolchain
    (D-101-12 for python; project-local for TypeScript).
    """
    project_root = (root or Path.cwd()).resolve()
    data = _read_raw_manifest(project_root)
    declared: dict[str, Any] = {}
    prereqs = data.get("prereqs")
    if isinstance(prereqs, dict):
        per_stack = prereqs.get("sdk_per_stack")
        if isinstance(per_stack, dict):
            declared = per_stack

    out: list[SdkPrereq] = []
    for name in stacks:
        if name not in SDK_REQUIRED_STACKS:
            continue
        entry = declared.get(name) if isinstance(declared.get(name), dict) else None
        if entry is None:
            entry = _CANONICAL_SDK_PREREQS[name]
        out.append(SdkPrereq.model_validate(entry))
    return out


def compute_tool_spec_hash(spec: Any) -> str:
    """Return SHA256 of a canonical-JSON tool spec entry (spec-107 D-107-09).

    Used by the H1 rug-pull detection wiring in :mod:`ai_engineering.installer.service`
    to detect silent mutation of declared tool specs across install cycles. The hash
    is stable across runs because:

    - ``sort_keys=True`` produces a deterministic key ordering.
    - ``separators=(",", ":")`` strips whitespace so cosmetic changes to the manifest
      do not register as semantic mismatches.
    - Pydantic model inputs (``ToolSpec``) are coerced via ``.model_dump(mode="json")``
      so enum values serialize as their string form (D-101-01 invariants).

    Returns the 64-char hex digest. The empty-spec case (``{}`` or ``None``)
    returns the canonical SHA256 of ``"{}"`` so callers always receive a string.

    Args:
        spec: Either a raw dict (manifest YAML projection) or a Pydantic model
            with ``.model_dump`` (e.g., :class:`ToolSpec`). ``None`` is treated
            as an empty dict.

    Returns:
        Hex-encoded SHA256 of the canonical-JSON serialization.
    """
    if spec is None:
        payload: Any = {}
    elif hasattr(spec, "model_dump"):
        payload = spec.model_dump(mode="json")
    else:
        payload = spec
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_python_env_mode(root: Path) -> PythonEnvMode:
    """Return ``manifest.python_env.mode`` defaulting to ``UV_TOOL`` (D-101-12).

    Returns :class:`PythonEnvMode.UV_TOOL` when the manifest is missing, the
    ``python_env`` block is absent, or the ``mode`` key is absent. Invalid
    values (e.g. ``"legacy-venv"``) raise :class:`pydantic.ValidationError`.
    """
    data = _read_raw_manifest(root)
    block = data.get("python_env")
    if not isinstance(block, dict):
        return PythonEnvMode.UV_TOOL
    if "mode" not in block:
        return PythonEnvMode.UV_TOOL

    return _PythonEnvWrapper.model_validate({"mode": block["mode"]}).mode
