"""Tests for _WARNED_FALLBACKS dedup behaviour (spec-132 D-132-07).

The previous implementation emitted one warning per
``_warn_on_deprecated_fallbacks`` invocation per stale file. During
``ai-eng install`` the helper is called ~once per ``connect()`` and the
installer itself runs many ``connect()`` calls, so a fresh install
showed ~34 duplicate warning lines for the same JSON sidecars. The
spec-132 dedup contract is:

* Warn at most ONCE per (state_dir, filename) pair per process lifetime.
* ``_reset_fallback_warnings()`` clears the dedup set so tests can
  exercise both the dedup and the re-emit paths.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from ai_engineering.state import state_db


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Tmp project root with state dir and a single stale JSON fallback."""
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "ownership-map.json").write_text("{}", encoding="utf-8")
    return tmp_path


def test_warn_emits_once_then_dedups(project_root: Path, caplog) -> None:
    """spec-132 D-132-07: a single warning per (state_dir, file) pair.

    Ten consecutive invocations on the same path emit exactly one
    warning record. The set is module-level so it survives across
    direct helper calls without re-instantiating state_db.
    """
    state_db._reset_fallback_warnings()  # explicit fresh start per test
    state_dir = project_root / ".ai-engineering" / "state"

    with caplog.at_level(logging.WARNING):
        for _ in range(10):
            state_db._warn_on_deprecated_fallbacks(state_dir)

    matching = [r for r in caplog.records if "ownership-map.json" in r.getMessage()]
    assert len(matching) == 1, f"Expected exactly one warning across 10 calls; got {len(matching)}"


def test_reset_re_enables_warning(project_root: Path, caplog) -> None:
    """spec-132 D-132-07: ``_reset_fallback_warnings`` clears the set."""
    state_db._reset_fallback_warnings()
    state_dir = project_root / ".ai-engineering" / "state"

    with caplog.at_level(logging.WARNING):
        state_db._warn_on_deprecated_fallbacks(state_dir)
        before_reset = sum(1 for r in caplog.records if "ownership-map.json" in r.getMessage())
        state_db._reset_fallback_warnings()
        state_db._warn_on_deprecated_fallbacks(state_dir)
        after_reset = sum(1 for r in caplog.records if "ownership-map.json" in r.getMessage())

    assert before_reset == 1
    assert after_reset == 2, "Second warning should re-emit after reset"


def test_warned_fallbacks_module_set_exists() -> None:
    """spec-132 D-132-07: the dedup set lives at module scope."""
    assert hasattr(state_db, "_WARNED_FALLBACKS")
    assert isinstance(state_db._WARNED_FALLBACKS, set)


def test_dedup_is_per_file(project_root: Path, caplog) -> None:
    """Dedup is keyed on (state_dir, filename), not on state_dir alone.

    Two distinct stale files in the same state directory must each
    emit their own warning even though the directory is identical.
    """
    state_db._reset_fallback_warnings()
    state_dir = project_root / ".ai-engineering" / "state"
    # The fixture seeds ownership-map.json; add a second STILL-deprecated
    # file. (spec-148 P2: decision-store.json is canonical, not deprecated.)
    (state_dir / "install-state.json").write_text("{}", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        state_db._warn_on_deprecated_fallbacks(state_dir)
        state_db._warn_on_deprecated_fallbacks(state_dir)

    file_messages = {
        r.getMessage().split("found at")[1].split(";")[0].strip()
        for r in caplog.records
        if "stale state JSON fallback found" in r.getMessage()
    }
    assert len(file_messages) == 2, f"Expected one warning per file, got files: {file_messages}"
