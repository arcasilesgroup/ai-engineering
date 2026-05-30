"""Unit tests for dual-scope update precedence (spec sub-003, D10).

``ai-eng update`` resolves against both install scopes:

- ``--global`` reconciles only the home brain (``~/.ai-engineering/``);
- ``--local`` reconciles only the repo brain (``<repo>/.ai-engineering/``);
- no flag reconciles *both* scopes that exist.

Precedence is local-wins: a global update must never write into the repo
(local) tree, so an existing local install is authoritative for its own files.

HOME is monkeypatched so the tests never touch the operator's real home.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer.service import install
from ai_engineering.updater.service import (
    ScopeNotInstalledError,
    reconcile_scopes_with_skips,
    update,
    update_scopes,
)


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: fake_home))
    return fake_home


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    project = tmp_path / "repo"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "0.0.1"\n', encoding="utf-8"
    )
    return project


def _install_local(repo: Path) -> None:
    install(repo, stacks=["python"])


def _install_global(home: Path) -> None:
    from ai_engineering.installer.phases import InstallContext, InstallMode
    from ai_engineering.installer.phases.governance import GovernancePhase
    from ai_engineering.installer.phases.state import StatePhase

    context = InstallContext(
        target=home,  # target is ignored for brain in global scope
        mode=InstallMode.INSTALL,
        scope="global",
        surfaces=["claude-code"],
    )
    for phase in (GovernancePhase(), StatePhase()):
        phase.execute(phase.plan(context), context)


# ---------------------------------------------------------------------------
# Scope targeting
# ---------------------------------------------------------------------------


def test_global_update_targets_home_brain(home: Path, repo: Path) -> None:
    """`update(scope="global")` reconciles the home brain, not the repo."""
    _install_global(home)
    result = update(repo, dry_run=True, scope="global")
    # Every evaluated path lives under the home brain root.
    for change in result.changes:
        assert str(home) in str(change.path), (
            f"global update touched a non-home path: {change.path}"
        )


def test_global_update_reroots_ide_surfaces_to_home_skins(home: Path, repo: Path) -> None:
    """spec-156 D-156-05 (blocker 1): global update plans ~/.claude/CLAUDE.md,
    never the home-root ~/CLAUDE.md, so global installs stay updatable."""
    _install_global(home)
    result = update(repo, dry_run=True, scope="global")
    paths = {str(c.path) for c in result.changes}

    good = str(home / ".claude" / "CLAUDE.md")
    bad = str(home / "CLAUDE.md")
    assert good in paths, f"expected re-rooted {good} in planned paths: {sorted(paths)}"
    assert bad not in paths, f"global update planned a home-root orphan: {bad}"


def test_local_update_targets_repo_brain(home: Path, repo: Path) -> None:
    """`update(scope="local")` reconciles the repo brain, never the home brain."""
    _install_local(repo)
    _install_global(home)
    result = update(repo, dry_run=True, scope="local")
    for change in result.changes:
        assert str(home) not in str(change.path), (
            f"local update leaked into the home brain: {change.path}"
        )


def test_local_update_does_not_write_home(home: Path, repo: Path) -> None:
    """R3/D10: a local apply must never mutate the global (home) tree."""
    _install_local(repo)
    _install_global(home)
    home_manifest = home / ".ai-engineering" / "manifest.yml"
    before = home_manifest.read_text(encoding="utf-8")
    update(repo, dry_run=False, scope="local")
    after = home_manifest.read_text(encoding="utf-8")
    assert before == after, "local update must not touch the global home brain"


# ---------------------------------------------------------------------------
# No-flag reconciles both scopes
# ---------------------------------------------------------------------------


def test_update_scopes_runs_both_when_present(home: Path, repo: Path) -> None:
    """No-flag update reconciles both scopes that exist."""
    _install_local(repo)
    _install_global(home)
    results = update_scopes(repo, dry_run=True, scope=None)
    assert set(results) == {"local", "global"}


def test_update_scopes_local_only_when_no_global(home: Path, repo: Path) -> None:
    """No-flag update reconciles only the scopes that actually exist."""
    _install_local(repo)
    results = update_scopes(repo, dry_run=True, scope=None)
    assert set(results) == {"local"}


def test_update_scopes_explicit_global(home: Path, repo: Path) -> None:
    """Explicit `--global` targets only the home scope."""
    _install_local(repo)
    _install_global(home)
    results = update_scopes(repo, dry_run=True, scope="global")
    assert set(results) == {"global"}


# ---------------------------------------------------------------------------
# HIGH-2: absent scope must not be a silent success
# ---------------------------------------------------------------------------


def test_no_flag_records_absent_global_as_skipped(home: Path, repo: Path) -> None:
    """No-flag update must signal that global was absent, not silently no-op.

    Previously an absent global root merged an empty success, so output read
    "update complete" with no hint global was never installed. The runner now
    reports the absent scope as skipped instead of pretending it ran.
    """
    _install_local(repo)
    # No global install.
    results, skipped = reconcile_scopes_with_skips(repo, dry_run=True)
    assert set(results) == {"local"}
    assert "global" in skipped, "absent global scope must be surfaced as skipped"


def test_no_flag_no_skips_when_both_present(home: Path, repo: Path) -> None:
    """When both scopes exist, nothing is reported as skipped."""
    _install_local(repo)
    _install_global(home)
    results, skipped = reconcile_scopes_with_skips(repo, dry_run=True)
    assert set(results) == {"local", "global"}
    assert skipped == []


def test_explicit_global_absent_fails_loud(home: Path, repo: Path) -> None:
    """`--global` with no global install fails loud — never a silent empty run."""
    _install_local(repo)
    # No global install.
    with pytest.raises(ScopeNotInstalledError) as excinfo:
        update_scopes(repo, dry_run=True, scope="global")
    message = str(excinfo.value)
    assert "global" in message
    assert "ai-eng install --global" in message


# ---------------------------------------------------------------------------
# Global state marker + framework_version stamp (T-3.8 / D11)
# ---------------------------------------------------------------------------


def test_global_install_writes_home_marker_with_version(home: Path, repo: Path) -> None:
    """Global install writes ~/.ai-engineering/state/install-state.json + version stamp."""
    import json

    from ai_engineering import __version__

    _install_global(home)
    marker = home / ".ai-engineering" / "state" / "install-state.json"
    assert marker.is_file(), "global install must mirror the install marker into HOME"
    data = json.loads(marker.read_text(encoding="utf-8"))
    assert data.get("framework_version") == __version__, (
        "framework_version must be stamped so update can detect drift (D11)"
    )
