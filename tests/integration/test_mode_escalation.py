"""RED skeleton for spec-105 Phase 5 — branch / CI / pre-push mode escalation.

Covers G-3: ``policy/mode_dispatch.py:resolve_mode`` honors three escalation
triggers, returning ``regulated`` even when manifest declares ``prototyping``:

1. **Branch trigger** — current ``HEAD`` matches one of ``PROTECTED_BRANCHES``
   (currently ``{"main", "master"}``) or a release-branch glob (``release/*``).
2. **CI trigger** — any of ``CI=true``, ``GITHUB_ACTIONS=true``, or
   ``TF_BUILD=True`` env vars are present (covered in detail by
   ``test_ci_override.py``).
3. **Pre-push target trigger** — ``check_push_target()`` reads stdin or
   falls back to ``git rev-parse --abbrev-ref @{u}`` and escalates when
   the target ref is a protected branch.

Status: RED — ``policy/mode_dispatch.py`` does not yet exist (lands in
Phase 5 T-5.4 / T-5.5 / T-5.7).
Marker: ``@pytest.mark.spec_105_red`` — excluded by default CI run.
Will be unmarked in Phase 5 (T-5.19) once the dispatcher ships.

Lesson learned in Phase 1: deferred imports of the target wiring keep
pytest collection green while modules are still missing.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _seed_manifest(root: Path, mode: str = "prototyping") -> None:
    """Write a minimal ``manifest.yml`` declaring the requested mode."""
    state_dir = root / ".ai-engineering"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "manifest.yml").write_text(
        f"schemaVersion: 1\ngates:\n  mode: {mode}\n",
        encoding="utf-8",
    )


def test_mode_escalates_on_protected_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``resolve_mode`` returns ``regulated`` when HEAD is a protected branch.

    Even when ``manifest.gates.mode = prototyping``, a HEAD pointing at
    ``main``/``master`` triggers escalation per spec D-105-04.
    """
    from unittest.mock import patch

    # Deferred import: ``mode_dispatch`` lands in Phase 5 T-5.4. Until then
    # collection passes thanks to the marker but execution fails on import.
    from ai_engineering.policy import mode_dispatch

    _seed_manifest(tmp_path, mode="prototyping")
    monkeypatch.chdir(tmp_path)

    # Mock git symbolic-ref to return "main".
    with patch("subprocess.check_output", return_value="main\n"):
        result = mode_dispatch.resolve_mode(tmp_path, env={})

    assert result == "regulated"


def test_mode_escalates_on_ci_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``resolve_mode`` returns ``regulated`` when ``CI=true`` is present.

    CI is the canonical "don't trust the local mode" signal — even on a
    feat branch with ``prototyping`` declared, CI execution always escalates.
    """
    from unittest.mock import patch

    from ai_engineering.policy import mode_dispatch

    _seed_manifest(tmp_path, mode="prototyping")
    monkeypatch.chdir(tmp_path)

    with patch("subprocess.check_output", return_value="feat/x\n"):
        result = mode_dispatch.resolve_mode(tmp_path, env={"CI": "true"})

    assert result == "regulated"


def test_mode_escalates_on_pre_push_protected_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pre-push hook escalates when target ref is protected.

    ``check_push_target`` reads the canonical pre-push stdin format
    ``"<local_ref> <local_sha> <remote_ref> <remote_sha>"``. When
    ``remote_ref`` matches a protected branch, escalation fires.
    """
    from ai_engineering.policy import mode_dispatch

    _seed_manifest(tmp_path, mode="prototyping")
    monkeypatch.chdir(tmp_path)

    # The Phase 5 implementation will expose ``resolve_mode`` with a
    # ``push_target`` argument or read it from a known env var; this
    # skeleton uses the env-var spelling to keep the surface stable.
    result = mode_dispatch.resolve_mode(
        tmp_path,
        env={"AIENG_PUSH_TARGET_REF": "refs/heads/main"},
    )

    assert result == "regulated"
