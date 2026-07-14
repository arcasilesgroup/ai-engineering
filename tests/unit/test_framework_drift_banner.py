"""spec-184 D-184-05: advise-only framework-drift banner (⟳, distinct from ◈)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering import __version__
from ai_engineering.cli_output import set_json_mode
from ai_engineering.cli_ui import maybe_render_framework_drift_notice


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    # redirect the throttle cache off the real home; clear opt-out + json mode
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("AIENG_NO_UPDATE_CHECK", raising=False)
    set_json_mode(False)
    yield
    set_json_mode(False)


def _proj(tmp_path: Path, framework_version: str) -> Path:
    p = tmp_path / "proj" / ".ai-engineering"
    p.mkdir(parents=True, exist_ok=True)
    (p / "manifest.yml").write_text(f'framework_version: "{framework_version}"\n', encoding="utf-8")
    return tmp_path / "proj"


def test_banner_shows_when_behind(tmp_path, capsys):
    maybe_render_framework_drift_notice(_proj(tmp_path, "0.0.1"), force=True)
    err = capsys.readouterr().err
    assert "ai-eng update" in err
    assert "version upgrade" not in err  # NOT the PyPI axis
    assert "0.0.1" in err


def test_no_banner_when_current(tmp_path, capsys):
    maybe_render_framework_drift_notice(_proj(tmp_path, __version__), force=True)
    assert capsys.readouterr().err == ""


def test_suppressed_in_json_mode(tmp_path, capsys):
    set_json_mode(True)
    maybe_render_framework_drift_notice(_proj(tmp_path, "0.0.1"), force=True)
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == ""


def test_opt_out_env_suppresses(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("AIENG_NO_UPDATE_CHECK", "1")
    maybe_render_framework_drift_notice(_proj(tmp_path, "0.0.1"), force=True)
    assert capsys.readouterr().err == ""


def test_throttled_second_call(tmp_path, capsys):
    proj = _proj(tmp_path, "0.0.1")
    maybe_render_framework_drift_notice(proj)  # first: shows + marks
    first = capsys.readouterr().err
    maybe_render_framework_drift_notice(proj)  # second: throttled
    second = capsys.readouterr().err
    assert "ai-eng update" in first
    assert second == ""
