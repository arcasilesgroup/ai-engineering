"""Category 5: Instruction File Consistency — all instruction files list identical skills/agents."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.validator._shared import (
    _REQUIRED_SUBSECTIONS,
    _SUBSECTION_PATTERN,
    CheckStatus,
    IntegrityCategory,
    IntegrityCheckResult,
    IntegrityReport,
    _extract_section,
    _instruction_files,
    _parse_agent_names,
    _parse_skill_names,
)


def _extract_listings(content: str) -> tuple[set[str], set[str]]:
    """Extract skill and agent sets from an instruction file."""
    skill_section = _extract_section(content, "Skills")
    agent_section = _extract_section(content, "Agents")
    skills = _parse_skill_names(skill_section)
    agents = _parse_agent_names(agent_section)
    return skills, agents


def _check_instruction_consistency(
    target: Path, report: IntegrityReport, **_kwargs: object
) -> None:
    """Verify all instruction files list identical skills and agents."""
    all_skills: dict[str, set[str]] = {}
    all_agents: dict[str, set[str]] = {}

    instruction_files = _instruction_files(target)
    for file_rel in instruction_files:
        file_path = target / file_rel
        if not file_path.exists():
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.INSTRUCTION_CONSISTENCY,
                    name=f"missing-{file_rel}",
                    status=CheckStatus.FAIL,
                    message=f"Instruction file not found: {file_rel}",
                    file_path=file_rel,
                )
            )
            continue
        content = file_path.read_text(encoding="utf-8", errors="replace")
        skills, agents = _extract_listings(content)
        all_skills[file_rel] = skills
        all_agents[file_rel] = agents

        # Check subsection structure
        subsections = set(_SUBSECTION_PATTERN.findall(content))
        missing_subs = _REQUIRED_SUBSECTIONS - subsections
        if missing_subs:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.INSTRUCTION_CONSISTENCY,
                    name=f"missing-subsections-{file_rel}",
                    status=CheckStatus.FAIL,
                    message=f"Missing subsections: {', '.join(sorted(missing_subs))}",
                    file_path=file_rel,
                )
            )

    if len(all_skills) < 2:
        return

    # Compare skills across all files
    reference_file = instruction_files[0]
    reference_skills = all_skills.get(reference_file, set())
    reference_agents = all_agents.get(reference_file, set())

    skills_consistent = True
    agents_consistent = True

    for file_rel, skills in all_skills.items():
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
                    status=CheckStatus.FAIL,
                    message=(f"Skills differ from {reference_file}: {'; '.join(details)}"),
                    file_path=file_rel,
                )
            )

    for file_rel, agents in all_agents.items():
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
                    status=CheckStatus.FAIL,
                    message=(f"Agents differ from {reference_file}: {'; '.join(details)}"),
                    file_path=file_rel,
                )
            )

    if skills_consistent:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.INSTRUCTION_CONSISTENCY,
                name="skills-consistent",
                status=CheckStatus.OK,
                message=f"All {len(all_skills)} files list identical skills",
            )
        )

    if agents_consistent:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.INSTRUCTION_CONSISTENCY,
                name="agents-consistent",
                status=CheckStatus.OK,
                message=f"All {len(all_agents)} files list identical agents",
            )
        )
