"""Tests for skill requirement status diagnostics."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.skills.service import list_local_skill_status

pytestmark = pytest.mark.unit

runner = CliRunner()


def _write_skill(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_list_local_skill_status_reports_missing_requirements(tmp_path: Path) -> None:
    skill_path = tmp_path / ".ai-engineering" / "skills" / "dev" / "sample.md"
    _write_skill(
        skill_path,
        (
            "---\n"
            "name: sample\n"
            "version: 1.0.0\n"
            "category: dev\n"
            "requires:\n"
            "  bins: [definitely-missing-binary]\n"
            "  anyBins: [missing-a, missing-b]\n"
            "  env: [MISSING_ENV]\n"
            "  config: [providers.primary]\n"
            "---\n\n"
            "# Sample\n"
        ),
    )
    manifest = tmp_path / ".ai-engineering" / "manifest.yml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("providers:\n  primary: github\n", encoding="utf-8")

    status = list_local_skill_status(tmp_path)
    assert len(status) == 1
    item = status[0]
    assert item.eligible is False
    assert "definitely-missing-binary" in item.missing_bins
    assert "missing-a" in item.missing_any_bins
    assert "MISSING_ENV" in item.missing_env
    assert item.missing_config == []


def test_skill_status_cli_prints_summary(tmp_path: Path) -> None:
    eligible_path = tmp_path / ".ai-engineering" / "skills" / "dev" / "ok.md"
    _write_skill(
        eligible_path,
        "---\nname: ok\nversion: 1.0.0\ncategory: dev\n---\n\n# Ok\n",
    )

    bad_path = tmp_path / ".ai-engineering" / "skills" / "dev" / "bad.md"
    _write_skill(
        bad_path,
        (
            "---\n"
            "name: bad\n"
            "version: 1.0.0\n"
            "category: dev\n"
            "requires:\n"
            "  env: [MISSING_ENV]\n"
            "---\n\n"
            "# Bad\n"
        ),
    )

    app = create_app()
    result = runner.invoke(app, ["skill", "status", "--target", str(tmp_path)])
    assert result.exit_code == 0
    assert "bad [ineligible]" in result.stdout
    assert "Summary:" in result.stdout
