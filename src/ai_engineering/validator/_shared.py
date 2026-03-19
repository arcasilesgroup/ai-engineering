"""Shared types, utilities, and constants for content-integrity validation."""

from __future__ import annotations

import hashlib
import re
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
    SKILL_FRONTMATTER = "skill-frontmatter"


class IntegrityStatus(StrEnum):
    """Status of a single integrity check."""

    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class IntegrityCheckResult:
    """Result of a single integrity check."""

    category: IntegrityCategory
    name: str
    status: IntegrityStatus
    message: str
    file_path: str | None = None


@dataclass
class IntegrityReport:
    """Aggregated report from all content-integrity categories."""

    checks: list[IntegrityCheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if no checks failed."""
        return all(c.status != IntegrityStatus.FAIL for c in self.checks)

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
        return all(c.status != IntegrityStatus.FAIL for c in self.checks if c.category == category)

    def to_dict(self) -> dict[str, object]:
        """Serialize report for JSON output."""
        categories = self.by_category()
        category_results: dict[str, object] = {}
        for cat in IntegrityCategory:
            cat_checks = categories.get(cat, [])
            category_results[cat.value] = {
                "passed": all(c.status != IntegrityStatus.FAIL for c in cat_checks),
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
    r"|contexts/[^\s`*]+\.md"
    r"|context/[^\s`*]+\.md)`?"
)

# Paths referenced in governance docs but only exist conditionally.
# The file-existence checker skips these to avoid false positives.
_KNOWN_OPTIONAL_PATHS: set[str] = {
    "specs/_active.md",
}

# Instruction files that must stay in sync.
# Base files exist in every governed project; template files only in the source repo.
_BASE_INSTRUCTION_FILES: list[str] = [
    ".github/copilot-instructions.md",
    "AGENTS.md",
    "CLAUDE.md",
]

_TEMPLATE_INSTRUCTION_FILES: list[str] = [
    "src/ai_engineering/templates/project/copilot-instructions.md",
    "src/ai_engineering/templates/project/AGENTS.md",
    "src/ai_engineering/templates/project/CLAUDE.md",
]


def _is_source_repo(target: Path) -> bool:
    """True if *target* is the ai-engineering source repository."""
    return (target / "src" / "ai_engineering" / "templates").is_dir()


def _instruction_files(target: Path) -> list[str]:
    """Return the instruction file list appropriate for *target*."""
    if _is_source_repo(target):
        return _BASE_INSTRUCTION_FILES + _TEMPLATE_INSTRUCTION_FILES
    return list(_BASE_INSTRUCTION_FILES)


# Mirror pairs: (canonical_root, mirror_root, glob_patterns, exclusion_prefixes)
# Note: skills/, agents/, and evals/ are no longer in templates — skills/agents
# live in IDE-specific directories (.claude/, .agents/), evals/ is runtime state.
# The governance mirror only validates standards, runbooks, and the manifest.
_GOVERNANCE_MIRROR = (
    ".ai-engineering",
    "src/ai_engineering/templates/.ai-engineering",
    [
        "contexts/**/*.md",
        "runbooks/**/*.md",
        "manifest.yml",
        "README.md",
    ],
    ["context/", "state/", "evals/", "tasks/"],
)

_CLAUDE_COMMANDS_MIRROR = (
    ".claude/commands",
    "src/ai_engineering/templates/project/.claude/commands",
)

_COPILOT_PROMPTS_MIRROR = (
    ".github/prompts",
    "src/ai_engineering/templates/project/prompts",
)

_COPILOT_AGENTS_MIRROR = (
    ".github/agents",
    "src/ai_engineering/templates/project/agents",
)

# Skill/agent listing patterns in instruction files (IDE-specific paths)
_SKILL_PATH_PATTERN = re.compile(
    r"^- `(?:\.claude|\.agents)/skills/([^`/]+)/SKILL\.md`",
    re.MULTILINE,
)
_AGENT_PATH_PATTERN = re.compile(
    r"^- `(?:\.claude|\.agents)/agents/([^`/]+)\.md`",
    re.MULTILINE,
)
_SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# Skill frontmatter patterns
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SUPPORTED_OSES = {"linux", "darwin", "win32"}

# Cross-reference patterns
_REFERENCES_SECTION = re.compile(r"^## References\s*\n(.*?)(?=\n## |\Z)", re.MULTILINE | re.DOTALL)
_REF_LINE = re.compile(r"^- `([^`]+)`", re.MULTILINE)

# Instruction consistency patterns
_SUBSECTION_PATTERN = re.compile(r"^### (.+)$", re.MULTILINE)
_REQUIRED_SUBSECTIONS: set[str] = set()


# ---------------------------------------------------------------------------
# Shared utility functions
# ---------------------------------------------------------------------------


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


def _extract_section(content: str, heading: str) -> str:
    """Extract markdown content under a level-2 heading until next level-2 heading."""
    lines = content.splitlines()
    heading_prefix = f"## {heading}".lower()
    start: int | None = None

    for index, line in enumerate(lines):
        if line.strip().lower().startswith(heading_prefix):
            start = index + 1
            break

    if start is None:
        return ""

    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break

    return "\n".join(lines[start:end])


def _is_table_separator(line: str) -> bool:
    """Return True when line is a markdown table separator row."""
    stripped = line.strip()
    return bool(stripped) and set(stripped) <= {"|", "-", ":", " "}


def _parse_skill_names(section: str) -> set[str]:
    """Parse skill names from instruction section supporting bullets and tables."""
    skills = set(_SKILL_PATH_PATTERN.findall(section))

    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or _is_table_separator(line):
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        for cell in cells:
            normalized = cell.lower()
            if not cell or normalized in {
                "skills",
                "skills (alphabetical)",
                "domain",
            }:
                continue
            for token in [part.strip() for part in cell.split(",")]:
                if _SKILL_NAME_PATTERN.fullmatch(token):
                    skills.add(token)

    return skills


def _parse_agent_names(section: str) -> set[str]:
    """Parse agent names from instruction section supporting bullets and tables."""
    agents = set(_AGENT_PATH_PATTERN.findall(section))

    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or _is_table_separator(line):
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells:
            continue

        first = cells[0]
        if not first or first.lower() == "agent":
            continue
        if _SKILL_NAME_PATTERN.fullmatch(first):
            agents.add(first)

    return agents


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


# ---------------------------------------------------------------------------
# File cache for single-pass enumeration + SHA-256 caching
# ---------------------------------------------------------------------------


class FileCache:
    """Cache for file enumeration and SHA-256 hashes.

    Reduces repeated rglob() calls and SHA-256 computations across
    multiple validation categories within a single run.
    """

    def __init__(self) -> None:
        self._hash_cache: dict[Path, str] = {}
        self._rglob_cache: dict[tuple[Path, str], list[Path]] = {}

    def sha256(self, path: Path) -> str:
        """Return cached SHA-256 hex digest, computing if needed."""
        if path not in self._hash_cache:
            self._hash_cache[path] = _sha256(path)
        return self._hash_cache[path]

    def rglob(self, root: Path, pattern: str) -> list[Path]:
        """Return cached rglob results, computing if needed."""
        key = (root, pattern)
        if key not in self._rglob_cache:
            self._rglob_cache[key] = sorted(root.rglob(pattern))
        return self._rglob_cache[key]

    def glob_files(self, root: Path, patterns: list[str]) -> set[Path]:
        """Collect files matching multiple glob patterns under a root (cached)."""
        result: set[Path] = set()
        for pattern in patterns:
            result.update(self.rglob(root, pattern))
        return {p for p in result if p.is_file()}
