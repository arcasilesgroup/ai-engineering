"""Tests for Sonar-aware CI/CD generation rendering."""

from __future__ import annotations

import pytest

from ai_engineering.installer.cicd import _render_azure_ci, _render_github_ci
from ai_engineering.state.models import SonarCicdConfig

pytestmark = pytest.mark.unit


def test_github_sonarcloud_uses_unified_action_and_fork_guard() -> None:
    cfg = SonarCicdConfig(
        enabled=True,
        hostUrl="https://sonarcloud.io",
        projectKey="my-key",
        organization="my-org",
    )

    content = _render_github_ci(["python"], cfg)

    assert "fetch-depth: 0" in content
    # D038-003: migrated from sonarcloud-github-action@v3 to unified action
    assert "sonarqube-scan-action@fd88b7d7ccbaefd23d8f36f73b59db7a3d246602" in content
    assert "sonarcloud-github-action" not in content
    assert "head.repo.full_name == github.repository" in content
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

    assert "sonarqube-scan-action@fd88b7d7ccbaefd23d8f36f73b59db7a3d246602" in content
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
    assert "python coverage" in content


def test_azure_no_coverage_step_without_sonar() -> None:
    content = _render_azure_ci(["python"], None)

    assert "--cov-report=xml" not in content


def test_no_sonar_config_keeps_existing_render_output() -> None:
    github_expected = "\n".join(
        [
            "name: CI",
            "on: [push, pull_request]",
            "jobs:",
            "  checks:",
            "    runs-on: ubuntu-latest",
            "    steps:",
            "      - uses: actions/checkout@v4",
            "      - uses: astral-sh/setup-uv@v5",
            "      - run: uv sync",
            "      - run: uv run ruff check src/",
            "      - run: uv run pytest tests/ -q",
            "      - run: uv run ty check src/",
            "      - run: gitleaks detect --no-git",
            "      - run: semgrep scan --config auto",
            "",
        ]
    )
    azure_expected = "\n".join(
        [
            "trigger:",
            "- '*'",
            "pr:",
            "- '*'",
            "steps:",
            "- script: echo 'checkout is implicit in Azure Pipelines'",
            "  displayName: checkout",
            "- script: uv sync",
            "  displayName: uv sync",
            "- script: uv run ruff check src/ && uv run pytest tests/ -q && uv run ty check src/",
            "  displayName: python checks",
            "- script: gitleaks detect --no-git && semgrep scan --config auto",
            "  displayName: security checks",
            "",
        ]
    )

    assert _render_github_ci(["python"], None) == github_expected
    assert _render_azure_ci(["python"], None) == azure_expected
