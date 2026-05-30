"""Integration: ``ai-eng install --global`` materializes home-scoped skins.

spec sub-003 D9 acceptance: a global install writes the brain into
``~/.ai-engineering/`` and the four home-capable surface skins into their
canonical home directories, while Cursor and Copilot emit guidance instead of
home files. ``--local`` (the default) is unchanged and stays repo-rooted.

HOME is monkeypatched to a tmp dir so the test never touches the operator's
real home directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer.phases import InstallContext, InstallMode
from ai_engineering.installer.phases.governance import GovernancePhase
from ai_engineering.installer.phases.ide_config import IdeConfigPhase


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: fake_home))
    return fake_home


@pytest.fixture
def target(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "smoke"\nversion = "0.0.1"\n', encoding="utf-8"
    )
    return repo


def _run_phase(phase, context: InstallContext) -> None:
    plan = phase.plan(context)
    phase.execute(plan, context)


# ---------------------------------------------------------------------------
# Global scope -- brain + home-capable skins
# ---------------------------------------------------------------------------


def test_global_state_persists_scope_to_home(home: Path, target: Path) -> None:
    """spec-156 D-156-07: a global install records scope='global' on the HOME marker."""
    import json

    from ai_engineering.installer.phases.state import StatePhase

    context = InstallContext(
        target=target,
        mode=InstallMode.INSTALL,
        scope="global",
        surfaces=["claude-code"],
    )
    _run_phase(GovernancePhase(), context)
    _run_phase(StatePhase(), context)

    marker = home / ".ai-engineering" / "state" / "install-state.json"
    assert marker.is_file()
    data = json.loads(marker.read_text(encoding="utf-8"))
    assert data["scope"] == "global"
    assert not (target / ".ai-engineering" / "state" / "install-state.json").exists()


def test_is_reinstall_scope_aware_for_global(home: Path, target: Path) -> None:
    """spec-156 D-156-07: --global reinstall detection checks the HOME marker."""
    from ai_engineering.cli_commands.core import _is_reinstall
    from ai_engineering.installer.phases.state import StatePhase

    context = InstallContext(
        target=target, mode=InstallMode.INSTALL, scope="global", surfaces=["claude-code"]
    )
    _run_phase(GovernancePhase(), context)
    _run_phase(StatePhase(), context)

    # Global marker exists at home, repo has none.
    assert _is_reinstall(target, scope="global") is True
    assert _is_reinstall(target, scope="local") is False
    assert _is_reinstall(target) is False  # repo-rooted default


def test_global_governance_writes_brain_to_home(home: Path, target: Path) -> None:
    """The governance (brain) phase writes ``.ai-engineering/`` under HOME."""
    context = InstallContext(
        target=target,
        mode=InstallMode.INSTALL,
        scope="global",
        surfaces=["claude-code"],
    )
    _run_phase(GovernancePhase(), context)

    assert (home / ".ai-engineering" / "manifest.yml").is_file()
    # The repo root must NOT receive the brain in global scope.
    assert not (target / ".ai-engineering" / "manifest.yml").exists()


def test_global_claude_code_skin_to_home(home: Path, target: Path) -> None:
    """claude-code skin materializes under ``~/.claude/`` (tree + CLAUDE.md)."""
    context = InstallContext(
        target=target,
        mode=InstallMode.INSTALL,
        scope="global",
        surfaces=["claude-code"],
    )
    _run_phase(IdeConfigPhase(), context)

    assert (home / ".claude").is_dir()
    assert (home / "CLAUDE.md").exists() is False  # not at home root
    assert (home / ".claude" / "CLAUDE.md").is_file()
    assert not (target / ".claude").exists()


def test_global_codex_agents_to_home(home: Path, target: Path) -> None:
    context = InstallContext(
        target=target,
        mode=InstallMode.INSTALL,
        scope="global",
        surfaces=["codex"],
    )
    _run_phase(IdeConfigPhase(), context)

    assert (home / ".codex" / "AGENTS.md").is_file()
    assert not (target / "AGENTS.md").exists()


def test_global_opencode_to_config_opencode(home: Path, target: Path) -> None:
    context = InstallContext(
        target=target,
        mode=InstallMode.INSTALL,
        scope="global",
        surfaces=["opencode"],
    )
    _run_phase(IdeConfigPhase(), context)

    assert (home / ".config" / "opencode" / "AGENTS.md").is_file()


def test_global_antigravity_never_writes_gemini_md(home: Path, target: Path) -> None:
    """R6: Antigravity writes ~/.gemini/AGENTS.md, never ~/.gemini/GEMINI.md."""
    context = InstallContext(
        target=target,
        mode=InstallMode.INSTALL,
        scope="global",
        surfaces=["antigravity"],
    )
    _run_phase(IdeConfigPhase(), context)

    assert (home / ".gemini" / "AGENTS.md").is_file()
    assert not (home / ".gemini" / "GEMINI.md").exists()


def test_global_cursor_emits_no_home_file(home: Path, target: Path) -> None:
    """Cursor has no home destination -- nothing is written under HOME."""
    context = InstallContext(
        target=target,
        mode=InstallMode.INSTALL,
        scope="global",
        surfaces=["cursor"],
    )
    _run_phase(IdeConfigPhase(), context)

    assert not (home / ".cursor").exists()


# ---------------------------------------------------------------------------
# Local scope -- unchanged repo-rooted behavior
# ---------------------------------------------------------------------------


def test_local_claude_code_stays_repo_rooted(home: Path, target: Path) -> None:
    context = InstallContext(
        target=target,
        mode=InstallMode.INSTALL,
        scope="local",
        surfaces=["claude-code"],
    )
    _run_phase(GovernancePhase(), context)
    _run_phase(IdeConfigPhase(), context)

    assert (target / ".ai-engineering" / "manifest.yml").is_file()
    assert (target / ".claude").is_dir()
    assert (target / "CLAUDE.md").is_file()
    # Nothing leaked into HOME.
    assert not (home / ".claude").exists()
    assert not (home / ".ai-engineering").exists()
