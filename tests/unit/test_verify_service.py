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
    verify_governance,
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


# ── verify_governance ─────────────────────────────────────────────────────


class TestVerifyGovernance:
    def test_validate_pass_returns_clean_score(self, fake_run: FakeSubprocess) -> None:
        # Arrange — ai-eng validate succeeds
        fake_run.set_response("ai-eng", returncode=0, stdout="")

        # Act
        result = verify_governance(Path("/fake"))

        # Assert
        assert result.score == 100
        assert not result.findings

    def test_validate_failure_reports_critical_finding(self, fake_run: FakeSubprocess) -> None:
        # Arrange — ai-eng validate fails
        fake_run.set_response("ai-eng", returncode=1, stdout="")

        # Act
        result = verify_governance(Path("/fake"))

        # Assert
        assert result.score < 100
        assert any(f.category == "integrity" for f in result.findings)


# ── verify_platform ───────────────────────────────────────────────────────


class TestVerifyPlatform:
    def test_aggregates_findings_from_all_modes(self, fake_run: FakeSubprocess) -> None:
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

        # Act
        result = verify_platform(Path("/fake"))

        # Assert — findings from quality + security combined
        categories = {f.category for f in result.findings}
        assert "lint" in categories
        assert "secrets" in categories


# ── MODES dict ────────────────────────────────────────────────────────────


class TestModes:
    def test_modes_has_four_entries(self) -> None:
        assert len(MODES) == 4

    def test_modes_keys_are_quality_security_governance_platform(self) -> None:
        assert set(MODES.keys()) == {
            "quality",
            "security",
            "governance",
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
            {"security": lambda _root: score},
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
        assert parsed["score"] == 100
        assert parsed["verdict"] == "PASS"
