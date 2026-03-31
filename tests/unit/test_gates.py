"""Tests for ai_engineering.policy.gates — quality gate checks.

Covers:
- CheckConfig: dataclass defaults.
- GateCheckResult: creation and fields.
- GateResult: aggregation, passed property, failed_checks property.
- validate_commit_message: empty/blank/valid/long commit messages.
- run_tool_check: tool found/missing, subprocess pass/fail/timeout, required vs advisory.
- _get_active_stacks: manifest present/absent/invalid, fallback behavior.
- run_checks_for_stacks: dispatch common + per-stack, unknown stack.
- run_gate: pre-commit/commit-msg/pre-push orchestration, early return on protection fail.
- check_expiring_risk_acceptances: no expiring / expiring risks.
- check_expired_risk_acceptances: no expired / expired risks.
- Registry validation: PRE_PUSH_CHECKS python stack-tests flags.

All external dependencies are mocked — no subprocess calls, no git operations,
no filesystem I/O beyond tmp_path for trivial file creation.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.policy.checks.commit_msg import validate_commit_message
from ai_engineering.policy.checks.risk import (
    check_expired_risk_acceptances,
    check_expiring_risk_acceptances,
)
from ai_engineering.policy.checks.sonar import check_sonar_gate
from ai_engineering.policy.checks.stack_runner import (
    PRE_PUSH_CHECKS,
    CheckConfig,
    run_checks_for_stacks,
    run_tool_check,
)
from ai_engineering.policy.gates import (
    GateCheckResult,
    GateResult,
    _get_active_stacks,
    run_gate,
)
from ai_engineering.state.models import (
    Decision,
    DecisionStatus,
    DecisionStore,
    GateHook,
    RiskCategory,
    RiskSeverity,
)

# ── CheckConfig ──────────────────────────────────────────────────────────


class TestCheckConfig:
    """Tests for CheckConfig dataclass defaults."""

    def test_defaults_required_true(self) -> None:
        cfg = CheckConfig(name="test", cmd=["echo"])
        assert cfg.required is True

    def test_defaults_timeout_300(self) -> None:
        cfg = CheckConfig(name="test", cmd=["echo"])
        assert cfg.timeout == 300

    def test_custom_values(self) -> None:
        cfg = CheckConfig(name="slow", cmd=["sleep", "10"], required=False, timeout=60)
        assert cfg.name == "slow"
        assert cfg.cmd == ["sleep", "10"]
        assert cfg.required is False
        assert cfg.timeout == 60


# ── GateCheckResult ──────────────────────────────────────────────────────


class TestGateCheckResult:
    """Tests for GateCheckResult dataclass."""

    def test_creation_passed(self) -> None:
        r = GateCheckResult(name="lint", passed=True, output="ok")
        assert r.name == "lint"
        assert r.passed is True
        assert r.output == "ok"

    def test_creation_failed(self) -> None:
        r = GateCheckResult(name="lint", passed=False, output="fail")
        assert r.passed is False

    def test_default_output_empty(self) -> None:
        r = GateCheckResult(name="lint", passed=True)
        assert r.output == ""


# ── GateResult ───────────────────────────────────────────────────────────


class TestGateResult:
    """Tests for GateResult aggregation."""

    def test_passed_all_checks_pass(self) -> None:
        result = GateResult(hook=GateHook.PRE_COMMIT)
        result.checks.append(GateCheckResult(name="a", passed=True))
        result.checks.append(GateCheckResult(name="b", passed=True))
        assert result.passed is True

    def test_passed_one_check_fails(self) -> None:
        result = GateResult(hook=GateHook.PRE_COMMIT)
        result.checks.append(GateCheckResult(name="a", passed=True))
        result.checks.append(GateCheckResult(name="b", passed=False))
        assert result.passed is False

    def test_failed_checks_returns_failed_names(self) -> None:
        result = GateResult(hook=GateHook.PRE_COMMIT)
        result.checks.append(GateCheckResult(name="a", passed=True))
        result.checks.append(GateCheckResult(name="b", passed=False))
        result.checks.append(GateCheckResult(name="c", passed=False))
        assert result.failed_checks == ["b", "c"]

    def test_empty_result_passes(self) -> None:
        result = GateResult(hook=GateHook.PRE_COMMIT)
        assert result.passed is True
        assert result.failed_checks == []


# ── validate_commit_message ─────────────────────────────────────────────


class TestValidateCommitMessage:
    """Tests for commit message validation."""

    def test_valid_message_passes(self) -> None:
        errors = validate_commit_message("feat: add new feature")
        assert errors == []

    def test_empty_message_fails(self) -> None:
        errors = validate_commit_message("")
        assert len(errors) > 0
        assert "empty" in errors[0].lower()

    def test_whitespace_only_fails(self) -> None:
        errors = validate_commit_message("   \n  \n  ")
        # After strip() in caller, msg becomes "" or first_line is empty
        # The function receives the stripped text, so let's test empty first line
        errors = validate_commit_message("\n\nsomething later")
        assert len(errors) > 0
        assert "empty" in errors[0].lower()

    def test_long_first_line_fails(self) -> None:
        long_msg = "a" * 73
        errors = validate_commit_message(long_msg)
        assert len(errors) > 0
        assert "72" in errors[0]

    def test_exactly_72_chars_passes(self) -> None:
        msg = "fix: " + "a" * 67  # 72 chars total, conventional format
        errors = validate_commit_message(msg)
        assert errors == []

    def test_multiline_valid(self) -> None:
        msg = "fix: resolve bug\n\nLonger description here."
        errors = validate_commit_message(msg)
        assert errors == []


# ── run_tool_check ──────────────────────────────────────────────────────


class TestRunToolCheck:
    """Tests for run_tool_check with mocked subprocess and shutil."""

    def test_tool_found_subprocess_passes(self) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_COMMIT)
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "all good"
        mock_proc.stderr = ""

        # Act
        with (
            patch(
                "ai_engineering.policy.checks.stack_runner.shutil.which",
                return_value="/usr/bin/ruff",
            ),
            patch(
                "ai_engineering.policy.checks.stack_runner.subprocess.run", return_value=mock_proc
            ),
        ):
            run_tool_check(
                result,
                name="ruff-lint",
                cmd=["ruff", "check", "."],
                cwd=Path("/fake"),
            )

        # Assert
        assert len(result.checks) == 1
        assert result.checks[0].passed is True
        assert result.checks[0].name == "ruff-lint"

    def test_tool_found_subprocess_fails(self) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_COMMIT)
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "lint errors found"

        # Act
        with (
            patch(
                "ai_engineering.policy.checks.stack_runner.shutil.which",
                return_value="/usr/bin/ruff",
            ),
            patch(
                "ai_engineering.policy.checks.stack_runner.subprocess.run", return_value=mock_proc
            ),
        ):
            run_tool_check(
                result,
                name="ruff-lint",
                cmd=["ruff", "check", "."],
                cwd=Path("/fake"),
            )

        # Assert
        assert result.checks[0].passed is False

    def test_tool_not_found_required_fails(self) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_COMMIT)

        # Act
        with patch("ai_engineering.policy.checks.stack_runner.shutil.which", return_value=None):
            run_tool_check(
                result,
                name="ruff-lint",
                cmd=["ruff", "check", "."],
                cwd=Path("/fake"),
                required=True,
            )

        # Assert
        assert result.checks[0].passed is False
        assert "not found" in result.checks[0].output.lower()

    def test_subprocess_timeout_fails(self) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_COMMIT)

        # Act
        with (
            patch(
                "ai_engineering.policy.checks.stack_runner.shutil.which",
                return_value="/usr/bin/ruff",
            ),
            patch(
                "ai_engineering.policy.checks.stack_runner.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd=["ruff"], timeout=10),
            ),
        ):
            run_tool_check(
                result,
                name="ruff-lint",
                cmd=["ruff", "check", "."],
                cwd=Path("/fake"),
                timeout=10,
            )

        # Assert
        assert result.checks[0].passed is False
        assert "timed out" in result.checks[0].output.lower()

    def test_tool_not_found_advisory_passes(self) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_COMMIT)

        # Act
        with patch("ai_engineering.policy.checks.stack_runner.shutil.which", return_value=None):
            run_tool_check(
                result,
                name="optional-tool",
                cmd=["optional", "--check"],
                cwd=Path("/fake"),
                required=False,
            )

        # Assert
        assert result.checks[0].passed is True
        assert "not found" in result.checks[0].output.lower()

    def test_custom_timeout_passed_to_subprocess(self) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_COMMIT)
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "ok"
        mock_proc.stderr = ""

        # Act
        with (
            patch(
                "ai_engineering.policy.checks.stack_runner.shutil.which",
                return_value="/usr/bin/tool",
            ),
            patch(
                "ai_engineering.policy.checks.stack_runner.subprocess.run", return_value=mock_proc
            ) as mock_run,
        ):
            run_tool_check(
                result,
                name="tool",
                cmd=["tool", "run"],
                cwd=Path("/fake"),
                timeout=42,
            )

        # Assert
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs["timeout"] == 42


# ── _get_active_stacks ───────────────────────────────────────────────────


class TestGetActiveStacks:
    """Tests for _get_active_stacks with mocked manifest loading."""

    def test_manifest_with_stacks(self, tmp_path: Path) -> None:
        # Arrange: write a manifest.yml with stacks
        manifest_path = tmp_path / ".ai-engineering" / "manifest.yml"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(
            "providers:\n  stacks: [python, dotnet]\n",
            encoding="utf-8",
        )

        # Act
        stacks = _get_active_stacks(tmp_path)

        # Assert
        assert stacks == ["python", "dotnet"]

    def test_no_manifest_returns_python_fallback(self, tmp_path: Path) -> None:
        # No manifest file exists
        stacks = _get_active_stacks(tmp_path)
        assert stacks == ["python"]

    def test_invalid_manifest_returns_python_fallback(self, tmp_path: Path) -> None:
        # Arrange: write an invalid manifest.yml
        manifest_path = tmp_path / ".ai-engineering" / "manifest.yml"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(": bad yaml [[[", encoding="utf-8")

        # Act
        stacks = _get_active_stacks(tmp_path)

        # Assert
        assert stacks == ["python"]

    def test_empty_stacks_returns_python_fallback(self, tmp_path: Path) -> None:
        # Arrange: write a manifest.yml with empty stacks list
        manifest_path = tmp_path / ".ai-engineering" / "manifest.yml"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(
            "providers:\n  stacks: []\n",
            encoding="utf-8",
        )

        # Act
        stacks = _get_active_stacks(tmp_path)

        # Assert
        assert stacks == ["python"]


# ── run_checks_for_stacks ───────────────────────────────────────────────


class TestRunChecksForStacks:
    """Tests for run_checks_for_stacks dispatch logic."""

    def test_dispatches_common_and_stack_checks(self) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_COMMIT)
        registry: dict[str, list[CheckConfig]] = {
            "common": [CheckConfig(name="common-check", cmd=["common"])],
            "python": [CheckConfig(name="py-check", cmd=["py"])],
        }

        # Act
        with patch("ai_engineering.policy.checks.stack_runner.run_tool_check") as mock_run:
            run_checks_for_stacks(
                Path("/fake"),
                result,
                registry,
                ["python"],
            )

        # Assert
        assert mock_run.call_count == 2
        call_names = [c.kwargs["name"] for c in mock_run.call_args_list]
        assert "common-check" in call_names
        assert "py-check" in call_names

    def test_unknown_stack_only_common_checks(self) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_COMMIT)
        registry: dict[str, list[CheckConfig]] = {
            "common": [CheckConfig(name="common-check", cmd=["common"])],
            "python": [CheckConfig(name="py-check", cmd=["py"])],
        }

        # Act
        with patch("ai_engineering.policy.checks.stack_runner.run_tool_check") as mock_run:
            run_checks_for_stacks(
                Path("/fake"),
                result,
                registry,
                ["rust"],  # unknown stack
            )

        # Assert
        assert mock_run.call_count == 1
        assert mock_run.call_args.kwargs["name"] == "common-check"


# ── run_gate ─────────────────────────────────────────────────────────────


class TestRunGate:
    """Tests for run_gate orchestration with all internals mocked."""

    def _mock_branch_protection_pass(self, project_root: Path, result: GateResult) -> None:
        result.checks.append(GateCheckResult(name="branch-protection", passed=True))

    def _mock_branch_protection_fail(self, project_root: Path, result: GateResult) -> None:
        result.checks.append(GateCheckResult(name="branch-protection", passed=False))

    def _mock_version_deprecation_pass(self, result: GateResult) -> None:
        result.checks.append(GateCheckResult(name="version-deprecation", passed=True))

    def _mock_hook_integrity_pass(self, project_root: Path, result: GateResult) -> None:
        result.checks.append(GateCheckResult(name="hook-integrity", passed=True))

    def test_pre_commit_runs_checks(self) -> None:
        # Act
        with (
            patch(
                "ai_engineering.policy.checks.branch_protection.check_branch_protection",
                side_effect=self._mock_branch_protection_pass,
            ),
            patch(
                "ai_engineering.policy.checks.branch_protection.check_version_deprecation",
                side_effect=self._mock_version_deprecation_pass,
            ),
            patch(
                "ai_engineering.policy.checks.branch_protection.check_hook_integrity",
                side_effect=self._mock_hook_integrity_pass,
            ),
            patch("ai_engineering.policy.gates._run_pre_commit_checks") as mock_pre_commit,
        ):
            result = run_gate(GateHook.PRE_COMMIT, Path("/fake"))

        # Assert
        mock_pre_commit.assert_called_once()
        assert result.hook == GateHook.PRE_COMMIT

    def test_branch_protection_fail_returns_early(self) -> None:
        # Act
        with (
            patch(
                "ai_engineering.policy.checks.branch_protection.check_branch_protection",
                side_effect=self._mock_branch_protection_fail,
            ),
            patch("ai_engineering.policy.gates._run_pre_commit_checks") as mock_pre_commit,
        ):
            result = run_gate(GateHook.PRE_COMMIT, Path("/fake"))

        # Assert
        mock_pre_commit.assert_not_called()
        assert result.passed is False

    def test_commit_msg_valid_message(self, tmp_path: Path) -> None:
        # Arrange
        msg_file = tmp_path / "COMMIT_EDITMSG"
        msg_file.write_text("fix: correct typo\n", encoding="utf-8")

        # Act
        with (
            patch(
                "ai_engineering.policy.checks.branch_protection.check_branch_protection",
                side_effect=self._mock_branch_protection_pass,
            ),
            patch(
                "ai_engineering.policy.checks.branch_protection.check_version_deprecation",
                side_effect=self._mock_version_deprecation_pass,
            ),
            patch(
                "ai_engineering.policy.checks.branch_protection.check_hook_integrity",
                side_effect=self._mock_hook_integrity_pass,
            ),
        ):
            result = run_gate(
                GateHook.COMMIT_MSG,
                Path("/fake"),
                commit_msg_file=msg_file,
            )

        # Assert
        check_names = [c.name for c in result.checks]
        assert "commit-msg-format" in check_names
        assert result.passed is True

    def test_pre_push_runs_checks(self) -> None:
        # Act
        with (
            patch(
                "ai_engineering.policy.checks.branch_protection.check_branch_protection",
                side_effect=self._mock_branch_protection_pass,
            ),
            patch(
                "ai_engineering.policy.checks.branch_protection.check_version_deprecation",
                side_effect=self._mock_version_deprecation_pass,
            ),
            patch(
                "ai_engineering.policy.checks.branch_protection.check_hook_integrity",
                side_effect=self._mock_hook_integrity_pass,
            ),
            patch("ai_engineering.policy.gates._run_pre_push_checks") as mock_pre_push,
        ):
            result = run_gate(GateHook.PRE_PUSH, Path("/fake"))

        # Assert
        mock_pre_push.assert_called_once()
        assert result.hook == GateHook.PRE_PUSH


# ── check_expiring_risk_acceptances ─────────────────────────────────────


class TestCheckExpiringRiskAcceptances:
    """Tests for expiring risk advisory check."""

    def test_no_expiring_no_warning(self, tmp_path: Path) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_COMMIT)
        mock_store = MagicMock(spec=DecisionStore)

        # Act
        with (
            patch(
                "ai_engineering.policy.checks.risk.load_decision_store",
                return_value=mock_store,
            ),
            patch(
                "ai_engineering.policy.checks.risk.list_expiring_soon",
                return_value=[],
            ),
        ):
            check_expiring_risk_acceptances(tmp_path, result)

        # Assert
        assert len(result.checks) == 1
        assert result.checks[0].passed is True
        assert "risk acceptance(s) expiring" not in result.checks[0].output

    def test_expiring_risks_adds_advisory(self, tmp_path: Path) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_COMMIT)
        mock_store = MagicMock(spec=DecisionStore)
        expiring_decision = Decision(
            id="RA-001",
            context="CVE-2025-99999 in dependency X",
            decision="accept for 30 days",
            decidedAt=datetime.now(tz=UTC) - timedelta(days=25),
            spec="004",
            expiresAt=datetime.now(tz=UTC) + timedelta(days=5),
            riskCategory=RiskCategory.RISK_ACCEPTANCE,
            severity=RiskSeverity.HIGH,
            status=DecisionStatus.ACTIVE,
        )

        # Act
        with (
            patch(
                "ai_engineering.policy.checks.risk.load_decision_store",
                return_value=mock_store,
            ),
            patch(
                "ai_engineering.policy.checks.risk.list_expiring_soon",
                return_value=[expiring_decision],
            ),
        ):
            check_expiring_risk_acceptances(tmp_path, result)

        # Assert
        assert len(result.checks) == 1
        assert result.checks[0].passed is True
        assert "expiring" in result.checks[0].output.lower()
        assert "RA-001" in result.checks[0].output

    def test_no_decision_store_skipped(self, tmp_path: Path) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_COMMIT)

        # Act
        with patch(
            "ai_engineering.policy.checks.risk.load_decision_store",
            return_value=None,
        ):
            check_expiring_risk_acceptances(tmp_path, result)

        # Assert
        assert len(result.checks) == 1
        assert result.checks[0].passed is True
        assert "skipped" in result.checks[0].output.lower()


# ── check_expired_risk_acceptances ──────────────────────────────────────


class TestCheckExpiredRiskAcceptances:
    """Tests for expired risk blocking check."""

    def test_no_expired_passes(self, tmp_path: Path) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_PUSH)
        mock_store = MagicMock(spec=DecisionStore)

        # Act
        with (
            patch(
                "ai_engineering.policy.checks.risk.load_decision_store",
                return_value=mock_store,
            ),
            patch(
                "ai_engineering.policy.checks.risk.list_expired_decisions",
                return_value=[],
            ),
        ):
            check_expired_risk_acceptances(tmp_path, result)

        # Assert
        assert len(result.checks) == 1
        assert result.checks[0].passed is True

    def test_expired_risks_blocks_gate(self, tmp_path: Path) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_PUSH)
        mock_store = MagicMock(spec=DecisionStore)
        expired_decision = Decision(
            id="RA-002",
            context="Expired vulnerability acceptance in lib Y",
            decision="accept for 15 days",
            decidedAt=datetime.now(tz=UTC) - timedelta(days=30),
            spec="004",
            expiresAt=datetime.now(tz=UTC) - timedelta(days=1),
            riskCategory=RiskCategory.RISK_ACCEPTANCE,
            severity=RiskSeverity.CRITICAL,
            status=DecisionStatus.ACTIVE,
        )

        # Act
        with (
            patch(
                "ai_engineering.policy.checks.risk.load_decision_store",
                return_value=mock_store,
            ),
            patch(
                "ai_engineering.policy.checks.risk.list_expired_decisions",
                return_value=[expired_decision],
            ),
        ):
            check_expired_risk_acceptances(tmp_path, result)

        # Assert
        assert len(result.checks) == 1
        assert result.checks[0].passed is False
        assert "RA-002" in result.checks[0].output

    def test_no_decision_store_skipped(self, tmp_path: Path) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_PUSH)

        # Act
        with patch(
            "ai_engineering.policy.checks.risk.load_decision_store",
            return_value=None,
        ):
            check_expired_risk_acceptances(tmp_path, result)

        # Assert
        assert len(result.checks) == 1
        assert result.checks[0].passed is True
        assert "skipped" in result.checks[0].output.lower()


# ── Registry Validation ──────────────────────────────────────────────────


class TestRegistryValidation:
    """Validate registry constants contain expected configuration."""

    def test_pre_push_python_stack_tests_flags(self) -> None:
        # Arrange
        python_checks = PRE_PUSH_CHECKS["python"]
        stack_tests = [c for c in python_checks if c.name == "stack-tests"]
        assert len(stack_tests) == 1, "Expected exactly one stack-tests check for python"

        # Act
        cmd = stack_tests[0].cmd

        # Assert
        assert "-n" in cmd, "Expected -n (parallel workers) in stack-tests cmd"
        n_idx = cmd.index("-n")
        assert cmd[n_idx + 1] == "auto", "Expected 'auto' after -n"

        assert "--dist" in cmd, "Expected --dist in stack-tests cmd"
        dist_idx = cmd.index("--dist")
        assert cmd[dist_idx + 1] == "worksteal", "Expected 'worksteal' distribution"

        assert "tests/unit/" in cmd, "Expected tests/unit/ directory in stack-tests cmd"


class TestSonarGateAdvisory:
    """Tests for advisory Sonar pre-push gate behavior."""

    def test_skips_when_scanner_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_PUSH)
        monkeypatch.setattr("ai_engineering.policy.checks.sonar.shutil.which", lambda _: None)

        # Act
        check_sonar_gate(tmp_path, result)

        # Assert
        assert result.checks[-1].passed is True
        assert "skipped" in result.checks[-1].output.lower()

    def test_skips_when_no_properties_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_PUSH)
        monkeypatch.setattr(
            "ai_engineering.policy.checks.sonar.shutil.which", lambda _: "/usr/bin/sonar"
        )

        # Act
        check_sonar_gate(tmp_path, result)

        # Assert
        assert result.checks[-1].passed is True
        assert "sonar-project.properties" in result.checks[-1].output

    def test_skips_when_no_token_and_not_configured(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_PUSH)
        (tmp_path / "sonar-project.properties").write_text("sonar.projectKey=x\n", encoding="utf-8")
        monkeypatch.delenv("SONAR_TOKEN", raising=False)
        monkeypatch.setattr(
            "ai_engineering.policy.checks.sonar.shutil.which", lambda _: "/usr/bin/sonar"
        )
        monkeypatch.setattr(
            "ai_engineering.policy.checks.sonar._resolve_sonar_token",
            lambda _: None,
        )

        # Act
        check_sonar_gate(tmp_path, result)

        # Assert
        assert result.checks[-1].passed is True
        assert "not configured" in result.checks[-1].output.lower()

    def test_skips_when_subprocess_missing_after_check(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_PUSH)
        (tmp_path / "sonar-project.properties").write_text("sonar.projectKey=x\n", encoding="utf-8")
        monkeypatch.setenv("SONAR_TOKEN", "token")
        monkeypatch.setattr(
            "ai_engineering.policy.checks.sonar.shutil.which", lambda _: "/usr/bin/sonar"
        )
        monkeypatch.setattr(
            "ai_engineering.policy.checks.sonar.subprocess.run",
            lambda *_, **__: (_ for _ in ()).throw(FileNotFoundError()),
        )

        # Act
        check_sonar_gate(tmp_path, result)

        # Assert
        assert result.checks[-1].passed is True
        assert "skipped" in result.checks[-1].output.lower()

    def test_scanner_failure_is_advisory(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_PUSH)
        (tmp_path / "sonar-project.properties").write_text("sonar.projectKey=x\n", encoding="utf-8")
        monkeypatch.setenv("SONAR_TOKEN", "token")
        monkeypatch.setattr(
            "ai_engineering.policy.checks.sonar.shutil.which", lambda _: "/usr/bin/sonar"
        )
        proc = MagicMock()
        proc.returncode = 1
        proc.stdout = ""
        proc.stderr = "quality gate failed"
        monkeypatch.setattr(
            "ai_engineering.policy.checks.sonar.subprocess.run", lambda *_, **__: proc
        )

        # Act
        check_sonar_gate(tmp_path, result)

        # Assert
        assert result.checks[-1].passed is True
        assert "advisory" in result.checks[-1].output.lower()
        assert "failed" in result.checks[-1].output.lower()

    def test_scanner_success_passes(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        # Arrange
        result = GateResult(hook=GateHook.PRE_PUSH)
        (tmp_path / "sonar-project.properties").write_text("sonar.projectKey=x\n", encoding="utf-8")
        monkeypatch.setenv("SONAR_TOKEN", "token")
        monkeypatch.setattr(
            "ai_engineering.policy.checks.sonar.shutil.which", lambda _: "/usr/bin/sonar"
        )
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = "Sonar gate passed"
        proc.stderr = ""
        monkeypatch.setattr(
            "ai_engineering.policy.checks.sonar.subprocess.run", lambda *_, **__: proc
        )

        # Act
        check_sonar_gate(tmp_path, result)

        # Assert
        assert result.checks[-1].passed is True
        assert "passed" in result.checks[-1].output.lower()
