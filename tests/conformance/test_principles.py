"""principles citation conformance — spec-131 S1 contract (sub-001 T-1.3).

The principles checker (``tools/skill_lint/checks/principles.py``) verifies
that every SKILL.md ``## Workflow`` section cites at least one §10.x
engineering principle anchor from CANONICAL.md (§10.1 KISS through
§10.8 Hexagonal Architecture).

This is the TDD RED partner of T-1.10. **DO NOT MODIFY THIS FILE during
T-1.10 GREEN.** The checker implementation must change to satisfy these
assertions.

Posture (per R-1.6): the checker runs in ADVISORY mode for sub-001 —
missing citation surfaces as MINOR, not MAJOR. Subsequent waves (S3
patch-ready /ai-plan + S6 SKILL audit) upgrade to blocking once every
shipped SKILL.md emits the "Principles applied" line.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixture helper — synthetic skill body.
# ---------------------------------------------------------------------------


def _write_skill(skill_dir: Path, *, body: str, name: str = "demo") -> Path:
    """Write a minimal SKILL.md fixture with custom body."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / "SKILL.md"
    md.write_text(
        textwrap.dedent(
            f"""\
            ---
            name: {name}
            description: synthetic principles fixture
            ---

            # Skill

            {body}
            """
        ),
        encoding="utf-8",
    )
    return md


# ---------------------------------------------------------------------------
# Check 1 — citation present (positive cases).
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_citation_present_with_section_anchor(tmp_path: Path) -> None:
    """OK when ## Workflow cites §10.5 explicitly."""
    skill_md = _write_skill(
        tmp_path / "ai-demo",
        body=textwrap.dedent(
            """\
            ## Workflow

            1. Apply §10.5 TDD: write failing test first.
            2. Implement.
            """
        ),
    )
    from skill_lint.checks.principles import check_principle_citation

    result = check_principle_citation(skill_md)
    assert result.severity == "OK", result.reason


@pytest.mark.unit
def test_citation_present_with_numeric_only_anchor(tmp_path: Path) -> None:
    """OK when ## Workflow cites 10.4 without the § sigil."""
    skill_md = _write_skill(
        tmp_path / "ai-demo",
        body=textwrap.dedent(
            """\
            ## Workflow

            1. 10.4 DRY: extract the shared helper.
            """
        ),
    )
    from skill_lint.checks.principles import check_principle_citation

    result = check_principle_citation(skill_md)
    assert result.severity == "OK", result.reason


@pytest.mark.unit
@pytest.mark.parametrize("anchor", ["§10.1", "§10.2", "§10.3", "§10.6", "§10.7", "§10.8"])
def test_citation_accepts_each_principle_anchor(tmp_path: Path, anchor: str) -> None:
    """OK for every §10.1 through §10.8 anchor."""
    skill_md = _write_skill(
        tmp_path / "ai-demo",
        body=textwrap.dedent(
            f"""\
            ## Workflow

            1. Apply {anchor}: keep it sharp.
            """
        ),
    )
    from skill_lint.checks.principles import check_principle_citation

    result = check_principle_citation(skill_md)
    assert result.severity == "OK", f"{anchor}: {result.reason}"


@pytest.mark.unit
def test_citation_counts_multiple_anchors_once(tmp_path: Path) -> None:
    """OK when multiple anchors appear; severity stays OK (single pass)."""
    skill_md = _write_skill(
        tmp_path / "ai-demo",
        body=textwrap.dedent(
            """\
            ## Workflow

            1. §10.5 TDD: RED first.
            2. §10.7 Clean Code: short functions.
            """
        ),
    )
    from skill_lint.checks.principles import check_principle_citation

    result = check_principle_citation(skill_md)
    assert result.severity == "OK", result.reason


# ---------------------------------------------------------------------------
# Check 2 — citation missing (advisory MINOR).
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_citation_missing_when_workflow_has_no_anchor(tmp_path: Path) -> None:
    """MINOR when ## Workflow exists but cites only prose names."""
    skill_md = _write_skill(
        tmp_path / "ai-demo",
        body=textwrap.dedent(
            """\
            ## Workflow

            1. Apply the KISS principle: prefer the simplest code.
            2. Honour SOLID principles.
            """
        ),
    )
    from skill_lint.checks.principles import check_principle_citation

    result = check_principle_citation(skill_md)
    assert result.severity == "MINOR", (
        f"prose-only mention without §10.x anchor must be MINOR advisory; got {result.severity}"
    )


@pytest.mark.unit
def test_citation_missing_when_workflow_is_empty(tmp_path: Path) -> None:
    """MINOR when ## Workflow has body but no §10.x anchor."""
    skill_md = _write_skill(
        tmp_path / "ai-demo",
        body=textwrap.dedent(
            """\
            ## Workflow

            Do the thing.
            """
        ),
    )
    from skill_lint.checks.principles import check_principle_citation

    result = check_principle_citation(skill_md)
    assert result.severity == "MINOR", result.reason


@pytest.mark.unit
def test_anchor_outside_workflow_section_does_not_count(tmp_path: Path) -> None:
    """MINOR when §10.x appears only in Examples section, not Workflow."""
    skill_md = _write_skill(
        tmp_path / "ai-demo",
        body=textwrap.dedent(
            """\
            ## Workflow

            Do the thing.

            ## Examples

            Example shows §10.5 TDD usage.
            """
        ),
    )
    from skill_lint.checks.principles import check_principle_citation

    result = check_principle_citation(skill_md)
    assert result.severity == "MINOR", (
        f"§10.x outside ## Workflow must not satisfy the rule; got {result.severity}"
    )


# ---------------------------------------------------------------------------
# Check 3 — workflow section missing (MAJOR).
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_workflow_section_missing_is_major(tmp_path: Path) -> None:
    """MAJOR when SKILL.md has no ## Workflow section at all."""
    skill_md = _write_skill(
        tmp_path / "ai-demo",
        body=textwrap.dedent(
            """\
            ## Quick start

            /ai-demo do-thing

            ## Procedure

            1. Apply §10.5 TDD here.
            """
        ),
    )
    from skill_lint.checks.principles import check_principle_citation

    result = check_principle_citation(skill_md)
    assert result.severity == "MAJOR", (
        f"missing ## Workflow is a structural failure; got {result.severity}"
    )


# ---------------------------------------------------------------------------
# Anchor pattern unit tests.
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "anchor,expected",
    [
        ("§10.1", True),
        ("§10.2", True),
        ("§10.5 TDD", True),
        ("10.4", True),
        ("10.8 Hexagonal", True),
        ("Section 10.5", True),
        ("10.0", False),
        ("10.9", False),
        ("100.5", False),
        ("§10", False),
        ("KISS principle", False),
    ],
)
def test_principle_regex_matches(anchor: str, expected: bool) -> None:
    """The exported regex matches §10.1-§10.8 anchors and rejects the rest."""
    from skill_lint.checks.principles import PRINCIPLE_RE

    matched = bool(PRINCIPLE_RE.search(anchor))
    assert matched is expected, f"{anchor!r}: expected match={expected}, got {matched}"


# ---------------------------------------------------------------------------
# Driver — check_principles_citations walks every SKILL.md.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_driver_walks_every_skill(tmp_path: Path) -> None:
    """Driver returns one (Path, RubricResult) per SKILL.md under skills_root."""
    skills_root = tmp_path / "skills"
    _write_skill(
        skills_root / "ai-foo",
        body="## Workflow\n\n1. Apply §10.5 TDD.\n",
        name="foo",
    )
    _write_skill(
        skills_root / "ai-bar",
        body="## Workflow\n\nDo the thing.\n",
        name="bar",
    )
    from skill_lint.checks.principles import check_principles_citations

    results = check_principles_citations(skills_root)
    assert len(results) == 2, f"expected 2 skill results, got {len(results)}"
    by_name = {p.parent.name: r for p, r in results}
    assert by_name["ai-foo"].severity == "OK"
    assert by_name["ai-bar"].severity == "MINOR"


@pytest.mark.unit
def test_driver_handles_missing_root(tmp_path: Path) -> None:
    """Driver raises a clear error when skills_root does not exist."""
    from skill_lint.checks.principles import check_principles_citations

    missing = tmp_path / "does-not-exist"
    with pytest.raises(FileNotFoundError):
        check_principles_citations(missing)
