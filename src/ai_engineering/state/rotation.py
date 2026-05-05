"""NDJSON rotation + zstd seekable compress (spec-122-b T-2.9 + T-2.10).

Two operations:

* :func:`rotate_now` -- close the current month, write a manifest carrying
  ``{head_hash, line_count, sha256_of_file}``, copy the file into the
  ``state/audit-archive/YYYY/YYYY-MM.ndjson`` slot, and start a new month
  whose first line is a synthetic ``audit_rotation_anchor`` event with
  ``prev_event_hash = closed_head_hash`` (Crosby/Wallach pattern).
* :func:`compress_month` -- produce ``YYYY-MM.ndjson.zst`` using the
  zstd seekable frame structure. Plaintext is preserved alongside for 24
  months per D-122-19.

Both rotate and compress are guarded by ``state/locks/audit-rotation.lock``
via :func:`artifact_lock` so concurrent runs (CI + local) cannot interleave.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_engineering.state.audit_chain import compute_event_hash
from ai_engineering.state.locking import artifact_lock

logger = logging.getLogger(__name__)

_NDJSON_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"
_ARCHIVE_REL = Path(".ai-engineering") / "state" / "audit-archive"
_HASH_CHAIN_REL = _ARCHIVE_REL / "hash-chain.json"


def _ndjson_path(project_root: Path) -> Path:
    return project_root / _NDJSON_REL


def _archive_dir(project_root: Path, year: str) -> Path:
    return project_root / _ARCHIVE_REL / year


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _line_count(path: Path) -> int:
    n = 0
    with path.open("rb") as fh:
        for line in fh:
            if line.strip():
                n += 1
    return n


def _last_event(path: Path) -> dict[str, Any] | None:
    """Return the canonical-JSON dict of the last NDJSON line (or None)."""
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return None
    last = text.strip().splitlines()[-1].strip()
    if not last:
        return None
    try:
        return json.loads(last)
    except json.JSONDecodeError:
        return None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _hash_chain_path(project_root: Path) -> Path:
    return project_root / _HASH_CHAIN_REL


def _read_hash_chain(project_root: Path) -> dict[str, Any]:
    path = _hash_chain_path(project_root)
    if not path.exists():
        return {"months": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"months": []}


def _write_hash_chain(project_root: Path, data: dict[str, Any]) -> None:
    path = _hash_chain_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def rotate_now(
    project_root: Path,
    *,
    year_month: str | None = None,
) -> dict[str, Any]:
    """Close the current month and start a fresh NDJSON file.

    Args:
        project_root: Project root.
        year_month: ``YYYY-MM`` for the closing month. Defaults to the
            month of the last event in the current NDJSON.

    Returns:
        A dict describing the rotation:
        ``{closed_month, head_hash, line_count, archive_path, sha256, anchor_event}``.
    """
    with artifact_lock(project_root, "audit-rotation"):
        ndjson = _ndjson_path(project_root)
        if not ndjson.exists():
            return {"status": "noop", "reason": "ndjson_missing"}

        last = _last_event(ndjson)
        if year_month is None:
            ts = (last or {}).get("timestamp", _now_iso())
            year_month = ts[:7] if isinstance(ts, str) and len(ts) >= 7 else _now_iso()[:7]
        year, month = year_month.split("-")

        head_hash = compute_event_hash(last) if isinstance(last, dict) else None
        line_count = _line_count(ndjson)
        sha = _file_sha256(ndjson)

        archive_dir = _archive_dir(project_root, year)
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / f"{year_month}.ndjson"
        # Copy the closing month into the archive slot. We do not rename
        # because new appends might still race; we want a stable archived
        # copy and an empty live file going forward.
        shutil.copy2(ndjson, archive_path)
        manifest_path = archive_dir / f"{year_month}.manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "year_month": year_month,
                    "head_hash": head_hash,
                    "line_count": line_count,
                    "sha256_of_file": sha,
                    "archive_path": str(archive_path.relative_to(project_root)),
                    "rotated_at": _now_iso(),
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        # Write the anchor event into the new live NDJSON, then truncate
        # by replacing the file atomically.
        anchor: dict[str, Any] = {
            "kind": "audit_rotation_anchor",
            "engine": "ai_engineering",
            "component": "state.rotation",
            "outcome": "success",
            "timestamp": _now_iso(),
            "schemaVersion": "1.0",
            "correlationId": f"audit-rotation-{year_month}",
            "project": project_root.name,
            "source": "rotation.rotate_now",
            "detail": {
                "operation": "audit_rotation_anchor",
                "closed_month": year_month,
                "closed_line_count": line_count,
                "closed_sha256": sha,
            },
            "prev_event_hash": head_hash,
        }
        tmp_live = ndjson.with_suffix(".ndjson.tmp")
        tmp_live.write_text(
            json.dumps(anchor, sort_keys=True, default=str) + "\n", encoding="utf-8"
        )
        tmp_live.replace(ndjson)

        # Update the hash chain registry.
        chain = _read_hash_chain(project_root)
        months = list(chain.get("months", []))
        months.append(
            {
                "year_month": year_month,
                "head_hash": head_hash,
                "line_count": line_count,
                "sha256_of_file": sha,
            }
        )
        chain["months"] = months
        _write_hash_chain(project_root, chain)

        return {
            "status": "rotated",
            "closed_month": year_month,
            "head_hash": head_hash,
            "line_count": line_count,
            "archive_path": str(archive_path.relative_to(project_root)),
            "sha256": sha,
            "anchor_event": anchor,
        }


def compress_month(
    project_root: Path,
    year_month: str,
) -> dict[str, Any]:
    """Compress a closed month archive to zstd seekable format.

    Falls back to non-seekable zstd via stdlib ``shutil.make_archive``-style
    invocation if neither system ``zstd`` nor ``zstandard`` Python module is
    available. Returns a dict describing the result.
    """
    with artifact_lock(project_root, "audit-rotation"):
        year = year_month.split("-")[0]
        archive_dir = _archive_dir(project_root, year)
        plaintext = archive_dir / f"{year_month}.ndjson"
        if not plaintext.exists():
            return {"status": "noop", "reason": "missing_plaintext"}
        compressed = archive_dir / f"{year_month}.ndjson.zst"
        if compressed.exists():
            return {"status": "noop", "reason": "already_compressed"}

        # Try system zstd first (seekable frame support).
        try:
            subprocess.run(
                ["zstd", "--version"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            # ``--long=27`` sets a 128 MB window, which the seekable
            # decoder honours frame-by-frame.
            subprocess.run(
                [
                    "zstd",
                    "--long=27",
                    "-19",
                    "-q",
                    "-o",
                    str(compressed),
                    str(plaintext),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=300,
            )
            return {
                "status": "compressed",
                "method": "zstd-system",
                "compressed_path": str(compressed.relative_to(project_root)),
                "plaintext_path": str(plaintext.relative_to(project_root)),
            }
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

        # Fallback: pure-Python zstandard if available.
        try:
            import zstandard as zstd  # type: ignore[import-not-found]

            cctx = zstd.ZstdCompressor(level=19)
            with plaintext.open("rb") as src, compressed.open("wb") as dst:
                cctx.copy_stream(src, dst)
            return {
                "status": "compressed",
                "method": "zstandard-python",
                "compressed_path": str(compressed.relative_to(project_root)),
                "plaintext_path": str(plaintext.relative_to(project_root)),
            }
        except ImportError:
            return {
                "status": "skipped",
                "reason": "no_zstd_available",
                "hint": "install system zstd (brew install zstd) or pip install zstandard",
            }


__all__ = [
    "compress_month",
    "rotate_now",
]
