"""Build-time/runtime boundary regression guard (spec-189 D-189-01 / B2).

Driver-tier is *model detection*, which is model management — out of
scope for the framework (D-189-01). The mirror-generation layer under
``scripts/sync_mirrors/`` is a pure build-time authoring transform: it
must never read the runtime driver-tier signal (``driver_tier`` /
``driver-tier``). This test pins that boundary going forward — it FAILS
with the offending file list if any mirror-generation module references
the runtime signal, and PASSES today (0 matches expected).
"""

from __future__ import annotations

import re
from pathlib import Path

# tests/conformance/ -> repo root is two parents up.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SYNC_MIRRORS = _REPO_ROOT / "scripts" / "sync_mirrors"

# The runtime driver-tier signal in either identifier or hyphenated form.
_DRIVER_TIER_RE = re.compile(r"driver[_-]tier")


def _iter_sync_mirror_modules() -> list[Path]:
    """Yield every ``.py`` under ``scripts/sync_mirrors/`` (excluding caches)."""
    return [path for path in sorted(_SYNC_MIRRORS.rglob("*.py")) if "__pycache__" not in path.parts]


def _offenders() -> list[str]:
    """Return ``path: line`` strings for every driver-tier reference found."""
    hits: list[str] = []
    for module in _iter_sync_mirror_modules():
        for lineno, line in enumerate(module.read_text(encoding="utf-8").splitlines(), start=1):
            if _DRIVER_TIER_RE.search(line):
                rel = module.relative_to(_REPO_ROOT)
                hits.append(f"{rel}:{lineno}: {line.strip()}")
    return hits


def test_sync_mirrors_directory_exists() -> None:
    """Guard: the scan target must exist or the gate is meaningless."""
    assert _SYNC_MIRRORS.is_dir(), f"Expected {_SYNC_MIRRORS!s} to exist; boundary scan cannot run."


def test_scan_finds_at_least_one_module() -> None:
    """Sanity: the glob actually surfaces build-time modules to scan."""
    modules = _iter_sync_mirror_modules()
    assert modules, "no .py modules found under scripts/sync_mirrors/"


def test_no_driver_tier_reads_at_buildtime() -> None:
    """No mirror-generation module reads the runtime driver-tier signal.

    Failure surfaces every offending ``path:line`` so the operator can see
    exactly where the build-time/runtime boundary was crossed (D-189-01).
    """
    offenders = _offenders()
    assert not offenders, (
        "Build-time mirror generation must not read the runtime driver-tier "
        "signal (driver_tier / driver-tier). Offenders:\n"
        + "\n".join(f"  - {hit}" for hit in offenders)
    )
