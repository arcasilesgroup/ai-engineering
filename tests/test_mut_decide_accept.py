"""Accepting a decision: what is refused, and what is never typed at a person.

`decide.accept` carried 54 surviving mutants. It moves one MADR out of `proposed` and
writes three authority fields beside it — and every one of those is read or measured, never
asked for. The role and the reference come from the approved Solution Intent; the timestamp
is now. A verb that asked a person to type their own authority would be a verb that lets
anybody grant it.

Three of its comments are apologies for defects that shipped, and each one gets a case
here, because a comment explaining a bug is a bug nothing is watching for.

The path one: `--accept` takes text off the command line and this used to build a glob out
of it, and `..` is a legal glob segment. The directory is listed and names compared now, so
the argument never touches path construction at all.

The message one: a record whose status is a bare `proposed` was refused with "has already
left proposed", which is not what the file says and not what happened. It cost the operator
five attempts at records they were entitled to look at.

The escaping one: the role and reference come from a file a person edits and were
interpolated between bare quotes, so a role holding a newline wrote its own frontmatter
lines into the record whose whole purpose is to be the thing that cannot be forged.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering import decide


def _adr(root: Path, name: str, body: str) -> Path:
    where = root / "docs" / "adr"
    where.mkdir(parents=True, exist_ok=True)
    path = where / name
    path.write_text(body, encoding="utf-8")
    return path


def _v1(status: str = '"proposed"') -> str:
    return (
        "---\n"
        'schema: "urn:ai-engineering:madr:1"\n'
        'schema_version: "1"\n'
        'type: "adr"\n'
        'id: "0001"\n'
        'title: "A decision"\n'
        f"status: {status}\n"
        "---\n\n# A decision\n"
    )


@pytest.mark.parametrize(
    "number",
    ["1", "00001", "abcd", "", "0001x", "../../../../etc/rc", "00*1", "0001 "],
)
def test_a_number_that_is_not_four_digits_is_refused_before_anything_is_listed(
    number: str, tmp_path: Path, capsys
):
    """`--accept` takes text off the command line, and this used to build a glob pattern out
    of it. `..` is a legal glob segment, so `../../../../etc/rc` matched a file outside
    `docs/adr` and the rewrite would have edited it. A framework whose subject is filesystem
    authority does not get to make that mistake in its own record verb."""

    assert decide.accept(tmp_path, number).outcome == "INCOMPLETE"
    assert "four-digit" in capsys.readouterr().out


def test_the_argument_never_reaches_path_construction_at_all(tmp_path: Path, capsys):
    """The second half of that fix, and the one that holds. A validated number is a promise
    about this call; listing the directory and comparing names is a property of the code, so
    there is no spelling of the argument that reaches outside `docs/adr`."""

    outside = tmp_path / "0001-elsewhere.md"
    outside.write_text(_v1(), encoding="utf-8")
    (tmp_path / "docs" / "adr").mkdir(parents=True)

    assert decide.accept(tmp_path, "0001").outcome == "INCOMPLETE"
    assert "0 MADRs are numbered" in capsys.readouterr().out
    assert "proposed" in outside.read_text(encoding="utf-8")


def test_two_records_sharing_a_number_are_refused_rather_than_one_being_picked(
    tmp_path: Path, capsys
):
    """Which of the two a person meant is exactly the question nobody can answer from here,
    and writing authority into either would be answering it for them."""

    _adr(tmp_path, "0001-first.md", _v1())
    _adr(tmp_path, "0001-second.md", _v1())

    assert decide.accept(tmp_path, "0001").outcome == "INCOMPLETE"
    assert "2 MADRs are numbered" in capsys.readouterr().out


def test_a_record_that_predates_the_schema_is_refused_with_its_own_reason(tmp_path: Path, capsys):
    """Two conditions, and the second was learned the expensive way. The message used to say
    "has already left proposed" for anything whose status was not the *quoted* literal, so
    the three records written before the schema — which carry a bare `status: proposed` —
    were refused with a sentence that is neither what the file says nor what happened.

    Widening it to accept both spellings was the obvious repair and it was wrong: those
    records have no v1 frontmatter, so accepting one writes authority fields into a header
    the schema does not describe and the whole graph then fails to validate. The refusal
    stands; what changed is that it says which of the two reasons it is."""

    _adr(tmp_path, "0001-old.md", "---\nstatus: proposed\ndate: 2024-01-01\n---\n\n# Old\n")

    assert decide.accept(tmp_path, "0001").outcome == "INCOMPLETE"
    printed = capsys.readouterr().out
    assert "predates the MADR schema" in printed
    assert "Migrate its frontmatter first" in printed


@pytest.mark.parametrize("status", ['"accepted"', '"superseded"', '"rejected"'])
def test_a_record_that_already_left_proposed_says_what_it_reads(
    status: str, tmp_path: Path, capsys
):
    """Naming the status it found rather than asserting a state. A message that states
    something the code did not establish is this repository's most common defect, and this
    verb is where it was found."""

    _adr(tmp_path, "0001-done.md", _v1(status))

    assert decide.accept(tmp_path, "0001").outcome == "INCOMPLETE"
    assert status.strip('"') in capsys.readouterr().out


def test_a_record_with_no_status_at_all_says_missing_rather_than_nothing(tmp_path: Path, capsys):
    _adr(
        tmp_path,
        "0001-nostatus.md",
        '---\nschema: "urn:ai-engineering:madr:1"\nid: "0001"\n---\n\n# x\n',
    )

    assert decide.accept(tmp_path, "0001").outcome == "INCOMPLETE"
    assert "missing" in capsys.readouterr().out


def test_without_a_validating_intent_nothing_is_written(tmp_path: Path, capsys):
    """The authority is read, never invented. An Intent that does not validate grants
    nothing, and a draft grants nothing either, because a draft has no approval block —
    which is the whole point of the draft state."""

    record = _adr(tmp_path, "0001-first.md", _v1())

    assert decide.accept(tmp_path, "0001").outcome == "INCOMPLETE"
    assert "Solution Intent" in capsys.readouterr().out
    assert 'status: "proposed"' in record.read_text(encoding="utf-8")


def test_an_authority_holding_a_newline_cannot_write_its_own_frontmatter(
    tmp_path: Path, monkeypatch, capsys
):
    """The role and the reference come from `.ai/intent.md`, which a person edits, and they
    were interpolated between bare quotes. `status`, `supersedes` and `spec` are all one
    newline away from being forgeable that way — in the file whose whole purpose is to be
    the thing that cannot be forged.

    Ordinary values are unchanged byte for byte. The escaping only shows on values that were
    never legal."""

    record = _adr(tmp_path, "0001-first.md", _v1())
    monkeypatch.setattr(
        decide, "granted", lambda _root: ('maintainer"\nstatus: "accepted', 'ref\nspec: "999"')
    )

    assert decide.accept(tmp_path, "0001").outcome == "PASS"
    capsys.readouterr()
    written = record.read_text(encoding="utf-8")

    # Lines, not substrings. The escaped newline is still the characters `\` and `n`
    # inside a JSON string, so `status:` appears twice in the text and only once as a line
    # — and a line is what a frontmatter parser reads.
    lines = written.splitlines()
    assert sum(1 for line in lines if line.startswith("status:")) == 1
    assert not any(line.startswith("spec:") for line in lines)
    assert json.loads(written.split("authority_role: ", 1)[1].split("\n", 1)[0])


def test_an_ordinary_acceptance_writes_the_three_fields_and_names_the_commit(
    tmp_path: Path, monkeypatch, capsys
):
    """The clean control, and the last line matters as much as the first three. The
    transition has to be its own commit, because that is what the validator checks and what
    makes the change reviewable — so this writes the record and names the commit rather than
    making it."""

    record = _adr(tmp_path, "0001-first.md", _v1())
    monkeypatch.setattr(decide, "granted", lambda _root: ("repository maintainer", "intent@abc"))

    assert decide.accept(tmp_path, "0001").outcome == "PASS"
    written = record.read_text(encoding="utf-8")
    printed = capsys.readouterr().out

    assert 'status: "accepted"' in written
    assert 'authority_role: "repository maintainer"' in written
    assert 'approval_ref: "intent@abc"' in written
    assert "approved_at:" in written
    assert "git commit" in printed
