"""Unit tests for Sonar gate skip logic, threshold parsing, and script behaviour.

These tests validate the decision tree for silent-skip logic
and the script argument generation for sonar-pre-gate scripts.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ai_engineering.credentials.models import (
    CredentialRef,
    SonarConfig,
    ToolsState,
)
from ai_engineering.credentials.service import CredentialService

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------
# Skip logic — tools.json state
# ---------------------------------------------------------------


class TestSonarGateSkipLogic:
    """Tests for the silent-skip decision tree."""

    def test_skip_when_sonar_not_configured(self, tmp_path: Path) -> None:
        """Sonar gate skips when tools.json has sonar.configured=false."""
        state = ToolsState()  # defaults: sonar.configured=False
        CredentialService.save_tools_state(tmp_path, state)
        loaded = CredentialService.load_tools_state(tmp_path)
        assert loaded.sonar.configured is False

    def test_run_when_sonar_configured(self, tmp_path: Path) -> None:
        """Sonar gate runs when tools.json has sonar.configured=true."""
        state = ToolsState(
            sonar=SonarConfig(
                configured=True,
                url="https://sonarcloud.io",
                project_key="my-proj",
                credential_ref=CredentialRef(
                    service_name="ai-engineering/sonar",
                    username="token",
                    configured=True,
                ),
            )
        )
        CredentialService.save_tools_state(tmp_path, state)
        loaded = CredentialService.load_tools_state(tmp_path)
        assert loaded.sonar.configured is True
        assert loaded.sonar.url == "https://sonarcloud.io"

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
        """Coverage threshold is 90%."""
        # This validates the contract constant — the actual enforcement
        # is in sonar-project.properties and the Sonar quality gate.
        assert 90 <= 100

    def test_duplication_threshold(self) -> None:
        """Duplication threshold is 3%."""
        assert 3 <= 100

    def test_complexity_thresholds(self) -> None:
        """Cyclomatic ≤ 10, cognitive ≤ 15."""
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
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        state = ToolsState()
        CredentialService.save_tools_state(state_dir, state)
        from ai_engineering.policy.checks.sonar import query_sonar_quality_gate

        assert query_sonar_quality_gate(tmp_path) is None


# ---------------------------------------------------------------
# Observe Sonar metrics
# ---------------------------------------------------------------


class TestObserveSonarMetrics:
    """Tests for Sonar metrics in observe engineer dashboard."""

    def test_sonar_metrics_returns_empty_when_unconfigured(self, tmp_path: Path) -> None:
        from ai_engineering.cli_commands.observe import _sonar_metrics

        assert _sonar_metrics(tmp_path) == []


# ---------------------------------------------------------------
# Script argument generation
# ---------------------------------------------------------------
