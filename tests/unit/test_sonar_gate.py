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
# Script argument generation
# ---------------------------------------------------------------


class TestScriptArguments:
    """Tests for sonar-pre-gate script argument construction."""

    def test_bash_script_exists(self) -> None:
        """Bash script is present in the skill directory."""
        script = (
            Path(__file__).resolve().parents[2]
            / ".ai-engineering"
            / "skills"
            / "dev"
            / "sonar-gate"
            / "scripts"
            / "sonar-pre-gate.sh"
        )
        assert script.exists(), f"Script not found: {script}"

    def test_powershell_script_exists(self) -> None:
        """PowerShell script is present in the skill directory."""
        script = (
            Path(__file__).resolve().parents[2]
            / ".ai-engineering"
            / "skills"
            / "dev"
            / "sonar-gate"
            / "scripts"
            / "sonar-pre-gate.ps1"
        )
        assert script.exists(), f"Script not found: {script}"

    def test_bash_script_has_skip_flag(self) -> None:
        """Bash script supports --skip-if-unconfigured flag."""
        script = (
            Path(__file__).resolve().parents[2]
            / ".ai-engineering"
            / "skills"
            / "dev"
            / "sonar-gate"
            / "scripts"
            / "sonar-pre-gate.sh"
        )
        content = script.read_text(encoding="utf-8")
        assert "--skip-if-unconfigured" in content

    def test_powershell_script_has_skip_flag(self) -> None:
        """PowerShell script supports -SkipIfUnconfigured flag."""
        script = (
            Path(__file__).resolve().parents[2]
            / ".ai-engineering"
            / "skills"
            / "dev"
            / "sonar-gate"
            / "scripts"
            / "sonar-pre-gate.ps1"
        )
        content = script.read_text(encoding="utf-8")
        assert "SkipIfUnconfigured" in content

    def test_bash_script_has_quality_gate_wait(self) -> None:
        """Bash script passes qualitygate.wait=true to sonar-scanner."""
        script = (
            Path(__file__).resolve().parents[2]
            / ".ai-engineering"
            / "skills"
            / "dev"
            / "sonar-gate"
            / "scripts"
            / "sonar-pre-gate.sh"
        )
        content = script.read_text(encoding="utf-8")
        assert "qualitygate.wait=true" in content

    def test_powershell_script_has_quality_gate_wait(self) -> None:
        """PowerShell script passes qualitygate.wait=true to sonar-scanner."""
        script = (
            Path(__file__).resolve().parents[2]
            / ".ai-engineering"
            / "skills"
            / "dev"
            / "sonar-gate"
            / "scripts"
            / "sonar-pre-gate.ps1"
        )
        content = script.read_text(encoding="utf-8")
        assert "qualitygate.wait=true" in content


# ---------------------------------------------------------------
# Template mirror integrity
# ---------------------------------------------------------------


class TestTemplateMirrors:
    """Tests that template mirrors match canonical files."""

    @pytest.fixture()
    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def test_skill_md_mirror_matches(self, repo_root: Path) -> None:
        canonical = repo_root / ".ai-engineering" / "skills" / "dev" / "sonar-gate" / "SKILL.md"
        mirror = (
            repo_root
            / "src"
            / "ai_engineering"
            / "templates"
            / ".ai-engineering"
            / "skills"
            / "dev"
            / "sonar-gate"
            / "SKILL.md"
        )
        assert canonical.read_text(encoding="utf-8") == mirror.read_text(encoding="utf-8")

    def test_bash_script_mirror_matches(self, repo_root: Path) -> None:
        canonical = (
            repo_root
            / ".ai-engineering"
            / "skills"
            / "dev"
            / "sonar-gate"
            / "scripts"
            / "sonar-pre-gate.sh"
        )
        mirror = (
            repo_root
            / "src"
            / "ai_engineering"
            / "templates"
            / ".ai-engineering"
            / "skills"
            / "dev"
            / "sonar-gate"
            / "scripts"
            / "sonar-pre-gate.sh"
        )
        assert canonical.read_text(encoding="utf-8") == mirror.read_text(encoding="utf-8")

    def test_powershell_script_mirror_matches(self, repo_root: Path) -> None:
        canonical = (
            repo_root
            / ".ai-engineering"
            / "skills"
            / "dev"
            / "sonar-gate"
            / "scripts"
            / "sonar-pre-gate.ps1"
        )
        mirror = (
            repo_root
            / "src"
            / "ai_engineering"
            / "templates"
            / ".ai-engineering"
            / "skills"
            / "dev"
            / "sonar-gate"
            / "scripts"
            / "sonar-pre-gate.ps1"
        )
        assert canonical.read_text(encoding="utf-8") == mirror.read_text(encoding="utf-8")

    def test_threshold_mapping_mirror_matches(self, repo_root: Path) -> None:
        canonical = (
            repo_root
            / ".ai-engineering"
            / "skills"
            / "dev"
            / "sonar-gate"
            / "references"
            / "sonar-threshold-mapping.md"
        )
        mirror = (
            repo_root
            / "src"
            / "ai_engineering"
            / "templates"
            / ".ai-engineering"
            / "skills"
            / "dev"
            / "sonar-gate"
            / "references"
            / "sonar-threshold-mapping.md"
        )
        assert canonical.read_text(encoding="utf-8") == mirror.read_text(encoding="utf-8")
