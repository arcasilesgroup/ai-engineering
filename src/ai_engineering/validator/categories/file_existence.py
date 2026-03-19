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

    # Working Buffer model: specs are transient files, not directories
    # No closed-spec directory exclusion needed

    # Scan all .md files for internal references
    broken_refs: list[tuple[str, str]] = []
    if cache:
        md_files = [p for p in cache.rglob(ai_dir, "*.md") if p.is_file()]
    else:
        md_files = sorted(ai_dir.rglob("*.md"))
    for md_file in md_files:
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

    # Verify Working Buffer spec files exist
    specs_dir = ai_dir / "specs"
    if specs_dir.is_dir():
        required_spec_files = ["spec.md", "plan.md"]
        missing_spec = [f for f in required_spec_files if not (specs_dir / f).exists()]
        if missing_spec:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="spec-buffer",
                    status=IntegrityStatus.FAIL,
                    message=f"Missing spec files: {', '.join(missing_spec)}",
                    file_path="specs/",
                )
            )
        else:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="spec-buffer",
                    status=IntegrityStatus.OK,
                    message="Spec buffer files present (spec.md, plan.md)",
                    file_path="specs/",
                )
            )
