"""spec-105 Phase 6 -- ``policy/auto_stage.py`` safety fixtures.

Covers D-105-09: the shared auto-stage utility re-stages files modified
by Wave 1 fixers (ruff format, ruff check --fix) -- BUT only the
intersection ``S_pre & M_post`` (originally staged AND now modified).
This guarantees fixers can never accidentally stage a file the user
didn't intend to commit.

The 8 fixtures cover the cartesian product of pre-state x post-state:

  (a) all-overlap  -- S_pre & M_post: re-stage all
  (b) s_pre only   -- M_post empty: nothing to re-stage
  (c) m_post only  -- S_pre empty: nothing to re-stage (no leakage)
  (d) neither      -- both empty: no-op
  (e) empty s_pre  -- explicit empty handling
  (f) empty m_post -- explicit empty handling
  (g) overlap-subset -- partial intersection
  (h) unstaged-then-modified -- file in M_post but not S_pre stays unstaged
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# --- Helpers ----------------------------------------------------------------


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    """Run a git command in ``repo_root``; raise on non-zero."""
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        check=True,
    )


def _init_repo(repo_root: Path) -> None:
    """Initialise a fresh git repo with a baseline commit."""
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "test")
    _git(repo_root, "config", "commit.gpgsign", "false")
    # Need an initial commit so ``git diff --cached`` has a HEAD to compare.
    (repo_root / ".gitkeep").write_text("", encoding="utf-8")
    _git(repo_root, "add", ".gitkeep")
    _git(repo_root, "commit", "-q", "-m", "initial")


def _stage(repo_root: Path, name: str, content: str = "x = 1\n") -> None:
    """Create and stage a file with ``content``."""
    (repo_root / name).write_text(content, encoding="utf-8")
    _git(repo_root, "add", name)


def _modify(repo_root: Path, name: str, content: str) -> None:
    """Overwrite an already-tracked file (no auto-stage)."""
    (repo_root / name).write_text(content, encoding="utf-8")


def _create_unstaged(repo_root: Path, name: str, content: str = "y = 2\n") -> None:
    """Create a file that exists in the worktree but is NOT in S_pre.

    To make it appear in ``git diff --name-only`` (M_post), we first commit
    a baseline version, then modify it without re-staging.
    """
    (repo_root / name).write_text("baseline\n", encoding="utf-8")
    _git(repo_root, "add", name)
    _git(repo_root, "commit", "-q", "-m", f"baseline {name}")
    (repo_root / name).write_text(content, encoding="utf-8")


# --- Fixture (a): all in S_pre + M_post ------------------------------------


def test_a_all_overlap_restages_all(tmp_path: Path) -> None:
    """(a) S_pre = M_post = {a, b, c}: all three are re-staged."""
    from ai_engineering.policy import auto_stage

    _init_repo(tmp_path)
    for name in ("a.py", "b.py", "c.py"):
        _stage(tmp_path, name, content="x = 1\n")
    s_pre = auto_stage.capture_staged_set(tmp_path)

    # Modify all three so they end up in M_post.
    for name in ("a.py", "b.py", "c.py"):
        _modify(tmp_path, name, content="x = 1  # touched\n")

    result = auto_stage.restage_intersection(tmp_path, s_pre)
    assert sorted(result.restaged) == ["a.py", "b.py", "c.py"]
    assert result.unstaged_modifications == []


# --- Fixture (b): S_pre only -----------------------------------------------


def test_b_s_pre_only_restages_nothing(tmp_path: Path) -> None:
    """(b) M_post empty: nothing was modified, so nothing to re-stage."""
    from ai_engineering.policy import auto_stage

    _init_repo(tmp_path)
    _stage(tmp_path, "a.py")
    _stage(tmp_path, "b.py")
    s_pre = auto_stage.capture_staged_set(tmp_path)

    # Do NOT modify any file -- M_post stays empty.

    result = auto_stage.restage_intersection(tmp_path, s_pre)
    assert result.restaged == []
    assert result.unstaged_modifications == []


# --- Fixture (c): M_post only (no overlap) ---------------------------------


def test_c_m_post_only_no_leakage(tmp_path: Path) -> None:
    """(c) S_pre empty: M_post non-empty must NOT be staged (safety)."""
    from ai_engineering.policy import auto_stage

    _init_repo(tmp_path)
    _create_unstaged(tmp_path, "leaky.py", content="leaked = True\n")

    s_pre: set[str] = set()
    result = auto_stage.restage_intersection(tmp_path, s_pre)
    assert result.restaged == []
    # M_post-only files surface as unstaged_modifications.
    assert "leaky.py" in result.unstaged_modifications


# --- Fixture (d): neither --------------------------------------------------


def test_d_neither_is_noop(tmp_path: Path) -> None:
    """(d) Both empty: total no-op, no exceptions."""
    from ai_engineering.policy import auto_stage

    _init_repo(tmp_path)
    result = auto_stage.restage_intersection(tmp_path, set())
    assert result.restaged == []
    assert result.unstaged_modifications == []


# --- Fixture (e): empty S_pre (explicit) -----------------------------------


def test_e_empty_s_pre_explicit(tmp_path: Path) -> None:
    """(e) Explicit empty S_pre handles None-ish edges."""
    from ai_engineering.policy import auto_stage

    _init_repo(tmp_path)
    # Some random modification in the worktree -- must NEVER be staged.
    _create_unstaged(tmp_path, "drifted.py", content="drift = True\n")

    result = auto_stage.restage_intersection(tmp_path, set())
    assert result.restaged == []


# --- Fixture (f): empty M_post (explicit) ----------------------------------


def test_f_empty_m_post_explicit(tmp_path: Path) -> None:
    """(f) Explicit empty M_post: Wave 1 produced no file changes."""
    from ai_engineering.policy import auto_stage

    _init_repo(tmp_path)
    _stage(tmp_path, "x.py")
    s_pre = auto_stage.capture_staged_set(tmp_path)

    # Do NOT touch x.py -- M_post stays empty.
    result = auto_stage.restage_intersection(tmp_path, s_pre)
    assert result.restaged == []


# --- Fixture (g): overlap subset ------------------------------------------


def test_g_overlap_subset(tmp_path: Path) -> None:
    """(g) Partial intersection: only the intersection re-stages."""
    from ai_engineering.policy import auto_stage

    _init_repo(tmp_path)
    for name in ("a.py", "b.py", "c.py"):
        _stage(tmp_path, name)
    s_pre = auto_stage.capture_staged_set(tmp_path)

    # Modify only a.py and b.py -- c.py stays clean.
    _modify(tmp_path, "a.py", "x = 1  # touched\n")
    _modify(tmp_path, "b.py", "x = 1  # touched\n")

    result = auto_stage.restage_intersection(tmp_path, s_pre)
    assert set(result.restaged) == {"a.py", "b.py"}
    assert "c.py" not in result.restaged


# --- Fixture (h): unstaged then modified ----------------------------------


def test_h_unstaged_then_modified_stays_unstaged(tmp_path: Path) -> None:
    """(h) File in M_post but NOT S_pre: stays unstaged AND surfaces as warning."""
    from ai_engineering.policy import auto_stage

    _init_repo(tmp_path)
    _stage(tmp_path, "keep.py", content="keep = True\n")
    s_pre = auto_stage.capture_staged_set(tmp_path)

    # Touch keep.py (in S_pre) AND a separate file that's tracked but
    # not staged in this round.
    _modify(tmp_path, "keep.py", "keep = True  # touched\n")
    _create_unstaged(tmp_path, "drifter.py", content="drifter = True\n")

    result = auto_stage.restage_intersection(tmp_path, s_pre)
    # Files only in M_post must NEVER appear in result.restaged.
    assert "drifter.py" not in result.restaged
    # Should appear in unstaged_modifications so the CLI can warn.
    assert "drifter.py" in result.unstaged_modifications
    # The intersection (keep.py) WAS re-staged.
    assert "keep.py" in result.restaged
