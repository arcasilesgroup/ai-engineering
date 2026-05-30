"""Tests for detection-first scope resolution (spec-156 D-156-01/02/03/17)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer.scope_resolution import (
    ResolvedScope,
    detect_scopes,
    resolve_scope,
)

_MARKER = Path(".ai-engineering") / "state" / "install-state.json"


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: fake_home))
    return fake_home


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    return r


def _install_marker(root: Path) -> None:
    p = root / _MARKER
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"schema_version": "2.0"}', encoding="utf-8")


# --- detection ------------------------------------------------------------


def test_detect_neither(home: Path, repo: Path) -> None:
    assert detect_scopes(repo) == set()


def test_detect_only_local(home: Path, repo: Path) -> None:
    _install_marker(repo)
    assert detect_scopes(repo) == {"local"}


def test_detect_only_global(home: Path, repo: Path) -> None:
    _install_marker(home)
    assert detect_scopes(repo) == {"global"}


def test_detect_both(home: Path, repo: Path) -> None:
    _install_marker(repo)
    _install_marker(home)
    assert detect_scopes(repo) == {"local", "global"}


def test_detect_repo_is_home_collapses_to_global(home: Path) -> None:
    """D-156-17: target == home -> one marker file -> report global only."""
    _install_marker(home)
    assert detect_scopes(home) == {"global"}


# --- resolution -----------------------------------------------------------


def test_resolve_neither_is_none(home: Path, repo: Path) -> None:
    r = resolve_scope(repo)
    assert r == ResolvedScope(scope=None, both=False, announce="")


def test_resolve_only_local(home: Path, repo: Path) -> None:
    _install_marker(repo)
    r = resolve_scope(repo)
    assert r.scope == "local"
    assert r.both is False
    assert "local install (./)" in r.announce
    assert "global also present" not in r.announce


def test_resolve_only_global(home: Path, repo: Path) -> None:
    _install_marker(home)
    r = resolve_scope(repo)
    assert r.scope == "global"
    assert "global install (~/)" in r.announce


def test_resolve_both_local_wins_and_announces(home: Path, repo: Path) -> None:
    _install_marker(repo)
    _install_marker(home)
    r = resolve_scope(repo)
    assert r.scope == "local"
    assert r.both is True
    assert "global also present" in r.announce


def test_explicit_global_overrides(home: Path, repo: Path) -> None:
    _install_marker(repo)  # only local present, but flag forces global
    r = resolve_scope(repo, explicit="global")
    assert r.scope == "global"


def test_explicit_local_overrides(home: Path, repo: Path) -> None:
    _install_marker(home)  # only global present, but flag forces local
    r = resolve_scope(repo, explicit="local")
    assert r.scope == "local"
