"""spec-119 evaluation-layer test fixtures."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parents[3]
_HOOKS_DIR = _REPO_ROOT / ".ai-engineering" / "scripts" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


@pytest.fixture()
def lib_obs():
    """Hook-local stdlib observability module under spec-119 emit_eval_* helpers."""
    # Force reload so test isolation across modules cannot leak frozen state.
    if "_lib.observability" in sys.modules:
        del sys.modules["_lib.observability"]
    return importlib.import_module("_lib.observability")


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Minimal project tree so build_framework_event has the directories it expects."""
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
    (tmp_path / ".ai-engineering" / "specs").mkdir(parents=True)
    (tmp_path / ".ai-engineering" / "specs" / "spec.md").write_text("# Spec\n")
    (tmp_path / ".ai-engineering" / "specs" / "plan.md").write_text("# Plan\n")
    (tmp_path / ".ai-engineering" / "CONSTITUTION.md").write_text("# Identity\n")
    (tmp_path / ".ai-engineering" / "state" / "decision-store.json").write_text("{}\n")
    contexts = tmp_path / ".ai-engineering" / "contexts"
    (contexts / "team").mkdir(parents=True)
    (contexts / "team" / "lessons.md").write_text("# Lessons\n")
    (contexts / "team" / "conventions.md").write_text("# Conventions\n")
    return tmp_path


@pytest.fixture()
def ndjson_path(project_root: Path) -> Path:
    return project_root / ".ai-engineering" / "state" / "framework-events.ndjson"


@pytest.fixture()
def repo_root() -> Path:
    return _REPO_ROOT
