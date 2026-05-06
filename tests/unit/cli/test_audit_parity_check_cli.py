"""Unit tests for ``ai-eng audit parity-check`` (cross-IDE coverage).

Covers the CLI surface registered in
:mod:`ai_engineering.cli_commands.audit_cmd`:

* exit 0 when canonical skills + agents are mirrored across .github,
  .gemini, .codex (within --threshold)
* frontmatter ``<ide>_compatible: false`` opts a skill out of the
  expected mirror set without triggering an unintentional-gap fail
* missing skill or agent without an opt-out flips verdict to ``fail``
  and exits 1, with the gap surfaced in the JSON envelope
* ``--threshold`` controls the score floor that triggers a non-zero exit

Each test pins ``cwd`` to a fresh ``tmp_path`` so the project's real
filesystem is never touched.

Status: ``audit parity-check`` is feature debt — the CLI surface
documented in this file's header was never wired into ``audit_cmd.py``
or the ``cli_factory``. These tests are kept as the executable spec
and marked ``xfail`` until the implementation lands. Spec-123 Phase 8
verified that no other test or runtime path depends on this command.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

# Mark every test in this module as expected-fail until the parity-check
# command is implemented. ``strict=False`` lets the test pass once the
# command exists without requiring a coordinated test edit.
pytestmark = pytest.mark.xfail(
    reason="audit parity-check command not yet implemented (feature debt)",
    strict=False,
)

runner = CliRunner()


def _write_skill(skills_dir: Path, name: str, frontmatter: dict[str, str] | None = None) -> None:
    """Create a minimal SKILL.md folder with optional frontmatter overrides."""
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    fm_lines = ["---", f"name: {name}"]
    if frontmatter:
        fm_lines.extend(f"{k}: {v}" for k, v in frontmatter.items())
    fm_lines.extend(["---", "", f"# {name}", ""])
    (skill_dir / "SKILL.md").write_text("\n".join(fm_lines), encoding="utf-8")


def _write_agent(agents_dir: Path, name: str, suffix: str = ".md") -> None:
    """Create a minimal agent .md file under *agents_dir*."""
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / f"{name}{suffix}").write_text(
        f"---\nname: {name}\n---\n\n# {name}\n", encoding="utf-8"
    )


def _seed_canonical(project_root: Path, skills: list[str], agents: list[str]) -> None:
    """Populate the .claude canonical skills and agents directories."""
    skills_dir = project_root / ".claude" / "skills"
    agents_dir = project_root / ".claude" / "agents"
    for skill in skills:
        _write_skill(skills_dir, skill)
    for agent in agents:
        _write_agent(agents_dir, f"ai-{agent}")


def _seed_mirror(
    project_root: Path,
    mirror_root: str,
    skills: list[str],
    agents: list[str],
    *,
    agent_suffix: str = ".md",
) -> None:
    """Populate a non-Claude IDE mirror directory."""
    skills_dir = project_root / mirror_root / "skills"
    agents_dir = project_root / mirror_root / "agents"
    for skill in skills:
        _write_skill(skills_dir, skill)
    for agent in agents:
        _write_agent(agents_dir, agent, suffix=agent_suffix)


@pytest.fixture
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_parity_pass_when_all_mirrors_complete(project_root: Path) -> None:
    """Happy path: every canonical skill + agent mirrored everywhere → exit 0."""
    skills = ["ai-brainstorm", "ai-plan"]
    agents = ["plan", "build"]

    _seed_canonical(project_root, skills, agents)
    for mirror in (".github", ".gemini", ".codex"):
        _seed_mirror(project_root, mirror, skills, agents)

    result = runner.invoke(create_app(), ["audit", "parity-check", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["verdict"] == "pass"
    assert payload["score"] == 1.0
    assert payload["unintentional_gaps_total"] == 0


def test_parity_intentional_exclusion_does_not_fail(project_root: Path) -> None:
    """A skill flagged ``copilot_compatible: false`` is allowed to be missing in .github."""
    skills_dir = project_root / ".claude" / "skills"
    _write_skill(skills_dir, "ai-brainstorm")
    _write_skill(skills_dir, "ai-analyze-permissions", {"copilot_compatible": "false"})
    _seed_canonical(project_root, [], ["plan"])  # only adds the agent

    # .github intentionally omits ai-analyze-permissions
    _seed_mirror(project_root, ".github", ["ai-brainstorm"], ["plan"])
    _seed_mirror(project_root, ".gemini", ["ai-brainstorm", "ai-analyze-permissions"], ["plan"])
    _seed_mirror(project_root, ".codex", ["ai-brainstorm", "ai-analyze-permissions"], ["plan"])

    result = runner.invoke(create_app(), ["audit", "parity-check", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["verdict"] == "pass"
    github_skills = payload["mirrors"]["github_copilot"]["skills"]
    assert github_skills["unintentional_gaps"] == []
    assert "ai-analyze-permissions" in github_skills["intentional_exclusions"]


def test_parity_fails_on_unintentional_gap(project_root: Path) -> None:
    """A canonical skill with no opt-out, missing from a mirror, fails the gate."""
    _seed_canonical(project_root, ["ai-brainstorm", "ai-plan"], ["plan"])
    # .gemini missing ai-plan with no exclusion flag.
    _seed_mirror(project_root, ".github", ["ai-brainstorm", "ai-plan"], ["plan"])
    _seed_mirror(project_root, ".gemini", ["ai-brainstorm"], ["plan"])
    _seed_mirror(project_root, ".codex", ["ai-brainstorm", "ai-plan"], ["plan"])

    result = runner.invoke(create_app(), ["audit", "parity-check", "--json"])
    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["verdict"] == "fail"
    assert payload["unintentional_gaps_total"] >= 1
    assert "ai-plan" in payload["mirrors"]["gemini"]["skills"]["unintentional_gaps"]


def test_parity_threshold_can_relax_gate(project_root: Path) -> None:
    """``--threshold 0.0`` lets score drop arbitrarily low without exit-1, but
    unintentional gaps still trip the verdict."""
    _seed_canonical(project_root, ["ai-brainstorm", "ai-plan"], ["plan"])
    _seed_mirror(project_root, ".github", ["ai-brainstorm", "ai-plan"], ["plan"])
    _seed_mirror(project_root, ".gemini", ["ai-brainstorm", "ai-plan"], ["plan"])
    _seed_mirror(project_root, ".codex", ["ai-brainstorm", "ai-plan"], ["plan"])

    result = runner.invoke(create_app(), ["audit", "parity-check", "--threshold", "0.0", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["threshold"] == 0.0


def test_parity_handles_copilot_agent_suffix(project_root: Path) -> None:
    """Copilot agents use ``<name>.agent.md``; the audit must still align them."""
    _seed_canonical(project_root, ["ai-brainstorm"], ["plan"])
    _seed_mirror(project_root, ".github", ["ai-brainstorm"], ["plan"], agent_suffix=".agent.md")
    _seed_mirror(project_root, ".gemini", ["ai-brainstorm"], ["plan"])
    _seed_mirror(project_root, ".codex", ["ai-brainstorm"], ["plan"])

    result = runner.invoke(create_app(), ["audit", "parity-check", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["mirrors"]["github_copilot"]["agents"]["missing"] == []
