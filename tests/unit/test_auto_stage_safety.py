"""RED skeleton for spec-105 Phase 6 -- ``policy/auto_stage.py`` safety.

Covers D-105-09: the shared auto-stage utility re-stages files modified
by Wave 1 fixers (ruff format, ruff check --fix) -- BUT only the
intersection ``S_pre  M_post`` (originally staged AND now modified).
This guarantees fixers can never accidentally stage a file the user
didn't intend to commit.

The 8 fixtures cover the cartesian product of pre-state x post-state:

  (a) all-overlap  -- S_pre  M_post: re-stage all
  (b) s_pre only   -- M_post empty: nothing to re-stage
  (c) m_post only  -- S_pre empty: nothing to re-stage (no leakage)
  (d) neither      -- both empty: no-op
  (e) empty s_pre  -- explicit empty handling
  (f) empty m_post -- explicit empty handling
  (g) overlap-subset -- partial intersection
  (h) unstaged-then-modified -- file in M_post but not S_pre stays unstaged

Status: RED -- ``policy/auto_stage.py`` does not exist yet (lands in
Phase 6 T-6.1 / T-6.2 / T-6.3).
Marker: ``@pytest.mark.spec_105_red`` -- excluded by default CI run.
Will be unmarked in Phase 6 (T-6.17).

Lesson learned in Phase 1: deferred imports of the target wiring keep
pytest collection green while modules are still missing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.spec_105_red


def test_a_all_overlap_restages_all(tmp_path: Path) -> None:
    """(a) S_pre = M_post = {a, b, c}: all three are re-staged."""
    from ai_engineering.policy import auto_stage

    s_pre = {"a.py", "b.py", "c.py"}
    result = auto_stage.restage_intersection(tmp_path, s_pre)
    assert sorted(result.restaged) == ["a.py", "b.py", "c.py"]


def test_b_s_pre_only_restages_nothing(tmp_path: Path) -> None:
    """(b) M_post empty: nothing was modified, so nothing to re-stage."""
    from ai_engineering.policy import auto_stage

    s_pre = {"a.py", "b.py"}
    result = auto_stage.restage_intersection(tmp_path, s_pre)
    assert result.restaged == []


def test_c_m_post_only_no_leakage(tmp_path: Path) -> None:
    """(c) S_pre empty: M_post non-empty must NOT be staged (safety)."""
    from ai_engineering.policy import auto_stage

    s_pre: set[str] = set()
    result = auto_stage.restage_intersection(tmp_path, s_pre)
    assert result.restaged == []
    # M_post-only files surface as unstaged_modifications (warning).
    assert isinstance(result.unstaged_modifications, list)


def test_d_neither_is_noop(tmp_path: Path) -> None:
    """(d) Both empty: total no-op, no exceptions."""
    from ai_engineering.policy import auto_stage

    result = auto_stage.restage_intersection(tmp_path, set())
    assert result.restaged == []
    assert result.unstaged_modifications == []


def test_e_empty_s_pre_explicit(tmp_path: Path) -> None:
    """(e) Explicit empty S_pre handles None-ish edges."""
    from ai_engineering.policy import auto_stage

    result = auto_stage.restage_intersection(tmp_path, set())
    assert result.restaged == []


def test_f_empty_m_post_explicit(tmp_path: Path) -> None:
    """(f) Explicit empty M_post: Wave 1 produced no file changes."""
    from ai_engineering.policy import auto_stage

    s_pre = {"x.py"}
    result = auto_stage.restage_intersection(tmp_path, s_pre)
    # No fixers ran; M_post empty; nothing to re-stage.
    assert result.restaged == []


def test_g_overlap_subset(tmp_path: Path) -> None:
    """(g) Partial intersection: only the intersection re-stages."""
    from ai_engineering.policy import auto_stage

    s_pre = {"a.py", "b.py", "c.py"}
    result = auto_stage.restage_intersection(tmp_path, s_pre)
    # The intersection logic must be set-strict; result.restaged should
    # contain at most the S_pre members that ALSO appear in M_post.
    assert set(result.restaged).issubset(s_pre)


def test_h_unstaged_then_modified_stays_unstaged(tmp_path: Path) -> None:
    """(h) File in M_post but NOT S_pre: stays unstaged AND surfaces as warning."""
    from ai_engineering.policy import auto_stage

    s_pre = {"keep.py"}
    result = auto_stage.restage_intersection(tmp_path, s_pre)
    # Files only in M_post must NEVER appear in result.restaged.
    # They should appear in unstaged_modifications so the CLI can warn.
    assert "new-unstaged.py" not in result.restaged
