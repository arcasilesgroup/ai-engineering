#!/usr/bin/env python3
"""Spec lifecycle automation (sub-spec sub-001 / umbrella spec-127).

Hexagonal layout in one file (~250 LOC):

- **Domain** (pure, zero I/O): ``LifecycleState`` enum, ``SpecRecord``
  dataclass, ``LEGAL_TRANSITIONS`` table, ``transition`` validator.
- **Infrastructure** (filesystem): ``_load_state`` / ``_write_state``
  (atomic via tempfile + ``os.replace`` under ``artifact_lock``);
  ``_append_event`` (NDJSON); ``_render_history`` (7-col markdown
  projection that reads any 5/6/7-col legacy header and preserves
  free-form retro sections verbatim).
- **Application** (CLI): ``start_new``, ``mark_shipped``, ``archive``,
  ``sweep``, ``status``, ``migrate_history`` — each composes one domain
  transition + one infra write under one lock. Every atomic op
  completes <500ms (no LLM, stdlib only).

Idempotency is enforced at the application layer: re-issuing the same
verb on a record already in the target state is a no-op (no FSM raise,
no duplicate history row, no extra NDJSON event for the duplicate
write).

Stdlib only — no third-party deps. Reuses ``artifact_lock`` from
``.ai-engineering/scripts/hooks/_lib/locking.py``.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path

# ---------------------------------------------------------------------------
# Locking primitive — wired in via sys.path so this script can run as a
# stand-alone CLI from any cwd that contains ``.ai-engineering/``.
# ---------------------------------------------------------------------------


def _load_artifact_lock():
    """Resolve ``artifact_lock`` from the hooks `_lib`, injecting sys.path on demand.

    The script can run as a stand-alone CLI from any cwd, so the hooks
    library is wired in lazily rather than at import time. Wrapping the
    sys.path insert + import inside a function keeps the module-level
    import block ruff-clean (no E402).
    """
    repo_root = Path(__file__).resolve().parents[2]
    hooks_lib = repo_root / ".ai-engineering" / "scripts" / "hooks"
    if str(hooks_lib) not in sys.path:
        sys.path.insert(0, str(hooks_lib))
    from _lib.locking import artifact_lock as _lock

    return _lock


artifact_lock = _load_artifact_lock()

# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------


class LifecycleState(Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    SHIPPED = "shipped"
    ABANDONED = "abandoned"
    ARCHIVED = "archived"


# Closed transition table: state -> set of legal next states.
LEGAL_TRANSITIONS: dict[LifecycleState, frozenset[LifecycleState]] = {
    LifecycleState.DRAFT: frozenset({LifecycleState.APPROVED, LifecycleState.ABANDONED}),
    LifecycleState.APPROVED: frozenset({LifecycleState.IN_PROGRESS, LifecycleState.ABANDONED}),
    LifecycleState.IN_PROGRESS: frozenset({LifecycleState.SHIPPED, LifecycleState.ABANDONED}),
    LifecycleState.SHIPPED: frozenset({LifecycleState.ARCHIVED}),
    LifecycleState.ABANDONED: frozenset({LifecycleState.ARCHIVED}),
    LifecycleState.ARCHIVED: frozenset(),  # terminal
}


def transition(current: LifecycleState, target: LifecycleState) -> LifecycleState:
    """Pure FSM validator — raises on illegal moves."""
    if target not in LEGAL_TRANSITIONS[current]:
        raise ValueError(f"illegal lifecycle transition: {current.name} -> {target.name}")
    return target


@dataclass
class SpecRecord:
    spec_id: str
    slug: str
    title: str
    state: LifecycleState
    created: str  # ISO-8601 UTC
    shipped: str | None = None
    pr: str | None = None
    branch: str | None = None
    extra: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        d = asdict(self)
        d["state"] = self.state.value
        return d

    @classmethod
    def from_json(cls, data: dict) -> SpecRecord:
        return cls(
            spec_id=data["spec_id"],
            slug=data["slug"],
            title=data["title"],
            state=LifecycleState(data["state"]),
            created=data["created"],
            shipped=data.get("shipped"),
            pr=data.get("pr"),
            branch=data.get("branch"),
            extra=data.get("extra", {}),
        )


# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------


def _specs_dir(project_root: Path) -> Path:
    return project_root / ".ai-engineering" / "state" / "specs"


def _sidecar_path(project_root: Path, spec_id: str) -> Path:
    return _specs_dir(project_root) / f"{spec_id}.json"


def _history_path(project_root: Path) -> Path:
    return project_root / ".ai-engineering" / "specs" / "_history.md"


def _events_path(project_root: Path) -> Path:
    return project_root / ".ai-engineering" / "state" / "framework-events.ndjson"


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(target: Path, payload: str) -> None:
    """Atomic write via tempfile in the same directory + ``os.replace``."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp_name, str(target))
    except Exception:
        # Tempfile cleanup on failure; original target untouched.
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def _load_state(project_root: Path, spec_id: str) -> SpecRecord:
    sidecar = _sidecar_path(project_root, spec_id)
    if not sidecar.exists():
        raise FileNotFoundError(f"spec sidecar missing: {spec_id}")
    return SpecRecord.from_json(json.loads(sidecar.read_text(encoding="utf-8")))


def _write_state(project_root: Path, record: SpecRecord) -> None:
    """Atomic JSON sidecar write under the shared specs lock."""
    with artifact_lock(project_root, "specs"):
        _atomic_write(
            _sidecar_path(project_root, record.spec_id),
            json.dumps(record.to_json(), indent=2, sort_keys=True),
        )


def _find_by_slug(project_root: Path, slug: str) -> SpecRecord | None:
    d = _specs_dir(project_root)
    if not d.exists():
        return None
    for path in d.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("slug") == slug:
            return SpecRecord.from_json(data)
    return None


def _append_event(project_root: Path, operation: str, detail: dict) -> None:
    """Append one ``framework_operation`` NDJSON event under the events lock."""
    payload = {
        "id": str(uuid.uuid4()),
        "timestamp": _utcnow_iso(),
        "kind": "framework_operation",
        "outcome": "success",
        "detail": {"operation": operation, **detail},
    }
    line = json.dumps(payload, sort_keys=True) + "\n"
    target = _events_path(project_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with (
        artifact_lock(project_root, "framework-events"),
        target.open("a", encoding="utf-8") as f,
    ):
        f.write(line)


# --- _history.md projection ------------------------------------------------

_HISTORY_HEADER = (
    "| ID | Title | Status | Created | Shipped | PR | Branch |\n"
    "|----|-------|--------|---------|---------|----|--------|\n"
)
_PREAMBLE = "# Spec History\n\nCompleted specs. Details in git history.\n\n"


def _split_history(text: str) -> tuple[list[str], str]:
    """Return (table_data_rows, freeform_tail).

    The free-form tail starts at the first blank line *after* the table
    block (i.e. once we leave consecutive ``|``-prefixed rows). Anything
    before the first ``|`` row is the preamble and is regenerated.
    """
    lines = text.splitlines()
    rows: list[str] = []
    tail_start = len(lines)
    in_table = False
    for i, line in enumerate(lines):
        if line.startswith("|"):
            in_table = True
            rows.append(line)
            continue
        if in_table:
            tail_start = i
            break
    tail = "\n".join(lines[tail_start:]).lstrip("\n")
    return rows, tail


def _normalize_row(row: str) -> list[str]:
    """Strip the leading/trailing ``|`` and split into cell strings."""
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    return cells


def _migrate_rows(rows: list[str]) -> list[str]:
    """Take any 5/6/7-col data rows and project to 7 columns.

    Column mappings (legacy → canonical):

    - 5-col ``ID, Title, Status, Created, Branch`` → fill empty Shipped + PR.
    - 6-col ``ID, Title, Status, Created, Shipped, Branch`` → fill empty PR.
    - 7-col already canonical → preserved verbatim.
    """
    if len(rows) < 2:
        return []
    # Drop header + separator rows; everything else is data.
    data: list[list[str]] = []
    for row in rows[2:]:
        if not row.strip().startswith("|"):
            continue
        cells = _normalize_row(row)
        if len(cells) == 5:
            spec_id, title, status, created, branch = cells
            data.append([spec_id, title, status, created, "—", "—", branch])
        elif len(cells) == 6:
            spec_id, title, status, created, shipped, branch = cells
            data.append([spec_id, title, status, created, shipped, "—", branch])
        elif len(cells) == 7:
            data.append(cells)
        else:
            # Skip malformed rows rather than crash on unknown legacy shapes.
            continue
    return ["| " + " | ".join(cells) + " |" for cells in data]


def _render_history(project_root: Path, append_row: list[str] | None = None) -> None:
    """Re-render ``_history.md`` with the canonical 7-col header.

    If ``append_row`` is supplied (7-cell list), it is appended *iff* an
    identical row is not already present. This keeps ``mark_shipped``
    idempotent: re-issuing the verb does not duplicate history.
    """
    history = _history_path(project_root)
    history.parent.mkdir(parents=True, exist_ok=True)
    if history.exists():
        rows, tail = _split_history(history.read_text(encoding="utf-8"))
    else:
        rows, tail = [], ""
    data_rows = _migrate_rows(rows)
    if append_row:
        candidate = "| " + " | ".join(append_row) + " |"
        if candidate not in data_rows:
            data_rows.append(candidate)
    body = _PREAMBLE + _HISTORY_HEADER + "\n".join(data_rows) + "\n"
    if tail.strip():
        body += "\n" + tail.rstrip() + "\n"
    with artifact_lock(project_root, "specs-history"):
        _atomic_write(history, body)


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


def start_new(slug: str, title: str, project_root: Path) -> SpecRecord:
    """Create (or return existing) DRAFT record for ``slug``."""
    existing = _find_by_slug(project_root, slug)
    if existing is not None:
        return existing  # idempotent
    record = SpecRecord(
        spec_id=slug,
        slug=slug,
        title=title,
        state=LifecycleState.DRAFT,
        created=_utcnow_iso(),
    )
    _write_state(project_root, record)
    _append_event(
        project_root,
        "spec_started",
        {"spec_id": record.spec_id, "title": title},
    )
    return record


def mark_shipped(spec_id: str, pr: str, branch: str, project_root: Path) -> SpecRecord:
    """Walk DRAFT→APPROVED→IN_PROGRESS→SHIPPED in one call (idempotent)."""
    record = _load_state(project_root, spec_id)
    if record.state is LifecycleState.SHIPPED:
        # Idempotent: refresh PR/branch metadata if missing, but no event.
        if record.pr != pr or record.branch != branch:
            record.pr = pr
            record.branch = branch
            _write_state(project_root, record)
        return record
    # Walk legal chain. Any illegal start state (ARCHIVED, ABANDONED) raises.
    chain = [
        LifecycleState.APPROVED,
        LifecycleState.IN_PROGRESS,
        LifecycleState.SHIPPED,
    ]
    for target in chain:
        if record.state is target:
            continue
        record.state = transition(record.state, target)
    record.pr = pr
    record.branch = branch
    record.shipped = _utcnow_iso()
    _write_state(project_root, record)
    _render_history(
        project_root,
        append_row=[
            record.spec_id,
            record.title,
            record.state.value,
            record.created.split("T")[0],
            record.shipped.split("T")[0],
            pr,
            branch,
        ],
    )
    _append_event(
        project_root,
        "spec_shipped",
        {"spec_id": record.spec_id, "pr": pr, "branch": branch},
    )
    return record


def archive(spec_id: str, project_root: Path) -> SpecRecord:
    """Move SHIPPED|ABANDONED → ARCHIVED (idempotent)."""
    record = _load_state(project_root, spec_id)
    if record.state is LifecycleState.ARCHIVED:
        return record  # idempotent
    record.state = transition(record.state, LifecycleState.ARCHIVED)
    _write_state(project_root, record)
    _append_event(project_root, "spec_archived", {"spec_id": record.spec_id})
    return record


def sweep(project_root: Path) -> dict:
    """Reap stale DRAFTs (>14d) → ABANDONED. Idempotent re-runs."""
    summary = {"abandoned": 0, "archived": 0}
    d = _specs_dir(project_root)
    if not d.exists():
        _append_event(project_root, "spec_sweep", summary)
        return summary
    cutoff = datetime.now(UTC) - timedelta(days=14)
    for path in sorted(d.glob("*.json")):
        try:
            record = SpecRecord.from_json(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
        if record.state is LifecycleState.DRAFT:
            try:
                created = datetime.fromisoformat(record.created)
            except ValueError:
                continue
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            if created < cutoff:
                record.state = transition(record.state, LifecycleState.ABANDONED)
                _write_state(project_root, record)
                summary["abandoned"] += 1
    _append_event(project_root, "spec_sweep", summary)
    return summary


def status(spec_id: str, project_root: Path) -> SpecRecord:
    """Read-only status query."""
    return _load_state(project_root, spec_id)


def migrate_history(project_root: Path) -> None:
    """One-shot migration: legacy 5/6-col `_history.md` → 7-col canonical."""
    _render_history(project_root)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="spec_lifecycle", description=__doc__)
    p.add_argument(
        "--project-root",
        default=str(Path.cwd()),
        help="Repository root (default: cwd)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    def _common(parser: argparse.ArgumentParser) -> None:
        # Mirror --project-root on every subparser so callers can place it
        # either before or after the subcommand. Stays optional; default
        # cascades from the top-level parser.
        parser.add_argument(
            "--project-root",
            default=None,
            help=argparse.SUPPRESS,
        )

    sn = sub.add_parser("start_new", help="Create DRAFT spec record")
    sn.add_argument("slug")
    sn.add_argument("title")
    _common(sn)
    ms = sub.add_parser("mark_shipped", help="Mark spec SHIPPED post-merge")
    ms.add_argument("spec_id")
    ms.add_argument("pr")
    ms.add_argument("branch")
    _common(ms)
    ar = sub.add_parser("archive", help="Move SHIPPED|ABANDONED → ARCHIVED")
    ar.add_argument("spec_id")
    _common(ar)
    sw = sub.add_parser("sweep", help="Reap stale DRAFT > 14d → ABANDONED")
    _common(sw)
    st = sub.add_parser("status", help="Read record state")
    st.add_argument("spec_id")
    _common(st)
    mh = sub.add_parser("migrate-history", help="One-shot legacy history migration")
    _common(mh)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    # Subparsers may override the global default (last writer wins under argparse).
    raw_root = args.project_root if args.project_root else str(Path.cwd())
    project_root = Path(raw_root).resolve()
    t0 = time.monotonic()
    try:
        if args.cmd == "start_new":
            record = start_new(args.slug, args.title, project_root)
            print(json.dumps(record.to_json(), indent=2))
        elif args.cmd == "mark_shipped":
            record = mark_shipped(args.spec_id, args.pr, args.branch, project_root)
            print(json.dumps(record.to_json(), indent=2))
        elif args.cmd == "archive":
            record = archive(args.spec_id, project_root)
            print(json.dumps(record.to_json(), indent=2))
        elif args.cmd == "sweep":
            print(json.dumps(sweep(project_root), indent=2))
        elif args.cmd == "status":
            record = status(args.spec_id, project_root)
            print(json.dumps(record.to_json(), indent=2))
        elif args.cmd == "migrate-history":
            migrate_history(project_root)
            print("migrated _history.md to 7-col canonical layout")
        else:
            return 2
    except (ValueError, FileNotFoundError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        elapsed = time.monotonic() - t0
        if elapsed >= 0.5:
            print(f"warning: op took {elapsed:.3f}s (>500ms budget)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
