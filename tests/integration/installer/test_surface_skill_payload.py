"""Per-surface install-smoke gate for the skill payload (spec-201 D-201-05).

RK-13: deleting a per-surface skill tree without re-pointing its
``_SURFACE_TREE_MAPS`` entry leaves a consumer who installed with
``--surfaces <that surface>`` holding **zero skills**, silently and with
no error message, in their own repository.

This module is the characterization gate for that risk. It installs a
fresh consumer repository per surface and asserts, from the installed
tree alone:

1. every surface resolves the full skill set (``skills.total`` from the
   manifest — 54 today);
2. every surface resolves the shared ``handlers/`` payload that
   ``/ai-build`` reads at preflight.

Assertion 2 is deliberately RED for ``cursor`` and ``opencode`` before
the spec-201 collapse: ``templates/project/.cursor/skills`` and
``templates/project/.opencode/skills`` each ship 54 skill directories
with **zero** ``handlers/`` directories, which is the live defect
D-201-04 names. Re-pointing both surfaces at ``.agents/skills`` (18
handler directories) is what turns them green.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.domain.surface import SURFACE_IDS
from ai_engineering.installer.service import install

REPO_ROOT = Path(__file__).resolve().parents[3]

PYPROJECT = '[project]\nname = "surface-payload-smoke"\nversion = "0.0.1"\n'


@pytest.fixture(scope="module")
def expected_skill_total() -> int:
    """Manifest-declared canonical skill count (single source of truth)."""
    return load_manifest_config(REPO_ROOT).skills.total


@pytest.fixture(scope="module", params=SURFACE_IDS)
def installed_surface(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[str, Path]:
    """Install a fresh consumer repo enabling exactly one surface."""
    surface: str = request.param
    target = tmp_path_factory.mktemp(f"payload-{surface.replace('-', '_')}")
    (target / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    install(target, stacks=["python"], surfaces=[surface])
    return surface, target


def _skill_files(target: Path) -> list[Path]:
    """Return every ``SKILL.md`` resolvable in the installed tree."""
    return sorted(target.rglob("SKILL.md"))


def _skill_handler_dirs(target: Path) -> list[Path]:
    """Return ``handlers/`` directories that belong to a skill.

    Scoped to directories whose parent also holds a ``SKILL.md`` so the
    unrelated ``.ai-engineering/runbooks/handlers`` payload — installed
    for every surface — cannot make this assertion vacuous.
    """
    return sorted(
        path
        for path in target.rglob("handlers")
        if path.is_dir() and (path.parent / "SKILL.md").is_file()
    )


def test_surface_payload_resolves_full_skill_set(
    installed_surface: tuple[str, Path],
    expected_skill_total: int,
) -> None:
    """RK-13: every surface's install payload carries the full skill set."""
    surface, target = installed_surface
    skill_files = _skill_files(target)
    skill_names = {path.parent.name for path in skill_files}

    assert len(skill_names) >= expected_skill_total, (
        f"Surface {surface!r} installed {len(skill_names)} distinct skills, "
        f"expected at least {expected_skill_total}. A consumer installing "
        f"with --surfaces {surface} would be missing skills. Re-point that "
        "surface's _SURFACE_TREE_MAPS entry at .agents/skills."
    )


def test_surface_payload_ships_skill_handlers(
    installed_surface: tuple[str, Path],
) -> None:
    """D-201-04: every surface's skill payload carries ``handlers/``.

    ``/ai-build`` reads its handler files at preflight; a skills tree
    without them stops the skill before it dispatches.
    """
    surface, target = installed_surface
    handler_dirs = _skill_handler_dirs(target)

    assert handler_dirs, (
        f"Surface {surface!r} installed skills with zero handlers/ "
        "directories, so /ai-build stops at preflight for that consumer. "
        "Re-point the surface at .agents/skills, which ships 18."
    )
