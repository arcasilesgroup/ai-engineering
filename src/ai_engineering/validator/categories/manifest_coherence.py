"""Category 6: Manifest Coherence — ownership globs match filesystem, active spec valid."""

from __future__ import annotations

import re
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
    ownership_dirs = [
        ("standards/framework", "framework_managed"),
        ("skills", "framework_managed"),
        ("agents", "framework_managed"),
        ("context", "project_managed"),
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

    # Verify active spec pointer
    active_path = ai_dir / "context" / "specs" / "_active.md"
    if active_path.exists():
        content = active_path.read_text(encoding="utf-8", errors="replace")
        # Extract active spec from frontmatter
        active_match = re.search(r'^active:\s*"([^"]+)"', content, re.MULTILINE)
        if active_match:
            active_spec = active_match.group(1)
            if active_spec == "none":
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.MANIFEST_COHERENCE,
                        name="active-spec",
                        status=IntegrityStatus.OK,
                        message="No active spec (idle)",
                    )
                )
            elif not (ai_dir / "context" / "specs" / active_spec).is_dir():
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.MANIFEST_COHERENCE,
                        name="active-spec-dir",
                        status=IntegrityStatus.FAIL,
                        message=f"Active spec directory not found: {active_spec}",
                    )
                )
            elif not (ai_dir / "context" / "specs" / active_spec / "spec.md").exists():
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.MANIFEST_COHERENCE,
                        name="active-spec-file",
                        status=IntegrityStatus.FAIL,
                        message=f"Active spec missing spec.md: {active_spec}",
                    )
                )
            else:
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.MANIFEST_COHERENCE,
                        name="active-spec",
                        status=IntegrityStatus.OK,
                        message=f"Active spec valid: {active_spec}",
                    )
                )
    else:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="active-spec-pointer",
                status=IntegrityStatus.WARN,
                message="_active.md not found",
            )
        )
