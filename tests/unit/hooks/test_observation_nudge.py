"""SessionStart observation-nudge decision logic (spec-165 D-165-03).

The nudge fires when there are session-watch observations newer than the
last --review. The staleness check MUST be O(1) — it compares
observation-events.ndjson mtime against meta.json lastReviewedAt and
NEVER reads the (multi-MB) event stream.
"""

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOK_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "runtime-observation-nudge.py"
HOOK_DIR = REPO / ".ai-engineering" / "scripts" / "hooks"

_NDJSON_REL = ".ai-engineering/state/observation-events.ndjson"
_META_REL = ".ai-engineering/observations/meta.json"
# 2000-01-01T00:00:00Z as a POSIX timestamp; anchors the ndjson mtime.
_NDJSON_MTIME = 946684800.0


@pytest.fixture
def nudge(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.syspath_prepend(str(HOOK_DIR))
    sys.modules.pop("aieng_observation_nudge_test", None)
    spec = importlib.util.spec_from_file_location("aieng_observation_nudge_test", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed(project: Path, *, ndjson_bytes: bytes | None, last_reviewed: str | None) -> None:
    if ndjson_bytes is not None:
        nd = project / _NDJSON_REL
        nd.parent.mkdir(parents=True, exist_ok=True)
        nd.write_bytes(ndjson_bytes)
        os.utime(nd, (_NDJSON_MTIME, _NDJSON_MTIME))
    meta = project / _META_REL
    meta.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schemaVersion": "1.0", "lastReviewedAt": last_reviewed, "reviewDeltaThreshold": 10}
    meta.write_text(json.dumps(payload), encoding="utf-8")


def test_pending_when_never_reviewed(nudge, tmp_path: Path) -> None:
    _seed(tmp_path, ndjson_bytes=b'{"x":1}\n', last_reviewed=None)
    assert nudge._pending(tmp_path) is True


def test_pending_when_events_newer_than_review(nudge, tmp_path: Path) -> None:
    _seed(tmp_path, ndjson_bytes=b'{"x":1}\n', last_reviewed="1999-01-01T00:00:00Z")
    assert nudge._pending(tmp_path) is True


def test_not_pending_when_reviewed_after_events(nudge, tmp_path: Path) -> None:
    _seed(tmp_path, ndjson_bytes=b'{"x":1}\n', last_reviewed="2001-01-01T00:00:00Z")
    assert nudge._pending(tmp_path) is False


def test_not_pending_when_no_ndjson(nudge, tmp_path: Path) -> None:
    _seed(tmp_path, ndjson_bytes=None, last_reviewed=None)
    assert nudge._pending(tmp_path) is False


def test_not_pending_when_empty_ndjson(nudge, tmp_path: Path) -> None:
    _seed(tmp_path, ndjson_bytes=b"", last_reviewed=None)
    assert nudge._pending(tmp_path) is False


def test_fail_open_on_corrupt_meta(nudge, tmp_path: Path) -> None:
    # Corrupt meta + real events -> can't confirm a review -> nudge (safe default).
    nd = tmp_path / _NDJSON_REL
    nd.parent.mkdir(parents=True, exist_ok=True)
    nd.write_bytes(b'{"x":1}\n')
    os.utime(nd, (_NDJSON_MTIME, _NDJSON_MTIME))
    meta = tmp_path / _META_REL
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text('{"sche', encoding="utf-8")
    assert nudge._pending(tmp_path) is True


def test_pending_does_not_read_event_stream_contents(nudge, tmp_path: Path, monkeypatch) -> None:
    """O(1): the decision must rely on stat(), never on reading the stream."""
    _seed(tmp_path, ndjson_bytes=b'{"x":1}\n' * 1000, last_reviewed=None)
    import builtins

    real_open = builtins.open

    def _guard(file, *a, **k):
        if str(file).endswith("observation-events.ndjson"):
            raise AssertionError("nudge read the event stream — must be O(1) stat-only")
        return real_open(file, *a, **k)

    monkeypatch.setattr(builtins, "open", _guard)
    assert nudge._pending(tmp_path) is True
