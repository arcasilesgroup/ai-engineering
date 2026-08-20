"""Materialising the Intent graph: what is followed, what is bounded, what is refused.

`spec._materialize` carried 39 surviving mutants. It walks the Solution Intent and every
document the Intent names, reading each through the transaction writer so that the whole
graph is one consistent snapshot rather than a set of files read at different moments.

The bound is the part worth pinning. A relation graph is user-authored and can point at
anything, including back at itself, so this walks it iteratively with a seen-set and stops
at 128 files — and stopping is a refusal, not a truncation. A snapshot that quietly held the
first 128 documents of a larger graph would be an authority decision taken over part of the
evidence, and nothing downstream could tell.

Every refusal here answers with a `_Snapshot` carrying the observations taken so far rather
than raising, because the caller needs to know what was read even when the answer is no —
the generations in those observations are what the transaction later checks nothing moved
underneath.
"""

from __future__ import annotations

import json
from typing import Any

from ai_engineering import spec


class _Reader:
    """A writer-shaped stand-in that answers reads from a dictionary.

    The real one needs an open transaction over a repository. What `_materialize` asks of it
    is one method, and the cases below are about which paths it asks for and in what order —
    which a dictionary can answer exactly."""

    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files
        self.asked: list[str] = []

    def read(self, relative: str, *, maximum: int) -> Any:
        self.asked.append(relative)
        if relative not in self.files:
            raise ValueError(f"no such file {relative}")
        return spec.spec_transaction.Observation(
            path=relative, body=self.files[relative], generation=None, parents=(), maximum=maximum
        )


def _intent(*relations: str, **extra: Any) -> bytes:
    record = {"relations": [{"path": path} for path in relations], **extra}
    return json.dumps(record).encode("utf-8")


def test_the_intent_itself_is_read_first_and_kept(capsys):
    reader = _Reader({".ai/intent.md": _intent()})

    snapshot = spec._materialize(reader)

    assert reader.asked[0] == ".ai/intent.md"
    assert [one.path for one in snapshot.observations] == [".ai/intent.md"]


def test_an_intent_that_is_not_an_object_is_schema_invalid():
    """A list, a number and a string are all valid JSON and none of them is an Intent.
    Reading `relations` off any of them would raise somewhere further down, where the
    message would be about a type rather than about the document."""

    for body in (b"[]", b"7", b'"text"'):
        snapshot = spec._materialize(_Reader({".ai/intent.md": body}))
        assert snapshot.validation.outcome != "PASS"
        assert snapshot.record is None


def test_relations_that_are_not_a_list_are_schema_invalid():
    snapshot = spec._materialize(_Reader({".ai/intent.md": b'{"relations": {"path": "a"}}'}))

    assert snapshot.validation.outcome != "PASS"


def test_a_relation_without_a_string_path_is_refused_and_keeps_what_was_read():
    """The record is kept this time and the Intent's own observation with it, because the
    caller needs to know what was read even when the answer is no — those generations are
    what the transaction later checks nothing moved underneath."""

    body = json.dumps({"relations": [{"path": "specs/a.md"}, {"path": 7}]}).encode()

    snapshot = spec._materialize(_Reader({".ai/intent.md": body}))

    assert snapshot.validation.outcome != "PASS"
    assert snapshot.record is not None
    assert [one.path for one in snapshot.observations] == [".ai/intent.md"]


def test_the_intent_is_never_read_twice_however_often_it_is_named():
    """A relation pointing back at `.ai/intent.md` is ordinary in a graph somebody wrote by
    hand. Reading it again would put two observations of one file in the snapshot, with two
    generations the transaction would then have to reconcile."""

    reader = _Reader({".ai/intent.md": _intent(".ai/intent.md", ".ai/intent.md")})

    spec._materialize(reader)

    assert reader.asked.count(".ai/intent.md") == 1


def test_the_queue_is_walked_from_the_end_and_a_broken_child_abandons_the_rest():
    """Two facts that only appear when you run it, and together they are worth knowing.

    `pending.pop()` takes from the end, so the relations an Intent lists are walked in
    reverse. And a child whose own relations cannot be parsed ends the walk with `break`
    rather than skipping that child — so siblings still queued behind it are never read.

    Which means: when one document is malformed, *which* of its siblings were read depends
    on the order the Intent happened to list them. The snapshot is refused either way, so
    nothing downstream acts on a partial read — but a future change trying to make this walk
    resilient has to start here."""

    reader = _Reader(
        {
            ".ai/intent.md": _intent("a.md", "b.md"),
            "a.md": b"no frontmatter",
            "b.md": b"no frontmatter",
        }
    )

    snapshot = spec._materialize(reader)

    assert reader.asked == [".ai/intent.md", "b.md"]
    assert snapshot.validation.outcome != "PASS"


def test_an_intent_naming_no_relations_reads_only_itself():
    reader = _Reader({".ai/intent.md": _intent()})

    spec._materialize(reader)

    assert reader.asked == [".ai/intent.md"]


def test_a_document_that_cannot_be_read_stops_the_walk_with_what_it_has():
    """A relation naming a file that is not there. The walk stops and the snapshot carries
    the observations taken so far, because a graph with a hole in it is not a graph and
    guessing what the missing document said is not available."""

    files = {".ai/intent.md": _intent("gone.md")}

    snapshot = spec._materialize(_Reader(files))

    assert snapshot.validation.outcome != "PASS"
    assert snapshot.record is None


def test_a_document_whose_own_relations_cannot_be_parsed_ends_the_walk_without_raising():
    """The `break` rather than a re-raise. That document was read and is in the snapshot;
    what could not be done is follow it further, and the validation below decides what that
    means — this function does not get to turn an unreadable child into a crash."""

    files = {
        ".ai/intent.md": _intent("child.md"),
        "child.md": b"not json at all",
    }
    reader = _Reader(files)

    snapshot = spec._materialize(reader)

    assert "child.md" in [one.path for one in snapshot.observations]
    assert snapshot.record is not None
