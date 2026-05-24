"""Unit tests for ``ai-eng doctor`` release-env-policy runtime probe.

Guards the tag-triggered publish path against GitHub deployment-environment
drift (the 0.8.0 near-miss). Every probe runs hermetically: ``subprocess.run``
is patched so the suite never touches the network or requires ``gh``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from ai_engineering.doctor.models import CheckStatus, DoctorContext
from ai_engineering.doctor.runtime import release_env_policy

_RUN = "ai_engineering.doctor.runtime.release_env_policy.subprocess.run"

# Tag-triggered release workflow with one environment (dict form).
_RELEASE_TAG_TRIGGERED_PYPI = """\
on:
  push:
    tags:
      - "v*"
jobs:
  publish-pypi:
    environment:
      name: pypi
    steps: []
"""

# Tag-triggered with two environments (dict + bare-string form).
_RELEASE_TAG_TRIGGERED_TWO = """\
on:
  push:
    tags:
      - "v*"
jobs:
  publish-pypi:
    environment:
      name: pypi
    steps: []
  finalize:
    environment: github-release
    steps: []
"""

_RELEASE_BRANCH_TRIGGERED = """\
on:
  push:
    branches:
      - main
jobs:
  publish-pypi:
    environment:
      name: pypi
    steps: []
"""

_RELEASE_TAG_NO_ENV = """\
on:
  push:
    tags:
      - "v*"
jobs:
  build:
    steps: []
"""


def _ctx(target: Path) -> DoctorContext:
    return DoctorContext(target=target)


def _cp(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def _write_release(target: Path, body: str) -> None:
    workflow = target / ".github" / "workflows" / "release.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text(body, encoding="utf-8")


def _slug_ok() -> subprocess.CompletedProcess:
    return _cp(0, stdout="owner/repo\n")


# ---------------------------------------------------------------------------
# Not-applicable paths (zero network)
# ---------------------------------------------------------------------------


def test_no_release_workflow_returns_empty(tmp_path: Path) -> None:
    with patch(_RUN) as run:
        results = release_env_policy.check(_ctx(tmp_path))
    assert results == []
    run.assert_not_called()


def test_branch_triggered_returns_empty(tmp_path: Path) -> None:
    _write_release(tmp_path, _RELEASE_BRANCH_TRIGGERED)
    with patch(_RUN) as run:
        results = release_env_policy.check(_ctx(tmp_path))
    assert results == []
    run.assert_not_called()


def test_tag_triggered_without_environments_returns_empty(tmp_path: Path) -> None:
    _write_release(tmp_path, _RELEASE_TAG_NO_ENV)
    with patch(_RUN) as run:
        results = release_env_policy.check(_ctx(tmp_path))
    assert results == []
    run.assert_not_called()


# ---------------------------------------------------------------------------
# gh / auth preflight failures -> single WARN, network short-circuited
# ---------------------------------------------------------------------------


def test_gh_missing_warns_once(tmp_path: Path) -> None:
    _write_release(tmp_path, _RELEASE_TAG_TRIGGERED_PYPI)
    with patch(_RUN, side_effect=FileNotFoundError("gh not found")):
        results = release_env_policy.check(_ctx(tmp_path))
    assert len(results) == 1
    assert results[0].name == "release-env-policy"
    assert results[0].status == CheckStatus.WARN
    assert "gh" in results[0].message.lower()


def test_repo_unresolved_warns_once(tmp_path: Path) -> None:
    _write_release(tmp_path, _RELEASE_TAG_TRIGGERED_PYPI)
    with patch(_RUN, return_value=_cp(1, stderr="not logged in")):
        results = release_env_policy.check(_ctx(tmp_path))
    assert len(results) == 1
    assert results[0].status == CheckStatus.WARN
    assert "pypi" in results[0].message


# ---------------------------------------------------------------------------
# Per-environment policy evaluation
# ---------------------------------------------------------------------------


def test_null_policy_is_ok(tmp_path: Path) -> None:
    _write_release(tmp_path, _RELEASE_TAG_TRIGGERED_PYPI)
    with patch(
        _RUN,
        side_effect=[
            _slug_ok(),
            _cp(0, stdout='{"name":"pypi","deployment_branch_policy":null}'),
        ],
    ):
        results = release_env_policy.check(_ctx(tmp_path))
    assert len(results) == 1
    assert results[0].name == "release-env-pypi"
    assert results[0].status == CheckStatus.OK


def test_protected_branches_only_warns(tmp_path: Path) -> None:
    _write_release(tmp_path, _RELEASE_TAG_TRIGGERED_PYPI)
    with patch(
        _RUN,
        side_effect=[
            _slug_ok(),
            _cp(
                0,
                stdout=(
                    '{"deployment_branch_policy":'
                    '{"protected_branches":true,"custom_branch_policies":false}}'
                ),
            ),
        ],
    ):
        results = release_env_policy.check(_ctx(tmp_path))
    assert len(results) == 1
    assert results[0].status == CheckStatus.WARN
    assert "REJECTED" in results[0].message
    assert "deployment-branch-policies" in results[0].message
    assert "type='tag'" in results[0].message


def test_custom_policy_with_v_star_tag_is_ok(tmp_path: Path) -> None:
    _write_release(tmp_path, _RELEASE_TAG_TRIGGERED_PYPI)
    with patch(
        _RUN,
        side_effect=[
            _slug_ok(),
            _cp(
                0,
                stdout=(
                    '{"deployment_branch_policy":'
                    '{"protected_branches":false,"custom_branch_policies":true}}'
                ),
            ),
            _cp(
                0,
                stdout=(
                    '{"branch_policies":'
                    '[{"name":"main","type":"branch"},{"name":"v*","type":"tag"}]}'
                ),
            ),
        ],
    ):
        results = release_env_policy.check(_ctx(tmp_path))
    assert len(results) == 1
    assert results[0].status == CheckStatus.OK
    assert "pypi" in results[0].message


def test_custom_policy_without_tag_warns(tmp_path: Path) -> None:
    _write_release(tmp_path, _RELEASE_TAG_TRIGGERED_PYPI)
    with patch(
        _RUN,
        side_effect=[
            _slug_ok(),
            _cp(0, stdout='{"deployment_branch_policy":{"custom_branch_policies":true}}'),
            _cp(0, stdout='{"branch_policies":[{"name":"main","type":"branch"}]}'),
        ],
    ):
        results = release_env_policy.check(_ctx(tmp_path))
    assert len(results) == 1
    assert results[0].status == CheckStatus.WARN
    assert "REJECTED" in results[0].message
    assert "v*" in results[0].message


def test_branch_named_v_star_does_not_satisfy_tag_requirement(tmp_path: Path) -> None:
    """A ``v*`` policy of type ``branch`` must NOT be mistaken for a tag policy."""
    _write_release(tmp_path, _RELEASE_TAG_TRIGGERED_PYPI)
    with patch(
        _RUN,
        side_effect=[
            _slug_ok(),
            _cp(0, stdout='{"deployment_branch_policy":{"custom_branch_policies":true}}'),
            _cp(0, stdout='{"branch_policies":[{"name":"v*","type":"branch"}]}'),
        ],
    ):
        results = release_env_policy.check(_ctx(tmp_path))
    assert results[0].status == CheckStatus.WARN


def test_env_api_error_warns_for_that_env(tmp_path: Path) -> None:
    _write_release(tmp_path, _RELEASE_TAG_TRIGGERED_PYPI)
    with patch(
        _RUN,
        side_effect=[
            _slug_ok(),
            _cp(1, stderr="gh: Not Found (HTTP 404)"),
        ],
    ):
        results = release_env_policy.check(_ctx(tmp_path))
    assert len(results) == 1
    assert results[0].status == CheckStatus.WARN
    assert "404" in results[0].message


def test_custom_policy_list_error_warns(tmp_path: Path) -> None:
    _write_release(tmp_path, _RELEASE_TAG_TRIGGERED_PYPI)
    with patch(
        _RUN,
        side_effect=[
            _slug_ok(),
            _cp(0, stdout='{"deployment_branch_policy":{"custom_branch_policies":true}}'),
            _cp(1, stderr="gh: Forbidden (HTTP 403)"),
        ],
    ):
        results = release_env_policy.check(_ctx(tmp_path))
    assert len(results) == 1
    assert results[0].status == CheckStatus.WARN
    assert "403" in results[0].message


def test_multiple_environments_one_result_each(tmp_path: Path) -> None:
    _write_release(tmp_path, _RELEASE_TAG_TRIGGERED_TWO)
    with patch(
        _RUN,
        side_effect=[
            _slug_ok(),
            _cp(0, stdout='{"name":"pypi","deployment_branch_policy":null}'),
            _cp(0, stdout='{"name":"github-release","deployment_branch_policy":null}'),
        ],
    ):
        results = release_env_policy.check(_ctx(tmp_path))
    names = {r.name for r in results}
    assert names == {"release-env-pypi", "release-env-github-release"}
    assert all(r.status == CheckStatus.OK for r in results)


def test_gh_calls_use_target_as_cwd(tmp_path: Path) -> None:
    _write_release(tmp_path, _RELEASE_TAG_TRIGGERED_PYPI)
    with patch(
        _RUN,
        side_effect=[
            _slug_ok(),
            _cp(0, stdout='{"deployment_branch_policy":null}'),
        ],
    ) as run:
        release_env_policy.check(_ctx(tmp_path))
    assert run.call_count >= 1
    for call in run.call_args_list:
        assert call.kwargs["cwd"] == tmp_path


# ---------------------------------------------------------------------------
# Catch-all: a runtime check must never crash diagnose()
# ---------------------------------------------------------------------------


def test_unexpected_error_downgrades_to_warn(tmp_path: Path) -> None:
    _write_release(tmp_path, _RELEASE_TAG_TRIGGERED_PYPI)
    with patch(
        "ai_engineering.doctor.runtime.release_env_policy._resolve_repo_slug",
        side_effect=RuntimeError("boom"),
    ):
        results = release_env_policy.check(_ctx(tmp_path))
    assert len(results) == 1
    assert results[0].name == "release-env-policy"
    assert results[0].status == CheckStatus.WARN
    assert "errored" in results[0].message


# ---------------------------------------------------------------------------
# Signature contract
# ---------------------------------------------------------------------------


def test_module_exports_check() -> None:
    assert hasattr(release_env_policy, "check")
    assert callable(release_env_policy.check)
    result = release_env_policy.check(_ctx(Path("/nonexistent-target-xyz")))
    assert isinstance(result, list)


def test_check_is_registered_in_service() -> None:
    """The module must be wired into the doctor runtime registry."""
    from ai_engineering.doctor import service

    assert "release_env_policy" in service._RUNTIME_CHECK_MODULES
    assert "release_env_policy" in service._RUNTIME_MODULES
    assert service._RUNTIME_CHECK_MODULES["release_env_policy"] is release_env_policy
