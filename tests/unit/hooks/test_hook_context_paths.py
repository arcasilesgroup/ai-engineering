"""Tests for ``_lib.hook_context`` canonical path constants (spec-125 T-2.1).

Spec-125 Wave 2 relocates two state-plane subdirectories to first-class
top-level locations under ``.ai-engineering/``:

  * ``runtime/`` — formerly ``.ai-engineering/state/runtime/``
  * ``cache/``   — formerly ``.ai-engineering/state/gate-cache/``
                   (consolidated under a single ``cache/`` umbrella with
                    ``cache/gate/`` as the gate-cache subdir).

The ``_lib/hook_context.py`` module is the single source of truth for
these locations so every hook script and cross-IDE wrapper resolves the
same path. This test pins the contract: given a ``project_root``, the
canonical helpers return the expected absolute paths.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOK_CONTEXT_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "hook_context.py"


@pytest.fixture
def hc():
    """Load ``_lib/hook_context.py`` under a fresh module name."""
    sys.modules.pop("aieng_lib_hook_context", None)
    spec = importlib.util.spec_from_file_location("aieng_lib_hook_context", HOOK_CONTEXT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_lib_hook_context"] = module
    spec.loader.exec_module(module)
    return module


def test_runtime_dir_resolves_under_project_root(hc, tmp_path: Path) -> None:
    """``RUNTIME_DIR(project_root)`` is ``<root>/.ai-engineering/runtime``."""
    project_root = tmp_path
    assert hc.RUNTIME_DIR(project_root) == project_root / ".ai-engineering" / "runtime"


def test_cache_dir_resolves_under_project_root(hc, tmp_path: Path) -> None:
    """``CACHE_DIR(project_root)`` is ``<root>/.ai-engineering/cache``."""
    project_root = tmp_path
    assert hc.CACHE_DIR(project_root) == project_root / ".ai-engineering" / "cache"


def test_path_helpers_are_exported_symbols(hc) -> None:
    """RUNTIME_DIR and CACHE_DIR are top-level module attributes."""
    assert hasattr(hc, "RUNTIME_DIR"), "_lib.hook_context must export RUNTIME_DIR"
    assert hasattr(hc, "CACHE_DIR"), "_lib.hook_context must export CACHE_DIR"


def test_path_helpers_have_no_pkg_imports() -> None:
    """``_lib/hook_context.py`` must not import from ``ai_engineering.*``.

    Hooks run pre-pip-install in fresh checkouts and pre-commit contexts;
    a pkg import would crash the hook. AST scan is import-side-effect-free.
    """
    source = HOOK_CONTEXT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("ai_engineering"):
                    offenders.append(f"import {alias.name}")
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("ai_engineering")
        ):
            offenders.append(f"from {node.module} import ...")
    assert offenders == [], (
        f"_lib/hook_context.py must not import from ai_engineering.*; found: {offenders}"
    )
