"""Notice render is post-command, json/automation-exempt (spec-156 D-156-09/13)."""

from __future__ import annotations

from unittest.mock import patch

import ai_engineering.cli_factory as cf


def test_exempt_set_covers_automation_hot_paths() -> None:
    assert {"version", "internal", "gate"} <= cf._NOTICE_EXEMPT


class _EnabledVersionCheck:
    enabled = True
    ttl_hours = 24


def _run_post_notice(command: str, *, json_mode: bool) -> bool:
    """Return whether maybe_render_update_notice would be invoked."""
    cf._invoked_command = command
    with (
        patch("ai_engineering.cli_output.is_json_mode", return_value=json_mode),
        # spec-157 F7: the gate now loads version_check once and threads it in.
        patch(
            "ai_engineering.cli_ui._load_version_check_config",
            return_value=_EnabledVersionCheck(),
        ),
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


def _run_gated(*, json_mode: bool) -> bool:
    """Return whether the shared gate would invoke the renderer."""
    with (
        patch("ai_engineering.cli_output.is_json_mode", return_value=json_mode),
        patch(
            "ai_engineering.cli_ui._load_version_check_config",
            return_value=_EnabledVersionCheck(),
        ),
        patch("ai_engineering.cli_ui.maybe_render_update_notice") as render,
    ):
        cf._render_update_notice_gated()
    return render.called


def test_gated_renders_for_human() -> None:
    assert _run_gated(json_mode=False) is True


def test_gated_suppressed_in_json_mode() -> None:
    assert _run_gated(json_mode=False) is True
    assert _run_gated(json_mode=True) is False


def test_bare_invocation_renders_notice() -> None:
    """Bare ``ai-eng`` exits in the app callback, so it must render the notice
    inline via the shared gate (not via the post-command boundary), and with
    ``force=True`` so it bypasses the throttle like an explicit version check."""
    from typer.testing import CliRunner

    from ai_engineering.cli_factory import create_app

    with patch("ai_engineering.cli_factory._render_update_notice_gated") as gate:
        CliRunner().invoke(create_app(), [])
    gate.assert_called_once_with(force=True)


def test_gate_threads_force_to_renderer() -> None:
    """The shared gate forwards ``force`` to the cli_ui renderer."""
    with (
        patch("ai_engineering.cli_output.is_json_mode", return_value=False),
        patch(
            "ai_engineering.cli_ui._load_version_check_config",
            return_value=_EnabledVersionCheck(),
        ),
        patch("ai_engineering.cli_ui.maybe_render_update_notice") as render,
    ):
        cf._render_update_notice_gated(force=True)
    render.assert_called_once()
    assert render.call_args.kwargs.get("force") is True


def test_bare_invocation_suppressed_in_json_mode() -> None:
    """``ai-eng --json`` (no subcommand) emits the command tree, never the notice."""
    from typer.testing import CliRunner

    from ai_engineering.cli_factory import create_app

    with patch("ai_engineering.cli_factory._render_update_notice_gated") as gate:
        CliRunner().invoke(create_app(), ["--json"])
    gate.assert_not_called()


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
