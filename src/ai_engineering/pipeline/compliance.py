"""Pipeline compliance scanning for CI/CD configurations.

Scans project CI/CD pipeline files to check whether required
risk governance gates are present. Supports GitHub Actions and
Azure DevOps pipelines.

Functions:
- ``detect_pipelines`` — find CI/CD config files in a project.
- ``scan_pipeline`` — check a single pipeline for risk gates.
- ``scan_all_pipelines`` — check all detected pipelines.
- ``compliance_report`` — generate a compliance summary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class PipelineType(Enum):
    """Known CI/CD pipeline types."""

    GITHUB_ACTIONS = "github-actions"
    AZURE_DEVOPS = "azure-devops"
    UNKNOWN = "unknown"


@dataclass
class PipelineFile:
    """A detected CI/CD pipeline configuration file."""

    path: Path
    pipeline_type: PipelineType


@dataclass
class ComplianceCheck:
    """Result of a single compliance check on a pipeline."""

    name: str
    passed: bool
    detail: str = ""


@dataclass
class PipelineComplianceResult:
    """Compliance result for a single pipeline file."""

    pipeline: PipelineFile
    checks: list[ComplianceCheck] = field(default_factory=list)

    @property
    def compliant(self) -> bool:
        """True if all compliance checks passed."""
        return all(c.passed for c in self.checks)


@dataclass
class ComplianceReport:
    """Aggregated compliance report across all pipelines."""

    results: list[PipelineComplianceResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def all_compliant(self) -> bool:
        """True if all pipelines are compliant."""
        return all(r.compliant for r in self.results)

    @property
    def total_pipelines(self) -> int:
        """Number of scanned pipelines."""
        return len(self.results)

    def to_markdown(self) -> str:
        """Render compliance report as Markdown.

        Returns:
            Markdown-formatted compliance summary.
        """
        lines: list[str] = []
        lines.append("## Pipeline Compliance Report")
        lines.append("")

        status = "COMPLIANT" if self.all_compliant else "NON-COMPLIANT"
        lines.append(f"**Status**: {status}")
        lines.append(f"**Pipelines scanned**: {self.total_pipelines}")
        lines.append("")

        if not self.results:
            lines.append("No CI/CD pipeline files detected.")
            lines.append("")
        else:
            lines.append("| Pipeline | Type | Compliant | Issues |")
            lines.append("|----------|------|-----------|--------|")

            for r in self.results:
                path = r.pipeline.path.as_posix()
                ptype = r.pipeline.pipeline_type.value
                compliant = "yes" if r.compliant else "**NO**"
                failed = [c.name for c in r.checks if not c.passed]
                issues = ", ".join(failed) if failed else "none"
                lines.append(f"| {path} | {ptype} | {compliant} | {issues} |")

            lines.append("")

        if self.warnings:
            lines.append("### Warnings")
            lines.append("")
            for w in self.warnings:
                lines.append(f"- {w}")
            lines.append("")

        return "\n".join(lines)


# GitHub Actions patterns that indicate risk gate presence.
_GITHUB_RISK_PATTERNS: list[str] = [
    "ai-eng gate risk-check",
    "risk-check",
    "pip-audit",
    "decision-store",
]

# Azure DevOps patterns that indicate risk gate presence.
_AZURE_RISK_PATTERNS: list[str] = [
    "ai-eng gate risk-check",
    "risk-check",
    "pip-audit",
    "decision-store",
]


def detect_pipelines(project_root: Path) -> list[PipelineFile]:
    """Detect CI/CD pipeline configuration files in a project.

    Looks for:
    - ``.github/workflows/*.yml`` — GitHub Actions
    - ``azure-pipelines.yml`` and ``.azure-pipelines/*.yml`` — Azure DevOps

    Args:
        project_root: Root directory of the project.

    Returns:
        List of detected pipeline files.
    """
    pipelines: list[PipelineFile] = []

    # GitHub Actions
    gh_dir = project_root / ".github" / "workflows"
    if gh_dir.is_dir():
        for f in sorted(gh_dir.glob("*.yml")):
            pipelines.append(
                PipelineFile(
                    path=f.relative_to(project_root),
                    pipeline_type=PipelineType.GITHUB_ACTIONS,
                )
            )
        for f in sorted(gh_dir.glob("*.yaml")):
            pipelines.append(
                PipelineFile(
                    path=f.relative_to(project_root),
                    pipeline_type=PipelineType.GITHUB_ACTIONS,
                )
            )

    # Azure DevOps — root file
    az_root = project_root / "azure-pipelines.yml"
    if az_root.is_file():
        pipelines.append(
            PipelineFile(
                path=az_root.relative_to(project_root),
                pipeline_type=PipelineType.AZURE_DEVOPS,
            )
        )

    # Azure DevOps — directory
    az_dir = project_root / ".azure-pipelines"
    if az_dir.is_dir():
        for f in sorted(az_dir.glob("*.yml")):
            pipelines.append(
                PipelineFile(
                    path=f.relative_to(project_root),
                    pipeline_type=PipelineType.AZURE_DEVOPS,
                )
            )
        for f in sorted(az_dir.glob("*.yaml")):
            pipelines.append(
                PipelineFile(
                    path=f.relative_to(project_root),
                    pipeline_type=PipelineType.AZURE_DEVOPS,
                )
            )

    return pipelines


def scan_pipeline(
    project_root: Path,
    pipeline: PipelineFile,
) -> PipelineComplianceResult:
    """Scan a single pipeline file for risk governance compliance.

    Checks:
    - File is readable and non-empty.
    - Contains risk gate step/task references.

    Args:
        project_root: Root directory of the project.
        pipeline: Pipeline file to check.

    Returns:
        PipelineComplianceResult with check details.
    """
    result = PipelineComplianceResult(pipeline=pipeline)
    full_path = project_root / pipeline.path

    # Readability check
    try:
        content = full_path.read_text(encoding="utf-8")
    except OSError as exc:
        result.checks.append(
            ComplianceCheck(
                name="readable",
                passed=False,
                detail=f"Cannot read: {exc}",
            )
        )
        return result

    if not content.strip():
        result.checks.append(
            ComplianceCheck(
                name="non-empty",
                passed=False,
                detail="Pipeline file is empty",
            )
        )
        return result

    result.checks.append(
        ComplianceCheck(
            name="readable",
            passed=True,
            detail="File is readable and non-empty",
        )
    )

    # Risk gate presence
    patterns = (
        _GITHUB_RISK_PATTERNS
        if pipeline.pipeline_type == PipelineType.GITHUB_ACTIONS
        else _AZURE_RISK_PATTERNS
    )
    content_lower = content.lower()
    found = any(p.lower() in content_lower for p in patterns)

    result.checks.append(
        ComplianceCheck(
            name="risk-gate-present",
            passed=found,
            detail=(
                "Risk gate step found"
                if found
                else "No risk gate step detected — add risk-check step to pipeline"
            ),
        )
    )

    return result


def scan_all_pipelines(project_root: Path) -> ComplianceReport:
    """Scan all detected pipelines for compliance.

    Args:
        project_root: Root directory of the project.

    Returns:
        ComplianceReport with all results.
    """
    report = ComplianceReport()
    pipelines = detect_pipelines(project_root)

    if not pipelines:
        report.warnings.append(
            "No CI/CD pipeline files detected. Add .github/workflows/ or azure-pipelines.yml."
        )
        return report

    for pipeline in pipelines:
        result = scan_pipeline(project_root, pipeline)
        report.results.append(result)

    return report
