"""spec-139 M5.T1 — IOC catalogue + decision-store mtime cache contract.

``.ai-engineering/scripts/hooks/prompt-injection-guard.py`` fires on every
Bash / Edit / Write / MultiEdit tool call. Without caching the IOC
catalogue (~38 KB) it would be reparsed from disk per invocation, which
is the exact regression spec-139 M5.T1 closes.

These tests pin the module-level cache contract:

  * Cached payload is returned identity-stably across calls when the
    catalogue file mtime + size are unchanged.
  * Cache invalidates and re-reads when the catalogue mtime advances.
  * Missing catalogue returns ``{}`` and drops any stale cache entry.

Cross-platform: tests use ``tmp_path`` + ``Path.touch`` (no shell calls),
``monkeypatch.delenv`` for hermetic env isolation, and avoid any sleep
loops that would flake on Windows clock granularity. The cache helpers
are imported by file path so the test does not depend on a particular
sys.path layout.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOK_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "prompt-injection-guard.py"
HOOK_DIR = REPO / ".ai-engineering" / "scripts" / "hooks"


@pytest.fixture
def guard_module(monkeypatch: pytest.MonkeyPatch):
    """Reload the hook module fresh so module-scope caches start empty.

    The hook lives outside the importable package tree, so we load it by
    file path via importlib. ``sys.modules.pop`` + new spec guarantee a
    pristine ``_IOC_CACHE`` / ``_DECISION_STORE_CACHE`` per test.
    """
    # Hermetic env: never inherit a real ``AIENG_HOOK_CACHE_TTL_SEC`` from
    # the operator's shell.
    monkeypatch.delenv("AIENG_HOOK_CACHE_TTL_SEC", raising=False)
    monkeypatch.delenv("AIENG_RISK_ACCUMULATOR_DISABLED", raising=False)
    monkeypatch.syspath_prepend(str(HOOK_DIR))
    sys.modules.pop("aieng_pi_guard_test", None)
    spec = importlib.util.spec_from_file_location("aieng_pi_guard_test", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Reset the module-level caches in case import-time globals were
    # initialised non-empty by a fixture race.
    module._IOC_CACHE = None
    module._DECISION_STORE_CACHE = None
    return module


def _write_ioc_catalogue(project_root: Path, payload: dict) -> Path:
    """Write a fake IOC catalogue into the canonical location."""
    rel = Path(".ai-engineering") / "security" / "iocs" / "iocs.json"
    path = project_root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _bump_mtime(path: Path, *, advance_seconds: float = 2.0) -> None:
    """Advance a file's mtime deterministically.

    POSIX gives ns precision; Windows / FAT32 only guarantee 2 s. We bump
    by 2 s so the test passes on every filesystem in CI.
    """
    stat = path.stat()
    new_mtime = stat.st_mtime + advance_seconds
    os.utime(path, (stat.st_atime, new_mtime))


def test_load_iocs_returns_cached_payload_on_repeated_calls(guard_module, tmp_path: Path) -> None:
    """spec-139 M5.T1: repeated calls return the SAME cached dict object.

    Identity (``is``) match is the contract — proves we skipped the JSON
    re-parse rather than just returning equal-but-fresh dicts.
    """
    _write_ioc_catalogue(
        tmp_path,
        {"sensitive_paths": {"patterns": ["/etc/shadow"]}},
    )
    first = guard_module.load_iocs(tmp_path)
    second = guard_module.load_iocs(tmp_path)
    assert first is second, (
        "load_iocs MUST return the cached dict identity on repeated calls "
        "when the catalogue mtime + size are unchanged (spec-139 M5.T1)."
    )
    assert first == {"sensitive_paths": {"patterns": ["/etc/shadow"]}}


def test_load_iocs_invalidates_on_mtime_change(guard_module, tmp_path: Path) -> None:
    """spec-139 M5.T1: an mtime bump invalidates the cache and re-reads.

    Without this contract, an operator who hand-edits ``iocs.json`` mid-
    session would see stale IOC matches forever.
    """
    path = _write_ioc_catalogue(
        tmp_path,
        {"sensitive_paths": {"patterns": ["/etc/shadow"]}},
    )
    cached = guard_module.load_iocs(tmp_path)
    assert "sensitive_paths" in cached

    # Rewrite the catalogue with a different payload then bump mtime so
    # POSIX nanosecond resolution + Windows 2 s FAT granularity both
    # observe a change.
    path.write_text(
        json.dumps({"sensitive_paths": {"patterns": ["/etc/passwd"]}}, sort_keys=True),
        encoding="utf-8",
    )
    _bump_mtime(path)

    fresh = guard_module.load_iocs(tmp_path)
    assert fresh is not cached, (
        "load_iocs MUST return a fresh dict when the catalogue mtime advances "
        "(spec-139 M5.T1 invalidation contract)."
    )
    assert fresh["sensitive_paths"]["patterns"] == ["/etc/passwd"]


def test_load_iocs_missing_file_drops_cache(guard_module, tmp_path: Path) -> None:
    """spec-139 M5.T1 + spec-107 D-107-05: missing catalogue returns ``{}``.

    Also verifies the cache is dropped so a subsequent appearance of the
    file is observed on the very next call.
    """
    # No catalogue on disk -> empty dict, cache stays None.
    result = guard_module.load_iocs(tmp_path)
    assert result == {}
    assert guard_module._IOC_CACHE is None

    # Now write a catalogue and verify it is observed immediately.
    _write_ioc_catalogue(tmp_path, {"sensitive_env_vars": {"patterns": ["AWS_SECRET"]}})
    appeared = guard_module.load_iocs(tmp_path)
    assert appeared == {"sensitive_env_vars": {"patterns": ["AWS_SECRET"]}}


def test_decision_store_cache_identity_stable(guard_module, tmp_path: Path) -> None:
    """spec-139 M5.T1 (companion): decision-store cache mirrors IOC cache.

    The hook caches decision-store.json under the same TTL + mtime keying
    so risk-acceptance lookups are O(1) per process after the first read.
    """
    store = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    store.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "decisions": [
            {
                "finding_id": "sentinel-sensitive_paths-_etc_shadow",
                "status": "active",
                "risk_category": "risk-acceptance",
            }
        ]
    }
    store.write_text(json.dumps(payload), encoding="utf-8")
    first = guard_module._load_decision_store(tmp_path)
    second = guard_module._load_decision_store(tmp_path)
    assert first is second
    assert first["decisions"][0]["finding_id"] == "sentinel-sensitive_paths-_etc_shadow"
