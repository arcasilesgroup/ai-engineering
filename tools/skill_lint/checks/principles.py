"""principles checker — spec-131 S1 §10.x anchor citation rule.

Every SKILL.md ``## Workflow`` section must cite at least one
``§10.x`` engineering principle anchor from CANONICAL.md (§10.1 KISS
through §10.8 Hexagonal Architecture). Without the anchor the skill
silently applies a principle without surfacing which one, which
breaks the traceability spec-131 R-1.6 promises.

Posture (per R-1.6 / S1 scope): the checker runs in ADVISORY mode —
missing citation surfaces as MINOR, not MAJOR. Missing ``## Workflow``
section itself surfaces as MAJOR (structural failure). Subsequent
waves (S3 patch-ready `/ai-plan` + S6 SKILL audit) upgrade citation
absence to blocking once every shipped SKILL.md emits the
"Principles applied" line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_VALID_SEVERITIES = {"OK", "INFO", "MINOR", "MAJOR", "CRITICAL"}


@dataclass(frozen=True)
class RubricResult:
    """Outcome of running the principle-citation check against a skill."""

    rule_name: str
    severity: str
    reason: str

    def __post_init__(self) -> None:
        if self.severity not in _VALID_SEVERITIES:
            raise ValueError(f"severity {self.severity!r} not in {sorted(_VALID_SEVERITIES)}")


# ── §10.x anchor regex (D-131-04 / CANONICAL.md §10) ─────────────────────
# Matches §10.1 through §10.8 with or without the section sign. The
# anchor token must be a standalone reference: ``§10.5``, ``10.5``,
# ``§10.5 TDD``, ``10.4 DRY``. The fractional pattern (e.g. ``10.0`` /
# ``100.5``) does not match. Word boundary on each side prevents
# overzealous matches like ``v10.5`` (semver-style) — although in
# practice SKILL.md bodies do not embed semver inside ## Workflow.
PRINCIPLE_RE: re.Pattern[str] = re.compile(r"§?10\.[1-8](?!\d)")


# ── Section regex (level-2 heading match) ────────────────────────────────
# Capture the contents of `## Workflow` up to the next level-2 heading
# (or end of file). Body matches lazily so multi-section SKILL files
# do not bleed Workflow content into Examples / Integration. Leading
# whitespace tolerated to absorb fixture-side indentation quirks
# (textwrap.dedent f-string interpolation) without weakening the
# section-boundary contract.
_WORKFLOW_RE = re.compile(
    r"^[ \t]*##\s+Workflow\b[^\n]*\n(?P<body>.*?)(?=^[ \t]*##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)


# ───────────────────────────── single-skill check ─────────────────────────


def check_principle_citation(skill_md: Path) -> RubricResult:
    """Run the principle-citation rule against a single SKILL.md.

    Returns one of:

    * ``OK`` — `## Workflow` exists and contains at least one §10.x
      anchor.
    * ``MINOR`` — `## Workflow` exists but cites no §10.x anchor
      (advisory mode per R-1.6).
    * ``MAJOR`` — `## Workflow` section is missing entirely
      (structural failure; SKILL.md layout contract — spec-127 — already
      requires Workflow).
    * ``CRITICAL`` — SKILL.md file is unreadable / missing.
    """
    if not skill_md.is_file():
        return RubricResult(
            "principle_citation",
            "CRITICAL",
            f"SKILL.md not found at {skill_md}",
        )
    text = skill_md.read_text(encoding="utf-8")
    match = _WORKFLOW_RE.search(text)
    if not match:
        return RubricResult(
            "principle_citation",
            "MAJOR",
            "## Workflow section missing — spec-127 layout contract violated",
        )
    body = match.group("body") or ""
    if PRINCIPLE_RE.search(body):
        return RubricResult(
            "principle_citation",
            "OK",
            "## Workflow cites at least one §10.x principle anchor",
        )
    return RubricResult(
        "principle_citation",
        "MINOR",
        "## Workflow lacks §10.x principle citation (advisory)",
    )


# ───────────────────────────── driver ─────────────────────────────────────


def check_principles_citations(skills_root: Path) -> list[tuple[Path, RubricResult]]:
    """Walk every `<skills_root>/ai-*/SKILL.md` and run the citation check.

    Returns ``[(skill_md_path, result), ...]`` sorted by path so CI
    output stays stable. Raises ``FileNotFoundError`` when
    ``skills_root`` does not exist (matches the
    ``check_all_skills`` contract in ``no_nested_refs.py``).
    """
    if not skills_root.is_dir():
        raise FileNotFoundError(f"skills root {skills_root} does not exist")
    results: list[tuple[Path, RubricResult]] = []
    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        results.append((skill_md, check_principle_citation(skill_md)))
    return results
