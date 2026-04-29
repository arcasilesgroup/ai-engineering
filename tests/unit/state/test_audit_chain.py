"""RED-phase failing tests for spec-110 Phase 3 audit_chain extensions.

Spec-110 (governance v3 harvest) extends ``state/audit_chain.py`` with two
new public APIs and a dual-read reader:

* :func:`compute_event_hash(event_dict: dict) -> str` -- canonical-JSON
  SHA-256 of an event payload, deterministic across key ordering.
* :func:`iter_validate_chain(path: Path) -> Iterator[ValidationResult]` --
  streams an NDJSON audit file and yields per-event validation outcomes
  (:class:`ValidationResult` dataclass with at minimum a boolean ``valid``
  attribute and forensic context).
* Reader dual-read: when an event carries ``prev_event_hash`` *only* under
  ``detail.prev_event_hash`` (legacy location, pre-spec-110), the reader
  must still surface the value AND emit a warning log per D-110-03 with
  the substring "legacy" in the message; the value remains readable for
  the 30-day grace window.

These RED tests are written first per TDD discipline (T-3.1 of plan-110).
They MUST fail today because the new APIs do not exist yet -- T-3.2
(``compute_event_hash``), T-3.3 (``iter_validate_chain`` +
``ValidationResult``) and T-3.4 (dual-read warning) introduce them.

Existing API in ``state/audit_chain.py`` (kept intact):
  * ``compute_entry_hash(entry: dict) -> str``
  * ``verify_audit_chain(file_path: Path, mode='ndjson') -> AuditChainVerdict``

The new ``compute_event_hash`` is intentionally a sibling of
``compute_entry_hash`` named for the spec-110 vocabulary (events vs
entries) and may be implemented as an alias or a fresh function -- the
contract here only asserts behavior, not internal wiring.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers shared by tests below.
# ---------------------------------------------------------------------------


def _canonical_sha256(payload: dict) -> str:
    """Reference canonical-JSON SHA-256 hash of ``payload``.

    Mirrors the contract expected of :func:`compute_event_hash`: sort keys,
    compact separators, UTF-8 bytes. Used by the chain-tampering fixtures
    so the tests construct their own valid chains independent of the SUT.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _build_chain(events: list[dict]) -> list[dict]:
    """Stitch ``events`` into a hash-chained NDJSON-ready list.

    Each event after the first gets its ``prev_event_hash`` set to the
    canonical hash of the *prior* event payload (excluding any pre-set
    ``prev_event_hash`` field on that prior entry, mirroring the
    audit_chain rule that the chain pointer is excluded from its own
    canonical-JSON hash).
    """
    chained: list[dict] = []
    prior_hash: str | None = None
    for event in events:
        # Strip any caller-supplied chain pointer so we control it.
        bare = {k: v for k, v in event.items() if k != "prev_event_hash"}
        chained_event = dict(bare)
        chained_event["prev_event_hash"] = prior_hash
        chained.append(chained_event)
        # Hash for *next* iteration is the canonical SHA-256 of the
        # event sans its chain pointer -- consistent with the existing
        # ``compute_entry_hash`` semantics.
        prior_hash = _canonical_sha256(bare)
    return chained


def _write_ndjson(path: Path, entries: list[dict]) -> None:
    """Write one JSON object per line at ``path`` (ndjson encoding)."""
    path.write_text(
        "\n".join(json.dumps(entry, sort_keys=True) for entry in entries) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# T-3.1.a -- compute_event_hash canonical serialization (deterministic)
# ---------------------------------------------------------------------------


def test_compute_event_hash_canonical_serialization() -> None:
    """Same logical event -> same hash regardless of key insertion order.

    The SUT must perform canonical JSON encoding (sorted keys, compact
    separators) before hashing so that a Python dict re-keyed during
    serialization (e.g. via Pydantic ``model_dump`` ordering or a manual
    rebuild) hashes identically. This is the foundation of the chain --
    if the hash were order-sensitive, every reader would have to mirror
    the writer's exact key insertion path, which is brittle.
    """
    from ai_engineering.state.audit_chain import compute_event_hash

    event_a = {
        "id": "ev-1",
        "kind": "control_outcome",
        "ts": "2026-04-29T00:00:00Z",
        "detail": {"foo": "bar", "alpha": 1},
    }
    # Same logical content, opposite key insertion order at every level.
    event_b = {
        "detail": {"alpha": 1, "foo": "bar"},
        "ts": "2026-04-29T00:00:00Z",
        "kind": "control_outcome",
        "id": "ev-1",
    }

    hash_a = compute_event_hash(event_a)
    hash_b = compute_event_hash(event_b)

    # Determinism: identical content yields identical hash.
    assert hash_a == hash_b, (
        "compute_event_hash must be canonical (sorted keys); got "
        f"hash_a={hash_a!r} != hash_b={hash_b!r}"
    )
    # Shape: hex-encoded SHA-256 = 64 hex chars.
    assert isinstance(hash_a, str)
    assert len(hash_a) == 64
    assert all(ch in "0123456789abcdef" for ch in hash_a)


# ---------------------------------------------------------------------------
# T-3.1.b -- iter_validate_chain detects mid-chain tampering
# ---------------------------------------------------------------------------


def test_iter_validate_chain_detects_tampering(tmp_path: Path) -> None:
    """Mutated middle event -> at least one ValidationResult is invalid.

    Construct a valid 3-event hash chain on disk, then rewrite the
    middle event's ``detail.foo`` value (leaving its ``prev_event_hash``
    pointer untouched). The third event's pointer now references the
    SHA-256 of the *original* second event but the file holds the
    *mutated* second event; the streaming validator must flag this gap.
    """
    from ai_engineering.state.audit_chain import iter_validate_chain

    base = [
        {"id": "ev-1", "kind": "control_outcome", "detail": {"foo": "bar"}},
        {"id": "ev-2", "kind": "control_outcome", "detail": {"foo": "baz"}},
        {"id": "ev-3", "kind": "control_outcome", "detail": {"foo": "qux"}},
    ]
    chained = _build_chain(base)
    chain_path = tmp_path / "framework-events.ndjson"
    _write_ndjson(chain_path, chained)

    # Tamper: reload, mutate the middle event's payload (keep its chain
    # pointer so the break is *between* event 2 and event 3 -- event 3
    # still claims to follow the *original* event 2).
    lines = chain_path.read_text(encoding="utf-8").strip().splitlines()
    event_two = json.loads(lines[1])
    event_two["detail"]["foo"] = "TAMPERED"
    lines[1] = json.dumps(event_two, sort_keys=True)
    chain_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    results = list(iter_validate_chain(chain_path))

    # At least one ValidationResult must report invalid; in a 3-event
    # chain the failure surfaces no later than the third entry's check.
    assert results, "iter_validate_chain yielded no results for a 3-entry chain"
    invalid_results = [r for r in results if not getattr(r, "valid", True)]
    assert invalid_results, (
        f"iter_validate_chain failed to detect mid-chain tampering; got results={results!r}"
    )


# ---------------------------------------------------------------------------
# T-3.1.c -- iter_validate_chain detects missing (gapped) events
# ---------------------------------------------------------------------------


def test_iter_validate_chain_detects_missing_event(tmp_path: Path) -> None:
    """Removed middle event -> chain gap -> invalid ValidationResult.

    Build a valid 3-entry chain, then delete the middle line. Event 3's
    ``prev_event_hash`` still points at event 2's hash, but the file now
    contains only events 1 and 3 in sequence -- event 3's declared
    pointer no longer matches event 1's computed hash, so the validator
    must flag the gap.
    """
    from ai_engineering.state.audit_chain import iter_validate_chain

    base = [
        {"id": "ev-1", "kind": "control_outcome", "detail": {"step": 1}},
        {"id": "ev-2", "kind": "control_outcome", "detail": {"step": 2}},
        {"id": "ev-3", "kind": "control_outcome", "detail": {"step": 3}},
    ]
    chained = _build_chain(base)
    chain_path = tmp_path / "framework-events.ndjson"
    _write_ndjson(chain_path, chained)

    # Drop the middle line entirely -- chain becomes [ev-1, ev-3].
    lines = chain_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3, "fixture must start with 3 entries"
    del lines[1]
    chain_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    results = list(iter_validate_chain(chain_path))

    assert results, "iter_validate_chain yielded no results for a gapped chain"
    invalid_results = [r for r in results if not getattr(r, "valid", True)]
    assert invalid_results, (
        f"iter_validate_chain failed to detect missing-event gap; got results={results!r}"
    )


# ---------------------------------------------------------------------------
# T-3.1.d -- dual-read of legacy `detail.prev_event_hash` warns + reads
# ---------------------------------------------------------------------------


def test_dual_read_legacy_emits_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Legacy ``detail.prev_event_hash`` is read AND emits a warning.

    Per D-110-03 the writer migrates to root-level ``prev_event_hash``
    while the reader keeps a 30-day dual-read window. When an event
    arrives with the chain pointer only under ``detail.prev_event_hash``,
    the reader must:

    1. Still surface the value (so chain validation continues to work
       across the migration boundary).
    2. Emit a ``logger.warning`` whose message contains the substring
       ``"legacy"`` so operators see migration nags.

    This test exercises behavior, not call-site -- the reader function
    under test is :func:`iter_validate_chain` because it is the new
    streaming reader introduced in T-3.3 and the natural surface for
    T-3.4's dual-read logic.
    """
    from ai_engineering.state.audit_chain import iter_validate_chain

    # Anchor event (no prev pointer needed; first entry establishes the
    # chain). Use root-level None so the reader sees a normal anchor.
    anchor = {"id": "ev-1", "kind": "control_outcome", "prev_event_hash": None}
    anchor_hash = _canonical_sha256({k: v for k, v in anchor.items() if k != "prev_event_hash"})
    # Legacy follow-up event -- chain pointer lives ONLY in detail.
    legacy_followup = {
        "id": "ev-2",
        "kind": "control_outcome",
        "detail": {"foo": "bar", "prev_event_hash": anchor_hash},
    }

    chain_path = tmp_path / "framework-events.ndjson"
    _write_ndjson(chain_path, [anchor, legacy_followup])

    with caplog.at_level(logging.WARNING, logger="ai_engineering.state.audit_chain"):
        results = list(iter_validate_chain(chain_path))

    # Behavioral contract: the legacy pointer was read and consumed
    # (the chain validates because detail.prev_event_hash matches the
    # anchor's hash). At minimum a result for ev-2 must exist.
    assert len(results) >= 2, (
        "iter_validate_chain dropped events when reading legacy detail.prev_event_hash; "
        f"got {len(results)} result(s)"
    )

    # Logging contract: at least one WARNING record from the audit_chain
    # logger contains the substring "legacy" (case-insensitive).
    warning_records = [
        r
        for r in caplog.records
        if r.levelno >= logging.WARNING and "legacy" in r.getMessage().lower()
    ]
    assert warning_records, (
        "dual-read path did not emit a warning containing 'legacy'; "
        f"records seen: {[(r.name, r.levelname, r.getMessage()) for r in caplog.records]!r}"
    )
