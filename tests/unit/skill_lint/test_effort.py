"""effort lint conformance — spec-131 S3 / spec-189 (D-189-04) contract.

The effort checker (``tools/skill_lint/checks/effort.py``) verifies that
every SKILL.md frontmatter declares ``effort: cheap|mid|high`` — enforced
(MAJOR on miss / invalid). Per spec-189 (D-189-04) ``effort`` is the sole
skill dispatch axis; the former ``model_tier`` field is deleted.

It also cross-checks each skill's declaration against the per-skill row in
``.ai-engineering/reference/model-dispatch-policy.md`` (SSOT) — declaration
/ policy mismatch is MAJOR.
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
    name: str | None = None,
) -> Path:
    """Write a minimal SKILL.md fixture with an optional ``effort:`` knob."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_name = name or skill_dir.name
    fm_lines = [f"name: {skill_name}", "description: synthetic effort fixture"]
    if effort is not None:
        fm_lines.append(f"effort: {effort}")
    fm_block = "\n".join(fm_lines)
    md = skill_dir / "SKILL.md"
    md.write_text(
        f"---\n{fm_block}\n---\n\n# Skill\n\n## Workflow\n\n1. Do the thing.\n",
        encoding="utf-8",
    )
    return md


def _write_policy(path: Path, rows: list[tuple[str, str]]) -> Path:
    """Write a minimal model-dispatch policy doc with 2-column table rows.

    ``rows`` is a list of ``(skill, effort)`` tuples. The parser tolerates
    the trailing rationale column but the test rows ship the minimum
    surface.
    """
    body = [
        "# Policy",
        "",
        "## Mapping",
        "",
        "| Skill | effort | Rationale |",
        "|---|---|---|",
    ]
    for skill, effort in rows:
        body.append(f"| {skill} | {effort} | n/a |")
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
    policy = _write_policy(tmp_path / "policy.md", [("ai-demo", "mid")])
    from skill_lint.checks.effort import check_effort, load_policy

    results = check_effort(skill_md, load_policy(policy))
    sev = {r.rule_name: r.severity for r in results}
    assert sev["effort_declared"] == "MAJOR", sev


@pytest.mark.unit
def test_effort_invalid_enum_is_major(tmp_path: Path) -> None:
    """MAJOR when ``effort:`` carries the legacy ``medium`` vocabulary."""
    skill_md = _write_skill(tmp_path / "ai-demo", effort="medium")
    policy = _write_policy(tmp_path / "policy.md", [("ai-demo", "mid")])
    from skill_lint.checks.effort import check_effort, load_policy

    results = check_effort(skill_md, load_policy(policy))
    sev = {r.rule_name: r.severity for r in results}
    assert sev["effort_declared"] == "MAJOR", sev


@pytest.mark.unit
@pytest.mark.parametrize("value", ["cheap", "mid", "high"])
def test_effort_valid_enum_is_ok(tmp_path: Path, value: str) -> None:
    """OK when ``effort:`` carries one of the three valid values."""
    skill_md = _write_skill(tmp_path / "ai-demo", effort=value)
    policy = _write_policy(tmp_path / "policy.md", [("ai-demo", value)])
    from skill_lint.checks.effort import check_effort, load_policy

    results = check_effort(skill_md, load_policy(policy))
    sev = {r.rule_name: r.severity for r in results}
    assert sev["effort_declared"] == "OK", sev


# ---------------------------------------------------------------------------
# Check 2 — policy mismatch.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_policy_mismatch_effort_is_major(tmp_path: Path) -> None:
    """MAJOR when declared effort differs from the policy row."""
    skill_md = _write_skill(tmp_path / "ai-demo", effort="cheap")
    policy = _write_policy(tmp_path / "policy.md", [("ai-demo", "high")])
    from skill_lint.checks.effort import check_effort, load_policy

    results = check_effort(skill_md, load_policy(policy))
    sev = {r.rule_name: r.severity for r in results}
    assert sev["effort_policy_match"] == "MAJOR", sev


@pytest.mark.unit
def test_policy_match_is_ok(tmp_path: Path) -> None:
    """OK when declared frontmatter matches the policy row exactly."""
    skill_md = _write_skill(tmp_path / "ai-demo", effort="mid")
    policy = _write_policy(tmp_path / "policy.md", [("ai-demo", "mid")])
    from skill_lint.checks.effort import check_effort, load_policy

    results = check_effort(skill_md, load_policy(policy))
    sev = {r.rule_name: r.severity for r in results}
    assert sev["effort_policy_match"] == "OK", sev


@pytest.mark.unit
def test_policy_absent_is_minor_advisory(tmp_path: Path) -> None:
    """MINOR when the skill is not listed in the policy (advisory)."""
    skill_md = _write_skill(tmp_path / "ai-demo", effort="mid")
    policy = _write_policy(tmp_path / "policy.md", [("ai-other", "high")])
    from skill_lint.checks.effort import check_effort, load_policy

    results = check_effort(skill_md, load_policy(policy))
    sev = {r.rule_name: r.severity for r in results}
    assert sev["effort_policy_match"] == "MINOR", sev


# ---------------------------------------------------------------------------
# Check 3 — GitHub mirror gap (allow-listed absence).
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
    _write_skill(skills_root / "ai-demo", effort="mid")
    policy = _write_policy(
        tmp_path / "policy.md",
        [("ai-demo", "mid"), ("ai-absent", "high")],
    )
    from skill_lint.checks.effort import check_all_skills, load_policy

    results = check_all_skills(skills_root, load_policy(policy))
    # Driver returns one entry per skill present; the absent skill is
    # silently skipped (an allow-listed mirror gap).
    skill_paths = {p.parent.name for p, _r in results}
    assert "ai-demo" in skill_paths
    assert "ai-absent" not in skill_paths


# ---------------------------------------------------------------------------
# Check 4 — driver shape parity with pair_aware.check_pair_consistency.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_check_all_skills_returns_per_skill_results(tmp_path: Path) -> None:
    """Driver yields ``[(Path, RubricResult)]`` matching pair_aware shape."""
    skills_root = tmp_path / "skills"
    _write_skill(skills_root / "ai-foo", effort="mid")
    _write_skill(skills_root / "ai-bar", effort="cheap")
    policy = _write_policy(
        tmp_path / "policy.md",
        [("ai-foo", "mid"), ("ai-bar", "cheap")],
    )
    from skill_lint.checks.effort import check_all_skills, load_policy

    results = check_all_skills(skills_root, load_policy(policy))
    # Multiple results per skill (effort_declared + effort_policy_match);
    # shape is uniform.
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

    policy = _write_policy(tmp_path / "policy.md", [("ai-demo", "mid")])
    missing = tmp_path / "does-not-exist"
    with pytest.raises(FileNotFoundError):
        check_all_skills(missing, load_policy(policy))


# ---------------------------------------------------------------------------
# Check 5 — policy loader.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_load_policy_parses_table_rows(tmp_path: Path) -> None:
    """``load_policy`` reads the markdown table and returns ``{skill: effort}``."""
    policy_path = _write_policy(
        tmp_path / "policy.md",
        [("ai-foo", "mid"), ("ai-bar", "cheap")],
    )
    from skill_lint.checks.effort import load_policy

    policy = load_policy(policy_path)
    assert policy["ai-foo"] == "mid"
    assert policy["ai-bar"] == "cheap"


@pytest.mark.unit
def test_load_policy_ignores_header_row(tmp_path: Path) -> None:
    """Header / separator rows must not pollute the parsed mapping."""
    policy_path = _write_policy(
        tmp_path / "policy.md",
        [("ai-foo", "mid")],
    )
    from skill_lint.checks.effort import load_policy

    policy = load_policy(policy_path)
    assert "Skill" not in policy
    assert "---" not in policy
    assert len(policy) == 1
