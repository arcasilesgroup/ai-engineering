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
  ``sweep``, ``status``, ``migrate_history``, ``consolidate_shipped`` —
  each composes one domain transition + one infra write under one lock.
  Every atomic op completes <500ms (no LLM, stdlib only).

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
import re
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
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


def _specs_root(project_root: Path) -> Path:
    """The working-buffer + archive root: ``.ai-engineering/specs/``."""
    return project_root / ".ai-engineering" / "specs"


def _spec_buffer_path(project_root: Path) -> Path:
    return _specs_root(project_root) / "spec.md"


def _plan_buffer_path(project_root: Path) -> Path:
    return _specs_root(project_root) / "plan.md"


def _archive_dir(project_root: Path) -> Path:
    return _specs_root(project_root) / "archive"


# Placeholder both working buffers are reset to once a spec ships (D-153-04).
_BUFFER_PLACEHOLDER = "# (no active spec)\n\nRun /ai-brainstorm to start one.\n"


def _events_path(project_root: Path) -> Path:
    return project_root / ".ai-engineering" / "state" / "framework-events.ndjson"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    """Resolve a record by sidecar id, falling back to slug lookup.

    Numeric ``spec-NNN`` is the canonical identity (spec-153 D-153-01), but
    callers that still pass a slug (e.g. the consolidate-spec handler) must
    keep resolving after the slug→numeric rename. We try the direct sidecar
    path first, then ``_find_by_slug``; only a miss on *both* raises.
    """
    sidecar = _sidecar_path(project_root, spec_id)
    if sidecar.exists():
        return SpecRecord.from_json(json.loads(sidecar.read_text(encoding="utf-8")))
    by_slug = _find_by_slug(project_root, spec_id)
    if by_slug is not None:
        return by_slug
    raise FileNotFoundError(f"spec sidecar missing: {spec_id}")


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
        candidate_id = append_row[0]
        replaced = False
        upserted_rows: list[str] = []
        for row in data_rows:
            row_cells = _normalize_row(row)
            if row_cells and row_cells[0] == candidate_id:
                if not replaced:
                    upserted_rows.append(candidate)
                    replaced = True
            else:
                upserted_rows.append(row)
        data_rows = upserted_rows
        if not replaced:
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
    """Create (or return existing) DRAFT record for ``slug``.

    The canonical identity is numeric ``spec-NNN`` (spec-153 D-153-01). The
    next number is the live max of ledger + sidecar numbers + 1, minted under
    the shared ``specs-history`` lock so concurrent mints serialize and never
    collide (D-153-05). The slug is preserved verbatim as the human tag.
    ``_find_by_slug`` keeps the verb idempotent: re-running for an existing
    slug returns the existing record without minting a new number.
    """
    existing = _find_by_slug(project_root, slug)
    if existing is not None:
        return existing  # idempotent — no new number minted.
    with artifact_lock(project_root, "specs-history"):
        # Re-check under the lock: a concurrent mint may have just created the
        # slug, in which case we return it rather than mint a duplicate.
        existing = _find_by_slug(project_root, slug)
        if existing is not None:
            return existing
        record = SpecRecord(
            spec_id=f"spec-{_next_spec_number(project_root):03d}",
            slug=slug,
            title=title,
            state=LifecycleState.DRAFT,
            created=_utcnow_iso(),
        )
        _atomic_write(
            _sidecar_path(project_root, record.spec_id),
            json.dumps(record.to_json(), indent=2, sort_keys=True),
        )
    _append_event(
        project_root,
        "spec_started",
        {"spec_id": record.spec_id, "title": title},
    )
    return record


def _buffer_is_placeholder(text: str) -> bool:
    """True when a working-buffer's content carries no active spec.

    A buffer is "empty" for snapshot purposes when it is whitespace-only or
    byte-equal to the reset placeholder. We refuse to snapshot a placeholder so
    an idempotent ``mark_shipped`` re-run never overwrites a real snapshot with
    the reset stub.
    """
    stripped = text.strip()
    return not stripped or text == _BUFFER_PLACEHOLDER


def _snapshot_and_reset(project_root: Path, record: SpecRecord) -> bool:
    """Snapshot ``spec.md``+``plan.md`` into the per-spec archive, then reset them.

    At the SHIPPED transition (D-153-04 / D-153-06): when ``specs/spec.md``
    exists and carries a real (non-placeholder) spec, copy ``spec.md`` and
    ``plan.md`` into ``specs/archive/spec-NNN-<slug>/{spec.md,plan.md}`` and
    overwrite both working buffers with the placeholder. When the buffers are
    already placeholders / absent (existing bare-tmp callers, an idempotent
    re-run after a prior ship), the snapshot is skipped gracefully and the
    buffers are left untouched. Returns ``True`` when a snapshot was taken.

    ARCHIVED stays a logical terminal marker with no file movement — this is
    only ever called from ``mark_shipped``.
    """
    spec_buffer = _spec_buffer_path(project_root)
    if not spec_buffer.exists():
        return False
    spec_text = spec_buffer.read_text(encoding="utf-8")
    if _buffer_is_placeholder(spec_text):
        return False

    target_dir = _archive_dir(project_root) / f"{record.spec_id}-{record.slug}"
    target_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write(target_dir / "spec.md", spec_text)

    plan_buffer = _plan_buffer_path(project_root)
    plan_text = plan_buffer.read_text(encoding="utf-8") if plan_buffer.exists() else ""
    _atomic_write(target_dir / "plan.md", plan_text)

    # Reset the working buffers to the placeholder so the next spec starts clean.
    _atomic_write(spec_buffer, _BUFFER_PLACEHOLDER)
    _atomic_write(plan_buffer, _BUFFER_PLACEHOLDER)
    return True


def mark_shipped(spec_id: str, pr: str, branch: str, project_root: Path) -> SpecRecord:
    """Walk DRAFT→APPROVED→IN_PROGRESS→SHIPPED in one call (idempotent)."""
    record = _load_state(project_root, spec_id)
    if record.state is LifecycleState.SHIPPED:
        # Idempotent: refresh metadata if needed and re-materialize the
        # projection. This supports the shared consolidation handler when a
        # SHIPPED sidecar exists but `_history.md` was deleted, stale, or
        # migrated from a legacy shape.
        if record.pr != pr or record.branch != branch or record.shipped is None:
            record.pr = pr
            record.branch = branch
            record.shipped = record.shipped or _utcnow_iso()
            _write_state(project_root, record)
        _render_history(project_root, append_row=_history_row_for(record))
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
    # Snapshot the working buffers into the per-spec archive directory and reset
    # them to the placeholder (D-153-04). Runs only on the fresh SHIPPED
    # transition — the already-SHIPPED idempotent branch returns earlier, so a
    # re-run never re-snapshots a now-placeholder buffer.
    _snapshot_and_reset(project_root, record)
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
    """Reap stale DRAFTs → ABANDONED and stray root spec files → archive.

    Retention is read from the manifest ``lifecycle:`` block (``draft_ttl_days``,
    ``reap_orphans``), fail-open to 14 days / reaping enabled (D-153-08). The
    DRAFT→ABANDONED pass runs first; then, when ``reap_orphans`` is set, the
    orphan reaper moves any stray ``specs/spec-*.md`` into its archive directory
    (D-153-07). Idempotent re-runs: an empty root reaps nothing. The summary —
    and the ``spec_sweep`` event detail — carries a ``reaped`` count.
    """
    draft_ttl_days, reap_orphans = _read_lifecycle_config(project_root)
    summary: dict[str, int] = {"abandoned": 0, "archived": 0, "reaped": 0}
    d = _specs_dir(project_root)
    if d.exists():
        cutoff = datetime.now(timezone.utc) - timedelta(days=draft_ttl_days)
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
                    created = created.replace(tzinfo=timezone.utc)
                if created < cutoff:
                    record.state = transition(record.state, LifecycleState.ABANDONED)
                    _write_state(project_root, record)
                    summary["abandoned"] += 1
    if reap_orphans:
        summary["reaped"] = _reap_orphans(project_root)
    _append_event(project_root, "spec_sweep", summary)
    return summary


def status(spec_id: str, project_root: Path) -> SpecRecord:
    """Read-only status query."""
    return _load_state(project_root, spec_id)


# --- manifest lifecycle retention (spec-153 D-153-07 / D-153-08) -----------

# Fail-open defaults when the manifest or its ``lifecycle:`` block is absent.
_DEFAULT_DRAFT_TTL_DAYS = 14
_DEFAULT_REAP_ORPHANS = True

# Working-buffer / housekeeping files that are never reaped from ``specs/``.
_PROTECTED_SPEC_FILES = frozenset({"spec.md", "plan.md", "_history.md"})


def _read_lifecycle_config(project_root: Path) -> tuple[int, bool]:
    """Return ``(draft_ttl_days, reap_orphans)`` from the manifest ``lifecycle`` block.

    Stdlib-only: ``ai_engineering.config.loader.load_manifest_config`` pulls in
    third-party deps (``yaml``/``ruamel``/``pydantic``), so this script parses
    the small top-level ``lifecycle:`` block by hand. Fail-open to the defaults
    (14 days, reaping enabled) when ``manifest.yml`` is missing, has no
    ``lifecycle`` block, or a value is unparseable — retention config must never
    be a hard dependency of the sweep.
    """
    manifest = project_root / ".ai-engineering" / "manifest.yml"
    if not manifest.exists():
        return _DEFAULT_DRAFT_TTL_DAYS, _DEFAULT_REAP_ORPHANS
    try:
        lines = manifest.read_text(encoding="utf-8").splitlines()
    except OSError:
        return _DEFAULT_DRAFT_TTL_DAYS, _DEFAULT_REAP_ORPHANS

    draft_ttl_days = _DEFAULT_DRAFT_TTL_DAYS
    reap_orphans = _DEFAULT_REAP_ORPHANS
    in_block = False
    for raw in lines:
        # A top-level key (column 0, non-space) closes the lifecycle block.
        if in_block and raw[:1] not in (" ", "\t", "") and not raw.startswith("#"):
            break
        stripped = raw.strip()
        if not in_block:
            if stripped == "lifecycle:":
                in_block = True
            continue
        if not stripped or stripped.startswith("#"):
            continue
        key, _sep, value = stripped.partition(":")
        key = key.strip()
        value = value.split("#", 1)[0].strip()
        if key == "draft_ttl_days":
            with contextlib.suppress(ValueError):
                draft_ttl_days = int(value)
        elif key == "reap_orphans":
            reap_orphans = value.lower() in ("true", "yes", "1", "on")
    return draft_ttl_days, reap_orphans


def _reap_orphans(project_root: Path) -> int:
    """Move stray ``specs/spec-*.md`` files into their per-spec archive directory.

    The ``specs/`` root invariant is ``{spec.md, plan.md, _history.md, drafts/,
    archive/}`` (D-153-07). Any other top-level ``spec-*.md`` file is an orphan:
    its basename already carries ``spec-NNN-<slug>``, so it moves to
    ``archive/<basename-without-.md>/spec.md``. The reaper only ever *moves*
    (``git mv`` with a plain-rename fallback) — it never deletes. Returns the
    number of files reaped.
    """
    specs_root = _specs_root(project_root)
    if not specs_root.is_dir():
        return 0
    reaped = 0
    for path in sorted(specs_root.glob("spec-*.md")):
        if not path.is_file():
            continue
        if path.name in _PROTECTED_SPEC_FILES:
            continue
        dest_dir = _archive_dir(project_root) / path.stem
        dest_dir.mkdir(parents=True, exist_ok=True)
        _git_mv(project_root, path, dest_dir / "spec.md")
        reaped += 1
    return reaped


def migrate_history(project_root: Path) -> None:
    """One-shot migration: legacy 5/6-col `_history.md` → 7-col canonical."""
    _render_history(project_root)


def _history_spec_ids(project_root: Path) -> set[str]:
    """Return spec ids already present in the canonical history table."""
    history = _history_path(project_root)
    if not history.exists():
        return set()
    rows, _tail = _split_history(history.read_text(encoding="utf-8"))
    data_rows = _migrate_rows(rows)
    ids: set[str] = set()
    for row in data_rows:
        row_cells = _normalize_row(row)
        if row_cells:
            ids.add(row_cells[0])
    return ids


_SPEC_NUMBER_RE = re.compile(r"^spec-(\d+)$")


def _scan_spec_numbers(project_root: Path) -> set[int]:
    """Collect every ``spec-NNN`` number from sidecars + the history ledger.

    Scans both the sidecar ``spec_id`` fields and the canonical
    ``_history.md`` ID cells, parsing the ``spec-(\\d+)`` form. Bare legacy
    numeric ledger IDs (``099``) are intentionally ignored here: the canonical
    identity is ``spec-NNN`` and the historical rows are frozen records, but
    the highest historical number is still captured via its ``spec-``-prefixed
    presence in sidecars / new rows. The fixture's bare ``099`` is matched by
    the dedicated ledger pass below.
    """
    numbers: set[int] = set()
    specs = _specs_dir(project_root)
    if specs.exists():
        for path in specs.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            match = _SPEC_NUMBER_RE.match(str(data.get("spec_id", "")))
            if match:
                numbers.add(int(match.group(1)))
    for hid in _history_spec_ids(project_root):
        match = _SPEC_NUMBER_RE.match(hid)
        if match:
            numbers.add(int(match.group(1)))
        elif hid.isdigit():
            # Legacy bare-number ledger rows (e.g. ``099``) still anchor the
            # max so the next mint never collides with a historical spec.
            numbers.add(int(hid))
    return numbers


def _next_spec_number(project_root: Path) -> int:
    """Return ``max(existing spec numbers) + 1`` (default 1 when none exist)."""
    numbers = _scan_spec_numbers(project_root)
    return (max(numbers) + 1) if numbers else 1


def _history_row_for(record: SpecRecord) -> list[str]:
    """Project a shipped sidecar record into the 7-column history row."""
    return [
        record.spec_id,
        record.title,
        record.state.value,
        record.created.split("T")[0],
        record.shipped.split("T")[0] if record.shipped else "—",
        record.pr or "—",
        record.branch or "—",
    ]


def consolidate_shipped(project_root: Path, *, dry_run: bool = False) -> dict:
    """Append missing `_history.md` rows for already-SHIPPED spec sidecars.

    This is the cold-path cleanup verb used by `ai-eng cleanup specs`. It
    deliberately does **not** mark APPROVED or IN_PROGRESS specs as shipped;
    lifecycle closure remains explicit via `mark_shipped`.
    """
    summary: dict[str, object] = {
        "consolidated": 0,
        "already_present": 0,
        "skipped": 0,
        "would_consolidate": [],
        "sweep": {"abandoned": 0, "archived": 0},
    }
    specs_dir = _specs_dir(project_root)
    if not specs_dir.exists():
        return summary

    if not dry_run:
        summary["sweep"] = sweep(project_root)

    known_ids = _history_spec_ids(project_root)
    for path in sorted(specs_dir.glob("*.json")):
        try:
            record = SpecRecord.from_json(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            summary["skipped"] = int(summary["skipped"]) + 1
            continue
        if record.state is not LifecycleState.SHIPPED:
            summary["skipped"] = int(summary["skipped"]) + 1
            continue
        if record.spec_id in known_ids:
            summary["already_present"] = int(summary["already_present"]) + 1
            continue
        if dry_run:
            cast_list = summary["would_consolidate"]
            if isinstance(cast_list, list):
                cast_list.append(record.spec_id)
            continue
        _render_history(project_root, append_row=_history_row_for(record))
        known_ids.add(record.spec_id)
        summary["consolidated"] = int(summary["consolidated"]) + 1

    if not dry_run and int(summary["consolidated"]) > 0:
        _append_event(project_root, "spec_history_consolidated", summary)
    return summary


# --- sidecar id migration (spec-153 D-153-01 / D-153-10) -------------------

# Explicit slug→number mappings for sidecars with no resolvable ``_history.md``
# numeric row. The supply-chain spec shipped under PR #536 as spec-152 but its
# sidecar was minted slug-keyed before numeric identity existed (D-153-02).
_EXPLICIT_ID_MAP: dict[str, str] = {
    "github-actions-supply-chain-hardening": "spec-152",
}

# The slug→spec-NNN- prefix is a deterministic numeric signal (the number is
# literally embedded in the slug), not a guess.
_SLUG_PREFIX_RE = re.compile(r"^spec-(\d+)-")


def _spec_frontmatter_id(project_root: Path) -> str | None:
    """Read the canonical ``spec:`` id from ``specs/spec.md`` frontmatter."""
    spec_md = project_root / ".ai-engineering" / "specs" / "spec.md"
    if not spec_md.exists():
        return None
    in_frontmatter = False
    for line in spec_md.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == "---":
            if in_frontmatter:
                break
            in_frontmatter = True
            continue
        if in_frontmatter and stripped.startswith("spec:"):
            value = stripped.split(":", 1)[1].strip()
            if _SPEC_NUMBER_RE.match(value):
                return value
    return None


def _history_title_to_id(project_root: Path) -> dict[str, list[str]]:
    """Map each ledger row title to the list of IDs that carry it."""
    history = _history_path(project_root)
    mapping: dict[str, list[str]] = {}
    if not history.exists():
        return mapping
    rows, _tail = _split_history(history.read_text(encoding="utf-8"))
    data_rows = _migrate_rows(rows)
    for row in data_rows:
        cells = _normalize_row(row)
        if len(cells) >= 2:
            mapping.setdefault(cells[1], []).append(cells[0])
    return mapping


def _resolve_numeric_id(
    record: SpecRecord,
    *,
    project_root: Path,
    frontmatter_id: str | None,
    title_index: dict[str, list[str]],
) -> str | None:
    """Resolve a slug sidecar to its canonical ``spec-NNN`` — or ``None``.

    Resolution order (all deterministic, never a guess):

    1. Explicit known mapping (``_EXPLICIT_ID_MAP``).
    2. This run's own sidecar → ``spec.md`` frontmatter ``spec:``.
    3. Unique ``_history.md`` row whose title equals the sidecar title.
    4. A ``spec-(\\d+)-`` slug prefix (number embedded literally in the slug).

    Returns the resolved ``spec-NNN`` only when it parses to ``^spec-\\d+$``
    and to exactly one candidate; otherwise ``None`` (caller reports it).
    """
    if record.slug in _EXPLICIT_ID_MAP:
        return _EXPLICIT_ID_MAP[record.slug]
    if record.slug == "spec-lifecycle-and-client-readme" and frontmatter_id:
        return frontmatter_id
    matches = title_index.get(record.title, [])
    numeric_matches = sorted({m for m in matches if _SPEC_NUMBER_RE.match(m)})
    if len(numeric_matches) == 1:
        return numeric_matches[0]
    bare_matches = sorted({m for m in matches if m.isdigit()})
    if not numeric_matches and len(bare_matches) == 1:
        return f"spec-{int(bare_matches[0]):03d}"
    prefix = _SLUG_PREFIX_RE.match(record.slug)
    if prefix:
        return f"spec-{int(prefix.group(1)):03d}"
    return None


def _git_mv(project_root: Path, src: Path, dst: Path) -> None:
    """``git mv`` to preserve history; fall back to ``os.replace`` if untracked."""
    try:
        subprocess.run(
            ["git", "-C", str(project_root), "mv", str(src), str(dst)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Untracked file (fresh tmp fixture) or git absent — plain rename.
        os.replace(str(src), str(dst))


def _git_rm(project_root: Path, target: Path) -> None:
    """``git rm`` to preserve history; fall back to ``unlink`` if untracked."""
    try:
        subprocess.run(
            ["git", "-C", str(project_root), "rm", str(target)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        with contextlib.suppress(OSError):
            target.unlink()


def _dedup_obvious_by_default(project_root: Path, *, dry_run: bool) -> dict[str, str] | None:
    """De-duplicate the ``obvious-by-default`` / ``-essentials`` sidecar pair.

    Keeps the record with the later ``created`` timestamp (the more recent,
    more-complete draft) and removes the other (D-153-10). Returns a report
    entry describing the decision, or ``None`` when the pair is not both
    present.
    """
    specs = _specs_dir(project_root)
    primary = specs / "obvious-by-default.json"
    essentials = specs / "obvious-by-default-essentials.json"
    if not (primary.exists() and essentials.exists()):
        return None
    try:
        p_created = json.loads(primary.read_text(encoding="utf-8")).get("created", "")
        e_created = json.loads(essentials.read_text(encoding="utf-8")).get("created", "")
    except (OSError, json.JSONDecodeError):
        return None
    # Later created wins; ISO-8601 strings sort lexicographically by time.
    if e_created >= p_created:
        keep, drop = essentials, primary
    else:
        keep, drop = primary, essentials
    if not dry_run:
        _git_rm(project_root, drop)
    return {"kept": keep.stem, "dropped": drop.stem}


def migrate_ids(project_root: Path, *, dry_run: bool = False) -> dict:
    """Migrate slug-keyed sidecars to the canonical ``spec-NNN`` scheme.

    For every sidecar whose ``spec_id`` is not already ``^spec-\\d+$``, resolve
    its canonical number deterministically (see ``_resolve_numeric_id``),
    rewrite ``spec_id`` in place, and ``git mv`` the file to ``spec-NNN.json``.
    The ``obvious-by-default`` pair is de-duplicated first. Any sidecar whose
    number cannot be unambiguously resolved is left untouched and listed under
    ``unresolved`` — a guessed number is never assigned (spec-153 D-153-01).

    Runs under the ``specs-history`` lock so it serializes against ``start_new``
    minting and never races a concurrent number allocation.
    """
    # Explicit typed accumulators keep the report values concrete (no opaque
    # ``object`` casts, so no suppression comments are needed).
    renamed: list[dict[str, str]] = []
    unresolved: list[str] = []
    already_numeric: list[str] = []
    dedup: dict[str, str] | None = None

    specs = _specs_dir(project_root)
    if not specs.exists():
        return {
            "renamed": renamed,
            "unresolved": unresolved,
            "already_numeric": already_numeric,
            "dedup": dedup,
            "dry_run": dry_run,
        }

    with artifact_lock(project_root, "specs-history"):
        dedup = _dedup_obvious_by_default(project_root, dry_run=dry_run)
        dropped_stem = dedup["dropped"] if dedup else None

        frontmatter_id = _spec_frontmatter_id(project_root)
        title_index = _history_title_to_id(project_root)

        for path in sorted(specs.glob("*.json")):
            if dropped_stem and path.stem == dropped_stem:
                continue  # already removed by the dedup pass.
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                unresolved.append(path.stem)
                continue
            spec_id = str(data.get("spec_id", ""))
            if _SPEC_NUMBER_RE.match(spec_id):
                already_numeric.append(spec_id)
                continue
            try:
                record = SpecRecord.from_json(data)
            except (KeyError, ValueError):
                unresolved.append(path.stem)
                continue
            target_id = _resolve_numeric_id(
                record,
                project_root=project_root,
                frontmatter_id=frontmatter_id,
                title_index=title_index,
            )
            if target_id is None:
                unresolved.append(record.slug)
                continue
            target_path = specs / f"{target_id}.json"
            # Never clobber an existing, distinct numeric sidecar.
            if target_path.exists() and target_path != path:
                unresolved.append(record.slug)
                continue
            renamed.append({"slug": record.slug, "from": path.name, "to": f"{target_id}.json"})
            if dry_run:
                continue
            data["spec_id"] = target_id
            _atomic_write(path, json.dumps(data, indent=2, sort_keys=True))
            _git_mv(project_root, path, target_path)

    if not dry_run and (renamed or dedup):
        _append_event(
            project_root,
            "spec_ids_migrated",
            {
                "renamed": len(renamed),
                "unresolved": len(unresolved),
                "deduped": bool(dedup),
            },
        )
    return {
        "renamed": renamed,
        "unresolved": unresolved,
        "already_numeric": already_numeric,
        "dedup": dedup,
        "dry_run": dry_run,
    }


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
    cs = sub.add_parser("consolidate_shipped", help="Append missing history rows for SHIPPED specs")
    cs.add_argument("--dry-run", action="store_true", help="Preview rows without mutating files")
    _common(cs)
    mi = sub.add_parser("migrate_ids", help="Rename slug sidecars to canonical spec-NNN")
    mi.add_argument("--dry-run", action="store_true", help="Preview renames without mutating files")
    _common(mi)
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
        elif args.cmd == "consolidate_shipped":
            print(json.dumps(consolidate_shipped(project_root, dry_run=args.dry_run), indent=2))
        elif args.cmd == "migrate_ids":
            print(json.dumps(migrate_ids(project_root, dry_run=args.dry_run), indent=2))
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
