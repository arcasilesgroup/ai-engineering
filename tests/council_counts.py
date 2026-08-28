#!/usr/bin/env python3
"""The two numbers a council run owes, recomputed from the file rather than read out of it.

`EP-195` asks a second model to "find a measurable gap, not manufacture consensus", and
`docs/adr/0019` closes by saying no benchmark defines the improvement a council shows. Spec
023's `D-023-05` answers with two counts per run: how many gaps appeared only after the
anonymised cross-read, and how many findings were deleted for carrying no command or for
being refuted.

A model printing its own score is what rule 11 refuses, so this does not read the totals the
run wrote and print them back. It counts the entries under the two round-two headings itself
and refuses when its count and the run's stated total disagree. That disagreement is the only
thing this can catch and it is the thing worth catching: a run that says eleven and lists
four has either lost nine entries or invented nine, and either way the number closing a
deferral would be fiction.

Spec 045 makes this the critic step, and dual by nature. The historical shape — a
`council.md` beside the spec, totals heading `## The two counts` — keeps counting exactly
as it did, because the council history written before the sections arrived must stay
guarded (a single-glob switch makes every old file invisible). The new shape — a
`## Council` section inside `spec.md`, totals heading `### The two counts` — is refused by
rules the first version of this file could not have, because 045's own grill executed
their absence:

- **emptiness is a refusal, not a `(0, 0)`**. A heading with no dash-bullets needs the
  literal line `none` to say "ran and found nothing"; without it, the unfilled draft and
  the clean pass are the same bytes and the counter cannot tell them apart.
- **a declared round may not carry the prompt**. Enforcement is conditional on a
  `ran: round` declaration: a section still holding the template's prompt and no
  declaration reads "has not run", the same green absence this file already gives a
  missing `council.md`. A section that declares a round and keeps the prompt is the
  false green — arithmetic alone passes it.
- **a `ran:` line that is present must be whole**: `ran: round <n>, <date> — <n> min`.
  `pending` is a word where a number belongs; the grammar refuses it. The minutes are
  self-reported (D-045-05): this checks the shape, not the stopwatch.

`## Grill` is read by the same step for the same reason: an empty grill is a grill that
did not run (D-045-01), and every `### Q` owes an `**A:**` line.

It fails closed. An unparseable file, a missing heading, a total that is not a number, a
count that does not match, a declared section carrying the prompt, a malformed `ran:`
line and an empty heading that never said `none` are all non-zero. A repository with no
council run at all — in either shape — is not a failure and is not a pass either: it says
so and exits zero, because a council that has not run is not a council that lied.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

NEW_HEADING = "### Gaps no single lens named"
CUT_HEADING = "### Findings cut for carrying no command"
REFUTED_HEADING = "### Findings the cross-read refuted"
TOTALS_HEADING = "## The two counts"

# The in-spec shape (D-045-03): the same headings inside a `## Council` section, whose
# totals heading sits one level down because it is a part of a section now.
COUNCIL_SECTION = "## Council"
GRILL_SECTION = "## Grill"
SECTION_TOTALS_HEADING = "### The two counts"

COUNCIL_HEADINGS = (NEW_HEADING, CUT_HEADING, REFUTED_HEADING)

_NEW_TOTAL = re.compile(r"^- Gaps that appeared only after the cross-read: \*\*(\d+)\*\*$", re.M)
_DELETED_TOTAL = re.compile(r"^- Findings deleted[^:]*: \*\*(\d+)\*\*$", re.M)

# A `ran:` declaration (D-045-05) is a line that *opens* with the word, possibly
# markdown-decorated. Decoration is deliberately accepted into declaration here: a
# line that looks like `ran:` is treated as one and then refused by `_RAN_GRAMMAR`
# unless it is canonical. Treating `**ran:**` as prose instead was the false green a
# review executed — the author believes they declared a round, the reader believes the
# critics never ran, and a planted bogus total passes exit-0 un-policed.
_RAN_LINE = re.compile(r"^\s*[`*_\"']*ran:", re.M)
_RAN_GRAMMAR = re.compile(
    r"^`?ran: round [0-9]+, [0-9]{4}-[0-9]{2}-[0-9]{2} — [0-9]+ min`?([ ].*)?$"
)

# The template's prompt shapes, anchored to a line start the way doctor's MARKER is:
# `TODO:` opening a line and the `<!--` comment under an empty heading. A file naming
# the words in prose is not carrying the prompt.
_PROMPT_LINE = re.compile(r"^\s*(?:[-*]|\d+\.)?\s*(TODO:|<!--)", re.M)

# A declared section is one with at least one `ran: round` line; grammar is checked per
# declaration, so `pending` and the minutes-less shape refuse here.

RECEIPT_SCHEMA = "urn:ai-engineering:check-evidence:1"
RECEIPT_MAX_AGE = 86_400

MAX_BYTES = 4_000_000


class Unreadable(ValueError):
    """The file exists and its shape cannot be trusted. Never a warning."""


def _section(body: str, heading: str) -> str:
    """The lines under one heading, stopping at the next heading of any level.

    Prepending the newline rather than testing for one: a conditional fallback here would
    return the whole document when the heading sits at position 0, and a file with no such
    section would read as having one. That is the fail-open direction."""

    found = ("\n" + body).partition("\n" + heading)[2]
    if not found:
        raise Unreadable(f"no {heading!r} section")
    return re.split(r"\n#{2,3} ", found, maxsplit=1)[0]


def _top_section(body: str, heading: str) -> str | None:
    """The whole of one `## ` section, subsections included, or None when absent.

    Absence is the green that must stay green: a spec whose critics have not run has no
    section to vouch for it, and no rule here may call that a lie about a run. The scan
    is a regex, not a string partition: a heading with trailing spaces and a heading at
    file position 0 are both real sections, and the partition form silently returned
    None and `""` for them — a review executed the first, and `_section`'s own docstring
    names the second the fail-open shape it exists to avoid."""

    match = re.search(r"(?m)^" + re.escape(heading) + r"[ \t]*$", body)
    if match is None:
        return None
    rest = body[match.end() :]
    stop = re.search(r"(?m)^## ", rest)
    return rest[: stop.start()] if stop else rest


def entries(section: str) -> int:
    """Top-level bullets. A nested bullet is a command or a reason belonging to the one
    above it, and counting it would inflate the number this whole script exists to hold
    honest."""

    return sum(1 for line in section.splitlines() if line.startswith("- "))


def counts(body: str, totals_heading: str = TOTALS_HEADING) -> tuple[int, int]:
    """(new, deleted), recomputed, refusing when the run's own totals disagree."""

    measured = (
        entries(_section(body, NEW_HEADING)),
        entries(_section(body, CUT_HEADING)) + entries(_section(body, REFUTED_HEADING)),
    )
    totals = _section(body, totals_heading)
    stated = (_NEW_TOTAL.search(totals), _DELETED_TOTAL.search(totals))
    if not all(stated):
        raise Unreadable(f"{totals_heading!r} does not state both counts in the form it must")
    claimed = (int(stated[0].group(1)), int(stated[1].group(1)))
    if claimed != measured:
        raise Unreadable(
            f"the run states {claimed[0]} new and {claimed[1]} deleted, and the file lists "
            f"{measured[0]} and {measured[1]}"
        )
    return measured


def _rounds(section: str) -> list[str]:
    """The `ran:` declarations of one section, each checked against the grammar."""

    declared = [line.strip() for line in section.splitlines() if _RAN_LINE.match(line)]
    for line in declared:
        if not _RAN_GRAMMAR.match(line):
            raise Unreadable(
                f"a ran: declaration does not match `ran: round <n>, <date> — <n> min`: {line!r}"
            )
    return declared


def _refuse_prompt(section: str, name: str) -> None:
    """A section that declared a round may not still carry the template's prompt."""

    for line in section.splitlines():
        if _PROMPT_LINE.match(line):
            raise Unreadable(
                f"{name} declares a round and still carries the prompt: {line.strip()!r}"
            )


def _refuse_empty(body: str) -> None:
    """Each required heading carries bullets or a literal `none` line."""

    for heading in COUNCIL_HEADINGS:
        section = _section(body, heading)
        if entries(section) == 0 and not any(
            line.strip() == "none" for line in section.splitlines()
        ):
            raise Unreadable(
                f"{heading!r} is empty and did not say `none`: an unfilled draft and a "
                "council that found nothing are the same bytes, and only one of them is true"
            )


def council_section_counts(body: str) -> tuple[int, int] | None:
    """The in-spec `## Council`, counted — or None when no round has been declared.

    A declared section is then held to all four rules: grammar, prompt, emptiness,
    arithmetic. An undeclared one is a council that has not run, and that absence is
    silence, not a green tick."""

    section = _top_section(body, COUNCIL_SECTION)
    if section is None or not _rounds(section):
        return None
    _refuse_prompt(section, "## Council")
    for heading in COUNCIL_HEADINGS:
        if "\n" + heading not in "\n" + section:
            raise Unreadable(f"## Council declares a round and has no {heading!r} heading")
    _refuse_empty(section)
    return counts(section, SECTION_TOTALS_HEADING)


def grill_questions(body: str) -> int | None:
    """The declared `## Grill`'s question count, or None before it declares a round.

    D-045-01: a declared grill with no `### Q` must carry the literal line `nothing
    checkable failed`, and every question owes its own `**A:**` answer line. The
    warranty is a line test, not a substring: the shipped template's own prompt says
    the phrase in prose, and a review executed the false green that left — delete the
    leading `TODO:` and the prompt paragraph vouches for a grill that ran nothing. The
    answers are paired per question for the same reason two totals happened to agree:
    two `**A:**` lines under Q1 hid a missing one under Q2."""

    section = _top_section(body, GRILL_SECTION)
    if section is None or not _rounds(section):
        return None
    _refuse_prompt(section, "## Grill")
    questions = 0
    answered = False
    for line in section.splitlines():
        if line.startswith("### Q"):
            if questions and not answered:
                raise Unreadable(f"## Grill: question {questions} carries no `**A:**` line")
            questions += 1
            answered = False
        elif line.lstrip().startswith("**A:**") and questions:
            answered = True
    if questions and not answered:
        raise Unreadable(f"## Grill: question {questions} carries no `**A:**` line")
    if questions == 0:
        if not any(
            line.strip().strip("`*") == "nothing checkable failed" for line in section.splitlines()
        ):
            raise Unreadable(
                "## Grill declares a round with no `### Q` entry and no `nothing checkable "
                "failed` line: an empty grill is a grill that did not run"
            )
        return 0
    return questions


def _guarded(path: Path) -> None:
    """A council file that is a link, or whose directory is one, is a file this repository
    did not write where it thinks it did. Refusing is the only answer a check can give."""

    if path.is_symlink() or path.parent.is_symlink():
        raise Unreadable("is a link, and a link is not a record")
    if path.stat().st_size > MAX_BYTES:
        raise Unreadable(f"is {path.stat().st_size} bytes, over {MAX_BYTES}")


def _receipt(files: int, new: int, deleted: int, started: str, digest: str) -> None:
    """Never raises. A receipt that could take the run down with it would make a record of
    a check into a way to fail the check."""

    where = ROOT / ".ai" / "receipts" / "council-counts.json"
    artifact = "sha256:" + hashlib.sha256(f"{new}/{deleted}".encode()).hexdigest()
    try:
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text(
            json.dumps(
                {
                    "schema": RECEIPT_SCHEMA,
                    "schema_version": "1",
                    "kind": "automated",
                    "id": "council-counts",
                    "applicability": "applicable" if files else "not-applicable",
                    "command": "python tests/council_counts.py",
                    "tool_version": f"council-counts over {files} file(s)",
                    "input_digest": digest,
                    "artifact_digest": artifact,
                    "started_at": started,
                    "finished_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "max_age_seconds": RECEIPT_MAX_AGE,
                    "outcome": "PASS",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError as why:
        print(f"  the counts were taken and the receipt could not be written: {why}")
        return
    print(f"  receipt: {where.relative_to(ROOT)}")


def main() -> int:
    started = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Two regimes, one receipt (D-045-03). The historical glob stays because the council
    # history written before the sections arrived must stay guarded by the arithmetic it
    # was written under; the spec-file glob joins it and stays silent until a section
    # declares a round, so drafting never reddens the gate.
    historical = sorted(ROOT.glob("specs/*/council.md"))
    bodies: dict[Path, str] = {}
    for path in sorted(ROOT.glob("specs/*/spec.md")):
        body = path.read_text(encoding="utf-8", errors="replace")
        if (
            _top_section(body, COUNCIL_SECTION) is not None
            or _top_section(body, GRILL_SECTION) is not None
        ):
            bodies[path] = body
    try:
        for path in (*historical, *bodies):
            _guarded(path)
    except Unreadable as why:
        print(f"  {path.relative_to(ROOT)} {why}")
        return 1

    new = deleted = 0
    try:
        for path in historical:
            gained, lost = counts(path.read_text(encoding="utf-8"))
            print(f"  {path.parent.name}  {gained} found only by the cross-read, {lost} deleted")
            new, deleted = new + gained, deleted + lost
        for path, body in bodies.items():
            pair = council_section_counts(body)
            questions = grill_questions(body)
            if pair is not None:
                print(
                    f"  {path.parent.name}  {pair[0]} found only by the cross-read, "
                    f"{pair[1]} deleted"
                )
                new, deleted = new + pair[0], deleted + pair[1]
            if questions is not None:
                print(f"  {path.parent.name}  grill: {questions} questions")
    except (Unreadable, OSError) as why:
        print(f"  {path.relative_to(ROOT)}: {why}")
        return 1

    counted = [*historical, *bodies]
    digest = hashlib.sha256(b"".join(path.read_bytes() for path in counted) or b"").hexdigest()
    if not counted:
        print("  no council has run in this repository, so there is nothing to count")
    _receipt(len(counted), new, deleted, started, "sha256:" + digest)
    print(f"RAN council={new}/{deleted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
