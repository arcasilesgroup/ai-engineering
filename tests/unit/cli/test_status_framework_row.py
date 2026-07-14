"""spec-184 D-184-05: ai-eng status Framework version row + drift."""

from __future__ import annotations

import pytest

from ai_engineering import __version__
from ai_engineering.cli_commands._render_config import render_config, render_config_payload
from ai_engineering.config.manifest import ManifestConfig
from ai_engineering.core.output import Renderer


def test_payload_reports_drift_when_behind() -> None:
    payload = render_config_payload(ManifestConfig(framework_version="0.0.1"))
    fw = payload["framework"]
    assert fw["applied"] == "0.0.1"
    assert fw["installed"] == __version__
    assert fw["behind"] is True


def test_payload_not_behind_when_current() -> None:
    payload = render_config_payload(ManifestConfig(framework_version=__version__))
    assert payload["framework"]["behind"] is False


def test_payload_missing_version_not_behind() -> None:
    payload = render_config_payload(ManifestConfig(framework_version=""))
    assert payload["framework"]["behind"] is False
    assert payload["framework"]["applied"] is None


def test_payload_exposes_three_version_axes() -> None:
    fw = render_config_payload(ManifestConfig(framework_version="0.0.1"))["framework"]
    # applied (project) · installed (machine) · latest (PyPI) — the full chain
    assert set(fw) >= {"applied", "installed", "latest", "behind", "upgrade_available"}
    assert fw["installed"] == __version__
    # latest is a string (cached/registry) or None offline — never crashes
    assert fw["latest"] is None or isinstance(fw["latest"], str)


def test_status_row_shows_behind_recovery(capsys: pytest.CaptureFixture) -> None:
    render_config(ManifestConfig(framework_version="0.0.1"), Renderer.from_app("status"))
    out = capsys.readouterr()
    combined = out.out + out.err
    assert "Framework" in combined
    assert f"installed {__version__}" in combined
    assert "run ai-eng update" in combined  # project-behind recovery (⟳ axis)
    # no ⟳ glyph in the plain status path (Windows cp1252 safety)
    assert "⟳" not in combined


def test_status_row_current_no_recovery(capsys: pytest.CaptureFixture) -> None:
    render_config(ManifestConfig(framework_version=__version__), Renderer.from_app("status"))
    combined = "".join(capsys.readouterr())
    assert "Framework" in combined
    assert "run ai-eng update" not in combined
