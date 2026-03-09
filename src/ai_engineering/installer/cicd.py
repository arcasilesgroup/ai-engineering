"""Stack-aware CI/CD file generation for install and regenerate flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.state.models import SonarCicdConfig


@dataclass
class CicdGenerationResult:
    """Result of CI/CD generation operation."""

    provider: str
    created: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)


def generate_pipelines(
    target: Path,
    *,
    provider: str,
    stacks: list[str],
    sonar_config: SonarCicdConfig | None = None,
) -> CicdGenerationResult:
    """Generate provider-specific pipeline files with stack-aware checks."""
    result = CicdGenerationResult(provider=provider)

    if provider == "github":
        files = {
            target / ".github" / "workflows" / "ci.yml": _render_github_ci(stacks, sonar_config),
            target / ".github" / "workflows" / "ai-pr-review.yml": _render_github_ai_review(),
            target / ".github" / "workflows" / "ai-eng-gate.yml": _render_github_gate(),
        }
    else:
        files = {
            target / ".azure-pipelines" / "ci.yml": _render_azure_ci(stacks, sonar_config),
            target / ".azure-pipelines" / "ai-pr-review.yml": _render_azure_ai_review(),
            target / ".azure-pipelines" / "ai-eng-gate.yml": _render_azure_gate(),
        }

    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            result.skipped.append(path)
            continue
        path.write_text(content, encoding="utf-8")
        result.created.append(path)

    return result


def _render_github_ci(stacks: list[str], sonar_config: SonarCicdConfig | None = None) -> str:
    python = "python" in stacks
    dotnet = "dotnet" in stacks
    nextjs = "nextjs" in stacks

    lines = [
        "name: CI",
        "on: [push, pull_request]",
        "jobs:",
        "  checks:",
        "    runs-on: ubuntu-latest",
        "    steps:",
    ]
    if sonar_config is not None and sonar_config.enabled:
        lines.extend(
            [
                "      - uses: actions/checkout@v4",
                "        with:",
                "          fetch-depth: 0",
            ]
        )
    else:
        lines.append("      - uses: actions/checkout@v4")

    has_sonar = sonar_config is not None and sonar_config.enabled and sonar_config.project_key

    if python:
        lines.extend(
            [
                "      - uses: astral-sh/setup-uv@v5",
                "      - run: uv sync",
                "      - run: uv run ruff check src/",
                "      - run: uv run pytest tests/ -q",
                "      - run: uv run ty check src/",
            ]
        )
        if has_sonar:
            lines.append(
                "      - run: uv run pytest tests/ -q --cov=src --cov-report=xml:coverage.xml"
            )
    if dotnet:
        lines.extend(["      - run: dotnet build", "      - run: dotnet test --no-build"])
        if has_sonar:
            lines.append('      - run: dotnet test --no-build --collect:"XPlat Code Coverage"')
    if nextjs:
        lines.extend(
            [
                "      - run: npm ci",
                "      - run: npm run lint --if-present",
                "      - run: npm test --if-present",
            ]
        )
        if has_sonar:
            lines.append("      - run: npx c8 report --reporter=lcov")

    if sonar_config is not None and sonar_config.enabled and sonar_config.project_key:
        lines.extend(_render_github_sonar_steps(sonar_config))

    lines.extend(
        ["      - run: gitleaks detect --no-git", "      - run: semgrep scan --config auto"]
    )
    return "\n".join(lines) + "\n"


def _render_github_ai_review() -> str:
    return (
        "name: AI PR Review\n"
        "on:\n  pull_request:\n"
        "jobs:\n"
        "  ai-review:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "      - run: echo 'High/Critical findings fail merge'\n"
        "      - run: ai-eng review pr --strict\n"
    )


def _render_github_gate() -> str:
    return (
        "name: AI Engineering Gate\n"
        "on:\n  pull_request:\n"
        "jobs:\n"
        "  gate:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "      - run: ai-eng gate risk-check --strict\n"
    )


def _render_azure_ci(stacks: list[str], sonar_config: SonarCicdConfig | None = None) -> str:
    has_sonar = sonar_config is not None and sonar_config.enabled and sonar_config.project_key
    steps = ["- script: echo 'checkout is implicit in Azure Pipelines'", "  displayName: checkout"]
    if "python" in stacks:
        steps.extend(
            [
                "- script: uv sync",
                "  displayName: uv sync",
                (
                    "- script: uv run ruff check src/ && "
                    "uv run pytest tests/ -q && uv run ty check src/"
                ),
                "  displayName: python checks",
            ]
        )
        if has_sonar:
            steps.extend(
                [
                    "- script: uv run pytest tests/ -q --cov=src --cov-report=xml:coverage.xml",
                    "  displayName: python coverage",
                ]
            )
    if "dotnet" in stacks:
        steps.extend(
            ["- script: dotnet build && dotnet test --no-build", "  displayName: dotnet checks"]
        )
        if has_sonar:
            steps.extend(
                [
                    '- script: dotnet test --no-build --collect:"XPlat Code Coverage"',
                    "  displayName: dotnet coverage",
                ]
            )
    if "nextjs" in stacks:
        steps.extend(
            [
                "- script: npm ci && npm run lint --if-present && npm test --if-present",
                "  displayName: nextjs checks",
            ]
        )
        if has_sonar:
            steps.extend(
                [
                    "- script: npx c8 report --reporter=lcov",
                    "  displayName: js coverage",
                ]
            )

    if sonar_config is not None and sonar_config.enabled and sonar_config.project_key:
        steps.extend(_render_azure_sonar_steps(sonar_config))

    steps.extend(
        [
            "- script: gitleaks detect --no-git && semgrep scan --config auto",
            "  displayName: security checks",
        ]
    )
    return "trigger:\n- '*'\npr:\n- '*'\nsteps:\n" + "\n".join(steps) + "\n"


def _render_azure_ai_review() -> str:
    return (
        "trigger: none\n"
        "pr:\n- '*'\n"
        "steps:\n"
        "- script: ai-eng review pr --strict\n"
        "  displayName: ai-pr-review\n"
    )


def _render_azure_gate() -> str:
    return (
        "trigger: none\n"
        "pr:\n- '*'\n"
        "steps:\n"
        "- script: ai-eng gate risk-check --strict\n"
        "  displayName: ai-eng-gate\n"
    )


def _render_github_sonar_steps(sonar_config: SonarCicdConfig) -> list[str]:
    guard = (
        "      - if: "
        "${{ github.event_name != 'pull_request' || "
        "github.event.pull_request.head.repo.full_name == github.repository }}"
    )
    # Unified action for both SonarCloud and SonarQube (D038-003)
    # Pin to full SHA for supply-chain security (S7637)
    _sonar_action = (
        "SonarSource/sonarqube-scan-action"
        "@fd88b7d7ccbaefd23d8f36f73b59db7a3d246602"  # v6
    )
    name = "SonarCloud Scan" if sonar_config.is_sonarcloud else "SonarQube Scan"
    lines = [
        guard,
        f"        name: {name}",
        f"        uses: {_sonar_action}",
        "        env:",
        "          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}",
        "        with:",
        "          args: >",
        f"            -Dsonar.projectKey={sonar_config.project_key}",
    ]
    if sonar_config.is_sonarcloud:
        lines.append(f"            -Dsonar.organization={sonar_config.organization}")
    else:
        lines.append(f"            -Dsonar.host.url={sonar_config.host_url}")
        if sonar_config.organization:
            lines.append(f"            -Dsonar.organization={sonar_config.organization}")
    return lines


def _render_azure_sonar_steps(sonar_config: SonarCicdConfig) -> list[str]:
    service_connection = sonar_config.service_connection or "$(SONAR_SERVICE_CONNECTION)"
    if sonar_config.is_sonarcloud:
        return [
            "- task: SonarCloudPrepare@3",
            "  inputs:",
            f"    SonarCloud: '{service_connection}'",
            "    scannerMode: 'CLI'",
            "    configMode: 'manual'",
            f"    organization: '{sonar_config.organization}'",
            f"    cliProjectKey: '{sonar_config.project_key}'",
            "    cliSources: '.'",
            "- task: SonarCloudAnalyze@3",
            "- task: SonarCloudPublish@3",
            "  inputs:",
            "    pollingTimeoutSec: '300'",
        ]

    lines = [
        "- task: SonarQubePrepare@7",
        "  inputs:",
        f"    SonarQube: '{service_connection}'",
        "    scannerMode: 'cli'",
        "    configMode: 'manual'",
        f"    cliProjectKey: '{sonar_config.project_key}'",
        "    cliSources: '.'",
        "    extraProperties: |",
        f"      sonar.host.url={sonar_config.host_url}",
    ]
    if sonar_config.organization:
        lines.append(f"      sonar.organization={sonar_config.organization}")
    lines.extend(
        [
            "- task: SonarQubeAnalyze@7",
            "- task: SonarQubePublish@7",
            "  inputs:",
            "    pollingTimeoutSec: '300'",
        ]
    )
    return lines
