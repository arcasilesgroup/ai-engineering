"""Unit-suite-only fixtures.

Wave 1 orchestrator tests in ``test_orchestrator_wave1.py`` assume the
working directory has an active spec when they don't ``monkeypatch.chdir``
into a synthetic project_root. Spec-127 Phase 6 cleanup deliberately left
the canonical ``.ai-engineering/specs/spec.md`` as the "No active spec"
placeholder; that broke the implicit assumption.

This conftest patches ``orchestrator._has_active_spec`` to return True
when the test has not pivoted into a tmp project. Tests that DO chdir
into a synthetic project (test 10 + the placeholder/pointer variants)
keep going through the real implementation so their explicit fixture
content drives the answer.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


def _is_tmp_cwd() -> bool:
    """Return True when the current working directory looks like a pytest tmp dir."""
    cwd = Path(os.getcwd()).resolve()
    tmp_root = Path(tempfile.gettempdir()).resolve()
    try:
        cwd.relative_to(tmp_root)
        return True
    except ValueError:
        pass
    # macOS pytest tmp dirs land under /private/var/folders too.
    cwd_str = str(cwd)
    return "/pytest-of-" in cwd_str or "/private/var/folders/" in cwd_str


@pytest.fixture(autouse=True)
def _wave1_active_spec_default(request: pytest.FixtureRequest) -> None:
    """Default ``_has_active_spec`` to True for wave1 tests that don't chdir.

    Only applies inside ``test_orchestrator_wave1.py``. Tests that
    ``monkeypatch.chdir`` into a tmp project keep the real impl.
    """
    if "test_orchestrator_wave1.py" not in str(request.fspath):
        return

    from ai_engineering.policy import orchestrator

    original = orchestrator._has_active_spec

    def _wrapper(project_root: Path | None = None) -> bool:
        # Caller passed an explicit project_root → defer (synthetic setups).
        if project_root is not None:
            return original(project_root)
        # Caller relies on cwd; if cwd is a pytest tmp dir, defer (test 10).
        if _is_tmp_cwd():
            return original(project_root)
        # Otherwise (repo root cwd) → active spec is the contract.
        return True

    monkeypatch = request.getfixturevalue("monkeypatch")
    monkeypatch.setattr(orchestrator, "_has_active_spec", _wrapper)
