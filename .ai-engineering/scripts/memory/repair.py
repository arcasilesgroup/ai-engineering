"""spec-118 T-1.5 -- repair pass for legacy memory/instinct state.

The framework's instinct subsystem accumulated empty `timestamp` fields on disk
in `instinct-observations.ndjson`, defeating the delta filter inside
`_lib/instincts.py::_filter_new_observations`. This module reconstructs the
missing timestamps from the available evidence (file mtime distributed across
line positions when no record-level timestamp survived) and rewrites the file
atomically. It also reports any malformed lines so downstream consumers do not
silently swallow corruption.

Stdlib-only. Safe to run multiple times: a record that already carries a valid
timestamp is left untouched.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

INSTINCT_OBSERVATIONS_REL = Path(".ai-engineering") / "state" / "instinct-observations.ndjson"
REPAIR_BACKUP_SUFFIX = ".repair-backup"


@dataclass(frozen=True)
class RepairReport:
    """Outcome of a repair pass; safe to serialize to audit detail."""

    path: str
    total_lines: int
    backfilled: int
    already_valid: int
    malformed: int
    backup_path: str | None
    duration_ms: int


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _has_valid_timestamp(record: dict) -> bool:
    ts = record.get("timestamp")
    if not isinstance(ts, str) or not ts.strip():
        return False
    cleaned = ts.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(cleaned)
    except ValueError:
        return False
    return True


def _synthesize_timestamps(line_count: int, file_mtime: datetime) -> list[str]:
    """Distribute synthetic timestamps backwards from file mtime.

    Each line is one second apart; line 0 is the oldest. This preserves
    monotonic ordering, which is the only property `_filter_new_observations`
    cares about. Line count must be > 0.
    """
    if line_count <= 0:
        return []
    return [_iso(file_mtime - timedelta(seconds=line_count - 1 - i)) for i in range(line_count)]


def _atomic_write(path: Path, lines: Iterable[str]) -> None:
    """Atomic write with O_NOFOLLOW so a pre-existing symlink at the temp path
    cannot redirect the write. Defense-in-depth: targets are hardcoded under
    `.ai-engineering/state/`, but the function accepts a `--target` override
    that could be exploited on shared hosts."""
    import os

    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    flags |= nofollow
    fd = os.open(str(tmp), flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
    except Exception:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    os.replace(str(tmp), str(path))


def backfill_timestamps(
    project_root: Path,
    *,
    target: Path | None = None,
    write_backup: bool = True,
) -> RepairReport:
    """Backfill empty `timestamp` fields in instinct-observations.ndjson.

    Idempotent: records with valid timestamps are preserved verbatim.
    Malformed JSON lines are dropped from the rewrite and counted in the report
    so the caller can surface them through the audit stream.
    """
    started = datetime.now(tz=UTC)
    path = target or (project_root / INSTINCT_OBSERVATIONS_REL)
    if not path.exists():
        return RepairReport(
            path=str(path),
            total_lines=0,
            backfilled=0,
            already_valid=0,
            malformed=0,
            backup_path=None,
            duration_ms=0,
        )

    raw_lines = path.read_text(encoding="utf-8").splitlines()
    parsed: list[tuple[int, dict]] = []
    malformed = 0
    for idx, raw in enumerate(raw_lines):
        if not raw.strip():
            continue
        try:
            parsed.append((idx, json.loads(raw)))
        except json.JSONDecodeError:
            malformed += 1
            continue

    file_mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    synthetic = _synthesize_timestamps(len(parsed), file_mtime)

    backfilled = 0
    already_valid = 0
    rebuilt: list[str] = []
    for (_, record), ts in zip(parsed, synthetic, strict=True):
        if _has_valid_timestamp(record):
            already_valid += 1
        else:
            record["timestamp"] = ts
            backfilled += 1
        rebuilt.append(json.dumps(record, sort_keys=True, separators=(",", ":")))

    backup_path: Path | None = None
    if write_backup and backfilled > 0:
        backup_path = path.with_suffix(path.suffix + REPAIR_BACKUP_SUFFIX)
        backup_path.write_text("\n".join(raw_lines) + "\n", encoding="utf-8")

    if backfilled > 0:
        _atomic_write(path, rebuilt)

    duration_ms = int((datetime.now(tz=UTC) - started).total_seconds() * 1000)
    return RepairReport(
        path=str(path),
        total_lines=len(parsed) + malformed,
        backfilled=backfilled,
        already_valid=already_valid,
        malformed=malformed,
        backup_path=str(backup_path) if backup_path else None,
        duration_ms=duration_ms,
    )


def _main() -> int:
    """Standalone CLI entry point: `python3 -m memory.repair`.

    Real production access is through `ai-eng memory repair --backfill-timestamps`,
    which routes through `memory/cli.py`. This entry point is for ad-hoc use
    inside the repository (e.g. CI smoke tests).
    """
    project_root = Path.cwd()
    report = backfill_timestamps(project_root)
    json.dump(report.__dict__, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
