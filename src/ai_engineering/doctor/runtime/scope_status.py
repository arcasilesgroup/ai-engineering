"""Doctor runtime check: install scope + version status (sub-003 OQ3 / T-4.3).

Emits one thin status line reporting the installed framework version, the
cached latest release (when known, read with zero network), and which install
scopes are present (local repo, global home). This gives operators a single
place to see "what version am I on, is there a newer one, and where am I
installed" (spec R7 scope-surprise mitigation).

Fail-open: any read error degrades to a still-useful line rather than a failure.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering import __version__
from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.version import cache as version_cache


def _active_scopes(target: Path) -> list[str]:
    """Return the install scopes present: ``local`` (repo) and/or ``global`` (home).

    spec-156 D-156-04/17: delegates to the single ``detect_scopes`` resolver,
    which collapses to ``global`` when the repo IS the home directory (the two
    markers are the same file) instead of double-counting ``local, global``.
    """
    from ai_engineering.installer.scope_resolution import detect_scopes

    order = {"local": 0, "global": 1}
    return sorted(detect_scopes(target), key=lambda s: order.get(s, 99))


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Report installed version, cached latest, and active install scopes."""
    # ``version_cache.read()`` is itself fail-open (returns ``{}`` on any IO or
    # JSON error), so no extra guard is needed here.
    latest = str(version_cache.read().get("latest") or "")

    scopes = _active_scopes(ctx.target)
    scope_label = ", ".join(scopes) if scopes else "none detected"

    from ai_engineering.version.compare import is_newer

    if latest and is_newer(latest, __version__):
        version_label = f"v{__version__} (latest v{latest} — run `ai-eng version upgrade`)"
    elif latest:
        version_label = f"v{__version__} (latest)"
    else:
        version_label = f"v{__version__}"

    message = f"ai-engineering {version_label}; install scope: {scope_label}"
    return [CheckResult(name="scope", status=CheckStatus.OK, message=message)]
