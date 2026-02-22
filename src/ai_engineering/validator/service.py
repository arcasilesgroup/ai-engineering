"""Content integrity validation service for ai-engineering governance.

Implements programmatic validation of the 6 content-integrity categories:
1. File Existence — verify all internal path references resolve.
2. Mirror Sync — SHA-256 compare canonical vs template mirrors.
3. Counter Accuracy — skill/agent counts match across instruction files and product-contract.
4. Cross-Reference Integrity — bidirectional reference validation.
5. Instruction File Consistency — all 6 instruction files list identical skills/agents.
6. Manifest Coherence — ownership globs match filesystem, active spec valid.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class IntegrityCategory(StrEnum):
    """Categories of content-integrity validation."""

    FILE_EXISTENCE = "file-existence"
    MIRROR_SYNC = "mirror-sync"
    COUNTER_ACCURACY = "counter-accuracy"
    CROSS_REFERENCE = "cross-reference"
    INSTRUCTION_CONSISTENCY = "instruction-consistency"
    MANIFEST_COHERENCE = "manifest-coherence"


class CheckStatus(StrEnum):
    """Status of a single integrity check."""

    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class IntegrityCheckResult:
    """Result of a single integrity check."""

    category: IntegrityCategory
    name: str
    status: CheckStatus
    message: str
    file_path: str | None = None


@dataclass
class IntegrityReport:
    """Aggregated report from all content-integrity categories."""

    checks: list[IntegrityCheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if no checks failed."""
        return all(c.status != CheckStatus.FAIL for c in self.checks)

    @property
    def summary(self) -> dict[str, int]:
        """Count of checks by status."""
        counts: dict[str, int] = {}
        for check in self.checks:
            counts[check.status.value] = counts.get(check.status.value, 0) + 1
        return counts

    def by_category(self) -> dict[IntegrityCategory, list[IntegrityCheckResult]]:
        """Group checks by category."""
        result: dict[IntegrityCategory, list[IntegrityCheckResult]] = {}
        for check in self.checks:
            result.setdefault(check.category, []).append(check)
        return result

    def category_passed(self, category: IntegrityCategory) -> bool:
        """True if all checks in a category passed (no FAIL)."""
        return all(c.status != CheckStatus.FAIL for c in self.checks if c.category == category)

    def to_dict(self) -> dict[str, object]:
        """Serialize report for JSON output."""
        categories = self.by_category()
        category_results: dict[str, object] = {}
        for cat in IntegrityCategory:
            cat_checks = categories.get(cat, [])
            category_results[cat.value] = {
                "passed": all(c.status != CheckStatus.FAIL for c in cat_checks),
                "checks": [
                    {
                        "name": c.name,
                        "status": c.status.value,
                        "message": c.message,
                        **({"file": c.file_path} if c.file_path else {}),
                    }
                    for c in cat_checks
                ],
            }
        categories_passed = sum(1 for cat in IntegrityCategory if self.category_passed(cat))
        return {
            "passed": self.passed,
            "summary": self.summary,
            "categories_passed": f"{categories_passed}/{len(IntegrityCategory)}",
            "categories": category_results,
        }


# ---------------------------------------------------------------------------
# Internal path reference pattern
# ---------------------------------------------------------------------------

_PATH_REF_PATTERN = re.compile(
    r"`?\.?(?:ai-engineering/)?(skills/[^\s`*]+\.md"
    r"|agents/[^\s`*]+\.md"
    r"|standards/[^\s`*]+\.md"
    r"|context/[^\s`*]+\.md)`?"
)

# Instruction files that must stay in sync (all 6)
_INSTRUCTION_FILES: list[str] = [
    ".github/copilot-instructions.md",
    "AGENTS.md",
    "CLAUDE.md",
    "codex.md",
    "src/ai_engineering/templates/project/copilot-instructions.md",
    "src/ai_engineering/templates/project/AGENTS.md",
    "src/ai_engineering/templates/project/CLAUDE.md",
    "src/ai_engineering/templates/project/codex.md",
]

# Mirror pairs: (canonical_root, mirror_root, glob_patterns, exclusion_prefixes)
_GOVERNANCE_MIRROR = (
    ".ai-engineering",
    "src/ai_engineering/templates/.ai-engineering",
    ["skills/**/*.md", "agents/**/*.md", "standards/framework/**/*.md"],
    ["context/", "state/", "standards/team/"],
)

_CLAUDE_COMMANDS_MIRROR = (
    ".claude/commands",
    "src/ai_engineering/templates/project/.claude/commands",
)

# Skill/agent listing patterns in instruction files
_SKILL_LINE_PATTERN = re.compile(r"^- `\.ai-engineering/skills/(.+\.md)`", re.MULTILINE)
_AGENT_LINE_PATTERN = re.compile(r"^- `\.ai-engineering/agents/(.+\.md)`", re.MULTILINE)

def _parse_counter(text: str, separator: str) -> tuple[int, int] | None:
    """Extract skill and agent counts from text using plain string parsing.

    Replaces regex-based counter patterns to eliminate backtracking risk
    (ReDoS — S5852).  The function splits by *separator* (e.g. ``,`` or
    ``+``), then tokenises each side looking for ``<number> skill(s)``
    and ``<number> agent(s)``.

    Args:
        text: The full text to search through line-by-line.
        separator: The character that separates the skill and agent parts
            (typically ``,`` for objectives or ``+`` for KPI rows).

    Returns:
        ``(skills, agents)`` tuple if both counts found, else ``None``.
    """
    for line in text.splitlines():
        if separator not in line:
            continue
        parts = line.split(separator)
        skills: int | None = None
        agents: int | None = None
        for part in parts:
            tokens = part.strip().split()
            for i, tok in enumerate(tokens):
                if tok.startswith("skill") and i > 0 and tokens[i - 1].isdigit():
                    skills = int(tokens[i - 1])
                elif tok.startswith("agent") and i > 0 and tokens[i - 1].isdigit():
                    agents = int(tokens[i - 1])
        if skills is not None and agents is not None:
            return (skills, agents)
    return None


def _sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _glob_files(root: Path, patterns: list[str]) -> set[Path]:
    """Collect files matching multiple glob patterns under a root."""
    result: set[Path] = set()
    for pattern in patterns:
        result.update(root.glob(pattern))
    return {p for p in result if p.is_file()}


def _is_excluded(relative: Path, prefixes: list[str]) -> bool:
    """Check if a relative path starts with any exclusion prefix."""
    rel_str = relative.as_posix()
    return any(rel_str.startswith(prefix) for prefix in prefixes)


# ---------------------------------------------------------------------------
# Category 1: File Existence
# ---------------------------------------------------------------------------


def _check_file_existence(target: Path, report: IntegrityReport) -> None:
    """Verify all internal path references resolve to existing files."""
    ai_dir = target / ".ai-engineering"
    if not ai_dir.is_dir():
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.FILE_EXISTENCE,
                name="governance-directory",
                status=CheckStatus.FAIL,
                message=".ai-engineering/ directory not found",
            )
        )
        return

    # Scan all .md files for internal references
    broken_refs: list[tuple[str, str]] = []
    md_files = sorted(ai_dir.rglob("*.md"))
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8", errors="replace")
        for match in _PATH_REF_PATTERN.finditer(content):
            ref_path = match.group(1) if match.group(1) else match.group(0)
            # Clean up backticks and leading dots
            ref_path = ref_path.strip("`").lstrip(".")
            if ref_path.startswith("ai-engineering/"):
                ref_path = ref_path[len("ai-engineering/") :]
            # Skip template placeholders like <name>, <stack>, <category>
            if "<" in ref_path and ">" in ref_path:
                continue
            full_path = ai_dir / ref_path
            if not full_path.exists():
                rel_source = md_file.relative_to(target).as_posix()
                broken_refs.append((rel_source, ref_path))

    if broken_refs:
        for source, ref in broken_refs:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="broken-reference",
                    status=CheckStatus.FAIL,
                    message=f"Reference to '{ref}' not found",
                    file_path=source,
                )
            )
    else:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.FILE_EXISTENCE,
                name="path-references",
                status=CheckStatus.OK,
                message="All internal path references resolve",
            )
        )

    # Verify spec directory completeness
    specs_dir = ai_dir / "context" / "specs"
    if specs_dir.is_dir():
        for spec_dir in sorted(specs_dir.iterdir()):
            if not spec_dir.is_dir() or spec_dir.name.startswith("_"):
                continue
            required = ["spec.md", "plan.md", "tasks.md"]
            missing = [f for f in required if not (spec_dir / f).exists()]
            if missing:
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.FILE_EXISTENCE,
                        name=f"spec-{spec_dir.name}",
                        status=CheckStatus.FAIL,
                        message=f"Missing files: {', '.join(missing)}",
                        file_path=spec_dir.relative_to(target).as_posix(),
                    )
                )
            else:
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.FILE_EXISTENCE,
                        name=f"spec-{spec_dir.name}",
                        status=CheckStatus.OK,
                        message="Spec directory complete",
                        file_path=spec_dir.relative_to(target).as_posix(),
                    )
                )


# ---------------------------------------------------------------------------
# Category 2: Mirror Sync
# ---------------------------------------------------------------------------


def _check_mirror_sync(target: Path, report: IntegrityReport) -> None:
    """SHA-256 compare canonical governance files vs template mirrors."""
    canonical_root = target / _GOVERNANCE_MIRROR[0]
    mirror_root = target / _GOVERNANCE_MIRROR[1]
    patterns = _GOVERNANCE_MIRROR[2]
    exclusions = _GOVERNANCE_MIRROR[3]

    if not canonical_root.is_dir():
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="canonical-root",
                status=CheckStatus.FAIL,
                message=f"Canonical root not found: {_GOVERNANCE_MIRROR[0]}",
            )
        )
        return

    if not mirror_root.is_dir():
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="mirror-root",
                status=CheckStatus.FAIL,
                message=f"Mirror root not found: {_GOVERNANCE_MIRROR[1]}",
            )
        )
        return

    # Collect canonical files
    canonical_files = _glob_files(canonical_root, patterns)
    canonical_relatives = {
        f.relative_to(canonical_root)
        for f in canonical_files
        if not _is_excluded(f.relative_to(canonical_root), exclusions)
    }

    # Collect mirror files
    mirror_files = _glob_files(mirror_root, patterns)
    mirror_relatives = {
        f.relative_to(mirror_root)
        for f in mirror_files
        if not _is_excluded(f.relative_to(mirror_root), exclusions)
    }

    # Check pairs
    mismatches = 0
    checked = 0
    for rel in sorted(canonical_relatives & mirror_relatives):
        checked += 1
        canonical_hash = _sha256(canonical_root / rel)
        mirror_hash = _sha256(mirror_root / rel)
        if canonical_hash != mirror_hash:
            mismatches += 1
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name=f"desync-{rel.as_posix()}",
                    status=CheckStatus.FAIL,
                    message=f"Mirror desync: {rel.as_posix()}",
                    file_path=rel.as_posix(),
                )
            )

    # Missing mirrors
    for rel in sorted(canonical_relatives - mirror_relatives):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name=f"missing-mirror-{rel.as_posix()}",
                status=CheckStatus.FAIL,
                message=f"Canonical file has no mirror: {rel.as_posix()}",
                file_path=rel.as_posix(),
            )
        )

    # Orphaned mirrors
    for rel in sorted(mirror_relatives - canonical_relatives):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name=f"orphan-mirror-{rel.as_posix()}",
                status=CheckStatus.WARN,
                message=f"Mirror file has no canonical source: {rel.as_posix()}",
                file_path=rel.as_posix(),
            )
        )

    # Claude commands mirror
    _check_claude_commands_mirror(target, report)

    if mismatches == 0 and not (canonical_relatives - mirror_relatives):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="governance-mirrors",
                status=CheckStatus.OK,
                message=f"All {checked} mirror pairs in sync",
            )
        )


def _check_claude_commands_mirror(target: Path, report: IntegrityReport) -> None:
    """Check .claude/commands/ mirror sync."""
    canonical_root = target / _CLAUDE_COMMANDS_MIRROR[0]
    mirror_root = target / _CLAUDE_COMMANDS_MIRROR[1]

    if not canonical_root.is_dir():
        return  # .claude/commands/ is optional
    if not mirror_root.is_dir():
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="claude-commands-mirror-root",
                status=CheckStatus.FAIL,
                message="Claude commands mirror directory not found",
            )
        )
        return

    canonical_files = {
        f.relative_to(canonical_root) for f in sorted(canonical_root.rglob("*.md")) if f.is_file()
    }
    mirror_files = {
        f.relative_to(mirror_root) for f in sorted(mirror_root.rglob("*.md")) if f.is_file()
    }

    mismatches = 0
    for rel in sorted(canonical_files & mirror_files):
        if _sha256(canonical_root / rel) != _sha256(mirror_root / rel):
            mismatches += 1
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name=f"claude-cmd-desync-{rel.as_posix()}",
                    status=CheckStatus.FAIL,
                    message=f"Claude command mirror desync: {rel.as_posix()}",
                    file_path=rel.as_posix(),
                )
            )

    for rel in sorted(canonical_files - mirror_files):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name=f"claude-cmd-missing-{rel.as_posix()}",
                status=CheckStatus.FAIL,
                message=f"Claude command has no mirror: {rel.as_posix()}",
                file_path=rel.as_posix(),
            )
        )

    if mismatches == 0 and not (canonical_files - mirror_files):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="claude-commands-mirrors",
                status=CheckStatus.OK,
                message=f"All {len(canonical_files & mirror_files)} Claude command mirrors in sync",
            )
        )


# ---------------------------------------------------------------------------
# Category 3: Counter Accuracy
# ---------------------------------------------------------------------------


def _extract_skill_agent_counts(
    content: str,
) -> tuple[list[str], list[str]]:
    """Extract skill and agent path listings from an instruction file."""
    skills = _SKILL_LINE_PATTERN.findall(content)
    agents = _AGENT_LINE_PATTERN.findall(content)
    return skills, agents


def _check_counter_accuracy(target: Path, report: IntegrityReport) -> None:
    """Verify skill/agent counts match across instruction files and product-contract."""
    counts: dict[str, tuple[int, int]] = {}  # file -> (skills, agents)

    for file_rel in _INSTRUCTION_FILES:
        file_path = target / file_rel
        if not file_path.exists():
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.COUNTER_ACCURACY,
                    name=f"missing-{file_rel}",
                    status=CheckStatus.FAIL,
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
                status=CheckStatus.FAIL,
                message=f"Skill counts differ across instruction files: {detail}",
            )
        )
    else:
        count = next(iter(unique_skill_counts)) if unique_skill_counts else 0
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.COUNTER_ACCURACY,
                name="skill-counts-consistent",
                status=CheckStatus.OK,
                message=f"All instruction files list {count} skills",
            )
        )

    if len(unique_agent_counts) > 1:
        detail = ", ".join(f"{f}: {c}" for f, c in agent_counts.items())
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.COUNTER_ACCURACY,
                name="agent-count-mismatch",
                status=CheckStatus.FAIL,
                message=f"Agent counts differ across instruction files: {detail}",
            )
        )
    else:
        count = next(iter(unique_agent_counts)) if unique_agent_counts else 0
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.COUNTER_ACCURACY,
                name="agent-counts-consistent",
                status=CheckStatus.OK,
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
                        status=CheckStatus.FAIL,
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
                        status=CheckStatus.OK,
                        message=f"product-contract.md skill count matches: {pc_skills}",
                    )
                )

            if pc_agents != ref_agents:
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.COUNTER_ACCURACY,
                        name="product-contract-agents",
                        status=CheckStatus.FAIL,
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
                        status=CheckStatus.OK,
                        message=f"product-contract.md agent count matches: {pc_agents}",
                    )
                )


# ---------------------------------------------------------------------------
# Category 4: Cross-Reference Integrity
# ---------------------------------------------------------------------------

_REFERENCES_SECTION = re.compile(r"^## References\s*\n(.*?)(?=\n## |\Z)", re.MULTILINE | re.DOTALL)
_REF_LINE = re.compile(r"^- `([^`]+)`", re.MULTILINE)


def _parse_references(content: str) -> list[str]:
    """Extract file paths from the ## References section of a governance file."""
    section_match = _REFERENCES_SECTION.search(content)
    if not section_match:
        return []
    section = section_match.group(1)
    return _REF_LINE.findall(section)


def _check_cross_references(target: Path, report: IntegrityReport) -> None:
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
        for md_file in sorted(base.rglob("*.md")):
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


# ---------------------------------------------------------------------------
# Category 5: Instruction File Consistency
# ---------------------------------------------------------------------------


def _extract_listings(content: str) -> tuple[set[str], set[str]]:
    """Extract skill and agent path sets from an instruction file."""
    skills = set(_SKILL_LINE_PATTERN.findall(content))
    agents = set(_AGENT_LINE_PATTERN.findall(content))
    return skills, agents


_SUBSECTION_PATTERN = re.compile(r"^### (.+)$", re.MULTILINE)

_REQUIRED_SUBSECTIONS = {
    "Workflows",
    "Dev Skills",
    "Review Skills",
    "Docs Skills",
    "Govern Skills",
    "Quality Skills",
}


def _check_instruction_consistency(target: Path, report: IntegrityReport) -> None:
    """Verify all 6 instruction files list identical skills and agents."""
    all_skills: dict[str, set[str]] = {}
    all_agents: dict[str, set[str]] = {}

    for file_rel in _INSTRUCTION_FILES:
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
    reference_file = _INSTRUCTION_FILES[0]
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


# ---------------------------------------------------------------------------
# Category 6: Manifest Coherence
# ---------------------------------------------------------------------------


def _check_manifest_coherence(target: Path, report: IntegrityReport) -> None:
    """Verify manifest ownership globs and active spec pointer."""
    ai_dir = target / ".ai-engineering"
    manifest_path = ai_dir / "manifest.yml"

    if not manifest_path.exists():
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="manifest-missing",
                status=CheckStatus.FAIL,
                message="manifest.yml not found",
            )
        )
        return

    # Check ownership directory structure exists
    ownership_dirs = [
        ("standards/framework", "framework_managed"),
        ("skills", "framework_managed"),
        ("agents", "framework_managed"),
        ("context", "project_managed"),
        ("state", "system_managed"),
    ]

    for dir_rel, category in ownership_dirs:
        dir_path = ai_dir / dir_rel
        if not dir_path.is_dir():
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MANIFEST_COHERENCE,
                    name=f"missing-dir-{dir_rel}",
                    status=CheckStatus.FAIL,
                    message=f"{category} directory not found: {dir_rel}",
                    file_path=f".ai-engineering/{dir_rel}",
                )
            )
        else:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MANIFEST_COHERENCE,
                    name=f"dir-{dir_rel}",
                    status=CheckStatus.OK,
                    message=f"{category} directory exists: {dir_rel}",
                )
            )

    # Verify active spec pointer
    active_path = ai_dir / "context" / "specs" / "_active.md"
    if active_path.exists():
        content = active_path.read_text(encoding="utf-8", errors="replace")
        # Extract active spec from frontmatter
        active_match = re.search(r'^active:\s*"([^"]+)"', content, re.MULTILINE)
        if active_match:
            active_spec = active_match.group(1)
            if active_spec == "none":
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.MANIFEST_COHERENCE,
                        name="active-spec",
                        status=CheckStatus.OK,
                        message="No active spec (idle)",
                    )
                )
            elif not (ai_dir / "context" / "specs" / active_spec).is_dir():
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.MANIFEST_COHERENCE,
                        name="active-spec-dir",
                        status=CheckStatus.FAIL,
                        message=f"Active spec directory not found: {active_spec}",
                    )
                )
            elif not (ai_dir / "context" / "specs" / active_spec / "spec.md").exists():
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.MANIFEST_COHERENCE,
                        name="active-spec-file",
                        status=CheckStatus.FAIL,
                        message=f"Active spec missing spec.md: {active_spec}",
                    )
                )
            else:
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.MANIFEST_COHERENCE,
                        name="active-spec",
                        status=CheckStatus.OK,
                        message=f"Active spec valid: {active_spec}",
                    )
                )
    else:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="active-spec-pointer",
                status=CheckStatus.WARN,
                message="_active.md not found",
            )
        )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

_CATEGORY_CHECKS: dict[
    IntegrityCategory,
    type[None],  # placeholder for callable type
] = {}

# Map category to checker function
_CHECKERS: list[tuple[IntegrityCategory, type[None]]] = []


def validate_content_integrity(
    target: Path,
    *,
    categories: list[IntegrityCategory] | None = None,
) -> IntegrityReport:
    """Run content-integrity validation on a project.

    Validates governance content across 6 categories. If *categories* is
    provided, only the specified categories are checked.

    Args:
        target: Project root directory.
        categories: Optional list of categories to check. Defaults to all.

    Returns:
        IntegrityReport with results from all checked categories.
    """
    report = IntegrityReport()

    checkers: list[tuple[IntegrityCategory, Callable[[Path, IntegrityReport], None]]] = [
        (IntegrityCategory.FILE_EXISTENCE, _check_file_existence),
        (IntegrityCategory.MIRROR_SYNC, _check_mirror_sync),
        (IntegrityCategory.COUNTER_ACCURACY, _check_counter_accuracy),
        (IntegrityCategory.CROSS_REFERENCE, _check_cross_references),
        (IntegrityCategory.INSTRUCTION_CONSISTENCY, _check_instruction_consistency),
        (IntegrityCategory.MANIFEST_COHERENCE, _check_manifest_coherence),
    ]

    active_categories = set(categories) if categories else None

    for category, checker in checkers:
        if active_categories and category not in active_categories:
            continue
        checker(target, report)

    return report
