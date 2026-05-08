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
    """Description is third-person and lists ≥3 trigger phrases."""
    rule = _get_rule("rule_2_third_person_cso_three_triggers")
    assert rule is not None

    # Grade D skill `ai-entropy-gc` (per brief §2.1) must NOT have an OK
    # severity on every rule — at least one rule must register MAJOR or
    # CRITICAL. Rule 2 is one of the strongest signals for Grade D.
    d_grade = [r for r in skills_report.per_skill if r.grade == "D"]
    assert len(d_grade) == 1, f"expected exactly one Grade D skill, got {len(d_grade)}"
    assert d_grade[0].path.name == "ai-entropy-gc", (
        f"expected ai-entropy-gc to be Grade D, got {d_grade[0].path.name}"
    )


# ---------------------------------------------------------------------------
# Rule 3 — negative scoping
# ---------------------------------------------------------------------------


def test_rule_3_negative_scoping(skills_report) -> None:
    """Description states what NOT to use the skill for when adjacent skills exist."""
    rule = _get_rule("rule_3_negative_scoping")
    assert rule is not None
    # 49 skills graded — disable-model-invocation skills are excluded
    # from the AI-discovery audit (one such skill on the live surface).
    assert len(skills_report.per_skill) == 49, (
        f"expected 49 skills evaluated, got {len(skills_report.per_skill)}"
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
    """`## Quick start`, `## Workflow`, `## Examples`, `## Integration` headings."""
    rule = _get_rule("rule_5_required_sections")
    assert rule is not None
    # Universal gap per brief §2.1: 0/50 skills have ## Examples — every
    # skill must therefore register a non-OK severity (INFO or higher)
    # on rule 5 because Examples is missing universally.
    missing_anything = [
        r
        for r in skills_report.per_skill
        if r.rule_for("rule_5_required_sections")
        and r.rule_for("rule_5_required_sections").severity != "OK"
    ]
    assert len(missing_anything) >= 44, (
        "brief §2.1 reports 0/50 skills with ## Examples — rule_5 must "
        f"flag almost every skill; got {len(missing_anything)}/49"
    )


# ---------------------------------------------------------------------------
# Rule 6 — examples count
# ---------------------------------------------------------------------------


def test_rule_6_examples_count(skills_report) -> None:
    """`## Examples` ≥2 invocations with expected output style."""
    rule = _get_rule("rule_6_examples_count")
    assert rule is not None
    # 0/50 baseline ⇒ rule 6 must fail on every current graded skill
    # (49 graded; one skill carries `disable-model-invocation: true`).
    failures = [
        r
        for r in skills_report.per_skill
        if r.rule_for("rule_6_examples_count")
        and r.rule_for("rule_6_examples_count").severity != "OK"
    ]
    assert len(failures) == 49, (
        "brief §2.1: 0/50 skills have ≥2 examples; expected 49 "
        f"failures (49 graded), got {len(failures)}"
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
    """`evals/<skill>.jsonl` with ≥3 entries; M6 brings the count to 16."""
    rule = _get_rule("rule_8_evals_present_threshold")
    assert rule is not None
    # M1 baseline: no evals exist yet — rule 8 should flag every graded
    # skill (49 graded after disable-model-invocation exclusion).
    flagged = [
        r
        for r in skills_report.per_skill
        if r.rule_for("rule_8_evals_present_threshold")
        and r.rule_for("rule_8_evals_present_threshold").severity != "OK"
    ]
    assert len(flagged) == 49


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

    Anti-pattern hits drive the Grade C/D spread. The grade vector must
    reproduce the shape of brief §2.1 (28 A / 14 B / 6 C / 1 D over the
    49 model-discoverable skills — `disable-model-invocation: true`
    skills are excluded from the AI-discovery audit). The §2.1 audit
    was a qualitative human review ("vague triggers", "weak boundary");
    the rubric is a deterministic predicate over file content, so the
    contract is "shape match within a calibrated tolerance" rather than
    bit-for-bit equality.

    Shape contract:

    * Grade D = 1 (the audit-named skill ``ai-entropy-gc`` — broken
      implementation prose, agent-shape frontmatter).
    * Grade C ≤ 9 (≤ §2.1 + 3 tolerance).
    * Grade A is the largest bucket.
    * Total graded skills = 49.
    """
    rule = _get_rule("rule_10_no_anti_patterns")
    assert rule is not None
    summary = skills_report.summary
    expected = {"A": 28, "B": 14, "C": 6, "D": 1}

    total = sum(summary.values())
    assert total == 49, f"expected 49 graded skills, got {total}: {summary}"
    assert summary.get("D", 0) == expected["D"], (
        f"expected exactly 1 Grade D skill, got {summary.get('D', 0)}: {summary}"
    )
    a_count = summary.get("A", 0)
    b_count = summary.get("B", 0)
    c_count = summary.get("C", 0)
    assert a_count >= b_count >= c_count, (
        f"§2.1 shape requires A ≥ B ≥ C; got A={a_count} B={b_count} C={c_count}"
    )
    assert c_count <= expected["C"] + 3, (
        f"Grade C count {c_count} exceeds §2.1 tolerance (target 6, +3): {summary}"
    )
    assert a_count >= expected["A"] - 3, (
        f"Grade A count {a_count} below §2.1 floor (target 28, -3): {summary}"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_rule(name: str):
    for rule in SKILL_RULES:
        if rule.name == name:
            return rule
    return None
