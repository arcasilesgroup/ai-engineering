"""Phase 4 RED: skill-audit advisory script + audit-report.json contract (spec-106 G-4).

These tests assert that ``scripts/skill-audit.sh`` exists and runs in
advisory mode (exits 0 even when sub-threshold skills are found), iterates
over every ``.claude/skills/ai-*/SKILL.md`` file, and emits an
``audit-report.json`` document with the canonical schema (array of
``{skill, result: {score, reason}}`` entries).

Marked ``spec_106_red``: excluded from the default CI run until Phase 4
delivers the GREEN script implementation, the audit-report.json contract,
and graceful handling of the missing ``ai-eng skill eval`` subcommand.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_AUDIT_SCRIPT = REPO_ROOT / "scripts" / "skill-audit.sh"
AUDIT_REPORT = REPO_ROOT / "audit-report.json"


@pytest.mark.spec_106_red
def test_skill_audit_script_exists() -> None:
    """Phase 4 must create the skill-audit advisory script."""
    # Deferred import per spec-106 RED contract.
    raise NotImplementedError(
        "spec-106 Phase 4 T-4.1: scripts/skill-audit.sh not yet created. "
        "Expected file: scripts/skill-audit.sh with set -euo pipefail and "
        "iteration over .claude/skills/ai-*/SKILL.md."
    )


@pytest.mark.spec_106_red
def test_skill_audit_runs_advisory_exit_zero() -> None:
    """Running the script must exit 0 even when sub-threshold skills exist.

    The script is advisory in spec-106 (D-106-04). Sub-threshold skills are
    listed but never block CI. Hard-gate landed in a future spec when
    >=90% of skills meet the threshold.
    """
    raise NotImplementedError(
        "spec-106 Phase 4 T-4.3: bash scripts/skill-audit.sh must exit 0 "
        "in advisory mode. Subprocess invocation will go here."
    )


@pytest.mark.spec_106_red
def test_audit_report_emitted_with_array_schema() -> None:
    """Running the script must emit audit-report.json with array schema.

    The report is a JSON array with one entry per skill. Each entry is an
    object with the canonical shape ``{skill, result: {score, reason}}``.
    Schema details validated by tests/unit/test_audit_report_schema.py;
    this integration test only confirms the file exists and parses as a
    JSON array after script execution.
    """
    raise NotImplementedError(
        "spec-106 Phase 4 T-4.3: scripts/skill-audit.sh must emit "
        "audit-report.json as a JSON array after execution. JSON-parsable "
        "and length >= 1 entry."
    )


@pytest.mark.spec_106_red
def test_audit_report_has_entry_per_skill() -> None:
    """The report must contain one entry per .claude/skills/ai-*/SKILL.md file.

    The script iterates the canonical skill directory pattern and emits a
    record per skill. Missing entries indicate the iteration logic skipped
    a skill or the JSON aggregation lost a record.
    """
    raise NotImplementedError(
        "spec-106 Phase 4 T-4.3: audit-report.json must contain one entry "
        "per .claude/skills/ai-*/SKILL.md file (count parity assertion)."
    )
