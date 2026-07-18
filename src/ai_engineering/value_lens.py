"""Client-Value Lens audience-level resolver (spec-186 D-186-02).

The lens renders user-facing reports and questions as sponsor-legible value
statements (see ``.ai-engineering/reference/value-lens.md``). Its audience
*depth* is a single knob resolved here with a fixed precedence:

    ``AIENG_VALUE_LENS_LEVEL`` env  →  manifest ``value_lens.default_level``
    →  built-in default ``"full"``.

Kept deliberately import-light and resilient: a bare-``python3`` UserPromptSubmit
hook lazy-imports :func:`resolve_level`, so a missing/corrupt manifest, an absent
config package, or any load failure degrades to ``"full"`` rather than raising.
"""

from __future__ import annotations

import os

_VALID_LEVELS = frozenset({"lite", "full", "ultra"})
_DEFAULT_LEVEL = "full"
_ENV_VAR = "AIENG_VALUE_LENS_LEVEL"


def _manifest_level() -> str | None:
    """Best-effort read of ``value_lens.default_level`` from the manifest.

    Wrapped in a broad try/except: config-package import, project-root
    discovery, or manifest parsing may all fail on a degraded host; any
    failure yields ``None`` so the caller falls through to the default.
    """
    try:
        from ai_engineering.config.loader import load_manifest_config
        from ai_engineering.paths import find_project_root

        config = load_manifest_config(find_project_root())
        level = config.value_lens.default_level
    except Exception:
        return None
    return level if isinstance(level, str) else None


def resolve_level() -> str:
    """Return the active Client-Value Lens level: ``lite`` | ``full`` | ``ultra``.

    Precedence: env override, then manifest default, then ``"full"``. Any value
    outside the known set (including an unset/blank override) falls back to
    ``"full"`` so downstream framing always has a valid level.
    """
    candidate = os.environ.get(_ENV_VAR)
    if not candidate:
        candidate = _manifest_level()
    if isinstance(candidate, str) and candidate.strip().lower() in _VALID_LEVELS:
        return candidate.strip().lower()
    return _DEFAULT_LEVEL
