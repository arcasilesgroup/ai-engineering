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

# README tagline / catalog counts (spec-153 D-153-12/13). Both READMEs carry a
# "N skills · M agents · K surfaces" line (root README.md tagline and the
# .ai-engineering/README.md catalog block). The numbers are derived caches over
# the skill/agent files + manifest surfaces; this check fails on count drift.
_README_SKILLS_RE = re.compile(r"(\d+)\s+skills?\b", re.IGNORECASE)
_README_AGENTS_RE = re.compile(r"(\d+)\s+agents?\b", re.IGNORECASE)
_README_SURFACES_RE = re.compile(r"(\d+)\s+surfaces?\b", re.IGNORECASE)
_CATALOG_START = "<!-- catalog:start -->"
_CATALOG_END = "<!-- catalog:end -->"

# README surfaces participating in the count drift gate, relative to the target
# root. Each is optional: absent files (or files without the tagline) are
# skipped, but a present tagline with a wrong count fails.
_README_COUNT_FILES: tuple[str, ...] = (
    "README.md",
    ".ai-engineering/README.md",
)


def _readme_counts(content: str) -> tuple[list[int], list[int], list[int]]:
    """Extract ALL (skills, agents, surfaces) counts from a README.

    Returns one list per dimension carrying *every* occurrence of the count
    string, not just the first (spec-153 quality loop FINDING 3). The root
    README states each count twice — banner alt text + tagline — and a single
    ``re.search`` would only validate the first, letting the second silently
    rot. ``re.findall`` captures all occurrences so the caller can assert every
    one agrees with canonical. An empty list means the token is absent (the
    dimension is then skipped, not failed). The catalog marker block is used as
    the haystack when present (generated counts are the authority); otherwise
    the whole document is scanned.
    """
    haystack = content
    start = content.find(_CATALOG_START)
    end = content.find(_CATALOG_END)
    if start != -1 and end != -1 and end > start:
        haystack = content[start:end]
    return (
        [int(m) for m in _README_SKILLS_RE.findall(haystack)],
        [int(m) for m in _README_AGENTS_RE.findall(haystack)],
        [int(m) for m in _README_SURFACES_RE.findall(haystack)],
    )


def _check_readme_counts(
    target: Path,
    report: IntegrityReport,
    canonical_skills: int,
    canonical_agents: int,
    canonical_surfaces: int,
) -> None:
    """Verify README skill/agent/surface counts match canonical truth.

    Sources (spec-153 D-153-13): skills -> ``len(registry)`` / ``skills.total``;
    agents -> ``agents.total`` (9); surfaces -> ``len(surfaces.enabled)`` from
    the manifest. The surfaces literal is checked only when a clean manifest
    source exists (``canonical_surfaces > 0``); otherwise it is left unchecked.
    Absent READMEs / missing taglines are skipped (not failed) so consumer
    projects and pre-Wave-6 READMEs without markers stay green.
    """
    expected = {
        "skills": canonical_skills,
        "agents": canonical_agents,
        "surfaces": canonical_surfaces,
    }
    for file_rel in _README_COUNT_FILES:
        file_path = target / file_rel
        if not file_path.is_file():
            continue
        content = file_path.read_text(encoding="utf-8", errors="replace")
        found = dict(zip(("skills", "agents", "surfaces"), _readme_counts(content), strict=True))
        for dimension, occurrences in found.items():
            canonical = expected[dimension]
            # Skip when the token is absent in this README, or when there is no
            # clean canonical source for the dimension (e.g. surfaces == 0).
            if not occurrences or canonical <= 0:
                continue
            # EVERY occurrence must agree with canonical — the root README carries
            # the count twice (banner alt + tagline); a single mismatch fails the
            # gate (spec-153 quality loop FINDING 3).
            mismatched = sorted({n for n in occurrences if n != canonical})
            if mismatched:
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.COUNTER_ACCURACY,
                        name=f"readme-{dimension}-{file_rel}",
                        status=IntegrityStatus.FAIL,
                        message=(
                            f"{file_rel} reports {', '.join(str(n) for n in mismatched)} "
                            f"{dimension} (across {len(occurrences)} occurrence(s)), "
                            f"canonical is {canonical}. "
                            "Fix: run 'ai-eng dev sync' to regenerate the catalog."
                        ),
                        file_path=file_rel,
                    )
                )
            else:
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.COUNTER_ACCURACY,
                        name=f"readme-{dimension}-{file_rel}",
                        status=IntegrityStatus.OK,
                        message=(
                            f"{file_rel} {dimension} count matches: {canonical} "
                            f"(all {len(occurrences)} occurrence(s) agree)"
                        ),
                    )
                )


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

    # Extract canonical counts from manifest.yml (source of truth). Loaded
    # before the early return so the README count drift gate (spec-153) runs
    # even when no instruction file carries pointer counts.
    cfg = load_manifest_config(target)
    canonical_skills = cfg.skills.total
    canonical_agents = cfg.agents.total
    canonical_surfaces = len(cfg.surfaces.enabled)

    # README tagline / catalog count drift gate (spec-153 D-153-12/13). Runs
    # independently of the instruction-file pointer counts.
    _check_readme_counts(
        target,
        report,
        canonical_skills=canonical_skills,
        canonical_agents=canonical_agents,
        canonical_surfaces=canonical_surfaces,
    )

    if not counts:
        return

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
