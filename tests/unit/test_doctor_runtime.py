"""Unit tests for doctor runtime check modules.

Tests all four runtime modules:
- vcs_auth: GitHub / Azure DevOps authentication
- feeds: Enterprise artifact feed configuration
- branch_policy: Protected branch detection
- version: Framework version lifecycle
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.doctor.models import CheckStatus, DoctorContext
from ai_engineering.doctor.runtime import branch_policy, feeds, vcs_auth, version

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(
    target: Path,
    install_state: object | None = None,
) -> DoctorContext:
    """Build a minimal DoctorContext for testing."""
    return DoctorContext(target=target, install_state=install_state)


def _make_install_state(vcs_provider: str | None = "github") -> MagicMock:
    """Create a mock InstallState with a vcs_provider attribute."""
    state = MagicMock()
    state.vcs_provider = vcs_provider
    return state


# ===========================================================================
# vcs_auth
# ===========================================================================


class TestVcsAuth:
    """Tests for doctor.runtime.vcs_auth.check()."""

    def test_no_install_state_returns_ok_skipped(self, tmp_path: Path) -> None:
        ctx = _ctx(tmp_path, install_state=None)
        results = vcs_auth.check(ctx)
        assert len(results) == 1
        assert results[0].status == CheckStatus.OK
        assert "skipped" in results[0].message

    @patch("ai_engineering.doctor.runtime.vcs_auth.subprocess.run")
    def test_github_auth_ok(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        ctx = _ctx(tmp_path, install_state=_make_install_state("github"))
        results = vcs_auth.check(ctx)
        assert len(results) == 1
        assert results[0].status == CheckStatus.OK
        assert results[0].name == "vcs-auth"
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == ["gh", "auth", "status"]

    @patch("ai_engineering.doctor.runtime.vcs_auth.subprocess.run")
    def test_github_auth_fail(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.return_value = MagicMock(returncode=1)
        ctx = _ctx(tmp_path, install_state=_make_install_state("github"))
        results = vcs_auth.check(ctx)
        assert len(results) == 1
        assert results[0].status == CheckStatus.WARN

    @patch("ai_engineering.doctor.runtime.vcs_auth.subprocess.run")
    def test_github_tool_not_found(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.side_effect = FileNotFoundError("gh not found")
        ctx = _ctx(tmp_path, install_state=_make_install_state("github"))
        results = vcs_auth.check(ctx)
        assert len(results) == 1
        assert results[0].status == CheckStatus.WARN
        assert "not found" in results[0].message

    @patch("ai_engineering.doctor.runtime.vcs_auth.subprocess.run")
    def test_github_timeout(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="gh", timeout=10)
        ctx = _ctx(tmp_path, install_state=_make_install_state("github"))
        results = vcs_auth.check(ctx)
        assert len(results) == 1
        assert results[0].status == CheckStatus.WARN

    @patch("ai_engineering.doctor.runtime.vcs_auth.subprocess.run")
    def test_azure_auth_ok(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        ctx = _ctx(tmp_path, install_state=_make_install_state("azure_devops"))
        results = vcs_auth.check(ctx)
        assert len(results) == 1
        assert results[0].status == CheckStatus.OK
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == ["az", "account", "show"]

    @patch("ai_engineering.doctor.runtime.vcs_auth.subprocess.run")
    def test_azure_auth_fail(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.return_value = MagicMock(returncode=1)
        ctx = _ctx(tmp_path, install_state=_make_install_state("azure_devops"))
        results = vcs_auth.check(ctx)
        assert len(results) == 1
        assert results[0].status == CheckStatus.WARN

    @patch("ai_engineering.doctor.runtime.vcs_auth.subprocess.run")
    def test_azure_tool_not_found(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.side_effect = FileNotFoundError("az not found")
        ctx = _ctx(tmp_path, install_state=_make_install_state("azure_devops"))
        results = vcs_auth.check(ctx)
        assert len(results) == 1
        assert results[0].status == CheckStatus.WARN
        assert "not found" in results[0].message

    @patch("ai_engineering.doctor.runtime.vcs_auth.subprocess.run")
    def test_azure_timeout(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="az", timeout=10)
        ctx = _ctx(tmp_path, install_state=_make_install_state("azure_devops"))
        results = vcs_auth.check(ctx)
        assert len(results) == 1
        assert results[0].status == CheckStatus.WARN

    def test_default_vcs_provider_is_github(self, tmp_path: Path) -> None:
        """When install_state has no vcs_provider, default to github."""
        state = _make_install_state(vcs_provider=None)
        ctx = _ctx(tmp_path, install_state=state)
        with patch("ai_engineering.doctor.runtime.vcs_auth.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            results = vcs_auth.check(ctx)
            assert results[0].status == CheckStatus.OK
            assert mock_run.call_args[0][0] == ["gh", "auth", "status"]


# ===========================================================================
# branch_policy
# ===========================================================================


class TestBranchPolicy:
    """Tests for doctor.runtime.branch_policy.check()."""

    @patch("ai_engineering.doctor.runtime.branch_policy.subprocess.run")
    def test_feature_branch_ok(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="true\n"),
            MagicMock(returncode=0, stdout="feature/my-branch\n"),
        ]
        ctx = _ctx(tmp_path)
        results = branch_policy.check(ctx)
        assert len(results) == 1
        assert results[0].status == CheckStatus.OK
        assert "feature/my-branch" in results[0].message

    @patch("ai_engineering.doctor.runtime.branch_policy.subprocess.run")
    def test_main_branch_warns(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="true\n"),
            MagicMock(returncode=0, stdout="main\n"),
        ]
        ctx = _ctx(tmp_path)
        results = branch_policy.check(ctx)
        assert len(results) == 1
        assert results[0].status == CheckStatus.WARN
        assert "protected branch" in results[0].message

    @patch("ai_engineering.doctor.runtime.branch_policy.subprocess.run")
    def test_master_branch_warns(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="true\n"),
            MagicMock(returncode=0, stdout="master\n"),
        ]
        ctx = _ctx(tmp_path)
        results = branch_policy.check(ctx)
        assert len(results) == 1
        assert results[0].status == CheckStatus.WARN

    @patch("ai_engineering.doctor.runtime.branch_policy.subprocess.run")
    def test_not_a_git_repo_returncode(self, mock_run: MagicMock, tmp_path: Path) -> None:
        # First call (rev-parse --is-inside-work-tree) returns non-zero.
        mock_run.return_value = MagicMock(returncode=128, stdout="")
        ctx = _ctx(tmp_path)
        results = branch_policy.check(ctx)
        assert len(results) == 1
        assert results[0].status == CheckStatus.WARN
        assert "not a git repository" in results[0].message

    @patch("ai_engineering.doctor.runtime.branch_policy.subprocess.run")
    def test_git_not_installed(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.side_effect = FileNotFoundError("git not found")
        ctx = _ctx(tmp_path)
        results = branch_policy.check(ctx)
        assert len(results) == 1
        assert results[0].status == CheckStatus.WARN
        assert "git binary not available" in results[0].message

    @patch("ai_engineering.doctor.runtime.branch_policy.subprocess.run")
    def test_unborn_head_treated_as_detached_ok(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Freshly init'd repo with no commits: HEAD is unborn, ``symbolic-ref``
        succeeds with the initial branch name. This was the user-reported bug
        where ``rev-parse --abbrev-ref HEAD`` fails with 'unknown revision'."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="true\n"),
            MagicMock(returncode=0, stdout="main\n"),
        ]
        ctx = _ctx(tmp_path)
        results = branch_policy.check(ctx)
        # Even unborn 'main' is still classified as protected — the WARN is
        # accurate (the user IS on main).  The fix is that we no longer say
        # "not a git repository" when the repo exists.
        assert results[0].status == CheckStatus.WARN
        assert "protected branch" in results[0].message

    @patch("ai_engineering.doctor.runtime.branch_policy.subprocess.run")
    def test_detached_head_ok(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """``symbolic-ref`` returns non-zero on detached HEAD; report as OK."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="true\n"),
            MagicMock(returncode=128, stdout=""),
        ]
        ctx = _ctx(tmp_path)
        results = branch_policy.check(ctx)
        assert results[0].status == CheckStatus.OK
        assert "detached" in results[0].message.lower()

    @patch("ai_engineering.doctor.runtime.branch_policy.subprocess.run")
    def test_passes_cwd_to_subprocess(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="true\n"),
            MagicMock(returncode=0, stdout="develop\n"),
        ]
        ctx = _ctx(tmp_path)
        branch_policy.check(ctx)
        # Both calls should use ctx.target as cwd.
        for call in mock_run.call_args_list:
            assert call.kwargs["cwd"] == tmp_path


# ===========================================================================
# version
# ===========================================================================


class TestVersion:
    """Tests for doctor.runtime.version.check()."""

    @patch("ai_engineering.doctor.runtime.version.check_version")
    def test_registry_unavailable_warns(self, mock_check: MagicMock, tmp_path: Path) -> None:
        mock_check.return_value = MagicMock(
            status=None,
            is_current=False,
            is_deprecated=False,
            is_eol=False,
            message="Version registry unavailable",
        )
        ctx = _ctx(tmp_path)
        results = version.check(ctx)
        assert len(results) == 1
        assert results[0].status == CheckStatus.WARN
        assert "registry" in results[0].message.lower()

    @patch("ai_engineering.doctor.runtime.version.check_version")
    def test_current_version_ok(self, mock_check: MagicMock, tmp_path: Path) -> None:
        mock_check.return_value = MagicMock(
            status="current",
            is_current=True,
            is_deprecated=False,
            is_eol=False,
            message="1.0.0 (current)",
        )
        ctx = _ctx(tmp_path)
        results = version.check(ctx)
        assert len(results) == 1
        assert results[0].status == CheckStatus.OK

    @patch("ai_engineering.doctor.runtime.version.check_version")
    def test_deprecated_version_fails(self, mock_check: MagicMock, tmp_path: Path) -> None:
        mock_check.return_value = MagicMock(
            status="deprecated",
            is_current=False,
            is_deprecated=True,
            is_eol=False,
            message="0.5.0 (deprecated)",
        )
        ctx = _ctx(tmp_path)
        results = version.check(ctx)
        assert len(results) == 1
        assert results[0].status == CheckStatus.FAIL

    @patch("ai_engineering.doctor.runtime.version.check_version")
    def test_eol_version_fails(self, mock_check: MagicMock, tmp_path: Path) -> None:
        mock_check.return_value = MagicMock(
            status="eol",
            is_current=False,
            is_deprecated=False,
            is_eol=True,
            message="0.1.0 (end-of-life)",
        )
        ctx = _ctx(tmp_path)
        results = version.check(ctx)
        assert len(results) == 1
        assert results[0].status == CheckStatus.FAIL

    @patch("ai_engineering.doctor.runtime.version.check_version")
    def test_outdated_version_warns(self, mock_check: MagicMock, tmp_path: Path) -> None:
        mock_check.return_value = MagicMock(
            status="supported",
            is_current=False,
            is_deprecated=False,
            is_eol=False,
            message="0.9.0 (outdated -- latest is 1.0.0)",
        )
        ctx = _ctx(tmp_path)
        results = version.check(ctx)
        assert len(results) == 1
        assert results[0].status == CheckStatus.WARN


# ===========================================================================
# feeds
# ===========================================================================


_PYPROJECT_PRIVATE_ONLY = """\
[tool.uv]
[[tool.uv.index]]
name = "internal"
url = "https://pkgs.dev.azure.com/org/_packaging/feed/pypi/simple/"
"""

_PYPROJECT_MIXED = """\
[tool.uv]
[[tool.uv.index]]
name = "internal"
url = "https://pkgs.dev.azure.com/org/_packaging/feed/pypi/simple/"
[[tool.uv.index]]
name = "pypi"
url = "https://pypi.org/simple/"
"""

_PYPROJECT_PYPI_ONLY = """\
[tool.uv]
[[tool.uv.index]]
name = "pypi"
url = "https://pypi.org/simple/"
"""

_PYPROJECT_NO_INDEX = """\
[tool.uv]
dev-dependencies = ["pytest"]
"""

_PYPROJECT_NO_UV = """\
[project]
name = "myproject"
"""


class TestFeeds:
    """Tests for doctor.runtime.feeds.check()."""

    def test_no_pyproject_returns_empty(self, tmp_path: Path) -> None:
        ctx = _ctx(tmp_path)
        results = feeds.check(ctx)
        assert results == []

    def test_pypi_only_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_PYPI_ONLY)
        ctx = _ctx(tmp_path)
        results = feeds.check(ctx)
        assert results == []

    def test_no_uv_index_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_NO_INDEX)
        ctx = _ctx(tmp_path)
        results = feeds.check(ctx)
        assert results == []

    def test_no_uv_section_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_NO_UV)
        ctx = _ctx(tmp_path)
        results = feeds.check(ctx)
        assert results == []

    def test_mixed_sources_warns_and_returns_early(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_MIXED)
        ctx = _ctx(tmp_path)
        results = feeds.check(ctx)
        assert len(results) == 1
        assert results[0].name == "feed-mixed-sources"
        assert results[0].status == CheckStatus.WARN

    def test_lock_leak_detected(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_PRIVATE_ONLY)
        (tmp_path / "uv.lock").write_text('source = "https://pypi.org/simple/"\nversion = "1.0"')
        ctx = _ctx(tmp_path)
        with patch.dict("os.environ", {"CI": "true"}):
            results = feeds.check(ctx)
        lock_leak = [r for r in results if r.name == "feed-lock-leak"]
        assert len(lock_leak) == 1
        assert lock_leak[0].status == CheckStatus.FAIL

    def test_lock_leak_clean(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_PRIVATE_ONLY)
        (tmp_path / "uv.lock").write_text(
            'source = "https://pkgs.dev.azure.com/org/feed/"\nversion = "1.0"'
        )
        ctx = _ctx(tmp_path)
        with patch.dict("os.environ", {"CI": "true"}):
            results = feeds.check(ctx)
        lock_leak = [r for r in results if r.name == "feed-lock-leak"]
        assert len(lock_leak) == 1
        assert lock_leak[0].status == CheckStatus.OK

    def test_lock_leak_no_lock_file(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_PRIVATE_ONLY)
        ctx = _ctx(tmp_path)
        with patch.dict("os.environ", {"CI": "true"}):
            results = feeds.check(ctx)
        lock_leak = [r for r in results if r.name == "feed-lock-leak"]
        assert len(lock_leak) == 1
        assert lock_leak[0].status == CheckStatus.OK

    def test_lock_freshness_missing_lock(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_PRIVATE_ONLY)
        ctx = _ctx(tmp_path)
        with patch.dict("os.environ", {"CI": "true"}):
            results = feeds.check(ctx)
        freshness = [r for r in results if r.name == "feed-lock-freshness"]
        assert len(freshness) == 1
        assert freshness[0].status == CheckStatus.WARN

    def test_lock_freshness_stale(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        lock = tmp_path / "uv.lock"
        lock.write_text("content")
        pyproject.write_text(_PYPROJECT_PRIVATE_ONLY)
        # Ensure pyproject is newer by setting lock mtime to the past
        import os

        os.utime(lock, (1000, 1000))

        ctx = _ctx(tmp_path)
        with patch.dict("os.environ", {"CI": "true"}):
            results = feeds.check(ctx)
        freshness = [r for r in results if r.name == "feed-lock-freshness"]
        assert len(freshness) == 1
        assert freshness[0].status == CheckStatus.WARN

    def test_lock_freshness_up_to_date(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        lock = tmp_path / "uv.lock"
        pyproject.write_text(_PYPROJECT_PRIVATE_ONLY)
        # Ensure lock is newer
        import os

        os.utime(pyproject, (1000, 1000))
        lock.write_text("content")

        ctx = _ctx(tmp_path)
        with patch.dict("os.environ", {"CI": "true"}):
            results = feeds.check(ctx)
        freshness = [r for r in results if r.name == "feed-lock-freshness"]
        assert len(freshness) == 1
        assert freshness[0].status == CheckStatus.OK

    def test_keyring_skipped_in_ci(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_PRIVATE_ONLY)
        (tmp_path / "uv.lock").write_text("content")
        ctx = _ctx(tmp_path)
        with patch.dict("os.environ", {"CI": "true"}, clear=False):
            results = feeds.check(ctx)
        keyring_results = [r for r in results if r.name == "feed-keyring"]
        assert keyring_results == []

    def test_keyring_skipped_in_github_actions(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_PRIVATE_ONLY)
        (tmp_path / "uv.lock").write_text("content")
        ctx = _ctx(tmp_path)
        with patch.dict("os.environ", {"GITHUB_ACTIONS": "true"}, clear=False):
            results = feeds.check(ctx)
        keyring_results = [r for r in results if r.name == "feed-keyring"]
        assert keyring_results == []

    @patch("ai_engineering.doctor.runtime.feeds.shutil.which")
    def test_keyring_not_found_warns(self, mock_which: MagicMock, tmp_path: Path) -> None:
        mock_which.return_value = None
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_PRIVATE_ONLY)
        (tmp_path / "uv.lock").write_text("content")
        ctx = _ctx(tmp_path)
        with patch.dict("os.environ", {}, clear=True):
            results = feeds.check(ctx)
        keyring_results = [r for r in results if r.name == "feed-keyring"]
        assert len(keyring_results) == 1
        assert keyring_results[0].status == CheckStatus.WARN

    @patch("ai_engineering.doctor.runtime.feeds.subprocess.run")
    @patch("ai_engineering.doctor.runtime.feeds.shutil.which")
    def test_keyring_found_and_ok(
        self, mock_which: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_which.return_value = "/usr/bin/keyring"
        mock_run.return_value = MagicMock(returncode=0)
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_PRIVATE_ONLY)
        (tmp_path / "uv.lock").write_text("content")
        ctx = _ctx(tmp_path)
        with patch.dict("os.environ", {}, clear=True):
            results = feeds.check(ctx)
        keyring_results = [r for r in results if r.name == "feed-keyring"]
        assert len(keyring_results) == 1
        assert keyring_results[0].status == CheckStatus.OK

    @patch("ai_engineering.doctor.runtime.feeds.subprocess.run")
    @patch("ai_engineering.doctor.runtime.feeds.shutil.which")
    def test_keyring_found_but_fails(
        self, mock_which: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_which.return_value = "/usr/bin/keyring"
        mock_run.return_value = MagicMock(returncode=1)
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_PRIVATE_ONLY)
        (tmp_path / "uv.lock").write_text("content")
        ctx = _ctx(tmp_path)
        with patch.dict("os.environ", {}, clear=True):
            results = feeds.check(ctx)
        keyring_results = [r for r in results if r.name == "feed-keyring"]
        assert len(keyring_results) == 1
        assert keyring_results[0].status == CheckStatus.FAIL

    @patch("ai_engineering.doctor.runtime.feeds.subprocess.run")
    @patch("ai_engineering.doctor.runtime.feeds.shutil.which")
    def test_keyring_found_but_timeout(
        self, mock_which: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_which.return_value = "/usr/bin/keyring"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="keyring", timeout=5)
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_PRIVATE_ONLY)
        (tmp_path / "uv.lock").write_text("content")
        ctx = _ctx(tmp_path)
        with patch.dict("os.environ", {}, clear=True):
            results = feeds.check(ctx)
        keyring_results = [r for r in results if r.name == "feed-keyring"]
        assert len(keyring_results) == 1
        assert keyring_results[0].status == CheckStatus.FAIL

    def test_invalid_toml_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("this is not valid toml [[[")
        ctx = _ctx(tmp_path)
        results = feeds.check(ctx)
        assert results == []


# ===========================================================================
# Signature contract: all modules export check(ctx) -> list[CheckResult]
# ===========================================================================


@pytest.mark.parametrize(
    "module",
    [vcs_auth, feeds, branch_policy, version],
    ids=["vcs_auth", "feeds", "branch_policy", "version"],
)
def test_runtime_module_has_check_function(module: object) -> None:
    """Every runtime module must export a check() function."""
    assert hasattr(module, "check")
    assert callable(module.check)
