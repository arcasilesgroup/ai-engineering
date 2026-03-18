"""Version detection, validation, comparison, and bump helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|[0-9A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|[0-9A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


@dataclass
class BumpResult:
    """Result for stack-specific version bumping."""

    files_modified: list[Path]
    old_version: str
    new_version: str


def validate_semver(version: str) -> bool:
    """Validate semver (supports prerelease and build metadata)."""
    return _SEMVER_RE.fullmatch(version) is not None


def _parse_semver(version: str) -> tuple[int, int, int, tuple[int, str, object] | None]:
    match = _SEMVER_RE.fullmatch(version)
    if not match:
        msg = f"Invalid semver: {version}"
        raise ValueError(msg)

    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3))
    prerelease = match.group(4)
    pre_key: tuple[int, str, object] | None = None
    if prerelease is not None:
        parts = prerelease.split(".")
        normalized: list[tuple[int, object]] = []
        for part in parts:
            if part.isdigit():
                normalized.append((0, int(part)))
            else:
                normalized.append((1, part))
        pre_key = (0, ".".join(parts), tuple(normalized))
    return major, minor, patch, pre_key


def compare_versions(current: str, new: str) -> int:
    """Compare semver versions.

    Returns -1 (current < new), 0 (equal), 1 (current > new).
    """
    c_major, c_minor, c_patch, c_pre = _parse_semver(current)
    n_major, n_minor, n_patch, n_pre = _parse_semver(new)

    c_core = (c_major, c_minor, c_patch)
    n_core = (n_major, n_minor, n_patch)
    if c_core < n_core:
        return -1
    if c_core > n_core:
        return 1

    # Same core: release > prerelease
    if c_pre is None and n_pre is None:
        return 0
    if c_pre is None and n_pre is not None:
        return 1
    if c_pre is not None and n_pre is None:
        return -1

    # Narrowing: both branches are guaranteed non-None at this point
    if c_pre is None or n_pre is None:
        msg = "unreachable: pre-release None after guard clauses"
        raise AssertionError(msg)
    c_parts = c_pre[2]
    n_parts = n_pre[2]
    c_norm = c_parts if isinstance(c_parts, tuple) else ()
    n_norm = n_parts if isinstance(n_parts, tuple) else ()
    for c_part, n_part in zip(c_norm, n_norm, strict=False):
        if c_part == n_part:
            continue
        c_kind, c_val = c_part
        n_kind, n_val = n_part
        if c_kind != n_kind:
            return -1 if c_kind < n_kind else 1
        if c_val < n_val:
            return -1
        return 1

    if len(c_norm) < len(n_norm):
        return -1
    if len(c_norm) > len(n_norm):
        return 1
    return 0


def detect_current_version(project_root: Path) -> str:
    """Read current version from pyproject.toml."""
    pyproject = project_root / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"\s*$', text, flags=re.MULTILINE)
    if not match:
        msg = f"Unable to find project version in {pyproject}"
        raise ValueError(msg)
    return match.group(1).strip()


def _find_version_file(project_root: Path) -> Path:
    direct = project_root / "src" / "ai_engineering" / "__version__.py"
    if direct.exists():
        return direct

    candidates = sorted((project_root / "src").glob("*/__version__.py"))
    if not candidates:
        msg = "Could not locate __version__.py under src/"
        raise FileNotFoundError(msg)
    return candidates[0]


def bump_python_version(project_root: Path, new_version: str) -> BumpResult:
    """Bump version in pyproject.toml and __version__.py."""
    if not validate_semver(new_version):
        msg = f"Invalid semver version: {new_version}"
        raise ValueError(msg)

    pyproject = project_root / "pyproject.toml"
    version_file = _find_version_file(project_root)
    old_version = detect_current_version(project_root)

    py_text = pyproject.read_text(encoding="utf-8")
    py_updated, py_count = re.subn(
        r'^(version\s*=\s*")([^"]+)("\s*)$',
        rf"\g<1>{new_version}\3",
        py_text,
        count=1,
        flags=re.MULTILINE,
    )
    if py_count != 1:
        msg = f"Unable to update version in {pyproject}"
        raise ValueError(msg)

    ver_text = version_file.read_text(encoding="utf-8")
    ver_updated, ver_count = re.subn(
        r'^(__version__\s*=\s*")([^"]+)("\s*)$',
        rf"\g<1>{new_version}\3",
        ver_text,
        count=1,
        flags=re.MULTILINE,
    )
    if ver_count != 1:
        msg = f"Unable to update __version__ in {version_file}"
        raise ValueError(msg)

    pyproject.write_text(py_updated, encoding="utf-8")
    version_file.write_text(ver_updated, encoding="utf-8")

    return BumpResult(
        files_modified=[pyproject, version_file],
        old_version=old_version,
        new_version=new_version,
    )
