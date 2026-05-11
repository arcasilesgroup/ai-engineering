"""Allowlist loader + DEC validator for ``no_suppression``.

The allowlist sits at ``.ai-engineering/suppression-allowlist.yml`` and
binds each accepted suppression to:

* ``path`` — a glob matching the file(s) carrying the suppression.
* ``rule`` — the bypassed analyser rule (``python:S5852``, ``S2083``, ...).
* ``pattern`` — the suppression marker family (``nosonar``, ``noqa``,
  ``sonar_multicriteria``, ...). Must match a ``rule_id`` emitted by
  :mod:`no_suppression.scanner`.
* ``justification`` — free-text reason. Required.
* ``spec_ref`` — owning spec / decision (``spec-128``, ``DEC-123``).
* ``expires_at`` — ISO-8601 expiry. Optional, but enforced when set.
* ``dec_id`` — optional foreign key into
  ``state.db::risk_acceptances``. When set, the gate confirms the DEC
  exists, is ``active``, and is not past its TTL.

A suppression that matches an allowlist entry passes the gate. A
suppression with no match — or a match against an expired / inactive
DEC — fails the gate.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from no_suppression.scanner import Finding

__all__ = (
    "DEFAULT_ALLOWLIST_PATH",
    "DEFAULT_STATE_DB_PATH",
    "AllowlistDecision",
    "AllowlistEntry",
    "evaluate",
    "load_allowlist",
)


DEFAULT_ALLOWLIST_PATH = Path(".ai-engineering") / "suppression-allowlist.yml"
DEFAULT_STATE_DB_PATH = Path(".ai-engineering") / "state" / "state.db"


@dataclass(frozen=True)
class AllowlistEntry:
    """A single allowlisted suppression with optional DEC binding."""

    path_glob: str
    rule_id: str
    pattern: str
    justification: str
    spec_ref: str
    expires_at: str = ""
    dec_id: str = ""
    severity: str = "low"


@dataclass(frozen=True)
class AllowlistDecision:
    """Outcome of joining one ``Finding`` against the allowlist."""

    finding: Finding
    status: str  # "allowed", "denied", "expired", "dec_missing"
    matched_entry: AllowlistEntry | None = None
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def load_allowlist(path: Path = DEFAULT_ALLOWLIST_PATH) -> list[AllowlistEntry]:
    """Load and validate the YAML allowlist. Missing file → empty list."""
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries_raw = raw.get("entries", [])
    if not isinstance(entries_raw, list):
        raise ValueError(
            f"allowlist {path} must contain a top-level 'entries' list, "
            f"got {type(entries_raw).__name__}"
        )
    entries: list[AllowlistEntry] = []
    for index, entry in enumerate(entries_raw):
        if not isinstance(entry, dict):
            raise ValueError(f"allowlist entry #{index} must be a mapping")
        required = ("path", "rule", "pattern", "justification", "spec_ref")
        missing = [field for field in required if not entry.get(field)]
        if missing:
            raise ValueError(f"allowlist entry #{index} missing required keys: {sorted(missing)}")
        entries.append(
            AllowlistEntry(
                path_glob=str(entry["path"]),
                rule_id=str(entry["rule"]),
                pattern=str(entry["pattern"]),
                justification=str(entry["justification"]),
                spec_ref=str(entry["spec_ref"]),
                expires_at=str(entry.get("expires_at", "")),
                dec_id=str(entry.get("dec_id", "")),
                severity=str(entry.get("severity", "low")),
            )
        )
    return entries


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    candidate = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _dec_status(state_db: Path, dec_id: str) -> tuple[str, str]:
    """Return ``(status, expires_at)`` for a DEC, or ``("missing", "")``."""
    if not state_db.exists():
        return ("missing", "")
    try:
        with sqlite3.connect(state_db) as conn:
            row = conn.execute(
                "SELECT status, expires_at FROM risk_acceptances WHERE risk_id = ?",
                (dec_id,),
            ).fetchone()
    except sqlite3.Error:
        return ("missing", "")
    if row is None:
        return ("missing", "")
    return (row[0] or "", row[1] or "")


def _file_matches(finding_path: Path, glob: str) -> bool:
    return finding_path.match(glob) or finding_path.as_posix() == glob


def _entry_matches(finding: Finding, entry: AllowlistEntry) -> bool:
    if entry.pattern != finding.rule_id:
        return False
    if not _file_matches(finding.path, entry.path_glob):
        return False
    # rule may be exact (``python:S5852``) or wildcard (``*``).
    if entry.rule_id != "*" and entry.rule_id != finding.rule_target:
        return False
    return True


def evaluate(
    findings: Iterable[Finding],
    entries: Iterable[AllowlistEntry],
    state_db: Path = DEFAULT_STATE_DB_PATH,
    now: datetime | None = None,
) -> list[AllowlistDecision]:
    """Join findings against allowlist; verify TTL + DEC for matches."""
    when = now or _now_utc()
    entries_list = list(entries)
    decisions: list[AllowlistDecision] = []
    for finding in findings:
        match = next((e for e in entries_list if _entry_matches(finding, e)), None)
        if match is None:
            decisions.append(
                AllowlistDecision(finding=finding, status="denied", reason="no allowlist entry")
            )
            continue
        expiry = _parse_iso(match.expires_at)
        if expiry is not None and expiry <= when:
            decisions.append(
                AllowlistDecision(
                    finding=finding,
                    status="expired",
                    matched_entry=match,
                    reason=f"allowlist entry expired at {match.expires_at}",
                )
            )
            continue
        if match.dec_id:
            dec_status, dec_expires = _dec_status(state_db, match.dec_id)
            if dec_status == "missing":
                decisions.append(
                    AllowlistDecision(
                        finding=finding,
                        status="dec_missing",
                        matched_entry=match,
                        reason=f"DEC {match.dec_id} not found in state.db",
                    )
                )
                continue
            if dec_status != "active":
                decisions.append(
                    AllowlistDecision(
                        finding=finding,
                        status="dec_missing",
                        matched_entry=match,
                        reason=f"DEC {match.dec_id} status={dec_status} (expected 'active')",
                    )
                )
                continue
            dec_expiry = _parse_iso(dec_expires)
            if dec_expiry is not None and dec_expiry <= when:
                decisions.append(
                    AllowlistDecision(
                        finding=finding,
                        status="expired",
                        matched_entry=match,
                        reason=f"DEC {match.dec_id} expired at {dec_expires}",
                    )
                )
                continue
        decisions.append(
            AllowlistDecision(
                finding=finding,
                status="allowed",
                matched_entry=match,
                reason="covered by allowlist",
            )
        )
    return decisions
