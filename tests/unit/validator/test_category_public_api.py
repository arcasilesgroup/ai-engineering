"""Public-API parity guard for validator category modules.

Introduced by spec-140 W2.5.T5. Greps every importer of
``ai_engineering.validator.categories.*`` in the codebase and asserts
every imported name still resolves to a callable / attribute on the
target module. This protects against silent breakage if a future
refactor splits or relocates the underlying implementation.

Production refactors W2.5.T1 (split manifest_coherence.py) and W2.5.T2
(split mirror_sync.py) were DEFERRED -- see CHANGELOG -- because the
D-140-07 LOC gate (test deletion >= 2x production-LOC overhead) was
incompatible with the per-dimension package split's import scaffolding
overhead. The parity test ships now so that any future split must keep
all symbols resolvable.
"""

from __future__ import annotations

import ast
import re
from importlib import import_module
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]

# Modules whose public API surfaces must remain stable.
_GUARDED_MODULES = (
    "ai_engineering.validator.categories",
    "ai_engineering.validator.categories.counter_accuracy",
    "ai_engineering.validator.categories.cross_references",
    "ai_engineering.validator.categories.file_existence",
    "ai_engineering.validator.categories.manifest_coherence",
    "ai_engineering.validator.categories.mirror_sync",
    "ai_engineering.validator.categories.required_tools",
    "ai_engineering.validator.categories.skill_frontmatter",
)


def _iter_python_files(root: Path) -> list[Path]:
    """Yield every .py file under repo root, skipping build/cache directories."""
    skip_dirs = {".venv", "venv", ".tox", "__pycache__", ".git", "node_modules", "build", "dist"}
    files: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in skip_dirs for part in path.parts):
            continue
        files.append(path)
    return files


_IMPORT_FROM_PATTERN = re.compile(
    r"^from\s+(ai_engineering\.validator\.categories(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)\s+import\s+(.+?)\s*(?:#.*)?$",
    re.MULTILINE,
)


def _collect_imports() -> dict[str, set[str]]:
    """Walk source for ``from ai_engineering.validator.categories... import ...`` statements.

    Returns a mapping ``module -> set(names)`` of every name imported
    from any of the guarded modules across the repo (excluding the
    guard test itself to avoid self-references).
    """
    imports: dict[str, set[str]] = {mod: set() for mod in _GUARDED_MODULES}

    for path in _iter_python_files(_REPO_ROOT):
        # Skip this test itself -- it references symbol names in strings.
        if path == Path(__file__):
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        # Use AST for robust import discovery (handles multiline imports).
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            module = node.module
            if module is None or module not in imports:
                continue
            for alias in node.names:
                # ``from foo import *`` is not actionable for parity.
                if alias.name == "*":
                    continue
                imports[module].add(alias.name)

    return imports


def test_every_imported_symbol_resolves() -> None:
    """For each guarded module, every imported name must be importable."""
    imports = _collect_imports()

    missing: list[str] = []
    for module_name, names in imports.items():
        if not names:
            continue
        module = import_module(module_name)
        for name in sorted(names):
            if not hasattr(module, name):
                missing.append(f"{module_name}::{name}")

    if missing:
        pytest.fail(
            "Public-API parity broken: the following symbols are imported "
            "elsewhere but no longer resolve on their declaring module. "
            "Restore them in the module's __all__ / re-exports.\n  - " + "\n  - ".join(missing)
        )


def test_check_functions_remain_callable() -> None:
    """The seven category check functions must remain callable from the categories package."""
    categories = import_module("ai_engineering.validator.categories")
    required = (
        "_check_counter_accuracy",
        "_check_cross_references",
        "_check_file_existence",
        "_check_manifest_coherence",
        "_check_mirror_sync",
        "_check_required_tools",
        "_check_skill_frontmatter",
    )
    for name in required:
        assert hasattr(categories, name), f"Missing public API: {name}"
        assert callable(getattr(categories, name)), f"Not callable: {name}"


def test_lint_service_imports_resolve() -> None:
    """tools/skill_app/lint_service.py is the canonical category orchestrator.

    Its imports must continue to resolve through the categories package
    even if W2.5.T1 / W2.5.T2 production splits land in a follow-up.
    """
    lint_service = import_module("skill_app.lint_service")
    for name in (
        "_check_counter_accuracy",
        "_check_cross_references",
        "_check_file_existence",
        "_check_manifest_coherence",
        "_check_mirror_sync",
        "_check_required_tools",
        "_check_skill_frontmatter",
        "_check_claude_commands_mirror",
        # spec-201 D-201-04: `_check_copilot_skills_mirror` deleted with
        # the `.github/skills` tree it validated.
        "_check_copilot_agents_mirror",
        "validate_content_integrity",
    ):
        assert hasattr(lint_service, name), f"lint_service lost public symbol: {name}"
