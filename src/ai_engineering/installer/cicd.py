"""Stack-aware CI/CD file generation for install and regenerate flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CicdGenerationResult:
    """Result of CI/CD generation operation."""

    provider: str
    created: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)


def generate_pipelines(target: Path, *, provider: str, stacks: list[str]) -> CicdGenerationResult:
    """Generate provider-specific pipeline files with stack-aware checks."""
    result = CicdGenerationResult(provider=provider)

    if provider == "github":
        files = {
            target / ".github" / "workflows" / "ci.yml": _render_github_ci(stacks),
            target / ".github" / "workflows" / "ai-pr-review.yml": _render_github_ai_review(),
            target / ".github" / "workflows" / "ai-eng-gate.yml": _render_github_gate(),
        }
    else:
        files = {
            target / ".azure-pipelines" / "ci.yml": _render_azure_ci(stacks),
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


def _render_github_ci(stacks: list[str]) -> str:
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
        "      - uses: actions/checkout@v4",
    ]
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
    if dotnet:
        lines.extend(["      - run: dotnet build", "      - run: dotnet test --no-build"])
    if nextjs:
        lines.extend(
            [
                "      - run: npm ci",
                "      - run: npm run lint --if-present",
                "      - run: npm test --if-present",
            ]
        )
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


def _render_azure_ci(stacks: list[str]) -> str:
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
    if "dotnet" in stacks:
        steps.extend(
            ["- script: dotnet build && dotnet test --no-build", "  displayName: dotnet checks"]
        )
    if "nextjs" in stacks:
        steps.extend(
            [
                "- script: npm ci && npm run lint --if-present && npm test --if-present",
                "  displayName: nextjs checks",
            ]
        )
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
