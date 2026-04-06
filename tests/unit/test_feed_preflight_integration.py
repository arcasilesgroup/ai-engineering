"""Unit coverage for feed-preflight integration in install and doctor flows."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ai_engineering.doctor.runtime.feeds import FeedValidationResult
from ai_engineering.doctor.service import diagnose
from ai_engineering.installer.service import install_with_pipeline


def test_install_with_pipeline_blocks_before_running_phases_when_feed_preflight_fails(
    tmp_path: Path,
) -> None:
    with (
        patch(
            "ai_engineering.installer.service.validate_feeds_for_install",
            return_value=FeedValidationResult(
                status="blocked",
                feeds=["https://pkgs.dev.azure.com/acme/_packaging/core/pypi/simple/"],
                message=(
                    "Blocked install: private feed preflight failed before dependency resolution."
                ),
            ),
        ),
        patch("ai_engineering.installer.service.PipelineRunner.run") as mock_run,
    ):
        result, summary = install_with_pipeline(tmp_path)

    assert result.readiness_status == "blocked"
    assert summary.failed_phase == "feed_preflight"
    mock_run.assert_not_called()


def test_doctor_fix_returns_feed_preflight_failure_before_phase_execution(tmp_path: Path) -> None:
    with (
        patch("ai_engineering.doctor.service.load_install_state", return_value=None),
        patch("ai_engineering.doctor.service.load_manifest_config", return_value=None),
        patch("ai_engineering.doctor.service.emit_framework_operation"),
        patch(
            "ai_engineering.doctor.service.validate_feeds_for_install",
            return_value=FeedValidationResult(
                status="blocked",
                feeds=["https://pkgs.dev.azure.com/acme/_packaging/core/pypi/simple/"],
                message=(
                    "Blocked repair: private feed preflight failed before dependency resolution."
                ),
            ),
        ),
        patch("ai_engineering.doctor.service.importlib.import_module") as mock_import,
    ):
        report = diagnose(tmp_path, fix=True)

    assert report.passed is False
    assert report.runtime[0].name == "feed-preflight"
    assert report.runtime[0].message.startswith("Blocked repair")
    mock_import.assert_not_called()
