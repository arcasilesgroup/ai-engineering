"""RED skeleton for spec-105 Phase 5 — detached-HEAD fallback.

Covers G-3 (resilience): when ``git symbolic-ref --short HEAD`` raises
``subprocess.CalledProcessError`` (the canonical signal for a detached
HEAD or repo-less directory), ``resolve_mode`` returns the conservative
``regulated`` default rather than propagating the exception.

This protects two real-world cases:
1. Bisect / cherry-pick sessions where HEAD is detached.
2. CI runners that check out a tag rather than a branch.

Status: RED — ``policy/mode_dispatch.py:resolve_mode`` does not exist yet
(lands in Phase 5 T-5.7).
Marker: ``@pytest.mark.spec_105_red`` — excluded by default CI run.
Will be unmarked in Phase 5 (T-5.19).

Lesson learned in Phase 1: deferred imports of the target wiring keep
pytest collection green while modules are still missing.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def test_resolve_mode_returns_regulated_on_detached_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``CalledProcessError`` from ``git symbolic-ref`` → ``regulated`` fallback.

    Even with ``manifest.gates.mode = prototyping``, a detached HEAD
    (``CalledProcessError`` on the symbolic-ref query) must escalate to
    ``regulated`` — the conservative default keeps Tier 2 active when
    the dispatcher cannot determine the branch context.
    """
    from unittest.mock import patch

    from ai_engineering.policy import mode_dispatch

    # Seed a manifest declaring prototyping so the fallback is observable.
    state_dir = tmp_path / ".ai-engineering"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "manifest.yml").write_text(
        "schemaVersion: 1\ngates:\n  mode: prototyping\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    # Force git symbolic-ref to raise the detached-HEAD canonical error.
    error = subprocess.CalledProcessError(returncode=128, cmd=["git", "symbolic-ref"])
    with patch("subprocess.check_output", side_effect=error):
        result = mode_dispatch.resolve_mode(tmp_path, env={})

    assert result == "regulated"
