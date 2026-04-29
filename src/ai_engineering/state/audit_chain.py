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
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

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


def compute_event_hash(event_dict: dict) -> str:
    """Canonical-JSON SHA-256 of an audit event payload (spec-110).

    Spec-110 vocabulary aligns on "events" (writer + reader streaming
    surface) where the existing audit-chain code uses "entries". The
    hashing contract is identical: sorted keys, compact separators,
    UTF-8 bytes, with chain-pointer fields stripped before hashing so
    that round-tripping ``prev_event_hash`` through the payload is
    stable.

    This function is a thin wrapper over :func:`compute_entry_hash` --
    the underlying byte canonicalization is the same -- exposed under
    the spec-110 name so callers (writer migration, streaming reader)
    can use the vocabulary the spec adopted without coupling to the
    legacy "entry" name.

    Args:
        event_dict: Mapping payload of a single audit event.

    Returns:
        Hex-encoded SHA-256 (64 lowercase hex chars) of the canonical
        JSON payload (sorted keys, compact separators, UTF-8 encoded),
        with ``prev_event_hash`` and its camelCase alias stripped prior
        to hashing.
    """
    return compute_entry_hash(event_dict)


@dataclass(frozen=True)
class ValidationResult:
    """Per-event outcome from :func:`iter_validate_chain` (spec-110 D-110-03).

    The streaming validator yields one :class:`ValidationResult` per
    NDJSON event so callers can stop at the first break (forensic UX) or
    aggregate every break (audit reports). The dataclass is frozen so
    instances are hashable and safe to pass through async pipelines.

    Attributes
    ----------
    valid:
        ``True`` when the event's declared ``prev_event_hash`` matches
        the computed hash of the prior event (or this is the first
        event, which establishes the chain anchor).
    line:
        1-indexed line number in the source NDJSON file. ``0`` is
        reserved for synthetic results (e.g. unparseable file).
    event_id:
        Identifier extracted from the event payload (``id`` field), or
        ``None`` when absent. Useful for log forensics without leaking
        the full event detail into validator output.
    reason:
        Human-readable description of why the event is invalid. ``None``
        when ``valid`` is ``True``.
    expected_hash:
        Hash the validator computed for the prior event. ``None`` when
        ``valid`` is ``True`` or no prior event exists.
    actual_hash:
        Value the event declared in its ``prev_event_hash`` pointer.
        ``None`` when ``valid`` is ``True`` or the field was absent.
    """

    valid: bool
    line: int
    event_id: str | None
    reason: str | None
    expected_hash: str | None
    actual_hash: str | None


def _extract_chain_pointer(event: dict) -> tuple[str | None, bool, bool]:
    """Locate the ``prev_event_hash`` pointer on ``event``.

    Resolves the chain pointer in priority order:

    1. Root-level ``prev_event_hash`` (canonical, post-spec-110).
    2. Root-level ``prevEventHash`` (camelCase Pydantic alias).
    3. ``detail.prev_event_hash`` (legacy, pre-spec-110 dual-read).

    Returns
    -------
    tuple
        ``(declared, present, legacy)`` where ``declared`` is the value
        (may be ``None`` when the field is explicitly null), ``present``
        is ``True`` when any of the three locations carried the field,
        and ``legacy`` is ``True`` only when the value was sourced from
        ``detail.prev_event_hash`` (so callers can warn under D-110-03).
    """
    if _CHAIN_FIELD in event:
        return event[_CHAIN_FIELD], True, False
    if _CHAIN_FIELD_ALIAS in event:
        return event[_CHAIN_FIELD_ALIAS], True, False
    detail = event.get("detail")
    if isinstance(detail, dict) and _CHAIN_FIELD in detail:
        return detail[_CHAIN_FIELD], True, True
    return None, False, False


def iter_validate_chain(
    path: Path,
) -> Iterator[
    ValidationResult
]:  # audit:exempt:streaming-state-machine-anchor-legacy-mismatch-branches
    """Stream-validate a hash-chained NDJSON audit log (spec-110 D-110-03).

    Walks ``path`` line-by-line, computing :func:`compute_event_hash`
    for each event and comparing the next event's declared
    ``prev_event_hash`` against the computed hash. Yields one
    :class:`ValidationResult` per event so consumers can short-circuit
    on the first break or accumulate every break.

    Decision protocol:

    * Empty/missing file -> no results yielded.
    * Malformed JSON line -> single ``valid=False`` result with reason
      ``"malformed JSON"``; iteration stops.
    * First event (line 1) -> always ``valid=True``; establishes anchor.
    * Subsequent events -> compare declared pointer vs computed hash of
      prior event:
        - Match (or both ``None``) -> ``valid=True``.
        - Mismatch -> ``valid=False`` with ``reason="hash mismatch"``,
          ``expected_hash`` = computed prior hash, ``actual_hash`` =
          declared pointer.
    * Legacy ``detail.prev_event_hash`` -> value is read transparently
      (T-3.3 supports the read; T-3.4 emits the deprecation warning).

    Args:
        path: Path to the NDJSON audit log (one event per line).

    Yields:
        :class:`ValidationResult` per event, in file order.
    """
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return

    prior_hash: str | None = None
    prior_was_first = True
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError as exc:
            yield ValidationResult(
                valid=False,
                line=lineno,
                event_id=None,
                reason=f"malformed JSON: {exc.msg}",
                expected_hash=None,
                actual_hash=None,
            )
            return
        if not isinstance(event, dict):
            yield ValidationResult(
                valid=False,
                line=lineno,
                event_id=None,
                reason="event is not a JSON object",
                expected_hash=None,
                actual_hash=None,
            )
            return

        event_id = event.get("id") if isinstance(event.get("id"), str) else None
        declared, present, legacy = _extract_chain_pointer(event)
        if legacy:
            # ----------------------------------------------------------
            # SUNSET 2026-05-29 (spec-114 T-3.6 marker, spec-115 follow-up)
            # ----------------------------------------------------------
            # D-110-03 dual-read warning: the writer migrated to root-level
            # ``prev_event_hash`` but this event still carries the pointer
            # only under ``detail.prev_event_hash``. Surface a deprecation
            # nag so operators migrate before the 30-day grace window
            # closes (2026-05-29; spec-110 + 30 days from 2026-04-29).
            #
            # Sunset plan (spec-115 / `/ai-skill-sharpen` x49):
            #   - On 2026-05-29 (or after a clean ``ai-eng maintenance
            #     reset-events`` run -- whichever comes first) drop the
            #     ``legacy`` branch in :func:`_extract_chain_pointer` so
            #     ``detail.prev_event_hash`` is no longer read, and remove
            #     this warning + the marker that ``maintenance reset-events``
            #     scans for in NDJSON. After that point a single chain
            #     pointer location remains (root ``prev_event_hash``).
            #   - The exact substring "legacy hash location detected" is
            #     the same string that
            #     ``ai_engineering.cli_commands.maintenance._has_recent_legacy_reads``
            #     greps for in the NDJSON to gate ``reset-events``; both
            #     must be retired together.
            logger.warning(
                "legacy hash location detected at line %d, migrate by 2026-05-29",
                lineno,
            )

        if prior_was_first:
            # First event in the file establishes the chain anchor.
            # Any declared pointer is informational only -- a non-null
            # head pointer is still legal in a sub-chain dump (e.g. a
            # tail slice for forensic review). We do not flag here.
            yield ValidationResult(
                valid=True,
                line=lineno,
                event_id=event_id,
                reason=None,
                expected_hash=None,
                actual_hash=declared if present else None,
            )
            prior_hash = compute_event_hash(event)
            prior_was_first = False
            continue

        if declared == prior_hash:
            yield ValidationResult(
                valid=True,
                line=lineno,
                event_id=event_id,
                reason=None,
                expected_hash=prior_hash,
                actual_hash=declared,
            )
        else:
            yield ValidationResult(
                valid=False,
                line=lineno,
                event_id=event_id,
                reason="hash mismatch",
                expected_hash=prior_hash,
                actual_hash=declared,
            )
        prior_hash = compute_event_hash(event)


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


def verify_audit_chain(  # audit:exempt:hash-chain-walker-head-truncation-mismatch-branches
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
    "ValidationResult",
    "compute_entry_hash",
    "compute_event_hash",
    "iter_validate_chain",
    "verify_audit_chain",
]
