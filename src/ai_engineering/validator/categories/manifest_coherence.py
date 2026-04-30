"""Category 6: Manifest Coherence — ownership globs match filesystem, active spec valid."""

from __future__ import annotations

import re
from pathlib import Path

from ai_engineering.release.version_bump import detect_current_version
from ai_engineering.validator._shared import (
    IntegrityCategory,
    IntegrityCheckResult,
    IntegrityReport,
    IntegrityStatus,
)

_FRAMEWORK_VERSION_RE = re.compile(
    r'^framework_version:\s*"?(?P<version>[^"\n]+)"?\s*$',
    flags=re.MULTILINE,
)


def _read_framework_version(manifest_path: Path) -> str | None:
    if not manifest_path.is_file():
        return None

    match = _FRAMEWORK_VERSION_RE.search(manifest_path.read_text(encoding="utf-8"))
    if match is None:
        return None
    return match.group("version").strip()


def _check_source_repo_framework_versions(target: Path, report: IntegrityReport) -> None:
    """Verify bundled framework manifests match the package version in source checkouts."""
    template_manifest_path = (
        target / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "manifest.yml"
    )
    if not template_manifest_path.is_file():
        return

    try:
        package_version = detect_current_version(target)
    except (FileNotFoundError, ValueError) as exc:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="framework-version-source",
                status=IntegrityStatus.FAIL,
                message=f"Unable to read framework package version: {exc}",
                file_path="pyproject.toml",
            )
        )
        return

    manifests = [
        (target / ".ai-engineering" / "manifest.yml", "framework-version-root"),
        (template_manifest_path, "framework-version-template"),
    ]
    for file_path, check_name in manifests:
        framework_version = _read_framework_version(file_path)
        relative_path = str(file_path.relative_to(target))
        if framework_version is None:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MANIFEST_COHERENCE,
                    name=check_name,
                    status=IntegrityStatus.FAIL,
                    message=f"framework_version not found in {relative_path}",
                    file_path=relative_path,
                )
            )
            continue

        if framework_version != package_version:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MANIFEST_COHERENCE,
                    name=check_name,
                    status=IntegrityStatus.FAIL,
                    message=(
                        f"{relative_path} framework_version is {framework_version}, "
                        f"expected {package_version} from pyproject.toml"
                    ),
                    file_path=relative_path,
                )
            )
            continue

        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name=check_name,
                status=IntegrityStatus.OK,
                message=f"{relative_path} framework_version matches pyproject.toml",
            )
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
    # they have moved to IDE-specific directories (.claude/, .codex/, .gemini/).
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

    _check_source_repo_framework_versions(target, report)

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
