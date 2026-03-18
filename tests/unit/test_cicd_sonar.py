"""Tests for Sonar-aware CI/CD generation rendering."""

from __future__ import annotations

import pytest

from ai_engineering.installer.cicd import _render_azure_ci, _render_github_ci
from ai_engineering.state.models import SonarCicdConfig

pytestmark = pytest.mark.unit


def test_github_sonarcloud_uses_unified_action() -> None:
    cfg = SonarCicdConfig(
        enabled=True,
        hostUrl="https://sonarcloud.io",
        projectKey="my-key",
        organization="my-org",
    )

    content = _render_github_ci(["python"], cfg)

    assert "fetch-depth: 0" in content
    assert "sonarqube-scan-action" in content
    assert "sonarcloud-github-action" not in content
    assert "-Dsonar.projectKey=my-key" in content
    assert "-Dsonar.organization=my-org" in content


def test_github_sonarqube_includes_action_and_host_url() -> None:
    cfg = SonarCicdConfig(
        enabled=True,
        hostUrl="https://sonar.corp.local",
        projectKey="my-key",
        organization="",
    )

    content = _render_github_ci(["python"], cfg)

    assert "sonarqube-scan-action" in content
    assert "-Dsonar.host.url=https://sonar.corp.local" in content


def test_github_sonar_generates_coverage_step_python() -> None:
    cfg = SonarCicdConfig(
        enabled=True,
        hostUrl="https://sonarcloud.io",
        projectKey="my-key",
        organization="my-org",
    )

    content = _render_github_ci(["python"], cfg)

    assert "--cov=src --cov-report=xml:coverage.xml" in content


def test_github_sonar_generates_coverage_step_dotnet() -> None:
    cfg = SonarCicdConfig(
        enabled=True,
        hostUrl="https://sonarcloud.io",
        projectKey="my-key",
        organization="my-org",
    )

    content = _render_github_ci(["dotnet"], cfg)

    assert "XPlat Code Coverage" in content


def test_github_sonar_generates_coverage_step_nextjs() -> None:
    cfg = SonarCicdConfig(
        enabled=True,
        hostUrl="https://sonarcloud.io",
        projectKey="my-key",
        organization="my-org",
    )

    content = _render_github_ci(["nextjs"], cfg)

    assert "c8 report --reporter=lcov" in content


def test_github_no_coverage_step_without_sonar() -> None:
    content = _render_github_ci(["python"], None)

    assert "--cov-report=xml" not in content
    assert "coverage.xml" not in content


def test_azure_sonarcloud_includes_prepare_analyze_publish() -> None:
    cfg = SonarCicdConfig(
        enabled=True,
        hostUrl="https://sonarcloud.io",
        projectKey="my-key",
        organization="my-org",
    )

    content = _render_azure_ci(["python"], cfg)

    assert "SonarCloudPrepare@3" in content
    assert "SonarCloudAnalyze@3" in content
    assert "SonarCloudPublish@3" in content
    assert "$(SONAR_SERVICE_CONNECTION)" in content


def test_azure_sonarqube_includes_prepare_analyze_publish() -> None:
    cfg = SonarCicdConfig(
        enabled=True,
        hostUrl="https://sonar.corp.local",
        projectKey="my-key",
    )

    content = _render_azure_ci(["python"], cfg)

    assert "SonarQubePrepare@7" in content
    assert "SonarQubeAnalyze@7" in content
    assert "SonarQubePublish@7" in content
    assert "sonar.host.url=https://sonar.corp.local" in content


def test_azure_sonar_generates_coverage_step_python() -> None:
    cfg = SonarCicdConfig(
        enabled=True,
        hostUrl="https://sonarcloud.io",
        projectKey="my-key",
        organization="my-org",
    )

    content = _render_azure_ci(["python"], cfg)

    assert "--cov=src --cov-report=xml:coverage.xml" in content
    assert "Python coverage" in content


def test_azure_no_coverage_step_without_sonar() -> None:
    content = _render_azure_ci(["python"], None)

    assert "--cov-report=xml" not in content


def test_no_sonar_config_produces_valid_yaml_output() -> None:
    """Generator produces structured YAML with proper jobs."""
    github = _render_github_ci(["python"], None)
    azure = _render_azure_ci(["python"], None)

    # GitHub: multi-job structure
    assert "name: CI" in github
    assert "lint:" in github
    assert "test:" in github
    assert "security:" in github
    assert "gate:" in github
    assert "permissions:" in github
    assert "concurrency:" in github
    assert "timeout-minutes:" in github
    assert "ruff check" in github
    assert "pytest" in github
    assert "gitleaks" in github
    assert "semgrep" in github
    # No sonar job when no config
    assert "sonarcloud:" not in github

    # Azure: single-stage structure
    assert "trigger:" in azure
    assert "pool:" in azure
    assert "vmImage: ubuntu-latest" in azure
    assert "ruff check" in azure
    assert "pytest" in azure
    assert "gitleaks" in azure
    assert "semgrep" in azure
    assert "SonarCloud" not in azure
