"""Governance CLI commands.

Provides consistency validation between IDE instruction files and the
canonical governance source document.

- ``ai-eng governance diff`` — compare IDE files against GOVERNANCE_SOURCE.md.
- ``ai-eng governance sync`` — report drift and suggest corrections.
"""

from __future__ import annotations

import re
from pathlib import Path

import typer


def _project_root() -> Path:
    """Walk up from cwd to find the project root."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".ai-engineering").is_dir():
            return parent
    return cwd


_CANONICAL_SECTIONS = {
    "session_start": "## Session Start Protocol",
    "prohibitions": "## Absolute Prohibitions",
    "skills": "## Skills",
    "agents": "## Agents",
    "quick_reference": "## Quick Reference",
}

_IDE_FILES = [
    "CLAUDE.md",
    "AGENTS.md",
    "GEMINI.md",
    ".github/copilot-instructions.md",
]


def _extract_section(text: str, heading: str) -> str | None:
    """Extract a markdown section by heading (until next ## or end)."""
    pattern = re.escape(heading) + r"\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _check_key_phrases(source_text: str, ide_text: str) -> list[str]:
    """Check that key governance phrases from source appear in IDE file."""
    drifts: list[str] = []

    key_phrases = [
        "NEVER",
        "--no-verify",
        "decision-store.json",
        "ruff, gitleaks, pytest, ty",
        "_active.md",
    ]

    for phrase in key_phrases:
        source_has = phrase.lower() in source_text.lower()
        ide_has = phrase.lower() in ide_text.lower()
        if source_has and not ide_has:
            drifts.append(f"Missing key phrase: '{phrase}'")

    return drifts


def _count_skills_in_text(text: str) -> int:
    """Count skill references in text by looking for known skill names."""
    skill_names = [
        "accessibility",
        "api",
        "architecture",
        "changelog",
        "cleanup",
        "cli",
        "code",
        "commit",
        "contract",
        "dashboard",
        "debug",
        "discover",
        "dispatch",
        "document",
        "evolve",
        "explain",
        "gap",
        "governance",
        "guard",
        "guide",
        "infra",
        "lifecycle",
        "migrate",
        "onboard",
        "ops",
        "performance",
        "pipeline",
        "plan",
        "pr",
        "quality",
        "refactor",
        "release",
        "risk",
        "schema",
        "security",
        "simplify",
        "spec",
        "standards",
        "test",
        "triage",
    ]
    count = 0
    for name in skill_names:
        if re.search(rf"\b{re.escape(name)}\b", text):
            count += 1
    return count


def governance_diff() -> None:
    """Compare IDE instruction files against GOVERNANCE_SOURCE.md."""
    root = _project_root()
    source_path = root / ".ai-engineering" / "GOVERNANCE_SOURCE.md"

    if not source_path.exists():
        typer.echo("GOVERNANCE_SOURCE.md not found.", err=True)
        raise typer.Exit(code=1)

    source_text = source_path.read_text(encoding="utf-8")
    total_drift = 0

    for ide_file in _IDE_FILES:
        ide_path = root / ide_file
        if not ide_path.exists():
            typer.echo(f"  SKIP {ide_file} (not found)")
            continue

        ide_text = ide_path.read_text(encoding="utf-8")
        drifts = _check_key_phrases(source_text, ide_text)

        # Check section presence
        for _section_key, heading in _CANONICAL_SECTIONS.items():
            source_section = _extract_section(source_text, heading)
            if source_section:
                # Check if the IDE file has a similar section
                heading_word = heading.replace("## ", "")
                if heading_word.lower() not in ide_text.lower():
                    drifts.append(f"Missing section: '{heading_word}'")

        if drifts:
            typer.echo(f"  DRIFT {ide_file} ({len(drifts)} issues)")
            for drift in drifts:
                typer.echo(f"    - {drift}")
            total_drift += len(drifts)
        else:
            typer.echo(f"  OK    {ide_file}")

    typer.echo(f"\nTotal drift issues: {total_drift}")
    if total_drift > 0:
        typer.echo("Run governance review to align IDE files with GOVERNANCE_SOURCE.md.")
        raise typer.Exit(code=1)


def governance_sync() -> None:
    """Validate governance consistency and report sync status."""
    root = _project_root()
    source_path = root / ".ai-engineering" / "GOVERNANCE_SOURCE.md"

    if not source_path.exists():
        typer.echo("GOVERNANCE_SOURCE.md not found.", err=True)
        raise typer.Exit(code=1)

    source_text = source_path.read_text(encoding="utf-8")

    # Validate source has all required sections
    typer.echo("Governance source validation:")
    missing_sections: list[str] = []
    for section_key, heading in _CANONICAL_SECTIONS.items():
        section = _extract_section(source_text, heading)
        if section:
            typer.echo(f"  OK    {heading}")
        else:
            typer.echo(f"  MISS  {heading}")
            missing_sections.append(section_key)

    if missing_sections:
        typer.echo(f"\n{len(missing_sections)} missing sections in source.")
        raise typer.Exit(code=1)

    # Count skills and agents in source
    source_skills = _count_skills_in_text(source_text)
    typer.echo(f"\nSkills referenced in source: {source_skills}/40")

    # Check IDE files exist
    typer.echo("\nIDE file status:")
    for ide_file in _IDE_FILES:
        ide_path = root / ide_file
        if ide_path.exists():
            lines = len(ide_path.read_text(encoding="utf-8").splitlines())
            typer.echo(f"  OK    {ide_file} ({lines} lines)")
        else:
            typer.echo(f"  MISS  {ide_file}")

    # Run diff
    typer.echo("\nDrift check:")
    governance_diff()
