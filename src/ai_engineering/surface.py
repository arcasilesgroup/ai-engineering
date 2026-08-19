"""Three questions about a surface, and three receipts that answer one each.

The defect this exists to cure was measured: the product answered "can it see the skills",
"can somebody run one" and "has a denial ever executed" with a single word per row, and
those answers routinely differ. A surface can list the skills and be unable to run them. It
can run them and never be able to stop anything.

So a state is read from its own receipt and speaks for nothing else. A missing receipt is
unproven for that state alone. A receipt naming another surface, or another state, ticks
nothing. And a surface that cannot deny reports enforcement as not applicable rather than
as a gap somebody might one day close — while a denial receipt handed to such a surface is
refused rather than believed, because that receipt is a claim the surface cannot make.

**Where a surface has an adapter, the receipt is measured against it.** The adapter declares
the exact receipt id an enforcement proof must carry, and a receipt naming anything else is
INCOMPLETE — including one written under a superseded adapter, because a version bump moves
that id with it. So on those surfaces a PASS means "this ran the thing we require".

**Where a surface has no adapter yet, it does not.** There the id is the one this module
composes, and a PASS still means only "this ran and said so". The two are different claims
and this file will not print the same word for both without saying which it had.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache
from pathlib import Path

from ai_engineering import evidence, outcome
from ai_engineering.readiness import _anchored, _object, _read, _Unreadable

RECEIPTS = ".ai/receipts/surface"
STATES = ("discovery", "invocation", "enforcement")


def _declared() -> tuple[str, ...]:
    """The surfaces, from the one file that decides which ones get installed.

    This was a second copy of the list, and the ids were written out four times in all:
    here, `policy/surfaces.toml`, the adapter schema's enum, and a test. Only the schema
    and the test were tied to each other; nothing tied either to the wiring table. A ninth
    surface added to the table would have left three copies behind, and the module that
    reports coverage would have carried on reporting eight.

    CONSTITUTION.md's Never list opens with "never create mirrors of guards, skills,
    templates or policy homes". This was that rule broken about the product's own data."""

    from ai_engineering import wiring

    return tuple(row["id"] for row in wiring.table()["surface"])


# Frozen by spec 010. `pi` and `zed` are instruction-only until a native hook exists, which
# is a fact about those editors and not a shortfall in this product.
SURFACES: tuple[str, ...] = _declared()
INSTRUCTION_ONLY = frozenset({"pi", "zed"})

RECEIPT_MISSING = "SURFACE_RECEIPT_MISSING"
RECEIPT_UNREADABLE = "SURFACE_RECEIPT_UNREADABLE"
RECEIPT_MALFORMED = "SURFACE_RECEIPT_MALFORMED"
RECEIPT_MISMATCH = "SURFACE_RECEIPT_MISMATCH"
RECEIPT_STALE = "SURFACE_RECEIPT_STALE"
EXECUTED_FAIL = "SURFACE_EXECUTED_FAIL"
WARNED = "SURFACE_PROVEN_WITH_WARNING"
REFUSED_EXCUSE = "SURFACE_NOT_APPLICABLE_REFUSED"
NOT_APPLICABLE = "SURFACE_ENFORCEMENT_NOT_APPLICABLE"
CANNOT_ENFORCE = "SURFACE_CANNOT_ENFORCE"
PROVEN = "SURFACE_PROVEN"

# The same ceiling the production-ready boxes use, and for the same reason: a proof older
# than a month has stopped describing the thing as it is now.
MAX_AGE_CEILING = 2_678_400
_SEVERITY = {"PASS": 0, "WARN": 1, "INCOMPLETE": 2, "FAIL": 3}


@dataclass(frozen=True, slots=True)
class Standing:
    """What one surface is proven to do in one of the three states."""

    surface: str
    state: str
    outcome: str
    code: str
    age_seconds: int | None

    def as_dict(self) -> dict[str, object]:
        return {
            "surface": self.surface,
            "state": self.state,
            "outcome": self.outcome,
            "code": self.code,
            "age_seconds": self.age_seconds,
        }


@dataclass(frozen=True, slots=True)
class Report:
    """Every surface in every state, and the worst of them."""

    result: outcome.Result
    rows: tuple[Standing, ...]

    def state(self, surface: str, state: str) -> Standing:
        for row in self.rows:
            if row.surface == surface and row.state == state:
                return row
        raise KeyError(f"{surface}.{state} is not one of the states this reads")

    def as_dict(self) -> dict[str, object]:
        return {"result": self.result.as_dict(), "rows": [row.as_dict() for row in self.rows]}


@cache
def _shaped() -> evidence._SchemaValidator:
    """The canonical check-evidence schema, read once and reused.

    This module deliberately does not bind a receipt to a requirement — that arrives with
    each surface's adapter. It does insist the file is a receipt, and the schema is what
    knows what that means."""

    return evidence._SchemaValidator(evidence.intent._json(evidence.SCHEMA_PATH.read_bytes()))


def _finished(record: dict[str, object], now: datetime) -> int | None:
    try:
        stamp = record["finished_at"]
        parsed = datetime.fromisoformat(str(stamp).removesuffix("Z") + "+00:00")
    except (KeyError, TypeError, ValueError):
        return None
    return None if parsed > now else int((now - parsed).total_seconds())


ADAPTERS = "adapters"


@cache
def adapter_proof(surface: str) -> str:
    """The receipt id this surface's adapter requires, or "" where no adapter exists.

    Read from `policy/adapters/<surface>.adapter.json`, which is data and not code, and
    cached because a report reads twenty-four rows and the answer cannot change inside one
    run. An adapter that cannot be parsed answers "" — the receipt then has to satisfy this
    module's own convention, which is the weaker claim and is reported as such rather than
    as a missing adapter nobody mentioned.
    """

    import json

    from ai_engineering import paths

    try:
        found = paths.policy(ADAPTERS) / f"{surface}.adapter.json"
        if not found.is_file():
            return ""
        declared = json.loads(found.read_text(encoding="utf-8"))
        return str(declared.get("proof", {}).get("receipt_id", ""))
    except (OSError, ValueError, TypeError, AttributeError):
        return ""


def receipt_binds_version(declared: dict) -> str:
    """Whether this adapter's receipt id moves when its denial protocol does.

    The schema decided how an enforcement receipt is bound to the adapter version and the
    denial protocol, and it chose not to add two fields — a second source of truth beside
    `receipt_id` is the EP-300 defect arriving again. It made the id itself move: "when a
    superseding version of this adapter changes what a denial looks like, this id moves with
    it and every receipt written under the old one stops proving anything."

    That was a sentence in a description and nothing read it. An adapter could go to version
    2, keep `claude-code.enforcement`, and every receipt earned against version 1's denial
    would carry on vouching for a protocol that had changed underneath it.

    Version 1 needs nothing in the id, because there is no earlier protocol for a receipt to
    have been earned against. Every version after it does. Returns the problem, or "" when
    there is none, so the caller decides what a problem costs.
    """

    version = str(declared.get("adapter_version", "")).strip()
    receipt_id = str((declared.get("proof") or {}).get("receipt_id", "")).strip()
    if not version or not receipt_id:
        return "the adapter declares no version or no receipt id, so nothing binds them"
    if version == "1" or version in receipt_id:
        return ""
    return (
        f"adapter version {version} keeps receipt id {receipt_id!r}: every receipt earned "
        f"under the previous denial protocol still proves this one"
    )


RECEIPT_FOREIGN = "SURFACE_RECEIPT_FOREIGN"


def adapter_identity(surface: str) -> dict[str, str]:
    """What a receipt for this surface must copy, and must not invent.

    `EP-147` asks a per-surface receipt to carry the surface id, the surface version, the
    adapter version and the deny protocol. Three of those four cannot go in a receipt at all,
    and finding out why is the useful half of measuring this row.

    `check-evidence-v1` has slots named `environment_id`, `protocol_id` and `protocol_version`
    — and forbids every one of them when `kind` is `automated`. They are the manual half of
    the schema: the person, the protocol they followed, the machine they used. Writing adapter
    facts into them would make an automated run read as a human protocol record, which is the
    schema stopping exactly the confusion it was closed to stop. The row recorded this as a
    schema with none of the fields; it is a schema that has them and refuses them here, which
    is a decision rather than a gap.

    What an automated receipt may carry is `tool_version`, and that is the adapter version.
    So that is what is compared, on the same principle `adapter_proof` applies to the id: the
    field is evidence because it is a requirement the receipt did not get to choose. The deny
    protocol now has a name in the adapter — `deny_protocol`, an identifier rather than the
    sentence in `translations.reply.deny` — and the report prints it beside the surface, which
    is the reachable half of what the requirement asked for.
    """

    import json

    from ai_engineering import paths

    try:
        found = paths.policy(ADAPTERS) / f"{surface}.adapter.json"
        if not found.is_file():
            return {}
        declared = json.loads(found.read_text(encoding="utf-8"))
        version = str(declared.get("adapter_version", ""))
        protocol = str(declared.get("deny_protocol", ""))
        if not version or not protocol:
            return {}
        return {"adapter_version": version, "deny_protocol": protocol}
    except (OSError, ValueError, TypeError, AttributeError):
        return {}


def _standing(root: Path, surface: str, state: str, now: datetime) -> Standing:
    def answer(status: str, code: str, age: int | None = None) -> Standing:
        return Standing(surface, state, status, code, age)

    enforcing = state == "enforcement" and surface in INSTRUCTION_ONLY
    try:
        raw = _read(_anchored(root, f"{RECEIPTS}/{surface}.{state}.json"))
    except _Unreadable:
        return answer("INCOMPLETE", RECEIPT_UNREADABLE)
    if raw is None:
        # Not applicable is an answer, and an answer is not a gap. It comes before the
        # missing-receipt one so a T3 surface never reads as something waiting to be proved.
        return (
            answer("PASS", NOT_APPLICABLE) if enforcing else answer("INCOMPLETE", RECEIPT_MISSING)
        )
    try:
        record = _object(raw)
    except (RecursionError, UnicodeDecodeError, ValueError):
        # RecursionError is in the list because a 60 KB file of nested objects sits well
        # inside the size bound and takes the whole report down with it: measured, `doctor`
        # aborted mid-run with a traceback and printed no terminal result at all.
        return answer("INCOMPLETE", RECEIPT_MALFORMED)

    # It has to be a check-evidence receipt before anything it says is worth reading, and
    # "a receipt" means the canonical schema says so — not a handful of keys this module
    # picked. The first attempt at this was four constants, and a re-review showed it moved
    # the cost of a forgery from typing four keys to typing eight in the same unreviewed
    # file. The schema is the thing that already knows what a receipt must carry: command,
    # tool version, both digests, both timestamps. Asking it is one line and closes the
    # class rather than the two examples.
    if not _shaped().valid(record) or record.get("kind") != "automated":
        return answer("INCOMPLETE", RECEIPT_MALFORMED)

    # A receipt that says the check does not apply is a receipt saying it did not run.
    # On a surface that cannot deny, that is the honest thing to write and it is accepted;
    # anywhere else it proves nothing, and it certainly does not prove a denial.
    if record.get("applicability") == "not_applicable":
        return (
            answer("PASS", NOT_APPLICABLE) if enforcing else answer("INCOMPLETE", RECEIPT_MISMATCH)
        )
    if enforcing:
        # Applicable, and on a surface that cannot deny: a claim it is not able to make.
        return answer("FAIL", CANNOT_ENFORCE)
    # The adapter's requirement where there is one, and this module's own convention where
    # there is not. The difference matters: the first is a requirement the receipt did not
    # write, which is the whole of what makes it evidence rather than a self-report.
    required = adapter_proof(surface) if state == "enforcement" else ""
    if record.get("id") != (required or f"{surface}.{state}"):
        return answer("INCOMPLETE", RECEIPT_MISMATCH)

    # And the three fields the adapter declares, where it declares them. A receipt carrying
    # a deny protocol its adapter does not is a receipt about some other surface, or about
    # this one under a protocol nobody reviewed; either way it is not proof of this adapter.
    # Absent is not the same as wrong: a receipt written before these fields existed is
    # incomplete rather than foreign, and the report says which.
    if state == "enforcement":
        declared = adapter_identity(surface)
        version = declared.get("adapter_version")
        # `tool_version` is free text by the schema, so what is checked is that it names the
        # version the adapter declares. A receipt written under adapter 1 and read after the
        # adapter moved to 2 is evidence about a protocol nobody is running any more.
        if version and version not in str(record.get("tool_version", "")):
            return answer("INCOMPLETE", RECEIPT_FOREIGN)

    age = _finished(record, now)
    if age is None:
        return answer("INCOMPLETE", RECEIPT_MALFORMED)
    window = record.get("max_age_seconds")
    if not isinstance(window, int) or isinstance(window, bool) or window < 1:
        return answer("INCOMPLETE", RECEIPT_MALFORMED)
    if age > min(window, MAX_AGE_CEILING):
        return answer("INCOMPLETE", RECEIPT_STALE, age)

    spoken = record.get("outcome")
    if spoken == "FAIL":
        return answer("FAIL", EXECUTED_FAIL, age)
    if spoken == "WARN":
        # A legal outcome the schema allows, and it was being called malformed. It is not
        # a pass and it is not a failure; it is the thing the vocabulary already has a word
        # for, and saying the wrong word about it teaches a reader the wrong vocabulary.
        return answer("WARN", WARNED, age)
    if spoken != "PASS":
        return answer("INCOMPLETE", RECEIPT_MALFORMED, age)
    return answer("PASS", PROVEN, age)


def read(root: Path, *, now: datetime) -> Report:
    """Every surface in every state, as of `now`."""

    if not isinstance(now, datetime) or now.utcoffset() != timedelta(0):
        return Report(outcome.result("INCOMPLETE"), ())
    now = now.astimezone(UTC)
    rows = tuple(_standing(root, surface, state, now) for surface in SURFACES for state in STATES)
    worst = max(rows, key=lambda row: _SEVERITY.get(row.outcome, _SEVERITY["INCOMPLETE"]))
    return Report(outcome.result(worst.outcome), rows)
