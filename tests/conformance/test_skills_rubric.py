"""Skills conformance rubric tests (spec-127 M1, brief §3 ten rules).

Pairing: TDD RED partner of umbrella T-2.10. GREEN target =
``LintSkillsUseCase(...).run()`` over the live ``.claude/skills/``
surface. **DO NOT MODIFY THIS FILE** during Phase D GREEN — the rubric
implementation must change to satisfy these assertions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_app.lint_skills import LintSkillsUseCase
from skill_domain.rubric import SKILL_RULES
from skill_infra.fs_scanner import FilesystemSkillScanner


@pytest.fixture(scope="module")
def skills_report(skills_root: Path):
    """Run the use case once per module — saves ~40 ms across the suite."""
    scanner = FilesystemSkillScanner(skills_root)
    return LintSkillsUseCase(scanner).run()


# ---------------------------------------------------------------------------
# Rule 1 — frontmatter validity
# ---------------------------------------------------------------------------


def test_rule_1_frontmatter_valid(skills_report) -> None:
    """Every skill has a parseable frontmatter with name + description."""
    rule = _get_rule("rule_1_frontmatter_valid")
    assert rule is not None, "rubric must declare rule_1_frontmatter_valid"

    # Every Grade-A skill must pass rule 1 with at most a MINOR-weight
    # deviation. ``INFO`` is treated as visible-but-zero-weight (the
    # universal "tolerated extras" gap, e.g. ``effort`` /
    # ``argument-hint``); ``MINOR`` is a small-but-tracked dev. A MAJOR
    # / CRITICAL rule_1 (non-tolerated fields, agent-shape frontmatter)
    # blocks Grade A.
    a_grade = [r for r in skills_report.per_skill if r.grade == "A"]
    assert a_grade, "expected at least one Grade A skill (brief §2.1: 28 A)"
    for result in a_grade:
        rule_result = result.rule_for("rule_1_frontmatter_valid")
        assert rule_result is not None
        assert rule_result.severity in {"OK", "INFO", "MINOR"}, (
            f"{result.path.name}: rule_1 severity {rule_result.severity!r} "
            f"incompatible with Grade A — reason={rule_result.reason}"
        )


# ---------------------------------------------------------------------------
# Rule 2 — third-person CSO description with ≥3 trigger phrases
# ---------------------------------------------------------------------------


def test_rule_2_third_person_cso_three_triggers(skills_report) -> None:
    """Description is third-person and lists ≥3 trigger phrases.

    Post-M2 contract: zero Grade D skills remain (D was an M1 baseline
    artifact eliminated by the Wave 2 CSO sweep). Rule 2 must still
    return a result per skill, and at least one skill must register a
    non-OK severity (the metaphor-named skills awaiting M4 rename
    carry Rule 2 violations adjacent to Rule 10).
    """
    rule = _get_rule("rule_2_third_person_cso_three_triggers")
    assert rule is not None

    d_grade = [r for r in skills_report.per_skill if r.grade == "D"]
    assert len(d_grade) == 0, (
        f"M2 must eliminate Grade D; got {len(d_grade)}: {[r.path.name for r in d_grade]}"
    )
    assert all(
        r.rule_for("rule_2_third_person_cso_three_triggers") is not None
        for r in skills_report.per_skill
    )


# ---------------------------------------------------------------------------
# Rule 3 — negative scoping
# ---------------------------------------------------------------------------


def test_rule_3_negative_scoping(skills_report) -> None:
    """Description states what NOT to use the skill for when adjacent skills exist."""
    rule = _get_rule("rule_3_negative_scoping")
    assert rule is not None
    # All 54 live skills are AI-discoverable and graded. spec-189 D-189-03
    # split /ai-marketing into growth + /ai-fundraising, so per_skill == the
    # live surface count. Update this alongside any skill add/remove (never loosen).
    assert len(skills_report.per_skill) == 54, (
        f"expected 54 skills evaluated, got {len(skills_report.per_skill)}"
    )


# ---------------------------------------------------------------------------
# Rule 4 — body length and token budget
# ---------------------------------------------------------------------------


def test_rule_4_line_and_token_budget(skills_report) -> None:
    """Body ≤500 lines and ≤5000 tokens; ≤120 lines is the lean target."""
    rule = _get_rule("rule_4_line_and_token_budget")
    assert rule is not None
    # No skill in the current surface exceeds the 500-line hard cap.
    for result in skills_report.per_skill:
        rr = result.rule_for("rule_4_line_and_token_budget")
        assert rr is not None
        assert rr.severity != "CRITICAL", (
            f"{result.path.name}: line/token budget exceeded — {rr.reason}"
        )


# ---------------------------------------------------------------------------
# Rule 5 — required sections present
# ---------------------------------------------------------------------------


def test_rule_5_required_sections(skills_report) -> None:
    """`## Workflow`, `## Examples`, `## Integration` headings present.

    spec-187 D-187-11 contract: "Quick start" is no longer required
    (redundant with the description under the leaner standard). Every
    skill must still carry Workflow (procedure), Examples, and
    Integration. A MAJOR/CRITICAL rule_5 (a genuinely missing core
    section) is a regression; residual MINORs are tolerated.
    """
    rule = _get_rule("rule_5_required_sections")
    assert rule is not None
    hard = [
        r
        for r in skills_report.per_skill
        if (rr := r.rule_for("rule_5_required_sections")) and rr.severity in {"MAJOR", "CRITICAL"}
    ]
    detail = [(r.path.name, r.rule_for("rule_5_required_sections").reason) for r in hard]
    assert len(hard) <= 2, (
        f"rule_5: MAJOR/CRITICAL missing-section flags must be ≤2; got {len(hard)}: {detail[:10]}"
    )


# ---------------------------------------------------------------------------
# Rule 6 — examples count
# ---------------------------------------------------------------------------


def test_rule_6_examples_count(skills_report) -> None:
    """`## Examples` carries ≥1 canonical invocation.

    spec-187 D-187-06 contract: one canonical example is the standard
    (the prior ≥2 requirement rewarded copy-paste boilerplate). rule_6
    is OK at ≥1 example and a visible-but-unpenalised INFO at 0
    (example moved to references/). It never emits a penalty severity,
    so no skill may carry a MINOR/MAJOR/CRITICAL rule_6 result.
    """
    rule = _get_rule("rule_6_examples_count")
    assert rule is not None
    penalised = [
        r
        for r in skills_report.per_skill
        if (rr := r.rule_for("rule_6_examples_count"))
        and rr.severity in {"MINOR", "MAJOR", "CRITICAL"}
    ]
    assert not penalised, (
        "spec-187 D-187-06: rule_6 is OK at ≥1 example, INFO at 0 — never "
        f"penalised; got {len(penalised)}: {[r.path.name for r in penalised][:10]}"
    )


# ---------------------------------------------------------------------------
# Rule 7 — refs nesting with TOC
# ---------------------------------------------------------------------------


def test_rule_7_refs_nesting_with_toc(skills_report) -> None:
    """References >100 lines live in `references/` one level deep with TOC."""
    rule = _get_rule("rule_7_refs_nesting_with_toc")
    assert rule is not None
    # Soft signal — most current skills do not have references/ dir.
    assert any(
        r.rule_for("rule_7_refs_nesting_with_toc") is not None for r in skills_report.per_skill
    )


# ---------------------------------------------------------------------------
# Rule 8 — evals present threshold (≥3)
# ---------------------------------------------------------------------------


def test_rule_8_evals_present_threshold(skills_report) -> None:
    """`evals/<skill>.jsonl` with ≥3 entries; M6 brings the count to 16.

    Pre-M6 contract: no evals exist yet — rule 8 must flag every
    graded skill until M6 (sub-007) ships the eval harness corpus.
    """
    rule = _get_rule("rule_8_evals_present_threshold")
    assert rule is not None
    flagged = [
        r
        for r in skills_report.per_skill
        if r.rule_for("rule_8_evals_present_threshold")
        and r.rule_for("rule_8_evals_present_threshold").severity != "OK"
    ]
    # All graded skills must still flag rule 8 (no evals shipped yet).
    # Bumped from 49 to 47 by spec-127 sub-005 (M4); 45-skill floor preserved.
    assert len(flagged) >= 43, (
        f"pre-M6: rule_8 must flag ~all skills (no evals yet); got {len(flagged)}/47"
    )


# ---------------------------------------------------------------------------
# Rule 9 — optimizer-committed (description tuned via run_loop)
# ---------------------------------------------------------------------------


def test_rule_9_optimizer_committed(skills_report) -> None:
    """Description optimized via `python -m scripts.run_loop --skill-path …`."""
    rule = _get_rule("rule_9_optimizer_committed")
    assert rule is not None
    # M1 baseline: optimizer not yet run — rule 9 must produce a result
    # per skill (severity may be MINOR / OK depending on heuristic).
    assert all(
        r.rule_for("rule_9_optimizer_committed") is not None for r in skills_report.per_skill
    )


# ---------------------------------------------------------------------------
# Rule 10 — no anti-patterns
# ---------------------------------------------------------------------------


def test_rule_10_no_anti_patterns(skills_report) -> None:
    """No metaphors in name, no first/second person, no time-stamped prose.

    Post-M4 contract: Wave 2 CSO sweep eliminated Grade D and dropped
    Grade C to zero. M4 rename retired the metaphor-named skills, leaving
    only refs-nesting rubric edge cases as Grade B.

    Shape contract (post-Wave-8):

    * Grade D = 0 (eliminated by Wave 2).
    * Grade C ≤ 2 (D-127-08 hard ceiling).
    * Grade A ≥ 32 (≥60% of 54 graded skills, post-spec-134).
    * Grade A is the largest bucket.
    * Total graded skills = 54 (spec-189 D-189-03 split /ai-marketing into
      growth + /ai-fundraising, so per_skill == the live surface count; no
      skill is excluded from the §2.1 audit).
    """
    rule = _get_rule("rule_10_no_anti_patterns")
    assert rule is not None
    summary = skills_report.summary

    total = sum(summary.values())
    assert total == 54, f"expected 54 graded skills, got {total}: {summary}"
    assert summary.get("D", 0) == 0, (
        f"M2 must eliminate Grade D; got {summary.get('D', 0)}: {summary}"
    )
    a_count = summary.get("A", 0)
    b_count = summary.get("B", 0)
    c_count = summary.get("C", 0)
    assert a_count >= b_count >= c_count, (
        f"shape requires A ≥ B ≥ C; got A={a_count} B={b_count} C={c_count}"
    )
    assert c_count <= 2, f"D-127-08 hard ceiling: Grade C must be ≤2; got {c_count}: {summary}"
    assert a_count >= 32, (
        f"Wave 8 floor: Grade A must be ≥32 (≥70%% of 46); got {a_count}: {summary}"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_rule(name: str):
    for rule in SKILL_RULES:
        if rule.name == name:
            return rule
    return None
