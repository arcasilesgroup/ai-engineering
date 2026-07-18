"""Naming lint conformance — brief §2.5 R1-R5 contract.

Pairing: TDD RED partner of plan T-6.2 (`tools/skill_lint/checks/naming.py`).
**DO NOT MODIFY THIS FILE during T-6.2 GREEN.** The checker implementation
must change to satisfy these assertions.

Brief §2.5 ships a 5-rule naming convention:

- **R1 — `ai-` prefix** on every skill / agent. Internal specialist roster
  (``reviewer-*``, ``verifier-*``, ``verify-*``) is exempt.
- **R2 — verb-noun + banned-metaphor list** on every hook script. The
  seven D-131-10-deferred legacy filenames emit advisory ``MINOR`` so the
  existing surface does not break CI.
- **R3 — paired lifecycle verbs**: when ``start.sh`` exists, the matching
  ``end.sh`` (or ``stop.sh`` for runtime/daemon/process nouns) must exist.
- **R4 — kebab-case** in user-facing surfaces.
- **R5 — `.sh` ↔ `.ps1` sibling parity**. Three skill-script gaps emit
  advisory ``INFO`` per D-131-10 defer; ``simplify-sweep`` is closed in
  T-6.5.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Module import contract.
# ---------------------------------------------------------------------------


def test_module_exports_check_naming_callable() -> None:
    """`skill_lint.checks.naming.check_naming` must exist and be callable."""
    from skill_lint.checks.naming import check_naming

    assert callable(check_naming), "check_naming must be callable"


def test_check_all_paths_returns_results_iterable(
    skills_root: Path, agents_root: Path, project_root: Path
) -> None:
    """`check_naming` returns a list of `(path, RubricResult)` tuples."""
    from skill_lint.checks.naming import check_naming

    hooks_root = project_root / ".ai-engineering" / "scripts" / "hooks"
    scheduled_root = project_root / ".ai-engineering" / "scripts" / "scheduled"

    results = check_naming(skills_root, agents_root, hooks_root, scheduled_root)
    assert isinstance(results, list), f"expected list, got {type(results)!r}"
    assert len(results) > 0, "expected at least one rule outcome from the live surface"
    for entry in results:
        assert isinstance(entry, tuple) and len(entry) == 2, (
            f"each result must be a (path, RubricResult) tuple, got {entry!r}"
        )
        path, rubric = entry
        assert isinstance(path, Path), f"first element must be Path, got {type(path)!r}"
        assert hasattr(rubric, "severity"), f"second element must expose .severity, got {rubric!r}"
        assert rubric.severity in {"OK", "INFO", "MINOR", "MAJOR", "CRITICAL"}, (
            f"unexpected severity {rubric.severity!r}"
        )
        assert hasattr(rubric, "rule_name"), f"missing rule_name on {rubric!r}"


# ---------------------------------------------------------------------------
# R1 — ai- prefix.
# ---------------------------------------------------------------------------


def test_r1_prefix_passes_canonical_skills(
    skills_root: Path, agents_root: Path, project_root: Path
) -> None:
    """Every shipped skill under `.claude/skills/` carries the `ai-` prefix."""
    from skill_lint.checks.naming import check_naming

    hooks_root = project_root / ".ai-engineering" / "scripts" / "hooks"
    scheduled_root = project_root / ".ai-engineering" / "scripts" / "scheduled"

    results = check_naming(skills_root, agents_root, hooks_root, scheduled_root)
    r1_results = [r for _p, r in results if r.rule_name == "naming_r1_prefix"]
    assert r1_results, "expected R1 prefix results from the live surface"
    non_ok = [r for r in r1_results if r.severity != "OK"]
    assert not non_ok, (
        f"unexpected R1 violations on shipped skills/agents: "
        f"{[(r.severity, r.reason) for r in non_ok]}"
    )


def test_r1_prefix_skips_internal_specialists(
    skills_root: Path, agents_root: Path, project_root: Path
) -> None:
    """`reviewer-*`, `verifier-*`, `verify-*` agents are NOT flagged by R1."""
    from skill_lint.checks.naming import check_naming

    hooks_root = project_root / ".ai-engineering" / "scripts" / "hooks"
    scheduled_root = project_root / ".ai-engineering" / "scripts" / "scheduled"

    results = check_naming(skills_root, agents_root, hooks_root, scheduled_root)
    r1_results = [(p, r) for p, r in results if r.rule_name == "naming_r1_prefix"]
    flagged_internal = [
        (p, r)
        for p, r in r1_results
        if p.name.startswith(("reviewer-", "verifier-", "verify-")) and r.severity != "OK"
    ]
    assert not flagged_internal, (
        f"specialist roster must be exempt from R1, but R1 flagged: "
        f"{[(str(p), r.severity) for p, r in flagged_internal]}"
    )


# ---------------------------------------------------------------------------
# R2 — verb-noun + banned metaphor list.
# ---------------------------------------------------------------------------


def test_r2_verb_noun_flags_legacy_metaphors_as_minor(
    skills_root: Path, agents_root: Path, project_root: Path
) -> None:
    """`copilot-instinct-*` / `copilot-strategic-compact` → advisory MINOR."""
    from skill_lint.checks.naming import check_naming

    hooks_root = project_root / ".ai-engineering" / "scripts" / "hooks"
    scheduled_root = project_root / ".ai-engineering" / "scripts" / "scheduled"

    results = check_naming(skills_root, agents_root, hooks_root, scheduled_root)
    r2_results = [(p, r) for p, r in results if r.rule_name == "naming_r2_verb_noun"]
    assert r2_results, "expected R2 verb-noun results"

    by_stem = {p.stem: r for p, r in r2_results}

    instinct_extract = by_stem.get("copilot-instinct-extract")
    assert instinct_extract is not None, "copilot-instinct-extract.sh must be linted by R2"
    assert instinct_extract.severity == "MINOR", (
        f"expected MINOR for legacy metaphor, got {instinct_extract.severity!r}"
    )
    assert "instinct" in instinct_extract.reason.lower(), (
        f"reason should mention 'instinct': {instinct_extract.reason!r}"
    )

    strategic_compact = by_stem.get("copilot-strategic-compact")
    assert strategic_compact is not None, "copilot-strategic-compact.sh must be linted by R2"
    assert strategic_compact.severity == "MINOR", (
        f"expected MINOR for legacy metaphor, got {strategic_compact.severity!r}"
    )
    assert "strategic" in strategic_compact.reason.lower(), (
        f"reason should mention 'strategic': {strategic_compact.reason!r}"
    )


def test_r2_verb_noun_passes_clean_names(
    skills_root: Path, agents_root: Path, project_root: Path
) -> None:
    """`copilot-session-start.sh` passes R2 — clean verb-noun, no metaphor."""
    from skill_lint.checks.naming import check_naming

    hooks_root = project_root / ".ai-engineering" / "scripts" / "hooks"
    scheduled_root = project_root / ".ai-engineering" / "scripts" / "scheduled"

    results = check_naming(skills_root, agents_root, hooks_root, scheduled_root)
    r2_results = [(p, r) for p, r in results if r.rule_name == "naming_r2_verb_noun"]
    by_stem = {p.stem: r for p, r in r2_results}

    session_start = by_stem.get("copilot-session-start")
    assert session_start is not None, "copilot-session-start.sh must be linted by R2"
    assert session_start.severity == "OK", (
        f"expected OK for clean verb-noun, got {session_start.severity!r} "
        f"({session_start.reason!r})"
    )


# ---------------------------------------------------------------------------
# R3 — paired lifecycle verbs.
# ---------------------------------------------------------------------------


def test_r3_lifecycle_pair_passes_session_pair(
    skills_root: Path, agents_root: Path, project_root: Path
) -> None:
    """Live hooks dir has matched session-start/session-end pair."""
    from skill_lint.checks.naming import check_naming

    hooks_root = project_root / ".ai-engineering" / "scripts" / "hooks"
    scheduled_root = project_root / ".ai-engineering" / "scripts" / "scheduled"

    results = check_naming(skills_root, agents_root, hooks_root, scheduled_root)
    r3_results = [r for _p, r in results if r.rule_name == "naming_r3_lifecycle_pair"]
    assert r3_results, "expected R3 lifecycle results"
    non_ok = [r for r in r3_results if r.severity != "OK"]
    assert not non_ok, (
        f"unexpected R3 violations on the live surface: {[(r.severity, r.reason) for r in non_ok]}"
    )


def test_r3_lifecycle_pair_fails_orphan_start(tmp_path: Path) -> None:
    """Synthetic orphan `foo-session-start.sh` → MAJOR."""
    from skill_lint.checks.naming import check_naming

    skills_root = tmp_path / ".claude" / "skills"
    agents_root = tmp_path / ".claude" / "agents"
    hooks_root = tmp_path / "hooks"
    scheduled_root = tmp_path / "scheduled"
    for d in (skills_root, agents_root, hooks_root, scheduled_root):
        d.mkdir(parents=True, exist_ok=True)

    # Orphan start with no matching end.
    (hooks_root / "foo-session-start.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (hooks_root / "foo-session-start.ps1").write_text("# parity\n", encoding="utf-8")

    results = check_naming(skills_root, agents_root, hooks_root, scheduled_root)
    r3_results = [(p, r) for p, r in results if r.rule_name == "naming_r3_lifecycle_pair"]
    major = [r for _p, r in r3_results if r.severity == "MAJOR"]
    assert major, (
        f"expected at least one R3 MAJOR for orphan start, got "
        f"{[(str(p.name), r.severity, r.reason) for p, r in r3_results]}"
    )


# ---------------------------------------------------------------------------
# R4 — kebab-case.
# ---------------------------------------------------------------------------


def test_r4_kebab_case_passes_today(
    skills_root: Path, agents_root: Path, project_root: Path
) -> None:
    """Every basename on the live surface uses kebab-case."""
    from skill_lint.checks.naming import check_naming

    hooks_root = project_root / ".ai-engineering" / "scripts" / "hooks"
    scheduled_root = project_root / ".ai-engineering" / "scripts" / "scheduled"

    results = check_naming(skills_root, agents_root, hooks_root, scheduled_root)
    r4_results = [(p, r) for p, r in results if r.rule_name == "naming_r4_kebab_case"]
    assert r4_results, "expected R4 kebab-case results"
    non_ok = [(p, r) for p, r in r4_results if r.severity != "OK"]
    assert not non_ok, (
        f"unexpected R4 violations on the live surface: "
        f"{[(str(p), r.severity, r.reason) for p, r in non_ok]}"
    )


def test_r4_kebab_case_flags_underscore_synthetic(tmp_path: Path) -> None:
    """Synthetic `foo_bar.sh` → MAJOR R4."""
    from skill_lint.checks.naming import check_naming

    skills_root = tmp_path / ".claude" / "skills"
    agents_root = tmp_path / ".claude" / "agents"
    hooks_root = tmp_path / "hooks"
    scheduled_root = tmp_path / "scheduled"
    for d in (skills_root, agents_root, hooks_root, scheduled_root):
        d.mkdir(parents=True, exist_ok=True)

    (hooks_root / "foo_bar.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (hooks_root / "foo_bar.ps1").write_text("# parity\n", encoding="utf-8")

    results = check_naming(skills_root, agents_root, hooks_root, scheduled_root)
    r4_results = [(p, r) for p, r in results if r.rule_name == "naming_r4_kebab_case"]
    major = [r for _p, r in r4_results if r.severity == "MAJOR"]
    assert major, (
        f"expected at least one R4 MAJOR for underscore basename, got "
        f"{[(str(p.name), r.severity) for p, r in r4_results]}"
    )


# ---------------------------------------------------------------------------
# R5 — .sh ↔ .ps1 sibling parity.
# ---------------------------------------------------------------------------


def test_r5_parity_allowlists_skill_scripts_as_info(
    skills_root: Path, agents_root: Path, project_root: Path
) -> None:
    """The deferred skill-script `.sh` files emit INFO, not MAJOR.

    `board-sync-github.sh`, `scaffold-skill.sh` have no `.ps1` siblings;
    the allow-list keeps them advisory. (`cleanup-settings-local.sh` was
    removed with the ai-analyze-permissions skill in spec-187 D-187-04.)
    """
    from skill_lint.checks.naming import check_naming

    hooks_root = project_root / ".ai-engineering" / "scripts" / "hooks"
    scheduled_root = project_root / ".ai-engineering" / "scripts" / "scheduled"

    results = check_naming(skills_root, agents_root, hooks_root, scheduled_root)
    r5_results = [(p, r) for p, r in results if r.rule_name == "naming_r5_sh_ps1_parity"]
    assert r5_results, "expected R5 parity results"

    info_stems = {p.stem for p, r in r5_results if r.severity == "INFO" and p.suffix == ".sh"}
    expected_info = {
        "board-sync-github",
        "scaffold-skill",
    }
    assert expected_info.issubset(info_stems), (
        f"expected the three deferred skill scripts to emit INFO, missing "
        f"{expected_info - info_stems}"
    )

    # The deferred trio must NEVER emit MAJOR — that would break CI.
    major_stems = {p.stem for p, r in r5_results if r.severity == "MAJOR" and p.suffix == ".sh"}
    assert not (expected_info & major_stems), (
        f"deferred trio leaked into MAJOR severity: {expected_info & major_stems}"
    )


def test_r5_parity_passes_lib_copilot_common_pair(
    skills_root: Path, agents_root: Path, project_root: Path
) -> None:
    """`_lib/copilot-common.{sh,ps1}` has matching pair → no R5 MAJOR."""
    from skill_lint.checks.naming import check_naming

    hooks_root = project_root / ".ai-engineering" / "scripts" / "hooks"
    scheduled_root = project_root / ".ai-engineering" / "scripts" / "scheduled"

    results = check_naming(skills_root, agents_root, hooks_root, scheduled_root)
    r5_results = [(p, r) for p, r in results if r.rule_name == "naming_r5_sh_ps1_parity"]
    common_violations = [
        (p, r)
        for p, r in r5_results
        if "copilot-common" in p.name and r.severity in {"MAJOR", "MINOR"}
    ]
    assert not common_violations, (
        f"copilot-common.{{sh,ps1}} pair should pass R5, got "
        f"{[(str(p), r.severity, r.reason) for p, r in common_violations]}"
    )
