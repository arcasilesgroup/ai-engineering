"""Pipeline risk gate injection for CI/CD configurations.

Generates risk gate step/task snippets that can be inserted
into existing pipeline files. Supports GitHub Actions and
Azure DevOps.

Functions:
- ``generate_github_step`` — produce a GitHub Actions step YAML snippet.
- ``generate_azure_task`` — produce an Azure DevOps task YAML snippet.
- ``suggest_injection`` — recommend where to add risk gates.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from ai_engineering.installer.cicd import CicdGenerationResult, generate_pipelines
from ai_engineering.pipeline.compliance import PipelineFile, PipelineType

# Template directory relative to this module.
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "pipeline"


def generate_github_step() -> str:
    """Generate a GitHub Actions risk gate step YAML snippet.

    Returns:
        YAML string for a GitHub Actions step that runs risk-check.
    """
    template_path = _TEMPLATES_DIR / "github-risk-gate-step.yml"
    if template_path.is_file():
        return template_path.read_text(encoding="utf-8")

    return dedent("""\
        - name: Risk Governance Gate
          run: |
            pip install ai-engineering
            ai-eng gate risk-check --strict
          shell: bash
    """)


def generate_azure_task() -> str:
    """Generate an Azure DevOps risk gate task YAML snippet.

    Returns:
        YAML string for an Azure DevOps task that runs risk-check.
    """
    template_path = _TEMPLATES_DIR / "azure-risk-gate-task.yml"
    if template_path.is_file():
        return template_path.read_text(encoding="utf-8")

    return dedent("""\
        - script: |
            pip install ai-engineering
            ai-eng gate risk-check --strict
          displayName: 'Risk Governance Gate'
          failOnStderr: true
    """)


def generate_github_sonar_step() -> str:
    """Generate a GitHub Actions Sonar analysis snippet."""
    template_path = _TEMPLATES_DIR / "github-sonar-step.yml"
    if template_path.is_file():
        return template_path.read_text(encoding="utf-8")

    return dedent("""\
        - name: Sonar analysis
          if: >
            ${{ github.event_name != 'pull_request' ||
                github.event.pull_request.head.repo.full_name == github.repository }}
          uses: SonarSource/sonarqube-scan-action@fd88b7d7ccbaefd23d8f36f73b59db7a3d246602  # v6
          env:
            SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          with:
            args: >
              -Dsonar.projectKey=<project-key>
              -Dsonar.organization=<organization>
    """)


def generate_azure_sonar_tasks() -> str:
    """Generate Azure DevOps Sonar task snippets."""
    template_path = _TEMPLATES_DIR / "azure-sonar-task.yml"
    if template_path.is_file():
        return template_path.read_text(encoding="utf-8")

    return dedent("""\
        - task: SonarCloudPrepare@3
          inputs:
            SonarCloud: '$(SONAR_SERVICE_CONNECTION)'
            scannerMode: 'CLI'
            configMode: 'manual'
            organization: '<organization>'
            cliProjectKey: '<project-key>'
            cliSources: '.'
        - task: SonarCloudAnalyze@3
        - task: SonarCloudPublish@3
          inputs:
            pollingTimeoutSec: '300'
    """)


def suggest_injection(pipeline: PipelineFile, *, injection_type: str = "risk") -> str:
    """Suggest a risk gate snippet for a specific pipeline file.

    Args:
        pipeline: The pipeline file to generate a suggestion for.

    Returns:
        YAML snippet appropriate for the pipeline type, with
        instructions for where to insert it.
    """
    if pipeline.pipeline_type == PipelineType.GITHUB_ACTIONS:
        snippet = (
            generate_github_sonar_step() if injection_type == "sonar" else generate_github_step()
        )
        return (
            f"# Add this step to your workflow in {pipeline.path.as_posix()}\n"
            f"# Place it after checkout and before deployment steps:\n\n"
            f"{snippet}"
        )

    if pipeline.pipeline_type == PipelineType.AZURE_DEVOPS:
        snippet = (
            generate_azure_sonar_tasks() if injection_type == "sonar" else generate_azure_task()
        )
        return (
            f"# Add this task to your pipeline in {pipeline.path.as_posix()}\n"
            f"# Place it after checkout and before deployment tasks:\n\n"
            f"{snippet}"
        )

    return f"# Unknown pipeline type for {pipeline.path.as_posix()}"


def generate_workflows(
    project_root: Path,
    *,
    provider: str,
    stacks: list[str],
) -> CicdGenerationResult:
    """Generate full CI/CD workflows for a provider.

    This is a higher-level entrypoint than snippet injection and is used by
    installer and regeneration flows.
    """
    return generate_pipelines(project_root, provider=provider, stacks=stacks)
