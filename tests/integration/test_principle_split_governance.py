"""RED-phase tests for spec-115 T-1.3 -- hybrid principle split.

Spec acceptance criteria:
    1. Spec-driven development, TDD, and proof-before-done keep explicit
       homes in governance documents.
    2. YAGNI, DRY, KISS, SOLID, clean architecture, and clean code live in
       exactly one canonical governed markdown artifact and are consumed from
       there by core implementation/review surfaces instead of being carried
       ad hoc across those surfaces.

Status: RED. The repository currently has governance homes for the hard-rule
subset, but it does not yet have one canonical operational-principles source.
The operational principles are still scattered across core Claude surfaces.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

ROOT_CONSTITUTION = REPO_ROOT / "CONSTITUTION.md"
FRAMEWORK_CONSTITUTION = REPO_ROOT / ".ai-engineering" / "CONSTITUTION.md"
GOVERNANCE_PATHS: tuple[Path, ...] = (ROOT_CONSTITUTION, FRAMEWORK_CONSTITUTION)

CORE_OPERATIONAL_SURFACE_PATHS: tuple[Path, ...] = (
    REPO_ROOT / ".claude" / "skills" / "ai-code" / "SKILL.md",
    REPO_ROOT / ".claude" / "skills" / "ai-test" / "handlers" / "tdd.md",
    REPO_ROOT / ".claude" / "agents" / "ai-build.md",
    REPO_ROOT / ".claude" / "agents" / "reviewer-architecture.md",
    REPO_ROOT / ".claude" / "agents" / "reviewer-correctness.md",
    REPO_ROOT / ".claude" / "agents" / "reviewer-maintainability.md",
)

EXCLUDED_OPERATIONAL_PREFIXES: tuple[str, ...] = (
    ".ai-engineering/specs",
    ".ai-engineering/state",
    ".ai-engineering/observations",
)

HARD_RULE_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "spec-driven development": (
        re.compile(r"\bspec-driven development\b", re.IGNORECASE),
        re.compile(r"\bapproved spec\b", re.IGNORECASE),
    ),
    "TDD": (
        re.compile(r"\btest-driven development\b", re.IGNORECASE),
        re.compile(r"\bfailing test\b", re.IGNORECASE),
        re.compile(r"\bTDD\b"),
    ),
    "proof-before-done": (
        re.compile(r"\bproof-before-done\b", re.IGNORECASE),
        re.compile(r"\bverify before done\b", re.IGNORECASE),
        re.compile(r"\bevidence before claims\b", re.IGNORECASE),
        re.compile(r"\bverification-before-done\b", re.IGNORECASE),
    ),
}

OPERATIONAL_PRINCIPLE_PATTERNS: dict[str, re.Pattern[str]] = {
    "YAGNI": re.compile(r"\bYAGNI\b"),
    "DRY": re.compile(r"\bDRY\b"),
    "KISS": re.compile(r"\bKISS\b"),
    "SOLID": re.compile(r"\bSOLID\b"),
    "clean architecture": re.compile(r"\bclean architecture\b", re.IGNORECASE),
    "clean code": re.compile(r"\bclean code\b", re.IGNORECASE),
}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _matches_any(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _principle_mentions(text: str) -> tuple[str, ...]:
    return tuple(
        principle
        for principle, pattern in OPERATIONAL_PRINCIPLE_PATTERNS.items()
        if pattern.search(text)
    )


def _is_operational_candidate_path(path: Path) -> bool:
    rel_path = path.relative_to(REPO_ROOT).as_posix()
    return not any(
        rel_path == prefix or rel_path.startswith(prefix + "/")
        for prefix in EXCLUDED_OPERATIONAL_PREFIXES
    )


def _find_canonical_operational_sources() -> list[Path]:
    candidates: list[Path] = []
    for path in sorted((REPO_ROOT / ".ai-engineering").rglob("*.md")):
        if not _is_operational_candidate_path(path):
            continue
        text = _read_text(path)
        if all(pattern.search(text) for pattern in OPERATIONAL_PRINCIPLE_PATTERNS.values()):
            candidates.append(path)
    return candidates


def test_hard_rule_subset_has_governance_homes() -> None:
    """The hard-rule subset remains encoded in governance documents."""
    missing_governance_files = [
        str(path.relative_to(REPO_ROOT)) for path in GOVERNANCE_PATHS if not path.is_file()
    ]

    assert not missing_governance_files, (
        "Expected the governance documents for the spec-115 hard-rule split to exist, "
        f"but these are missing: {missing_governance_files}."
    )

    governance_text = {path: _read_text(path) for path in GOVERNANCE_PATHS}
    missing_rules: list[str] = []

    for rule_name, patterns in HARD_RULE_PATTERNS.items():
        owners = [
            str(path.relative_to(REPO_ROOT))
            for path, text in governance_text.items()
            if _matches_any(text, patterns)
        ]
        if not owners:
            missing_rules.append(rule_name)

    assert not missing_rules, (
        "Spec-115 requires the hard-rule subset to remain in governance documents, "
        f"but these rules do not have a governance home: {missing_rules}."
    )


def test_operational_principles_have_one_canonical_source_and_consumers_reference_it() -> None:
    """Operational principles live once and core consumers point to that source."""
    missing_operational_surfaces = [
        str(path.relative_to(REPO_ROOT))
        for path in CORE_OPERATIONAL_SURFACE_PATHS
        if not path.is_file()
    ]

    assert not missing_operational_surfaces, (
        "Expected the canonical Claude operational-consumer surfaces for spec-115 to exist, "
        f"but these are missing: {missing_operational_surfaces}."
    )

    candidates = _find_canonical_operational_sources()
    candidate_rels = [str(path.relative_to(REPO_ROOT)) for path in candidates]

    scattered_mentions: list[str] = []
    for path in CORE_OPERATIONAL_SURFACE_PATHS:
        mentions = _principle_mentions(_read_text(path))
        if mentions:
            scattered_mentions.append(f"{path.relative_to(REPO_ROOT)} -> {', '.join(mentions)}")

    assert len(candidates) == 1, (
        "Expected exactly one canonical operational-principles markdown artifact "
        "under .ai-engineering/ (excluding specs/state/instincts) that contains "
        "YAGNI, DRY, KISS, SOLID, clean architecture, and clean code. "
        f"Found {len(candidates)} candidate(s): {candidate_rels}. "
        "Current scattered mentions across core Claude surfaces: "
        f"{scattered_mentions}."
    )

    canonical_source = candidates[0]
    canonical_rel = canonical_source.relative_to(REPO_ROOT).as_posix()
    canonical_name = canonical_source.name

    missing_references: list[str] = []
    for path in CORE_OPERATIONAL_SURFACE_PATHS:
        text = _read_text(path)
        mentions = _principle_mentions(text)
        if not mentions:
            continue
        if canonical_rel not in text and canonical_name not in text:
            missing_references.append(
                f"{path.relative_to(REPO_ROOT)} mentions {', '.join(mentions)} "
                f"but does not reference {canonical_rel}"
            )

    assert not missing_references, (
        "Core implementation/review surfaces must consume the canonical operational-principles "
        "source instead of carrying free-floating principle guidance. Missing references: "
        f"{missing_references}."
    )
