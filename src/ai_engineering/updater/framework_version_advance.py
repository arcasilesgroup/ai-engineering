"""spec-184 Phase B: advance ``manifest.framework_version`` on ``ai-eng update``.

``framework_version`` is the sole framework-owned key ``ai-eng update`` writes
into the ownership-protected ``manifest.yml`` (D-184-02/06). Like
``migrate_hook_commands`` (the sibling field-migration for the protected
``.claude/settings.json``), this never flows through the DENY-gated FileChange
path: it computes the plan always (dry-run visibility) and writes only on
apply, via the comment-preserving ``update_manifest_field``. It is strictly
restricted to the framework-writable allowlist so no user key is touched, and
it is fail-open — any error returns a no-op report and never breaks update.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from ai_engineering.config.loader import update_manifest_field
from ai_engineering.config.manifest_ownership import is_framework_writable_manifest_key

_MANIFEST_REL = Path(".ai-engineering") / "manifest.yml"
_KEY = "framework_version"


@dataclass
class FrameworkVersionAdvance:
    """Report of a framework_version advancement (or the plan, on dry-run)."""

    previous: str | None = None
    advanced_to: str | None = None
    applied: bool = False


def _read_framework_version(manifest: Path) -> str | None:
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    value = data.get(_KEY) if isinstance(data, dict) else None
    return str(value) if value is not None else None


def advance_framework_version(target: Path, *, dry_run: bool) -> FrameworkVersionAdvance:
    """Advance ``manifest.framework_version`` to the installed package version.

    Computes always (dry-run visibility); writes only when ``dry_run`` is
    False. Restricted to the framework-writable allowlist (v1:
    ``framework_version``). Fail-open: never raises.
    """
    from ai_engineering import __version__

    manifest = target / _MANIFEST_REL
    if not manifest.is_file() or not is_framework_writable_manifest_key(_KEY):
        return FrameworkVersionAdvance()

    try:
        previous = _read_framework_version(manifest)
    except Exception:
        return FrameworkVersionAdvance()

    if previous == __version__:
        # Already current — no write, no drift.
        return FrameworkVersionAdvance(previous=previous, advanced_to=__version__, applied=False)

    if dry_run:
        return FrameworkVersionAdvance(previous=previous, advanced_to=__version__, applied=False)

    try:
        # insert_missing: a slim manifest may omit framework_version.
        update_manifest_field(target, _KEY, __version__, insert_missing=True)
    except Exception:
        return FrameworkVersionAdvance(previous=previous)

    return FrameworkVersionAdvance(previous=previous, advanced_to=__version__, applied=True)
