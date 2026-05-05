"""Tests for zstd seekable compress of closed NDJSON months (spec-123 T-3.7).

The rotation module ships :func:`compress_month` which produces a
``.ndjson.zst`` artifact for a closed month. Spec-123 D-123-25 mandates
that the closed-month archive layout includes a canonical
``state/archive/ndjson/YYYY-MM/`` slot, that the original plaintext is
removed after a successful compress (storage savings + tamper-evidence
via the seekable hash chain), and that ``verify-chain`` continues to
work against the archive.

These tests exercise the new public surface
:func:`compress_closed_month` which:

* Reads the plaintext NDJSON the rotation module rolled up under
  ``state/audit-archive/<year>/<year-month>.ndjson``.
* Writes a seekable ``.ndjson.zst`` artifact under
  ``state/archive/ndjson/<year-month>/<year-month>.ndjson.zst``.
* Removes the plaintext after a successful compress.
* Surfaces a status dict for the audit CLI.
* Skips with a soft "no zstd" status when neither system zstd nor the
  Python ``zstandard`` package is available -- never fails the audit.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ai_engineering.state.rotation import (
    compress_closed_month,
    verify_archive_chain,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _has_zstd() -> bool:
    """Return True when either system zstd or the Python module is usable."""
    try:
        subprocess.run(
            ["zstd", "--version"],
            check=True,
            capture_output=True,
            timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    try:
        import zstandard  # type: ignore[import-not-found]  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Tmp project root with the audit-archive structure ready."""
    (tmp_path / ".ai-engineering" / "state" / "audit-archive").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _stage_plaintext_month(project_root: Path, year_month: str, lines: int = 50) -> Path:
    """Drop a synthetic ``YYYY-MM.ndjson`` under ``state/audit-archive/<year>/``."""
    year = year_month.split("-")[0]
    archive_dir = project_root / ".ai-engineering" / "state" / "audit-archive" / year
    archive_dir.mkdir(parents=True, exist_ok=True)
    plaintext = archive_dir / f"{year_month}.ndjson"
    body = "\n".join(
        '{"timestamp":"2025-12-01T00:00:00Z","engine":"claude_code",'
        f'"kind":"x","component":"c","outcome":"success","seq":{i}'
        "}"
        for i in range(lines)
    )
    plaintext.write_text(body + "\n", encoding="utf-8")
    return plaintext


# ---------------------------------------------------------------------------
# T-3.7 — RED + GREEN: compress_closed_month
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _has_zstd(), reason="zstd binary or python module not available")
class TestCompressClosedMonth:
    """``compress_closed_month`` produces a seekable .zst and removes plaintext."""

    def test_zst_artifact_lands_under_archive_ndjson_yyyy_mm(self, project_root: Path) -> None:
        """The compressed file lives at archive/ndjson/<year-month>/<file>."""
        plaintext = _stage_plaintext_month(project_root, "2025-12")
        plaintext_size = plaintext.stat().st_size

        result = compress_closed_month(project_root, "2025-12")

        assert result["status"] == "compressed", result
        compressed = (
            project_root
            / ".ai-engineering"
            / "state"
            / "archive"
            / "ndjson"
            / "2025-12"
            / "2025-12.ndjson.zst"
        )
        assert compressed.exists(), f"compressed file missing at {compressed}"
        assert compressed.stat().st_size > 0
        assert compressed.stat().st_size < plaintext_size  # actually compressed

    def test_plaintext_removed_after_compress(self, project_root: Path) -> None:
        """The plaintext file is removed once the .zst lands successfully."""
        plaintext = _stage_plaintext_month(project_root, "2025-11")
        assert plaintext.exists()

        compress_closed_month(project_root, "2025-11")

        assert not plaintext.exists(), "plaintext was not removed after compress"

    def test_compress_idempotent(self, project_root: Path) -> None:
        """Re-running compress on an already-compressed month is a no-op."""
        _stage_plaintext_month(project_root, "2025-10")

        first = compress_closed_month(project_root, "2025-10")
        second = compress_closed_month(project_root, "2025-10")

        assert first["status"] == "compressed"
        assert second["status"] == "noop"
        assert second.get("reason") in {"already_compressed", "missing_plaintext"}

    def test_verify_chain_runs_against_archive(self, project_root: Path) -> None:
        """``verify_archive_chain`` accepts the compressed archive."""
        _stage_plaintext_month(project_root, "2025-09")
        compress_closed_month(project_root, "2025-09")

        verdict = verify_archive_chain(project_root, "2025-09")

        assert verdict["ok"] is True, verdict
        # Spot-check that the line count survives compression.
        assert verdict["entries_checked"] == 50

    def test_missing_plaintext_returns_noop(self, project_root: Path) -> None:
        """Compressing a month that was never staged returns a noop status."""
        result = compress_closed_month(project_root, "2025-08")

        assert result["status"] == "noop"
        assert result.get("reason") == "missing_plaintext"


class TestCompressFallback:
    """When zstd is absent, the call must surface a soft skipped status."""

    def test_skipped_when_no_zstd(
        self, project_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Force-disable zstd discovery; result is ``status='skipped'``."""

        def _no_zstd_run(*args, **kwargs):  # type: ignore[no-untyped-def]
            raise FileNotFoundError("simulated: no zstd binary")

        monkeypatch.setattr(subprocess, "run", _no_zstd_run)
        # Hide the zstandard module from the import system inside compress_closed_month.
        import importlib
        import sys

        for mod_name in [
            name
            for name in list(sys.modules)
            if name == "zstandard" or name.startswith("zstandard.")
        ]:
            del sys.modules[mod_name]

        original_find = importlib.util.find_spec

        def _no_zstandard(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
            if name == "zstandard":
                return None
            return original_find(name, *args, **kwargs)

        monkeypatch.setattr(importlib.util, "find_spec", _no_zstandard)
        # Block the import via meta_path so that ``import zstandard`` raises ImportError.
        block = _BlockZstdImporter()
        monkeypatch.setattr(sys, "meta_path", [block, *sys.meta_path])

        _stage_plaintext_month(project_root, "2024-12")
        result = compress_closed_month(project_root, "2024-12")

        assert result["status"] == "skipped", result


class _BlockZstdImporter:
    """meta_path importer that raises ImportError for zstandard."""

    def find_spec(self, fullname: str, path=None, target=None):  # type: ignore[no-untyped-def]
        if fullname == "zstandard" or fullname.startswith("zstandard."):
            raise ImportError("zstandard blocked for test")
        return None
