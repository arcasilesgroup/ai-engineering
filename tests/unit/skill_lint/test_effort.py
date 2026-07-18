"""effort lint conformance — spec-131 S3 contract (sub-003 T-3.2 RED).

The effort checker (``tools/skill_lint/checks/effort.py``) verifies that
every SKILL.md frontmatter declares:

* ``effort: cheap|mid|high`` — enforced (MAJOR on miss / invalid).
* ``model_tier: haiku|sonnet|opus`` — observation-only (MINOR on miss /
  invalid) during the R-131-09 grace window; flipped to MAJOR via the
  ``enforce_tier=True`` parameter once the dispatch logic has been live
  and audited.

It also cross-checks each skill's declaration against the per-skill row in
``.ai-engineering/reference/model-dispatch-policy.md`` (SSOT) — declaration / policy mismatch
is MAJOR (effort) or MINOR (model_tier, grace window).

This is the TDD RED partner of T-3.3. **DO NOT MODIFY THIS FILE during
T-3.3 GREEN.** The checker implementation must change to satisfy these
assertions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixture helpers — synthetic SKILL.md + policy doc.
# ---------------------------------------------------------------------------


def _write_skill(
    skill_dir: Path,
    *,
    effort: str | None = "mid",
    model_tier: str | None = "sonnet",
    name: str | None = None,
) -> Path:
    """Write a minimal SKILL.md fixture with optional frontmatter knobs."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_name = name or skill_dir.name
    fm_lines = [f"name: {skill_name}", "description: synthetic effort fixture"]
    if effort is not None:
        fm_lines.append(f"effort: {effort}")
    if model_tier is not None:
        fm_lines.append(f"model_tier: {model_tier}")
    fm_block = "\n".join(fm_lines)
    md = skill_dir / "SKILL.md"
    md.write_text(
        f"---\n{fm_block}\n---\n\n# Skill\n\n## Workflow\n\n1. Do the thing.\n",
        encoding="utf-8",
    )
    return md


def _write_policy(path: Path, rows: list[tuple[str, str, str]]) -> Path:
    """Write a minimal model-dispatch policy doc with table rows.

    ``rows`` is a list of ``(skill, effort, model_tier)`` tuples. The
    parser tolerates additional table columns (rationale) but the test
    rows ship the minimum surface.
    """
    body = [
        "# Policy",
        "",
        "## Mapping",
        "",
        "| Skill | effort | model_tier | Rationale |",
        "|---|---|---|---|",
    ]
    for skill, effort, tier in rows:
        body.append(f"| {skill} | {effort} | {tier} | n/a |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Check 1 — effort field missing / invalid / valid.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_effort_missing_field_is_major(tmp_path: Path) -> None:
    """MAJOR when SKILL.md frontmatter has no ``effort:`` field."""
    skill_md = _write_skill(tmp_path / "ai-demo", effort=None)
    policy = _write_policy(tmp_path / "policy.md", [("ai-demo", "mid", "sonnet")])
    from skill_lint.checks.effort import check_effort, load_policy

    results = check_effort(skill_md, load_policy(policy))
    sev = {r.rule_name: r.severity for r in results}
    assert sev["effort_declared"] == "MAJOR", sev


@pytest.mark.unit
def test_effort_invalid_enum_is_major(tmp_path: Path) -> None:
    """MAJOR when ``effort:`` carries the legacy ``medium`` vocabulary."""
    skill_md = _write_skill(tmp_path / "ai-demo", effort="medium")
    policy = _write_policy(tmp_path / "policy.md", [("ai-demo", "mid", "sonnet")])
    from skill_lint.checks.effort import check_effort, load_policy

    results = check_effort(skill_md, load_policy(policy))
    sev = {r.rule_name: r.severity for r in results}
    assert sev["effort_declared"] == "MAJOR", sev


@pytest.mark.unit
@pytest.mark.parametrize("value", ["cheap", "mid", "high"])
def test_effort_valid_enum_is_ok(tmp_path: Path, value: str) -> None:
    """OK when ``effort:`` carries one of the three valid values."""
    skill_md = _write_skill(tmp_path / "ai-demo", effort=value)
    policy = _write_policy(tmp_path / "policy.md", [("ai-demo", value, "sonnet")])
    from skill_lint.checks.effort import check_effort, load_policy

    results = check_effort(skill_md, load_policy(policy))
    sev = {r.rule_name: r.severity for r in results}
    assert sev["effort_declared"] == "OK", sev


# ---------------------------------------------------------------------------
# Check 2 — model_tier field; observation-only during grace.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_model_tier_missing_is_minor_during_grace(tmp_path: Path) -> None:
    """MINOR when ``model_tier:`` is missing — observation-only per R-131-09."""
    skill_md = _write_skill(tmp_path / "ai-demo", model_tier=None)
    policy = _write_policy(tmp_path / "policy.md", [("ai-demo", "mid", "sonnet")])
    from skill_lint.checks.effort import check_effort, load_policy

    results = check_effort(skill_md, load_policy(policy), enforce_tier=False)
    sev = {r.rule_name: r.severity for r in results}
    assert sev["model_tier_declared"] == "MINOR", sev


@pytest.mark.unit
def test_model_tier_missing_is_major_when_enforce_tier(tmp_path: Path) -> None:
    """MAJOR when ``model_tier:`` is missing and enforce_tier=True (post-grace)."""
    skill_md = _write_skill(tmp_path / "ai-demo", model_tier=None)
    policy = _write_policy(tmp_path / "policy.md", [("ai-demo", "mid", "sonnet")])
    from skill_lint.checks.effort import check_effort, load_policy

    results = check_effort(skill_md, load_policy(policy), enforce_tier=True)
    sev = {r.rule_name: r.severity for r in results}
    assert sev["model_tier_declared"] == "MAJOR", sev


@pytest.mark.unit
def test_model_tier_invalid_enum_is_major(tmp_path: Path) -> None:
    """MAJOR when ``model_tier:`` carries an unknown value (e.g. ``gpt4``)."""
    skill_md = _write_skill(tmp_path / "ai-demo", model_tier="gpt4")
    policy = _write_policy(tmp_path / "policy.md", [("ai-demo", "mid", "sonnet")])
    from skill_lint.checks.effort import check_effort, load_policy

    results = check_effort(skill_md, load_policy(policy))
    sev = {r.rule_name: r.severity for r in results}
    assert sev["model_tier_declared"] == "MAJOR", sev


@pytest.mark.unit
@pytest.mark.parametrize("value", ["haiku", "sonnet", "opus"])
def test_model_tier_valid_enum_is_ok(tmp_path: Path, value: str) -> None:
    """OK when ``model_tier:`` carries one of the three valid values."""
    skill_md = _write_skill(tmp_path / "ai-demo", model_tier=value)
    policy = _write_policy(tmp_path / "policy.md", [("ai-demo", "mid", value)])
    from skill_lint.checks.effort import check_effort, load_policy

    results = check_effort(skill_md, load_policy(policy))
    sev = {r.rule_name: r.severity for r in results}
    assert sev["model_tier_declared"] == "OK", sev


# ---------------------------------------------------------------------------
# Check 3 — policy mismatch.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_policy_mismatch_effort_is_major(tmp_path: Path) -> None:
    """MAJOR when declared effort differs from the policy row."""
    skill_md = _write_skill(tmp_path / "ai-demo", effort="cheap")
    policy = _write_policy(tmp_path / "policy.md", [("ai-demo", "high", "opus")])
    from skill_lint.checks.effort import check_effort, load_policy

    results = check_effort(skill_md, load_policy(policy))
    sev = {r.rule_name: r.severity for r in results}
    assert sev["effort_policy_match"] == "MAJOR", sev


@pytest.mark.unit
def test_policy_mismatch_model_tier_is_minor_during_grace(tmp_path: Path) -> None:
    """MINOR when declared model_tier differs from the policy row (grace)."""
    skill_md = _write_skill(tmp_path / "ai-demo", model_tier="haiku")
    policy = _write_policy(tmp_path / "policy.md", [("ai-demo", "mid", "sonnet")])
    from skill_lint.checks.effort import check_effort, load_policy

    results = check_effort(skill_md, load_policy(policy), enforce_tier=False)
    sev = {r.rule_name: r.severity for r in results}
    assert sev["model_tier_policy_match"] == "MINOR", sev


@pytest.mark.unit
def test_policy_match_is_ok(tmp_path: Path) -> None:
    """OK when declared frontmatter matches the policy row exactly."""
    skill_md = _write_skill(tmp_path / "ai-demo", effort="mid", model_tier="sonnet")
    policy = _write_policy(tmp_path / "policy.md", [("ai-demo", "mid", "sonnet")])
    from skill_lint.checks.effort import check_effort, load_policy

    results = check_effort(skill_md, load_policy(policy))
    sev = {r.rule_name: r.severity for r in results}
    assert sev["effort_policy_match"] == "OK", sev
    assert sev["model_tier_policy_match"] == "OK", sev


# ---------------------------------------------------------------------------
# Check 4 — GitHub mirror gap (allow-listed absence).
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_github_mirror_gap_tolerated(tmp_path: Path) -> None:
    """A policy skill absent from a mirror is allow-listed, not an error.

    The driver walks every mirror but must not raise when a policy lists a
    skill that a given mirror does not carry; the skill simply does not
    appear in the result set for that mirror.
    """
    skills_root = tmp_path / ".github" / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)
    # Only ai-demo lives in the gap-mirror; ai-absent is policy-only.
    _write_skill(skills_root / "ai-demo", effort="mid", model_tier="sonnet")
    policy = _write_policy(
        tmp_path / "policy.md",
        [("ai-demo", "mid", "sonnet"), ("ai-absent", "high", "opus")],
    )
    from skill_lint.checks.effort import check_all_skills, load_policy

    results = check_all_skills(skills_root, load_policy(policy))
    # Driver returns one entry per skill present; the absent skill is
    # silently skipped (an allow-listed mirror gap).
    skill_paths = {p.parent.name for p, _r in results}
    assert "ai-demo" in skill_paths
    assert "ai-absent" not in skill_paths


# ---------------------------------------------------------------------------
# Check 5 — driver shape parity with pair_aware.check_pair_consistency.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_check_all_skills_returns_per_skill_results(tmp_path: Path) -> None:
    """Driver yields ``[(Path, RubricResult)]`` matching pair_aware shape."""
    skills_root = tmp_path / "skills"
    _write_skill(skills_root / "ai-foo", effort="mid", model_tier="sonnet")
    _write_skill(skills_root / "ai-bar", effort="cheap", model_tier="haiku")
    policy = _write_policy(
        tmp_path / "policy.md",
        [("ai-foo", "mid", "sonnet"), ("ai-bar", "cheap", "haiku")],
    )
    from skill_lint.checks.effort import check_all_skills, load_policy

    results = check_all_skills(skills_root, load_policy(policy))
    # Multiple results per skill (effort_declared + model_tier_declared +
    # effort_policy_match + model_tier_policy_match); shape is uniform.
    assert results, "driver returned no results"
    for path, rubric in results:
        assert isinstance(path, Path)
        assert hasattr(rubric, "severity")
        assert hasattr(rubric, "rule_name")
        assert hasattr(rubric, "reason")


@pytest.mark.unit
def test_check_all_skills_handles_missing_root(tmp_path: Path) -> None:
    """Driver raises ``FileNotFoundError`` when ``skills_root`` is absent."""
    from skill_lint.checks.effort import check_all_skills, load_policy

    policy = _write_policy(tmp_path / "policy.md", [("ai-demo", "mid", "sonnet")])
    missing = tmp_path / "does-not-exist"
    with pytest.raises(FileNotFoundError):
        check_all_skills(missing, load_policy(policy))


# ---------------------------------------------------------------------------
# Check 6 — policy loader.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_load_policy_parses_table_rows(tmp_path: Path) -> None:
    """``load_policy`` reads the markdown table and returns ``{skill: (effort, tier)}``."""
    policy_path = _write_policy(
        tmp_path / "policy.md",
        [("ai-foo", "mid", "sonnet"), ("ai-bar", "cheap", "haiku")],
    )
    from skill_lint.checks.effort import load_policy

    policy = load_policy(policy_path)
    assert policy["ai-foo"] == ("mid", "sonnet")
    assert policy["ai-bar"] == ("cheap", "haiku")


@pytest.mark.unit
def test_load_policy_ignores_header_row(tmp_path: Path) -> None:
    """Header / separator rows must not pollute the parsed mapping."""
    policy_path = _write_policy(
        tmp_path / "policy.md",
        [("ai-foo", "mid", "sonnet")],
    )
    from skill_lint.checks.effort import load_policy

    policy = load_policy(policy_path)
    assert "Skill" not in policy
    assert "---" not in policy
    assert len(policy) == 1
