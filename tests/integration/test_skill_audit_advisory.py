"""Phase 4 GREEN: skill-audit advisory script + audit-report.json contract (spec-106 G-4).

These tests assert that ``scripts/skill-audit.sh`` exists and runs in
advisory mode (exits 0 even when sub-threshold skills are found), iterates
over every ``.claude/skills/ai-*/SKILL.md`` file, and emits an
``audit-report.json`` document with the canonical schema (array of
``{skill, result: {score, reason}}`` entries).

Mode: advisory only (spec-106 D-106-04, NG-2). The script never blocks
CI; sub-threshold skills are surfaced via stdout + the JSON report for
downstream dashboards. Hard-gate enforcement is deferred to a future spec
when >=90% of skills meet the threshold.

Platform: POSIX-only. ``scripts/skill-audit.sh`` is a bash shell script
that requires (a) the POSIX execute bit (Windows file systems do not
preserve it across git checkout) and (b) a real bash interpreter on PATH
(GitHub Actions ``windows-latest`` runners only ship a stub that triggers
WSL, which has no installed distribution). The Linux + macOS integration
matrices remain authoritative — Windows skips this module.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="skill-audit.sh is a bash script; Windows runners lack execute-bit + bash",
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_AUDIT_SCRIPT = REPO_ROOT / "scripts" / "skill-audit.sh"
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"


def _expected_skill_names() -> list[str]:
    """Resolve the canonical list of ai-* skill directory names."""
    return sorted(p.parent.name for p in SKILLS_DIR.glob("ai-*/SKILL.md"))


def _run_audit(cwd: Path) -> tuple[subprocess.CompletedProcess[str], Path]:
    """Invoke the audit script in ``cwd`` and return (result, audit_report_path)."""
    result = subprocess.run(
        ["bash", str(SKILL_AUDIT_SCRIPT)],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    return result, cwd / "audit-report.json"


def test_skill_audit_script_exists() -> None:
    """Phase 4 must create the skill-audit advisory script."""
    assert SKILL_AUDIT_SCRIPT.exists(), (
        f"Missing script: {SKILL_AUDIT_SCRIPT}. Phase 4 T-4.1 must create the "
        "advisory audit script per spec-106 D-106-04."
    )
    # Script must be executable so `bash scripts/skill-audit.sh` and direct
    # invocation both work; mirrors Phase 4 T-4.2.
    assert SKILL_AUDIT_SCRIPT.stat().st_mode & 0o111, (
        f"{SKILL_AUDIT_SCRIPT} must be executable (chmod +x). T-4.2 contract."
    )


def test_skill_audit_runs_advisory_exit_zero(tmp_path: Path) -> None:
    """Running the script must exit 0 even when sub-threshold skills exist.

    The script is advisory in spec-106 (D-106-04). Sub-threshold skills are
    listed but never block CI. Hard-gate landed in a future spec when
    >=90% of skills meet the threshold.
    """
    result, _ = _run_audit(tmp_path)
    assert result.returncode == 0, (
        f"skill-audit.sh exited {result.returncode} (expected 0 advisory). "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "Audit complete." in result.stdout, (
        f"Expected 'Audit complete.' summary in stdout, got: {result.stdout!r}"
    )


def test_audit_report_emitted_with_array_schema(tmp_path: Path) -> None:
    """Running the script must emit audit-report.json with array schema.

    The report is a JSON array with one entry per skill. Each entry is an
    object with the canonical shape ``{skill, result: {score, reason}}``.
    Schema details validated by tests/unit/test_audit_report_schema.py;
    this integration test only confirms the file exists and parses as a
    JSON array after script execution.
    """
    result, audit_report = _run_audit(tmp_path)
    assert result.returncode == 0, f"audit failed: {result.stderr!r}"
    assert audit_report.exists(), (
        f"audit-report.json not created at {audit_report} after script run"
    )
    payload = json.loads(audit_report.read_text(encoding="utf-8"))
    assert isinstance(payload, list), (
        f"audit-report.json root must be a JSON array, got {type(payload).__name__}"
    )
    assert len(payload) >= 1, "audit-report.json must contain >=1 entry"
    # Schema spot-check: each entry has the canonical shape.
    for index, entry in enumerate(payload):
        assert isinstance(entry, dict), f"entry[{index}] must be an object"
        assert isinstance(entry.get("skill"), str), f"entry[{index}].skill must be string"
        assert isinstance(entry.get("result"), dict), f"entry[{index}].result must be object"
        result_obj = entry["result"]
        assert isinstance(result_obj.get("score"), (int, float)), (
            f"entry[{index}].result.score must be numeric"
        )
        assert isinstance(result_obj.get("reason"), str) and result_obj["reason"], (
            f"entry[{index}].result.reason must be non-empty string"
        )


def test_audit_report_has_entry_per_skill(tmp_path: Path) -> None:
    """The report must contain one entry per .claude/skills/ai-*/SKILL.md file.

    The script iterates the canonical skill directory pattern and emits a
    record per skill. Missing entries indicate the iteration logic skipped
    a skill or the JSON aggregation lost a record.
    """
    result, audit_report = _run_audit(tmp_path)
    assert result.returncode == 0, f"audit failed: {result.stderr!r}"
    payload = json.loads(audit_report.read_text(encoding="utf-8"))
    actual_names = sorted(entry["skill"] for entry in payload)
    expected_names = _expected_skill_names()
    assert actual_names == expected_names, (
        f"audit-report.json skill set diverges from .claude/skills/ai-*/SKILL.md.\n"
        f"missing: {sorted(set(expected_names) - set(actual_names))}\n"
        f"extra:   {sorted(set(actual_names) - set(expected_names))}"
    )
