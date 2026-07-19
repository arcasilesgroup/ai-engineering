"""spec-131 S7 (sub-007): unit tests for ``tools/spec_lint/`` checks.

Each check has positive + negative + fixture coverage. Tests use
``tmp_path`` for fixtures so no on-disk spec corpus is mutated. The
integration suite (``tests/integration/test_spec_lint_e2e.py``) covers
the live corpus end-to-end.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from spec_lint import cli as _spec_lint_cli
from spec_lint.checks.decisions import check_decisions
from spec_lint.checks.frontmatter import (
    EXTRAS_ALLOWLIST,
    REQUIRED_FIELDS,
    check_frontmatter,
)
from spec_lint.checks.non_goals import check_non_goals
from spec_lint.checks.references import check_references
from spec_lint.checks.sections import REQUIRED_SECTIONS, check_sections

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_FRONTMATTER_FULL = """\
---
spec: spec-131
slug: dx-excellence-refactor
title: spec-131 — DX Excellence Refactor
status: approved
approved_at: 2026-05-11
approved_by: operator
effort: large
branch: spec-128/context-overrides-refactor
pr: arcasilesgroup/ai-engineering#509
target_dispatch: /ai-autopilot
source_brief: .ai-engineering/specs/drafts/dx-excellence-refactor-brief.md
chains_after: spec-129
summary: DX excellence refactor lands the canonical chain skeleton.
---

## Summary

Body.
"""

_FRONTMATTER_MINIMAL = """\
---
spec: spec-129
title: Spec 129
status: approved
effort: medium
summary: Minimal spec fixture used by the spec_lint frontmatter test suite.
---

## Summary

Body.
"""


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "spec.md"
    p.write_text(text, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# T-7.2 — Frontmatter check
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_frontmatter_full_spec_131_shape_passes(tmp_path: Path) -> None:
    spec_path = _write(tmp_path, _FRONTMATTER_FULL)
    results = check_frontmatter(spec_path)
    assert results == [], f"expected no findings, got {results}"


@pytest.mark.unit
def test_frontmatter_minimal_spec_129_shape_passes(tmp_path: Path) -> None:
    spec_path = _write(tmp_path, _FRONTMATTER_MINIMAL)
    results = check_frontmatter(spec_path)
    assert results == [], f"expected no findings, got {results}"


@pytest.mark.unit
def test_frontmatter_missing_spec_field_is_blocker(tmp_path: Path) -> None:
    text = "---\ntitle: t\nstatus: approved\neffort: large\n---\n## Summary\n"
    spec_path = _write(tmp_path, text)
    results = check_frontmatter(spec_path)
    assert any(
        r.check_name == "frontmatter_missing_required"
        and r.severity == "BLOCKER"
        and "spec" in r.reason
        for r in results
    )


@pytest.mark.unit
def test_frontmatter_missing_title_field_is_blocker(tmp_path: Path) -> None:
    text = "---\nspec: spec-131\nstatus: approved\neffort: large\n---\n## Summary\n"
    spec_path = _write(tmp_path, text)
    results = check_frontmatter(spec_path)
    assert any(
        r.check_name == "frontmatter_missing_required"
        and r.severity == "BLOCKER"
        and "title" in r.reason
        for r in results
    )


@pytest.mark.unit
def test_frontmatter_invalid_status_enum_is_blocker(tmp_path: Path) -> None:
    text = "---\nspec: spec-131\ntitle: t\nstatus: experimental\neffort: large\n---\n## Summary\n"
    spec_path = _write(tmp_path, text)
    results = check_frontmatter(spec_path)
    assert any(
        r.check_name == "frontmatter_invalid_enum"
        and r.severity == "BLOCKER"
        and "status" in r.reason
        for r in results
    )


@pytest.mark.unit
def test_frontmatter_invalid_effort_enum_is_blocker(tmp_path: Path) -> None:
    text = "---\nspec: spec-131\ntitle: t\nstatus: approved\neffort: huge\n---\n## Summary\n"
    spec_path = _write(tmp_path, text)
    results = check_frontmatter(spec_path)
    assert any(
        r.check_name == "frontmatter_invalid_enum"
        and r.severity == "BLOCKER"
        and "effort" in r.reason
        for r in results
    )


@pytest.mark.unit
def test_frontmatter_unknown_key_is_advisory(tmp_path: Path) -> None:
    text = (
        "---\nspec: spec-131\ntitle: t\nstatus: approved\neffort: large\n"
        "summary: s\nweird_extra_field: foo\n---\n## Summary\n"
    )
    spec_path = _write(tmp_path, text)
    results = check_frontmatter(spec_path)
    advisories = [
        r
        for r in results
        if r.check_name == "frontmatter_unknown_key"
        and r.severity == "ADVISORY"
        and "weird_extra_field" in r.reason
    ]
    assert advisories, f"expected ADVISORY for weird_extra_field, got {results}"
    # No BLOCKER should fire for the unknown key alone.
    assert not [r for r in results if r.severity == "BLOCKER"], results


@pytest.mark.unit
def test_frontmatter_missing_fence_is_blocker(tmp_path: Path) -> None:
    text = "spec: spec-131\ntitle: t\n## Summary\n"
    spec_path = _write(tmp_path, text)
    results = check_frontmatter(spec_path)
    assert any(r.check_name == "frontmatter_missing" and r.severity == "BLOCKER" for r in results)


@pytest.mark.unit
def test_frontmatter_required_fields_match_schema_doc() -> None:
    # Guard rail: any future change to REQUIRED_FIELDS must also update
    # the schema doc.
    assert frozenset({"spec", "title", "status", "effort"}) == REQUIRED_FIELDS


@pytest.mark.unit
def test_frontmatter_extras_allowlist_covers_spec_131_extras() -> None:
    # Spec-131 ships the eight extras documented in spec-schema.md.
    expected = {
        "branch",
        "pr",
        "slug",
        "target_dispatch",
        "source_brief",
        "chains_after",
        "approved_at",
        "approved_by",
    }
    assert expected <= EXTRAS_ALLOWLIST


# ---------------------------------------------------------------------------
# T-7.3 — Sections check
# ---------------------------------------------------------------------------


def _spec_with_sections(sections: list[str]) -> str:
    body = "---\nspec: spec-131\ntitle: t\nstatus: approved\neffort: large\n---\n\n"
    body += "\n".join(f"## {s}\n\nBody.\n" for s in sections)
    return body


@pytest.mark.unit
def test_sections_all_five_required_present_passes(tmp_path: Path) -> None:
    spec_path = _write(tmp_path, _spec_with_sections(list(REQUIRED_SECTIONS)))
    results = check_sections(spec_path)
    assert results == [], results


@pytest.mark.unit
def test_sections_required_plus_optional_passes(tmp_path: Path) -> None:
    spec_path = _write(
        tmp_path,
        _spec_with_sections([*REQUIRED_SECTIONS, "References", "Open Questions"]),
    )
    results = check_sections(spec_path)
    assert results == [], results


@pytest.mark.unit
def test_sections_missing_goals_is_blocker(tmp_path: Path) -> None:
    spec_path = _write(
        tmp_path,
        _spec_with_sections(["Summary", "Non-Goals", "Decisions", "Risks"]),
    )
    results = check_sections(spec_path)
    assert any(
        r.check_name == "section_missing" and r.severity == "BLOCKER" and "Goals" in r.reason
        for r in results
    )


@pytest.mark.unit
def test_sections_heading_text_mismatch_is_blocker(tmp_path: Path) -> None:
    # ``## Goals!`` (extra punctuation) is not an exact match.
    text = (
        "---\nspec: spec-131\ntitle: t\nstatus: approved\neffort: large\n---\n\n"
        "## Summary\n## Goals!\n## Non-Goals\n## Decisions\n## Risks\n"
    )
    spec_path = _write(tmp_path, text)
    results = check_sections(spec_path)
    blockers = [r for r in results if r.severity == "BLOCKER"]
    assert blockers, results


@pytest.mark.unit
def test_sections_case_sensitive_match(tmp_path: Path) -> None:
    # ``## goals`` (lowercase) is not an exact match.
    text = (
        "---\nspec: spec-131\ntitle: t\nstatus: approved\neffort: large\n---\n\n"
        "## Summary\n## goals\n## Non-Goals\n## Decisions\n## Risks\n"
    )
    spec_path = _write(tmp_path, text)
    results = check_sections(spec_path)
    assert any(r.check_name == "section_missing" and "Goals" in r.reason for r in results)


# ---------------------------------------------------------------------------
# T-7.4 — Decisions check
# ---------------------------------------------------------------------------


_DECISIONS_BULLET_OK = (
    "---\nspec: spec-131\ntitle: t\nstatus: approved\neffort: large\n---\n\n"
    "## Summary\nBody.\n\n## Goals\nx\n\n## Non-Goals\n- y\n\n"
    "## Decisions\n\n"
    "- **D-131-01 — Trim scope.** Drop full M1.\n"
    "  *Rationale*: avoids re-work.\n\n"
    "## Risks\nz\n"
)


_DECISIONS_HEADING_OK = (
    "---\nspec: spec-129\ntitle: t\nstatus: approved\neffort: medium\n---\n\n"
    "## Summary\nBody.\n\n## Goals\nx\n\n## Non-Goals\n- y\n\n"
    "## Decisions\n\n"
    "### D-129-01 — PR scope expansion\n\n"
    "**Decision**: Rename PR.\n\n"
    "**Rationale**: User-selected option A.\n\n"
    "## Risks\nz\n"
)


@pytest.mark.unit
def test_decisions_bullet_form_with_italic_rationale_passes(tmp_path: Path) -> None:
    spec_path = _write(tmp_path, _DECISIONS_BULLET_OK)
    results = check_decisions(spec_path)
    assert results == [], results


@pytest.mark.unit
def test_decisions_heading_form_with_bold_rationale_passes(tmp_path: Path) -> None:
    spec_path = _write(tmp_path, _DECISIONS_HEADING_OK)
    results = check_decisions(spec_path)
    assert results == [], results


@pytest.mark.unit
def test_decisions_heading_form_with_italic_rationale_passes(tmp_path: Path) -> None:
    # Heading form + italic rationale prefix (mixed-case acceptance).
    text = (
        "---\nspec: spec-129\ntitle: t\nstatus: approved\neffort: medium\n---\n\n"
        "## Summary\nBody.\n\n## Goals\nx\n\n## Non-Goals\n- y\n\n"
        "## Decisions\n\n"
        "### D-129-01 — Decision text\n\n"
        "**Decision**: x.\n\n"
        "*Rationale*: italic prefix here.\n\n"
        "## Risks\nz\n"
    )
    spec_path = _write(tmp_path, text)
    results = check_decisions(spec_path)
    assert results == [], results


@pytest.mark.unit
def test_decisions_bullet_missing_rationale_is_blocker(tmp_path: Path) -> None:
    text = (
        "---\nspec: spec-131\ntitle: t\nstatus: approved\neffort: large\n---\n\n"
        "## Summary\nx\n\n## Goals\nx\n\n## Non-Goals\n- y\n\n"
        "## Decisions\n\n"
        "- **D-131-01 — Trim scope.** Drop full M1.\n\n"
        "## Risks\nz\n"
    )
    spec_path = _write(tmp_path, text)
    results = check_decisions(spec_path)
    assert any(
        r.check_name == "decision_missing_rationale"
        and r.severity == "BLOCKER"
        and "D-131-01" in r.reason
        for r in results
    )


@pytest.mark.unit
def test_decisions_heading_missing_rationale_is_blocker(tmp_path: Path) -> None:
    text = (
        "---\nspec: spec-129\ntitle: t\nstatus: approved\neffort: medium\n---\n\n"
        "## Summary\nx\n\n## Goals\nx\n\n## Non-Goals\n- y\n\n"
        "## Decisions\n\n"
        "### D-129-01 — Decision text\n\n"
        "**Decision**: x.\n\n"
        "## Risks\nz\n"
    )
    spec_path = _write(tmp_path, text)
    results = check_decisions(spec_path)
    assert any(
        r.check_name == "decision_missing_rationale"
        and r.severity == "BLOCKER"
        and "D-129-01" in r.reason
        for r in results
    )


@pytest.mark.unit
def test_decisions_id_prefix_mismatch_is_blocker(tmp_path: Path) -> None:
    # Frontmatter says spec-131 but the decision id is D-128-01.
    text = (
        "---\nspec: spec-131\ntitle: t\nstatus: approved\neffort: large\n---\n\n"
        "## Summary\nx\n\n## Goals\nx\n\n## Non-Goals\n- y\n\n"
        "## Decisions\n\n"
        "- **D-128-01 — Wrong prefix.** body\n"
        "  *Rationale*: noted.\n\n"
        "## Risks\nz\n"
    )
    spec_path = _write(tmp_path, text)
    results = check_decisions(spec_path)
    assert any(
        r.check_name == "decision_id_prefix_mismatch"
        and r.severity == "BLOCKER"
        and "D-128-01" in r.reason
        for r in results
    )


@pytest.mark.unit
def test_decisions_section_empty_is_blocker(tmp_path: Path) -> None:
    text = (
        "---\nspec: spec-131\ntitle: t\nstatus: approved\neffort: large\n---\n\n"
        "## Summary\nx\n\n## Goals\nx\n\n## Non-Goals\n- y\n\n"
        "## Decisions\n\n"
        "## Risks\nz\n"
    )
    spec_path = _write(tmp_path, text)
    results = check_decisions(spec_path)
    assert any(
        r.check_name == "decisions_section_empty" and r.severity == "BLOCKER" for r in results
    )


@pytest.mark.unit
def test_decisions_slug_derived_prefix_passes(tmp_path: Path) -> None:
    # spec-id is a slug (no leading ``spec-``); expected prefix is
    # ``D-skills-agents-excellence-``.
    text = (
        "---\nspec: skills-agents-excellence\ntitle: t\nstatus: approved\n"
        "effort: large\n---\n\n"
        "## Summary\nx\n\n## Goals\nx\n\n## Non-Goals\n- y\n\n"
        "## Decisions\n\n"
        "- **D-skills-agents-excellence-01 — Decision.** body\n"
        "  *Rationale*: noted.\n\n"
        "## Risks\nz\n"
    )
    spec_path = _write(tmp_path, text)
    results = check_decisions(spec_path)
    assert results == [], results


# ---------------------------------------------------------------------------
# T-7.5 — Non-Goals check
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_non_goals_numbered_list_passes(tmp_path: Path) -> None:
    text = (
        "---\nspec: spec-131\ntitle: t\nstatus: approved\neffort: large\n---\n\n"
        "## Non-Goals\n\n1. **No X.**\n2. **No Y.**\n\n## Decisions\n"
    )
    spec_path = _write(tmp_path, text)
    results = check_non_goals(spec_path)
    assert results == [], results


@pytest.mark.unit
def test_non_goals_bulleted_list_passes(tmp_path: Path) -> None:
    text = (
        "---\nspec: spec-131\ntitle: t\nstatus: approved\neffort: large\n---\n\n"
        "## Non-Goals\n\n- No X.\n- No Y.\n\n## Decisions\n"
    )
    spec_path = _write(tmp_path, text)
    results = check_non_goals(spec_path)
    assert results == [], results


@pytest.mark.unit
def test_non_goals_empty_section_is_blocker(tmp_path: Path) -> None:
    text = (
        "---\nspec: spec-131\ntitle: t\nstatus: approved\neffort: large\n---\n\n"
        "## Non-Goals\n\n## Decisions\n"
    )
    spec_path = _write(tmp_path, text)
    results = check_non_goals(spec_path)
    assert any(r.check_name == "non_goals_empty" and r.severity == "BLOCKER" for r in results)


@pytest.mark.unit
def test_non_goals_placeholder_only_is_blocker(tmp_path: Path) -> None:
    text = (
        "---\nspec: spec-131\ntitle: t\nstatus: approved\neffort: large\n---\n\n"
        "## Non-Goals\n\n*placeholder*\n\n## Decisions\n"
    )
    spec_path = _write(tmp_path, text)
    results = check_non_goals(spec_path)
    assert any(r.check_name == "non_goals_empty" and r.severity == "BLOCKER" for r in results)


# ---------------------------------------------------------------------------
# T-7.6 — References check
# ---------------------------------------------------------------------------


def _refs_spec(references_body: str) -> str:
    return (
        "---\nspec: spec-131\ntitle: t\nstatus: approved\neffort: large\n---\n\n"
        f"## References\n\n{references_body}\n"
    )


@pytest.mark.unit
def test_references_pr_owner_repo_shape_passes(tmp_path: Path) -> None:
    spec_path = _write(tmp_path, _refs_spec("- pr: arcasilesgroup/ai-engineering#509"))
    results = check_references(spec_path)
    assert results == [], results


@pytest.mark.unit
def test_references_pr_url_passes(tmp_path: Path) -> None:
    spec_path = _write(
        tmp_path,
        _refs_spec("- pr: https://github.com/arcasilesgroup/ai-engineering/pull/509"),
    )
    results = check_references(spec_path)
    assert results == [], results


@pytest.mark.unit
def test_references_doc_path_passes(tmp_path: Path) -> None:
    spec_path = _write(tmp_path, _refs_spec("- doc: .ai-engineering/specs/drafts/foo.md"))
    results = check_references(spec_path)
    assert results == [], results


@pytest.mark.unit
def test_references_doc_url_passes(tmp_path: Path) -> None:
    spec_path = _write(tmp_path, _refs_spec("- doc: https://example.com/api"))
    results = check_references(spec_path)
    assert results == [], results


@pytest.mark.unit
def test_references_research_md_path_passes(tmp_path: Path) -> None:
    spec_path = _write(tmp_path, _refs_spec("- research: .ai-engineering/runtime/research/foo.md"))
    results = check_references(spec_path)
    assert results == [], results


@pytest.mark.unit
def test_references_work_item_passes(tmp_path: Path) -> None:
    spec_path = _write(tmp_path, _refs_spec("- work-item: GH-123"))
    results = check_references(spec_path)
    assert results == [], results


@pytest.mark.unit
def test_references_research_bare_uuid_is_advisory(tmp_path: Path) -> None:
    spec_path = _write(
        tmp_path,
        _refs_spec("- research: NotebookLM b8a09700-2ce7-4d6c-84d7-82b89765ea53"),
    )
    results = check_references(spec_path)
    advisories = [
        r
        for r in results
        if r.check_name == "references_research_shape" and r.severity == "ADVISORY"
    ]
    assert advisories, results
    # No BLOCKER on a bare UUID — operator metadata ergonomics.
    assert not [r for r in results if r.severity == "BLOCKER"], results


@pytest.mark.unit
def test_references_pr_malformed_target_is_blocker(tmp_path: Path) -> None:
    spec_path = _write(tmp_path, _refs_spec("- pr: just-some-text"))
    results = check_references(spec_path)
    assert any(r.check_name == "references_pr_shape" and r.severity == "BLOCKER" for r in results)


@pytest.mark.unit
def test_references_unknown_prefix_is_blocker(tmp_path: Path) -> None:
    spec_path = _write(tmp_path, _refs_spec("- foobar: anything"))
    results = check_references(spec_path)
    assert any(
        r.check_name == "references_unknown_prefix" and r.severity == "BLOCKER" for r in results
    )


@pytest.mark.unit
def test_references_section_absent_passes(tmp_path: Path) -> None:
    # No ``## References`` heading at all — optional section, no findings.
    text = (
        "---\nspec: spec-131\ntitle: t\nstatus: approved\neffort: large\n---\n\n## Summary\nBody.\n"
    )
    spec_path = _write(tmp_path, text)
    results = check_references(spec_path)
    assert results == [], results


# ---------------------------------------------------------------------------
# Plan check (plan-schema.md)
# ---------------------------------------------------------------------------

from spec_lint.checks.plan import check_plan  # noqa: E402


def _spec_and_plan(tmp_path: Path, plan_text: str) -> Path:
    spec_path = _write(
        tmp_path, "---\nspec: spec-test\ntitle: t\nstatus: approved\neffort: small\n---\n"
    )
    (tmp_path / "plan.md").write_text(plan_text, encoding="utf-8")
    return spec_path


@pytest.mark.unit
def test_plan_no_file_skips_silently(tmp_path: Path) -> None:
    spec_path = _write(tmp_path, "---\nspec: x\ntitle: t\nstatus: draft\neffort: small\n---\n")
    assert check_plan(spec_path) == []


@pytest.mark.unit
def test_plan_active_with_tasks_passes(tmp_path: Path) -> None:
    plan = (
        "---\nspec: spec-test\ntitle: T\nstatus: in-progress\n---\n"
        "# Plan\n\n- [x] **T-1.1**: done\n- [ ] **T-1.2**: pending\n"
    )
    spec_path = _spec_and_plan(tmp_path, plan)
    results = check_plan(spec_path)
    assert [r for r in results if r.severity == "BLOCKER"] == []


@pytest.mark.unit
def test_plan_active_without_tasks_is_blocker(tmp_path: Path) -> None:
    plan = "---\nspec: spec-test\ntitle: T\nstatus: approved\n---\n# Plan\n\nNo tasks here.\n"
    spec_path = _spec_and_plan(tmp_path, plan)
    results = check_plan(spec_path)
    assert any(r.check_name == "plan_tasks_missing" and r.severity == "BLOCKER" for r in results)


# ---------------------------------------------------------------------------
# spec-167 D-167-07 — pre-merge consolidation makes the feature PR run CI
# against the idle (`# No active spec`) slot. Pin that spec_lint stays green on
# that state so a consolidated feature PR never reds its own CI.
# ---------------------------------------------------------------------------

_IDLE_SPEC = "# No active spec\n\nRun /ai-brainstorm to start one.\n"
_IDLE_PLAN = "# No active plan\n\nRun /ai-plan after brainstorm approval.\n"


@pytest.mark.unit
def test_consolidated_feature_pr_idle_slot_passes_spec_lint(tmp_path: Path) -> None:
    """A consolidated feature PR (slot cleared to placeholder + archived spec
    dir present) must keep ``spec_lint --check`` at exit 0. Mirrors the
    post-Step-14b state of every D-167-07 feature PR."""
    spec_path = _write(tmp_path, _IDLE_SPEC)
    (tmp_path / "plan.md").write_text(_IDLE_PLAN, encoding="utf-8")
    # The consolidation archived the real spec under archive/spec-NNN-<slug>/.
    archive = tmp_path / "archive" / "spec-167-lifecycle-execution-gaps"
    archive.mkdir(parents=True)
    (archive / "spec.md").write_text("---\nspec: spec-167\n---\n# shipped\n", "utf-8")

    rc = _spec_lint_cli.main(["--check", str(spec_path)])
    assert rc == 0, "idle slot after consolidation must not red the gate"


@pytest.mark.unit
def test_non_idle_malformed_spec_still_blocks(tmp_path: Path) -> None:
    """Control: the exit-0 above is the idle short-circuit, NOT a blanket pass.
    A non-placeholder spec missing required sections must still fail."""
    spec_path = _write(
        tmp_path, "---\nspec: spec-9\ntitle: t\nstatus: approved\neffort: small\n---\n# X\n"
    )
    rc = _spec_lint_cli.main(["--check", str(spec_path)])
    assert rc != 0, "a real but malformed spec must still block"


@pytest.mark.unit
def test_plan_shipped_without_tasks_passes(tmp_path: Path) -> None:
    plan = (
        "---\nspec: spec-test\ntitle: T\nstatus: shipped-pending-pr-merge\n---\n"
        "# Plan — shipped aggregate index\n\n- **Wave 1**: summary\n- **Wave 2**: summary\n"
    )
    spec_path = _spec_and_plan(tmp_path, plan)
    results = check_plan(spec_path)
    assert [r for r in results if r.severity == "BLOCKER"] == []


@pytest.mark.unit
def test_plan_invalid_marker_is_blocker(tmp_path: Path) -> None:
    plan = (
        "---\nspec: spec-test\ntitle: T\nstatus: in-progress\n---\n"
        "# Plan\n\n- [?] **T-1.1**: bad marker\n- [x] **T-1.2**: ok\n"
    )
    spec_path = _spec_and_plan(tmp_path, plan)
    results = check_plan(spec_path)
    assert any(
        r.check_name == "plan_task_marker_invalid" and r.severity == "BLOCKER" for r in results
    )


@pytest.mark.unit
def test_plan_missing_frontmatter_is_blocker(tmp_path: Path) -> None:
    plan = "# Plan\n\n- [x] T-1.1: thing\n"
    spec_path = _spec_and_plan(tmp_path, plan)
    results = check_plan(spec_path)
    assert any(r.check_name == "plan_frontmatter_missing" for r in results)


@pytest.mark.unit
def test_plan_invalid_status_enum_is_blocker(tmp_path: Path) -> None:
    plan = "---\nspec: x\ntitle: T\nstatus: weird-state\n---\n# Plan\n\n- [x] T-1.1: a\n"
    spec_path = _spec_and_plan(tmp_path, plan)
    results = check_plan(spec_path)
    assert any(r.check_name == "plan_status_invalid" and r.severity == "BLOCKER" for r in results)


@pytest.mark.unit
def test_plan_duplicate_task_id_is_advisory(tmp_path: Path) -> None:
    plan = (
        "---\nspec: x\ntitle: T\nstatus: in-progress\n---\n# Plan\n\n"
        "- [x] **T-1.1**: first\n- [ ] **T-1.1**: dup\n"
    )
    spec_path = _spec_and_plan(tmp_path, plan)
    results = check_plan(spec_path)
    assert any(
        r.check_name == "plan_task_id_duplicate" and r.severity == "ADVISORY" for r in results
    )
    assert [r for r in results if r.severity == "BLOCKER"] == []


@pytest.mark.unit
def test_plan_execution_route_valid_metadata_passes(tmp_path: Path) -> None:
    plan = (
        "---\n"
        "spec: spec-test\n"
        "title: T\n"
        "status: approved\n"
        "execution_route:\n"
        "  version: 1\n"
        "  spec: spec-test\n"
        "  executor: build\n"
        "  automation: hitl\n"
        "  concern_count: 1\n"
        "  estimated_files: 3\n"
        '  reason: "Single-concern plan."\n'
        '  safe_next_command: "/ai-build"\n'
        "---\n"
        "# Plan\n\n"
        "- [ ] **T-1.1**: pending\n"
    )
    spec_path = _spec_and_plan(tmp_path, plan)
    results = check_plan(spec_path)
    route_results = [r for r in results if r.check_name.startswith("plan_execution_route")]
    assert route_results == []


@pytest.mark.unit
def test_plan_execution_route_rejects_unknown_executor(tmp_path: Path) -> None:
    plan = (
        "---\n"
        "spec: spec-test\n"
        "title: T\n"
        "status: approved\n"
        "execution_route:\n"
        "  version: 1\n"
        "  spec: spec-test\n"
        "  executor: serial\n"
        "  automation: hitl\n"
        "  concern_count: 1\n"
        "  estimated_files: 3\n"
        '  reason: "No host-admission states are valid executors."\n'
        '  safe_next_command: "/ai-build"\n'
        "---\n"
        "# Plan\n\n"
        "- [ ] **T-1.1**: pending\n"
    )
    spec_path = _spec_and_plan(tmp_path, plan)
    results = check_plan(spec_path)
    assert any(
        r.check_name == "plan_execution_route_executor_invalid" and r.severity == "BLOCKER"
        for r in results
    )


@pytest.mark.unit
def test_plan_execution_route_command_must_match_executor(tmp_path: Path) -> None:
    plan = (
        "---\n"
        "spec: spec-test\n"
        "title: T\n"
        "status: approved\n"
        "execution_route:\n"
        "  version: 1\n"
        "  spec: spec-test\n"
        "  executor: autopilot\n"
        "  automation: hitl\n"
        "  concern_count: 3\n"
        "  estimated_files: 12\n"
        '  reason: "Multi-concern plan."\n'
        '  safe_next_command: "/ai-build"\n'
        "---\n"
        "# Plan\n\n"
        "- [ ] **T-1.1**: pending\n"
    )
    spec_path = _spec_and_plan(tmp_path, plan)
    results = check_plan(spec_path)
    assert any(
        r.check_name == "plan_execution_route_command_mismatch" and r.severity == "BLOCKER"
        for r in results
    )


@pytest.mark.unit
def test_plan_execution_route_cannot_duplicate_approval_state(tmp_path: Path) -> None:
    plan = (
        "---\n"
        "spec: spec-test\n"
        "title: T\n"
        "status: approved\n"
        "execution_route:\n"
        "  version: 1\n"
        "  spec: spec-test\n"
        "  executor: build\n"
        "  automation: hitl\n"
        "  concern_count: 1\n"
        "  estimated_files: 3\n"
        '  reason: "Single-concern plan."\n'
        '  safe_next_command: "/ai-build"\n'
        "  approved: true\n"
        "---\n"
        "# Plan\n\n"
        "- [ ] **T-1.1**: pending\n"
    )
    spec_path = _spec_and_plan(tmp_path, plan)
    results = check_plan(spec_path)
    assert any(
        r.check_name == "plan_execution_route_approval_duplicate" and r.severity == "BLOCKER"
        for r in results
    )


# ---------------------------------------------------------------------------
# spec-188 D-188-02 — strict YAML frontmatter validation (fail closed)
# ---------------------------------------------------------------------------


def test_frontmatter_malformed_yaml_colon_title_is_blocker(tmp_path: Path) -> None:
    # An unquoted title whose mid-value colon breaks YAML must be a BLOCKER.
    # The stdlib partition parser silently accepted it (that is how the
    # spec-186 bug shipped); spec_lint now strict-parses the block.
    spec_path = tmp_path / "spec.md"
    spec_path.write_text(
        "---\n"
        "spec: spec-999\n"
        "title: spec-999 — Thing: subtitle that breaks yaml\n"
        "status: approved\n"
        "effort: small\n"
        "summary: valid one-line summary\n"
        "---\n\n# Body\n",
        encoding="utf-8",
    )
    results = check_frontmatter(spec_path)
    assert any(
        r.check_name == "frontmatter_yaml_invalid" and r.severity == "BLOCKER" for r in results
    )


def test_frontmatter_quoted_colon_title_passes_yaml(tmp_path: Path) -> None:
    # The quoted form (the spec-186 fix) parses cleanly — no yaml_invalid finding.
    spec_path = tmp_path / "spec.md"
    spec_path.write_text(
        "---\n"
        "spec: spec-999\n"
        'title: "spec-999 — Thing: subtitle that is now quoted"\n'
        "status: approved\n"
        "effort: small\n"
        "summary: valid one-line summary\n"
        "---\n\n# Body\n",
        encoding="utf-8",
    )
    results = check_frontmatter(spec_path)
    assert not any(r.check_name == "frontmatter_yaml_invalid" for r in results)
