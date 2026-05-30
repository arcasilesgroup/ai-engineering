"""Unit tests for the doctor scope+version status line (sub-003 T-4.3 / OQ3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering import __version__
from ai_engineering.doctor.models import CheckStatus, DoctorContext
from ai_engineering.doctor.runtime import scope_status


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
    project = tmp_path / "repo"
    project.mkdir()
    return project


def _mark_installed(root: Path) -> None:
    state = root / ".ai-engineering" / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "install-state.json").write_text("{}", encoding="utf-8")


def test_reports_installed_version(home: Path, repo: Path) -> None:
    results = scope_status.check(DoctorContext(target=repo))
    assert len(results) == 1
    check = results[0]
    assert check.name == "scope"
    assert check.status == CheckStatus.OK
    assert f"v{__version__}" in check.message


def test_reports_local_scope_when_repo_installed(home: Path, repo: Path) -> None:
    _mark_installed(repo)
    message = scope_status.check(DoctorContext(target=repo))[0].message
    assert "local" in message
    assert "global" not in message


def test_reports_both_scopes_when_both_installed(home: Path, repo: Path) -> None:
    _mark_installed(repo)
    _mark_installed(home)
    message = scope_status.check(DoctorContext(target=repo))[0].message
    assert "local" in message
    assert "global" in message


def test_reports_none_when_no_install_marker(home: Path, repo: Path) -> None:
    message = scope_status.check(DoctorContext(target=repo))[0].message
    assert "none detected" in message


def test_surfaces_latest_when_cache_newer(
    home: Path, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scope_status.version_cache, "read", lambda: {"latest": "999.0.0"})
    message = scope_status.check(DoctorContext(target=repo))[0].message
    assert "999.0.0" in message
    assert "ai-eng version upgrade" in message


def test_no_upgrade_hint_when_current(
    home: Path, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scope_status.version_cache, "read", lambda: {"latest": __version__})
    message = scope_status.check(DoctorContext(target=repo))[0].message
    assert "upgrade" not in message
    assert "(latest)" in message
