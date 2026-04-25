"""Unit tests for ``AIENG_TEST_SIMULATE_INSTALL_OK`` synthetic-success hook.

Sister to ``AIENG_TEST_SIMULATE_FAIL`` (spec-101 T-2.17). The
synthetic-OK hook short-circuits the real install mechanism in CI smoke
runs where network-bound mechanisms (GitHub releases, brew, winget) are
unavailable or rate-limited. The flow upstream of the mechanism boundary
still executes; only the network call is replaced with a synthetic
:class:`InstallResult` carrying ``failed=False``.

Hook semantics (mirrors ``_check_simulate_fail``):

* Inert when ``AIENG_TEST != "1"`` -> ``None``.
* Inert when ``AIENG_TEST_SIMULATE_INSTALL_OK`` unset or empty.
* Wildcard ``"*"`` -> every tool gets a synthetic success.
* Comma-separated list -> only listed tools succeed synthetically.
"""

from __future__ import annotations

import pytest

from ai_engineering.installer.mechanisms import InstallResult


class TestCheckSimulateInstallOkHelper:
    """Unit-level contract for the synthetic-OK hook."""

    def test_no_env_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Without ``AIENG_TEST=1``, the hook is inert."""
        from ai_engineering.installer.user_scope_install import _check_simulate_install_ok

        monkeypatch.delenv("AIENG_TEST", raising=False)
        monkeypatch.setenv("AIENG_TEST_SIMULATE_INSTALL_OK", "*")

        assert _check_simulate_install_ok("ruff") is None

    def test_aieng_test_set_but_no_target_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``AIENG_TEST=1`` alone without OK env var -> ``None``."""
        from ai_engineering.installer.user_scope_install import _check_simulate_install_ok

        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.delenv("AIENG_TEST_SIMULATE_INSTALL_OK", raising=False)

        assert _check_simulate_install_ok("ruff") is None

    def test_wildcard_matches_any_tool(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """``AIENG_TEST_SIMULATE_INSTALL_OK="*"`` -> success for every tool."""
        from ai_engineering.installer.user_scope_install import _check_simulate_install_ok

        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_INSTALL_OK", "*")

        for tool_name in ("ruff", "gitleaks", "jq", "ty"):
            result = _check_simulate_install_ok(tool_name)
            assert result is not None, f"wildcard must match {tool_name!r}"
            assert isinstance(result, InstallResult)
            assert result.failed is False

    def test_named_target_matches(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Named tool in the list -> synthetic success."""
        from ai_engineering.installer.user_scope_install import _check_simulate_install_ok

        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_INSTALL_OK", "ruff,ty")

        for tool_name in ("ruff", "ty"):
            result = _check_simulate_install_ok(tool_name)
            assert result is not None
            assert result.failed is False

        assert _check_simulate_install_ok("gitleaks") is None

    def test_synthetic_result_marks_mechanism_origin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The synthetic ``InstallResult.mechanism`` MUST identify the test hook.

        Auditors / log readers need to distinguish a real install from a
        synthetic one when reviewing CI runs.
        """
        from ai_engineering.installer.user_scope_install import _check_simulate_install_ok

        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_INSTALL_OK", "*")

        result = _check_simulate_install_ok("ruff")
        assert result is not None
        assert "aieng_test_simulate_install_ok" in result.mechanism

    def test_empty_string_is_inert(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty string is treated as unset (no-op)."""
        from ai_engineering.installer.user_scope_install import _check_simulate_install_ok

        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_INSTALL_OK", "")

        assert _check_simulate_install_ok("ruff") is None
