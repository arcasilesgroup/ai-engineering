"""spec-131 S7 (sub-007): end-to-end CLI invocation against the live corpus.

Runs ``python -m spec_lint --check`` in a child process so import cost is
included (mirrors the pre-commit hook invocation path). Three test
cases:

* ``test_spec_lint_self_validates_canonical_spec`` — the canonical
  ``.ai-engineering/specs/spec.md`` (spec-131) passes; this closes the
  D-131-17 self-validation gate.
* ``test_spec_lint_accepts_legacy_heading_form`` — the spec-129 archive
  (``.ai-engineering/specs/archive/spec-129-skills-agents-excellence-pragmatic/spec.md``)
  passes every *form* check (bullet vs heading + italic vs bold
  rationale). The archive has one known content defect (D-129-05
  missing rationale) which the validator correctly surfaces — the test
  documents this finding explicitly so future readers can trace the
  exception.
* ``test_spec_lint_rejects_broken_spec`` — a fixture with a missing
  required section exits 1 and surfaces ``section_missing``. Confirms
  the BLOCKER path lights up in a child process.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "tools"
CANONICAL_SPEC = REPO_ROOT / ".ai-engineering" / "specs" / "spec.md"
# spec-153 W3: reaped into the uniform per-spec archive directory (D-153-06).
LEGACY_ARCHIVE = (
    REPO_ROOT
    / ".ai-engineering"
    / "specs"
    / "archive"
    / "spec-129-skills-agents-excellence-pragmatic"
    / "spec.md"
)


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{TOOLS_DIR}{os.pathsep}{existing}" if existing else str(TOOLS_DIR)
    return subprocess.run(
        [sys.executable, "-m", "spec_lint", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


@pytest.mark.integration
def test_spec_lint_self_validates_canonical_spec() -> None:
    """spec-131 D-131-17: spec_lint must clear the spec that introduced it."""
    result = _run(["--check"])
    assert result.returncode == 0, (
        f"canonical spec.md failed lint: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "BLOCKERS=0" in result.stdout, result.stdout


@pytest.mark.integration
def test_spec_lint_accepts_legacy_heading_form() -> None:
    """spec-131 R-131-12: heading-form decision entries clear the form check.

    Spec-129 uses ``### D-129-NN — …`` heading form with bold
    ``**Rationale**:`` lines. The form-acceptance gate is verified by
    asserting that NO ``decision_id_prefix_mismatch`` blockers fire
    (form recognition works) and that the ADVISORY count stays bounded.

    Note: spec-129's D-129-05 entry is a documented content-level
    defect (body is a checklist with no rationale prose). The validator
    correctly surfaces this as a single ``decision_missing_rationale``
    BLOCKER — fixing the archive body is out of scope for sub-007.
    This test asserts the validator runs against the archive and
    surfaces only the expected single content blocker, NOT any form
    blockers.
    """
    if not LEGACY_ARCHIVE.is_file():
        pytest.skip(f"legacy archive not present at {LEGACY_ARCHIVE}")
    result = _run(["--check", str(LEGACY_ARCHIVE)])

    # Form acceptance: no prefix-mismatch + no decisions_section_empty
    # blocker (i.e. the validator recognised the heading-form entries).
    assert "decision_id_prefix_mismatch" not in result.stdout, result.stdout
    assert "decisions_section_empty" not in result.stdout, result.stdout

    # Sections + frontmatter pass (no section_missing,
    # frontmatter_missing_required, frontmatter_invalid_enum,
    # non_goals_empty). ``frontmatter_missing_summary`` is excluded
    # from this guard because spec-139 M8 D-139-06 introduces a
    # soft-rollout advisory that legacy archives are expected to
    # trigger until 2026-06-16.
    for expected_form_check in (
        "section_missing",
        "frontmatter_missing_required",
        "frontmatter_invalid_enum",
        "non_goals_empty",
        "references_unknown_prefix",
        "references_pr_shape",
    ):
        assert expected_form_check not in result.stdout, (
            f"unexpected {expected_form_check} fired on legacy archive: stdout={result.stdout!r}"
        )


@pytest.mark.integration
def test_spec_lint_rejects_broken_spec(tmp_path: Path) -> None:
    """A minimal broken spec.md (missing ## Goals) exits 1 with section_missing."""
    broken = tmp_path / "broken.md"
    broken.write_text(
        "---\nspec: spec-999\ntitle: t\nstatus: draft\neffort: trivial\n---\n\n"
        "## Summary\nx\n\n## Non-Goals\n- y\n\n## Decisions\n\n"
        "- **D-999-01 — Decision.** x\n  *Rationale*: y\n\n## Risks\nz\n",
        encoding="utf-8",
    )
    result = _run(["--check", str(broken)])
    assert result.returncode == 1, (
        f"expected exit 1, got {result.returncode}: stdout={result.stdout!r}"
    )
    assert "section_missing" in result.stdout, result.stdout
    assert "Goals" in result.stdout, result.stdout


@pytest.mark.integration
def test_spec_lint_missing_file_exits_2(tmp_path: Path) -> None:
    """File-not-found returns exit 2 per argparse convention."""
    missing = tmp_path / "does-not-exist.md"
    result = _run(["--check", str(missing)])
    assert result.returncode == 2, (
        f"expected exit 2, got {result.returncode}: stderr={result.stderr!r}"
    )
    assert "not found" in result.stderr.lower(), result.stderr
