"""Hash-chained audit trail verifier (spec-107 D-107-10 / G-12, H2).

Layers a tamper-evident chain over ``framework-events.ndjson`` and
``decision-store.json``. Each entry adds an optional ``prev_event_hash``
field carrying the SHA256 of the prior entry's canonical-JSON payload
(excluding the field itself). This module ships:

* :func:`compute_entry_hash` -- canonical-JSON SHA256 of an entry payload,
  excluding the ``prev_event_hash`` field itself so that hashing is
  round-trip stable.
* :class:`AuditChainVerdict` -- dataclass returned by the walker.
* :func:`verify_audit_chain` -- walks an ndjson or json-array file in
  order and validates each entry's ``prev_event_hash`` against the
  computed hash of the prior entry. Reports the first break index +
  reason on mismatch.

Decision protocol (D-107-10):

* Empty file -> verdict ok=True (vacuously valid).
* Single entry -> verdict ok=True (no chain to verify yet).
* Linear chain with each ``prev_event_hash`` matching SHA256 of prior
  payload -> verdict ok=True.
* Mid-chain mutation, truncation, or append-injection -> verdict
  ok=False with the first break index + a human-readable reason.
* Legacy entries lacking ``prev_event_hash`` field entirely -> verdict
  ok=True (additive backward-compat per D-107-10).

Backward-compat: the chain is *additive*. Pre-spec-107 entries do not
carry ``prev_event_hash`` at all; the verifier treats those as legacy
and does not flag them as broken.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Field name carrying the chain pointer in canonical-JSON entries.
_CHAIN_FIELD = "prev_event_hash"

# Aliased camelCase variant used by Pydantic models when ``by_alias=True``.
_CHAIN_FIELD_ALIAS = "prevEventHash"


@dataclass(frozen=True)
class AuditChainVerdict:
    """Outcome of :func:`verify_audit_chain` over an audit file.

    Attributes
    ----------
    ok:
        ``True`` when the chain is intact (or the file is vacuously
        valid: empty, single legacy entry, all-legacy entries).
    entries_checked:
        Number of entries the walker processed before stopping.
    first_break_index:
        Zero-based index of the first entry whose ``prev_event_hash``
        did not match the computed hash of the prior entry. ``None``
        when ``ok`` is ``True``.
    first_break_reason:
        Human-readable description of the break (mismatch, missing
        prior, malformed JSON, etc.). ``None`` when ``ok`` is ``True``.
    """

    ok: bool
    entries_checked: int
    first_break_index: int | None
    first_break_reason: str | None


def _strip_chain_field(entry: dict) -> dict:
    """Return a copy of ``entry`` with the chain pointer fields removed.

    Removes both the canonical ``prev_event_hash`` and the camelCase
    alias ``prevEventHash`` so that a Pydantic ``by_alias=True`` dump
    and a hand-built ndjson line yield the same hash.
    """
    return {k: v for k, v in entry.items() if k not in (_CHAIN_FIELD, _CHAIN_FIELD_ALIAS)}


def compute_entry_hash(entry: dict) -> str:
    """Compute the canonical-JSON SHA256 of ``entry``.

    The chain pointer fields (``prev_event_hash`` and its camelCase
    alias) are stripped before hashing so that round-tripping a chain
    pointer through the entry is stable.

    Args:
        entry: Mapping payload of a single audit-chain entry.

    Returns:
        Hex-encoded SHA256 of the canonical-JSON payload (sorted keys,
        compact separators, UTF-8 encoded).
    """
    stripped = _strip_chain_field(entry)
    canonical = json.dumps(stripped, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_entries(
    file_path: Path,
    mode: Literal["ndjson", "json_array"],
) -> tuple[list[dict] | None, str | None]:
    """Load entries from ``file_path`` according to ``mode``.

    Returns
    -------
    tuple
        ``(entries, error_reason)`` where ``entries`` is the parsed list
        or ``None`` on parse failure, and ``error_reason`` is the
        human-readable failure reason (``None`` on success).
    """
    if not file_path.exists():
        return [], None
    text = file_path.read_text(encoding="utf-8").strip()
    if not text:
        return [], None

    if mode == "ndjson":
        entries: list[dict] = []
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                entry = json.loads(stripped)
            except json.JSONDecodeError as exc:
                return None, f"line {lineno}: malformed JSON: {exc.msg}"
            if not isinstance(entry, dict):
                return None, f"line {lineno}: entry is not a JSON object"
            entries.append(entry)
        return entries, None

    # json_array mode (decision-store style: top-level dict with a
    # ``decisions`` array).
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"malformed JSON: {exc.msg}"

    if isinstance(payload, list):
        candidate = payload
    elif isinstance(payload, dict):
        candidate = payload.get("decisions") or payload.get("entries") or []
    else:
        return None, "json_array mode expected a list or an object with a 'decisions' key"

    if not isinstance(candidate, list):
        return None, "json_array mode expected an array of entries"
    for idx, entry in enumerate(candidate):
        if not isinstance(entry, dict):
            return None, f"entry {idx}: not a JSON object"
    return list(candidate), None


def verify_audit_chain(
    file_path: Path,
    mode: Literal["ndjson", "json_array"] = "ndjson",
) -> AuditChainVerdict:
    """Walk ``file_path`` and verify the hash chain.

    Args:
        file_path: Path to the audit file (ndjson or json-array).
        mode: ``"ndjson"`` for line-delimited JSON streams (events log)
            or ``"json_array"`` for decision-store-style payloads.

    Returns:
        :class:`AuditChainVerdict` describing the outcome.
    """
    entries, parse_error = _load_entries(file_path, mode)
    if entries is None:
        return AuditChainVerdict(
            ok=False,
            entries_checked=0,
            first_break_index=0,
            first_break_reason=parse_error or "unparseable audit file",
        )

    if not entries:
        return AuditChainVerdict(
            ok=True,
            entries_checked=0,
            first_break_index=None,
            first_break_reason=None,
        )

    prior_hash: str | None = None
    for index, entry in enumerate(entries):
        # Locate the chain pointer (canonical or alias). Missing field is
        # legacy backward-compat -- treat as valid and refresh prior hash
        # to the current entry so subsequent entries can still chain on
        # if they carry the field.
        if _CHAIN_FIELD in entry:
            declared = entry[_CHAIN_FIELD]
        elif _CHAIN_FIELD_ALIAS in entry:
            declared = entry[_CHAIN_FIELD_ALIAS]
        else:
            declared = None
            prior_hash = compute_entry_hash(entry)
            continue

        if index == 0:
            if declared is not None:
                # First entry must declare prev_event_hash=None to
                # establish a chain anchor. A non-null first pointer is
                # forensic evidence of a head-truncation.
                return AuditChainVerdict(
                    ok=False,
                    entries_checked=index + 1,
                    first_break_index=index,
                    first_break_reason=(
                        "first entry has non-null prev_event_hash; possible head truncation"
                    ),
                )
            prior_hash = compute_entry_hash(entry)
            continue

        if declared != prior_hash:
            return AuditChainVerdict(
                ok=False,
                entries_checked=index + 1,
                first_break_index=index,
                first_break_reason=(
                    f"prev_event_hash mismatch at entry {index}: "
                    f"declared={declared!r}, expected={prior_hash!r}"
                ),
            )
        prior_hash = compute_entry_hash(entry)

    return AuditChainVerdict(
        ok=True,
        entries_checked=len(entries),
        first_break_index=None,
        first_break_reason=None,
    )


__all__ = [
    "AuditChainVerdict",
    "compute_entry_hash",
    "verify_audit_chain",
]
