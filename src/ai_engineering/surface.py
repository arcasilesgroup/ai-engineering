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

**What this does not yet do**, said here rather than left to be discovered: it proves that
a receipt exists, names its own state, ran, and is fresh. It does not yet measure the
receipt against a requirement it did not write. That binding arrives with each surface's
adapter, which is where the command and the digests it must match first exist. Until then a
state that reads PASS means "this ran and said so", not "this ran the thing we require".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ai_engineering import outcome
from ai_engineering.readiness import _anchored, _object, _read, _Unreadable

RECEIPTS = ".ai/receipts/surface"
STATES = ("discovery", "invocation", "enforcement")

# Frozen by spec 010. `pi` and `zed` are instruction-only until a native hook exists, which
# is a fact about those editors and not a shortfall in this product.
SURFACES: tuple[str, ...] = (
    "claude-code",
    "opencode",
    "codex-cli",
    "cursor",
    "copilot-cli",
    "vscode-copilot",
    "pi",
    "zed",
)
INSTRUCTION_ONLY = frozenset({"pi", "zed"})

RECEIPT_MISSING = "SURFACE_RECEIPT_MISSING"
RECEIPT_UNREADABLE = "SURFACE_RECEIPT_UNREADABLE"
RECEIPT_MALFORMED = "SURFACE_RECEIPT_MALFORMED"
RECEIPT_MISMATCH = "SURFACE_RECEIPT_MISMATCH"
RECEIPT_STALE = "SURFACE_RECEIPT_STALE"
EXECUTED_FAIL = "SURFACE_EXECUTED_FAIL"
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


def _finished(record: dict[str, object], now: datetime) -> int | None:
    try:
        stamp = record["finished_at"]
        parsed = datetime.fromisoformat(str(stamp).removesuffix("Z") + "+00:00")
    except (KeyError, TypeError, ValueError):
        return None
    return None if parsed > now else int((now - parsed).total_seconds())


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
    except (UnicodeDecodeError, ValueError):
        return answer("INCOMPLETE", RECEIPT_MALFORMED)

    if enforcing:
        # A receipt exists claiming a denial executed on a surface that cannot deny. That is
        # decided and wrong, not unproven: believing it would hand the coverage screen its
        # first fabricated green.
        return answer("FAIL", CANNOT_ENFORCE)
    if record.get("id") != f"{surface}.{state}":
        return answer("INCOMPLETE", RECEIPT_MISMATCH)

    age = _finished(record, now)
    if age is None:
        return answer("INCOMPLETE", RECEIPT_MALFORMED)
    window = record.get("max_age_seconds")
    if not isinstance(window, int) or isinstance(window, bool) or window < 1:
        return answer("INCOMPLETE", RECEIPT_MALFORMED)
    if age > min(window, MAX_AGE_CEILING):
        return answer("INCOMPLETE", RECEIPT_STALE, age)

    if record.get("outcome") == "FAIL":
        return answer("FAIL", EXECUTED_FAIL, age)
    if record.get("outcome") != "PASS":
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
