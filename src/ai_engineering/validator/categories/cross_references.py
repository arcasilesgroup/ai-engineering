"""Category 4: Cross-Reference Integrity — bidirectional reference validation."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.validator._shared import (
    _REF_LINE,
    _REFERENCES_SECTION,
    FileCache,
    IntegrityCategory,
    IntegrityCheckResult,
    IntegrityReport,
    IntegrityStatus,
)


def _parse_references(content: str) -> list[str]:
    """Extract file paths from the ## References section of a governance file."""
    section_match = _REFERENCES_SECTION.search(content)
    if not section_match:
        return []
    section = section_match.group(1)
    return _REF_LINE.findall(section)


def _check_cross_references(
    target: Path, report: IntegrityReport, *, cache: FileCache | None = None
) -> None:
    """Verify bidirectional cross-references in skills and agents."""
    # Skills and agents now live in IDE-specific directories
    ide_dirs = [
        target / ".claude" / "skills",
        target / ".claude" / "agents",
        target / ".agents" / "skills",
        target / ".agents" / "agents",
    ]

    # Build reference map: file -> list of referenced paths
    ref_map: dict[str, list[str]] = {}

    for base in ide_dirs:
        if not base.is_dir():
            continue
        if cache:
            md_files = [p for p in cache.rglob(base, "*.md") if p.is_file()]
        else:
            md_files = sorted(base.rglob("*.md"))
        for md_file in md_files:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            refs = _parse_references(content)
            rel_key = md_file.relative_to(target).as_posix()
            ref_map[rel_key] = refs

    # Validate each reference exists
    broken = 0
    for source, refs in ref_map.items():
        for ref in refs:
            ref_clean = ref.strip()
            if not ref_clean:
                continue
            ref_path = target / ref_clean
            # References to standards/context/state are relative to .ai-engineering/
            ai_eng_path = target / ".ai-engineering" / ref_clean
            # Also check in canonical templates (for framework repo)
            tpl_path = (
                target / "src" / "ai_engineering" / "templates" / ".ai-engineering" / ref_clean
            )
            if not (ref_path.exists() or ai_eng_path.exists() or tpl_path.exists()):
                broken += 1
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.CROSS_REFERENCE,
                        name=f"broken-ref-{source}",
                        status=IntegrityStatus.FAIL,
                        message=f"'{source}' references non-existent '{ref_clean}'",
                        file_path=source,
                    )
                )

    if broken == 0:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.CROSS_REFERENCE,
                name="all-references-valid",
                status=IntegrityStatus.OK,
                message=f"All cross-references valid ({len(ref_map)} files checked)",
            )
        )
