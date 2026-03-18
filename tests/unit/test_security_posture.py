"""Tests for security_posture_metrics fallback chain."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

SONAR_PATCH = "ai_engineering.lib.signals.sonar_detailed_metrics"
SUBPROCESS_PATCH = "subprocess.run"
SONAR_UNAVAILABLE = {"available": False}


class TestSecurityPostureMetrics:
    """Tests for security_posture_metrics in signals.py."""

    def setup_method(self):
        from ai_engineering.lib.signals import _reset_sonar_cache

        _reset_sonar_cache()

    def test_sonarcloud_source(self, tmp_path: Path):
        """Uses SonarCloud data when available."""
        from ai_engineering.lib.signals import security_posture_metrics

        sonar_data = {
            "available": True,
            "vulnerabilities": 3,
            "security_hotspots": 5,
            "security_rating": "B",
        }
        with (
            patch(SONAR_PATCH, return_value=sonar_data),
            patch(SUBPROCESS_PATCH, side_effect=FileNotFoundError),
        ):
            result = security_posture_metrics(tmp_path)
        assert result["source"] == "sonarcloud"
        assert result["vulnerabilities"] == 3
        assert result["security_hotspots"] == 5
        assert result["security_rating"] == "B"

    def test_pip_audit_fallback(self, tmp_path: Path):
        """Falls back to pip-audit when SonarCloud unavailable."""
        from ai_engineering.lib.signals import security_posture_metrics

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps(
            [
                {"name": "pkg1", "version": "1.0", "vulns": [{"id": "CVE-1"}]},
                {"name": "pkg2", "version": "2.0", "vulns": [{"id": "CVE-2"}]},
            ]
        )
        with (
            patch(SONAR_PATCH, return_value=SONAR_UNAVAILABLE),
            patch(SUBPROCESS_PATCH, return_value=mock_proc),
        ):
            result = security_posture_metrics(tmp_path)
        assert result["source"] == "pip-audit"
        assert result["dep_vulns"] == 2

    def test_sonar_plus_pip_audit(self, tmp_path: Path):
        """Both sources combined when available."""
        from ai_engineering.lib.signals import security_posture_metrics

        sonar_data = {
            "available": True,
            "vulnerabilities": 1,
            "security_hotspots": 2,
            "security_rating": "A",
        }
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps(
            [
                {"name": "pkg1", "version": "1.0", "vulns": []},
            ]
        )
        with (
            patch(SONAR_PATCH, return_value=sonar_data),
            patch(SUBPROCESS_PATCH, return_value=mock_proc),
        ):
            result = security_posture_metrics(tmp_path)
        assert "sonarcloud" in result["source"]
        assert "pip-audit" in result["source"]
        assert result["vulnerabilities"] == 1
        assert result["dep_vulns"] == 1

    def test_no_data_fallback(self, tmp_path: Path):
        """Returns defaults when no source available."""
        from ai_engineering.lib.signals import security_posture_metrics

        with (
            patch(SONAR_PATCH, return_value=SONAR_UNAVAILABLE),
            patch(SUBPROCESS_PATCH, side_effect=FileNotFoundError),
        ):
            result = security_posture_metrics(tmp_path)
        assert result["source"] == "none"
        assert result["vulnerabilities"] == 0
        assert result["dep_vulns"] == 0

    def test_pip_audit_timeout(self, tmp_path: Path):
        """pip-audit timeout is handled gracefully."""
        import subprocess as sp

        from ai_engineering.lib.signals import security_posture_metrics

        with (
            patch(SONAR_PATCH, return_value=SONAR_UNAVAILABLE),
            patch(
                SUBPROCESS_PATCH,
                side_effect=sp.TimeoutExpired("pip-audit", 60),
            ),
        ):
            result = security_posture_metrics(tmp_path)
        assert result["source"] == "none"

    def test_pip_audit_nonzero_with_vulns(self, tmp_path: Path):
        """pip-audit non-zero return with vulnerability data."""
        from ai_engineering.lib.signals import security_posture_metrics

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = json.dumps(
            {
                "dependencies": [
                    {"name": "p1", "version": "1.0", "vulns": [{"id": "CVE-1"}]},
                    {"name": "p2", "version": "2.0", "vulns": []},
                    {"name": "p3", "version": "3.0", "vulns": [{"id": "CVE-3"}]},
                ]
            }
        )
        with (
            patch(SONAR_PATCH, return_value=SONAR_UNAVAILABLE),
            patch(SUBPROCESS_PATCH, return_value=mock_proc),
        ):
            result = security_posture_metrics(tmp_path)
        assert result["source"] == "pip-audit"
        assert result["dep_vulns"] == 2  # Only p1 and p3 have vulns

    def test_pip_audit_nonzero_invalid_json(self, tmp_path: Path):
        """pip-audit non-zero with invalid JSON handled gracefully."""
        from ai_engineering.lib.signals import security_posture_metrics

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "not json"
        with (
            patch(SONAR_PATCH, return_value=SONAR_UNAVAILABLE),
            patch(SUBPROCESS_PATCH, return_value=mock_proc),
        ):
            result = security_posture_metrics(tmp_path)
        assert result["source"] == "pip-audit"
        assert result["dep_vulns"] == 0
