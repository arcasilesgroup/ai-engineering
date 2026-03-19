"""Category 1: File Existence — verify all internal path references resolve."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.validator._shared import (
    _KNOWN_OPTIONAL_PATHS,
    _PATH_REF_PATTERN,
    FileCache,
    IntegrityCategory,
    IntegrityCheckResult,
    IntegrityReport,
    IntegrityStatus,
)


def _check_file_existence(
    target: Path, report: IntegrityReport, *, cache: FileCache | None = None
) -> None:
    """Verify all internal path references resolve to existing files."""
    ai_dir = target / ".ai-engineering"
    if not ai_dir.is_dir():
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.FILE_EXISTENCE,
                name="governance-directory",
                status=IntegrityStatus.FAIL,
                message=".ai-engineering/ directory not found",
            )
        )
        return

    # Collect closed spec directories (have done.md = historical archive)
    specs_dir_path = ai_dir / "specs"
    closed_specs: set[Path] = set()
    if specs_dir_path.is_dir():
        for spec_dir in specs_dir_path.iterdir():
            if spec_dir.is_dir() and (spec_dir / "done.md").exists():
                closed_specs.add(spec_dir)
        # The archive/ directory contains moved closed specs — always excluded
        archive_dir = specs_dir_path / "archive"
        if archive_dir.is_dir():
            closed_specs.add(archive_dir)

    # Scan all .md files for internal references (skip closed spec archives)
    broken_refs: list[tuple[str, str]] = []
    if cache:
        md_files = [p for p in cache.rglob(ai_dir, "*.md") if p.is_file()]
    else:
        md_files = sorted(ai_dir.rglob("*.md"))
    for md_file in md_files:
        # Skip files in closed spec directories — historical archives with old paths
        if any(md_file.is_relative_to(s) for s in closed_specs):
            continue
        content = md_file.read_text(encoding="utf-8", errors="replace")
        for match in _PATH_REF_PATTERN.finditer(content):
            ref_path = match.group(1) if match.group(1) else match.group(0)
            # Clean up backticks and leading dots
            ref_path = ref_path.strip("`").lstrip(".")
            if ref_path.startswith("ai-engineering/"):
                ref_path = ref_path[len("ai-engineering/") :]
            # Skip template placeholders like <name>, <stack>, {SKILL_NAME}
            if "<" in ref_path and ">" in ref_path:
                continue
            if "{" in ref_path and "}" in ref_path:
                continue
            # Skip IDE directory references (e.g. .agents/agents/, .agents/skills/)
            # These are matched by the regex but are not governance paths
            if ref_path.startswith(("agents/agents/", "agents/skills/")):
                continue
            # Skip known-optional governance paths (exist only conditionally)
            if ref_path in _KNOWN_OPTIONAL_PATHS:
                continue
            full_path = ai_dir / ref_path
            if not full_path.exists():
                # Fallback: skills/ and agents/ live in IDE-adapted mirrors
                # (.claude/, .agents/, .github/), not in .ai-engineering/.
                # IDE mirrors use ai- prefix (e.g. agents/build.md → .claude/agents/ai-build.md,
                # skills/test/SKILL.md → .claude/skills/ai-test/SKILL.md).
                fallback_roots = [
                    target / ".claude",
                    target / ".agents",
                    target / ".github",
                ]
                # Build IDE-adapted path variant (ai- prefix)
                ide_ref = ref_path
                if ref_path.startswith("agents/"):
                    name = ref_path.removeprefix("agents/")
                    ide_ref = f"agents/ai-{name}"
                elif ref_path.startswith("skills/"):
                    parts = ref_path.removeprefix("skills/").split("/", 1)
                    if len(parts) == 2:
                        ide_ref = f"skills/ai-{parts[0]}/{parts[1]}"
                candidates = [ref_path, ide_ref]
                if any((root / c).exists() for root in fallback_roots for c in candidates):
                    continue
                rel_source = md_file.relative_to(target).as_posix()
                broken_refs.append((rel_source, ref_path))

    if broken_refs:
        for source, ref in broken_refs:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="broken-reference",
                    status=IntegrityStatus.FAIL,
                    message=f"Reference to '{ref}' not found",
                    file_path=source,
                )
            )
    else:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.FILE_EXISTENCE,
                name="path-references",
                status=IntegrityStatus.OK,
                message="All internal path references resolve",
            )
        )

    # Verify spec directory completeness
    specs_dir = ai_dir / "specs"
    if specs_dir.is_dir():
        for spec_dir in sorted(specs_dir.iterdir()):
            if not spec_dir.is_dir() or spec_dir.name.startswith("_"):
                continue
            # Skip archive directory — historical specs with known stale paths
            if spec_dir.name == "archive":
                continue
            required = ["spec.md", "plan.md", "tasks.md"]
            missing = [f for f in required if not (spec_dir / f).exists()]
            if missing:
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.FILE_EXISTENCE,
                        name=f"spec-{spec_dir.name}",
                        status=IntegrityStatus.FAIL,
                        message=f"Missing files: {', '.join(missing)}",
                        file_path=spec_dir.relative_to(target).as_posix(),
                    )
                )
            else:
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.FILE_EXISTENCE,
                        name=f"spec-{spec_dir.name}",
                        status=IntegrityStatus.OK,
                        message="Spec directory complete",
                        file_path=spec_dir.relative_to(target).as_posix(),
                    )
                )
