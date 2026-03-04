"""Category 3: Counter Accuracy — skill/agent counts match across files."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.validator._shared import (
    IntegrityCategory,
    IntegrityCheckResult,
    IntegrityReport,
    IntegrityStatus,
    _instruction_files,
    _parse_counter,
)
from ai_engineering.validator.categories.instruction_consistency import _extract_listings


def _extract_skill_agent_counts(
    content: str,
) -> tuple[list[str], list[str]]:
    """Extract skill and agent listings from an instruction file."""
    skills, agents = _extract_listings(content)
    return sorted(skills), sorted(agents)


def _check_counter_accuracy(target: Path, report: IntegrityReport, **_kwargs: object) -> None:
    """Verify skill/agent counts match across instruction files and product-contract."""
    counts: dict[str, tuple[int, int]] = {}  # file -> (skills, agents)

    for file_rel in _instruction_files(target):
        file_path = target / file_rel
        if not file_path.exists():
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.COUNTER_ACCURACY,
                    name=f"missing-{file_rel}",
                    status=IntegrityStatus.FAIL,
                    message=f"Instruction file not found: {file_rel}",
                    file_path=file_rel,
                )
            )
            continue
        content = file_path.read_text(encoding="utf-8", errors="replace")
        skills, agents = _extract_skill_agent_counts(content)
        counts[file_rel] = (len(skills), len(agents))

    if not counts:
        return

    # All instruction files should have the same counts
    skill_counts = {f: c[0] for f, c in counts.items()}
    agent_counts = {f: c[1] for f, c in counts.items()}

    unique_skill_counts = set(skill_counts.values())
    unique_agent_counts = set(agent_counts.values())

    if len(unique_skill_counts) > 1:
        detail = ", ".join(f"{f}: {c}" for f, c in skill_counts.items())
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.COUNTER_ACCURACY,
                name="skill-count-mismatch",
                status=IntegrityStatus.FAIL,
                message=f"Skill counts differ across instruction files: {detail}",
            )
        )
    else:
        count = next(iter(unique_skill_counts)) if unique_skill_counts else 0
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.COUNTER_ACCURACY,
                name="skill-counts-consistent",
                status=IntegrityStatus.OK,
                message=f"All instruction files list {count} skills",
            )
        )

    if len(unique_agent_counts) > 1:
        detail = ", ".join(f"{f}: {c}" for f, c in agent_counts.items())
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.COUNTER_ACCURACY,
                name="agent-count-mismatch",
                status=IntegrityStatus.FAIL,
                message=f"Agent counts differ across instruction files: {detail}",
            )
        )
    else:
        count = next(iter(unique_agent_counts)) if unique_agent_counts else 0
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.COUNTER_ACCURACY,
                name="agent-counts-consistent",
                status=IntegrityStatus.OK,
                message=f"All instruction files list {count} agents",
            )
        )

    # Verify product-contract.md counters
    pc_path = target / ".ai-engineering" / "context" / "product" / "product-contract.md"
    if pc_path.exists():
        pc_content = pc_path.read_text(encoding="utf-8", errors="replace")
        obj_match = _parse_counter(pc_content, ",")
        if obj_match:
            pc_skills, pc_agents = obj_match
            ref_skills = next(iter(unique_skill_counts), 0)
            ref_agents = next(iter(unique_agent_counts), 0)

            if pc_skills != ref_skills:
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.COUNTER_ACCURACY,
                        name="product-contract-skills",
                        status=IntegrityStatus.FAIL,
                        message=(
                            f"product-contract.md says {pc_skills} skills, "
                            f"instruction files list {ref_skills}"
                        ),
                        file_path=pc_path.relative_to(target).as_posix(),
                    )
                )
            else:
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.COUNTER_ACCURACY,
                        name="product-contract-skills",
                        status=IntegrityStatus.OK,
                        message=f"product-contract.md skill count matches: {pc_skills}",
                    )
                )

            if pc_agents != ref_agents:
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.COUNTER_ACCURACY,
                        name="product-contract-agents",
                        status=IntegrityStatus.FAIL,
                        message=(
                            f"product-contract.md says {pc_agents} agents, "
                            f"instruction files list {ref_agents}"
                        ),
                        file_path=pc_path.relative_to(target).as_posix(),
                    )
                )
            else:
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.COUNTER_ACCURACY,
                        name="product-contract-agents",
                        status=IntegrityStatus.OK,
                        message=f"product-contract.md agent count matches: {pc_agents}",
                    )
                )
