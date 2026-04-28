"""Unit tests for ``prereqs.uv._check_uv_in_range`` (spec-101 T-2.5 + T-2.6).

The framework's own Python tool installer routes through ``uv tool install``
(D-101-12), so ``uv`` is a HARD prerequisite. The manifest declares an
acceptable range via ``prereqs.uv.version_range`` (PEP 440 SpecifierSet
syntax, e.g. ``">=0.4.0,<1.0"``). At install-time:

* Below the lower bound -> :class:`PrereqOutOfRange` -> EXIT 81.
* Above the upper bound -> :class:`PrereqOutOfRange` -> EXIT 81.
* In range -> no exception raised.

The tests exercise the ``_check_uv_in_range`` helper directly with a mocked
``_query_uv_version`` seam. The seam also lets the integration tests prove
the EXIT 81 mapping without touching real ``uv``.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.cli_commands._exit_codes import (
    PrereqMissing,
    PrereqOutOfRange,
)

# Canonical range used by the spec-101 manifest template.
_DEFAULT_RANGE: str = ">=0.4.0,<1.0"


# ---------------------------------------------------------------------------
# Lower-bound failures
# ---------------------------------------------------------------------------


class TestUvVersionBelowLowerBound:
    """Versions below the lower bound raise :class:`PrereqOutOfRange`."""

    def test_zero_three_five_below_zero_four_zero_raises(self) -> None:
        from ai_engineering.prereqs import uv as uv_mod

        with (
            patch.object(uv_mod, "_query_uv_version", return_value="0.3.5"),
            pytest.raises(PrereqOutOfRange) as exc_info,
        ):
            uv_mod._check_uv_in_range(_DEFAULT_RANGE)

        # Mismatch message must surface BOTH the version AND the range so
        # the operator sees the actionable context.
        assert "0.3.5" in str(exc_info.value)
        assert _DEFAULT_RANGE in str(exc_info.value)


# ---------------------------------------------------------------------------
# Upper-bound failures
# ---------------------------------------------------------------------------


class TestUvVersionAboveUpperBound:
    """Versions above the upper bound raise :class:`PrereqOutOfRange`."""

    def test_one_five_zero_above_one_zero_raises(self) -> None:
        from ai_engineering.prereqs import uv as uv_mod

        with (
            patch.object(uv_mod, "_query_uv_version", return_value="1.5.0"),
            pytest.raises(PrereqOutOfRange) as exc_info,
        ):
            uv_mod._check_uv_in_range(_DEFAULT_RANGE)

        assert "1.5.0" in str(exc_info.value)
        assert _DEFAULT_RANGE in str(exc_info.value)


# ---------------------------------------------------------------------------
# In-range happy path
# ---------------------------------------------------------------------------


class TestUvVersionInRange:
    """A version inside the range returns silently."""

    def test_zero_five_two_in_range_does_not_raise(self) -> None:
        from ai_engineering.prereqs import uv as uv_mod

        with patch.object(uv_mod, "_query_uv_version", return_value="0.5.2"):
            # Must NOT raise.
            uv_mod._check_uv_in_range(_DEFAULT_RANGE)


# ---------------------------------------------------------------------------
# uv absent surfaces PrereqMissing (subclass distinct from OutOfRange).
# ---------------------------------------------------------------------------


class TestUvAbsentRaisesPrereqMissing:
    """Absent uv must raise the parent :class:`PrereqMissing`, not OutOfRange."""

    def test_query_returns_none_raises_prereq_missing(self) -> None:
        from ai_engineering.prereqs import uv as uv_mod

        with (
            patch.object(uv_mod, "_query_uv_version", return_value=None),
            pytest.raises(PrereqMissing),
        ):
            uv_mod._check_uv_in_range(_DEFAULT_RANGE)


# ---------------------------------------------------------------------------
# Manifest loader returns the declared range
# ---------------------------------------------------------------------------


class TestLoadUvVersionRangeFromManifest:
    """``_load_uv_version_range`` reads the spec-101 prereqs.uv block."""

    def test_manifest_with_declared_range_returns_specifier(
        self,
        tmp_path: Path,
    ) -> None:
        from ai_engineering.prereqs import uv as uv_mod

        ai_dir = tmp_path / ".ai-engineering"
        ai_dir.mkdir()
        (ai_dir / "manifest.yml").write_text(
            "prereqs:\n  uv:\n    version_range: '>=0.4.0,<1.0'\n",
            encoding="utf-8",
        )
        assert uv_mod._load_uv_version_range(tmp_path) == _DEFAULT_RANGE

    def test_manifest_without_prereqs_block_returns_none(
        self,
        tmp_path: Path,
    ) -> None:
        from ai_engineering.prereqs import uv as uv_mod

        ai_dir = tmp_path / ".ai-engineering"
        ai_dir.mkdir()
        (ai_dir / "manifest.yml").write_text("name: foo\n", encoding="utf-8")
        assert uv_mod._load_uv_version_range(tmp_path) is None
