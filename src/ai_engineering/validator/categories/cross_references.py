"""Category 4: Cross-Reference Integrity — bidirectional reference validation."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.validator._shared import (
    _REF_LINE,
    _REFERENCES_SECTION,
    CheckStatus,
    FileCache,
    IntegrityCategory,
    IntegrityCheckResult,
    IntegrityReport,
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
    ai_dir = target / ".ai-engineering"
    if not ai_dir.is_dir():
        return

    # Build reference map: file -> list of referenced paths
    ref_map: dict[str, list[str]] = {}

    for subdir in ["skills", "agents"]:
        base = ai_dir / subdir
        if not base.is_dir():
            continue
        if cache:
            md_files = [p for p in cache.rglob(base, "*.md") if p.is_file()]
        else:
            md_files = sorted(base.rglob("*.md"))
        for md_file in md_files:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            refs = _parse_references(content)
            rel_key = md_file.relative_to(ai_dir).as_posix()
            ref_map[rel_key] = refs

    # Validate each reference exists
    broken = 0
    for source, refs in ref_map.items():
        for ref in refs:
            ref_clean = ref.strip()
            if not ref_clean:
                continue
            ref_path = ai_dir / ref_clean
            if not ref_path.exists():
                broken += 1
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.CROSS_REFERENCE,
                        name=f"broken-ref-{source}",
                        status=CheckStatus.FAIL,
                        message=f"'{source}' references non-existent '{ref_clean}'",
                        file_path=source,
                    )
                )

    if broken == 0:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.CROSS_REFERENCE,
                name="all-references-valid",
                status=CheckStatus.OK,
                message=f"All cross-references valid ({len(ref_map)} files checked)",
            )
        )
