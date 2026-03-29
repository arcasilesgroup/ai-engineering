"""E2E test: install_with_pipeline orchestrator.

Validates that ``install_with_pipeline()`` correctly plans and executes
the 6-phase install pipeline, including dry-run semantics and automatic
REPAIR mode detection on re-install.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ai_engineering.installer import service
from ai_engineering.installer.phases import PHASE_ORDER
from ai_engineering.installer.service import install_with_pipeline


@pytest.fixture()
def stub_ops(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub operational phases to prevent network/tool calls."""
    monkeypatch.setattr(service, "check_tools_for_stacks", lambda s: SimpleNamespace(tools=[]))
    monkeypatch.setattr(
        service, "ensure_tool", lambda t: SimpleNamespace(available=True, detail="ok")
    )
    monkeypatch.setattr(service, "provider_required_tools", lambda v: [])

    # Stub provider -- available=False short-circuits VCS auth + branch policy
    stub_prov = MagicMock()
    stub_prov.is_available.return_value = False
    stub_prov.provider_name.return_value = "github"
    stub_prov.check_auth.return_value = MagicMock(success=False)
    stub_prov.apply_branch_policy.return_value = MagicMock(success=False, manual_guide=None)
    monkeypatch.setattr(service, "get_provider", lambda p: stub_prov)


class TestInstallPipeline:
    """End-to-end tests for the phase-pipeline installer."""

    def test_pipeline_dry_run_no_files_written(self, tmp_path: Path) -> None:
        """Dry-run plans all phases but writes nothing to disk."""
        _result, summary = install_with_pipeline(tmp_path, stacks=["python"], dry_run=True)

        assert summary.dry_run is True
        assert not (tmp_path / ".ai-engineering").exists()
        assert len(summary.plans) == len(PHASE_ORDER)

    def test_pipeline_clean_install_creates_structure(self, tmp_path: Path, stub_ops: None) -> None:
        """Clean install creates governance dir, manifest, and state files."""
        result, summary = install_with_pipeline(tmp_path, stacks=["python"])

        assert (tmp_path / ".ai-engineering").is_dir()
        assert (tmp_path / ".ai-engineering" / "manifest.yml").exists()
        assert (tmp_path / ".ai-engineering" / "state" / "install-state.json").exists()
        assert result.total_created > 0
        assert summary.failed_phase is None

    def test_pipeline_repair_mode_auto_detection(self, tmp_path: Path, stub_ops: None) -> None:
        """Second install auto-detects REPAIR mode and reports already_installed."""
        install_with_pipeline(tmp_path, stacks=["python"])
        result, summary = install_with_pipeline(tmp_path, stacks=["python"])

        assert result.already_installed is True
        assert summary.failed_phase is None

    def test_pipeline_dry_run_returns_plans_but_no_results(self, tmp_path: Path) -> None:
        """Dry-run collects plans but produces zero results and zero created files."""
        result, summary = install_with_pipeline(tmp_path, stacks=["python"], dry_run=True)

        assert len(summary.plans) > 0
        assert len(summary.results) == 0
        assert result.total_created == 0
