"""Category 6: Manifest Coherence — ownership globs match filesystem, active spec valid."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.validator._shared import (
    IntegrityCategory,
    IntegrityCheckResult,
    IntegrityReport,
    IntegrityStatus,
)


def _check_manifest_coherence(target: Path, report: IntegrityReport, **_kwargs: object) -> None:
    """Verify manifest ownership globs and active spec pointer."""
    ai_dir = target / ".ai-engineering"
    manifest_path = ai_dir / "manifest.yml"

    if not manifest_path.exists():
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="manifest-missing",
                status=IntegrityStatus.FAIL,
                message="manifest.yml not found",
            )
        )
        return

    # Check ownership directory structure exists
    # Note: skills/ and agents/ no longer live under .ai-engineering/ —
    # they have moved to IDE-specific directories (.claude/, .agents/).
    ownership_dirs = [
        ("contexts", "framework_managed"),
        ("state", "system_managed"),
    ]

    for dir_rel, category in ownership_dirs:
        dir_path = ai_dir / dir_rel
        if not dir_path.is_dir():
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MANIFEST_COHERENCE,
                    name=f"missing-dir-{dir_rel}",
                    status=IntegrityStatus.FAIL,
                    message=f"{category} directory not found: {dir_rel}",
                    file_path=f".ai-engineering/{dir_rel}",
                )
            )
        else:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MANIFEST_COHERENCE,
                    name=f"dir-{dir_rel}",
                    status=IntegrityStatus.OK,
                    message=f"{category} directory exists: {dir_rel}",
                )
            )

    # Verify Working Buffer spec file
    spec_path = ai_dir / "specs" / "spec.md"
    if spec_path.exists():
        content = spec_path.read_text(encoding="utf-8", errors="replace")
        if content.strip().startswith("# No active spec"):
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MANIFEST_COHERENCE,
                    name="active-spec",
                    status=IntegrityStatus.OK,
                    message="No active spec (idle)",
                )
            )
        else:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MANIFEST_COHERENCE,
                    name="active-spec",
                    status=IntegrityStatus.OK,
                    message="Active spec present in specs/spec.md",
                )
            )
    else:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="active-spec-pointer",
                status=IntegrityStatus.WARN,
                message="specs/spec.md not found",
            )
        )
