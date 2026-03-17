"""Stack-aware CI/CD file generation for install and regenerate flows.

Generates provider-specific pipeline files (GitHub Actions, Azure Pipelines)
using YAML composition from the action-pins manifest and stack-aware templates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ai_engineering.state.models import SonarCicdConfig

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "pipeline"


@dataclass
class CicdGenerationResult:
    """Result of CI/CD generation operation."""

    provider: str
    created: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)


def _load_action_pins() -> dict[str, dict[str, str | None]]:
    """Load action SHA pins from the centralized manifest."""
    pins_file = _TEMPLATES_DIR / "action-pins.yml"
    if not pins_file.is_file():
        return {}
    data = yaml.safe_load(pins_file.read_text(encoding="utf-8"))
    return data or {}


def _pin(action: str, pins: dict[str, dict[str, str | None]] | None) -> str:
    """Return a pinned action reference: owner/action@sha # version."""
    if not pins:
        return action
    info = pins.get(action)
    if not info:
        return action
    sha = info.get("sha")
    version = info.get("version", "")
    if sha:
        return f"{action}@{sha} # {version}"
    return f"{action}@{version}"


def generate_pipelines(
    target: Path,
    *,
    provider: str,
    stacks: list[str],
    sonar_config: SonarCicdConfig | None = None,
) -> CicdGenerationResult:
    """Generate provider-specific pipeline files with stack-aware checks."""
    result = CicdGenerationResult(provider=provider)
    pins = _load_action_pins()

    if provider == "github":
        files = _build_github_files(target, stacks, pins, sonar_config)
    else:
        files = _build_azure_files(target, stacks, sonar_config)

    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            result.skipped.append(path)
            continue
        path.write_text(content, encoding="utf-8")
        result.created.append(path)

    return result


# ---------------------------------------------------------------------------
# GitHub Actions
# ---------------------------------------------------------------------------


def _build_github_files(
    target: Path,
    stacks: list[str],
    pins: dict,
    sonar_config: SonarCicdConfig | None,
) -> dict[Path, str]:
    wf = target / ".github" / "workflows"
    return {
        wf / "ci.yml": _render_github_ci(stacks, sonar_config, pins=pins),
        wf / "ai-pr-review.yml": _render_github_ai_review(pins=pins),
        wf / "ai-eng-gate.yml": _render_github_gate(pins=pins),
    }


def _render_github_ci(
    stacks: list[str],
    sonar_config: SonarCicdConfig | None = None,
    pins: dict | None = None,
) -> str:
    """Render a production-quality GitHub Actions CI workflow."""
    has_sonar = sonar_config is not None and sonar_config.enabled and sonar_config.project_key

    checkout = _pin("actions/checkout", pins)
    setup_uv = _pin("astral-sh/setup-uv", pins)

    # --- Build YAML as structured data ---
    workflow: dict = {
        "name": "CI",
        "on": {"push": {"branches": ["main"]}, "pull_request": {"branches": ["main"]}},
        "permissions": {"contents": "read"},
        "concurrency": {"group": "ci-${{ github.ref }}", "cancel-in-progress": True},
    }

    jobs: dict = {}

    # --- Lint & Security job ---
    lint_steps: list[dict] = [{"uses": checkout}]

    if "python" in stacks:
        lint_steps.extend(
            [
                {"uses": setup_uv, "with": {"enable-cache": True}},
                {"name": "Install", "run": "uv sync --dev"},
                {"name": "Ruff check", "run": "uv run ruff check src/ tests/"},
                {"name": "Ruff format", "run": "uv run ruff format --check src/ tests/"},
            ]
        )
    if "dotnet" in stacks:
        lint_steps.append({"name": "Format check", "run": "dotnet format --verify-no-changes"})
    if "nextjs" in stacks:
        lint_steps.extend(
            [
                {"name": "Install", "run": "npm ci"},
                {"name": "Lint", "run": "npm run lint --if-present"},
            ]
        )

    jobs["lint"] = {
        "name": "Lint & Format",
        "runs-on": "ubuntu-latest",
        "timeout-minutes": 10,
        "steps": lint_steps,
    }

    # --- Test job ---
    test_steps: list[dict] = [{"uses": checkout, "with": {"fetch-depth": 0}}]

    if "python" in stacks:
        test_steps.extend(
            [
                {"uses": setup_uv, "with": {"enable-cache": True}},
                {"name": "Install", "run": "uv sync --dev"},
                {"name": "Test", "run": "uv run pytest tests/ -v --durations=10"},
                {"name": "Type check", "run": "uv run ty check src/"},
            ]
        )
        if has_sonar:
            test_steps.append(
                {
                    "name": "Coverage",
                    "run": ("uv run pytest tests/ -v --cov=src --cov-report=xml:coverage.xml"),
                }
            )
    if "dotnet" in stacks:
        test_steps.extend(
            [
                {"name": "Build", "run": "dotnet build"},
                {"name": "Test", "run": "dotnet test --no-build"},
            ]
        )
        if has_sonar:
            test_steps.append(
                {
                    "name": "Coverage",
                    "run": 'dotnet test --no-build --collect:"XPlat Code Coverage"',
                }
            )
    if "nextjs" in stacks:
        test_steps.extend(
            [
                {"name": "Install", "run": "npm ci"},
                {"name": "Test", "run": "npm test --if-present"},
            ]
        )
        if has_sonar:
            test_steps.append({"name": "Coverage", "run": "npx c8 report --reporter=lcov"})

    jobs["test"] = {
        "name": "Test",
        "runs-on": "ubuntu-latest",
        "timeout-minutes": 30,
        "steps": test_steps,
    }

    # --- Security job ---
    sec_steps: list[dict] = [{"uses": checkout}]
    if "python" in stacks:
        sec_steps.extend(
            [
                {"uses": setup_uv, "with": {"enable-cache": True}},
                {"name": "Install", "run": "uv sync --dev"},
                {"name": "pip-audit", "run": "uv run pip-audit"},
            ]
        )
    if "dotnet" in stacks:
        sec_steps.append(
            {"name": "Vuln check", "run": "dotnet list package --vulnerable --include-transitive"}
        )
    if "nextjs" in stacks:
        sec_steps.append({"name": "npm audit", "run": "npm audit --audit-level=high || true"})
    sec_steps.extend(
        [
            {"name": "gitleaks", "run": "gitleaks detect --no-git --no-banner --redact"},
            {"name": "semgrep", "run": "semgrep scan --config auto"},
        ]
    )

    jobs["security"] = {
        "name": "Security",
        "runs-on": "ubuntu-latest",
        "timeout-minutes": 15,
        "steps": sec_steps,
    }

    # --- SonarCloud job (optional) ---
    if has_sonar and sonar_config is not None:
        sonar_action = _pin("SonarSource/sonarqube-scan-action", pins)
        sonar_name = "SonarCloud Scan" if sonar_config.is_sonarcloud else "SonarQube Scan"
        sonar_args = f"-Dsonar.projectKey={sonar_config.project_key}"
        if sonar_config.is_sonarcloud:
            sonar_args += f"\n-Dsonar.organization={sonar_config.organization}"
        else:
            sonar_args += f"\n-Dsonar.host.url={sonar_config.host_url}"
            if sonar_config.organization:
                sonar_args += f"\n-Dsonar.organization={sonar_config.organization}"

        jobs["sonarcloud"] = {
            "name": "SonarCloud",
            "needs": ["test"],
            "runs-on": "ubuntu-latest",
            "timeout-minutes": 15,
            "steps": [
                {"uses": checkout, "with": {"fetch-depth": 0}},
                {
                    "name": sonar_name,
                    "uses": sonar_action,
                    "env": {"SONAR_TOKEN": "${{ secrets.SONAR_TOKEN }}"},
                    "with": {"args": sonar_args},
                },
            ],
        }

    # --- AI Engineering Gate ---
    jobs["gate"] = {
        "name": "Risk Gate",
        "runs-on": "ubuntu-latest",
        "timeout-minutes": 5,
        "steps": [
            {"uses": checkout},
            {"name": "Risk check", "run": "ai-eng gate risk-check --strict"},
        ],
    }

    workflow["jobs"] = jobs
    return yaml.dump(workflow, default_flow_style=False, sort_keys=False, width=120)


def _render_github_ai_review(*, pins: dict | None = None) -> str:
    checkout = _pin("actions/checkout", pins)
    workflow = {
        "name": "AI PR Review",
        "on": {"pull_request": None},
        "permissions": {"contents": "read", "pull-requests": "write"},
        "jobs": {
            "ai-review": {
                "name": "AI PR Review",
                "runs-on": "ubuntu-latest",
                "timeout-minutes": 10,
                "steps": [
                    {"uses": checkout},
                    {"name": "Review", "run": "ai-eng review pr --strict"},
                ],
            }
        },
    }
    return yaml.dump(workflow, default_flow_style=False, sort_keys=False, width=120)


def _render_github_gate(*, pins: dict | None = None) -> str:
    checkout = _pin("actions/checkout", pins)
    workflow = {
        "name": "AI Engineering Gate",
        "on": {"pull_request": None},
        "permissions": {"contents": "read"},
        "jobs": {
            "gate": {
                "name": "Risk Gate",
                "runs-on": "ubuntu-latest",
                "timeout-minutes": 5,
                "steps": [
                    {"uses": checkout},
                    {"name": "Risk check", "run": "ai-eng gate risk-check --strict"},
                ],
            }
        },
    }
    return yaml.dump(workflow, default_flow_style=False, sort_keys=False, width=120)


# ---------------------------------------------------------------------------
# Azure Pipelines
# ---------------------------------------------------------------------------


def _build_azure_files(
    target: Path,
    stacks: list[str],
    sonar_config: SonarCicdConfig | None,
) -> dict[Path, str]:
    az = target / ".azure-pipelines"
    return {
        az / "ci.yml": _render_azure_ci(stacks, sonar_config),
        az / "ai-pr-review.yml": _render_azure_ai_review(),
        az / "ai-eng-gate.yml": _render_azure_gate(),
    }


def _render_azure_ci(
    stacks: list[str],
    sonar_config: SonarCicdConfig | None = None,
) -> str:
    has_sonar = sonar_config is not None and sonar_config.enabled and sonar_config.project_key

    steps: list[dict] = []

    if "python" in stacks:
        steps.extend(
            [
                {"script": "uv sync --dev", "displayName": "Install Python deps"},
                {
                    "script": "uv run ruff check src/ && uv run ruff format --check src/",
                    "displayName": "Lint Python",
                },
                {"script": "uv run pytest tests/ -v --durations=10", "displayName": "Test Python"},
                {"script": "uv run ty check src/", "displayName": "Type check"},
            ]
        )
        if has_sonar:
            steps.append(
                {
                    "script": ("uv run pytest tests/ -v --cov=src --cov-report=xml:coverage.xml"),
                    "displayName": "Python coverage",
                }
            )
    if "dotnet" in stacks:
        steps.extend(
            [
                {"script": "dotnet build", "displayName": "Build .NET"},
                {"script": "dotnet test --no-build", "displayName": "Test .NET"},
            ]
        )
        if has_sonar:
            steps.append(
                {
                    "script": 'dotnet test --no-build --collect:"XPlat Code Coverage"',
                    "displayName": ".NET coverage",
                }
            )
    if "nextjs" in stacks:
        steps.extend(
            [
                {"script": "npm ci", "displayName": "Install Node deps"},
                {"script": "npm run lint --if-present", "displayName": "Lint Node"},
                {"script": "npm test --if-present", "displayName": "Test Node"},
            ]
        )
        if has_sonar:
            steps.append({"script": "npx c8 report --reporter=lcov", "displayName": "JS coverage"})

    # Sonar tasks
    if has_sonar and sonar_config is not None:
        steps.extend(_render_azure_sonar_steps(sonar_config))

    # Security
    steps.extend(
        [
            {
                "script": "gitleaks detect --no-git --no-banner --redact",
                "displayName": "Secret scan",
            },
            {"script": "semgrep scan --config auto", "displayName": "SAST scan"},
        ]
    )

    pipeline: dict = {
        "trigger": {"branches": {"include": ["main"]}},
        "pr": {"branches": {"include": ["main"]}},
        "pool": {"vmImage": "ubuntu-latest"},
        "steps": steps,
    }
    return yaml.dump(pipeline, default_flow_style=False, sort_keys=False, width=120)


def _render_azure_ai_review() -> str:
    pipeline = {
        "trigger": "none",
        "pr": {"branches": {"include": ["main"]}},
        "pool": {"vmImage": "ubuntu-latest"},
        "steps": [{"script": "ai-eng review pr --strict", "displayName": "AI PR Review"}],
    }
    return yaml.dump(pipeline, default_flow_style=False, sort_keys=False, width=120)


def _render_azure_gate() -> str:
    pipeline = {
        "trigger": "none",
        "pr": {"branches": {"include": ["main"]}},
        "pool": {"vmImage": "ubuntu-latest"},
        "steps": [
            {"script": "ai-eng gate risk-check --strict", "displayName": "Risk Gate"},
        ],
    }
    return yaml.dump(pipeline, default_flow_style=False, sort_keys=False, width=120)


def _render_azure_sonar_steps(sonar_config: SonarCicdConfig) -> list[dict]:
    """Render Azure Pipelines Sonar tasks."""
    service_connection = sonar_config.service_connection or "$(SONAR_SERVICE_CONNECTION)"

    if sonar_config.is_sonarcloud:
        return [
            {
                "task": "SonarCloudPrepare@3",
                "inputs": {
                    "SonarCloud": service_connection,
                    "scannerMode": "CLI",
                    "configMode": "manual",
                    "organization": sonar_config.organization,
                    "cliProjectKey": sonar_config.project_key,
                    "cliSources": ".",
                },
            },
            {"task": "SonarCloudAnalyze@3"},
            {"task": "SonarCloudPublish@3", "inputs": {"pollingTimeoutSec": "300"}},
        ]

    inputs: dict = {
        "SonarQube": service_connection,
        "scannerMode": "cli",
        "configMode": "manual",
        "cliProjectKey": sonar_config.project_key,
        "cliSources": ".",
        "extraProperties": f"sonar.host.url={sonar_config.host_url}",
    }
    if sonar_config.organization:
        inputs["extraProperties"] += f"\nsonar.organization={sonar_config.organization}"

    return [
        {"task": "SonarQubePrepare@7", "inputs": inputs},
        {"task": "SonarQubeAnalyze@7"},
        {"task": "SonarQubePublish@7", "inputs": {"pollingTimeoutSec": "300"}},
    ]
