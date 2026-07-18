"""value_block adoption conformance — spec-186 Client-Value Lens contract.

The value_block checker (``tools/skill_lint/checks/value_block.py``) verifies
that each of the five canonical chain skills (``ai-brainstorm``, ``ai-plan``,
``ai-build``, ``ai-autopilot``, ``ai-pr``) adopts the Client-Value Lens by
citing ``value-lens.md`` in its SKILL.md or any file under handlers/.

Posture: BLOCKING. A chain skill omitting the citation surfaces as CRITICAL
and drives the CLI exit code to 1 (D-186-06).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_VALUE_LENS_DOC = _REPO_ROOT / ".ai-engineering" / "reference" / "value-lens.md"
_SKILLS_ROOT = _REPO_ROOT / ".claude" / "skills"


# ---------------------------------------------------------------------------
# Fixture helper — synthetic skill directory (mirrors test_principles.py).
# ---------------------------------------------------------------------------


def _write_skill(skill_dir: Path, *, body: str, name: str = "demo") -> Path:
    """Write a minimal SKILL.md fixture with a custom body."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / "SKILL.md"
    md.write_text(
        textwrap.dedent(
            f"""\
            ---
            name: {name}
            description: synthetic value_block fixture
            ---

            # Skill

            {body}
            """
        ),
        encoding="utf-8",
    )
    return md


# ---------------------------------------------------------------------------
# Contract 1 — the value-lens.md reference doc exists and is well-formed.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_value_lens_reference_exists() -> None:
    """The canonical value-lens.md reference doc ships in the repo."""
    assert _VALUE_LENS_DOC.is_file(), f"missing reference doc at {_VALUE_LENS_DOC}"


@pytest.mark.unit
@pytest.mark.parametrize(
    "field_label",
    [
        "Bottom line",
        "Why it matters",
        "What's done",
        "Risk",
        "Next",
        "Details",
    ],
)
def test_value_lens_reference_has_six_fields(field_label: str) -> None:
    """value-lens.md documents all six canonical value-block field labels."""
    text = _VALUE_LENS_DOC.read_text(encoding="utf-8")
    assert field_label in text, f"value-lens.md omits field label {field_label!r}"


@pytest.mark.unit
def test_value_lens_reference_has_carveout_section() -> None:
    """value-lens.md carries the load-bearing carve-out section."""
    text = _VALUE_LENS_DOC.read_text(encoding="utf-8")
    assert "Carve-out" in text, "value-lens.md omits the carve-out section"


# ---------------------------------------------------------------------------
# Contract 2 — CHAIN_SKILLS is exactly the five canonical chain skills.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_chain_skills_tuple_is_exactly_five() -> None:
    """CHAIN_SKILLS is exactly the five chain skills, in order."""
    from skill_lint.checks.value_block import CHAIN_SKILLS

    assert CHAIN_SKILLS == (
        "ai-brainstorm",
        "ai-plan",
        "ai-build",
        "ai-autopilot",
        "ai-pr",
    )


# ---------------------------------------------------------------------------
# Contract 3 — single-skill check: chain vs non-chain, cited vs not.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_chain_skill_without_citation_is_critical(tmp_path: Path) -> None:
    """A chain skill dir lacking value-lens.md surfaces CRITICAL."""
    skill_dir = tmp_path / "ai-plan"
    _write_skill(
        skill_dir,
        body="## Workflow\n\n1. Do the thing.\n",
        name="plan",
    )
    from skill_lint.checks.value_block import check_value_block_citation

    result = check_value_block_citation(skill_dir)
    assert result.severity == "CRITICAL", result.reason


@pytest.mark.unit
def test_chain_skill_with_citation_in_skill_md_is_ok(tmp_path: Path) -> None:
    """A chain skill citing value-lens.md in SKILL.md surfaces OK."""
    skill_dir = tmp_path / "ai-plan"
    _write_skill(
        skill_dir,
        body="## Workflow\n\n1. Render the report per reference/value-lens.md.\n",
        name="plan",
    )
    from skill_lint.checks.value_block import check_value_block_citation

    result = check_value_block_citation(skill_dir)
    assert result.severity == "OK", result.reason


@pytest.mark.unit
def test_chain_skill_with_citation_in_handler_is_ok(tmp_path: Path) -> None:
    """A chain skill citing value-lens.md in a handlers/*.md surfaces OK."""
    skill_dir = tmp_path / "ai-pr"
    _write_skill(
        skill_dir,
        body="## Workflow\n\n1. Do the thing.\n",
        name="pr",
    )
    handlers = skill_dir / "handlers"
    handlers.mkdir(parents=True, exist_ok=True)
    (handlers / "report.md").write_text(
        "Render the sponsor summary via reference/value-lens.md.\n",
        encoding="utf-8",
    )
    from skill_lint.checks.value_block import check_value_block_citation

    result = check_value_block_citation(skill_dir)
    assert result.severity == "OK", result.reason


@pytest.mark.unit
def test_non_chain_skill_without_citation_is_not_critical(tmp_path: Path) -> None:
    """A non-chain skill lacking the citation is out of scope (never CRITICAL)."""
    skill_dir = tmp_path / "ai-foo"
    _write_skill(
        skill_dir,
        body="## Workflow\n\n1. Do the thing.\n",
        name="foo",
    )
    from skill_lint.checks.value_block import check_value_block_citation

    result = check_value_block_citation(skill_dir)
    assert result.severity != "CRITICAL", result.reason


# ---------------------------------------------------------------------------
# Contract 4 — driver walks ai-*/ and raises on a missing root.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_driver_walks_chain_and_non_chain(tmp_path: Path) -> None:
    """Driver returns one (Path, RubricResult) per ai-*/ dir, sorted."""
    skills_root = tmp_path / "skills"
    _write_skill(
        skills_root / "ai-plan",
        body="## Workflow\n\n1. Do the thing.\n",
        name="plan",
    )
    _write_skill(
        skills_root / "ai-foo",
        body="## Workflow\n\n1. Do the thing.\n",
        name="foo",
    )
    from skill_lint.checks.value_block import check_value_block_citations

    results = check_value_block_citations(skills_root)
    by_name = {p.name: r for p, r in results}
    assert by_name["ai-plan"].severity == "CRITICAL"
    assert by_name["ai-foo"].severity != "CRITICAL"


@pytest.mark.unit
def test_driver_handles_missing_root(tmp_path: Path) -> None:
    """Driver raises a clear error when skills_root does not exist."""
    from skill_lint.checks.value_block import check_value_block_citations

    missing = tmp_path / "does-not-exist"
    with pytest.raises(FileNotFoundError):
        check_value_block_citations(missing)


# ---------------------------------------------------------------------------
# Contract 5 — CLI _exit_code treats a value_block CRITICAL as blocking.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_exit_code_blocks_on_value_block_critical() -> None:
    """_exit_code returns 1 when any chain result is CRITICAL, 0 otherwise."""
    from skill_lint.checks.value_block import RubricResult
    from skill_lint.cli import _exit_code

    ok = (Path("ai-plan"), RubricResult("value_block_citation", "OK", "ok"))
    crit = (
        Path("ai-plan"),
        RubricResult("value_block_citation", "CRITICAL", "omits citation"),
    )

    assert _exit_code({}, value_block_results=[crit]) == 1
    assert _exit_code({}, value_block_results=[ok]) == 0


# ---------------------------------------------------------------------------
# Contract 6 — REAL-REPO enforcement (spec-186 D-186-06).
#
# NOTE: this test is the enforcement teeth. It may RED until the five chain
# skills under .claude/skills/ adopt the value-lens.md citation (a sibling
# agent lands those edits concurrently). Keep it — it goes GREEN once the
# skills adopt.
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "chain_skill",
    ["ai-brainstorm", "ai-plan", "ai-build", "ai-autopilot", "ai-pr"],
)
def test_real_repo_chain_skill_cites_value_lens(chain_skill: str) -> None:
    """Each of the five real chain skills cites value-lens.md (enforcement)."""
    from skill_lint.checks.value_block import check_value_block_citation

    skill_dir = _SKILLS_ROOT / chain_skill
    assert skill_dir.is_dir(), f"chain skill dir missing: {skill_dir}"
    result = check_value_block_citation(skill_dir)
    assert result.severity == "OK", result.reason
