"""Hexagonal layer-isolation enforcement (spec-127 D-127-09).

The domain layer (``tools/skill_domain/``) is the innermost ring of the
hex architecture and **must not** depend on the application or
infrastructure layers. This test walks every ``.py`` file under the
domain root, AST-parses it, collects every imported module name, and
asserts none resolve into ``skill_app`` / ``skill_infra`` (whether
imported as top-level distribution packages — the runtime contract per
``pyproject.toml`` ``pythonpath = ["src", "tools"]`` — or via the
``tools.skill_*`` filesystem-rooted form).

D-127-09 deliberately enforces the layering through this test rather
than a custom lint plugin: AST parsing keeps the rule readable in one
file and avoids inventing a project-specific lint surface that would
need its own maintenance.

A vacuous-pass guard (``len(walked_files) >= 1``) prevents the test
silently turning green if someone deletes the domain tree.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Repo root resolved relative to this test file so the suite remains
# portable across CI runners that may invoke pytest from different
# working directories.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOMAIN_ROOT = _REPO_ROOT / "tools" / "skill_domain"

# Banned import prefixes. Both the top-level distribution-package form
# (``skill_app.foo``) and the filesystem-rooted form
# (``tools.skill_app.foo``) are forbidden because either would couple
# the domain to an outer ring.
_BANNED_PREFIXES: tuple[str, ...] = (
    "skill_app",
    "skill_infra",
    "tools.skill_app",
    "tools.skill_infra",
)


def _collect_imports(tree: ast.Module) -> list[str]:
    """Return the dotted names of every import in ``tree``."""
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            # ``from X import Y`` — the module under inspection is X.
            # Relative imports (level > 0) cannot reach outside the
            # package, so they are domain-internal by construction;
            # ``node.module`` may still be ``None`` for ``from . import x``.
            names.append(node.module)
    return names


def _is_banned(module_name: str) -> bool:
    """Whether ``module_name`` resolves into a forbidden outer ring."""
    return any(
        module_name == banned or module_name.startswith(banned + ".") for banned in _BANNED_PREFIXES
    )


def test_domain_layer_has_no_outer_ring_imports() -> None:
    """``tools/skill_domain/`` must not import from app or infra."""
    walked_files: list[Path] = []
    violations: list[tuple[Path, str]] = []

    assert _DOMAIN_ROOT.is_dir(), (
        f"domain root missing: {_DOMAIN_ROOT}. "
        "M1 sub-002 must scaffold tools/skill_domain/ before this test runs."
    )

    for py_file in sorted(_DOMAIN_ROOT.rglob("*.py")):
        # Skip generated cache directories defensively (``rglob`` already
        # excludes them on most setups, but Python may write them on
        # import during pytest collection).
        if "__pycache__" in py_file.parts:
            continue
        walked_files.append(py_file)
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError as exc:  # pragma: no cover — would fail flake too
            pytest.fail(f"could not parse {py_file}: {exc}")
        for module_name in _collect_imports(tree):
            if _is_banned(module_name):
                violations.append((py_file, module_name))

    # Vacuous-pass guard: the domain tree must contain at least one
    # ``.py`` file or the assertion is meaningless. M1 ships ``rubric``,
    # ``skill_model``, ``agent_model`` so the floor is well above 1.
    assert len(walked_files) >= 1, (
        f"no .py files walked under {_DOMAIN_ROOT} — vacuous pass guard. "
        "Domain tree empty or path mis-resolved."
    )

    if violations:
        formatted = "\n".join(
            f"  {p.relative_to(_REPO_ROOT)} imports {mod!r}" for p, mod in violations
        )
        pytest.fail(
            f"domain layer imports forbidden outer-ring modules (D-127-09 violation):\n{formatted}"
        )
