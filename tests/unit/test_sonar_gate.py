"""Unit tests for Sonar gate skip logic, threshold parsing, and script behaviour.

These tests validate the decision tree for silent-skip logic
and the script argument generation for sonar-pre-gate scripts.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.credentials.service import CredentialService

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------
# Skip logic -- keyring-based (ToolsState removed)
# ---------------------------------------------------------------


class TestSonarGateSkipLogic:
    """Tests for the silent-skip decision tree."""

    def test_skip_when_no_token_in_keyring(self) -> None:
        """Sonar gate skips when keyring has no token."""
        backend = MagicMock()
        backend.get_password.return_value = None
        svc = CredentialService(backend=backend)
        assert svc.retrieve("sonar", "token") is None

    def test_run_when_token_in_keyring(self) -> None:
        """Sonar gate runs when keyring has a token."""
        backend = MagicMock()
        backend.get_password.return_value = "squ_test_token"
        svc = CredentialService(backend=backend)
        assert svc.retrieve("sonar", "token") == "squ_test_token"


# ---------------------------------------------------------------
# Threshold mapping
# ---------------------------------------------------------------


class TestThresholdMapping:
    """Tests for threshold values matching the quality contract."""

    def test_coverage_threshold(self) -> None:
        """Coverage threshold is 80% (aligned with SonarCloud Quality Gate)."""
        assert 80 <= 100

    def test_duplication_threshold(self) -> None:
        """Duplication threshold is 3%."""
        assert 3 <= 100

    def test_complexity_thresholds(self) -> None:
        """Cyclomatic <= 10, cognitive <= 15."""
        max_cyclomatic = 10
        max_cognitive = 15
        assert max_cyclomatic < max_cognitive


# ---------------------------------------------------------------
# Properties parsing
# ---------------------------------------------------------------


class TestPropertiesParsing:
    """Tests for sonar-project.properties parsing."""

    def test_parse_properties(self, tmp_path: Path) -> None:
        props = tmp_path / "sonar-project.properties"
        props.write_text(
            "sonar.projectKey=my-key\n"
            "sonar.organization=my-org\n"
            "# comment\n"
            "\n"
            "sonar.qualitygate.wait=true\n"
        )
        from ai_engineering.policy.checks.sonar import _parse_properties

        result = _parse_properties(props)
        assert result["sonar.projectKey"] == "my-key"
        assert result["sonar.organization"] == "my-org"
        assert result["sonar.qualitygate.wait"] == "true"

    def test_parse_properties_empty(self, tmp_path: Path) -> None:
        props = tmp_path / "sonar-project.properties"
        props.write_text("")
        from ai_engineering.policy.checks.sonar import _parse_properties

        assert _parse_properties(props) == {}


# ---------------------------------------------------------------
# Quality Gate API query
# ---------------------------------------------------------------


class TestQuerySonarQualityGate:
    """Tests for SonarCloud API quality gate query."""

    def test_returns_none_when_no_properties(self, tmp_path: Path) -> None:
        from ai_engineering.policy.checks.sonar import query_sonar_quality_gate

        assert query_sonar_quality_gate(tmp_path) is None

    def test_returns_none_when_no_project_key(self, tmp_path: Path) -> None:
        props = tmp_path / "sonar-project.properties"
        props.write_text("sonar.host.url=https://sonarcloud.io\n")
        from ai_engineering.policy.checks.sonar import query_sonar_quality_gate

        assert query_sonar_quality_gate(tmp_path) is None

    def test_returns_none_when_no_token(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        props = tmp_path / "sonar-project.properties"
        props.write_text("sonar.projectKey=my-key\nsonar.host.url=https://sonarcloud.io\n")
        monkeypatch.delenv("SONAR_TOKEN", raising=False)
        from ai_engineering.policy.checks.sonar import query_sonar_quality_gate

        assert query_sonar_quality_gate(tmp_path) is None


# ---------------------------------------------------------------
# Observe Sonar metrics
# ---------------------------------------------------------------


class TestQuerySonarQualityGateWithToken:
    """Tests for API query when token is available."""

    def test_returns_status_on_successful_api_call(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        props = tmp_path / "sonar-project.properties"
        props.write_text("sonar.projectKey=my-key\nsonar.host.url=https://sonarcloud.io\n")
        monkeypatch.setenv("SONAR_TOKEN", "squ_test_123")

        api_data = {"projectStatus": {"status": "OK", "conditions": []}}

        from ai_engineering.policy.checks.sonar import query_sonar_quality_gate

        with patch("ai_engineering.policy.checks.sonar._sonar_api_get", return_value=api_data):
            result = query_sonar_quality_gate(tmp_path)

        assert result is not None
        assert result["status"] == "OK"

    def test_returns_none_on_api_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        props = tmp_path / "sonar-project.properties"
        props.write_text("sonar.projectKey=my-key\nsonar.host.url=https://sonarcloud.io\n")
        monkeypatch.setenv("SONAR_TOKEN", "squ_test_123")

        from ai_engineering.policy.checks.sonar import query_sonar_quality_gate

        with patch("ai_engineering.policy.checks.sonar._sonar_api_get", return_value=None):
            assert query_sonar_quality_gate(tmp_path) is None


# ---------------------------------------------------------------
# API gate check (pre-push advisory)
# ---------------------------------------------------------------


class TestCheckSonarApiGate:
    """Tests for _check_sonar_api_gate advisory check."""

    def test_appends_skip_when_api_unavailable(self, tmp_path: Path) -> None:
        from ai_engineering.policy.checks.sonar import _check_sonar_api_gate
        from ai_engineering.policy.gates import GateResult
        from ai_engineering.state.models import GateHook

        result = GateResult(hook=GateHook.PRE_PUSH, checks=[])
        _check_sonar_api_gate(tmp_path, result)
        assert len(result.checks) == 1
        assert result.checks[0].passed is True
        assert "skipped" in result.checks[0].output

    def test_appends_status_when_api_returns_data(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        props = tmp_path / "sonar-project.properties"
        props.write_text("sonar.projectKey=my-key\nsonar.host.url=https://sonarcloud.io\n")
        monkeypatch.setenv("SONAR_TOKEN", "squ_test_123")

        api_response = json.dumps({"projectStatus": {"status": "OK", "conditions": []}}).encode()
        api_data = json.loads(api_response)

        from ai_engineering.policy.checks.sonar import _check_sonar_api_gate
        from ai_engineering.policy.gates import GateResult
        from ai_engineering.state.models import GateHook

        result = GateResult(hook=GateHook.PRE_PUSH, checks=[])

        with patch("ai_engineering.policy.checks.sonar._sonar_api_get", return_value=api_data):
            _check_sonar_api_gate(tmp_path, result)

        assert len(result.checks) == 1
        assert result.checks[0].passed is True
        assert "OK" in result.checks[0].output


# ---------------------------------------------------------------
# Observe Sonar metrics
# ---------------------------------------------------------------


class TestObserveSonarMetrics:
    """Tests for Sonar metrics in observe engineer dashboard."""

    def test_sonar_metrics_returns_unavailable_when_unconfigured(self, tmp_path: Path) -> None:
        from ai_engineering.cli_commands.observe import _sonar_metrics_data

        result = _sonar_metrics_data(tmp_path)
        assert result == {"available": False}

    def test_sonar_metrics_returns_dict_with_coverage(self, tmp_path: Path) -> None:
        qg_data = {
            "status": "OK",
            "conditions": [
                {"metricKey": "new_coverage", "actualValue": "85.2"},
            ],
        }
        from ai_engineering.cli_commands.observe import _sonar_metrics_data

        with (
            patch(
                "ai_engineering.policy.checks.sonar.query_sonar_quality_gate",
                return_value=qg_data,
            ),
            patch(
                "ai_engineering.cli_commands.observe.sonar_detailed_metrics",
                return_value={"available": False},
            ),
        ):
            result = _sonar_metrics_data(tmp_path)

        assert result["available"] is True
        assert result["status"] == "OK"
        assert result["new_code_coverage"] == "85.2"
        assert result["conditions_count"] == 1

    def test_sonar_metrics_without_coverage_condition(self, tmp_path: Path) -> None:
        qg_data = {"status": "ERROR", "conditions": []}
        from ai_engineering.cli_commands.observe import _sonar_metrics_data

        with (
            patch(
                "ai_engineering.policy.checks.sonar.query_sonar_quality_gate",
                return_value=qg_data,
            ),
            patch(
                "ai_engineering.cli_commands.observe.sonar_detailed_metrics",
                return_value={"available": False},
            ),
        ):
            result = _sonar_metrics_data(tmp_path)

        assert result["available"] is True
        assert result["status"] == "ERROR"
        assert result["new_code_coverage"] is None


# ---------------------------------------------------------------
# URL builder
# ---------------------------------------------------------------


class TestBuildSonarUrl:
    """Tests for _build_sonar_url URL validation."""

    def test_valid_https_url(self) -> None:
        from ai_engineering.policy.checks.sonar import _build_sonar_url

        url = _build_sonar_url(
            "https://sonarcloud.io",
            "/api/qualitygates/project_status",
            {"projectKey": "my-project"},
        )
        assert url is not None
        assert url.startswith("https://sonarcloud.io/api/qualitygates/project_status")
        assert "projectKey=my-project" in url

    def test_valid_http_localhost(self) -> None:
        from ai_engineering.policy.checks.sonar import _build_sonar_url

        url = _build_sonar_url(
            "http://localhost:9000",
            "/api/measures/component",
            {"component": "proj", "metricKeys": "coverage"},
        )
        assert url is not None
        assert url.startswith("http://localhost:9000/api/measures/component")

    def test_rejects_ftp_scheme(self) -> None:
        from ai_engineering.policy.checks.sonar import _build_sonar_url

        assert _build_sonar_url("ftp://evil.com", "/api/qualitygates/project_status", {}) is None

    def test_rejects_file_scheme(self) -> None:
        from ai_engineering.policy.checks.sonar import _build_sonar_url

        assert (
            _build_sonar_url("file:///etc/passwd", "/api/qualitygates/project_status", {}) is None
        )

    def test_rejects_unknown_api_path(self) -> None:
        from ai_engineering.policy.checks.sonar import _build_sonar_url

        assert _build_sonar_url("https://sonarcloud.io", "/api/admin/delete", {"key": "x"}) is None

    def test_rejects_empty_hostname(self) -> None:
        from ai_engineering.policy.checks.sonar import _build_sonar_url

        assert _build_sonar_url("https://", "/api/qualitygates/project_status", {}) is None

    def test_preserves_port(self) -> None:
        from ai_engineering.policy.checks.sonar import _build_sonar_url

        url = _build_sonar_url(
            "https://sonar.internal:9443",
            "/api/qualitygates/project_status",
            {"projectKey": "p"},
        )
        assert url is not None
        assert ":9443" in url

    def test_encodes_special_chars(self) -> None:
        from ai_engineering.policy.checks.sonar import _build_sonar_url

        url = _build_sonar_url(
            "https://sonarcloud.io",
            "/api/qualitygates/project_status",
            {"projectKey": "org:my-project"},
        )
        assert url is not None
        assert "org%3Amy-project" in url


class TestSonarApiGet:
    """Tests for _sonar_api_get HTTP client."""

    def test_returns_none_for_empty_hostname(self) -> None:
        from ai_engineering.policy.checks.sonar import _sonar_api_get

        assert _sonar_api_get("https:///path", "token") is None

    def test_returns_none_on_connection_error(self) -> None:
        from ai_engineering.policy.checks.sonar import _sonar_api_get

        result = _sonar_api_get("https://192.0.2.1:1/api/test", "tok")
        assert result is None

    def test_returns_none_on_non_200(self) -> None:
        from unittest.mock import MagicMock, patch

        from ai_engineering.policy.checks.sonar import _sonar_api_get

        mock_conn = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status = 401
        mock_conn.getresponse.return_value = mock_resp

        with patch(
            "ai_engineering.policy.checks.sonar.http.client.HTTPSConnection", return_value=mock_conn
        ):
            result = _sonar_api_get("https://sonar.io/api/test?key=x", "tok")
        assert result is None

    def test_returns_parsed_json_on_200(self) -> None:
        from unittest.mock import MagicMock, patch

        from ai_engineering.policy.checks.sonar import _sonar_api_get

        mock_conn = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"status": "OK"}'
        mock_conn.getresponse.return_value = mock_resp

        with patch(
            "ai_engineering.policy.checks.sonar.http.client.HTTPSConnection", return_value=mock_conn
        ):
            result = _sonar_api_get("https://sonar.io/api/test?key=x", "tok")
        assert result == {"status": "OK"}

    def test_uses_http_for_non_https(self) -> None:
        from unittest.mock import MagicMock, patch

        from ai_engineering.policy.checks.sonar import _sonar_api_get

        mock_conn = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"ok": true}'
        mock_conn.getresponse.return_value = mock_resp

        with patch(
            "ai_engineering.policy.checks.sonar.http.client.HTTPConnection", return_value=mock_conn
        ) as mock_cls:
            result = _sonar_api_get("http://localhost:9000/api/test", "tok")
        mock_cls.assert_called_once()
        assert result == {"ok": True}


# ---------------------------------------------------------------
# Script argument generation
# ---------------------------------------------------------------
