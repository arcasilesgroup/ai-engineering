"""Tests for the PyPI version source adapter (spec version-update-notice).

The adapter is fail-open: it returns the latest release string on success
and ``None`` on any failure (timeout, offline, non-200, malformed JSON, or
``httpx`` missing). It must never raise. Mirrors the lazy-httpx +
``http.client`` fallback pattern from ``platforms/sonar.py``.
"""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from ai_engineering.version import pypi


class _Resp:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


def _install_fake_httpx(monkeypatch: pytest.MonkeyPatch, get_impl) -> None:
    fake = types.ModuleType("httpx")
    fake.get = get_impl  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "httpx", fake)


def test_fetch_latest_parses_info_version(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, timeout: float = 0.0) -> _Resp:
        assert "pypi.org" in url
        return _Resp(200, {"info": {"version": "1.2.3"}})

    _install_fake_httpx(monkeypatch, fake_get)
    assert pypi.fetch_latest() == "1.2.3"


def test_fetch_latest_none_on_non_200(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_httpx(monkeypatch, lambda url, timeout=0.0: _Resp(503, {}))
    assert pypi.fetch_latest() is None


def test_fetch_latest_none_on_malformed_json(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_httpx(monkeypatch, lambda url, timeout=0.0: _Resp(200, {"nope": 1}))
    assert pypi.fetch_latest() is None


def test_fetch_latest_none_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(url: str, timeout: float = 0.0) -> _Resp:
        raise TimeoutError("slow")

    _install_fake_httpx(monkeypatch, boom)
    assert pypi.fetch_latest() is None


def test_fetch_latest_falls_back_when_httpx_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force httpx import to fail, then make the http.client fallback return a value.
    monkeypatch.setitem(sys.modules, "httpx", None)

    captured = {}

    def fake_fallback(timeout: float) -> str | None:
        captured["called"] = True
        return "4.5.6"

    monkeypatch.setattr(pypi, "_fetch_latest_stdlib", fake_fallback)
    assert pypi.fetch_latest() == "4.5.6"
    assert captured.get("called") is True


def test_stdlib_fallback_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # Even with a broken connection class, the stdlib path returns None.
    import http.client

    class BrokenConn:
        def __init__(self, *a: Any, **k: Any) -> None:
            raise OSError("no network")

    monkeypatch.setattr(http.client, "HTTPSConnection", BrokenConn)
    assert pypi._fetch_latest_stdlib(2.0) is None
