"""Every refusal `_validate_field` and `validate_record` can make, one at a time.

Between them these two carried 103 of the 533 mutants that survived over `acceptance.py`,
the largest single pool in the tree. `tests/test_acceptance.py` exercises them through a
corpus of whole records, which proves the shapes a real record takes; it leaves the shapes a
malformed one takes to whatever the corpus happens to contain.

Every branch here refuses, and they refuse with different words on purpose. A record that is
not JSON, one that is JSON but not canonical, one whose fields are right and whose digest is
wrong, and one whose value is three bytes over a limit are four different conversations with
whoever wrote it — and a reader who gets "malformed" for all four learns nothing about which.

These call both functions directly against the real schema. Using a fixture schema would
prove this code agrees with a fixture, and the whole design of `validate_record` is that the
schema document is the contract rather than a restatement of it.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from ai_engineering import acceptance

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "policy" / "risk-acceptance-v1.schema.json").read_text("utf-8"))

DIGEST = "sha256:" + "a" * 64
OTHER = "sha256:" + "b" * 64


def _record(**overrides: Any) -> dict[str, Any]:
    record = {
        "schema": "urn:ai-engineering:risk-acceptance:1",
        "schema_version": "1",
        "id": "R-010-01",
        "spec": "010",
        "spec_digest": DIGEST,
        "finding": "the native backend cannot prove power-loss durability",
        "severity": "medium",
        "authority_role": "repository maintainer",
        "accepted": "2026-08-14",
        "expires": "2026-11-14",
        "renewals": 0,
        "renews": "",
        "renews_digest": "",
        "justification": "The supported rename APIs promise no survival across power loss.",
        "evidence": {"path": "specs/010-x/spec.md", "content_digest": OTHER},
        "follow_up": "",
        "record_digest": DIGEST,
    }
    record.update(overrides)
    return record


def _sealed(**overrides: Any) -> bytes:
    """A record whose digest is its own, so a test about one field is about that field.

    Without this every case below would refuse on the digest first and prove nothing about
    the thing it set out to check — which is the shape of green test that measures the
    order of the checks rather than any of them.
    """

    record = _record(**overrides)
    record["record_digest"] = acceptance.record_digest(record)
    return acceptance.canonical_bytes(record)


def _refused(body: bytes) -> acceptance.Refusal:
    with pytest.raises(acceptance.Refusal) as raised:
        acceptance.validate_record(body, "the record", SCHEMA)
    return raised.value


def test_a_record_that_holds_together_is_accepted():
    """The clean control. Without it every refusal below is satisfied by a function that
    refuses everything, which is the passing test this repository exists to refuse."""

    assert acceptance.validate_record(_sealed(), "the record", SCHEMA) == json.loads(_sealed())


# --- the four ways a document fails before any field is looked at -------------------


def test_bytes_that_are_not_json_are_refused_as_not_json():
    refusal = _refused(b"not json at all")

    assert refusal.code == "ACCEPTANCE_MALFORMED"
    assert "not JSON" in str(refusal)


def test_json_that_is_not_an_object_is_refused_for_being_the_wrong_shape():
    """A list of records is a plausible mistake and would otherwise reach `set(record)`,
    which answers about the indices of a list without complaining."""

    refusal = _refused(b"[]")

    assert "not one JSON object" in str(refusal)


def test_a_record_that_is_not_canonical_is_refused_even_though_it_parses():
    """Whitespace, key order and escaping all change the bytes without changing the
    meaning, and the digest is over the bytes. A record accepted in a second spelling is a
    record whose digest proves nothing, because there would be a spelling for every value.
    """

    record = _record()
    record["record_digest"] = acceptance.record_digest(record)
    loose = json.dumps(record, indent=2).encode("utf-8")

    assert "not canonical JSON" in str(_refused(loose))


def test_a_missing_field_and_an_extra_field_are_the_same_refusal():
    """The field set is closed in both directions. An extra key is how a field nobody
    reviewed arrives, and a missing one is how a field somebody relies on disappears."""

    missing = _record()
    del missing["follow_up"]
    missing["record_digest"] = acceptance.record_digest(missing)

    extra = _record(surprise="x")
    extra["record_digest"] = acceptance.record_digest(extra)

    for body in (acceptance.canonical_bytes(missing), acceptance.canonical_bytes(extra)):
        assert "exactly the closed fields" in str(_refused(body))


# --- _validate_field: one table, one branch per row ----------------------------------
#
# Thirteen branches, and each refuses with different words on purpose — a reader who gets
# "malformed" for all thirteen learns nothing about which. So the case and the words it
# must produce sit in the same row, and the row's id says why that branch exists.
#
# One function rather than thirteen. Every case is still separate to pytest, so a failure
# still names exactly which branch broke; what goes away is thirteen copies of the same
# four lines. The reasoning that was in thirteen docstrings is in the ids and the comments
# beside the rows that earned one.


@pytest.mark.parametrize(
    ("override", "says"),
    [
        pytest.param({"renewals": "0"}, "non-integer renewals", id="an integer as a string"),
        # `isinstance(True, int)` is true in Python and false in JSON Schema. Without the
        # explicit exclusion, `renewals: true` validates and is then counted.
        pytest.param(
            {"renewals": True}, "non-integer renewals", id="a boolean Python calls an integer"
        ),
        pytest.param({"renewals": -1}, "outside its range", id="an integer below its minimum"),
        # The set comparison comes before the children are walked. Walking an object with a
        # key missing raises `KeyError` from inside the schema lookup, which reaches a person
        # as a traceback rather than as a refusal naming the field.
        pytest.param(
            {"evidence": {"path": "x"}}, "malformed evidence", id="an object missing a child"
        ),
        pytest.param(
            {"evidence": "specs/010-x/spec.md"},
            "malformed evidence",
            id="an object that is not one",
        ),
        # The recursion carries the path, or the message names `evidence` for a fault in
        # `evidence.content_digest` and the person re-reads the wrong line.
        pytest.param(
            {"evidence": {"path": "specs/010-x/spec.md", "content_digest": "nope"}},
            "evidence.content_digest",
            id="a child named by its own path",
        ),
        pytest.param({"finding": 7}, "non-string finding", id="a string field holding a number"),
        # Separate from the pattern check and before it: a record carrying an escape sequence
        # renders as something other than what it says in any terminal that prints it, and
        # several fields here have no pattern to catch it.
        pytest.param(
            {"finding": "a finding\u0007bell"}, "control character", id="a control character"
        ),
        pytest.param(
            {"schema": "urn:something:else:1"},
            "unexpected schema",
            id="a const holding something else",
        ),
        pytest.param(
            {"severity": "apocalyptic"}, "undefined severity", id="outside an enumeration"
        ),
        pytest.param({"id": "R-10-1"}, "malformed id", id="failing its pattern"),
        # Distinct words from "malformed", because an empty field is nearly always somebody
        # who meant to come back to it and a malformed one is nearly always a misunderstanding.
        pytest.param(
            {"justification": ""}, "empty justification", id="empty where a length is required"
        ),
        # Not merely a date-shaped string. `2026-02-30` matches every pattern anybody writes
        # for a date and is not a day that exists.
        pytest.param(
            {"accepted": "2026-02-30"}, "not one exact date", id="a date that is not a day"
        ),
    ],
)
def test_a_field_that_violates_its_schema_is_refused_and_says_which_way(override, says):
    refusal = _refused(_sealed(**override))

    assert refusal.code == "ACCEPTANCE_MALFORMED"
    assert says in str(refusal)


# --- validate_record, after the fields are individually sound ------------------------


def test_a_value_over_its_byte_limit_is_refused_even_when_its_pattern_holds():
    """The limits are in bytes and the pattern is in characters, so a field can pass every
    other check and still be too large to store. Measured in UTF-8, because that is what
    goes on disk, and a character count would let a field of accented text through at up to
    twice the size."""

    limits = SCHEMA["x-utf8-byte-limits"]
    name, limit = next(iter(limits.items()))
    if "." in name:
        pytest.skip(f"{name} is nested and this case wants a top-level field")

    assert "byte bound" in str(_refused(_sealed(**{name: "a" * (limit + 1)})))


def test_a_record_whose_digest_is_not_its_own_is_a_checksum_refusal_not_a_malformed_one():
    """A different code, because this is the only refusal that says somebody edited a
    record after it was sealed rather than wrote one badly."""

    refusal = _refused(acceptance.canonical_bytes(_record(record_digest=OTHER)))

    assert refusal.code == "ACCEPTANCE_CHECKSUM"
    assert "its own record digest" in str(refusal)


def test_an_expiry_before_its_acceptance_is_refused():
    """A window that closes before it opens. Every reader downstream asks whether today is
    inside it and gets a consistent, meaningless no."""

    assert str(_refused(_sealed(accepted="2026-08-14", expires="2026-08-13")))


# --- the frozen legacy recognizer -----------------------------------------------------
#
# `_parse_legacy` and `_normalized_legacy` carried 102 more of the surviving mutants. They
# read the shape of risk acceptance this repository shipped before there was a schema, and
# the word that governs both is *frozen*: whatever they accepted then, they accept now, and
# whatever they refuse has to be refused for a reason somebody can act on.
#
# The stakes are asymmetric and that is why they are worth this many cases. A reader that
# refuses a real block reports one acceptance short and somebody notices. A reader that
# accepts a block it should not, or reads a value as something other than what it says,
# reports an expiry that is not the expiry — and a register whose dates are wrong is worse
# than no register, because it is consulted.


def _block(**fields: str) -> str:
    base = {"finding": "a finding", "expires": "2026-11-14"}
    return "".join(f"{name}: {value}\n" for name, value in (base | fields).items())


def _read(block: str) -> dict[str, str] | None:
    return acceptance._parse_legacy(block, "the block")


def _rejected(block: str) -> acceptance.Refusal:
    with pytest.raises(acceptance.Refusal) as raised:
        acceptance._parse_legacy(block, "the block")
    return raised.value


def test_a_block_without_a_finding_or_an_expiry_is_somebody_elses_yaml():
    """The recognizer's whole boundary. A repository is full of fenced YAML that has nothing
    to do with risk, and reading one of those as a malformed acceptance would make every
    unrelated code block a reason to refuse the file."""

    assert _read("name: something\nvalue: 3\n") is None
    assert _read("finding: a finding\n") is None
    assert _read("expires: 2026-11-14\n") is None
    assert _read(_block()) == {"finding": "a finding", "expires": "2026-11-14"}


def test_blank_lines_and_comments_are_not_content():
    assert _read(f"# a comment\n\n{_block()}   \n") == {
        "finding": "a finding",
        "expires": "2026-11-14",
    }


def test_a_continued_value_is_joined_with_one_space_however_it_was_indented():
    """A finding long enough to wrap is the common case, and the join has to be exactly one
    space or the digest of the same text differs by how somebody laid it out."""

    read = _read("finding: a finding\n    that continues\n\there\nexpires: 2026-11-14\n")

    assert read is not None and read["finding"] == "a finding that continues here"


def test_an_indented_line_before_any_key_is_refused_rather_than_dropped():
    assert "indents a line with no key above" in str(_rejected("   orphan\n"))


@pytest.mark.parametrize("opener", ["- one", "? one"])
def test_an_indented_container_is_refused_because_this_reader_holds_no_lists(opener: str):
    """A list under a key is valid YAML and is not something this recognizer can represent.
    Flattening it would turn `- 2026-11-14` into the string `2026-11-14` and read a list of
    dates as one date."""

    block = f"finding: a finding\n  {opener}\nexpires: 2026-11-14\n"

    assert "container where a value" in str(_rejected(block))


@pytest.mark.parametrize("opener", ["[2026-11-14]", "{a: b}"])
def test_an_inline_container_is_refused_for_the_same_reason(opener: str):
    assert "container where a value" in str(_rejected(_block(expires=opener)))


def test_a_line_that_is_not_a_key_is_refused():
    assert "a line that is not a key" in str(_rejected("finding a finding\n"))


def test_a_repeated_key_is_refused_rather_than_last_one_winning():
    """Two expiry dates in one block is a block with two answers, and taking either is
    choosing for somebody who has not been told there was a choice."""

    block = "finding: a finding\nexpires: 2026-11-14\nexpires: 2036-11-14\n"

    assert "repeats the key expires" in str(_rejected(block))


@pytest.mark.parametrize("marker", [">", ">-", "|", "|-"])
def test_a_fold_marker_alone_reads_as_empty_rather_than_as_its_own_symbol(marker: str):
    """`finding: >` with the text on the lines below is ordinary YAML. Reading the marker as
    the value gives a finding called ">" — a record that says nothing and looks filled in."""

    read = _read(_block(**{"accepted_by": marker}))

    assert read is not None and read["accepted_by"] == ""


def test_surrounding_quotes_are_not_part_of_the_value():
    read = _read(_block(**{"id": '"R-010-01"', "severity": "'high'"}))

    assert read is not None and read["id"] == "R-010-01" and read["severity"] == "high"


# --- _normalized_legacy: what a recognized block still has to be ----------------------


def _normal(**fields: str) -> dict[str, Any]:
    return acceptance._normalized_legacy(
        {"finding": "a finding", "expires": "2026-11-14"} | fields, "the block"
    )


def _refused_normal(**fields: str) -> acceptance.Refusal:
    with pytest.raises(acceptance.Refusal) as raised:
        _normal(**fields)
    return raised.value


def test_a_recognized_block_takes_the_frozen_defaults_for_everything_it_omits():
    """The defaults are the shipped behaviour and are not negotiable: a block that omits
    severity was `medium` when it was written and has to stay `medium`, or every register
    ever published changes meaning the day this code does."""

    record = _normal()

    assert record["severity"] == "medium"
    assert record["accepted_by"] == "?"
    assert record["id"] == "" and record["accepted"] == "" and record["renewals"] == 0


@pytest.mark.parametrize(
    ("fields", "says"),
    [
        # Ignoring an unknown key is how a typo hides an expiry: `expries: 2026-01-01`
        # leaves the block with no expiry at all and nothing said.
        pytest.param({"expries": "2026-01-01"}, "never defined", id="a key nobody defined"),
        pytest.param(
            {"finding": "a\x07finding"}, "control character in finding", id="a control character"
        ),
        # `accepted_by: no` is the boolean false in YAML, not the person called No. Reading
        # it as text puts a word in the authority field that nobody typed.
        *[
            pytest.param(
                {"accepted_by": v}, "non-string value in accepted_by", id=f"the YAML scalar {v}"
            )
            for v in ("true", "null", "~", "no", "off")
        ],
        pytest.param(
            {"finding": "a" * 257}, "legacy bound on finding", id="over its bound in bytes"
        ),
        # The key is what the recognizer keys on, so an empty one gets this far. A record
        # whose finding is blank says a risk was accepted and not which.
        pytest.param({"finding": ""}, "empty finding", id="a finding that is empty"),
        pytest.param({"severity": "apocalyptic"}, "never defined", id="a severity nobody defined"),
        # Including the two that are date-shaped. A register sorted by an expiry that is not
        # a day sorts fine and expires nothing.
        *[
            pytest.param({"expires": v}, "not one exact date", id=f"an expiry of {v}")
            for v in ("2026-13-01", "2026-02-30", "not a date")
        ],
        pytest.param(
            {"accepted": "2026-02-30"}, "not one date", id="an accepted date that is not one"
        ),
        pytest.param({"id": "R-10-1"}, "not R-NNN-NN", id="an identity off the frozen shape"),
        pytest.param(
            {"evidence": "specs/010-x/spec.md"}, "no readable syntax", id="evidence with no digest"
        ),
    ],
)
def test_a_recognized_block_that_is_still_wrong_is_refused_and_says_how(fields, says):
    """Fourteen ways a block can be recognized and still not be a record, each with the
    words it must produce. One function; pytest still names the row that failed."""

    assert says in str(_refused_normal(**fields))


def test_the_optional_fields_are_only_checked_when_they_are_there():
    """Absence is the frozen default for all three and has to stay legal — a block written
    in 2024 omitted them and is still a record. A value that is present and wrong is not."""

    record = _normal()

    assert record["accepted"] == "" and record["id"] == "" and record["evidence"] == ""
    assert _normal(evidence="specs/010-x/spec.md@sha256:" + "a" * 64)["evidence"]


# --- _legacy_renewals: the counter that decides how many times a risk may come back ---


def test_an_absent_or_wordy_renewal_counter_is_zero_because_it_always_was():
    """The shipped behaviour, preserved exactly. `renewals: once` counted as zero when it
    was written, and a register that suddenly reads it as one retires a live acceptance."""

    assert acceptance._legacy_renewals(None, "x") == 0
    assert acceptance._legacy_renewals("", "x") == 0
    assert acceptance._legacy_renewals("once", "x") == 0


def test_a_boolean_renewal_counter_is_refused_rather_than_read_as_zero():
    """The one place the frozen leniency stops. `renewals: true` claims a renewal, and
    reading it as zero turns it back into an original — which lets the same finding be
    renewed twice more, past a ceiling of two."""

    with pytest.raises(acceptance.Refusal) as raised:
        acceptance._legacy_renewals("true", "x")

    assert "not a value" in str(raised.value)


def test_a_counter_holding_a_digit_and_something_else_is_refused():
    """`1 time` has a digit in it, so the wordy path does not catch it, and it is not a
    number. Rounding it to one would be this reader deciding what somebody meant."""

    with pytest.raises(acceptance.Refusal) as raised:
        acceptance._legacy_renewals("1 time", "x")

    assert "not a number" in str(raised.value)


@pytest.mark.parametrize("value", ["3", "9"])
def test_a_counter_past_the_ceiling_of_two_is_refused(value: str):
    with pytest.raises(acceptance.Refusal) as raised:
        acceptance._legacy_renewals(value, "x")

    assert "outside zero to two" in str(raised.value)


@pytest.mark.parametrize("value", ["0", "1", "2"])
def test_the_three_counts_inside_the_ceiling_are_read_as_themselves(value: str):
    assert acceptance._legacy_renewals(value, "x") == int(value)


# --- _safe_stat and _read: the path checks that run before anything is opened ---------
#
# 48 more survivors, and they are the highest-consequence ones in the file. Everything
# above decides whether a record says what it should; this decides whether the bytes being
# read are the bytes the repository holds. A symbolic link, a hard link, a device node or a
# path that walks onto another volume all read perfectly and none of them is the file the
# path names — and every one of them is a way somebody outside the repository puts content
# inside the register.
#
# The order matters as much as the checks. `lstat` and never `stat`, because `stat` follows
# the link and then reports on the target: the check would answer about the file at the far
# end and pass. And the size is taken from the same `lstat` the read is bounded by, so a
# file that grows between the two is caught rather than read short.


def _volume(path: Path) -> int:
    return path.lstat().st_dev


def _unsafe(path: Path, *, directory: bool = False) -> acceptance.Refusal:
    with pytest.raises(acceptance.Refusal) as raised:
        acceptance._safe_stat(path, _volume(path.parent), directory=directory)
    return raised.value


def test_a_real_file_and_a_real_directory_on_this_volume_are_accepted(tmp_path: Path):
    """The clean control, in both modes. Without it every refusal below is satisfied by a
    function that refuses everything."""

    here = tmp_path / "spec.md"
    here.write_text("x", encoding="utf-8")

    assert acceptance._safe_stat(here, _volume(tmp_path), directory=False) is None
    assert acceptance._safe_stat(tmp_path, _volume(tmp_path.parent), directory=True) is None


def test_a_path_that_is_not_there_is_unreadable_rather_than_unsafe(tmp_path: Path):
    """Two different codes for two different conversations. Absent is a register that names
    a file somebody deleted; unsafe is a register somebody is pointing somewhere else."""

    refusal = _unsafe(tmp_path / "gone.md")

    assert refusal.code == "ACCEPTANCE_UNREADABLE"


def test_a_symbolic_link_is_refused_even_when_it_points_at_a_real_file(tmp_path: Path):
    """The one this function exists for. A link inside the repository pointing at a file
    outside it reads as a perfectly ordinary acceptance whose content nobody in the
    repository controls — and `stat` rather than `lstat` would report on the target and
    never see the link at all."""

    target = tmp_path / "real.md"
    target.write_text("x", encoding="utf-8")
    link = tmp_path / "link.md"
    link.symlink_to(target)

    refusal = _unsafe(link)

    assert refusal.code == "ACCEPTANCE_UNSAFE_PATH"
    assert "symbolic link" in str(refusal)


def test_a_file_with_a_second_hard_link_is_refused(tmp_path: Path):
    """A hard link is not a link the filesystem will tell you about from the path. Both
    names are the file, so a second one anywhere on the volume is a second way to change
    what the register reads, with nothing at this path to show for it."""

    target = tmp_path / "real.md"
    target.write_text("x", encoding="utf-8")
    (tmp_path / "second.md").hardlink_to(target)

    assert "more than one link" in str(_unsafe(target))


def test_a_directory_offered_as_a_file_is_refused_and_the_reverse_too(tmp_path: Path):
    """Both directions, because the caller states which it expects and a check that only
    looked one way would let the other through in whichever call site got it wrong."""

    here = tmp_path / "spec.md"
    here.write_text("x", encoding="utf-8")

    assert "not a regular file" in str(_unsafe(tmp_path, directory=False))
    assert "not a directory" in str(_unsafe(here, directory=True))


def test_something_that_is_neither_a_file_nor_a_directory_is_refused(tmp_path: Path):
    """A named pipe passes `exists()` and blocks forever on read. It is not a regular file,
    which is the check that catches it before anything opens it."""

    pipe = tmp_path / "pipe"
    os.mkfifo(pipe)

    assert "not a regular file" in str(_unsafe(pipe))


def test_a_path_on_another_volume_is_refused(tmp_path: Path):
    """Stated as the device the repository is on rather than discovered per path, so a
    mount point inside the tree cannot vouch for itself."""

    here = tmp_path / "spec.md"
    here.write_text("x", encoding="utf-8")

    with pytest.raises(acceptance.Refusal) as raised:
        acceptance._safe_stat(here, _volume(here) + 1, directory=False)

    assert "crosses a filesystem boundary" in str(raised.value)


def test_a_file_over_its_bound_is_refused_before_it_is_read(tmp_path: Path):
    """The bound is the point: a register that reads whatever it is pointed at is a register
    somebody can make take as long as they like."""

    here = tmp_path / "spec.md"
    here.write_bytes(b"a" * 40)
    budget = acceptance._Budget(1_000_000)

    with pytest.raises(acceptance.Refusal) as raised:
        acceptance._read(here, 20, _volume(here), budget)

    assert raised.value.code == "ACCEPTANCE_OVER_BOUND"


def test_a_file_within_its_bound_is_read_and_spends_its_size(tmp_path: Path):
    here = tmp_path / "spec.md"
    here.write_bytes(b"a" * 40)
    budget = acceptance._Budget(1_000_000)

    assert acceptance._read(here, 100, _volume(here), budget) == b"a" * 40


def test_a_file_that_grows_between_the_measurement_and_the_read_is_refused(tmp_path: Path):
    """The check that makes the bound mean anything. Without it a file measured small and
    then replaced is read in full, and the bound describes a moment that has passed."""

    here = tmp_path / "spec.md"
    here.write_bytes(b"a" * 10)
    budget = acceptance._Budget(1_000_000)
    original = Path.read_bytes

    def grown(self: Path) -> bytes:
        return original(self) + b"more"

    with pytest.MonkeyPatch.context() as patched:
        patched.setattr(Path, "read_bytes", grown)
        with pytest.raises(acceptance.Refusal) as raised:
            acceptance._read(here, 100, _volume(here), budget)

    assert "changed while it was read" in str(raised.value)


def test_bytes_that_are_not_utf8_are_refused_as_such_and_not_replaced(tmp_path: Path):
    """Decoding with replacement would turn an unreadable file into a readable record full
    of question marks, which is the false green in miniature."""

    with pytest.raises(acceptance.Refusal) as raised:
        acceptance._text(b"\xff\xfe", "the record")

    assert "not valid UTF-8" in str(raised.value)


# --- _spec_directories, owner_of and legacy_spans: what the register walks -------------
#
# 31 more survivors in the walk, and the ruling inside it is the one worth pinning: a link
# in the specs home is *refused*, and a plain file is *skipped*. Those look like the same
# leniency and are opposites. Skipping a link takes whatever it points at out of the
# register without saying so — which is a way to make an acceptance disappear with no trace
# in the file that names it. A plain file cannot hold records at all, so passing over it
# hides nothing.


def _specs(root: Path) -> list[Path]:
    return acceptance._spec_directories(root, root.lstat().st_dev)


def test_a_repository_with_no_specs_home_yields_nothing_rather_than_refusing(tmp_path: Path):
    """Absence is an answer. A repository that has never written a spec has no acceptances,
    which is different from one whose specs cannot be read."""

    assert _specs(tmp_path) == []


def test_dot_directories_are_not_specs(tmp_path: Path):
    (tmp_path / "specs" / ".cache").mkdir(parents=True)
    (tmp_path / "specs" / "010-a").mkdir()

    assert [one.name for one in _specs(tmp_path)] == ["010-a"]


def test_a_link_in_the_specs_home_is_refused_and_a_plain_file_is_passed_over(tmp_path: Path):
    """The two that look like one rule. Skipping a link takes whatever it points at out of
    the register silently; a plain file cannot hold records, so skipping it hides nothing."""

    home = tmp_path / "specs"
    (home / "010-a").mkdir(parents=True)
    (home / "README.md").write_text("x", encoding="utf-8")

    assert [one.name for one in _specs(tmp_path)] == ["010-a"]

    (home / "011-linked").symlink_to(home / "010-a")

    with pytest.raises(acceptance.Refusal) as raised:
        _specs(tmp_path)
    assert raised.value.code == "ACCEPTANCE_UNSAFE_PATH"
    assert "is a link" in str(raised.value)


def test_more_spec_directories_than_the_bound_is_refused(tmp_path: Path, monkeypatch):
    """A bound on the walk, not only on each file. Without it a directory of a million
    empty entries is a way to make the register take as long as somebody likes."""

    home = tmp_path / "specs"
    home.mkdir(parents=True)
    for index in range(4):
        (home / f"{index:03d}-a").mkdir()
    monkeypatch.setattr(acceptance, "MAX_SPEC_DIRECTORIES", 3)

    with pytest.raises(acceptance.Refusal) as raised:
        _specs(tmp_path)
    assert raised.value.code == "ACCEPTANCE_OVER_BOUND"


def test_the_specs_home_itself_being_a_link_is_refused(tmp_path: Path):
    real = tmp_path / "elsewhere"
    real.mkdir()
    (tmp_path / "specs").symlink_to(real)

    with pytest.raises(acceptance.Refusal) as raised:
        _specs(tmp_path)
    assert "symbolic link" in str(raised.value)


@pytest.mark.parametrize(
    ("leaf", "owner"),
    [
        pytest.param("010-governed-foundation", "010", id="canonical"),
        pytest.param("spec-010", "010", id="digits not at the front"),
        pytest.param("0102-a", "010", id="more than three digits takes the first three"),
        pytest.param("1-2-3-x", "123", id="digits scattered through the name"),
    ],
)
def test_a_directory_names_its_owner_by_its_ascii_digits(leaf: str, owner: str):
    """Pre-canonical names are preserved rather than renamed, so the owner has to be read
    out of whatever somebody called the directory in 2024."""

    assert acceptance.owner_of(leaf) == owner


@pytest.mark.parametrize("leaf", ["ab", "01-x", "no-digits-at-all"])
def test_a_directory_with_fewer_than_three_digits_is_undecidable_not_guessed(leaf: str):
    """Its own code, because guessing puts records in a namespace that is not theirs — and
    a register whose rows are filed under the wrong spec is wrong in the direction nobody
    checks."""

    with pytest.raises(acceptance.Refusal) as raised:
        acceptance.owner_of(leaf)

    assert raised.value.code == "ACCEPTANCE_UNDECIDABLE_OWNER"


def test_the_digits_have_to_be_ascii(leaf: str = "٠١٢-arabic-indic"):
    """`str.isdigit()` is true for the Arabic-Indic digits and for a superscript two, and
    `int()` accepts some of them. A spec owned by `٠١٢` is a spec nobody can type."""

    with pytest.raises(acceptance.Refusal):
        acceptance.owner_of(leaf)


def test_a_fenced_block_span_runs_from_the_first_backtick_to_the_last(tmp_path: Path):
    """A renewal binds the span, so it is taken from the stored bytes rather than from a
    re-rendering. An off-by-one at either fence binds a different document."""

    body = b"before\n```yaml\nfinding: a\n```\nafter\n"

    spans = acceptance.legacy_spans(body)

    assert len(spans) == 1
    start, end, block = spans[0]
    assert body[start:end].startswith(b"```yaml") and body[start:end].endswith(b"```")
    assert block.strip() == "finding: a"


def test_a_block_written_on_windows_is_still_a_block(tmp_path: Path):
    """The bug this reader was corrected for: with the carriage return unmatched the fence
    read as unclosed, and the register answered PASS over zero acceptances in a file that
    held one — the quietest way a register can be wrong."""

    body = b"```yaml\r\nfinding: a\r\nexpires: 2026-11-14\r\n```\r\n"

    assert len(acceptance.legacy_spans(body)) == 1
