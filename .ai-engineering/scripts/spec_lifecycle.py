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


def _drafts_dir(project_root: Path) -> Path:
    """Researched problem briefs awaiting ``/ai-brainstorm``: ``specs/drafts/``."""
    return _specs_root(project_root) / "drafts"


def _archive_drafts_dir(project_root: Path) -> Path:
    """Durable home for reaped stale briefs: ``specs/archive/drafts/``."""
    return _archive_dir(project_root) / "drafts"


# Placeholders the working buffers are reset to once a spec ships (D-153-04).
# These MUST match the framework-wide reset markers (``# No active spec`` /
# ``# No active plan``) that the idle-slot gates and ``maintenance/spec_reset.py``
# recognize — otherwise a freshly consolidated buffer reds the canonical-slot
# gate + ``spec_lint`` on main (spec-161 follow-up). spec.md and plan.md get
# their OWN marker (the plan buffer is not a spec).
_SPEC_BUFFER_PLACEHOLDER = "# No active spec\n\nRun /ai-brainstorm to start one.\n"
_PLAN_BUFFER_PLACEHOLDER = "# No active plan\n\nRun /ai-plan after brainstorm approval.\n"

# Legacy lowercase-paren form previously WRITTEN by ``mark_shipped`` before the
# spec-161 follow-up. Still RECOGNIZED so an idempotent re-run never snapshots a
# buffer a prior (buggy) consolidation already reset.
_LEGACY_BUFFER_PLACEHOLDER = "# (no active spec)\n\nRun /ai-brainstorm to start one.\n"

# Framework-wide placeholder markers RECOGNIZED as empty buffers.
# ``maintenance/spec_reset.py`` clears buffers with ``# No active spec`` /
# ``# No active plan``; recognizing them here keeps ``mark_shipped`` from
# snapshotting a reset buffer (spec-153 quality loop FINDING 4).
_PLACEHOLDER_MARKER_PREFIXES = ("# No active spec", "# No active plan")


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

    A buffer is "empty" for snapshot purposes when it is whitespace-only,
    byte-equal to the reset placeholder, or carries a framework-wide reset
    marker (``# No active spec`` / ``# No active plan`` written by
    ``spec_reset.py``). We refuse to snapshot a placeholder so an idempotent
    ``mark_shipped`` re-run — or a ``spec_reset``-cleared buffer — never
    overwrites a real snapshot with the reset stub.
    """
    stripped = text.strip()
    if not stripped or text in (
        _SPEC_BUFFER_PLACEHOLDER,
        _PLAN_BUFFER_PLACEHOLDER,
        _LEGACY_BUFFER_PLACEHOLDER,
    ):
        return True
    return stripped.startswith(_PLACEHOLDER_MARKER_PREFIXES)


def _snapshot_and_reset(project_root: Path, record: SpecRecord) -> bool:
    """Snapshot ``spec.md``+``plan.md`` into the per-spec archive, then reset them.

    At the SHIPPED transition (D-153-04 / D-153-06): when ``specs/spec.md``
    exists and carries a real (non-placeholder) spec, copy ``spec.md`` and
    ``plan.md`` into ``specs/archive/spec-NNN-<slug>/{spec.md,plan.md}`` and
    overwrite both working buffers with the placeholder. When the buffers are
    already placeholders / absent (existing bare-tmp callers, an idempotent
    re-run after a prior ship), the snapshot is skipped gracefully and the
    buffers are left untouched. Returns ``True`` when a snapshot was taken.

    Snapshot-safety guard (spec-153 D-153-03 / W4): the live working buffer is
    snapshotted **only** when its frontmatter ``spec:`` equals ``record.spec_id``.
    The ``/ai-pr`` path always satisfies this — the buffer *is* the spec being
    shipped. ``reconcile_merged``, by contrast, can mark an OLD/different spec
    whose content is no longer in the buffer (the buffer now holds a later,
    in-flight spec); in that case we MUST NOT snapshot/clear the unrelated
    buffer. The caller still performs the state transition, history row, and
    event — only the file movement is gated here.

    ARCHIVED stays a logical terminal marker with no file movement — this is
    only ever called from ``mark_shipped``.
    """
    spec_buffer = _spec_buffer_path(project_root)
    if not spec_buffer.exists():
        return False
    spec_text = spec_buffer.read_text(encoding="utf-8")
    if _buffer_is_placeholder(spec_text):
        return False
    # Only snapshot when the live buffer IS the spec being shipped. A mismatch
    # means an unrelated in-flight spec is in the buffer (the reconcile path);
    # leave it untouched.
    buffer_id = _spec_frontmatter_id(project_root)
    if buffer_id is not None and buffer_id != record.spec_id:
        return False

    target_dir = _archive_dir(project_root) / f"{record.spec_id}-{record.slug}"
    target_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write(target_dir / "spec.md", spec_text)

    plan_buffer = _plan_buffer_path(project_root)
    plan_text = plan_buffer.read_text(encoding="utf-8") if plan_buffer.exists() else ""
    _atomic_write(target_dir / "plan.md", plan_text)

    # Reset the working buffers to their recognized placeholders so the next
    # spec starts clean — and the idle canonical slot passes the slot gates.
    _atomic_write(spec_buffer, _SPEC_BUFFER_PLACEHOLDER)
    _atomic_write(plan_buffer, _PLAN_BUFFER_PLACEHOLDER)
    return True


def mark_shipped(spec_id: str, pr: str, branch: str, project_root: Path) -> SpecRecord:
    """Walk the current state forward to SHIPPED in one call (idempotent).

    Starts from wherever the record is (DRAFT for the ``/ai-pr`` path,
    APPROVED/IN_PROGRESS for the reconcile backstop) and advances along the
    linear chain DRAFT→APPROVED→IN_PROGRESS→SHIPPED. Already-SHIPPED records
    re-materialize their ledger row idempotently; terminal ARCHIVED/ABANDONED
    raise via the FSM validator.
    """
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
    # Walk the linear lifecycle chain forward FROM the current state to SHIPPED.
    # Records can start at DRAFT (start_new + /ai-pr) or mid-chain at APPROVED /
    # IN_PROGRESS (the reconcile backstop marks a spec already under way). We
    # advance only through the suffix of the chain after the current state, so a
    # legal forward walk never attempts an illegal backward step (e.g.
    # IN_PROGRESS -> APPROVED). Terminal start states (ARCHIVED/ABANDONED) are
    # not in the chain and raise on the first transition — the FSM stays the gate.
    chain = [
        LifecycleState.DRAFT,
        LifecycleState.APPROVED,
        LifecycleState.IN_PROGRESS,
        LifecycleState.SHIPPED,
    ]
    if record.state in chain:
        start = chain.index(record.state)
        for target in chain[start + 1 :]:
            record.state = transition(record.state, target)
    else:
        # ABANDONED/ARCHIVED: surface the illegal move via the FSM validator.
        record.state = transition(record.state, LifecycleState.SHIPPED)
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


def approve(spec_id: str, project_root: Path) -> SpecRecord:
    """Transition DRAFT → APPROVED (idempotent, FSM-guarded; spec-161 D-161-06).

    Composes ``_load_state`` + the domain ``transition`` + ``_write_state`` +
    ``_append_event`` under the shared write path. Re-approving an already-
    APPROVED record is a no-op (no FSM raise, no duplicate event, no write).
    Any other source state (SHIPPED/ABANDONED/ARCHIVED) surfaces an illegal move
    via ``transition`` (ValueError → ``main`` returns 1). The sidecar JSON is the
    canonical store; the ``spec.md`` frontmatter is a best-effort mirror written
    AFTER the sidecar write (D-161-01).
    """
    record = _load_state(project_root, spec_id)
    if record.state is LifecycleState.APPROVED:
        return record  # idempotent — no event, no write.
    record.state = transition(record.state, LifecycleState.APPROVED)
    _write_state(project_root, record)
    _append_event(project_root, "spec_approved", {"spec_id": record.spec_id})
    _mirror_frontmatter_status(project_root, record)
    return record


def start(spec_id: str, project_root: Path) -> SpecRecord:
    """Transition APPROVED → IN_PROGRESS (idempotent, FSM-guarded; spec-161 D-161-06).

    Symmetric with ``approve``. The event kind ``spec_started_impl`` is distinct
    from the ``spec_started`` create-event ``start_new`` emits, so the two never
    collide in the audit stream. Re-starting an already-IN_PROGRESS record is a
    no-op; an illegal source state surfaces via ``transition``.
    """
    record = _load_state(project_root, spec_id)
    if record.state is LifecycleState.IN_PROGRESS:
        return record  # idempotent — no event, no write.
    record.state = transition(record.state, LifecycleState.IN_PROGRESS)
    _write_state(project_root, record)
    _append_event(project_root, "spec_started_impl", {"spec_id": record.spec_id})
    _mirror_frontmatter_status(project_root, record)
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


def _current_branch(project_root: Path) -> str | None:
    """Return the checked-out branch name, or ``None`` off a git worktree."""
    out = _git_stdout(project_root, "rev-parse", "--abbrev-ref", "HEAD")
    if out is None:
        return None
    name = out.strip()
    return name or None


def sweep(
    project_root: Path,
    *,
    default_branch: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Reap stale DRAFTs → ABANDONED and stray root spec files → archive.

    Retention is read from the manifest ``lifecycle:`` block (``draft_ttl_days``,
    ``reap_orphans``), fail-open to 14 days / reaping enabled (D-153-08).

    Safety guards (spec-180 D-180-05):

    - **Protected-branch refusal**: when the checkout is ``main``/``master``/
      ``default_branch`` the sweep makes NO in-place writes and returns
      ``{"protected_branch": <name>, "skipped": "on-protected-branch",
      "abandoned": 0}`` so it can never abandon specs on a shared branch.
    - **Shipped-detection before abandon**: a stale DRAFT whose branch/ledger/
      archive/decision signal proves it shipped is routed away from abandonment
      (counted under ``skipped_shipped``) rather than mislabeled ABANDONED.
    - **dry_run**: classify and count without writing any sidecar.

    The DRAFT→ABANDONED pass runs first; then, when ``reap_orphans`` is set and
    this is not a dry run, the orphan reaper moves any stray ``specs/spec-*.md``
    into its archive directory (D-153-07) and the draft reaper moves stale
    ``specs/drafts/*-brief.md`` files into ``specs/archive/drafts/``. The summary
    — and the ``spec_sweep`` event detail — carries ``reaped`` (stray specs) and
    ``drafts_reaped`` (stale briefs) counts.
    """
    if default_branch is None:
        default_branch = _DEFAULT_BRANCH
    branch = _current_branch(project_root)
    if branch in {"main", "master", default_branch}:
        return {
            "protected_branch": branch,
            "skipped": "on-protected-branch",
            "abandoned": 0,
        }

    draft_ttl_days, reap_orphans = _read_lifecycle_config(project_root)
    summary: dict[str, int] = {
        "abandoned": 0,
        "archived": 0,
        "reaped": 0,
        "drafts_reaped": 0,
        "skipped_shipped": 0,
    }
    ledger_done = _history_done_ids(project_root)
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
                if created >= cutoff:
                    continue
                # Shipped-detection guard: never abandon a stale DRAFT that the
                # signals prove landed. Route it to skipped_shipped instead.
                evidence, _pr = _reconcile_signals(
                    project_root,
                    record,
                    default_branch=default_branch,
                    ledger_done=ledger_done,
                )
                if evidence:
                    summary["skipped_shipped"] += 1
                    continue
                summary["abandoned"] += 1
                if not dry_run:
                    record.state = transition(record.state, LifecycleState.ABANDONED)
                    _write_state(project_root, record)
    if reap_orphans and not dry_run:
        summary["reaped"] = _reap_orphans(project_root)
        summary["drafts_reaped"] = _reap_stale_drafts(project_root, draft_ttl_days)
    if not dry_run:
        _append_event(project_root, "spec_sweep", summary)
    return summary


def status(spec_id: str, project_root: Path) -> SpecRecord:
    """Read-only status query."""
    return _load_state(project_root, spec_id)


def slot_status(project_root: Path) -> dict:
    """Read-only: report whether the live spec slot holds an un-shipped spec.

    Returns a JSON-able dict so ``/ai-brainstorm`` Step -1 (D-167-05) can warn
    before overwriting ``spec.md``. Fail-open: never raises — a missing or
    malformed buffer/sidecar yields a conservative shape rather than an
    exception, so the guard can never block interrogation. ``occupied`` means
    the buffer carries real (non-placeholder) content; ``state`` carries the
    sidecar lifecycle state (e.g. ``shipped``) so the caller can decide that a
    shipped-but-not-cleared slot is safe to overwrite.
    """
    buffer = _spec_buffer_path(project_root)
    try:
        text = buffer.read_text(encoding="utf-8") if buffer.exists() else ""
    except OSError:
        text = ""
    if _buffer_is_placeholder(text):
        return {
            "occupied": False,
            "idle": True,
            "spec_id": None,
            "slug": None,
            "state": None,
        }
    spec_id = _spec_frontmatter_id(project_root)
    slug: str | None = None
    state: str | None = None
    if spec_id is not None:
        try:
            record = _load_state(project_root, spec_id)
            slug = record.slug
            state = record.state.value
        except (FileNotFoundError, KeyError, ValueError):
            pass
    return {
        "occupied": True,
        "idle": False,
        "spec_id": spec_id,
        "slug": slug,
        "state": state,
    }


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
        # Skip symlinks outright: ``is_file()`` follows them, so a hostile
        # ``spec-evil.md -> /outside`` would otherwise be relocated, escaping
        # the tree (spec-153 quality loop FINDING 2). Never follow a symlink.
        if path.is_symlink():
            continue
        if not path.is_file():
            continue
        if path.name in _PROTECTED_SPEC_FILES:
            continue
        dest_dir = _archive_dir(project_root) / path.stem
        dest_dir.mkdir(parents=True, exist_ok=True)
        _git_mv(project_root, path, dest_dir / "spec.md")
        reaped += 1
    return reaped


def _reap_stale_drafts(project_root: Path, draft_ttl_days: int) -> int:
    """Move stale ``specs/drafts/*-brief.md`` files into ``specs/archive/drafts/``.

    Researched problem briefs feed ``/ai-brainstorm`` and otherwise accumulate
    unbounded. A brief whose mtime is older than ``draft_ttl_days`` is reaped to
    ``archive/drafts/<basename>`` (preserving the filename). Like the orphan
    reaper, this only ever *moves* (``git mv`` with a plain-rename fallback) —
    it never deletes — and never follows a symlink (a hostile
    ``evil-brief.md -> /outside`` must not escape the tree). Only ``*-brief.md``
    files are reaped: other markdown in ``drafts/`` is left untouched. Returns
    the number of briefs reaped.
    """
    drafts_dir = _drafts_dir(project_root)
    if not drafts_dir.is_dir():
        return 0
    cutoff = (datetime.now(timezone.utc) - timedelta(days=draft_ttl_days)).timestamp()
    reaped = 0
    for path in sorted(drafts_dir.glob("*-brief.md")):
        if path.is_symlink():
            continue
        if not path.is_file():
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime >= cutoff:
            continue
        dest_dir = _archive_drafts_dir(project_root)
        dest_dir.mkdir(parents=True, exist_ok=True)
        _git_mv(project_root, path, dest_dir / path.name)
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


def _spec_id_in_ledger(spec_id: str, ledger_ids: set[str]) -> bool:
    """True when ``spec_id`` (or its bare-numeric equivalent) is in the ledger.

    The ledger keys historical rows numerically: ``spec-136`` may appear as the
    bare ``136`` (152 of 153 rows) or the ``spec-NNN`` form. We match either so
    the reconcile backstop is idempotent against any historical row shape
    (spec-153 quality loop FINDING 1). ``spec-136`` ↔ ``136`` both resolve.
    """
    if spec_id in ledger_ids:
        return True
    match = _SPEC_NUMBER_RE.match(spec_id)
    if match:
        # bare-numeric equivalent: ``spec-136`` -> ``136`` (zero-padding-agnostic).
        bare = str(int(match.group(1)))
        if bare in ledger_ids or match.group(1) in ledger_ids:
            return True
    return False


def _scan_spec_numbers(project_root: Path) -> set[int]:
    """Collect every ``spec-NNN`` number from sidecars, the ledger + archive dirs.

    Scans three sources, all parsed via the ``spec-(\\d+)`` form: the sidecar
    ``spec_id`` fields, the canonical ``_history.md`` ID cells, and the archive
    ``spec-NNN-<slug>`` directory names under ``specs/archive/`` (spec-161 #574
    Bug 1 — a shipped+archived spec whose sidecar was consolidated away must
    still anchor the next mint so an archived number is never re-used). Bare
    legacy numeric ledger IDs (``099``) are intentionally ignored here: the
    canonical identity is ``spec-NNN`` and the historical rows are frozen
    records, but the highest historical number is still captured via its
    ``spec-``-prefixed presence in sidecars / new rows. The fixture's bare
    ``099`` is matched by the dedicated ledger pass below.
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
    archive = _archive_dir(project_root)
    if archive.is_dir():
        for child in archive.iterdir():
            if not child.is_dir():
                continue
            amatch = _ARCHIVE_DIR_RE.match(child.name)
            if amatch:
                numbers.add(int(amatch.group(1)))
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


# --- ledger-consistency guard (spec-180 D-180-04) --------------------------

# Leading ``spec-NNN`` extracted from a slug so we can compare its number to the
# sidecar id (e.g. id ``spec-158`` vs slug ``spec-159-renamed`` is a mismatch).
_SLUG_LEADING_NUM_RE = re.compile(r"^spec-(\d+)\b")


def _shipped_evidence_labels(
    project_root: Path,
    record: SpecRecord,
    *,
    ledger_done: set[str],
) -> list[str]:
    """Return the on-disk SHIPPED-evidence labels for ``record`` (no network).

    The shared, network-free evidence definition (FIX 2, D-180-04) so
    ``check_ledger`` flags a SHIPPED sidecar ONLY when it has NONE of these:

    - ``pr``: a real (non-empty, non em-dash) PR value on the sidecar.
    - ``ledger-row``: a ``_history.md`` done/shipped row for the id.
    - ``archive-dir``: a unique ``archive/spec-NNN-<slug>/`` directory.
    - ``decision-ref``: a live ``D-<num>-`` anchor across the fixed surface.

    This mirrors ``_reconcile_signals`` minus the ``gh-pr`` git/gh signal, which
    is irrelevant once the sidecar is already SHIPPED (and keeps the guard off
    the network so it can gate CI deterministically).
    """
    labels: list[str] = []
    pr = (record.pr or "").strip()
    if pr and pr != "—":
        labels.append("pr")
    if _spec_id_in_ledger(record.spec_id, ledger_done):
        labels.append("ledger-row")
    if _resolve_via_archive_dir(project_root, record.slug) is not None:
        labels.append("archive-dir")
    if _live_decision_refs(project_root, record.spec_id):
        labels.append("decision-ref")
    return labels


def check_ledger(project_root: Path) -> dict:
    """Read-only guard: flag structural inconsistencies across the spec ledger.

    Walks every sidecar and emits a ``violations`` list (each entry is
    ``{spec_id, rule, detail}``) plus a ``checked`` count. Three rules
    (spec-180 D-180-04), all derived from on-disk state — never a network call,
    never a mutation:

    - ``shipped-no-evidence``: a SHIPPED sidecar with NONE of the four on-disk
      evidences (a real PR, a ``_history`` done-row, an archive directory, or a
      live ``D-<num>-`` decision-ref). This uses the SAME evidence definition as
      ``reconcile_all`` (FIX 2, D-180-04), so a freshly-reconciled-correct ledger
      — including ledger-row-only or decision-ref-only specs — never false-flags.
    - ``nonterminal-with-archive``: a DRAFT/APPROVED/IN_PROGRESS sidecar whose
      archive directory already exists (the work shipped but the sidecar never
      advanced — a stuck-open record).
    - ``id-slug-mismatch``: the numeric prefix embedded in the slug
      (``spec-NNN-…``) disagrees with the sidecar's own ``spec-NNN`` id.

    Designed to gate CI: ``main`` prints the JSON and exits non-zero when any
    violation is present.
    """
    violations: list[dict[str, str]] = []
    checked = 0
    specs_dir = _specs_dir(project_root)
    if not specs_dir.exists():
        return {"violations": violations, "checked": checked}

    ledger_done = _history_done_ids(project_root)
    for path in sorted(specs_dir.glob("*.json")):
        try:
            record = SpecRecord.from_json(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            continue
        checked += 1
        archived_number = _resolve_via_archive_dir(project_root, record.slug)
        has_archive = archived_number is not None

        if record.state is LifecycleState.SHIPPED:
            if not _shipped_evidence_labels(project_root, record, ledger_done=ledger_done):
                violations.append(
                    {
                        "spec_id": record.spec_id,
                        "rule": "shipped-no-evidence",
                        "detail": (
                            "shipped sidecar has no evidence: null PR, no archive "
                            "directory, no _history done-row, no live decision-ref"
                        ),
                    }
                )
        elif record.state in _NON_TERMINAL_STATES and has_archive:
            violations.append(
                {
                    "spec_id": record.spec_id,
                    "rule": "nonterminal-with-archive",
                    "detail": (
                        f"{record.state.value} sidecar has an archive directory "
                        f"({archived_number}); it shipped but never advanced"
                    ),
                }
            )

        slug_match = _SLUG_LEADING_NUM_RE.match(record.slug)
        id_match = _SPEC_NUMBER_RE.match(record.spec_id)
        if slug_match and id_match and int(slug_match.group(1)) != int(id_match.group(1)):
            violations.append(
                {
                    "spec_id": record.spec_id,
                    "rule": "id-slug-mismatch",
                    "detail": (
                        f"slug {record.slug!r} embeds spec-{int(slug_match.group(1)):03d} "
                        f"but the sidecar id is {record.spec_id}"
                    ),
                }
            )

    return {"violations": violations, "checked": checked}


# --- merged-branch reconcile backstop (spec-153 D-153-03) ------------------

# Default branch a spec PR merges into. The classification below mirrors
# ``/ai-branch-cleanup`` Phase 1 exactly (SKILL.md:54-56).
_DEFAULT_BRANCH = "main"

# Non-terminal states whose merged branch should auto-transition to SHIPPED.
_NON_TERMINAL_STATES = frozenset(
    {
        LifecycleState.DRAFT,
        LifecycleState.APPROVED,
        LifecycleState.IN_PROGRESS,
    }
)


def _git_stdout(project_root: Path, *args: str) -> str | None:
    """Run ``git -C <root> <args>`` and return stdout, or ``None`` on failure.

    Fail-open: a missing ``git`` or non-zero exit returns ``None`` so the
    reconcile pass never blocks branch cleanup (the load-bearing hot path).
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _branch_is_merged(project_root: Path, branch: str, default: str) -> bool:
    """True when ``branch`` is merged into ``default`` (mirrors ai-branch-cleanup).

    Two signals, matching ``cli_commands/cleanup.py`` exactly:

    1. **True merge / fast-forward**: ``branch`` appears in
       ``git branch --merged <default>``.
    2. **Squash-merge**: the branch's content landed on ``default`` under a
       single squashed commit — detected with the proven git-trim taxonomy
       (``cleanup.py:_list_squashed_branches``): synthesise a commit of the
       branch tree against the merge-base and ask ``git cherry`` whether that
       patch is already present on ``default`` (a leading ``-``).

    A *naive* empty ``git diff <default>..<branch>`` is deliberately **not**
    used: an empty diff also occurs for a branch with zero unique commits
    (freshly cut from ``default``, rebased away, or at/behind it), which would
    phantom-ship a spec. We therefore require evidence the content actually
    landed: a strictly-positive unique-commit count (``git rev-list --count
    <default>..<branch>``) AND a squashed-patch hit from the cherry taxonomy.
    Any ``None`` (git failed / branch absent) is never treated as merged.
    """
    merged = _git_stdout(project_root, "branch", "--merged", default)
    if merged is not None:
        names = {line.strip().lstrip("* ").strip() for line in merged.splitlines()}
        names.discard("")
        if branch in names:
            return True
    return _branch_is_squash_merged(project_root, branch, default)


def _branch_is_squash_merged(project_root: Path, branch: str, default: str) -> bool:
    """Squash-merge detection via the ``cleanup.py`` merge-base/cherry taxonomy.

    Returns ``True`` only when the branch carries at least one unique commit
    relative to ``default`` AND the synthesised commit of its tree is already
    reachable (cherry-equivalent) on ``default``. A branch with zero unique
    commits — the empty-diff false-positive — returns ``False``.
    """
    # Guard: zero unique commits is NOT a squash-merge (empty/behind/at-default).
    count_out = _git_stdout(project_root, "rev-list", "--count", f"{default}..{branch}")
    if count_out is None:
        return False
    try:
        unique_commits = int(count_out.strip() or "0")
    except ValueError:
        return False
    if unique_commits <= 0:
        return False

    # cleanup.py taxonomy: merge-base + commit-tree(branch-tree) + cherry.
    merge_base = _git_stdout(project_root, "merge-base", default, branch)
    if merge_base is None or not merge_base.strip():
        return False
    tree = _git_stdout(project_root, "rev-parse", f"{branch}^{{tree}}")
    if tree is None or not tree.strip():
        return False
    synthetic = _git_stdout(
        project_root, "commit-tree", tree.strip(), "-p", merge_base.strip(), "-m", "_check"
    )
    if synthetic is None or not synthetic.strip():
        return False
    cherry = _git_stdout(project_root, "cherry", default, synthetic.strip())
    # A leading "-" marks a patch already present on <default> (squash-merged).
    return cherry is not None and cherry.strip().startswith("-")


def _resolve_merged_pr(project_root: Path, branch: str) -> str:
    """Resolve the merged PR number for ``branch`` via ``gh``; fail-open to ``—``.

    Runs ``gh pr list --head <branch> --state merged --json number`` and returns
    the first number as a string. When ``gh`` is absent, errs, or returns no
    rows, returns the em-dash placeholder so the ledger row stays well-formed.
    """
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--head",
                branch,
                "--state",
                "merged",
                "--json",
                "number",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return "—"
    if result.returncode != 0:
        return "—"
    try:
        rows = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return "—"
    if isinstance(rows, list) and rows:
        number = rows[0].get("number")
        if number is not None:
            return str(number)
    return "—"


def _pr_merged_via_gh(project_root: Path, branch: str) -> bool:
    """True when ``gh`` reports at least one merged PR for ``branch``; fail-open False.

    Runs ``gh pr list --head <branch> --state merged --json number`` (mirroring
    the subprocess fail-open shape of ``_resolve_merged_pr``). A merged PR closes
    the gap where the local branch ref was pruned post-merge, so
    ``_branch_is_merged`` alone would mis-classify a genuinely merged spec as
    unmerged (spec-161 #574 Bug 2). ``gh`` absent / non-zero / empty / JSON error
    all return ``False`` so the classification never blocks the cleanup path.
    """
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--head",
                branch,
                "--state",
                "merged",
                "--json",
                "number",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return False
    if result.returncode != 0:
        return False
    try:
        rows = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return False
    return isinstance(rows, list) and len(rows) >= 1


def reconcile_merged(project_root: Path, *, default_branch: str = _DEFAULT_BRANCH) -> dict:
    """Auto-mark merged-but-unshipped specs SHIPPED (idempotent backstop).

    The backstop for D-153-03: ``/ai-pr`` marks a spec at merge time when it
    holds the PR + branch, but a spec merged via the GitHub UI (or any non-
    ``/ai-pr`` path) never fires ``mark_shipped``. This verb closes that gap.

    For each sidecar in a non-terminal state (DRAFT/APPROVED/IN_PROGRESS)
    carrying a ``branch``, classify the branch with the same logic as
    ``/ai-branch-cleanup`` (``git branch --merged`` + squash-merge emptiness).
    A merged branch resolves its PR via ``gh`` (fail-open to ``—``) and calls
    ``mark_shipped`` — which is idempotent, so already-SHIPPED records are a
    no-op (they are terminal and skipped before any git work). Sidecars with no
    branch are skipped. Stays off the pre-push hot path (cleanup-time only).

    Returns ``{"shipped": [...], "skipped": [...], "unmerged": [...]}`` reports.
    """
    shipped: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    unmerged: list[dict[str, str]] = []

    specs = _specs_dir(project_root)
    if not specs.exists():
        return {"shipped": shipped, "skipped": skipped, "unmerged": unmerged}

    # Ledger-presence idempotency guard (spec-153 quality loop FINDING 1): a
    # spec already recorded in ``_history.md`` (under either its ``spec-NNN`` id
    # or its bare-numeric equivalent ``NNN``) must never be re-shipped, even if
    # its branch still classifies as merged. This neutralizes the empty-diff
    # phantom-ship risk against historical rows regardless of branch-detection.
    ledger_ids = _history_spec_ids(project_root)

    for path in sorted(specs.glob("*.json")):
        try:
            record = SpecRecord.from_json(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            skipped.append({"spec_id": path.stem, "reason": "unreadable"})
            continue
        if record.state not in _NON_TERMINAL_STATES:
            # SHIPPED / ABANDONED / ARCHIVED are terminal for the reconcile.
            skipped.append({"spec_id": record.spec_id, "reason": "terminal-state"})
            continue
        if _spec_id_in_ledger(record.spec_id, ledger_ids):
            # Already shipped historically — skip regardless of branch state.
            skipped.append({"spec_id": record.spec_id, "reason": "already-in-ledger"})
            continue
        if not record.branch:
            skipped.append({"spec_id": record.spec_id, "reason": "no-branch"})
            continue
        # Classify merged via two independent signals (spec-161 #574 Bug 2): a
        # ``gh``-reported merged PR for the branch (survives a pruned local ref)
        # OR the local-branch true-merge / squash taxonomy. The ledger guard
        # above still precedes any git/gh work, so historical rows never re-ship.
        merged = _pr_merged_via_gh(project_root, record.branch) or _branch_is_merged(
            project_root, record.branch, default_branch
        )
        if not merged:
            unmerged.append({"spec_id": record.spec_id, "branch": record.branch})
            continue
        pr = _resolve_merged_pr(project_root, record.branch)
        mark_shipped(record.spec_id, pr, record.branch, project_root)
        shipped.append({"spec_id": record.spec_id, "pr": pr, "branch": record.branch})

    if shipped:
        _append_event(
            project_root,
            "spec_reconciled_merged",
            {"shipped": len(shipped), "default_branch": default_branch},
        )
    return {"shipped": shipped, "skipped": skipped, "unmerged": unmerged}


# --- 3-signal reconcile (spec-180 D-180-03) --------------------------------

# Ledger row statuses that mean the spec landed (any case).
_DONE_STATUSES = frozenset({"done", "shipped", "implemented"})

# Sidecars older than this (and with no shipped signal) are abandonment-eligible.
_RECONCILE_STALE_DAYS = 30

# Fixed surface scanned for live ``D-<NNN>-`` decision anchors. Root files are
# scanned directly; the directory entries are walked recursively. Kept stdlib
# only (os.walk / Path.rglob) so the script stays import-light.
_DECISION_REF_FILES = (
    "CLAUDE.md",
    "CONSTITUTION.md",
    "SOUL.md",
    "CHANGELOG.md",
    ".ai-engineering/solution-intent.md",
    ".ai-engineering/LESSONS.md",
)
_DECISION_REF_GLOBS = (
    (".ai-engineering/reference", "*.md"),
    ("docs", "*.md"),
)
_DECISION_REF_TREES = ("src", ".github")


def _history_done_ids(project_root: Path) -> set[str]:
    """Return spec ids whose ``_history.md`` row status reads done/shipped/etc.

    Matches the ledger row status cell (column 3) against ``_DONE_STATUSES``
    case-insensitively. Both ``spec-NNN`` and bare-numeric ids are returned so
    the caller can match either historical row shape via ``_spec_id_in_ledger``.
    """
    history = _history_path(project_root)
    if not history.exists():
        return set()
    rows, _tail = _split_history(history.read_text(encoding="utf-8"))
    data_rows = _migrate_rows(rows)
    ids: set[str] = set()
    for row in data_rows:
        cells = _normalize_row(row)
        if len(cells) >= 3 and cells[2].strip().lower() in _DONE_STATUSES:
            ids.add(cells[0])
    return ids


def _history_pr_for(project_root: Path, spec_id: str) -> str | None:
    """Return the PR cell (column 6) of ``spec_id``'s ``_history.md`` row, or None.

    Resolves the row by id under either the ``spec-NNN`` or bare-numeric shape
    (mirroring ``_spec_id_in_ledger``). A real PR value (e.g. ``#509``, ``517``)
    is returned verbatim; the em-dash placeholder ``—`` and an empty cell both
    yield ``None`` so the caller falls back to its own sentinel. This is the
    bundle-PR backfill source (spec-180 FIX 1): a bundle-merged spec whose branch
    yields no ``gh`` PR still adopts the bundle PR recorded in the ledger row.
    """
    history = _history_path(project_root)
    if not history.exists():
        return None
    rows, _tail = _split_history(history.read_text(encoding="utf-8"))
    data_rows = _migrate_rows(rows)
    match = _SPEC_NUMBER_RE.match(spec_id)
    bare = str(int(match.group(1))) if match else None
    raw = match.group(1) if match else None
    for row in data_rows:
        cells = _normalize_row(row)
        if not cells:
            continue
        row_id = cells[0]
        if row_id == spec_id or (bare is not None and row_id in {bare, raw}):
            pr = cells[5].strip() if len(cells) >= 6 else ""
            if pr and pr != "—":
                return pr
            return None
    return None


def _live_decision_refs(project_root: Path, spec_id: str) -> bool:
    """True when a live ``D-<NNN>-`` decision anchor for ``spec_id`` exists.

    ``NNN`` is the spec number (``spec-180`` -> ``180``). We match ``D-180-``
    (the trailing hyphen anchors the decision index) across a FIXED surface list
    so a plain prose mention of ``spec-180`` never counts as a live decision.
    Fail-open: an unreadable file is skipped, never raised.
    """
    match = _SPEC_NUMBER_RE.match(spec_id)
    if not match:
        return False
    needle = f"D-{int(match.group(1))}-"
    candidates: list[Path] = []
    for rel in _DECISION_REF_FILES:
        candidates.append(project_root / rel)
    for rel_dir, pattern in _DECISION_REF_GLOBS:
        base = project_root / rel_dir
        if base.is_dir():
            candidates.extend(sorted(base.rglob(pattern)))
    for rel_tree in _DECISION_REF_TREES:
        base = project_root / rel_tree
        if not base.is_dir():
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in files:
                if name.endswith((".pyc", ".pyo")):
                    continue
                candidates.append(Path(root) / name)
    for path in candidates:
        if path.is_symlink() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if needle in text:
            return True
    return False


def _reconcile_signals(
    project_root: Path,
    record: SpecRecord,
    *,
    default_branch: str,
    ledger_done: set[str],
) -> tuple[list[str], str | None]:
    """Collect SHIPPED evidence for ``record``; return ``(evidence, pr)``.

    Evidence labels (in precedence order for the resolved PR): ``gh-pr``,
    ``ledger-row``, ``archive-dir``, ``decision-ref``. ``pr`` is the gh-resolved
    number when a branch classified as merged, else ``None`` (the caller falls
    back to a sentinel). An empty evidence list means no shipped signal.
    """
    evidence: list[str] = []
    pr: str | None = None
    if record.branch and (
        _pr_merged_via_gh(project_root, record.branch)
        or _branch_is_merged(project_root, record.branch, default_branch)
    ):
        evidence.append("gh-pr")
        pr = _resolve_merged_pr(project_root, record.branch)
    if _spec_id_in_ledger(record.spec_id, ledger_done):
        evidence.append("ledger-row")
    if _resolve_via_archive_dir(project_root, record.slug) is not None:
        evidence.append("archive-dir")
    if _live_decision_refs(project_root, record.spec_id):
        evidence.append("decision-ref")
    return evidence, pr


def reconcile_all(
    project_root: Path,
    *,
    default_branch: str = _DEFAULT_BRANCH,
    dry_run: bool = False,
) -> dict:
    """Classify every non-terminal sidecar via four independent signals.

    A non-terminal (DRAFT/APPROVED/IN_PROGRESS) sidecar is classified SHIPPED
    when ANY signal holds: (1) a ``gh`` merged PR / merged branch, (2) a
    ``_history.md`` ledger row marking it done/shipped/implemented, (3) a
    ``archive/<spec_id>-<slug>/`` directory, or (4) a live ``D-<NNN>-`` decision
    anchor. It is classified ABANDONED only when ALL four signals are absent AND
    the sidecar is superseded (``extra.superseded_by``) OR older than the
    staleness threshold. Terminal states (SHIPPED/ABANDONED/ARCHIVED) are never
    downgraded — they are skipped before any signal work.

    ``dry_run=True`` returns the full report (with per-spec ``evidence``) and
    mutates NOTHING. On a live run shipped sidecars advance via ``mark_shipped``
    (PR = gh-resolved value or the ``—`` sentinel) and abandoned sidecars
    transition DRAFT/APPROVED/IN_PROGRESS → ABANDONED.

    Returns ``{"shipped": [...], "abandoned": [...], "skipped": [...]}``.
    """
    shipped: list[dict[str, str | list[str]]] = []
    abandoned: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []

    specs = _specs_dir(project_root)
    if not specs.exists():
        return {"shipped": shipped, "abandoned": abandoned, "skipped": skipped}

    ledger_done = _history_done_ids(project_root)
    cutoff = datetime.now(timezone.utc) - timedelta(days=_RECONCILE_STALE_DAYS)

    for path in sorted(specs.glob("*.json")):
        try:
            record = SpecRecord.from_json(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            skipped.append({"spec_id": path.stem, "reason": "unreadable"})
            continue
        if record.state not in _NON_TERMINAL_STATES:
            skipped.append({"spec_id": record.spec_id, "reason": "terminal-state"})
            continue

        evidence, pr = _reconcile_signals(
            project_root, record, default_branch=default_branch, ledger_done=ledger_done
        )
        if evidence:
            # PR precedence: a real gh-resolved value (most direct) wins; the
            # em-dash sentinel from a gh miss does NOT, so a bundle-merged spec
            # backfills its bundle PR from the ledger row (FIX 1, D-180-03). Only
            # when neither yields a real number do we fall back to the sentinel.
            gh_pr = pr if (pr and pr != "—") else None
            resolved_pr = gh_pr or _history_pr_for(project_root, record.spec_id) or "—"
            if not dry_run:
                mark_shipped(record.spec_id, resolved_pr, record.branch or "—", project_root)
            shipped.append({"spec_id": record.spec_id, "pr": resolved_pr, "evidence": evidence})
            continue

        # No shipped signal — abandon only when superseded or stale.
        superseded = bool(record.extra.get("superseded_by"))
        stale = False
        try:
            created = datetime.fromisoformat(record.created)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            stale = created < cutoff
        except ValueError:
            stale = False
        if superseded or stale:
            if not dry_run:
                record.state = transition(record.state, LifecycleState.ABANDONED)
                _write_state(project_root, record)
            abandoned.append(
                {"spec_id": record.spec_id, "reason": "superseded" if superseded else "stale"}
            )
        else:
            skipped.append({"spec_id": record.spec_id, "reason": "no-signal-fresh"})

    if not dry_run and (shipped or abandoned):
        _append_event(
            project_root,
            "spec_reconciled_all",
            {
                "shipped": len(shipped),
                "abandoned": len(abandoned),
                "default_branch": default_branch,
            },
        )
    return {"shipped": shipped, "abandoned": abandoned, "skipped": skipped}


# --- sidecar id migration (spec-153 D-153-01 / D-153-10) -------------------

# Explicit slug→number mappings for sidecars with no resolvable ``_history.md``
# numeric row. The supply-chain spec shipped under PR #536 as spec-152 but its
# sidecar was minted slug-keyed before numeric identity existed (D-153-02).
_EXPLICIT_ID_MAP: dict[str, str] = {
    "github-actions-supply-chain-hardening": "spec-152",
    "ai-engineering-release-version-cicd-pypi": "spec-143",
}

# The slug→spec-NNN- prefix is a deterministic numeric signal (the number is
# literally embedded in the slug), not a guess.
_SLUG_PREFIX_RE = re.compile(r"^spec-(\d+)-")

# Archive directory name shape: ``spec-NNN-<slug>`` (W3 layout, D-153-06). The
# trailing ``<slug>`` must match a sidecar slug exactly for an authoritative
# number adoption (spec-153 quality loop FINDING 5).
_ARCHIVE_DIR_RE = re.compile(r"^spec-(\d+)-(.+)$")


def _resolve_via_archive_dir(project_root: Path, slug: str) -> str | None:
    """Adopt the number of the UNIQUE ``archive/spec-NNN-<slug>/`` dir, or None.

    W3 created per-spec archive directories named ``spec-NNN-<slug>`` for
    shipped specs (D-153-06). When a slug sidecar's ``<slug>`` exactly equals an
    archive dir's trailing slug AND that match is unique, the embedded number is
    an authoritative source (spec-153 quality loop FINDING 5). Zero matches or
    an ambiguous (>1 distinct number) match returns ``None`` — a guessed or
    ambiguous number is never assigned.
    """
    archive = _archive_dir(project_root)
    if not archive.is_dir():
        return None
    numbers: set[int] = set()
    for child in archive.iterdir():
        if not child.is_dir():
            continue
        match = _ARCHIVE_DIR_RE.match(child.name)
        # ``group(2)`` is the BARE trailing slug; match it for plain slugs, and
        # also accept a verbatim ``child.name == slug`` so a sidecar whose slug
        # already carries the ``spec-NNN-`` prefix (e.g. spec-133) still resolves
        # its archive dir (spec-180 review hardening — was a silent blind spot).
        if match and (match.group(2) == slug or child.name == slug):
            numbers.add(int(match.group(1)))
    if len(numbers) == 1:
        return f"spec-{next(iter(numbers)):03d}"
    return None


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


# state.value → frontmatter ``status:`` vocabulary map (spec-161 D-161-02).
_STATE_TO_STATUS: dict[str, str] = {
    "draft": "draft",
    "approved": "approved",
    "in_progress": "in-progress",
    "shipped": "done",
}


def _frontmatter_field(project_root: Path, field_name: str) -> str | None:
    """Read a raw frontmatter ``field_name:`` value from ``specs/spec.md``, or None."""
    spec_md = _spec_buffer_path(project_root)
    if not spec_md.exists():
        return None
    in_frontmatter = False
    prefix = f"{field_name}:"
    for line in spec_md.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == "---":
            if in_frontmatter:
                break
            in_frontmatter = True
            continue
        if in_frontmatter and stripped.startswith(prefix):
            return stripped.split(":", 1)[1].strip()
    return None


def _mirror_frontmatter_status(project_root: Path, record: SpecRecord) -> None:
    """Best-effort mirror the record's state onto the ``specs/spec.md`` frontmatter.

    The sidecar JSON is canonical; this mirror is a convenience projection written
    AFTER the sidecar write (spec-161 D-161-01). The ``status:`` line is rewritten
    using the ``state.value`` → status map (D-161-02) **only** when the live
    buffer's frontmatter ``spec:`` equals ``record.spec_id`` OR its ``slug:``
    equals ``record.slug`` — never a cross-spec write against an unrelated
    in-flight buffer. All other frontmatter lines and the body bytes are preserved
    exactly. Fail-open (D-161-08): any ``OSError`` logs to stderr and returns; this
    function NEVER raises, so a missing/locked/unwritable buffer can't fail the verb.
    """
    spec_md = _spec_buffer_path(project_root)
    new_status = _STATE_TO_STATUS.get(record.state.value)
    if new_status is None:
        return
    try:
        if not spec_md.exists():
            return
        fm_spec = _frontmatter_field(project_root, "spec")
        fm_slug = _frontmatter_field(project_root, "slug")
        if fm_spec != record.spec_id and fm_slug != record.slug:
            return  # not this spec's buffer — never cross-write.
        original = spec_md.read_text(encoding="utf-8")
        lines = original.splitlines(keepends=True)
        in_frontmatter = False
        rewritten = False
        out: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not rewritten and stripped == "---":
                if in_frontmatter:
                    # Closing fence reached without a status line — append one.
                    out.append(f"status: {new_status}\n")
                    out.append(line)
                    rewritten = True
                    in_frontmatter = False
                    continue
                in_frontmatter = True
                out.append(line)
                continue
            if in_frontmatter and not rewritten and stripped.startswith("status:"):
                newline = "\n" if line.endswith("\n") else ""
                out.append(f"status: {new_status}{newline}")
                rewritten = True
                continue
            out.append(line)
        _atomic_write(spec_md, "".join(out))
    except OSError as exc:
        print(f"warning: frontmatter status mirror skipped: {exc}", file=sys.stderr)


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
    5. A UNIQUE ``archive/spec-NNN-<slug>/`` directory whose ``<slug>`` equals
       the sidecar slug (W3 layout; authoritative for shipped specs, spec-153
       quality loop FINDING 5).

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
    return _resolve_via_archive_dir(project_root, record.slug)


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
    ap = sub.add_parser("approve", help="Transition DRAFT → APPROVED")
    ap.add_argument("spec_id")
    _common(ap)
    sta = sub.add_parser("start", help="Transition APPROVED → IN_PROGRESS")
    sta.add_argument("spec_id")
    _common(sta)
    ms = sub.add_parser("mark_shipped", help="Mark spec SHIPPED post-merge")
    ms.add_argument("spec_id")
    ms.add_argument("pr")
    ms.add_argument("branch")
    _common(ms)
    ar = sub.add_parser("archive", help="Move SHIPPED|ABANDONED → ARCHIVED")
    ar.add_argument("spec_id")
    _common(ar)
    sw = sub.add_parser("sweep", help="Reap stale DRAFT > 14d → ABANDONED")
    sw.add_argument(
        "--default-branch",
        default=_DEFAULT_BRANCH,
        help=f"Protected branch the sweep refuses to write on (default: {_DEFAULT_BRANCH})",
    )
    sw.add_argument(
        "--dry-run",
        action="store_true",
        help="Report would-be abandons without mutating sidecars",
    )
    _common(sw)
    st = sub.add_parser("status", help="Read record state")
    st.add_argument("spec_id")
    _common(st)
    ss = sub.add_parser("slot_status", help="Report whether the live spec slot is occupied")
    _common(ss)
    mh = sub.add_parser("migrate-history", help="One-shot legacy history migration")
    _common(mh)
    cs = sub.add_parser("consolidate_shipped", help="Append missing history rows for SHIPPED specs")
    cs.add_argument("--dry-run", action="store_true", help="Preview rows without mutating files")
    _common(cs)
    mi = sub.add_parser("migrate_ids", help="Rename slug sidecars to canonical spec-NNN")
    mi.add_argument("--dry-run", action="store_true", help="Preview renames without mutating files")
    _common(mi)
    rm = sub.add_parser(
        "reconcile_merged",
        help="Auto-mark merged-but-unshipped specs SHIPPED (idempotent backstop)",
    )
    rm.add_argument(
        "--default-branch",
        default=_DEFAULT_BRANCH,
        help=f"Branch PRs merge into (default: {_DEFAULT_BRANCH})",
    )
    _common(rm)
    cl = sub.add_parser(
        "check_ledger",
        help="Flag ledger inconsistencies (exits non-zero when any violation)",
    )
    _common(cl)
    ra = sub.add_parser(
        "reconcile_all",
        help="Classify non-terminal specs SHIPPED/ABANDONED via 4 signals",
    )
    ra.add_argument(
        "--default-branch",
        default=_DEFAULT_BRANCH,
        help=f"Branch PRs merge into (default: {_DEFAULT_BRANCH})",
    )
    ra.add_argument(
        "--dry-run",
        action="store_true",
        help="Report classifications without mutating sidecars",
    )
    _common(ra)
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
        elif args.cmd == "approve":
            record = approve(args.spec_id, project_root)
            print(json.dumps(record.to_json(), indent=2))
        elif args.cmd == "start":
            record = start(args.spec_id, project_root)
            print(json.dumps(record.to_json(), indent=2))
        elif args.cmd == "mark_shipped":
            record = mark_shipped(args.spec_id, args.pr, args.branch, project_root)
            print(json.dumps(record.to_json(), indent=2))
        elif args.cmd == "archive":
            record = archive(args.spec_id, project_root)
            print(json.dumps(record.to_json(), indent=2))
        elif args.cmd == "sweep":
            print(
                json.dumps(
                    sweep(
                        project_root,
                        default_branch=args.default_branch,
                        dry_run=args.dry_run,
                    ),
                    indent=2,
                )
            )
        elif args.cmd == "status":
            record = status(args.spec_id, project_root)
            print(json.dumps(record.to_json(), indent=2))
        elif args.cmd == "slot_status":
            print(json.dumps(slot_status(project_root), indent=2))
        elif args.cmd == "migrate-history":
            migrate_history(project_root)
            print("migrated _history.md to 7-col canonical layout")
        elif args.cmd == "consolidate_shipped":
            print(json.dumps(consolidate_shipped(project_root, dry_run=args.dry_run), indent=2))
        elif args.cmd == "migrate_ids":
            print(json.dumps(migrate_ids(project_root, dry_run=args.dry_run), indent=2))
        elif args.cmd == "reconcile_merged":
            print(
                json.dumps(
                    reconcile_merged(project_root, default_branch=args.default_branch),
                    indent=2,
                )
            )
        elif args.cmd == "check_ledger":
            ledger_report = check_ledger(project_root)
            print(json.dumps(ledger_report, indent=2))
            if ledger_report["violations"]:
                return 1
        elif args.cmd == "reconcile_all":
            print(
                json.dumps(
                    reconcile_all(
                        project_root,
                        default_branch=args.default_branch,
                        dry_run=args.dry_run,
                    ),
                    indent=2,
                )
            )
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
