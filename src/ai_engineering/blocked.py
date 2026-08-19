"""What is waiting for a person, collected from records that already exist.

Specification 019 fixed the loop that spent four days on two specifications. It did not fix
the other half: a build that reaches something only a person can decide stops, and the person
finds out by reading a terminal transcript. This module is the half that was missing — one
list of what is stuck, so a stop is visible instead of silent.

Four fields, and the fourth is the one that cannot be faked. What is waiting, since when, why
it stopped, and a literal the reader can copy. The fourth is what separates this from a bug
tracker with worse ergonomics, which is the case specification 020 was challenged with: a row
whose only advice is "decide this" is not rendered at all, and the count says how many were
dropped so the filter cannot hide itself.

Nothing here grants anything. A row states that a gate was reached and what is missing; it
never records that the missing thing arrived.
"""

from __future__ import annotations

import hashlib
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

# The four, named once. Read by the collector, by the renderer and by the subcommand that
# writes a stop, so a fifth field cannot be added to one of them and forgotten in the others.
FIELDS = ("what", "since", "why", "action")

LEDGER = Path("docs") / "blocked.toml"


class Unreadable(Exception):
    """The record of what is stuck could not be read, so nothing about it is known."""


@dataclass(frozen=True)
class Row:
    """One thing waiting for a person.

    `kind` says which record it came from, because the four fields read the same whether the
    source is a halted run, an unapproved specification or an audited requirement, and a
    reader deciding what to do first needs to know which.
    """

    kind: str
    id: str
    what: str
    since: str
    why: str
    action: str


def _rows(entries: list[dict], kind: str) -> tuple[list[Row], list[str]]:
    """The whole rows and the ids of the ones that were dropped.

    Both halves in one pass and returned together. Counting the drops separately means two
    passes that can disagree, and a section whose "21 of 28" is computed from a different
    walk than its rows is a number that looks checked and is not.
    """

    whole: list[Row] = []
    dropped: list[str] = []
    for entry in entries:
        name = str(entry.get("id") or "")
        if all(str(entry.get(field) or "").strip() for field in FIELDS):
            whole.append(Row(kind=kind, id=name, **{f: str(entry[f]).strip() for f in FIELDS}))
        else:
            dropped.append(name)
    return whole, dropped


def stops(root: Path) -> tuple[list[Row], list[str]]:
    """Every halt a run recorded, and the ids of the halts that did not say enough.

    A tree that never halted has no ledger, and having nothing to say is the right answer
    rather than a missing file. A ledger that does not parse is the other direction and is
    refused: read as "nothing is stuck" it would render a green section over a tree nobody
    measured, which is the fail-open the page's tracked-file list already closed once.
    """

    where = root / LEDGER
    if not where.is_file():
        return [], []
    try:
        loaded = tomllib.loads(where.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as refused:
        raise Unreadable(f"{LEDGER.as_posix()} could not be read: {refused}") from refused
    return _rows(list(loaded.get("stop") or []), "halt")


# The vocabulary `docs/requirements.toml` uses for a row nothing more can be done about
# without a person. INCOMPLETE and NO-EVIDENCE are deliberately not here: they are work the
# build owes itself, and a section that listed all 165 of them would be the bug tracker
# specification 020 was challenged with and kept its scope to answer.
STUCK = ("BLOCKED", "CONTRADICTED")

_MEASURED = re.compile(r"^# Measured on (\d{4}-\d{2}-\d{2})", re.M)

# Stops first, then drafts, then verdicts. The question the section answers is what unsticks
# the build, not what is worst — an audited requirement that is unreachable by construction
# has been unreachable for months and will keep, and a run that halted an hour ago will not.
ORDER = ("halt", "draft", "verdict")


def _verdicts(root: Path) -> tuple[list[Row], list[str]]:
    """The audited rows nothing but a person can move.

    `subject` is what is waiting, `note` is why it stopped and `evidence` is the command that
    decides it — three of the four already written, by four auditors who had no idea they
    were filling this in. The fourth is the file's own measurement date, read from its header
    rather than pinned here: a header that stops saying when it was measured drops every row
    it holds, which is louder than a date this module made up.
    """

    where = root / "docs" / "requirements.toml"
    if not where.is_file():
        return [], []
    try:
        body = where.read_text(encoding="utf-8")
        loaded = tomllib.loads(body)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as refused:
        raise Unreadable(f"docs/requirements.toml could not be read: {refused}") from refused
    stamped = _MEASURED.search(body)
    since = stamped.group(1) if stamped else ""
    return _rows(
        [
            {
                "id": entry.get("id"),
                "what": entry.get("subject"),
                "since": since,
                "why": entry.get("note"),
                "action": entry.get("evidence"),
            }
            for entry in loaded.get("requirement") or []
            if entry.get("verdict") in STUCK
        ],
        "verdict",
    )


def _drafts(root: Path) -> tuple[list[Row], list[str]]:
    """The specifications that have everything they need except somebody saying yes.

    A draft with no plan is not here: it is waiting on the build. A draft with a plan has run
    out of things an agent may do on its own, and the digest in its action is of the file as
    it is on disk, so approving it cannot silently approve a later edit — which is the whole
    reason the block gate in 019 asked for digests in the first place.
    """

    entries = []
    for home in sorted((root / "specs").glob("*/spec.md")):
        raw = home.read_text(encoding="utf-8")
        parts = raw.split("---", 2)
        if len(parts) < 3:
            continue
        front = dict(
            (key.strip(), value.strip().strip('"'))
            for key, _, value in (line.partition(":") for line in parts[1].splitlines())
            if key.strip()
        )
        if front.get("status") != "draft":
            continue
        name = front.get("id") or home.parent.name.split("-", 1)[0]
        digest = hashlib.sha256(home.read_bytes()).hexdigest()
        entries.append(
            {
                "id": name,
                "what": f"specification {name} is drafted and nobody has approved it",
                "since": front.get("date"),
                "why": "an agent may write a specification and may not approve one",
                # Only when there is a plan. Without it the field is empty and `_rows` drops
                # the row, which is the same refusal every other incomplete row gets.
                "action": (
                    f"apruebo {name} en {digest[:12]}"
                    if (home.parent / "plan.md").is_file()
                    else ""
                ),
            }
        )
    return _rows(entries, "draft")


def collect(root: Path) -> tuple[list[Row], list[str]]:
    """Everything waiting for a person, and the ids of everything that did not say enough."""

    shown: list[Row] = []
    dropped: list[str] = []
    for reader in (stops, _drafts, _verdicts):
        whole, missing = reader(root)
        shown.extend(whole)
        dropped.extend(missing)
    return shown, dropped


def considered(root: Path) -> int:
    """How many candidates were looked at, shown or not.

    Derived from the same call the rows come from rather than from a second walk. The count
    line on the page states it beside the number of rows, and two numbers that came from two
    passes can disagree while both look measured.
    """

    shown, dropped = collect(root)
    return len(shown) + len(dropped)
