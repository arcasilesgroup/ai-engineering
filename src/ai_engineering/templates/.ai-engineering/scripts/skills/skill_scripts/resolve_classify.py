"""Conflict classification for merge-conflict resolution (spec-129 T-12).

Pure classifier: maps a single path (with optional file content) to a
``Classification`` describing what kind of conflict it is, what action is
safe, and how confident the heuristic is. **This module never performs
resolution** — it only labels the file so the caller can decide whether
to auto-merge, surface to a human, or refuse.

Conservative-default contract (spec-129 §Risks): when in doubt return
``action="ambiguous"`` (or ``"manual"`` for unmistakable code). NEVER
return ``action="auto-resolve"`` on a low-confidence signal. Filename
heuristics alone (for example ``*_pb2.py``) MUST NOT trigger
auto-resolve — an in-file sentinel is required.

Classification rules — STRICT ORDER, FIRST MATCH WINS:

1. **Migration path** (highest priority): path contains a ``/migrations/``
   segment, matches ``*_migration.sql``, or starts with ``db/migrate/``.
   → ``(MIGRATION, ambiguous, high)``. Migrations are *never*
   auto-resolved even though their identity is certain — the operator
   owns reconciliation.
2. **Lock file with manual edits** (adversarial): filename matches
   ``*.lock`` / ``package-lock.json`` / ``uv.lock`` / ``poetry.lock`` /
   ``Cargo.lock`` AND the file body contains a comment marker like
   ``// MANUAL EDIT``, ``# MANUAL EDIT``, ``<!-- MANUAL EDIT``, or a
   ``"_comment": "MANUAL EDIT…"`` JSON sentinel. Body scan is bounded to
   the first 200 lines.
   → ``(LOCK, ambiguous, low)``.
3. **Lock file vanilla**: filename matches the lock patterns above, no
   manual-edit markers found. → ``(LOCK, auto-resolve, high)``.
4. **Generated WITH sentinel**: file body's first 20 lines contains
   ``AUTO-GENERATED`` (case-sensitive sentinel banner) in any common
   comment shape (``// AUTO-GENERATED``, ``# AUTO-GENERATED``,
   ``/* AUTO-GENERATED``). → ``(GENERATED, auto-resolve, high)``.
5. **Looks generated WITHOUT sentinel** (adversarial): filename matches
   ``*_pb2.py``, ``*_pb.go``, ``*.gen.<ext>``, ``*_gen.<ext>``,
   ``*_generated.<ext>``, or ``*.generated.<ext>`` BUT the body carries
   no sentinel. → ``(UNKNOWN, ambiguous, low)``. We refuse to
   auto-resolve on filename alone.
6. **Config file**: filename matches ``.env``, ``pyproject.toml``,
   ``package.json`` (without ``-lock``), ``*.toml``, ``*.yaml``/
   ``*.yml``, ``*.json`` (excluding lock variants), ``tsconfig.json``.
   → ``(CONFIG, ambiguous, medium)``.
7. **Plain code file**: extension matches ``.py``, ``.ts``, ``.tsx``,
   ``.js``, ``.jsx``, ``.go``, ``.rs``, ``.java``, ``.cs``, ``.kt``,
   ``.swift``. → ``(CODE, manual, high)``.
8. **Default fallback**: anything else.
   → ``(UNKNOWN, ambiguous, low)``.

Performance: 100 paths classify in well under 500 ms (string-level
checks plus a bounded line scan on lock / sentinel candidates only).
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class ConflictType(StrEnum):
    """Family of conflict surfaced by ``classify_conflict``."""

    LOCK = "lock"
    GENERATED = "generated"
    MIGRATION = "migration"
    CODE = "code"
    CONFIG = "config"
    UNKNOWN = "unknown"


Action = Literal["auto-resolve", "ambiguous", "manual"]
Confidence = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class Classification:
    """Result of classifying a single conflict path.

    Immutable so callers can hand it to downstream renderers / loggers
    without defensive copying.
    """

    type: ConflictType
    action: Action
    confidence: Confidence
    reason: str


# ---------------------------------------------------------------------------
# Heuristic tables (module-level so we pay the cost once per process)
# ---------------------------------------------------------------------------

_LOCK_EXACT_NAMES: frozenset[str] = frozenset(
    {
        "package-lock.json",
        "uv.lock",
        "poetry.lock",
        "Cargo.lock",
        "yarn.lock",
        "pnpm-lock.yaml",
        "Pipfile.lock",
        "Gemfile.lock",
        "composer.lock",
    }
)

# Suffix-only lock heuristic: catches generic ``*.lock`` files such as
# ``vendor.lock`` while keeping the exact-name table for the common
# ecosystem files (where prefix matters, e.g. ``package-lock.json``).
_LOCK_SUFFIX: str = ".lock"

# Prefix-based lock heuristic: covers adversarial / annotated variants
# such as ``package-lock-edited.json`` (a fixture name) or
# ``package-lock.v2.json`` where the conventional base name is buried
# under git rename suffixes. The token is unique enough to the lock
# family that false positives are negligible.
_LOCK_NAME_PREFIXES: tuple[str, ...] = (
    "package-lock",
    "yarn-lock",
)

_MIGRATION_FILE_SUFFIX: str = "_migration.sql"
_MIGRATION_PATH_SEGMENTS: tuple[str, ...] = ("migrations", "migrate")

_SENTINEL_TOKEN: str = "AUTO-GENERATED"
_SENTINEL_SCAN_LINES: int = 20

_MANUAL_EDIT_TOKENS: tuple[str, ...] = (
    "// MANUAL EDIT",
    "# MANUAL EDIT",
    "<!-- MANUAL EDIT",
    "/* MANUAL EDIT",
    "MANUAL EDIT:",  # JSON ``"_comment": "MANUAL EDIT: …"`` sentinel.
)
_MANUAL_EDIT_SCAN_LINES: int = 200

_CODE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".go",
        ".rs",
        ".java",
        ".cs",
        ".kt",
        ".swift",
        ".rb",
        ".php",
    }
)

_CONFIG_EXACT_NAMES: frozenset[str] = frozenset(
    {
        ".env",
        "pyproject.toml",
        "package.json",
        "tsconfig.json",
    }
)
_CONFIG_SUFFIXES: frozenset[str] = frozenset({".toml", ".yaml", ".yml", ".json", ".ini"})


# ---------------------------------------------------------------------------
# Heuristic predicates
# ---------------------------------------------------------------------------


def _is_migration_path(path: Path) -> bool:
    """Return True when ``path`` is recognisably a database migration.

    Three signals collapse into one rule (per spec § rules.1):

    * any path segment named ``migrations`` (Django, Alembic ``versions``'s
      parent, generic ``src/db/migrations/`` layouts),
    * any path segment named ``migrate`` (Rails ``db/migrate/`` layout),
    * a filename ending ``_migration.sql`` (raw SQL migrations).
    """
    parts = path.parts
    if any(segment in _MIGRATION_PATH_SEGMENTS for segment in parts):
        return True
    # Alembic stores files under ``alembic/versions/`` — when the test
    # composes ``alembic/versions/abc123_init.py`` the ``versions``
    # segment is unique enough to count as a migration when paired with
    # an ``alembic`` ancestor.
    if "alembic" in parts and "versions" in parts:
        return True
    return path.name.endswith(_MIGRATION_FILE_SUFFIX)


def _is_lock_filename(name: str) -> bool:
    """Return True for the lock-file family by filename only."""
    if name in _LOCK_EXACT_NAMES:
        return True
    if name.endswith(_LOCK_SUFFIX):
        return True
    return any(name.startswith(prefix) for prefix in _LOCK_NAME_PREFIXES)


def _looks_generated_filename(name: str) -> bool:
    """Return True when filename mimics a generated artefact.

    We deliberately scan suffixes / infixes rather than running a regex
    per call — keeps the hot path branch-predictable and avoids the
    ``re`` import for what is a tiny finite enumeration.
    """
    # protobuf
    if name.endswith("_pb2.py") or name.endswith("_pb.go"):
        return True
    # ``.gen.<ext>`` and ``_gen.<ext>`` (wire_gen.go, service.gen.ts)
    if ".gen." in name or name.endswith("_gen.go") or name.endswith("_gen.py"):
        return True
    # ``.generated.<ext>`` and ``_generated.<ext>``
    return ".generated." in name or "_generated." in name


def _is_config_filename(name: str) -> bool:
    """Return True for config files that are *not* in the lock family."""
    if name in _CONFIG_EXACT_NAMES:
        return True
    if _is_lock_filename(name):
        # ``Cargo.lock`` ends ``.lock`` — never treat lock as config.
        return False
    suffix = Path(name).suffix
    return suffix in _CONFIG_SUFFIXES


def _is_code_filename(name: str) -> bool:
    """Return True when the extension belongs to the supported code stacks."""
    return Path(name).suffix in _CODE_EXTENSIONS


def _read_head_lines(path: Path, *, limit: int) -> list[str] | None:
    """Read up to ``limit`` lines from ``path``; return None on read failure.

    Failure is silent on purpose — classification must never raise on a
    missing or unreadable file (per spec: "when file does not exist on
    disk, still classify based on path heuristics"). Binary files trip
    ``UnicodeDecodeError``; we catch it and treat the file as opaque so
    rule 8 wins downstream.
    """
    try:
        with path.open("r", encoding="utf-8", errors="strict") as handle:
            lines: list[str] = []
            for index, raw in enumerate(handle):
                if index >= limit:
                    break
                lines.append(raw)
            return lines
    except (OSError, UnicodeDecodeError):
        return None


def _has_sentinel(lines: list[str]) -> bool:
    """Return True when any line carries the AUTO-GENERATED banner."""
    return any(_SENTINEL_TOKEN in line for line in lines)


def _has_manual_edit_marker(lines: list[str]) -> bool:
    """Return True when any line carries a MANUAL EDIT comment."""
    for line in lines:
        for token in _MANUAL_EDIT_TOKENS:
            if token in line:
                return True
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_conflict(path: Path | str, content: str | None = None) -> Classification:
    """Classify a single conflict path.

    Parameters
    ----------
    path:
        Path to the conflicted file. May be missing on disk — path-only
        heuristics still fire.
    content:
        Pre-loaded file body. When supplied we skip the file read; this
        keeps the function testable from in-memory strings and lets the
        caller pass the *theirs* / *ours* side of a 3-way merge.

    Returns
    -------
    Classification
        Immutable record describing the resolution posture for ``path``.

    Notes
    -----
    The function never writes resolutions and never raises on missing
    files — it falls back to the conservative ``(UNKNOWN, ambiguous,
    low)`` verdict per spec-129 §Risks.
    """
    path = Path(path) if not isinstance(path, Path) else path
    name = path.name

    # Rule 1 — migration paths win unconditionally.
    if _is_migration_path(path):
        return Classification(
            type=ConflictType.MIGRATION,
            action="ambiguous",
            confidence="high",
            reason="migration path detected",
        )

    # Lazy line-buffer so content rules pay for at most one read.
    head_lines: list[str] | None = None

    def _ensure_lines(limit: int) -> list[str] | None:
        nonlocal head_lines
        if content is not None:
            if head_lines is None or len(head_lines) < limit:
                head_lines = content.splitlines()[:limit]
            return head_lines
        if head_lines is None or len(head_lines) < limit:
            head_lines = _read_head_lines(path, limit=limit)
        return head_lines

    lock_filename = _is_lock_filename(name)

    # Rules 2 & 3 — lock files: manual-edit body wins over the
    # vanilla auto-resolve verdict.
    if lock_filename:
        manual_lines = _ensure_lines(_MANUAL_EDIT_SCAN_LINES) or []
        if _has_manual_edit_marker(manual_lines):
            return Classification(
                type=ConflictType.LOCK,
                action="ambiguous",
                confidence="low",
                reason="lock file has manual edits",
            )
        return Classification(
            type=ConflictType.LOCK,
            action="auto-resolve",
            confidence="high",
            reason="vanilla lock file",
        )

    # Rule 4 — sentinel-bearing files auto-resolve regardless of name.
    sentinel_lines = _ensure_lines(_SENTINEL_SCAN_LINES) or []
    if _has_sentinel(sentinel_lines):
        return Classification(
            type=ConflictType.GENERATED,
            action="auto-resolve",
            confidence="high",
            reason="sentinel detected",
        )

    # Rule 5 — filename mimics generated but body has no sentinel.
    # This is the deliberate "filename alone is not enough" case.
    if _looks_generated_filename(name):
        return Classification(
            type=ConflictType.UNKNOWN,
            action="ambiguous",
            confidence="low",
            reason="filename suggests generated but no sentinel",
        )

    # Rule 6 — config files. Order matters: a code-extension config
    # (e.g. ``conftest.py``) would never reach here because rule 7
    # below uses ``.py``; the config check sees ``pyproject.toml`` and
    # the ``.toml`` / ``.json`` / ``.yaml`` suffix families.
    if _is_config_filename(name):
        return Classification(
            type=ConflictType.CONFIG,
            action="ambiguous",
            confidence="medium",
            reason="config file — three-way merge possible",
        )

    # Rule 7 — plain code in any supported stack.
    if _is_code_filename(name):
        return Classification(
            type=ConflictType.CODE,
            action="manual",
            confidence="high",
            reason="plain code conflict — needs review",
        )

    # Rule 8 — conservative fallback.
    return Classification(
        type=ConflictType.UNKNOWN,
        action="ambiguous",
        confidence="low",
        reason="no clear classification",
    )


# ---------------------------------------------------------------------------
# CLI entry point — ``python resolve_classify.py <path>``
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Tiny CLI wrapper so ops can spot-check a path from the shell.

    Prints a single JSON object to stdout and returns ``0`` on success.
    Returns ``2`` on argument errors so shell pipelines can distinguish
    "no input" from "classification succeeded".
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: resolve_classify.py <path>", file=sys.stderr)
        return 2
    target = Path(args[0])
    result = classify_conflict(target)
    payload = {
        "type": result.type.value,
        "action": result.action,
        "confidence": result.confidence,
        "reason": result.reason,
    }
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - thin shim
    raise SystemExit(main())
