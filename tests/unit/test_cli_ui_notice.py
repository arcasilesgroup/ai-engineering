"""Tests for the update-available notice renderer (spec version-update-notice).

``maybe_render_update_notice`` reads the version-check cache, the installed
version, and the manifest ``version_check`` block. It renders ONE compact
dim-teal line pointing at ``ai-eng version upgrade`` when a newer release is
available and the throttle window has elapsed — and emits nothing when the
installed version is current, throttled, disabled, or in JSON mode.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ai_engineering import cli_ui
from ai_engineering.version import cache


@pytest.fixture(autouse=True)
def _home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def _clear_console(monkeypatch: pytest.MonkeyPatch) -> None:
    # The stderr console is lru_cached; clear it so env changes take effect.
    cli_ui.get_console.cache_clear()
    monkeypatch.delenv("AIENG_NO_UPDATE_CHECK", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)


@pytest.fixture(autouse=True)
def _resolver_reads_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    # These tests exercise the RENDERER, not the SSOT reconciliation (covered in
    # tests/unit/version/test_latest.py). Pin the resolver to the seeded cache so
    # the bundled registry's real high-water mark never leaks into renderer
    # assertions — the renderer looks up resolve_latest_known on the version
    # package at call time, so patch it there.
    monkeypatch.setattr(
        "ai_engineering.version.resolve_latest_known",
        lambda: cache.read().get("latest") or None,
    )


def _seed_cache(latest: str, *, shown_hours_ago: float | None = None) -> None:
    payload: dict = {
        "latest": latest,
        "checked_at": datetime.now(UTC).isoformat(),
        "source": "pypi",
    }
    if shown_hours_ago is not None:
        payload["last_shown_at"] = (
            datetime.now(UTC) - timedelta(hours=shown_hours_ago)
        ).isoformat()
    path = cache.cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_renders_when_outdated(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(cli_ui, "__version__", "0.1.0")
    _seed_cache("0.9.0")
    cli_ui.maybe_render_update_notice()
    err = capsys.readouterr().err
    assert "0.9.0" in err
    assert "ai-eng version upgrade" in err


def test_silent_when_current(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(cli_ui, "__version__", "0.9.0")
    _seed_cache("0.9.0")
    cli_ui.maybe_render_update_notice()
    assert capsys.readouterr().err == ""


def test_silent_when_cache_empty(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(cli_ui, "__version__", "0.1.0")
    cli_ui.maybe_render_update_notice()
    assert capsys.readouterr().err == ""


def test_silent_when_throttled(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(cli_ui, "__version__", "0.1.0")
    _seed_cache("0.9.0", shown_hours_ago=1.0)  # within 24h window
    cli_ui.maybe_render_update_notice()
    assert capsys.readouterr().err == ""


def test_renders_when_throttle_expired(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(cli_ui, "__version__", "0.1.0")
    _seed_cache("0.9.0", shown_hours_ago=48.0)  # past 24h window
    cli_ui.maybe_render_update_notice()
    assert "0.9.0" in capsys.readouterr().err


def test_silent_when_env_disabled(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setenv("AIENG_NO_UPDATE_CHECK", "1")
    monkeypatch.setattr(cli_ui, "__version__", "0.1.0")
    _seed_cache("0.9.0")
    cli_ui.maybe_render_update_notice()
    assert capsys.readouterr().err == ""


def test_stamps_last_shown_on_render(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_ui, "__version__", "0.1.0")
    _seed_cache("0.9.0")
    assert not cache.read().get("last_shown_at")
    cli_ui.maybe_render_update_notice()
    assert cache.read().get("last_shown_at")


def test_plain_text_under_no_color(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    cli_ui.get_console.cache_clear()
    monkeypatch.setattr(cli_ui, "__version__", "0.1.0")
    _seed_cache("0.9.0")
    cli_ui.maybe_render_update_notice()
    err = capsys.readouterr().err
    assert "0.9.0" in err
    # No Rich markup tags leak into plain output.
    assert "[brand" not in err
    assert "\x1b[" not in err  # no ANSI escape sequences


def test_disabled_via_manifest_flag(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(cli_ui, "__version__", "0.1.0")
    _seed_cache("0.9.0")

    class _VersionCheck:
        enabled = False
        ttl_hours = 24

    monkeypatch.setattr(cli_ui, "_load_version_check_config", lambda: _VersionCheck())
    cli_ui.maybe_render_update_notice()
    assert capsys.readouterr().err == ""


def _seed_stale_cache(latest: str, *, checked_hours_ago: float) -> None:
    payload = {
        "latest": latest,
        "checked_at": (datetime.now(UTC) - timedelta(hours=checked_hours_ago)).isoformat(),
        "source": "pypi",
    }
    path = cache.cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_stale_cache_fires_background_refresh(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    # spec-157 review F4: a cache older than ttl_hours kicks off a detached
    # refresh so it self-heals, while still rendering from current contents.
    monkeypatch.setattr(cli_ui, "__version__", "0.1.0")
    _seed_stale_cache("0.9.0", checked_hours_ago=48.0)  # past the 24h default TTL
    spawned: dict = {}
    monkeypatch.setattr(
        "ai_engineering.version.refresh.spawn_background",
        lambda: spawned.setdefault("called", True),
    )
    cli_ui.maybe_render_update_notice()
    assert spawned.get("called") is True
    assert "0.9.0" in capsys.readouterr().err


def test_fresh_cache_does_not_spawn_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    # The detached refresh must NOT fire when the cache is fresh — otherwise
    # every CLI invocation would spawn a child (spec-157 review F4).
    monkeypatch.setattr(cli_ui, "__version__", "0.1.0")
    _seed_cache("0.9.0")  # checked_at=now -> fresh
    spawned: dict = {}
    monkeypatch.setattr(
        "ai_engineering.version.refresh.spawn_background",
        lambda: spawned.setdefault("called", True),
    )
    cli_ui.maybe_render_update_notice()
    assert "called" not in spawned
