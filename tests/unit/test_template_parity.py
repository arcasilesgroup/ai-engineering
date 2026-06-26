"""Template parity tests — ensure installed templates match the live project.

These tests prevent drift between the live dogfooding project and the
templates shipped to downstream installations via ``ai-eng install``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_LIVE_HOOKS = _ROOT / ".ai-engineering" / "scripts" / "hooks"
_TEMPLATE_HOOKS = (
    _ROOT / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "scripts" / "hooks"
)
_LIVE_SETTINGS = _ROOT / ".claude" / "settings.json"
_TEMPLATE_SETTINGS = (
    _ROOT / "src" / "ai_engineering" / "templates" / "project" / ".claude" / "settings.json"
)


def _count_scripts(root: Path) -> set[str]:
    """Return relative paths of all non-pycache files under *root*."""
    return {
        str(f.relative_to(root))
        for f in root.rglob("*")
        if f.is_file() and "__pycache__" not in str(f) and f.suffix != ".pyc"
    }


class TestHookScriptParity:
    """Hook script files in templates/ must match scripts/hooks/ exactly."""

    def test_hook_script_count_matches(self, template_hooks_lock) -> None:
        with template_hooks_lock():  # serialize vs test_surface_drift probe writes
            live = _count_scripts(_LIVE_HOOKS)
            template = _count_scripts(_TEMPLATE_HOOKS)
        assert len(live) == len(template), (
            f"Hook script count mismatch: live={len(live)}, template={len(template)}. "
            f"Missing in template: {live - template}. "
            f"Extra in template: {template - live}."
        )

    def test_hook_script_names_match(self, template_hooks_lock) -> None:
        with template_hooks_lock():  # serialize vs test_surface_drift probe writes
            live = _count_scripts(_LIVE_HOOKS)
            template = _count_scripts(_TEMPLATE_HOOKS)
        assert live == template, (
            f"Hook scripts differ. Missing in template: {live - template}. "
            f"Extra in template: {template - live}."
        )


class TestSettingsJsonParity:
    """Template settings.json hook configuration must match live."""

    @pytest.fixture()
    def live_settings(self) -> dict:
        return json.loads(_LIVE_SETTINGS.read_text(encoding="utf-8"))

    @pytest.fixture()
    def template_settings(self) -> dict:
        return json.loads(_TEMPLATE_SETTINGS.read_text(encoding="utf-8"))

    def test_hook_event_types_match(self, live_settings: dict, template_settings: dict) -> None:
        live_events = set(live_settings.get("hooks", {}).keys())
        tmpl_events = set(template_settings.get("hooks", {}).keys())
        assert live_events == tmpl_events, (
            f"Hook event types differ. Missing in template: {live_events - tmpl_events}. "
            f"Extra in template: {tmpl_events - live_events}."
        )

    def test_hook_entry_count_per_event(self, live_settings: dict, template_settings: dict) -> None:
        live_hooks = live_settings.get("hooks", {})
        tmpl_hooks = template_settings.get("hooks", {})
        for event in live_hooks:
            live_count = len(live_hooks.get(event, []))
            tmpl_count = len(tmpl_hooks.get(event, []))
            assert live_count == tmpl_count, (
                f"Hook count mismatch for event '{event}': live={live_count}, template={tmpl_count}"
            )

    def test_deny_rules_match(self, live_settings: dict, template_settings: dict) -> None:
        live_deny = set(live_settings.get("permissions", {}).get("deny", []))
        tmpl_deny = set(template_settings.get("permissions", {}).get("deny", []))
        assert live_deny == tmpl_deny, (
            f"Deny rules differ. Missing in template: {live_deny - tmpl_deny}. "
            f"Extra in template: {tmpl_deny - live_deny}."
        )


# spec-180 D-180-06: the top-level ``.ai-engineering/scripts/*.py`` scripts ship
# to consumers and MUST stay byte-identical to their template twin. Until now
# only session_bootstrap.py + auto-format.py were byte-guarded; spec_lifecycle.py
# and the rest drifted silently. ``glob("*.py")`` is top-level only, so the
# hooks/ and skills/ subtrees (guarded elsewhere) and the spec-131/ one-time
# migration subdir (no twin, project-specific) are excluded automatically.
_LIVE_SCRIPTS = _ROOT / ".ai-engineering" / "scripts"
_TEMPLATE_SCRIPTS = _ROOT / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "scripts"


def _top_level_scripts(root: Path) -> list[str]:
    return sorted(p.name for p in root.glob("*.py"))


def _norm_bytes(path: Path) -> bytes:
    """CRLF-normalized bytes so Windows checkouts do not spuriously differ."""
    return path.read_bytes().replace(b"\r\n", b"\n")


class TestTopLevelScriptsParity:
    """Top-level .ai-engineering/scripts/*.py must match the template twin."""

    def test_top_level_script_names_match(self) -> None:
        live = set(_top_level_scripts(_LIVE_SCRIPTS))
        template = set(_top_level_scripts(_TEMPLATE_SCRIPTS))
        assert live == template, (
            f"Top-level script set differs. Missing in template: {live - template}. "
            f"Extra in template: {template - live}."
        )

    @pytest.mark.parametrize("name", _top_level_scripts(_LIVE_SCRIPTS))
    def test_top_level_script_bytes_match(self, name: str) -> None:
        live = _LIVE_SCRIPTS / name
        template = _TEMPLATE_SCRIPTS / name
        assert template.exists(), f"missing template twin for {name}"
        assert _norm_bytes(live) == _norm_bytes(template), (
            f"{name} drifted between live and template "
            f"(live={len(_norm_bytes(live))}B, template={len(_norm_bytes(template))}B). "
            f"Re-sync: cp .ai-engineering/scripts/{name} "
            f"src/ai_engineering/templates/.ai-engineering/scripts/{name}"
        )
