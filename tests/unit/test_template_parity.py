"""Template parity tests — ensure installed templates match the live project.

These tests prevent drift between the live dogfooding project and the
templates shipped to downstream installations via ``ai-eng install``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_LIVE_HOOKS = _ROOT / "scripts" / "hooks"
_TEMPLATE_HOOKS = _ROOT / "src" / "ai_engineering" / "templates" / "project" / "scripts" / "hooks"
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

    def test_hook_script_count_matches(self) -> None:
        live = _count_scripts(_LIVE_HOOKS)
        template = _count_scripts(_TEMPLATE_HOOKS)
        assert len(live) == len(template), (
            f"Hook script count mismatch: live={len(live)}, template={len(template)}. "
            f"Missing in template: {live - template}. "
            f"Extra in template: {template - live}."
        )

    def test_hook_script_names_match(self) -> None:
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
