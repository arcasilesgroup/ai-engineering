"""Tests for the detached version-refresh spawner (spec version-update-notice).

``spawn_background`` must launch a detached child and return immediately
without blocking or raising (fail-open). ``refresh_now`` is the synchronous
child entrypoint: it fetches the latest release and writes the cache.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from ai_engineering.version import cache, pypi, refresh


@pytest.fixture(autouse=True)
def _home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    return tmp_path


def test_refresh_now_writes_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pypi, "fetch_latest", lambda *a, **k: "2.0.0")
    refresh.refresh_now()
    assert cache.read()["latest"] == "2.0.0"


def test_refresh_now_skips_write_when_fetch_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pypi, "fetch_latest", lambda *a, **k: None)
    refresh.refresh_now()
    # No latest fetched -> no cache written.
    assert cache.read() == {}


def test_refresh_now_fail_open_on_fetch_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a: object, **k: object) -> str:
        raise RuntimeError("network exploded")

    monkeypatch.setattr(pypi, "fetch_latest", boom)
    # Must not raise.
    refresh.refresh_now()


def test_spawn_background_is_nonblocking(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    class FakePopen:
        def __init__(self, argv: list[str], **kwargs: object) -> None:
            captured["argv"] = argv
            captured["kwargs"] = kwargs

        def wait(self) -> int:  # pragma: no cover - must NOT be called
            raise AssertionError("spawn_background must not block on the child")

    monkeypatch.setattr(subprocess, "Popen", FakePopen)
    refresh.spawn_background()

    argv = captured["argv"]
    assert argv[0] == sys.executable
    assert "ai_engineering.version.refresh" in argv
    assert captured["kwargs"].get("start_new_session") is True


def test_spawn_background_swallows_spawn_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a: object, **k: object) -> None:
        raise OSError("cannot spawn")

    monkeypatch.setattr(subprocess, "Popen", boom)
    # Must not raise (fail-open).
    refresh.spawn_background()
