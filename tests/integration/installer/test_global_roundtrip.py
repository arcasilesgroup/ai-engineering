"""End-to-end global scope round-trip (spec-156 W7).

Drives the REAL install pipeline (not hand-rolled phase calls, which masked
audit blockers 1-3), then update + doctor, asserting a --global install:
  - persists operator choices to ~/.ai-engineering/manifest.yml
  - leaves NO phantom repo-local marker
  - is cleanly updatable (no ~/CLAUDE.md orphan; zero spurious changes)
  - reports a single 'global' scope from doctor
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer.service import install_with_pipeline


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
    r = tmp_path / "repo"
    r.mkdir()
    (r / "pyproject.toml").write_text(
        '[project]\nname = "rt"\nversion = "0.0.1"\n', encoding="utf-8"
    )
    return r


def test_global_install_update_doctor_roundtrip(home: Path, repo: Path) -> None:
    install_with_pipeline(
        repo,
        stacks=["python"],
        surfaces=["claude-code", "codex"],
        vcs_provider="github",
        scope="global",
    )

    # 1. Brain + skins live under HOME; repo stays clean (no phantom marker).
    assert (home / ".ai-engineering" / "state" / "install-state.json").is_file()
    assert (home / ".claude" / "CLAUDE.md").is_file()
    assert (home / ".codex" / "AGENTS.md").is_file()
    assert not (repo / ".ai-engineering").exists()
    assert not (home / "CLAUDE.md").exists()  # never the home root

    # 2. Operator choices persisted to the HOME manifest, not template defaults.
    import yaml

    manifest = yaml.safe_load(
        (home / ".ai-engineering" / "manifest.yml").read_text(encoding="utf-8")
    )
    assert set(manifest["surfaces"]["enabled"]) >= {"claude-code", "codex"}

    # 3. Scope persisted on the install marker.
    import json

    state = json.loads(
        (home / ".ai-engineering" / "state" / "install-state.json").read_text(encoding="utf-8")
    )
    assert state["scope"] == "global"

    # 4. Global update is clean — no home-root orphan planned.
    from ai_engineering.updater.service import update

    result = update(repo, dry_run=True, scope="global")
    planned = {str(c.path) for c in result.changes}
    assert str(home / "CLAUDE.md") not in planned
    assert str(home / "AGENTS.md") not in planned

    # 5. Doctor reports a single 'global' scope.
    from ai_engineering.doctor.models import DoctorContext
    from ai_engineering.doctor.runtime.scope_status import check

    msg = check(DoctorContext(target=repo))[0].message
    assert "global" in msg
    assert "local" not in msg
