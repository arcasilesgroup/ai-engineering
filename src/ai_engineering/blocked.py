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
import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

# The four, named once. Read by the collector, by the renderer and by the subcommand that
# writes a stop, so a fifth field cannot be added to one of them and forgotten in the others.
FIELDS = ("what", "since", "why", "action")

# Stops first, then drafts, then verdicts. The question the section answers is what unsticks
# the build, not what is worst — an audited requirement that is unreachable by construction
# has been unreachable for months and will keep, and a run that halted an hour ago will not.
ORDER = ("halt", "draft", "verdict")

# A fourth field that is present and useless. The module docstring above promises these are
# refused and the first version only checked for whitespace, so `action = "TODO"` rendered as
# though somebody could act on it. That is the bug-tracker failure specification 020 was
# challenged with, arriving through the one field that was supposed to prevent it.
REFUSED = re.compile(r"^\s*(todo|tbd|fixme|xxx|pending\b|n/?a\b|ask\b|decide\b|figure\b)", re.I)

LEDGER = Path("docs") / "blocked.toml"

HEADER = """# What is waiting for a person, written by the run that stopped.
#
# Each row states a gate that was reached and what is missing. Nothing here records that the
# missing thing arrived: a model reading approval out of a conversation is what the
# constitution forbids, and a ledger that could clear itself would be worse than none.
#
# Written by `ai-eng report blocked`. Rendered by the section at the top of
# `docs/solution-intent.html`. Rows are keyed by what is waiting, so the same gate reached
# twice is one row with a newer reason and the date of the first halt.

"""

# What a TOML basic string escapes, and nothing else. The first version reached for
# `json.dumps`, which is close enough to be tempting and wrong in one place: with the default
# `ensure_ascii` it writes an emoji as a surrogate pair, `tomllib` refuses an escaped
# surrogate as "not a Unicode scalar value", and a single emoji in a `--why` bricked the
# ledger permanently — every later read raised, every later write refused, and the only
# recovery was hand-editing a governed file.
_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}


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


def _basic(value: str) -> str:
    """One TOML basic string. Astral characters go through as themselves, which is what the
    format asks for; only the control characters it forbids become escapes."""

    out = ['"']
    for char in value:
        if char in _ESCAPES:
            out.append(_ESCAPES[char])
        elif char < " " or char == "\x7f":
            out.append(f"\\u{ord(char):04x}")
        else:
            out.append(char)
    out.append('"')
    return "".join(out)


def _usable(value: object) -> str:
    """The field as a row may carry it, or the empty string when it may not.

    A string, non-blank, and not one of the placeholders that says a decision has not been
    made. `True` and `["run", "this"]` are not near-misses to coerce — a field holding either
    is a hand-edited record whose author meant something this module cannot know.
    """

    if not isinstance(value, str) or not value.strip() or REFUSED.match(value):
        return ""
    return value.strip()


def _rows(entries: list[dict], kind: str) -> tuple[list[Row], list[str]]:
    """The whole rows and the ids of the ones that were dropped.

    Both halves in one pass and returned together. Counting the drops separately means two
    passes that can disagree, and a section whose "22 of 28" is computed from a different
    walk than its rows is a number that looks checked and is not.
    """

    whole: list[Row] = []
    dropped: list[str] = []
    for at, entry in enumerate(entries):
        # Never nameless. A drop with an empty id is a filter hiding itself, which is the
        # defect this whole module exists to remove, arriving one level down.
        name = str(entry.get("id") or "").strip() or f"{kind}[{at}]"
        usable = {field: _usable(entry.get(field)) for field in FIELDS}
        if all(usable.values()):
            whole.append(Row(kind=kind, id=name, **usable))
        else:
            dropped.append(name)
    return whole, dropped


def _entries(root: Path) -> list[dict]:
    """The ledger's rows as written, before any of them is judged.

    Returned raw as well as parsed because `record` rewrites the whole file: building the new
    file out of `Row`s would delete every row the reader had only dropped, so an unrelated
    halt would destroy the half-written record that the drop list existed to make visible.
    """

    where = root / LEDGER
    if not where.is_file():
        return []
    try:
        loaded = tomllib.loads(where.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as refused:
        raise Unreadable(f"{LEDGER.as_posix()} could not be read: {refused}") from refused
    listed = loaded.get("stop") or []
    # `[stop]` instead of `[[stop]]` is the likeliest hand-edit typo and parses to a table
    # rather than a list of them, and `stop = ["a"]` parses to strings. Both are valid TOML
    # of the wrong shape, and the first version called `.get` on them and raised
    # `AttributeError` straight through every caller that promised to refuse rather than
    # raise — including the one that runs while a build is already failing.
    entries = [one for one in listed if isinstance(one, dict)] if isinstance(listed, list) else []
    if len(entries) != (len(listed) if isinstance(listed, list) else 1):
        raise Unreadable(
            f"{LEDGER.as_posix()} holds something that is not a [[stop]] table, so what it "
            "says about the rest cannot be trusted"
        )
    return entries


def stops(root: Path) -> tuple[list[Row], list[str]]:
    """Every halt a run recorded, and the ids of the halts that did not say enough.

    A tree that never halted has no ledger, and having nothing to say is the right answer
    rather than a missing file. A ledger that does not parse is the other direction and is
    refused: read as "nothing is stuck" it would render a green section over a tree nobody
    measured, which is the fail-open the page's tracked-file list already closed once.
    """

    return _rows(_entries(root), "halt")


# The vocabulary `docs/requirements.toml` uses for a row nothing more can be done about
# without a person. INCOMPLETE and NO-EVIDENCE are deliberately not here: they are work the
# build owes itself, and a section that listed all 165 of them would be the bug tracker
# specification 020 was challenged with and kept its scope to answer.
STUCK = ("BLOCKED", "CONTRADICTED")

_MEASURED = re.compile(r"^# Measured on (\d{4}-\d{2}-\d{2})", re.M)


def _verdicts(root: Path) -> tuple[list[Row], list[str]]:
    """The audited rows nothing but a person can move.

    `subject` is what is waiting, `note` is why it stopped and `evidence` is the command that
    decides it — three of the four already written, by four auditors who had no idea they
    were filling this in. The fourth is the file's own measurement date.

    That date is the file's, not each row's, and it is the weakest field in this module: a
    re-audit moves all seventeen forward and makes months-old blocks look new, which is the
    harm `record` guards against for halts. It is what the record holds; nothing better can
    be derived from it without inventing a date, and the column heading says so.

    A header that stops saying when it was measured refuses rather than dropping seventeen
    rows quietly. Dropped, the count line would report them as waiting on the build when they
    are waiting on a person — a true number with a false reason, which is the bug this
    repository has now shipped four times.
    """

    where = root / "docs" / "requirements.toml"
    if not where.is_file():
        return [], []
    try:
        body = where.read_text(encoding="utf-8")
        loaded = tomllib.loads(body)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as refused:
        raise Unreadable(f"docs/requirements.toml could not be read: {refused}") from refused
    stuck = [one for one in loaded.get("requirement") or [] if one.get("verdict") in STUCK]
    stamped = _MEASURED.search(body)
    if stuck and stamped is None:
        raise Unreadable(
            "docs/requirements.toml no longer says when it was measured, so its "
            f"{len(stuck)} unreachable rows cannot say since when"
        )
    return _rows(
        [
            {
                "id": entry.get("id"),
                "what": entry.get("subject"),
                "since": stamped.group(1) if stamped else "",
                "why": entry.get("note"),
                "action": entry.get("evidence"),
            }
            for entry in stuck
        ],
        "verdict",
    )


def _frontmatter(raw: str) -> dict[str, str] | None:
    """The frontmatter block, or None when the file has none.

    Three shapes defeated the first version and each one made a specification vanish from
    both halves of the count, which is the filter hiding itself. A file whose body merely
    contains `---` twice was read as frontmattered and handed an approval literal; a value
    holding `---` truncated the block so `status:` landed outside it; and `status: 'draft'`
    in legal single-quoted YAML was read as `'draft'` and matched nothing.
    """

    if not raw.startswith("---"):
        return None
    _, _, rest = raw.partition("---")
    block, marker, _ = rest.partition("\n---")
    if not marker:
        return None
    return {
        key.strip(): value.strip().strip("\"'")
        for key, _, value in (line.partition(":") for line in block.splitlines())
        if key.strip() and not key.startswith("#")
    }


def _drafts(root: Path) -> tuple[list[Row], list[str]]:
    """The specifications that have everything they need except somebody saying yes.

    A draft with no plan is not here: it is waiting on the build. A draft with a plan has run
    out of things an agent may do on its own, and the digest in its action is of the file as
    it is on disk, so approving it cannot silently approve a later edit — which is the whole
    reason the block gate in 019 asked for digests in the first place. The path is in the
    action beside the digest, because a person asked to grant authority over a hash should
    not have to already know what was hashed.
    """

    entries = []
    for home in sorted((root / "specs").glob("*/spec.md")):
        front = _frontmatter(home.read_text(encoding="utf-8"))
        if front is None:
            # Counted, never silent. A spec.md nobody can read the front of is exactly the
            # kind of thing that should be on this list rather than missing from both halves.
            entries.append({"id": home.parent.name.split("-", 1)[0]})
            continue
        if front.get("status") != "draft":
            continue
        name = front.get("id") or home.parent.name.split("-", 1)[0]
        digest = hashlib.sha256(home.read_bytes()).hexdigest()
        where = home.relative_to(root).as_posix()
        entries.append(
            {
                "id": name,
                "what": f"specification {name} is drafted and nobody has approved it",
                "since": front.get("date", ""),
                "why": "an agent may write a specification and may not approve one",
                # Only when there is a plan. Without it the field is empty and `_rows` drops
                # the row, which is the same refusal every other incomplete row gets.
                "action": (
                    f"apruebo {name} en {digest[:12]} — sha256 de {where}"
                    if (home.parent / "plan.md").is_file()
                    else ""
                ),
            }
        )
    return _rows(entries, "draft")


READERS = {"halt": stops, "draft": _drafts, "verdict": _verdicts}


def collect(root: Path) -> tuple[list[Row], list[str]]:
    """Everything waiting for a person, and the ids of everything that did not say enough.

    One walk. There was a `considered()` beside this that called it again to count, and its
    own docstring claimed the two numbers came from one pass — the exact thing `_rows` above
    refuses. A caller that wants the denominator adds the two lengths of one call.
    """

    shown: list[Row] = []
    dropped: list[str] = []
    for kind in ORDER:
        whole, missing = READERS[kind](root)
        shown.extend(whole)
        dropped.extend(missing)
    return shown, dropped


def _name(what: str) -> str:
    """A stable id from the thing that is waiting, so the same gate reached twice collides.

    The hash is not decoration. Two gates whose first forty characters agree — and block
    headers phrased by the same skill routinely do — slugged to one id while staying two
    rows, which puts a duplicate id in the rendered table.
    """

    slug = re.sub(r"[^a-z0-9]+", "-", what.lower()).strip("-")[:40] or "stop"
    return f"{slug}-{hashlib.sha256(what.encode('utf-8', 'surrogatepass')).hexdigest()[:8]}"


def record(root: Path, *, what: str, why: str, action: str, since: str) -> Path:
    """Write one halt into the ledger, or refresh the one already there.

    The identity is what is waiting. A build that halts twice at the same gate is one row
    with a newer reason, because two rows would make the section count one stop as two — and
    the date stays the date of the first halt, since "since when" is the question the column
    asks and refreshing it on every retry would make a week-old block look new.

    Rebuilt from the entries as written rather than from the parsed rows, so a row this
    module drops is left where it is instead of being deleted by an unrelated halt. Written
    to a sibling and renamed, so an interrupted write cannot leave a truncated governed file
    that every later read refuses.
    """

    held = _entries(root)
    already = next((one for one in held if _usable(one.get("what")) == what.strip()), None)
    fresh = {
        "id": str(already.get("id")) if already else _name(what),
        "what": what,
        "since": str(already.get("since")) if already else since,
        "why": why,
        "action": action,
    }
    kept = [one for one in held if one is not already]
    body = "".join(
        "[[stop]]\n"
        + "".join(f"{field} = {_basic(str(one.get(field, '')))}\n" for field in ("id", *FIELDS))
        + "\n"
        for one in [*kept, fresh]
    )
    where = root / LEDGER
    where.parent.mkdir(parents=True, exist_ok=True)
    beside = where.with_suffix(".toml.writing")
    beside.write_text(HEADER + body, encoding="utf-8")
    os.replace(beside, where)
    return where
