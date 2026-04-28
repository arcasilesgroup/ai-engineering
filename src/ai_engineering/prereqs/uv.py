"""uv prereq checks for spec-101 (D-101-11 + D-101-14).

The framework's own Python tool installer routes through ``uv tool install``
(D-101-12), so ``uv`` is a HARD prerequisite. Two failure modes surface here:

* **Absent** -- ``uv`` not found on PATH (or not in DRIVER_BINARIES).
* **Out of range** -- ``uv --version`` returns a value outside the manifest's
  ``prereqs.uv.version_range`` SpecifierSet (PEP 440 specifier syntax).

Both raise :class:`PrereqMissing` / :class:`PrereqOutOfRange` so the install
CLI can map them onto :data:`EXIT_PREREQS_MISSING` (81). The version-range
check is applied to the cleaned version string after stripping any
``uv `` prefix that ``uv --version`` emits (``"uv 0.5.2 (homebrew)"``).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

from ai_engineering.cli_commands._exit_codes import PrereqMissing, PrereqOutOfRange

__all__ = (
    "_check_uv_in_range",
    "_load_uv_version_range",
    "_query_uv_version",
    "check_uv_prereq",
)


_MANIFEST_REL = Path(".ai-engineering") / "manifest.yml"
_UV_VERSION_RE = re.compile(r"\b(\d+(?:\.\d+){0,3}(?:[-+][\w.\-]+)?)\b")


def _query_uv_version() -> str | None:
    """Return the bare version string from ``uv --version`` or None on failure.

    The function exists so tests can patch a single seam to inject a
    deterministic version string. The production path runs the actual
    subprocess; tests substitute a stub.
    """
    if shutil.which("uv") is None:
        return None
    try:
        completed = subprocess.run(
            ["uv", "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None

    output = (completed.stdout or completed.stderr or "").strip()
    if not output:
        return None
    match = _UV_VERSION_RE.search(output)
    return match.group(1) if match else None


def _load_uv_version_range(root: Path) -> str | None:
    """Return the ``prereqs.uv.version_range`` from manifest, or None.

    The manifest is read directly (rather than via ``ManifestConfig``) so the
    loader doesn't fail when other manifest blocks are absent. Returns ``None``
    when the manifest is missing, the block is absent, or the value is not a
    string.
    """
    manifest_path = root / _MANIFEST_REL
    if not manifest_path.is_file():
        return None
    try:
        raw = manifest_path.read_text(encoding="utf-8")
        data: Any = yaml.safe_load(raw)
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    prereqs = data.get("prereqs")
    if not isinstance(prereqs, dict):
        return None
    uv_block = prereqs.get("uv")
    if not isinstance(uv_block, dict):
        return None
    range_spec = uv_block.get("version_range")
    if isinstance(range_spec, str) and range_spec.strip():
        return range_spec.strip()
    return None


def _check_uv_in_range(version_range_spec: str) -> None:
    """Raise :class:`PrereqOutOfRange` if installed uv is outside the range.

    Args:
        version_range_spec: PEP 440 specifier, e.g. ``">=0.4.0,<1.0"``.

    Raises:
        PrereqMissing: ``uv`` not found on PATH.
        PrereqOutOfRange: ``uv`` is present but its version sits outside the
            specifier range.
    """
    version_str = _query_uv_version()
    if version_str is None:
        msg = (
            "prereq missing: 'uv' was not found on PATH. "
            "Install it via https://docs.astral.sh/uv/getting-started/installation/."
        )
        raise PrereqMissing(msg)

    try:
        version = Version(version_str)
    except InvalidVersion:
        msg = (
            f"prereq out of range: 'uv' reported an unparseable version "
            f"{version_str!r}; expected a PEP 440-compatible version."
        )
        raise PrereqOutOfRange(msg) from None

    specifier = SpecifierSet(version_range_spec)
    if version not in specifier:
        msg = (
            f"prereq out of range: 'uv' version {version_str} is outside the "
            f"declared range {version_range_spec!r} "
            f"(prereqs.uv.version_range in .ai-engineering/manifest.yml)."
        )
        raise PrereqOutOfRange(msg)


def check_uv_prereq(root: Path) -> None:
    """Run the uv prereq sweep -- absence + version-range check.

    Test seam: when ``AIENG_TEST=1`` and
    ``AIENG_TEST_SIMULATE_PREREQ_MISSING=uv`` are set, the function raises
    :class:`PrereqMissing` without touching subprocess. This keeps the
    integration-test surface deterministic without needing root-level
    monkey-patching of ``shutil.which`` or PATH.

    Args:
        root: Project root containing ``.ai-engineering/manifest.yml``.

    Raises:
        PrereqMissing: ``uv`` is absent OR a test-only simulation says so.
        PrereqOutOfRange: ``uv`` is present but out of the manifest's range.
    """
    if os.getenv("AIENG_TEST") == "1" and os.getenv("AIENG_TEST_SIMULATE_PREREQ_MISSING") == "uv":
        msg = "prereq missing: 'uv' simulated absent via AIENG_TEST_SIMULATE_PREREQ_MISSING."
        raise PrereqMissing(msg)

    range_spec = _load_uv_version_range(root)
    if range_spec is None:
        # No declared range -- bare-presence check only.
        if _query_uv_version() is None:
            msg = (
                "prereq missing: 'uv' was not found on PATH. "
                "Install it via https://docs.astral.sh/uv/getting-started/installation/."
            )
            raise PrereqMissing(msg)
        return
    _check_uv_in_range(range_spec)
