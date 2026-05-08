"""Tests for ``_lib/risk_accumulator.py`` — the PRISM-style session risk score.

Pin the contracts that downstream wiring (``prompt-injection-guard.py``
block path, ``runtime-guard.py`` warn check) depends on:

* **Severity scoring** — the public mapping (LOW=1, MEDIUM=5, HIGH=20,
  CRITICAL=50) must be the literal dispatch table; ``add()`` must use
  it, not a recomputed copy.
* **Threshold ladder** — each band ``silent / warn / block /
  force_stop`` must trigger at exactly the documented score, including
  the boundaries.
* **TTL decay** — exponential ``0.95**minute`` applied at read time so
  a long-quiet session is forgiven without explicit reset.
* **Repeat-signal weighting** — same ``ioc_id`` within 60 minutes
  earns the documented multipliers (1.5x for one prior, 2.5x for
  two-or-more priors).
* **Ring buffer cap** — ``RING_BUFFER_CAP`` events maximum so the
  state file stays small.
* **Atomic writes** — no ``.tmp`` litter on the happy path.
* **Corruption tolerance** — malformed JSON returns ``score=0``
  rather than crashing the host hook.
* **Reset** — wipes the persisted file unconditionally.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
LIB_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "risk_accumulator.py"


@pytest.fixture
def risk(monkeypatch: pytest.MonkeyPatch):
    """Load risk_accumulator fresh per test (monkey-safe)."""
    monkeypatch.syspath_prepend(str(REPO / ".ai-engineering" / "scripts" / "hooks"))
    sys.modules.pop("aieng_risk_accumulator", None)
    spec = importlib.util.spec_from_file_location("aieng_risk_accumulator", LIB_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_risk_accumulator"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "runtime").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _state_path(project: Path) -> Path:
    return project / ".ai-engineering" / "runtime" / "risk-score.json"


def test_severity_to_score_mapping(risk) -> None:
    """The public severity table is the dispatch table; values are exact."""
    assert risk.SEVERITY_SCORES["LOW"] == 1.0
    assert risk.SEVERITY_SCORES["MEDIUM"] == 5.0
    assert risk.SEVERITY_SCORES["HIGH"] == 20.0
    assert risk.SEVERITY_SCORES["CRITICAL"] == 50.0


def test_threshold_ladder(risk) -> None:
    """Each ladder rung returns the documented label at the boundary."""
    # Below 10 -> silent.
    assert risk.threshold_action(0) == "silent"
    assert risk.threshold_action(5) == "silent"
    assert risk.threshold_action(9.99) == "silent"
    # 10 <= score < 30 -> warn.
    assert risk.threshold_action(10) == "warn"
    assert risk.threshold_action(15) == "warn"
    assert risk.threshold_action(29.99) == "warn"
    # 30 <= score < 60 -> block.
    assert risk.threshold_action(30) == "block"
    assert risk.threshold_action(45) == "block"
    assert risk.threshold_action(59.99) == "block"
    # >= 60 -> force_stop.
    assert risk.threshold_action(60) == "force_stop"
    assert risk.threshold_action(100) == "force_stop"


def test_decay_on_read(risk, project: Path) -> None:
    """A score of 20, 30 minutes old, must decay to ~6.96 (= 20 * 0.95**30)."""
    past = datetime.now(UTC) - timedelta(minutes=30)
    iso = past.strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "schemaVersion": "1.0",
        "session_id": "s1",
        "score": 20.0,
        "last_update_ts": iso,
        "events": [],
    }
    _state_path(project).write_text(json.dumps(payload), encoding="utf-8")

    state = risk.get(project, session_id="s1")
    expected = 20.0 * (0.95**30)  # ≈ 6.96
    assert abs(state.score - expected) < 0.5, (
        f"decay mismatch: got {state.score}, expected ~{expected}"
    )


def test_repeat_signal_weighting_1_5x(risk, project: Path) -> None:
    """Same ioc_id once in last 60 min → next add() applies 1.5x multiplier."""
    now = datetime.now(UTC)
    five_min_ago = now - timedelta(minutes=5)
    iso_old = five_min_ago.strftime("%Y-%m-%dT%H:%M:%SZ")
    iso_now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Pre-seed: 1 prior fire of "ioc-x" 5 min ago.
    payload = {
        "schemaVersion": "1.0",
        "session_id": "s1",
        "score": 0.0,  # decayed to 0; only the events matter for repeat counting.
        "last_update_ts": iso_now_str,
        "events": [
            {
                "ts": iso_old,
                "ioc_id": "ioc-x",
                "severity": "MEDIUM",
                "score_added": 5.0,
                "source": "prompt-injection-guard",
            }
        ],
    }
    _state_path(project).write_text(json.dumps(payload), encoding="utf-8")

    state = risk.add(project, session_id="s1", severity="MEDIUM", ioc_id="ioc-x", now=now)
    # base_score = 5, multiplier = 1.5 -> add 7.5; previous score is 0.
    assert abs(state.score - 7.5) < 0.01, f"expected 7.5, got {state.score}"


def test_repeat_signal_weighting_2_5x(risk, project: Path) -> None:
    """Two+ priors in last 60 min → next add() applies 2.5x multiplier."""
    now = datetime.now(UTC)
    iso_now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    iso_5 = (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    iso_10 = (now - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = {
        "schemaVersion": "1.0",
        "session_id": "s1",
        "score": 0.0,
        "last_update_ts": iso_now_str,
        "events": [
            {
                "ts": iso_10,
                "ioc_id": "ioc-y",
                "severity": "MEDIUM",
                "score_added": 5.0,
                "source": "prompt-injection-guard",
            },
            {
                "ts": iso_5,
                "ioc_id": "ioc-y",
                "severity": "MEDIUM",
                "score_added": 5.0,
                "source": "prompt-injection-guard",
            },
        ],
    }
    _state_path(project).write_text(json.dumps(payload), encoding="utf-8")

    state = risk.add(project, session_id="s1", severity="MEDIUM", ioc_id="ioc-y", now=now)
    # base_score = 5, multiplier = 2.5 -> add 12.5; previous score is 0.
    assert abs(state.score - 12.5) < 0.01, f"expected 12.5, got {state.score}"


def test_ring_buffer_limit(risk, project: Path) -> None:
    """Adding 60 events must leave at most ``RING_BUFFER_CAP`` retained."""
    cap = risk.RING_BUFFER_CAP
    for i in range(60):
        # Distinct ioc_ids so repeat-weighting doesn't skew the score.
        risk.add(project, session_id="s1", severity="LOW", ioc_id=f"ioc-{i}")
    state = risk.get(project, session_id="s1")
    assert len(state.events) <= cap


def test_atomic_write_no_tmp_leftover(risk, project: Path) -> None:
    """Happy-path add() must not leave a ``.tmp`` sibling behind."""
    risk.add(project, session_id="s1", severity="HIGH", ioc_id="ioc-z")
    runtime = project / ".ai-engineering" / "runtime"
    leftovers = [p.name for p in runtime.iterdir() if p.suffix == ".tmp"]
    assert leftovers == [], f"unexpected .tmp leftovers: {leftovers}"


def test_corruption_falls_back_to_fresh(risk, project: Path) -> None:
    """Malformed JSON in risk-score.json must yield a fresh ``score=0`` snapshot."""
    _state_path(project).write_text("not valid json {{{", encoding="utf-8")
    state = risk.get(project, session_id="s1")
    assert state.score == 0.0
    assert state.session_id == "s1"


def test_reset_clears_state(risk, project: Path) -> None:
    """``reset()`` removes the file; subsequent ``get()`` is fresh."""
    risk.add(project, session_id="s1", severity="CRITICAL", ioc_id="ioc-q")
    assert _state_path(project).exists()
    risk.reset(project)
    assert not _state_path(project).exists()
    state = risk.get(project, session_id="s1")
    assert state.score == 0.0
