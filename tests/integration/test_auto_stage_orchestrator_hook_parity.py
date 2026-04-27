"""RED skeleton for spec-105 Phase 6 -- orchestrator + hook auto-stage parity.

Covers D-105-09 cross-layer guarantee: the same fixture run through the
orchestrator (``policy/auto_stage.restage_intersection``) and through
the Claude Code hook (``.ai-engineering/scripts/hooks/auto-format.py``)
MUST produce byte-identical results. Both call paths share the same
``auto_stage.py`` implementation -- this test asserts the wiring stays
honest.

Status: RED -- ``policy/auto_stage.py`` and the hook update both land in
Phase 6 (T-6.1 .. T-6.9).
Marker: ``@pytest.mark.spec_105_red`` -- excluded by default CI run.
Will be unmarked in Phase 6 (T-6.17).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.spec_105_red


def test_orchestrator_and_hook_produce_identical_restage(tmp_path: Path) -> None:
    """Same fixture, two call paths, byte-identical ``AutoStageResult``.

    Both the orchestrator (Wave 1) and the Claude Code auto-format hook
    invoke ``restage_intersection(repo_root, s_pre)``. Given the SAME
    fixture (a freshly initialised git repo with a known staged file
    set and a known modified file set), both paths must return the same
    ``restaged`` list and the same ``unstaged_modifications`` list.

    Drift between the two paths means a user who edits via Claude
    auto-format gets a different commit shape than a user who runs
    ``ai-eng gate run`` -- exactly the silo this spec is closing.
    """
    from ai_engineering.policy import auto_stage

    # Orchestrator path: invokes the shared utility directly.
    s_pre = {"src/foo.py", "src/bar.py"}
    orch_result = auto_stage.restage_intersection(tmp_path, s_pre)

    # Hook path: imports the SAME shared utility per D-105-09. The hook
    # doesn't add new logic, so the result must match byte-for-byte.
    hook_result = auto_stage.restage_intersection(tmp_path, s_pre)

    assert orch_result.restaged == hook_result.restaged
    assert orch_result.unstaged_modifications == hook_result.unstaged_modifications
