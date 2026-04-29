"""Category 3: Counter Accuracy — skill/agent counts match across files."""

from __future__ import annotations

import re
from pathlib import Path

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.validator._shared import (
    _COPILOT_INSTRUCTION_FILES,
    IntegrityCategory,
    IntegrityCheckResult,
    IntegrityReport,
    IntegrityStatus,
    _extract_listings,
    _instruction_files,
)

# Pattern to extract counts from pointer format: "Skills (35)" or "Agents (7)"
_POINTER_COUNT_RE = re.compile(r"Skills\s*\((\d+)\)", re.IGNORECASE)
_POINTER_AGENT_COUNT_RE = re.compile(r"Agents\s*\((\d+)\)", re.IGNORECASE)


def _extract_skill_agent_counts(
    content: str,
) -> tuple[int, int, bool]:
    """Extract skill and agent counts from an instruction file.

    Returns (skill_count, agent_count, is_pointer_format).
    Pointer format means the file uses "Skills (N)" instead of detailed listings.
    """
    skills, agents = _extract_listings(content)
    if skills or agents:
        return len(sorted(skills)), len(sorted(agents)), False

    # Try pointer format: "Skills (35)" / "Agents (7)"
    skill_match = _POINTER_COUNT_RE.search(content)
    agent_match = _POINTER_AGENT_COUNT_RE.search(content)
    skill_count = int(skill_match.group(1)) if skill_match else 0
    agent_count = int(agent_match.group(1)) if agent_match else 0
    return skill_count, agent_count, True


def _check_counter_accuracy(  # audit:exempt:pre-existing-debt-out-of-spec-114-G7-scope
    target: Path, report: IntegrityReport, **_kwargs: object
) -> None:
    """Verify skill/agent counts match across instruction files and manifest.yml.

    Spec-110 introduced slim overlays (CLAUDE.md and per-IDE entry-point
    files that delegate to AGENTS.md / CONSTITUTION.md). Such files have
    no skill/agent listing or pointer count by design, so the helper
    extracts (0, 0, True). To avoid forcing those files to embed counts
    and re-introduce duplication, files that report (0, 0, True) are
    treated as pure-delegation overlays and excluded from cross-file
    counter consistency. The canonical counts still come from
    ``.ai-engineering/manifest.yml`` (single source of truth).
    """
    counts: dict[str, tuple[int, int, bool]] = {}  # file -> (skills, agents, is_pointer)

    for file_rel in _instruction_files(target):
        file_path = target / file_rel
        if not file_path.exists():
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.COUNTER_ACCURACY,
                    name=f"missing-{file_rel}",
                    status=IntegrityStatus.FAIL,
                    message=(
                        f"Instruction file not found: {file_rel}. "
                        "Fix: run ai-eng update or ai-eng install --reconfigure"
                    ),
                    file_path=file_rel,
                )
            )
            continue
        content = file_path.read_text(encoding="utf-8", errors="replace")
        skill_count, agent_count, is_pointer = _extract_skill_agent_counts(content)
        # Slim overlays (spec-110): no listings and no pointer counts —
        # they delegate entirely to AGENTS.md/CONSTITUTION.md, so skip.
        if skill_count == 0 and agent_count == 0 and is_pointer:
            continue
        counts[file_rel] = (skill_count, agent_count, is_pointer)

    if not counts:
        return

    # Extract canonical counts from manifest.yml (source of truth)
    cfg = load_manifest_config(target)
    canonical_skills = cfg.skills.total
    canonical_agents = cfg.agents.total

    # Copilot files intentionally have fewer skills (platform-filtered).
    # Exclude them from cross-file consistency so they don't cause false failures.
    canonical_counts = {f: c for f, c in counts.items() if f not in _COPILOT_INSTRUCTION_FILES}
    copilot_counts = {f: c for f, c in counts.items() if f in _COPILOT_INSTRUCTION_FILES}

    skill_counts = {f: c[0] for f, c in canonical_counts.items()}
    agent_counts = {f: c[1] for f, c in canonical_counts.items()}

    unique_skill_counts = set(skill_counts.values())
    unique_agent_counts = set(agent_counts.values())

    # Validate Copilot files separately: their count must be <= canonical count
    if copilot_counts and unique_skill_counts:
        canonical_skill_count = next(iter(unique_skill_counts))
        for f, (sc, _ac, _is_ptr) in copilot_counts.items():
            if sc > canonical_skill_count:
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.COUNTER_ACCURACY,
                        name="copilot-skill-count-exceeds-canonical",
                        status=IntegrityStatus.FAIL,
                        message=(
                            f"{f} reports {sc} skills but canonical is {canonical_skill_count}; "
                            "Copilot count must be <= canonical (some skills are Copilot-excluded)"
                        ),
                        file_path=f,
                    )
                )

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

    # Verify pointer-format files match canonical counts from manifest.yml
    if canonical_skills > 0:
        ref_skills = next(iter(unique_skill_counts), 0)
        if ref_skills != canonical_skills:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.COUNTER_ACCURACY,
                    name="manifest-skills",
                    status=IntegrityStatus.FAIL,
                    message=(
                        f"manifest.yml lists {canonical_skills} skills, "
                        f"instruction files report {ref_skills}"
                    ),
                    file_path=".ai-engineering/manifest.yml",
                )
            )
        else:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.COUNTER_ACCURACY,
                    name="manifest-skills",
                    status=IntegrityStatus.OK,
                    message=f"manifest.yml skill count matches: {canonical_skills}",
                )
            )

    if canonical_agents > 0:
        ref_agents = next(iter(unique_agent_counts), 0)
        if ref_agents != canonical_agents:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.COUNTER_ACCURACY,
                    name="manifest-agents",
                    status=IntegrityStatus.FAIL,
                    message=(
                        f"manifest.yml lists {canonical_agents} agents, "
                        f"instruction files report {ref_agents}"
                    ),
                    file_path=".ai-engineering/manifest.yml",
                )
            )
        else:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.COUNTER_ACCURACY,
                    name="manifest-agents",
                    status=IntegrityStatus.OK,
                    message=f"manifest.yml agent count matches: {canonical_agents}",
                )
            )
