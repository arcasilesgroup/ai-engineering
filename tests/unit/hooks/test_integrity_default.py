"""Tests for the spec-147 G1 integrity default flip (warn -> enforce).

CLAUDE.md and the ``_lib/integrity.py`` docstring both commit to
``enforce`` being the default. The module constant lagged behind at
``warn`` — a 3-way contradiction that left a fail-open gap: a hook whose
bytes drifted from the committed manifest ran silently with ALL
``AIENG_*`` env vars unset.

This module pins the sealed contract:

* ``_DEFAULT_MODE == "enforce"`` and ``integrity_mode()`` resolves to
  ``enforce`` when ``AIENG_HOOK_INTEGRITY_MODE`` is unset.
* A drifted (sha256-mismatch) script fails closed end-to-end through
  ``run_hook_safe`` with a non-zero ``SystemExit`` when no env var is set.
* The loud fail-closed signal names the ``AIENG_HOOK_INTEGRITY_MODE=warn``
  escape hatch and the ``regenerate-hooks-manifest.py`` recovery command.
* The ``warn`` escape hatch still relaxes to fail-open for active dev.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
INTEGRITY_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "integrity.py"
HOOK_COMMON_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "hook-common.py"


@pytest.fixture
def integ(monkeypatch: pytest.MonkeyPatch):
    """Load ``_lib/integrity.py`` under a fresh, env-clean module name."""
    monkeypatch.delenv("AIENG_HOOK_INTEGRITY_MODE", raising=False)
    spec = importlib.util.spec_from_file_location("aieng_integrity_default", INTEGRITY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if hasattr(module, "_MANIFEST_CACHE"):
        module._MANIFEST_CACHE.clear()
    return module


@pytest.fixture
def hc(monkeypatch: pytest.MonkeyPatch):
    """Load ``_lib/hook-common.py`` under a fresh module name."""
    monkeypatch.delenv("AIENG_HOOK_INTEGRITY_MODE", raising=False)
    sys.modules.pop("aieng_hook_common_default", None)
    monkeypatch.syspath_prepend(str(REPO / ".ai-engineering" / "scripts" / "hooks"))
    spec = importlib.util.spec_from_file_location("aieng_hook_common_default", HOOK_COMMON_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_hook_common_default"] = module
    spec.loader.exec_module(module)
    return module


def _sha(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _write_manifest(project: Path, hooks: dict[str, str]) -> None:
    manifest = project / ".ai-engineering" / "state" / "hooks-manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"schemaVersion": "1.0", "hooks": hooks}))


# ── T-1.1: the constant + resolved mode ──────────────────────────────────


def test_default_mode_constant_is_enforce(integ) -> None:
    """The headline flip: the module constant must be ``enforce``."""
    assert integ._DEFAULT_MODE == "enforce"


def test_integrity_mode_unset_env_resolves_enforce(integ, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AIENG_HOOK_INTEGRITY_MODE", raising=False)
    assert integ.integrity_mode() == "enforce"


def test_unrecognised_env_value_falls_back_to_enforce(
    integ, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A typo / stale value falls back to the fail-closed default, not warn."""
    monkeypatch.setenv("AIENG_HOOK_INTEGRITY_MODE", "not-a-valid-mode")
    assert integ.integrity_mode() == "enforce"


def test_warn_escape_hatch_still_relaxes(integ, monkeypatch: pytest.MonkeyPatch) -> None:
    """``AIENG_HOOK_INTEGRITY_MODE=warn`` keeps the dev fail-open posture."""
    monkeypatch.setenv("AIENG_HOOK_INTEGRITY_MODE", "warn")
    assert integ.integrity_mode() == "warn"


# ── T-1.2: drift fails closed end-to-end + loud hint ─────────────────────


def test_drifted_hook_reason_names_escape_hatch_under_enforce(
    integ, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no env var, a drifted hook must report a loud reason naming the
    ``AIENG_HOOK_INTEGRITY_MODE=warn`` escape hatch (so the fail-closed
    stderr line is actionable)."""
    monkeypatch.delenv("AIENG_HOOK_INTEGRITY_MODE", raising=False)
    integ._MANIFEST_CACHE.clear()
    project = tmp_path
    hook = project / "hook.py"
    hook.write_text("tampered")
    _write_manifest(project, {"hook.py": _sha("original")})

    ok, reason = integ.verify_hook_integrity(hook, project)

    assert ok is False
    assert reason is not None
    assert "sha256 mismatch" in reason
    assert "AIENG_HOOK_INTEGRITY_MODE=warn" in reason


def test_unenrolled_hook_reason_names_escape_hatch_under_enforce(
    integ, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    assert "AIENG_HOOK_INTEGRITY_MODE=warn" in reason


def test_run_hook_safe_fails_closed_with_unset_env(
    hc, integ, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """End-to-end: a drifted hook + unset env exits non-zero (fail-closed).

    This is the spec-147 G1 invariant: no gate or hook may exit 0 when its
    integrity contract is violated and no env var relaxes it.
    """
    monkeypatch.delenv("AIENG_HOOK_INTEGRITY_MODE", raising=False)
    project = tmp_path
    (project / ".ai-engineering").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))

    hook = project / "drifted-hook.py"
    hook.write_text("tampered-bytes")
    _write_manifest(project, {"drifted-hook.py": _sha("committed-bytes")})

    # Silence the audit emission (NDJSON writer is not under test here).
    monkeypatch.setattr(hc, "_emit_integrity_violation", lambda **kw: None)

    with pytest.raises(SystemExit) as exc_info:
        hc.run_hook_safe(
            lambda: None,
            component="hook.test",
            hook_kind="pre-tool-use",
            script_path=hook,
        )

    assert exc_info.value.code != 0
    captured = capsys.readouterr()
    assert "[hook-integrity]" in captured.err
    assert "regenerate-hooks-manifest.py" in captured.err


# ── spec-179: formatter reflow drifts the sha; re-pin recovers ───────────


def test_formatter_reflow_drifts_then_repin_recovers(
    integ, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """spec-179: reformatting a pinned script (100-col → 88-col reflow) changes
    its sha, so integrity fails closed; re-pinning the manifest to the on-disk
    bytes recovers it. Integrity code itself is UNCHANGED (D-179-05) — this pins
    the defect + the recovery semantics the doctor self-heal automates.
    """
    monkeypatch.delenv("AIENG_HOOK_INTEGRITY_MODE", raising=False)
    integ._MANIFEST_CACHE.clear()
    project = tmp_path
    hook = project / "auto-format.py"

    # 88-col reflow of a logically-identical 100-col canonical line.
    canonical = "value = ctx.project_root / '.ai-engineering' / 'state' / 'telemetry-debug.log'\n"
    reflow = (
        "value = (\n    ctx.project_root / '.ai-engineering' / 'state' / 'telemetry-debug.log'\n)\n"
    )
    hook.write_text(reflow, encoding="utf-8")

    # Manifest pins the canonical (committed) sha → on-disk reflow drifts.
    _write_manifest(project, {"auto-format.py": _sha(canonical)})
    ok, reason = integ.verify_hook_integrity(hook, project)
    assert ok is False
    assert reason is not None and "sha256 mismatch" in reason

    # Re-pin to the on-disk bytes (what `regenerate-hooks-manifest.py` writes).
    integ._MANIFEST_CACHE.clear()
    _write_manifest(project, {"auto-format.py": integ.compute_file_sha256(hook)})
    ok2, _ = integ.verify_hook_integrity(hook, project)
    assert ok2 is True, "re-pinning the manifest to on-disk bytes must recover integrity"
