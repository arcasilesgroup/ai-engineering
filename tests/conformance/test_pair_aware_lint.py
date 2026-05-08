"""Pair-aware lint conformance — brief §22.5 contract.

Brief §22.5 ships the following pair-aware checks (extending
``tools/skill_lint/``):

1. Phase-narrative duplication: ≥3 consecutive headings shared between
   skill+agent → MAJOR.
2. Dispatch threshold present: skill body must contain a numeric
   threshold rule.
3. Agent links back to skill (``skills/<slug>/SKILL.md`` reference).
4. Length caps from §22.3 table.

Each test below pins one rule against synthetic markdown fixtures so
the checker behaviour is independent of the live skill surface.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from skill_lint.checks.pair_aware import (
    LENGTH_CAPS,
    check_agent_links_back,
    check_dispatch_threshold,
    check_length_caps,
    check_no_phase_duplication,
    check_pair_consistency,
)

# ---------------------------------------------------------------------------
# Fixtures: synthetic skill+agent dirs.
# ---------------------------------------------------------------------------


def _write_skill(skill_dir: Path, body: str, name: str = "demo") -> Path:
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / "SKILL.md"
    md.write_text(
        textwrap.dedent(
            f"""\
            ---
            name: {name}
            description: synthetic skill fixture
            ---

            {body}
            """
        ),
        encoding="utf-8",
    )
    return md


def _write_agent(agents_root: Path, name: str, body: str) -> Path:
    agents_root.mkdir(parents=True, exist_ok=True)
    md = agents_root / f"{name}.md"
    md.write_text(
        textwrap.dedent(
            f"""\
            ---
            name: {name}
            description: synthetic agent fixture
            ---

            {body}
            """
        ),
        encoding="utf-8",
    )
    return md


# ---------------------------------------------------------------------------
# Check 1 — phase-narrative duplication
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase_duplication_flagged_when_three_headings_overlap() -> None:
    """3 consecutive matching headings in both bodies → MAJOR."""
    skill_body = textwrap.dedent(
        """\
        ## Overview
        text
        ## Process
        text
        ### Step 1
        text
        ### Step 2
        text
        ### Step 3
        text
        """
    )
    agent_body = textwrap.dedent(
        """\
        ## Identity
        ip
        ### Step 1
        x
        ### Step 2
        x
        ### Step 3
        x
        """
    )
    result = check_no_phase_duplication(skill_body, agent_body)
    assert result.severity == "MAJOR"
    assert result.rule_name == "pair_no_phase_duplication"


@pytest.mark.unit
def test_phase_duplication_ok_when_only_two_match() -> None:
    skill_body = textwrap.dedent(
        """\
        ## Process
        ### Step 1
        ### Step 2
        ### Step 3
        """
    )
    agent_body = textwrap.dedent(
        """\
        ## Identity
        ## Capabilities
        ### Different
        """
    )
    result = check_no_phase_duplication(skill_body, agent_body)
    assert result.severity == "OK"


# ---------------------------------------------------------------------------
# Check 2 — dispatch threshold present
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_dispatch_threshold_present_passes() -> None:
    body = textwrap.dedent(
        """\
        ## When to Use

        Dispatch when files > 50 or sub_specs >= 5.
        """
    )
    result = check_dispatch_threshold(body)
    assert result.severity == "OK"


@pytest.mark.unit
def test_dispatch_threshold_missing_flagged() -> None:
    body = "## When to Use\n\nDispatch only on big change.\n"
    result = check_dispatch_threshold(body)
    assert result.severity == "MAJOR"


@pytest.mark.unit
def test_dispatch_threshold_unicode_inequality_recognised() -> None:
    body = "## Dispatch\n\nIf score ≥ 3 then dispatch.\n"
    result = check_dispatch_threshold(body)
    assert result.severity == "OK"


# ---------------------------------------------------------------------------
# Check 3 — agent links back to skill
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_agent_link_back_present() -> None:
    body = "## Identity\n\nSee: skills/ai-autopilot/SKILL.md for procedure.\n"
    result = check_agent_links_back(body, "ai-autopilot")
    assert result.severity == "OK"


@pytest.mark.unit
def test_agent_link_back_missing_flagged() -> None:
    body = "## Identity\n\nNo link here.\n"
    result = check_agent_links_back(body, "ai-autopilot")
    assert result.severity == "MINOR"


@pytest.mark.unit
def test_agent_link_back_wrong_slug_flagged() -> None:
    body = "See: skills/ai-other/SKILL.md\n"
    result = check_agent_links_back(body, "ai-autopilot")
    assert result.severity == "MINOR"


# ---------------------------------------------------------------------------
# Check 4 — length caps from §22.3
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_length_caps_within_limits_passes() -> None:
    skill_cap, agent_cap = LENGTH_CAPS["ai-plan"]
    result = check_length_caps("ai-plan", skill_cap, agent_cap)
    assert result.severity == "OK"


@pytest.mark.unit
def test_length_caps_minor_when_over_by_under_10pct() -> None:
    """ai-plan caps: skill ≤100, agent ≤50. 105/52 = small overshoot."""
    result = check_length_caps("ai-plan", 105, 52)
    assert result.severity == "MINOR"


@pytest.mark.unit
def test_length_caps_major_when_over_by_more_than_10pct() -> None:
    """ai-autopilot caps: 120/60. Skill at 200 = major overshoot."""
    result = check_length_caps("ai-autopilot", 200, 60)
    assert result.severity == "MAJOR"


@pytest.mark.unit
def test_length_caps_info_when_no_cap_configured() -> None:
    """A pair without a brief §22.3 cap surfaces INFO, not MAJOR."""
    result = check_length_caps("ai-other-pair", 500, 500)
    assert result.severity == "INFO"


# ---------------------------------------------------------------------------
# Driver — full pair walk
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_check_pair_consistency_yields_results_per_pair(tmp_path: Path) -> None:
    """The driver returns one result per check per paired surface."""
    skills_root = tmp_path / "skills"
    agents_root = tmp_path / "agents"

    # Two paired surfaces, one with no agent (must be skipped).
    _write_skill(
        skills_root / "demo",
        body="## Process\n\nDispatch when files > 50.\n",
        name="demo",
    )
    _write_agent(
        agents_root,
        "demo",
        body="## Identity\n\nSee: skills/demo/SKILL.md.\n",
    )
    _write_skill(skills_root / "lonely", body="## Process\n", name="lonely")
    # No agents/lonely.md → must be skipped.

    results = check_pair_consistency(skills_root, agents_root)
    slugs = {slug for slug, _ in results}
    # Only the paired demo surfaces; lonely was skipped.
    assert slugs == {"demo"}
    # Four checks per pair = 4 results for the demo pair.
    rules = {r.rule_name for _, r in results}
    assert rules == {
        "pair_no_phase_duplication",
        "pair_dispatch_threshold",
        "pair_agent_links_back",
        "pair_length_caps",
    }
