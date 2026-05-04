"""Drift-pin: `_DEFAULT_MODE` must stay in sync with CLAUDE.md guidance.

Per spec-120 follow-up, the integrity verification default flipped from
``warn`` to ``enforce``. CLAUDE.md documents that contract; this test pins
the source so a future revert silently lands a CI failure instead of
quietly weakening the security posture.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
INTEGRITY_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "integrity.py"


@pytest.fixture
def integrity_mod():
    spec = importlib.util.spec_from_file_location("aieng_integrity_pin", INTEGRITY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_mode_is_enforce(integrity_mod) -> None:
    """CLAUDE.md commits to fail-closed by default; pin the constant.

    Behaviour is governed by AIENG_HOOK_INTEGRITY_MODE; ``enforce`` is the
    default after the spec-120 governance review.
    """
    assert integrity_mod._DEFAULT_MODE == "enforce", (
        "Drift detected: _DEFAULT_MODE must stay 'enforce' per CLAUDE.md "
        "(Hooks Configuration → Integrity verification). Update CLAUDE.md "
        "first if intentional."
    )


def test_resolve_mode_returns_enforce_when_env_unset(
    integrity_mod, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AIENG_HOOK_INTEGRITY_MODE", raising=False)
    assert integrity_mod._resolve_mode() == "enforce"


def test_resolve_mode_honors_warn_opt_out(integrity_mod, monkeypatch: pytest.MonkeyPatch) -> None:
    """The dev-friendly opt-out must keep working (CLAUDE.md commits to it)."""
    monkeypatch.setenv("AIENG_HOOK_INTEGRITY_MODE", "warn")
    assert integrity_mod._resolve_mode() == "warn"


def test_resolve_mode_honors_off_opt_out(integrity_mod, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIENG_HOOK_INTEGRITY_MODE", "off")
    assert integrity_mod._resolve_mode() == "off"


def test_invalid_mode_falls_back_to_default(integrity_mod, monkeypatch: pytest.MonkeyPatch) -> None:
    """Bad env value → safe default (enforce). Defensive: typoed configs
    fail-closed instead of silently going to warn."""
    monkeypatch.setenv("AIENG_HOOK_INTEGRITY_MODE", "permissive")
    assert integrity_mod._resolve_mode() == "enforce"
