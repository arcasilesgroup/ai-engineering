"""Unit tests for ``ai-eng doctor`` secrets-gate runtime probe (spec-124 T-4.3).

Each probe is exercised in isolation with monkeypatched binary paths and
file-system fixtures so the test suite stays hermetic regardless of
whether ``gitleaks`` / ``semgrep`` are installed on the executing host.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ai_engineering.doctor.models import CheckStatus, DoctorContext
from ai_engineering.doctor.runtime import secrets_gate


def _ctx(target: Path) -> DoctorContext:
    return DoctorContext(target=target)


def _completed(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _seed_hooks(target: Path, *, pre_commit_marker: bool, pre_push_marker: bool) -> None:
    hooks_dir = target / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    pre_commit = hooks_dir / "pre-commit"
    pre_push = hooks_dir / "pre-push"
    pre_commit.write_text(
        "#!/usr/bin/env bash\nai-eng gate pre-commit\n"
        if pre_commit_marker
        else "#!/usr/bin/env bash\necho 'noop'\n",
        encoding="utf-8",
    )
    pre_push.write_text(
        "#!/usr/bin/env bash\nai-eng gate pre-push\n"
        if pre_push_marker
        else "#!/usr/bin/env bash\necho 'noop'\n",
        encoding="utf-8",
    )


def _seed_configs(target: Path, *, gitleaks: bool, semgrep: bool) -> None:
    if gitleaks:
        (target / ".gitleaks.toml").write_text("title = 'test'\n", encoding="utf-8")
        (target / ".gitleaksignore").write_text("# stub\n", encoding="utf-8")
    if semgrep:
        (target / ".semgrep.yml").write_text("rules: []\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# gitleaks-binary probe
# ---------------------------------------------------------------------------


def test_gitleaks_binary_missing_warns(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        secrets_gate.shutil,
        "which",
        lambda name: None if name in {"gitleaks", "semgrep"} else "/usr/bin/" + name,
    )
    results = secrets_gate.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["gitleaks-binary"].status == CheckStatus.WARN
    assert "brew install gitleaks" in by_name["gitleaks-binary"].message


def test_gitleaks_binary_present_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        secrets_gate.shutil,
        "which",
        lambda name: f"/usr/local/bin/{name}",
    )
    monkeypatch.setattr(
        secrets_gate.subprocess,
        "run",
        lambda *_, **__: _completed(0, stdout="v8.18.0\n"),
    )
    results = secrets_gate.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["gitleaks-binary"].status == CheckStatus.OK
    assert "/usr/local/bin/gitleaks" in by_name["gitleaks-binary"].message


# ---------------------------------------------------------------------------
# gitleaks-version probe
# ---------------------------------------------------------------------------


def test_gitleaks_version_runs_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(secrets_gate.shutil, "which", lambda _: "/usr/local/bin/gitleaks")
    monkeypatch.setattr(
        secrets_gate.subprocess,
        "run",
        lambda *_, **__: _completed(0, stdout="v8.18.0\n"),
    )
    results = secrets_gate.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["gitleaks-version"].status == CheckStatus.OK
    assert "v8.18.0" in by_name["gitleaks-version"].message


def test_gitleaks_version_missing_binary_warns(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(secrets_gate.shutil, "which", lambda _: None)
    results = secrets_gate.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["gitleaks-version"].status == CheckStatus.WARN


def test_gitleaks_version_subprocess_failure_warns(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(secrets_gate.shutil, "which", lambda _: "/usr/local/bin/gitleaks")
    monkeypatch.setattr(
        secrets_gate.subprocess,
        "run",
        lambda *_, **__: _completed(1, stderr="boom\n"),
    )
    results = secrets_gate.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["gitleaks-version"].status == CheckStatus.WARN


# ---------------------------------------------------------------------------
# semgrep-binary probe
# ---------------------------------------------------------------------------


def test_semgrep_binary_missing_warns(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        secrets_gate.shutil,
        "which",
        lambda name: None if name == "semgrep" else "/usr/bin/" + name,
    )
    monkeypatch.setattr(
        secrets_gate.subprocess,
        "run",
        lambda *_, **__: _completed(0, stdout="v8.18.0\n"),
    )
    results = secrets_gate.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["semgrep-binary"].status == CheckStatus.WARN
    assert "pipx install semgrep" in by_name["semgrep-binary"].message


def test_semgrep_binary_present_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(secrets_gate.shutil, "which", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(
        secrets_gate.subprocess,
        "run",
        lambda *_, **__: _completed(0, stdout="v8.18.0\n"),
    )
    results = secrets_gate.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["semgrep-binary"].status == CheckStatus.OK
    assert "/usr/local/bin/semgrep" in by_name["semgrep-binary"].message


# ---------------------------------------------------------------------------
# semgrep-config probe
# ---------------------------------------------------------------------------


def test_semgrep_config_missing_warns(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(secrets_gate.shutil, "which", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(
        secrets_gate.subprocess,
        "run",
        lambda *_, **__: _completed(0, stdout="v8.18.0\n"),
    )
    results = secrets_gate.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["semgrep-config"].status == CheckStatus.WARN
    assert ".semgrep.yml" in by_name["semgrep-config"].message


def test_semgrep_config_present_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(secrets_gate.shutil, "which", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(
        secrets_gate.subprocess,
        "run",
        lambda *_, **__: _completed(0, stdout="v8.18.0\n"),
    )
    _seed_configs(tmp_path, gitleaks=False, semgrep=True)
    results = secrets_gate.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["semgrep-config"].status == CheckStatus.OK


# ---------------------------------------------------------------------------
# gitleaks-config probe
# ---------------------------------------------------------------------------


def test_gitleaks_config_missing_warns(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(secrets_gate.shutil, "which", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(
        secrets_gate.subprocess,
        "run",
        lambda *_, **__: _completed(0, stdout="v8.18.0\n"),
    )
    results = secrets_gate.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["gitleaks-config"].status == CheckStatus.WARN
    assert ".gitleaks.toml" in by_name["gitleaks-config"].message


def test_gitleaks_config_partial_warns(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Only .gitleaks.toml present without .gitleaksignore -> WARN."""
    monkeypatch.setattr(secrets_gate.shutil, "which", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(
        secrets_gate.subprocess,
        "run",
        lambda *_, **__: _completed(0, stdout="v8.18.0\n"),
    )
    (tmp_path / ".gitleaks.toml").write_text("title='t'\n", encoding="utf-8")
    results = secrets_gate.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["gitleaks-config"].status == CheckStatus.WARN
    assert ".gitleaksignore" in by_name["gitleaks-config"].message


def test_gitleaks_config_present_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(secrets_gate.shutil, "which", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(
        secrets_gate.subprocess,
        "run",
        lambda *_, **__: _completed(0, stdout="v8.18.0\n"),
    )
    _seed_configs(tmp_path, gitleaks=True, semgrep=False)
    results = secrets_gate.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["gitleaks-config"].status == CheckStatus.OK


# ---------------------------------------------------------------------------
# pre-commit-hook-installed probe
# ---------------------------------------------------------------------------


def test_pre_commit_hook_missing_warns(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(secrets_gate.shutil, "which", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(
        secrets_gate.subprocess,
        "run",
        lambda *_, **__: _completed(0, stdout="v8.18.0\n"),
    )
    results = secrets_gate.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["pre-commit-hook-installed"].status == CheckStatus.WARN
    assert "ai-eng install" in by_name["pre-commit-hook-installed"].message


def test_pre_commit_hook_without_marker_warns(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(secrets_gate.shutil, "which", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(
        secrets_gate.subprocess,
        "run",
        lambda *_, **__: _completed(0, stdout="v8.18.0\n"),
    )
    _seed_hooks(tmp_path, pre_commit_marker=False, pre_push_marker=True)
    results = secrets_gate.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["pre-commit-hook-installed"].status == CheckStatus.WARN


def test_pre_commit_hook_wired_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(secrets_gate.shutil, "which", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(
        secrets_gate.subprocess,
        "run",
        lambda *_, **__: _completed(0, stdout="v8.18.0\n"),
    )
    _seed_hooks(tmp_path, pre_commit_marker=True, pre_push_marker=True)
    results = secrets_gate.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["pre-commit-hook-installed"].status == CheckStatus.OK


# ---------------------------------------------------------------------------
# pre-push-hook-installed probe
# ---------------------------------------------------------------------------


def test_pre_push_hook_missing_warns(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(secrets_gate.shutil, "which", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(
        secrets_gate.subprocess,
        "run",
        lambda *_, **__: _completed(0, stdout="v8.18.0\n"),
    )
    results = secrets_gate.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["pre-push-hook-installed"].status == CheckStatus.WARN


def test_pre_push_hook_wired_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(secrets_gate.shutil, "which", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(
        secrets_gate.subprocess,
        "run",
        lambda *_, **__: _completed(0, stdout="v8.18.0\n"),
    )
    _seed_hooks(tmp_path, pre_commit_marker=True, pre_push_marker=True)
    results = secrets_gate.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["pre-push-hook-installed"].status == CheckStatus.OK


# ---------------------------------------------------------------------------
# Aggregate happy-path
# ---------------------------------------------------------------------------


def test_all_probes_ok_when_fully_provisioned(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(secrets_gate.shutil, "which", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(
        secrets_gate.subprocess,
        "run",
        lambda *_, **__: _completed(0, stdout="v8.18.0\n"),
    )
    _seed_configs(tmp_path, gitleaks=True, semgrep=True)
    _seed_hooks(tmp_path, pre_commit_marker=True, pre_push_marker=True)
    results = secrets_gate.check(_ctx(tmp_path))
    statuses = {r.name: r.status for r in results}
    assert all(status == CheckStatus.OK for status in statuses.values()), statuses
    assert set(statuses) == {
        "gitleaks-binary",
        "gitleaks-version",
        "semgrep-binary",
        "semgrep-config",
        "gitleaks-config",
        "pre-commit-hook-installed",
        "pre-push-hook-installed",
    }
