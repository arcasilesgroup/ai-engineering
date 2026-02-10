"""Tests for ai_engineering.pipeline.compliance and injector.

Covers:
- detect_pipelines: GitHub Actions and Azure DevOps detection.
- scan_pipeline: risk gate presence checking.
- scan_all_pipelines: aggregated compliance report.
- ComplianceReport: Markdown rendering.
- generate_github_step / generate_azure_task: snippet generation.
- suggest_injection: per-pipeline suggestion.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.pipeline.compliance import (
    ComplianceReport,
    PipelineFile,
    PipelineType,
    detect_pipelines,
    scan_all_pipelines,
    scan_pipeline,
)
from ai_engineering.pipeline.injector import (
    generate_azure_task,
    generate_github_step,
    suggest_injection,
)

# ── detect_pipelines ────────────────────────────────────────────────────


class TestDetectPipelines:
    """Tests for pipeline file detection."""

    def test_detects_github_actions(self, tmp_path: Path) -> None:
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text("name: CI")
        (wf_dir / "release.yml").write_text("name: Release")

        pipelines = detect_pipelines(tmp_path)
        assert len(pipelines) == 2
        assert all(p.pipeline_type == PipelineType.GITHUB_ACTIONS for p in pipelines)

    def test_detects_azure_devops_root(self, tmp_path: Path) -> None:
        (tmp_path / "azure-pipelines.yml").write_text("trigger: main")

        pipelines = detect_pipelines(tmp_path)
        assert len(pipelines) == 1
        assert pipelines[0].pipeline_type == PipelineType.AZURE_DEVOPS

    def test_detects_azure_devops_dir(self, tmp_path: Path) -> None:
        az_dir = tmp_path / ".azure-pipelines"
        az_dir.mkdir()
        (az_dir / "build.yml").write_text("steps:")

        pipelines = detect_pipelines(tmp_path)
        assert len(pipelines) == 1
        assert pipelines[0].pipeline_type == PipelineType.AZURE_DEVOPS

    def test_detects_both_platforms(self, tmp_path: Path) -> None:
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI")
        (tmp_path / "azure-pipelines.yml").write_text("trigger: main")

        pipelines = detect_pipelines(tmp_path)
        types = {p.pipeline_type for p in pipelines}
        assert PipelineType.GITHUB_ACTIONS in types
        assert PipelineType.AZURE_DEVOPS in types

    def test_empty_when_no_pipelines(self, tmp_path: Path) -> None:
        pipelines = detect_pipelines(tmp_path)
        assert pipelines == []

    def test_detects_yaml_extension(self, tmp_path: Path) -> None:
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yaml").write_text("name: CI")

        pipelines = detect_pipelines(tmp_path)
        assert len(pipelines) == 1


# ── scan_pipeline ───────────────────────────────────────────────────────


class TestScanPipeline:
    """Tests for individual pipeline compliance scanning."""

    def test_compliant_with_risk_gate(self, tmp_path: Path) -> None:
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text(
            "name: CI\njobs:\n  check:\n    steps:\n      - run: ai-eng gate risk-check\n"
        )
        pipeline = PipelineFile(
            path=Path(".github/workflows/ci.yml"),
            pipeline_type=PipelineType.GITHUB_ACTIONS,
        )
        result = scan_pipeline(tmp_path, pipeline)
        assert result.compliant

    def test_non_compliant_without_risk_gate(self, tmp_path: Path) -> None:
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text("name: CI\njobs:\n  build:\n    steps: []\n")
        pipeline = PipelineFile(
            path=Path(".github/workflows/ci.yml"),
            pipeline_type=PipelineType.GITHUB_ACTIONS,
        )
        result = scan_pipeline(tmp_path, pipeline)
        assert not result.compliant

    def test_unreadable_file(self, tmp_path: Path) -> None:
        pipeline = PipelineFile(
            path=Path("nonexistent.yml"),
            pipeline_type=PipelineType.GITHUB_ACTIONS,
        )
        result = scan_pipeline(tmp_path, pipeline)
        assert not result.compliant

    def test_empty_file(self, tmp_path: Path) -> None:
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "empty.yml").write_text("")
        pipeline = PipelineFile(
            path=Path(".github/workflows/empty.yml"),
            pipeline_type=PipelineType.GITHUB_ACTIONS,
        )
        result = scan_pipeline(tmp_path, pipeline)
        assert not result.compliant


# ── scan_all_pipelines ──────────────────────────────────────────────────


class TestScanAllPipelines:
    """Tests for aggregated compliance scanning."""

    def test_reports_warning_when_no_pipelines(self, tmp_path: Path) -> None:
        report = scan_all_pipelines(tmp_path)
        assert not report.results
        assert len(report.warnings) > 0

    def test_reports_all_pipelines(self, tmp_path: Path) -> None:
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text("name: CI\nsteps:\n  - run: risk-check\n")
        (wf_dir / "deploy.yml").write_text("name: Deploy\nsteps: []\n")

        report = scan_all_pipelines(tmp_path)
        assert report.total_pipelines == 2


# ── ComplianceReport ────────────────────────────────────────────────────


class TestComplianceReport:
    """Tests for ComplianceReport Markdown rendering."""

    def test_all_compliant_status(self) -> None:
        report = ComplianceReport()
        assert report.all_compliant  # No results = vacuously true

    def test_to_markdown_includes_status(self) -> None:
        report = ComplianceReport()
        md = report.to_markdown()
        assert "Pipeline Compliance Report" in md

    def test_to_markdown_includes_warnings(self) -> None:
        report = ComplianceReport(warnings=["No pipeline files detected."])
        md = report.to_markdown()
        assert "Warnings" in md


# ── Snippet generation ──────────────────────────────────────────────────


class TestSnippetGeneration:
    """Tests for pipeline snippet generators."""

    def test_github_step_contains_risk_check(self) -> None:
        snippet = generate_github_step()
        assert "risk-check" in snippet
        assert "ai-eng" in snippet

    def test_azure_task_contains_risk_check(self) -> None:
        snippet = generate_azure_task()
        assert "risk-check" in snippet
        assert "ai-eng" in snippet


# ── suggest_injection ───────────────────────────────────────────────────


class TestSuggestInjection:
    """Tests for pipeline injection suggestions."""

    def test_github_suggestion(self) -> None:
        pipeline = PipelineFile(
            path=Path(".github/workflows/ci.yml"),
            pipeline_type=PipelineType.GITHUB_ACTIONS,
        )
        suggestion = suggest_injection(pipeline)
        assert "ci.yml" in suggestion
        assert "risk-check" in suggestion

    def test_azure_suggestion(self) -> None:
        pipeline = PipelineFile(
            path=Path("azure-pipelines.yml"),
            pipeline_type=PipelineType.AZURE_DEVOPS,
        )
        suggestion = suggest_injection(pipeline)
        assert "azure-pipelines.yml" in suggestion
        assert "risk-check" in suggestion
