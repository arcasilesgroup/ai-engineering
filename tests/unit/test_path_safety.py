"""Unit tests for ai_engineering.lib.path_safety (spec-128 sub-d).

Verifies the shared path-traversal sanitiser:

* ``safe_realpath_within`` rejects paths that resolve outside the base.
* ``safe_resolve_within`` shares the same guarantee with ``Path`` return.
* ``PathTraversalError`` inherits from ``ValueError`` (legacy compat).
* Symlinks that escape the base are rejected (realpath resolution).
* The trusted base path itself is accepted.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ai_engineering.lib.path_safety import (
    PathTraversalError,
    safe_realpath_within,
    safe_resolve_within,
)


class TestSafeRealpathWithin:
    """Tests for safe_realpath_within()."""

    def test_accepts_path_inside_base(self, tmp_path: Path) -> None:
        candidate = tmp_path / "sub" / "file.txt"
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text("ok", encoding="utf-8")
        result = safe_realpath_within(candidate, tmp_path)
        assert result == os.path.realpath(candidate)

    def test_accepts_base_itself(self, tmp_path: Path) -> None:
        result = safe_realpath_within(tmp_path, tmp_path)
        assert result == os.path.realpath(tmp_path)

    def test_rejects_path_outside_base(self, tmp_path: Path) -> None:
        outside = tmp_path.parent / "escape.txt"
        with pytest.raises(PathTraversalError, match="resolves outside"):
            safe_realpath_within(outside, tmp_path)

    def test_rejects_dotdot_escape(self, tmp_path: Path) -> None:
        candidate = tmp_path / "sub" / ".." / ".." / "evil.txt"
        with pytest.raises(PathTraversalError):
            safe_realpath_within(candidate, tmp_path)

    def test_rejects_symlink_escape(self, tmp_path: Path) -> None:
        outside_dir = tmp_path.parent / "outside_dir"
        outside_dir.mkdir(parents=True, exist_ok=True)
        try:
            link = tmp_path / "link"
            link.symlink_to(outside_dir)
            candidate = link / "evil.txt"
            with pytest.raises(PathTraversalError):
                safe_realpath_within(candidate, tmp_path)
        finally:
            if outside_dir.exists():
                outside_dir.rmdir()

    def test_returns_string_type(self, tmp_path: Path) -> None:
        result = safe_realpath_within(tmp_path / "f.txt", tmp_path)
        assert isinstance(result, str)

    def test_accepts_string_inputs(self, tmp_path: Path) -> None:
        candidate = tmp_path / "sub" / "file.txt"
        result = safe_realpath_within(str(candidate), str(tmp_path))
        assert result == os.path.realpath(candidate)

    def test_does_not_match_partial_prefix(self, tmp_path: Path) -> None:
        """A sibling whose name prefixes base must be rejected.

        e.g. base=/tmp/foo, candidate=/tmp/foobar/file — the literal
        prefix check would falsely accept this without the os.sep guard.
        """
        sibling = tmp_path.parent / f"{tmp_path.name}_sibling"
        sibling.mkdir(parents=True, exist_ok=True)
        try:
            candidate = sibling / "file.txt"
            with pytest.raises(PathTraversalError):
                safe_realpath_within(candidate, tmp_path)
        finally:
            sibling.rmdir()


class TestSafeResolveWithin:
    """Tests for safe_resolve_within() (Path variant)."""

    def test_returns_path_instance(self, tmp_path: Path) -> None:
        result = safe_resolve_within(tmp_path / "f.txt", tmp_path)
        assert isinstance(result, Path)

    def test_path_matches_realpath_string(self, tmp_path: Path) -> None:
        candidate = tmp_path / "sub" / "file.txt"
        str_result = safe_realpath_within(candidate, tmp_path)
        path_result = safe_resolve_within(candidate, tmp_path)
        assert str(path_result) == str_result

    def test_rejects_outside(self, tmp_path: Path) -> None:
        with pytest.raises(PathTraversalError):
            safe_resolve_within(tmp_path.parent / "escape", tmp_path)


class TestPathTraversalError:
    """PathTraversalError inherits from ValueError for backwards compat."""

    def test_is_value_error_subclass(self) -> None:
        assert issubclass(PathTraversalError, ValueError)

    def test_caught_by_except_value_error(self, tmp_path: Path) -> None:
        outside = tmp_path.parent / "escape"
        try:
            safe_realpath_within(outside, tmp_path)
        except ValueError as exc:
            assert isinstance(exc, PathTraversalError)
        else:
            pytest.fail("PathTraversalError was not raised")
