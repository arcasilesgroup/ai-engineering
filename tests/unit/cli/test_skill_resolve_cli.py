"""Contract tests for ``ai-eng skill resolve`` (spec-201 D-201-11).

The resolver is READ-ONLY metadata: it maps a skill name to its canonical
``SKILL.md`` path, the surface that owns it, and the handler / reference sets
beside it. It deliberately does NOT execute anything — the spec's Non-Goals
reject an ``ai-eng skill run`` verb, so nothing here asserts execution
behaviour (§10.2 YAGNI).

Every test pins ``--target`` at a ``tmp_path`` project so the repository's own
skill tree is never the subject, except the one case that resolves a real
canonical skill end to end.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.skills.service import SkillResolution, resolve_skill

runner = CliRunner()

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _seed_skill(root: Path, surface: str, name: str, *, handlers: tuple[str, ...] = ()) -> Path:
    """Create ``<root>/<surface>/<name>/SKILL.md`` plus optional handlers."""
    skill_dir = root / surface / name
    _write(
        skill_dir / "SKILL.md",
        f"---\nname: {name}\ndescription: demo skill\n---\n\n# {name}\n",
    )
    for handler in handlers:
        _write(skill_dir / "handlers" / handler, f"# handler {handler}\n")
    return skill_dir / "SKILL.md"


@pytest.fixture
def demo_project(tmp_path: Path) -> Path:
    """A tmp project with one Claude-surface skill carrying two handlers."""
    _seed_skill(tmp_path, ".claude/skills", "ai-demo", handlers=("a.md", "b.md"))
    return tmp_path


# ── Service layer ────────────────────────────────────────────────────────────


def test_resolve_skill_returns_path_surface_and_handlers(demo_project: Path) -> None:
    """The domain function returns the canonical path plus both handlers."""
    resolution = resolve_skill(demo_project, "ai-demo")
    assert isinstance(resolution, SkillResolution)
    assert resolution.name == "ai-demo"
    assert resolution.file_path == ".claude/skills/ai-demo/SKILL.md"
    assert resolution.surface == ".claude/skills"
    assert resolution.handlers == [
        ".claude/skills/ai-demo/handlers/a.md",
        ".claude/skills/ai-demo/handlers/b.md",
    ]
    assert resolution.references == []


def test_resolve_skill_returns_none_for_unknown_name(demo_project: Path) -> None:
    """An unknown name is a ``None``, not an exception — the CLI owns the exit."""
    assert resolve_skill(demo_project, "ai-does-not-exist") is None


def test_claude_surface_wins_over_agents_surface(tmp_path: Path) -> None:
    """A skill in BOTH trees resolves to `.claude/skills` — `_SKILL_DIRS` order."""
    _seed_skill(tmp_path, ".claude/skills", "ai-dual", handlers=("claude-side.md",))
    _seed_skill(tmp_path, ".agents/skills", "ai-dual", handlers=("agents-side.md",))

    resolution = resolve_skill(tmp_path, "ai-dual")
    assert resolution is not None
    assert resolution.surface == ".claude/skills"
    assert resolution.file_path == ".claude/skills/ai-dual/SKILL.md"
    assert resolution.handlers == [".claude/skills/ai-dual/handlers/claude-side.md"]


def test_agents_surface_resolves_when_claude_absent(tmp_path: Path) -> None:
    """The shared tree is a real resolution source, not a fallback that never fires."""
    _seed_skill(tmp_path, ".agents/skills", "ai-shared")
    resolution = resolve_skill(tmp_path, "ai-shared")
    assert resolution is not None
    assert resolution.surface == ".agents/skills"


# ── CLI adapter ──────────────────────────────────────────────────────────────


def test_resolve_prints_path_and_handlers(demo_project: Path) -> None:
    """Human output names the SKILL.md path and every handler."""
    result = runner.invoke(
        create_app(),
        ["skill", "resolve", "ai-demo", "--target", str(demo_project)],
    )
    assert result.exit_code == 0, result.output
    assert ".claude/skills/ai-demo/SKILL.md" in result.output
    assert "handlers/a.md" in result.output
    assert "handlers/b.md" in result.output


def test_bare_name_resolves_identically_to_prefixed_name(demo_project: Path) -> None:
    """`demo` and `ai-demo` hit the same skill — one normalisation site."""
    bare = runner.invoke(
        create_app(),
        ["--json", "skill", "resolve", "demo", "--target", str(demo_project)],
    )
    prefixed = runner.invoke(
        create_app(),
        ["--json", "skill", "resolve", "ai-demo", "--target", str(demo_project)],
    )
    assert bare.exit_code == 0, bare.output
    assert prefixed.exit_code == 0, prefixed.output
    assert _envelope(bare.output)["result"] == _envelope(prefixed.output)["result"]


def test_json_envelope_carries_the_full_resolution(demo_project: Path) -> None:
    """``--json`` emits the `emit_success` envelope with every documented key."""
    result = runner.invoke(
        create_app(),
        ["--json", "skill", "resolve", "ai-demo", "--target", str(demo_project)],
    )
    assert result.exit_code == 0, result.output
    envelope = _envelope(result.output)
    assert envelope["ok"] is True
    assert envelope["command"] == "ai-eng skill resolve"
    payload = envelope["result"]
    assert payload["name"] == "ai-demo"
    assert payload["file_path"] == ".claude/skills/ai-demo/SKILL.md"
    assert payload["surface"] == ".claude/skills"
    assert payload["handlers"] == [
        ".claude/skills/ai-demo/handlers/a.md",
        ".claude/skills/ai-demo/handlers/b.md",
    ]
    assert payload["references"] == []


def test_unknown_skill_exits_non_zero_naming_the_searched_surfaces(demo_project: Path) -> None:
    """An unknown name fails loudly and legibly — never a traceback."""
    result = runner.invoke(
        create_app(),
        ["skill", "resolve", "ai-nope", "--target", str(demo_project)],
    )
    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert ".claude/skills" in result.output
    assert ".agents/skills" in result.output


def test_resolves_a_real_canonical_skill_with_handlers() -> None:
    """End to end against this repository: `ai-build` resolves with handlers."""
    resolution = resolve_skill(_PROJECT_ROOT, "ai-build")
    assert resolution is not None
    assert resolution.file_path == ".claude/skills/ai-build/SKILL.md"
    assert resolution.handlers, "ai-build declares handlers; resolver found none"


def _envelope(output: str) -> dict:
    """Extract the trailing JSON envelope from CLI output."""
    start = output.index("{")
    return json.loads(output[start:])
