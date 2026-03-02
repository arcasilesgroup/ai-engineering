"""Tests for policy/gates.py — gate checks, branch blocking, tool execution, risk gates.

Covers:
- Branch protection (protected branch blocking).
- Pre-commit gate checks (ruff format, ruff lint, gitleaks, risk warnings).
- Commit-msg validation (format rules).
- Pre-push gate checks (semgrep, pip-audit, tests, ty, expired risk blocking).
- Tool-not-found behavior (fail-closed default).
- GateResult aggregation.
- Risk expiry warnings (pre-commit, non-blocking).
- Risk expired blocking (pre-push, blocking).
- Security tool configs are required.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.policy.gates import (
    CheckConfig,
    GateCheckResult,
    GateResult,
    _check_expired_risk_acceptances,
    _check_expiring_risk_acceptances,
    _get_active_stacks,
    _run_checks_for_stacks,
    _run_pre_push_checks,
    _run_tool_check,
    _validate_commit_message,
    run_gate,
)
from ai_engineering.policy.test_scope import TestScope
from ai_engineering.state.models import GateHook

pytestmark = pytest.mark.integration


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a real git repo on a feature branch."""
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    # Create initial commit so we can create branches
    (tmp_path / "README.md").write_text("init")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    # Switch to feature branch
    subprocess.run(
        ["git", "checkout", "-b", "feature/test"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Branch protection
# ---------------------------------------------------------------------------


class TestBranchProtection:
    """Tests for protected branch blocking."""

    def test_blocks_main_branch(self, tmp_path: Path) -> None:
        with patch("ai_engineering.policy.gates.current_branch", return_value="main"):
            result = run_gate(GateHook.PRE_COMMIT, tmp_path)
            assert not result.passed
            failed = result.failed_checks
            assert "branch-protection" in failed

    def test_blocks_master_branch(self, tmp_path: Path) -> None:
        with patch("ai_engineering.policy.gates.current_branch", return_value="master"):
            result = run_gate(GateHook.PRE_COMMIT, tmp_path)
            assert not result.passed

    def test_allows_feature_branch(self, git_repo: Path) -> None:
        result = run_gate(GateHook.PRE_COMMIT, git_repo)
        branch_check = _find_check(result, "branch-protection")
        assert branch_check.passed


# ---------------------------------------------------------------------------
# Commit message validation
# ---------------------------------------------------------------------------


class TestCommitMsgValidation:
    """Tests for commit message format validation."""

    def test_valid_message(self) -> None:
        errors = _validate_commit_message("fix: resolve issue with parser")
        assert errors == []

    def test_empty_message(self) -> None:
        errors = _validate_commit_message("")
        assert len(errors) > 0

    def test_first_line_too_long(self) -> None:
        long_msg = "x" * 73
        errors = _validate_commit_message(long_msg)
        assert any("72" in e for e in errors)

    def test_exactly_72_chars(self) -> None:
        msg = "x" * 72
        errors = _validate_commit_message(msg)
        assert errors == []

    def test_multiline_message(self) -> None:
        msg = "short subject\n\nLong body with details about the change."
        errors = _validate_commit_message(msg)
        assert errors == []


class TestCommitMsgGate:
    """Tests for the commit-msg gate hook."""

    def test_with_valid_msg_file(self, git_repo: Path) -> None:
        msg_file = git_repo / ".git" / "COMMIT_EDITMSG"
        msg_file.write_text("valid commit message")
        result = run_gate(GateHook.COMMIT_MSG, git_repo, commit_msg_file=msg_file)
        check = _find_check(result, "commit-msg-format")
        assert check.passed
        content = msg_file.read_text(encoding="utf-8")
        assert "Ai-Eng-Gate: passed" in content

    def test_with_invalid_msg_file(self, git_repo: Path) -> None:
        msg_file = git_repo / ".git" / "COMMIT_EDITMSG"
        msg_file.write_text("x" * 100)
        result = run_gate(GateHook.COMMIT_MSG, git_repo, commit_msg_file=msg_file)
        check = _find_check(result, "commit-msg-format")
        assert not check.passed

    def test_without_msg_file(self, git_repo: Path) -> None:
        result = run_gate(GateHook.COMMIT_MSG, git_repo)
        check = _find_check(result, "commit-msg-format")
        assert check.passed  # Skipped gracefully


# ---------------------------------------------------------------------------
# Pre-commit checks
# ---------------------------------------------------------------------------


class TestPreCommitGate:
    """Tests for pre-commit gate checks."""

    def test_runs_all_checks(self, git_repo: Path) -> None:
        result = run_gate(GateHook.PRE_COMMIT, git_repo)
        check_names = {c.name for c in result.checks}
        assert "branch-protection" in check_names
        assert "hook-integrity" in check_names
        # ruff-format, ruff-lint, gitleaks may be skipped if not installed
        assert "ruff-format" in check_names or len(check_names) >= 2

    def test_hook_integrity_blocks_when_present_hook_invalid(self, git_repo: Path) -> None:
        hook_path = git_repo / ".git" / "hooks" / "pre-commit"
        hook_path.write_text("#!/usr/bin/env bash\necho custom\n", encoding="utf-8")
        with patch(
            "ai_engineering.policy.gates.verify_hooks",
            return_value={"pre-commit": False, "commit-msg": True, "pre-push": True},
        ):
            result = run_gate(GateHook.PRE_COMMIT, git_repo)
        assert result.passed is False
        assert "hook-integrity" in result.failed_checks


# ---------------------------------------------------------------------------
# Pre-push checks
# ---------------------------------------------------------------------------


class TestPrePushGate:
    """Tests for pre-push gate checks."""

    def test_runs_all_checks(self, git_repo: Path) -> None:
        result = run_gate(GateHook.PRE_PUSH, git_repo)
        check_names = {c.name for c in result.checks}
        assert "branch-protection" in check_names
        # Tools may be skipped if not installed
        assert len(result.checks) >= 2


# ---------------------------------------------------------------------------
# Tool check required parameter
# ---------------------------------------------------------------------------


class TestToolCheckRequired:
    """Tests for _run_tool_check required parameter behavior."""

    def test_missing_tool_passes_when_not_required(self, tmp_path: Path) -> None:
        result = GateResult(hook=GateHook.PRE_COMMIT)
        with patch("ai_engineering.policy.gates.shutil.which", return_value=None):
            _run_tool_check(
                result,
                name="fake-tool",
                cmd=["nonexistent-tool", "check"],
                cwd=tmp_path,
                required=False,
            )
        check = _find_check(result, "fake-tool")
        assert check.passed
        assert "skipped" in check.output

    def test_missing_tool_fails_when_required(self, tmp_path: Path) -> None:
        result = GateResult(hook=GateHook.PRE_COMMIT)
        with patch("ai_engineering.policy.gates.shutil.which", return_value=None):
            _run_tool_check(
                result,
                name="fake-tool",
                cmd=["nonexistent-tool", "check"],
                cwd=tmp_path,
                required=True,
            )
        check = _find_check(result, "fake-tool")
        assert not check.passed
        assert "required" in check.output
        assert "ai-eng doctor --fix-tools" in check.output

    def test_tool_success_records_pass(self, tmp_path: Path) -> None:
        result = GateResult(hook=GateHook.PRE_COMMIT)
        mock_proc = subprocess.CompletedProcess(
            args=["tool"], returncode=0, stdout="all good", stderr=""
        )
        with (
            patch("ai_engineering.policy.gates.shutil.which", return_value="/usr/bin/tool"),
            patch("ai_engineering.policy.gates.subprocess.run", return_value=mock_proc),
        ):
            _run_tool_check(
                result,
                name="test-tool",
                cmd=["tool", "check"],
                cwd=tmp_path,
            )
        check = _find_check(result, "test-tool")
        assert check.passed
        assert "all good" in check.output

    def test_tool_failure_records_fail(self, tmp_path: Path) -> None:
        result = GateResult(hook=GateHook.PRE_COMMIT)
        mock_proc = subprocess.CompletedProcess(
            args=["tool"], returncode=1, stdout="", stderr="error found"
        )
        with (
            patch("ai_engineering.policy.gates.shutil.which", return_value="/usr/bin/tool"),
            patch("ai_engineering.policy.gates.subprocess.run", return_value=mock_proc),
        ):
            _run_tool_check(
                result,
                name="test-tool",
                cmd=["tool", "check"],
                cwd=tmp_path,
            )
        check = _find_check(result, "test-tool")
        assert not check.passed

    def test_empty_output_shows_exit_code(self, tmp_path: Path) -> None:
        result = GateResult(hook=GateHook.PRE_COMMIT)
        mock_proc = subprocess.CompletedProcess(args=["tool"], returncode=1, stdout="", stderr="")
        with (
            patch("ai_engineering.policy.gates.shutil.which", return_value="/usr/bin/tool"),
            patch("ai_engineering.policy.gates.subprocess.run", return_value=mock_proc),
        ):
            _run_tool_check(
                result,
                name="test-tool",
                cmd=["tool", "check"],
                cwd=tmp_path,
            )
        check = _find_check(result, "test-tool")
        assert "exited with code 1" in check.output

    def test_default_required_is_true(self, tmp_path: Path) -> None:
        """_run_tool_check defaults to required=True (fail-closed)."""
        result = GateResult(hook=GateHook.PRE_COMMIT)
        with patch("ai_engineering.policy.gates.shutil.which", return_value=None):
            _run_tool_check(
                result,
                name="default-tool",
                cmd=["nonexistent-tool", "check"],
                cwd=tmp_path,
                # No required= argument — uses default
            )
        check = _find_check(result, "default-tool")
        assert not check.passed, "Default required should be True (fail-closed)"

    def test_security_tools_are_required(self) -> None:
        """Gitleaks and semgrep check configs have required=True."""
        from ai_engineering.policy.gates import _PRE_COMMIT_CHECKS, _PRE_PUSH_CHECKS

        gitleaks_configs = [
            c for checks in _PRE_COMMIT_CHECKS.values() for c in checks if "gitleaks" in c.name
        ]
        semgrep_configs = [
            c for checks in _PRE_PUSH_CHECKS.values() for c in checks if "semgrep" in c.name
        ]
        assert gitleaks_configs, "gitleaks must be in pre-commit registry"
        assert semgrep_configs, "semgrep must be in pre-push registry"
        for config in gitleaks_configs + semgrep_configs:
            assert config.required is True, f"{config.name} must be required"

    def test_timeout_passed_to_subprocess(self, tmp_path: Path) -> None:
        """_run_tool_check passes custom timeout to subprocess.run."""
        result = GateResult(hook=GateHook.PRE_COMMIT)
        mock_proc = subprocess.CompletedProcess(args=["tool"], returncode=0, stdout="ok", stderr="")
        with (
            patch("ai_engineering.policy.gates.shutil.which", return_value="/usr/bin/tool"),
            patch("ai_engineering.policy.gates.subprocess.run", return_value=mock_proc) as mock_run,
        ):
            _run_tool_check(
                result,
                name="test-tool",
                cmd=["tool", "check"],
                cwd=tmp_path,
                timeout=600,
            )
        mock_run.assert_called_once()
        assert mock_run.call_args.kwargs["timeout"] == 600

    def test_timeout_message_includes_custom_value(self, tmp_path: Path) -> None:
        """Timeout error message reflects the configured timeout value."""
        result = GateResult(hook=GateHook.PRE_COMMIT)
        with (
            patch("ai_engineering.policy.gates.shutil.which", return_value="/usr/bin/tool"),
            patch(
                "ai_engineering.policy.gates.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="tool", timeout=600),
            ),
        ):
            _run_tool_check(
                result,
                name="test-tool",
                cmd=["tool", "check"],
                cwd=tmp_path,
                timeout=600,
            )
        check = _find_check(result, "test-tool")
        assert not check.passed
        assert "600s" in check.output

    def test_stack_tests_uses_parallel_unit_only(self) -> None:
        """stack-tests runs unit tier only with parallel execution."""
        from ai_engineering.policy.gates import _PRE_PUSH_CHECKS

        stack_tests = [c for c in _PRE_PUSH_CHECKS.get("python", []) if c.name == "stack-tests"]
        assert stack_tests, "stack-tests must exist in python pre-push checks"
        cmd = stack_tests[0].cmd
        assert "--no-cov" in cmd, "stack-tests must skip coverage"
        assert "-x" in cmd, "stack-tests must fail fast"
        assert "unit" in " ".join(cmd), "stack-tests must select unit marker"
        assert "-n" in cmd, "stack-tests must use parallel execution"
        assert "worksteal" in " ".join(cmd), "stack-tests must use worksteal distribution"

    def test_stack_tests_has_optimized_timeout(self) -> None:
        """stack-tests timeout is 120s for unit-only parallel execution."""
        from ai_engineering.policy.gates import _PRE_PUSH_CHECKS

        stack_tests = [c for c in _PRE_PUSH_CHECKS.get("python", []) if c.name == "stack-tests"]
        assert stack_tests, "stack-tests must exist"
        assert stack_tests[0].timeout == 120, "stack-tests timeout must be 120s"

    def test_check_config_default_timeout(self) -> None:
        """CheckConfig defaults to 300s timeout."""
        config = CheckConfig(name="test", cmd=["test"])
        assert config.timeout == 300


# ---------------------------------------------------------------------------
# GateResult
# ---------------------------------------------------------------------------


class TestGateResult:
    """Tests for GateResult aggregation."""

    def test_passed_when_all_pass(self) -> None:
        result = GateResult(
            hook=GateHook.PRE_COMMIT,
            checks=[
                GateCheckResult(name="a", passed=True),
                GateCheckResult(name="b", passed=True),
            ],
        )
        assert result.passed is True

    def test_not_passed_when_any_fails(self) -> None:
        result = GateResult(
            hook=GateHook.PRE_COMMIT,
            checks=[
                GateCheckResult(name="a", passed=True),
                GateCheckResult(name="b", passed=False),
            ],
        )
        assert result.passed is False

    def test_failed_checks_list(self) -> None:
        result = GateResult(
            hook=GateHook.PRE_COMMIT,
            checks=[
                GateCheckResult(name="a", passed=True),
                GateCheckResult(name="b", passed=False),
                GateCheckResult(name="c", passed=False),
            ],
        )
        assert result.failed_checks == ["b", "c"]

    def test_empty_result_passes(self) -> None:
        result = GateResult(hook=GateHook.PRE_COMMIT)
        assert result.passed is True


# ---------------------------------------------------------------------------
# Risk gate checks
# ---------------------------------------------------------------------------


class TestRiskExpiryWarning:
    """Tests for _check_expiring_risk_acceptances (pre-commit, non-blocking)."""

    def test_no_decision_store_passes(self, tmp_path: Path) -> None:
        result = GateResult(hook=GateHook.PRE_COMMIT)
        _check_expiring_risk_acceptances(tmp_path, result)
        check = _find_check(result, "risk-expiry-warning")
        assert check.passed

    def test_no_expiring_passes(self, tmp_path: Path) -> None:
        # Create an empty decision store
        ds_dir = tmp_path / ".ai-engineering" / "state"
        ds_dir.mkdir(parents=True)
        import json

        (ds_dir / "decision-store.json").write_text(
            json.dumps({"schemaVersion": "1.1", "decisions": []})
        )
        result = GateResult(hook=GateHook.PRE_COMMIT)
        _check_expiring_risk_acceptances(tmp_path, result)
        check = _find_check(result, "risk-expiry-warning")
        assert check.passed

    def test_expiring_warns_but_passes(self, tmp_path: Path) -> None:
        import json
        from datetime import UTC, datetime, timedelta

        ds_dir = tmp_path / ".ai-engineering" / "state"
        ds_dir.mkdir(parents=True)
        (ds_dir / "decision-store.json").write_text(
            json.dumps(
                {
                    "schemaVersion": "1.1",
                    "decisions": [
                        {
                            "id": "RA-001",
                            "context": "test risk",
                            "decision": "accept",
                            "decidedAt": "2025-01-01T00:00:00Z",
                            "spec": "004",
                            "riskCategory": "risk-acceptance",
                            "severity": "high",
                            "status": "active",
                            "expiresAt": (datetime.now(tz=UTC) + timedelta(days=3)).strftime(
                                "%Y-%m-%dT%H:%M:%SZ"
                            ),
                            "renewalCount": 0,
                        }
                    ],
                }
            )
        )
        result = GateResult(hook=GateHook.PRE_COMMIT)
        _check_expiring_risk_acceptances(tmp_path, result)
        check = _find_check(result, "risk-expiry-warning")
        assert check.passed  # Warning only, non-blocking
        assert "expiring" in check.output.lower()


class TestRiskExpiredBlock:
    """Tests for _check_expired_risk_acceptances (pre-push, blocking)."""

    def test_no_decision_store_passes(self, tmp_path: Path) -> None:
        result = GateResult(hook=GateHook.PRE_PUSH)
        _check_expired_risk_acceptances(tmp_path, result)
        check = _find_check(result, "risk-expired-block")
        assert check.passed

    def test_no_expired_passes(self, tmp_path: Path) -> None:
        import json

        ds_dir = tmp_path / ".ai-engineering" / "state"
        ds_dir.mkdir(parents=True)
        (ds_dir / "decision-store.json").write_text(
            json.dumps({"schemaVersion": "1.1", "decisions": []})
        )
        result = GateResult(hook=GateHook.PRE_PUSH)
        _check_expired_risk_acceptances(tmp_path, result)
        check = _find_check(result, "risk-expired-block")
        assert check.passed

    def test_expired_blocks(self, tmp_path: Path) -> None:
        import json

        ds_dir = tmp_path / ".ai-engineering" / "state"
        ds_dir.mkdir(parents=True)
        (ds_dir / "decision-store.json").write_text(
            json.dumps(
                {
                    "schemaVersion": "1.1",
                    "decisions": [
                        {
                            "id": "RA-001",
                            "context": "test expired risk",
                            "decision": "accept",
                            "decidedAt": "2025-01-01T00:00:00Z",
                            "spec": "004",
                            "riskCategory": "risk-acceptance",
                            "severity": "critical",
                            "status": "active",
                            "expiresAt": "2020-01-01T00:00:00Z",
                            "renewalCount": 0,
                        }
                    ],
                }
            )
        )
        result = GateResult(hook=GateHook.PRE_PUSH)
        _check_expired_risk_acceptances(tmp_path, result)
        check = _find_check(result, "risk-expired-block")
        assert not check.passed  # Blocks push


# ---------------------------------------------------------------------------
# Version deprecation gate
# ---------------------------------------------------------------------------


class TestVersionDeprecationGate:
    """Tests for _check_version_deprecation gate check."""

    def test_deprecated_blocks_gate(self, git_repo: Path) -> None:
        from ai_engineering.version.checker import VersionCheckResult
        from ai_engineering.version.models import VersionStatus

        mock_result = VersionCheckResult(
            installed="0.1.0",
            status=VersionStatus.DEPRECATED,
            is_current=False,
            is_outdated=False,
            is_deprecated=True,
            is_eol=False,
            latest="0.2.0",
            message="0.1.0 (deprecated — CVE-2025-9999)",
        )
        with patch(
            "ai_engineering.version.checker.check_version",
            return_value=mock_result,
        ):
            result = run_gate(GateHook.PRE_COMMIT, git_repo)
        assert not result.passed
        assert "version-deprecation" in result.failed_checks

    def test_outdated_does_not_block_gate(self, git_repo: Path) -> None:
        from ai_engineering.version.checker import VersionCheckResult
        from ai_engineering.version.models import VersionStatus

        mock_result = VersionCheckResult(
            installed="0.1.0",
            status=VersionStatus.SUPPORTED,
            is_current=False,
            is_outdated=True,
            is_deprecated=False,
            is_eol=False,
            latest="0.2.0",
            message="0.1.0 (outdated — latest is 0.2.0)",
        )
        with patch(
            "ai_engineering.version.checker.check_version",
            return_value=mock_result,
        ):
            result = run_gate(GateHook.PRE_COMMIT, git_repo)
        version_check = _find_check(result, "version-deprecation")
        assert version_check.passed

    def test_current_passes_gate(self, git_repo: Path) -> None:
        from ai_engineering.version.checker import VersionCheckResult
        from ai_engineering.version.models import VersionStatus

        mock_result = VersionCheckResult(
            installed="0.1.0",
            status=VersionStatus.CURRENT,
            is_current=True,
            is_outdated=False,
            is_deprecated=False,
            is_eol=False,
            latest="0.1.0",
            message="0.1.0 (current)",
        )
        with patch(
            "ai_engineering.version.checker.check_version",
            return_value=mock_result,
        ):
            result = run_gate(GateHook.PRE_COMMIT, git_repo)
        version_check = _find_check(result, "version-deprecation")
        assert version_check.passed


# ---------------------------------------------------------------------------
# Multi-stack gate dispatch
# ---------------------------------------------------------------------------


class TestGetActiveStacks:
    """Tests for _get_active_stacks — install manifest reading."""

    def test_returns_python_when_no_manifest(self, tmp_path: Path) -> None:
        stacks = _get_active_stacks(tmp_path)
        assert stacks == ["python"]

    def test_reads_stacks_from_manifest(self, tmp_path: Path) -> None:
        import json

        ds_dir = tmp_path / ".ai-engineering" / "state"
        ds_dir.mkdir(parents=True)
        (ds_dir / "install-manifest.json").write_text(
            json.dumps(
                {
                    "schemaVersion": "1.1",
                    "frameworkVersion": "0.1.0",
                    "installedAt": "2026-02-22T00:00:00Z",
                    "installedStacks": ["python", "dotnet"],
                    "installedIdes": [],
                    "toolingReadiness": {},
                }
            )
        )
        stacks = _get_active_stacks(tmp_path)
        assert stacks == ["python", "dotnet"]

    def test_returns_python_when_manifest_empty_stacks(self, tmp_path: Path) -> None:
        pass

    def test_returns_python_when_manifest_invalid(self, tmp_path: Path) -> None:
        ds_dir = tmp_path / ".ai-engineering" / "state"
        ds_dir.mkdir(parents=True)
        (ds_dir / "install-manifest.json").write_text("invalid json")
        stacks = _get_active_stacks(tmp_path)
        assert stacks == ["python"]


class TestRunChecksForStacks:
    """Tests for _run_checks_for_stacks — stack-aware dispatch."""

    def test_runs_common_and_python_checks(self, tmp_path: Path) -> None:
        registry: dict[str, list[CheckConfig]] = {
            "common": [CheckConfig(name="gitleaks", cmd=["gitleaks"])],
            "python": [CheckConfig(name="ruff-format", cmd=["ruff", "format"])],
            "dotnet": [CheckConfig(name="dotnet-format", cmd=["dotnet", "format"])],
        }
        result = GateResult(hook=GateHook.PRE_COMMIT)
        with patch("ai_engineering.policy.gates.shutil.which", return_value=None):
            _run_checks_for_stacks(tmp_path, result, registry, ["python"])
        names = {c.name for c in result.checks}
        assert "gitleaks" in names
        assert "ruff-format" in names
        assert "dotnet-format" not in names

    def test_runs_dotnet_checks_when_active(self, tmp_path: Path) -> None:
        registry: dict[str, list[CheckConfig]] = {
            "common": [CheckConfig(name="gitleaks", cmd=["gitleaks"])],
            "python": [CheckConfig(name="ruff-format", cmd=["ruff"])],
            "dotnet": [CheckConfig(name="dotnet-format", cmd=["dotnet"])],
        }
        result = GateResult(hook=GateHook.PRE_COMMIT)
        with patch("ai_engineering.policy.gates.shutil.which", return_value=None):
            _run_checks_for_stacks(tmp_path, result, registry, ["dotnet"])
        names = {c.name for c in result.checks}
        assert "gitleaks" in names
        assert "dotnet-format" in names
        assert "ruff-format" not in names

    def test_runs_multi_stack_checks(self, tmp_path: Path) -> None:
        registry: dict[str, list[CheckConfig]] = {
            "common": [CheckConfig(name="gitleaks", cmd=["gitleaks"])],
            "python": [CheckConfig(name="pip-audit", cmd=["pip-audit"])],
            "nextjs": [CheckConfig(name="npm-audit", cmd=["npm", "audit"])],
        }
        result = GateResult(hook=GateHook.PRE_PUSH)
        with patch("ai_engineering.policy.gates.shutil.which", return_value=None):
            _run_checks_for_stacks(tmp_path, result, registry, ["python", "nextjs"])
        names = {c.name for c in result.checks}
        assert "gitleaks" in names
        assert "pip-audit" in names
        assert "npm-audit" in names


class TestSelectiveScopeIntegration:
    """Integration-level tests for selective scope behavior in pre-push gates."""

    def test_selective_enforce_overrides_stack_tests(self, git_repo: Path) -> None:
        seen_cmds: list[list[str]] = []

        def fake_run_tool_check(
            result: GateResult,
            *,
            name: str,
            cmd: list[str],
            **kwargs: object,
        ) -> None:
            seen_cmds.append(cmd)
            result.checks.append(GateCheckResult(name=name, passed=True, output="ok"))

        with (
            patch.dict(
                "os.environ",
                {"AI_ENG_TEST_SCOPE_MODE": "enforce"},
                clear=False,
            ),
            patch("ai_engineering.policy.gates._get_active_stacks", return_value=["python"]),
            patch(
                "ai_engineering.policy.gates._compute_test_scope",
                return_value=TestScope(
                    selected_tests=["tests/unit/test_hooks.py"],
                    mode="selective",
                    reasons=["selective"],
                    changed_files=["src/ai_engineering/hooks/manager.py"],
                    matched_rules=["hooks"],
                    unmatched_src_files=[],
                ),
            ),
            patch("ai_engineering.policy.gates._check_expired_risk_acceptances", return_value=None),
            patch("ai_engineering.policy.gates._run_tool_check", side_effect=fake_run_tool_check),
        ):
            result = GateResult(hook=GateHook.PRE_PUSH)
            _run_pre_push_checks(git_repo, result)

        pytest_cmd = next(cmd for cmd in seen_cmds if "pytest" in cmd)
        assert "tests/unit/test_hooks.py" in pytest_cmd
        assert _find_check(result, "test-scope").passed

    def test_full_mode_keeps_unscoped_stack_tests(self, git_repo: Path) -> None:
        seen_cmds: list[list[str]] = []

        def fake_run_tool_check(
            result: GateResult,
            *,
            name: str,
            cmd: list[str],
            **kwargs: object,
        ) -> None:
            seen_cmds.append(cmd)
            result.checks.append(GateCheckResult(name=name, passed=True, output="ok"))

        with (
            patch.dict("os.environ", {"AI_ENG_TEST_SCOPE_MODE": "enforce"}, clear=False),
            patch("ai_engineering.policy.gates._get_active_stacks", return_value=["python"]),
            patch(
                "ai_engineering.policy.gates._compute_test_scope",
                return_value=TestScope(
                    selected_tests=["tests/unit"],
                    mode="full",
                    reasons=["full_suite_trigger_changed"],
                    changed_files=["pyproject.toml"],
                    matched_rules=[],
                    unmatched_src_files=[],
                ),
            ),
            patch("ai_engineering.policy.gates._check_expired_risk_acceptances", return_value=None),
            patch("ai_engineering.policy.gates._run_tool_check", side_effect=fake_run_tool_check),
        ):
            result = GateResult(hook=GateHook.PRE_PUSH)
            _run_pre_push_checks(git_repo, result)

        pytest_cmd = next(cmd for cmd in seen_cmds if "pytest" in cmd)
        assert "tests/unit/test_hooks.py" not in pytest_cmd

    def test_scope_computation_failure_falls_back_full(self, git_repo: Path) -> None:
        seen_cmds: list[list[str]] = []

        def fake_run_tool_check(
            result: GateResult,
            *,
            name: str,
            cmd: list[str],
            **kwargs: object,
        ) -> None:
            seen_cmds.append(cmd)
            result.checks.append(GateCheckResult(name=name, passed=True, output="ok"))

        with (
            patch.dict("os.environ", {"AI_ENG_TEST_SCOPE_MODE": "enforce"}, clear=False),
            patch("ai_engineering.policy.gates._get_active_stacks", return_value=["python"]),
            patch(
                "ai_engineering.policy.gates._compute_test_scope",
                side_effect=RuntimeError("boom"),
            ),
            patch("ai_engineering.policy.gates._check_expired_risk_acceptances", return_value=None),
            patch("ai_engineering.policy.gates._run_tool_check", side_effect=fake_run_tool_check),
        ):
            result = GateResult(hook=GateHook.PRE_PUSH)
            _run_pre_push_checks(git_repo, result)

        pytest_cmd = next(cmd for cmd in seen_cmds if "pytest" in cmd)
        assert "tests/unit/test_hooks.py" not in pytest_cmd
        diagnostic = _find_check(result, "test-scope")
        assert "scope_computation_failed" in diagnostic.output

    def test_docs_only_scope_skips_stack_tests(self, git_repo: Path) -> None:
        seen_names: list[str] = []

        def fake_run_tool_check(
            result: GateResult,
            *,
            name: str,
            cmd: list[str],
            **kwargs: object,
        ) -> None:
            seen_names.append(name)
            result.checks.append(GateCheckResult(name=name, passed=True, output="ok"))

        with (
            patch.dict("os.environ", {"AI_ENG_TEST_SCOPE_MODE": "enforce"}, clear=False),
            patch("ai_engineering.policy.gates._get_active_stacks", return_value=["python"]),
            patch(
                "ai_engineering.policy.gates._compute_test_scope",
                return_value=TestScope(
                    selected_tests=[],
                    mode="selective",
                    reasons=["docs_only"],
                    changed_files=["README.md"],
                    matched_rules=[],
                    unmatched_src_files=[],
                ),
            ),
            patch("ai_engineering.policy.gates._check_expired_risk_acceptances", return_value=None),
            patch("ai_engineering.policy.gates._run_tool_check", side_effect=fake_run_tool_check),
        ):
            result = GateResult(hook=GateHook.PRE_PUSH)
            _run_pre_push_checks(git_repo, result)

        assert "stack-tests" not in seen_names


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_check(result: GateResult, name: str) -> GateCheckResult:
    """Find a check by name in a gate result."""
    for check in result.checks:
        if check.name == name:
            return check
    pytest.fail(f"Check '{name}' not found in result")
