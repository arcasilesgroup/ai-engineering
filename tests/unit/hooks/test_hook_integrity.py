"""Tests for `_lib/integrity.py` -- hook script sha256 manifest verification.

Pin the three modes (`enforce`/`warn`/`off`) and the unenrolled-hook policy.
Earlier versions returned True for any hook missing from the manifest, even
in enforce mode -- that turned the integrity check into an allow-list bypass.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
INTEGRITY_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "integrity.py"


@pytest.fixture
def integ(monkeypatch: pytest.MonkeyPatch):
    spec = importlib.util.spec_from_file_location("aieng_integrity", INTEGRITY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Bust any cache from a prior test in the same process.
    if hasattr(module, "_MANIFEST_CACHE"):
        module._MANIFEST_CACHE.clear()
    return module


def _sha(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _write_manifest(project: Path, hooks: dict[str, str]) -> None:
    manifest = project / ".ai-engineering" / "state" / "hooks-manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"schemaVersion": "1.0", "hooks": hooks}))


def test_match_returns_ok(integ, tmp_path: Path) -> None:
    project = tmp_path
    hook = project / "hook.py"
    hook.write_text("real")
    rel = "hook.py"
    _write_manifest(project, {rel: _sha("real")})
    ok, reason = integ.verify_hook_integrity(hook, project)
    assert ok is True
    assert reason is None


def test_mismatch_returns_failure_reason(integ, tmp_path: Path) -> None:
    project = tmp_path
    hook = project / "hook.py"
    hook.write_text("tampered")
    _write_manifest(project, {"hook.py": _sha("original")})
    ok, reason = integ.verify_hook_integrity(hook, project)
    assert ok is False
    assert reason is not None
    assert "sha256 mismatch" in reason


def test_unenrolled_hook_allowed_in_warn_mode(
    integ, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AIENG_HOOK_INTEGRITY_MODE", "warn")
    project = tmp_path
    hook = project / "new-hook.py"
    hook.write_text("anything")
    _write_manifest(project, {"other-hook.py": _sha("x")})
    ok, reason = integ.verify_hook_integrity(hook, project)
    assert ok is True
    assert reason is None


def test_unenrolled_hook_refused_in_enforce_mode(
    integ, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The headline regression: enforce mode must NOT silently allow hooks
    missing from the manifest."""
    monkeypatch.setenv("AIENG_HOOK_INTEGRITY_MODE", "enforce")
    integ._MANIFEST_CACHE.clear()
    project = tmp_path
    hook = project / "new-hook.py"
    hook.write_text("anything")
    _write_manifest(project, {"other-hook.py": _sha("x")})
    ok, reason = integ.verify_hook_integrity(hook, project)
    assert ok is False
    assert reason is not None
    assert "not enrolled" in reason


def test_load_manifest_caches_on_mtime(integ, tmp_path: Path) -> None:
    project = tmp_path
    _write_manifest(project, {"a.py": _sha("a")})
    integ._MANIFEST_CACHE.clear()
    first = integ.load_manifest(project)
    second = integ.load_manifest(project)
    # Same dict instance returned on cache hit (cheap identity check is enough
    # to prove we did not reparse from disk).
    assert first is second


def test_load_manifest_busts_cache_on_edit(integ, tmp_path: Path) -> None:
    project = tmp_path
    _write_manifest(project, {"a.py": _sha("a")})
    integ._MANIFEST_CACHE.clear()
    integ.load_manifest(project)
    # Force a different mtime by writing fresh bytes after a small sleep wouldn't
    # be deterministic; bump mtime explicitly.
    manifest = project / ".ai-engineering" / "state" / "hooks-manifest.json"
    import os

    new_mtime = manifest.stat().st_mtime + 5
    os.utime(manifest, (new_mtime, new_mtime))
    _write_manifest(project, {"a.py": _sha("b")})
    os.utime(manifest, (new_mtime + 1, new_mtime + 1))
    second = integ.load_manifest(project)
    assert second["a.py"] == _sha("b")


def test_default_mode_is_enforce(integ, monkeypatch: pytest.MonkeyPatch) -> None:
    """spec-120 follow-up: the default flipped from ``warn`` to ``enforce``.

    With no env override, the integrity check must fail-closed. Anyone who
    needs the old lenient default explicitly opts in via
    ``AIENG_HOOK_INTEGRITY_MODE=warn`` (documented in CLAUDE.md)."""
    monkeypatch.delenv("AIENG_HOOK_INTEGRITY_MODE", raising=False)
    assert integ.integrity_mode() == "enforce"


def test_unset_env_uses_enforce_for_unenrolled_hook(
    integ, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unset env var must inherit the new fail-closed default for the
    unenrolled-hook policy too -- the previous behaviour silently allowed any
    new hook through, now it must refuse."""
    monkeypatch.delenv("AIENG_HOOK_INTEGRITY_MODE", raising=False)
    integ._MANIFEST_CACHE.clear()
    project = tmp_path
    hook = project / "new-hook.py"
    hook.write_text("anything")
    _write_manifest(project, {"other-hook.py": _sha("x")})
    ok, reason = integ.verify_hook_integrity(hook, project)
    assert ok is False
    assert reason is not None
    assert "not enrolled" in reason


def test_unrecognised_env_value_falls_back_to_enforce(
    integ, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A typo or stale value (e.g. ``AIENG_HOOK_INTEGRITY_MODE=foo``) must
    fail-closed via the default rather than silently disabling the check."""
    monkeypatch.setenv("AIENG_HOOK_INTEGRITY_MODE", "not-a-valid-mode")
    assert integ.integrity_mode() == "enforce"
