"""Category 5: Instruction File Consistency — all instruction files list identical skills/agents."""

from __future__ import annotations

import re
from pathlib import Path

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.validator._shared import (
    _REQUIRED_SUBSECTIONS,
    _SUBSECTION_PATTERN,
    IntegrityCategory,
    IntegrityCheckResult,
    IntegrityReport,
    IntegrityStatus,
    _extract_section,
    _instruction_files,
    _parse_agent_names,
    _parse_skill_names,
)

# Pattern to extract counts from pointer format: "Skills (35)" or "Agents (7)"
_POINTER_SKILL_RE = re.compile(r"Skills\s*\((\d+)\)", re.IGNORECASE)
_POINTER_AGENT_RE = re.compile(r"Agents\s*\((\d+)\)", re.IGNORECASE)


def _extract_listings(content: str) -> tuple[set[str], set[str]]:
    """Extract skill and agent sets from an instruction file.

    Looks for ## Skills and ## Agents sections with detailed listings.
    Also checks #### Skills and #### Agents subsections (product-contract format).
    """
    # Try ## Skills / ## Agents first
    skill_section = _extract_section(content, "Skills")
    agent_section = _extract_section(content, "Agents")
    skills = _parse_skill_names(skill_section)
    agents = _parse_agent_names(agent_section)

    # If not found at ## level, try #### level (product-contract.md format)
    if not skills:
        skills = _parse_skill_names_from_subsection(content, "Skills")
    if not agents:
        agents = _parse_agent_names_from_subsection(content, "Agents")

    return skills, agents


def _extract_subsection(content: str, heading: str) -> str:
    """Extract markdown content under a level-4 heading until next same-or-higher heading."""
    lines = content.splitlines()
    heading_prefix = f"#### {heading}".lower()
    start: int | None = None

    for index, line in enumerate(lines):
        if line.strip().lower().startswith(heading_prefix):
            start = index + 1
            break

    if start is None:
        return ""

    end = len(lines)
    for index in range(start, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith(("#### ", "### ", "## ")):
            end = index
            break

    return "\n".join(lines[start:end])


def _parse_skill_names_from_subsection(content: str, heading: str) -> set[str]:
    """Parse skill names from a #### subsection."""
    section = _extract_subsection(content, heading)
    return _parse_skill_names(section)


def _parse_agent_names_from_subsection(content: str, heading: str) -> set[str]:
    """Parse agent names from a #### subsection."""
    section = _extract_subsection(content, heading)
    return _parse_agent_names(section)


def _get_pointer_counts(content: str) -> tuple[int | None, int | None]:
    """Extract skill/agent counts from pointer format: 'Skills (35)' / 'Agents (7)'."""
    skill_match = _POINTER_SKILL_RE.search(content)
    agent_match = _POINTER_AGENT_RE.search(content)
    skill_count = int(skill_match.group(1)) if skill_match else None
    agent_count = int(agent_match.group(1)) if agent_match else None
    return skill_count, agent_count


def _check_instruction_consistency(
    target: Path, report: IntegrityReport, **_kwargs: object
) -> None:
    """Verify all instruction files list identical skills and agents.

    Files can use either detailed listings (tables/bullets) or pointer format
    ('Skills (35)'). Pointer-format files are validated against the canonical
    source: manifest.yml.
    """
    # Detailed listings per file
    detailed_skills: dict[str, set[str]] = {}
    detailed_agents: dict[str, set[str]] = {}
    # Pointer counts per file
    pointer_skills: dict[str, int] = {}
    pointer_agents: dict[str, int] = {}

    instruction_files = _instruction_files(target)
    for file_rel in instruction_files:
        file_path = target / file_rel
        if not file_path.exists():
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.INSTRUCTION_CONSISTENCY,
                    name=f"missing-{file_rel}",
                    status=IntegrityStatus.FAIL,
                    message=f"Instruction file not found: {file_rel}",
                    file_path=file_rel,
                )
            )
            continue
        content = file_path.read_text(encoding="utf-8", errors="replace")
        skills, agents = _extract_listings(content)

        if skills or agents:
            detailed_skills[file_rel] = skills
            detailed_agents[file_rel] = agents
        else:
            # Try pointer format
            s_count, a_count = _get_pointer_counts(content)
            if s_count is not None:
                pointer_skills[file_rel] = s_count
            if a_count is not None:
                pointer_agents[file_rel] = a_count

        # Check subsection structure
        subsections = set(_SUBSECTION_PATTERN.findall(content))
        missing_subs = _REQUIRED_SUBSECTIONS - subsections
        if missing_subs:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.INSTRUCTION_CONSISTENCY,
                    name=f"missing-subsections-{file_rel}",
                    status=IntegrityStatus.FAIL,
                    message=f"Missing subsections: {', '.join(sorted(missing_subs))}",
                    file_path=file_rel,
                )
            )

    # Get canonical listings from manifest.yml (source of truth)
    cfg = load_manifest_config(target)
    canonical_skills: set[str] = set(cfg.skills.registry.keys())
    canonical_agents: set[str] = set(cfg.agents.names)

    # Compare files with detailed listings against each other
    if len(detailed_skills) >= 2:
        reference_file = next(iter(detailed_skills))
        reference_skills = detailed_skills[reference_file]
        reference_agents = detailed_agents.get(reference_file, set())

        skills_consistent = True
        agents_consistent = True

        for file_rel, skills in detailed_skills.items():
            if file_rel == reference_file:
                continue
            if skills != reference_skills:
                skills_consistent = False
                only_in_ref = reference_skills - skills
                only_in_file = skills - reference_skills
                details: list[str] = []
                if only_in_ref:
                    details.append(f"missing: {', '.join(sorted(only_in_ref))}")
                if only_in_file:
                    details.append(f"extra: {', '.join(sorted(only_in_file))}")
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.INSTRUCTION_CONSISTENCY,
                        name=f"skills-differ-{file_rel}",
                        status=IntegrityStatus.FAIL,
                        message=(f"Skills differ from {reference_file}: {'; '.join(details)}"),
                        file_path=file_rel,
                    )
                )

        for file_rel, agents in detailed_agents.items():
            if file_rel == reference_file:
                continue
            if agents != reference_agents:
                agents_consistent = False
                only_in_ref = reference_agents - agents
                only_in_file = agents - reference_agents
                details = []
                if only_in_ref:
                    details.append(f"missing: {', '.join(sorted(only_in_ref))}")
                if only_in_file:
                    details.append(f"extra: {', '.join(sorted(only_in_file))}")
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.INSTRUCTION_CONSISTENCY,
                        name=f"agents-differ-{file_rel}",
                        status=IntegrityStatus.FAIL,
                        message=(f"Agents differ from {reference_file}: {'; '.join(details)}"),
                        file_path=file_rel,
                    )
                )

        if skills_consistent:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.INSTRUCTION_CONSISTENCY,
                    name="skills-consistent",
                    status=IntegrityStatus.OK,
                    message=f"All {len(detailed_skills)} detailed files list identical skills",
                )
            )

        if agents_consistent:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.INSTRUCTION_CONSISTENCY,
                    name="agents-consistent",
                    status=IntegrityStatus.OK,
                    message=f"All {len(detailed_agents)} detailed files list identical agents",
                )
            )

    # Validate pointer-format files against canonical counts
    if canonical_skills:
        for file_rel, count in pointer_skills.items():
            if count != len(canonical_skills):
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.INSTRUCTION_CONSISTENCY,
                        name=f"pointer-skills-mismatch-{file_rel}",
                        status=IntegrityStatus.FAIL,
                        message=(
                            f"{file_rel} says {count} skills, "
                            f"manifest.yml lists {len(canonical_skills)}"
                        ),
                        file_path=file_rel,
                    )
                )

    if canonical_agents:
        for file_rel, count in pointer_agents.items():
            if count != len(canonical_agents):
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.INSTRUCTION_CONSISTENCY,
                        name=f"pointer-agents-mismatch-{file_rel}",
                        status=IntegrityStatus.FAIL,
                        message=(
                            f"{file_rel} says {count} agents, "
                            f"manifest.yml lists {len(canonical_agents)}"
                        ),
                        file_path=file_rel,
                    )
                )

    # If all pointer files match, report success
    all_pointer_files = set(pointer_skills.keys()) | set(pointer_agents.keys())
    if all_pointer_files and not any(
        c.status == IntegrityStatus.FAIL and c.name.startswith("pointer-") for c in report.checks
    ):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.INSTRUCTION_CONSISTENCY,
                name="pointer-format-consistent",
                status=IntegrityStatus.OK,
                message=(
                    f"{len(all_pointer_files)} pointer-format files match "
                    f"manifest.yml canonical counts"
                ),
            )
        )
