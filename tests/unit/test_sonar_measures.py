"""Tests for SonarCloud token resolution and measures API."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# --- Token resolution tests ---


class TestResolveSonarToken:
    """Tests for _resolve_sonar_token fallback chain."""

    def test_env_var_takes_priority(self, tmp_path: Path):
        """SONAR_TOKEN env var is used when set."""
        from ai_engineering.policy.checks.sonar import _resolve_sonar_token

        with patch.dict("os.environ", {"SONAR_TOKEN": "env-token-123"}):
            result = _resolve_sonar_token(tmp_path)
        assert result == "env-token-123"

    def test_keyring_fallback_when_no_env(self, tmp_path: Path):
        """Falls back to OS keyring when env var not set."""
        from ai_engineering.policy.checks.sonar import _resolve_sonar_token

        mock_cred = MagicMock()
        mock_cred.retrieve.return_value = "keyring-token-456"
        with (
            patch.dict("os.environ", {"SONAR_TOKEN": ""}),
            patch(
                "ai_engineering.policy.checks.sonar.CredentialService",
                return_value=mock_cred,
            ),
        ):
            result = _resolve_sonar_token(tmp_path)
        assert result == "keyring-token-456"
        mock_cred.retrieve.assert_called_once_with("sonar", "token")

    def test_none_when_no_token_anywhere(self, tmp_path: Path):
        """Returns None when neither env var nor keyring has token."""
        from ai_engineering.policy.checks.sonar import _resolve_sonar_token

        mock_cred = MagicMock()
        mock_cred.retrieve.return_value = None
        with (
            patch.dict("os.environ", {"SONAR_TOKEN": ""}),
            patch(
                "ai_engineering.policy.checks.sonar.CredentialService",
                return_value=mock_cred,
            ),
        ):
            result = _resolve_sonar_token(tmp_path)
        assert result is None

    def test_keyring_exception_returns_none(self, tmp_path: Path):
        """Keyring failure is fail-open -- returns None."""
        from ai_engineering.policy.checks.sonar import _resolve_sonar_token

        with (
            patch.dict("os.environ", {"SONAR_TOKEN": ""}),
            patch(
                "ai_engineering.policy.checks.sonar.CredentialService",
                side_effect=RuntimeError("no keyring"),
            ),
        ):
            result = _resolve_sonar_token(tmp_path)
        assert result is None

    def test_whitespace_only_env_var_ignored(self, tmp_path: Path):
        """Whitespace-only SONAR_TOKEN is treated as unset."""
        from ai_engineering.policy.checks.sonar import _resolve_sonar_token

        mock_cred = MagicMock()
        mock_cred.retrieve.return_value = "keyring-token"
        with (
            patch.dict("os.environ", {"SONAR_TOKEN": "  "}),
            patch(
                "ai_engineering.policy.checks.sonar.CredentialService",
                return_value=mock_cred,
            ),
        ):
            result = _resolve_sonar_token(tmp_path)
        assert result == "keyring-token"


# --- Quality gate with fixed token resolution ---


class TestQuerySonarQualityGateTokenFix:
    """Verify query_sonar_quality_gate uses _resolve_sonar_token."""

    def test_uses_resolve_sonar_token(self, tmp_path: Path):
        """quality_gate delegates to _resolve_sonar_token for auth."""
        from ai_engineering.policy.checks.sonar import query_sonar_quality_gate

        props = tmp_path / "sonar-project.properties"
        props.write_text("sonar.projectKey=test-key\nsonar.host.url=https://sonar.test\n")
        with patch(
            "ai_engineering.policy.checks.sonar._resolve_sonar_token",
            return_value=None,
        ):
            result = query_sonar_quality_gate(tmp_path)
        assert result is None

    def test_quality_gate_with_keyring_token(self, tmp_path: Path):
        """quality_gate works with keyring-resolved token."""
        from ai_engineering.policy.checks.sonar import query_sonar_quality_gate

        props = tmp_path / "sonar-project.properties"
        props.write_text("sonar.projectKey=test-key\nsonar.host.url=https://sonar.test\n")
        response_data = json.dumps({"projectStatus": {"status": "OK", "conditions": []}}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = response_data
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with (
            patch(
                "ai_engineering.policy.checks.sonar._resolve_sonar_token",
                return_value="keyring-tok",
            ),
            patch(
                "ai_engineering.policy.checks.sonar.urlopen",
                return_value=mock_resp,
            ),
        ):
            result = query_sonar_quality_gate(tmp_path)
        assert result is not None
        assert result["status"] == "OK"


# --- Measures API tests ---


class TestQuerySonarMeasures:
    """Tests for query_sonar_measures."""

    def test_returns_none_without_properties(self, tmp_path: Path):
        """Returns None when sonar-project.properties missing."""
        from ai_engineering.policy.checks.sonar import query_sonar_measures

        result = query_sonar_measures(tmp_path)
        assert result is None

    def test_returns_none_without_project_key(self, tmp_path: Path):
        """Returns None when project key not in properties."""
        from ai_engineering.policy.checks.sonar import query_sonar_measures

        props = tmp_path / "sonar-project.properties"
        props.write_text("sonar.host.url=https://sonar.test\n")
        result = query_sonar_measures(tmp_path)
        assert result is None

    def test_returns_none_without_token(self, tmp_path: Path):
        """Returns None when no token available."""
        from ai_engineering.policy.checks.sonar import query_sonar_measures

        props = tmp_path / "sonar-project.properties"
        props.write_text("sonar.projectKey=test-key\n")
        with patch(
            "ai_engineering.policy.checks.sonar._resolve_sonar_token",
            return_value=None,
        ):
            result = query_sonar_measures(tmp_path)
        assert result is None

    def test_returns_measures_dict(self, tmp_path: Path):
        """Returns flat dict of metric values."""
        from ai_engineering.policy.checks.sonar import query_sonar_measures

        props = tmp_path / "sonar-project.properties"
        props.write_text("sonar.projectKey=test-key\nsonar.host.url=https://sonar.test\n")
        response_data = json.dumps(
            {
                "component": {
                    "measures": [
                        {"metric": "coverage", "value": "87.5"},
                        {"metric": "duplicated_lines_density", "value": "2.1"},
                        {"metric": "vulnerabilities", "value": "3"},
                        {"metric": "cognitive_complexity", "value": "145"},
                    ]
                }
            }
        ).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = response_data
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with (
            patch(
                "ai_engineering.policy.checks.sonar._resolve_sonar_token",
                return_value="tok",
            ),
            patch(
                "ai_engineering.policy.checks.sonar.urlopen",
                return_value=mock_resp,
            ),
        ):
            result = query_sonar_measures(
                tmp_path,
                [
                    "coverage",
                    "duplicated_lines_density",
                    "vulnerabilities",
                    "cognitive_complexity",
                ],
            )
        assert result is not None
        assert result["coverage"] == 87.5
        assert result["duplicated_lines_density"] == 2.1
        assert result["vulnerabilities"] == 3.0
        assert result["cognitive_complexity"] == 145.0

    def test_api_error_returns_none(self, tmp_path: Path):
        """API error is fail-open -- returns None."""
        from ai_engineering.policy.checks.sonar import query_sonar_measures

        props = tmp_path / "sonar-project.properties"
        props.write_text("sonar.projectKey=test-key\n")
        with (
            patch(
                "ai_engineering.policy.checks.sonar._resolve_sonar_token",
                return_value="tok",
            ),
            patch(
                "ai_engineering.policy.checks.sonar.urlopen",
                side_effect=Exception("timeout"),
            ),
        ):
            result = query_sonar_measures(tmp_path)
        assert result is None

    def test_custom_metrics_list(self, tmp_path: Path):
        """Custom metrics list is passed to API."""
        from ai_engineering.policy.checks.sonar import query_sonar_measures

        props = tmp_path / "sonar-project.properties"
        props.write_text("sonar.projectKey=my-proj\nsonar.host.url=https://sc.io\n")
        response_data = json.dumps(
            {"component": {"measures": [{"metric": "coverage", "value": "90"}]}}
        ).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = response_data
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        captured_url: list[str] = []

        def capture_urlopen(req, **kw):
            captured_url.append(req.full_url)
            return mock_resp

        with (
            patch(
                "ai_engineering.policy.checks.sonar._resolve_sonar_token",
                return_value="tok",
            ),
            patch(
                "ai_engineering.policy.checks.sonar.urlopen",
                side_effect=capture_urlopen,
            ),
        ):
            query_sonar_measures(tmp_path, ["coverage"])
        assert "metricKeys=coverage" in captured_url[0]


# --- sonar_detailed_metrics tests ---


class TestSonarDetailedMetrics:
    """Tests for sonar_detailed_metrics in signals.py."""

    def setup_method(self):
        from ai_engineering.lib.signals import _reset_sonar_cache

        _reset_sonar_cache()

    def test_returns_unavailable_when_no_sonar(self, tmp_path: Path):
        from ai_engineering.lib.signals import _reset_sonar_cache, sonar_detailed_metrics

        _reset_sonar_cache()
        with patch(
            "ai_engineering.policy.checks.sonar.query_sonar_measures",
            return_value=None,
        ):
            result = sonar_detailed_metrics(tmp_path)
        assert result["available"] is False
        assert result["source"] == "none"

    def test_returns_structured_metrics(self, tmp_path: Path):
        from ai_engineering.lib.signals import _reset_sonar_cache, sonar_detailed_metrics

        _reset_sonar_cache()
        raw = {
            "coverage": 87.5,
            "cognitive_complexity": 145.0,
            "duplicated_lines_density": 2.1,
            "vulnerabilities": 3.0,
            "security_hotspots": 5.0,
            "security_rating": 1.0,
            "reliability_rating": 2.0,
            "bugs": 7.0,
            "ncloc": 5000.0,
        }
        with patch(
            "ai_engineering.policy.checks.sonar.query_sonar_measures",
            return_value=raw,
        ):
            result = sonar_detailed_metrics(tmp_path)
        assert result["available"] is True
        assert result["source"] == "sonarcloud"
        assert result["coverage_pct"] == 87.5
        assert result["cognitive_complexity"] == 145
        assert result["duplication_pct"] == 2.1
        assert result["vulnerabilities"] == 3
        assert result["security_hotspots"] == 5
        assert result["security_rating"] == "A"
        assert result["reliability_rating"] == "B"
        assert result["bugs"] == 7

    def test_caches_result(self, tmp_path: Path):
        from ai_engineering.lib.signals import _reset_sonar_cache, sonar_detailed_metrics

        _reset_sonar_cache()
        with patch(
            "ai_engineering.policy.checks.sonar.query_sonar_measures",
            return_value=None,
        ) as mock:
            sonar_detailed_metrics(tmp_path)
            sonar_detailed_metrics(tmp_path)
        assert mock.call_count == 1
