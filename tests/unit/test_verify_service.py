"""Tests for ai_engineering.verify.service — fake-based, behavior-focused.

Uses FakeSubprocess instead of monkeypatch mocks. Tests WHAT the service
reports, not HOW it calls subprocess. TDD-ready (Type-E) exemplar.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ai_engineering.verify.scoring import FindingSeverity, Verdict
from ai_engineering.verify.service import (
    MODES,
    verify_a11y,
    verify_architecture,
    verify_feature,
    verify_governance,
    verify_performance,
    verify_platform,
    verify_quality,
    verify_security,
)

pytestmark = pytest.mark.unit


# ── Fake subprocess ───────────────────────────────────────────────────────


class FakeSubprocess:
    """Configurable fake for subprocess.run — replaces _run() in service."""

    def __init__(self) -> None:
        self._responses: dict[str, subprocess.CompletedProcess[str]] = {}

    def set_response(
        self,
        cmd_contains: str,
        *,
        returncode: int = 0,
        stdout: str = "",
    ) -> None:
        self._responses[cmd_contains] = subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=stdout, stderr=""
        )

    def __call__(
        self,
        cmd: list[str],
        *_args: object,
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        cmd_str = " ".join(cmd)
        for key, response in self._responses.items():
            if key in cmd_str:
                return response
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")


@pytest.fixture()
def fake_run(monkeypatch: pytest.MonkeyPatch) -> FakeSubprocess:
    """Inject a FakeSubprocess into the verify service."""
    fake = FakeSubprocess()
    monkeypatch.setattr("ai_engineering.verify.service._run", fake)
    return fake


# ── verify_quality ────────────────────────────────────────────────────────


class TestVerifyQuality:
    def test_clean_run_returns_score_100(self, fake_run: FakeSubprocess) -> None:
        # Arrange — ruff returns clean
        fake_run.set_response("ruff", returncode=0, stdout="")

        # Act
        result = verify_quality(Path("/fake"))

        # Assert
        assert result.score == 100
        assert result.verdict == Verdict.PASS
        assert result.specialists[0].name == "quality"

    def test_ruff_findings_reduce_score(self, fake_run: FakeSubprocess) -> None:
        # Arrange — ruff reports 2 lint violations
        findings = [
            {
                "message": "F401 unused import",
                "filename": "foo.py",
                "location": {"row": 10},
            },
            {
                "message": "E501 line too long",
                "filename": "bar.py",
                "location": {"row": 5},
            },
        ]
        fake_run.set_response("ruff", returncode=1, stdout=json.dumps(findings))

        # Act
        result = verify_quality(Path("/fake"))

        # Assert
        assert result.score < 100
        assert len(result.findings) >= 2
        assert all(f.category == "lint" for f in result.findings)

    def test_ruff_json_decode_error_still_reports_finding(self, fake_run: FakeSubprocess) -> None:
        # Arrange — ruff returns non-JSON output
        fake_run.set_response("ruff", returncode=1, stdout="not valid json")

        # Act
        result = verify_quality(Path("/fake"))

        # Assert — should add a finding about non-JSON output
        assert any("non-JSON" in f.message for f in result.findings)


# ── verify_security ───────────────────────────────────────────────────────


class TestVerifySecurity:
    def test_clean_scan_returns_score_100(self, fake_run: FakeSubprocess) -> None:
        # Arrange — both tools return clean
        fake_run.set_response("gitleaks", returncode=0, stdout="")
        fake_run.set_response("pip-audit", returncode=0, stdout="")

        # Act
        result = verify_security(Path("/fake"))

        # Assert
        assert result.score == 100

    def test_gitleaks_findings_are_blocker_severity(self, fake_run: FakeSubprocess) -> None:
        # Arrange — gitleaks detects a secret
        leaks = [{"Description": "AWS Key", "File": "config.py", "StartLine": 5}]
        fake_run.set_response("gitleaks", returncode=1, stdout=json.dumps(leaks))

        # Act
        result = verify_security(Path("/fake"))

        # Assert — secrets are BLOCKER severity
        secret_findings = [f for f in result.findings if f.category == "secrets"]
        assert len(secret_findings) == 1
        assert secret_findings[0].severity == FindingSeverity.BLOCKER

    def test_pip_audit_vulnerabilities_are_critical_severity(
        self, fake_run: FakeSubprocess
    ) -> None:
        # Arrange — pip-audit finds a vulnerability
        audit = {
            "dependencies": [
                {
                    "name": "requests",
                    "vulns": [{"id": "CVE-2023-1234"}],
                }
            ]
        }
        fake_run.set_response("pip-audit", returncode=1, stdout=json.dumps(audit))

        # Act
        result = verify_security(Path("/fake"))

        # Assert — dependency vulns are CRITICAL
        dep_findings = [f for f in result.findings if f.category == "dependency"]
        assert len(dep_findings) == 1
        assert dep_findings[0].severity == FindingSeverity.CRITICAL
        assert dep_findings[0].specialist == "security"


# ── verify_governance ─────────────────────────────────────────────────────


class TestVerifyGovernance:
    def test_validate_pass_returns_clean_score(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange — validate_content_integrity returns empty report
        from ai_engineering.validator._shared import IntegrityReport

        monkeypatch.setattr(
            "ai_engineering.verify.service.validate_content_integrity",
            lambda _root, **_kw: IntegrityReport(),
        )

        # Act
        result = verify_governance(Path("/fake"))

        # Assert
        assert result.score == 100
        assert not result.findings

    def test_validate_failure_reports_critical(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange — report with a FAIL check
        from ai_engineering.validator._shared import (
            IntegrityCategory,
            IntegrityCheckResult,
            IntegrityReport,
            IntegrityStatus,
        )

        report = IntegrityReport(
            checks=[
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name="mirror-mismatch",
                    status=IntegrityStatus.FAIL,
                    message="CLAUDE.md mirror out of sync",
                    file_path="CLAUDE.md",
                ),
            ]
        )
        monkeypatch.setattr(
            "ai_engineering.verify.service.validate_content_integrity",
            lambda _root, **_kw: report,
        )

        # Act
        result = verify_governance(Path("/fake"))

        # Assert
        assert result.score < 100
        assert len(result.findings) == 1
        assert result.findings[0].severity == FindingSeverity.CRITICAL
        assert result.findings[0].category == "mirror-sync"

    def test_validate_warn_reports_minor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange — report with a WARN check
        from ai_engineering.validator._shared import (
            IntegrityCategory,
            IntegrityCheckResult,
            IntegrityReport,
            IntegrityStatus,
        )

        report = IntegrityReport(
            checks=[
                IntegrityCheckResult(
                    category=IntegrityCategory.SKILL_FRONTMATTER,
                    name="optional-field-missing",
                    status=IntegrityStatus.WARN,
                    message="Optional field 'os' missing",
                    file_path="skills/ai-test/SKILL.md",
                ),
            ]
        )
        monkeypatch.setattr(
            "ai_engineering.verify.service.validate_content_integrity",
            lambda _root, **_kw: report,
        )

        # Act
        result = verify_governance(Path("/fake"))

        # Assert
        assert result.score == 99  # MINOR penalty = 1
        assert len(result.findings) == 1
        assert result.findings[0].severity == FindingSeverity.MINOR
        assert result.findings[0].category == "skill-frontmatter"


# ── verify_platform ───────────────────────────────────────────────────────


class TestVerifyPlatform:
    def test_aggregates_findings_from_all_modes(
        self, fake_run: FakeSubprocess, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange — ruff finds 1 issue, gitleaks finds 1 leak
        fake_run.set_response(
            "ruff",
            returncode=1,
            stdout=json.dumps([{"message": "lint", "filename": "a.py", "location": {"row": 1}}]),
        )
        fake_run.set_response(
            "gitleaks",
            returncode=1,
            stdout=json.dumps([{"Description": "key", "File": "b.py", "StartLine": 2}]),
        )
        # Governance now calls validate_content_integrity directly — mock it
        from ai_engineering.validator._shared import IntegrityReport

        monkeypatch.setattr(
            "ai_engineering.verify.service.validate_content_integrity",
            lambda _root, **_kw: IntegrityReport(),
        )

        # Act
        result = verify_platform(Path("/fake"))

        # Assert — findings from quality + security combined
        categories = {f.category for f in result.findings}
        assert "lint" in categories
        assert "secrets" in categories
        assert [specialist.name for specialist in result.specialists] == [
            "governance",
            "security",
            "architecture",
            "quality",
            "performance",
            "a11y",
            "feature",
        ]
        assert {specialist.runner for specialist in result.specialists} == {
            "macro-agent-1",
            "macro-agent-2",
        }

    def test_normal_profile_preserves_original_specialist_attribution(
        self, fake_run: FakeSubprocess, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_run.set_response(
            "ruff",
            returncode=1,
            stdout=json.dumps([{"message": "lint", "filename": "a.py", "location": {"row": 1}}]),
        )
        from ai_engineering.validator._shared import IntegrityReport

        monkeypatch.setattr(
            "ai_engineering.verify.service.validate_content_integrity",
            lambda _root, **_kw: IntegrityReport(),
        )

        result = verify_platform(Path("/fake"))

        lint_finding = next(finding for finding in result.findings if finding.category == "lint")
        assert lint_finding.specialist == "quality"
        assert lint_finding.runner == "macro-agent-2"

    def test_full_profile_sets_runner_per_specialist(
        self, fake_run: FakeSubprocess, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_run.set_response("ruff", returncode=0, stdout="")
        fake_run.set_response("gitleaks", returncode=0, stdout="")
        fake_run.set_response("pip-audit", returncode=0, stdout="")
        from ai_engineering.validator._shared import IntegrityReport

        monkeypatch.setattr(
            "ai_engineering.verify.service.validate_content_integrity",
            lambda _root, **_kw: IntegrityReport(),
        )

        result = verify_platform(Path("/fake"), profile="full")

        assert {specialist.runner for specialist in result.specialists} == {
            "governance",
            "security",
            "architecture",
            "quality",
            "performance",
            "a11y",
            "feature",
        }


class TestAdditionalSpecialists:
    def test_verify_architecture_reports_internal_cycle(self, tmp_path: Path) -> None:
        root = tmp_path
        package = root / "src" / "ai_engineering" / "demo"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "a.py").write_text("from ai_engineering.demo import b\n", encoding="utf-8")
        (package / "b.py").write_text("from ai_engineering.demo import a\n", encoding="utf-8")

        result = verify_architecture(root)

        assert result.findings
        assert result.findings[0].category == "cycle"

    def test_verify_a11y_marks_repo_without_ui_as_not_applicable(self, tmp_path: Path) -> None:
        result = verify_a11y(tmp_path)

        assert result.specialists[0].applicable is False
        assert "No frontend or UI files" in result.specialists[0].rationale

    def test_verify_performance_marks_missing_benchmarks_as_not_applicable(
        self, tmp_path: Path
    ) -> None:
        result = verify_performance(tmp_path)

        assert result.specialists[0].applicable is False
        assert "No benchmark" in result.specialists[0].rationale

    def test_verify_feature_reads_active_spec_and_plan(self, tmp_path: Path) -> None:
        spec_dir = tmp_path / ".ai-engineering" / "specs"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text(
            "---\nstatus: approved\napproval: approved\n---\n# Spec\n",
            encoding="utf-8",
        )
        (spec_dir / "plan.md").write_text(
            "---\ntotal: 1\ncompleted: 0\n---\n# Plan\n", encoding="utf-8"
        )

        result = verify_feature(tmp_path)

        assert result.findings == []
        assert result.specialists[0].applicable is True


# ── MODES dict ────────────────────────────────────────────────────────────


class TestModes:
    def test_modes_has_eight_entries(self) -> None:
        assert len(MODES) == 8

    def test_modes_keys_cover_all_specialists_and_platform(self) -> None:
        assert set(MODES.keys()) == {
            "a11y",
            "architecture",
            "feature",
            "governance",
            "performance",
            "quality",
            "security",
            "platform",
        }

    def test_all_modes_are_callable(self) -> None:
        for name, func in MODES.items():
            assert callable(func), f"MODES['{name}'] is not callable"


# ── verify_cmd CLI --json flag ────────────────────────────────────────────


class TestVerifyCmdJsonFlag:
    """Tests for verify_cmd local --json output."""

    def test_local_json_flag_outputs_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """verify_cmd with output_json=True produces valid JSON."""
        from ai_engineering.cli_commands.verify_cmd import verify_cmd
        from ai_engineering.verify.scoring import VerifyScore

        score = VerifyScore(raw=100, findings=[])
        monkeypatch.setattr(
            "ai_engineering.cli_commands.verify_cmd.MODES",
            {"security": lambda _root, profile="normal": score},
        )
        monkeypatch.setattr(
            "ai_engineering.cli_commands.verify_cmd.resolve_project_root",
            lambda _t: Path("/tmp"),
        )
        monkeypatch.setattr(
            "ai_engineering.cli_commands.verify_cmd.is_json_mode",
            lambda: False,
        )
        captured: list[str] = []
        monkeypatch.setattr(
            "typer.echo",
            lambda msg=None, **kw: captured.append(str(msg)) if msg else None,
        )

        verify_cmd(mode="security", target=None, output_json=True)

        output = "\n".join(captured)
        parsed = json.loads(output)
        assert parsed["mode"] == "security"
        assert parsed["profile"] == "normal"
        assert parsed["score"] == 100
        assert parsed["verdict"] == "PASS"

    def test_local_json_flag_includes_specialist_and_runner_details(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """verify_cmd preserves specialist attribution in JSON output."""
        from ai_engineering.cli_commands.verify_cmd import verify_cmd
        from ai_engineering.verify.scoring import (
            FindingSeverity,
            SpecialistResult,
            VerifyScore,
        )

        specialist = SpecialistResult(
            name="security",
            label="Security",
            runner="macro-agent-1",
        )
        specialist.add(
            FindingSeverity.BLOCKER,
            "secrets",
            "Leak detected",
            file="config.py",
            line=4,
        )
        score = VerifyScore(
            mode="platform",
            profile="normal",
            findings=list(specialist.findings),
            specialists=[specialist],
        )
        monkeypatch.setattr(
            "ai_engineering.cli_commands.verify_cmd.MODES",
            {"platform": lambda _root, profile="normal": score},
        )
        monkeypatch.setattr(
            "ai_engineering.cli_commands.verify_cmd.resolve_project_root",
            lambda _t: Path("/tmp"),
        )
        monkeypatch.setattr(
            "ai_engineering.cli_commands.verify_cmd.is_json_mode",
            lambda: False,
        )
        captured: list[str] = []
        monkeypatch.setattr(
            "typer.echo",
            lambda msg=None, **_kw: captured.append(str(msg)) if msg else None,
        )

        verify_cmd(mode="platform", target=None, output_json=True)

        parsed = json.loads("\n".join(captured))
        assert parsed["specialists"][0]["name"] == "security"
        assert parsed["specialists"][0]["runner"] == "macro-agent-1"
        assert parsed["findings"][0]["specialist"] == "security"
        assert parsed["findings"][0]["runner"] == "macro-agent-1"
