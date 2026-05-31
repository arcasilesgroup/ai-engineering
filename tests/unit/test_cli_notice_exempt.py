"""Notice render is post-command, json/automation-exempt (spec-156 D-156-09/13)."""

from __future__ import annotations

from unittest.mock import patch

import ai_engineering.cli_factory as cf


def test_exempt_set_covers_automation_hot_paths() -> None:
    assert {"version", "internal", "gate"} <= cf._NOTICE_EXEMPT


def _run_post_notice(command: str, *, json_mode: bool) -> bool:
    """Return whether maybe_render_update_notice would be invoked."""
    cf._invoked_command = command
    with (
        patch("ai_engineering.cli_output.is_json_mode", return_value=json_mode),
        patch.object(cf, "_update_check_disabled", return_value=False),
        patch("ai_engineering.cli_ui.maybe_render_update_notice") as render,
    ):
        cf._maybe_render_post_command_notice()
    return render.called


def test_notice_renders_for_human_command() -> None:
    assert _run_post_notice("doctor", json_mode=False) is True


def test_notice_suppressed_in_json_mode() -> None:
    """Per-command --json (resolved post-callback) suppresses the notice."""
    assert _run_post_notice("doctor", json_mode=True) is False


def test_notice_suppressed_on_exempt_commands() -> None:
    for cmd in ("internal", "gate", "version"):
        assert _run_post_notice(cmd, json_mode=False) is False, cmd


def test_refresh_touches_checked_at_on_failure(tmp_path, monkeypatch) -> None:
    """spec-156 D-156-13: failed fetch advances checked_at (no respawn storm)."""
    from ai_engineering.version import cache, refresh

    monkeypatch.setattr(cache, "cache_path", lambda: tmp_path / "version-check.json")
    with (
        patch("ai_engineering.version.pypi.fetch_latest", return_value=None),
        patch.object(cache, "touch_checked_at") as touch,
    ):
        refresh.refresh_now()
    touch.assert_called_once()
