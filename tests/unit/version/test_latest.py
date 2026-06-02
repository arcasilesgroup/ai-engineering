"""Tests for the latest-version SSOT resolver (``version.latest``).

``resolve_latest_known`` reconciles two signals — the bundled registry
high-water mark and the live PyPI cache — into one authoritative value (the
newer of the two), so the inline notice, ``ai-eng version``, and the
``/ai-start`` dashboard can never contradict each other. Fail-open on any error.
"""

from __future__ import annotations

import pytest

from ai_engineering.version import latest


@pytest.fixture
def _sources(monkeypatch: pytest.MonkeyPatch):
    """Patch both signal sources; return a setter (registry, cache)."""

    def _set(registry: str | None, cache: str | None) -> None:
        monkeypatch.setattr(latest, "_registry_latest", lambda: registry)
        monkeypatch.setattr(latest, "_cache_latest", lambda: cache)

    return _set


def test_returns_newer_when_cache_ahead(_sources) -> None:
    _sources("0.9.0", "0.9.2")
    assert latest.resolve_latest_known() == "0.9.2"


def test_returns_newer_when_registry_ahead(_sources) -> None:
    _sources("0.9.2", "0.9.0")
    assert latest.resolve_latest_known() == "0.9.2"


def test_registry_only(_sources) -> None:
    _sources("0.9.2", None)
    assert latest.resolve_latest_known() == "0.9.2"


def test_cache_only(_sources) -> None:
    _sources(None, "0.9.1")
    assert latest.resolve_latest_known() == "0.9.1"


def test_none_when_no_signal(_sources) -> None:
    _sources(None, None)
    assert latest.resolve_latest_known() is None


def test_equal_sources_collapse(_sources) -> None:
    _sources("0.9.2", "0.9.2")
    assert latest.resolve_latest_known() == "0.9.2"


def test_registry_helper_fails_open(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_a, **_k):
        raise OSError("no package data")

    monkeypatch.setattr("ai_engineering.version.latest.load_registry", _boom)
    assert latest._registry_latest() is None


def test_cache_helper_fails_open(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom() -> dict:
        raise OSError("no home")

    monkeypatch.setattr("ai_engineering.version.latest.cache.read", _boom)
    assert latest._cache_latest() is None
