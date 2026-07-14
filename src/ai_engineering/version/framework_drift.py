"""spec-184 Phase C: project-framework drift detection (the LOCAL version axis).

Distinct from the PyPI-update axis (``resolve_latest_known`` / the ◈ notice):
this compares the framework version APPLIED to the project
(``manifest.framework_version``, advanced by ``ai-eng update`` — Phase B)
against the INSTALLED package ``__version__``. Drift = the installed package is
newer than what last wrote the project's files, i.e. ``ai-eng update`` should be
run. Pure, local, zero-network, and fail-open (a missing / malformed manifest or
version never reports drift).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from ai_engineering.version.compare import is_newer

_MANIFEST_REL = Path(".ai-engineering") / "manifest.yml"


@dataclass(frozen=True)
class FrameworkDrift:
    """Result of comparing applied vs installed framework version."""

    applied: str | None
    installed: str
    behind: bool

    @property
    def recovery(self) -> str:
        """The command that clears the drift."""
        return "ai-eng update"


def _read_applied(root: Path) -> str | None:
    manifest = root / _MANIFEST_REL
    if not manifest.is_file():
        return None
    try:
        data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    value = data.get("framework_version") if isinstance(data, dict) else None
    return str(value) if value is not None else None


def framework_is_behind(applied: str | None, installed: str) -> bool:
    """True iff the installed package is strictly newer than the applied version.

    The single drift predicate, shared by :func:`detect_framework_drift` and the
    surfaces (status/doctor/dashboard) so the comparison lives in one place. Any
    missing / unparseable value yields False — never nag on missing data.
    """
    return bool(applied and is_newer(installed, applied))


def detect_framework_drift(root: Path) -> FrameworkDrift:
    """Return the applied-vs-installed framework drift for a project.

    ``behind`` is True only when the installed package is strictly newer than
    the applied ``framework_version`` (PEP 440). Any unreadable / unparseable
    value yields ``behind=False`` — never nag on missing data.
    """
    from ai_engineering import __version__

    applied = _read_applied(root)
    return FrameworkDrift(
        applied=applied,
        installed=__version__,
        behind=framework_is_behind(applied, __version__),
    )
