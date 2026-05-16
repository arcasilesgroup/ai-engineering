"""Architecture: template tree completeness (spec-128 Wave 4).

Catches the next time someone adds ``from foo_lib import bar`` in a hot-path
script without shipping ``foo_lib`` into the template tree. That class of
regression caused the user-reported ``ModuleNotFoundError: skill_scripts_lib``
in installed targets (the lib lived in source `.ai-engineering/scripts/skills/`
but the installer copies only the root scripts list — not the `skills/` subtree).

Two assertions:

1. **Presence** — the skill_scripts_lib + skill_scripts subtrees ship in the
   installer template tree (`src/ai_engineering/templates/.ai-engineering/
   scripts/skills/`).
2. **Drift** — every `from skill_scripts_lib.<mod> import ...` or
   `from skill_scripts.<mod> import ...` in a templated `.py` resolves to a
   shipped file inside the same template tree.

Stdlib + well-known third-party modules (``yaml``, ``ai_engineering``) are not
checked — only the in-tree consumer libs that the installer is responsible for
shipping.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATE_SCRIPTS = (
    _REPO_ROOT / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "scripts"
)
_TEMPLATE_SKILLS = _TEMPLATE_SCRIPTS / "skills"

# Libs we DO ship into target projects' `.ai-engineering/scripts/skills/`.
# Any new in-tree lib must be added here AND shipped under the same dir.
_IN_TREE_LIB_PACKAGES = frozenset({"skill_scripts_lib", "skill_scripts"})

# Expected files for each shipped lib subtree.
_REQUIRED_LIB_FILES: dict[str, tuple[str, ...]] = {
    "skill_scripts_lib": (
        "__init__.py",
        "git_activity.py",
        "markdown_render.py",
        "manifest_reader.py",
    ),
    "skill_scripts": (
        "__init__.py",
        "cleanup_run.py",
        "resolve_classify.py",
        "standup_render.py",
    ),
}


def test_template_skills_subtree_exists() -> None:
    """The `skills/` subtree must exist in the installer template tree."""
    assert _TEMPLATE_SKILLS.is_dir(), (
        f"Template tree missing `skills/` subtree at {_TEMPLATE_SKILLS}. "
        "Without this, installed projects raise ModuleNotFoundError on "
        "session_bootstrap.py / commit_compose.py / pr_body_compose.py."
    )


@pytest.mark.parametrize("lib", sorted(_REQUIRED_LIB_FILES))
def test_template_lib_files_present(lib: str) -> None:
    """Each in-tree lib package ships every module the source has."""
    lib_dir = _TEMPLATE_SKILLS / lib
    assert lib_dir.is_dir(), f"Missing template lib dir: {lib_dir}"
    for name in _REQUIRED_LIB_FILES[lib]:
        path = lib_dir / name
        assert path.is_file(), f"Missing template lib file: {path}"


def _iter_imported_from(py_path: Path) -> list[str]:
    """Yield the top-level module name from each `from X import …` in a .py."""
    try:
        tree = ast.parse(py_path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        pytest.fail(f"{py_path} failed AST parse: {exc}")
    bases: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                bases.append(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                bases.append(alias.name.split(".")[0])
    return bases


def test_every_in_tree_import_target_is_shipped() -> None:
    """Every `from skill_scripts_lib.X` or `from skill_scripts.X` import in any
    templated `.py` must resolve inside the template tree.

    Stdlib and out-of-tree modules (e.g. ``yaml``, ``ai_engineering``) are
    skipped — they are not the installer's responsibility.
    """
    unresolved: list[tuple[str, str]] = []
    for py in sorted(_TEMPLATE_SCRIPTS.rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        for base in _iter_imported_from(py):
            if base not in _IN_TREE_LIB_PACKAGES:
                continue
            init_path = _TEMPLATE_SKILLS / base / "__init__.py"
            if not init_path.exists():
                rel = py.relative_to(_REPO_ROOT)
                unresolved.append((str(rel), base))
    assert not unresolved, "In-tree imports without shipped target:\n" + "\n".join(
        f"  {src}: from {pkg} import …" for src, pkg in unresolved
    )
