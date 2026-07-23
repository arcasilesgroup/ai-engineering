"""Architecture guard: the one-shot spec-193 runner is never agent-autoloaded."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_RELATIVE = ".ai-engineering/scripts/spec-193"
STATE_ROOT_MARKER = "agent-cli/spec-193"
AUTOLOAD_SURFACES = (
    ".claude",
    ".agents",
    ".codex",
    ".github",
    ".cursor",
    ".opencode",
    "src/ai_engineering/templates",
    "scripts/sync_mirrors",
    "pyproject.toml",
)


def _text_files(surface: Path) -> list[Path]:
    if surface.is_file():
        return [surface]
    return [path for path in surface.rglob("*") if path.is_file()]


def test_cutover_runner_and_private_state_are_absent_from_autoload_surfaces() -> None:
    violations: list[str] = []
    for relative in AUTOLOAD_SURFACES:
        surface = REPO_ROOT / relative
        if not surface.exists():
            continue
        for path in _text_files(surface):
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if RUNNER_RELATIVE in content or STATE_ROOT_MARKER in content:
                violations.append(path.relative_to(REPO_ROOT).as_posix())

    assert violations == []


def test_cutover_runner_contains_no_skill_or_cli_registration_surface() -> None:
    runner = REPO_ROOT / RUNNER_RELATIVE

    assert not list(runner.rglob("SKILL.md"))
    assert "if __name__" not in (runner / "security_cutover.py").read_text(encoding="utf-8")


def test_persistence_doctrine_declares_the_external_spec_193_boundary() -> None:
    doctrine = (REPO_ROOT / "docs/persistence-doctrine.md").read_text(encoding="utf-8")

    assert "Spec-193 external migration bundle" in doctrine
    assert "agent-cli/spec-193" in doctrine
    assert "derived, rebuildable projection" in doctrine


def test_private_spec_193_bundle_cannot_be_listed_by_repository_status() -> None:
    status = subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=REPO_ROOT, text=True)

    assert STATE_ROOT_MARKER not in status
