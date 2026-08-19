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
