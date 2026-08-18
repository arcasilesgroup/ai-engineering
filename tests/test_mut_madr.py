"""What `_parse` and `_worktree_files` decide, one decision at a time.

Between them these two functions carried 194 of the 571 mutants that survived over
`madr.py` and `wiring.py` — a third of the whole gap in two functions. `tests/test_madr.py`
exercises both, but through `madr.validate`, which reaches them with whatever a plausible
repository happens to contain. That proves the paths a good record takes. It leaves the
ones a bad record takes to chance, and every one of those is a decision about whether a
file is a record at all.

Both functions are the same shape of thing and it is worth naming: they answer *is this
mine, and can I read it* before anything downstream is allowed to have an opinion. A
mistake there does not produce a wrong verdict, it produces a verdict about the wrong file
— which is the failure this repository keeps finding under a different name.

These call the two functions directly. Going through `validate` would mean every case had
to be a valid-enough repository first, and the case that matters most here is the file that
is not valid anything.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from ai_engineering import madr


def _repo(root: Path) -> Path:
    """A real git repository, because `_worktree_files` asks git what exists."""

    root.mkdir(parents=True, exist_ok=True)
    quiet = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, env=quiet)
    return root


def _write(root: Path, relative: str, payload: bytes | str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_bytes(payload)
    return path


# ── _parse: what counts as frontmatter, and what a broken one is called ──────────────


def test_a_file_that_does_not_open_with_a_fence_is_not_a_record_and_is_not_a_problem():
    """The difference between "not mine" and "mine and broken".

    A repository is full of Markdown that has nothing to do with this framework. Reading
    one of those as a damaged record would make every unrelated file a reason to refuse.
    """

    parsed = madr._parse(b"# just a heading\n\ntext\n")

    assert parsed.problem is None
    assert parsed.fields == {} and parsed.raw_fields == {}
    assert parsed.declares_v1 is False and parsed.ambiguous_candidate is False


@pytest.mark.parametrize(
    "opening",
    [
        pytest.param(b"---\n", id="lf"),
        pytest.param(b"---\r\n", id="crlf"),
        pytest.param(b"\xef\xbb\xbf---\n", id="byte order mark then lf"),
        pytest.param(b"\xef\xbb\xbf---\r\n", id="byte order mark then crlf"),
    ],
)
def test_the_four_ways_a_record_can_open_all_reach_the_same_fields(opening: bytes):
    """A record written on Windows, or by an editor that stamps a byte order mark, is the
    same record. The mark is stripped before the fence is looked for and again by the
    decoder, and the two strippings have to agree or the header starts one character late
    and every field in it is lost."""

    raw = opening + b'type: "adr"\nid: "0001"\n---\nbody\n'.replace(
        b"\n", b"\r\n" if b"\r" in opening else b"\n"
    )

    parsed = madr._parse(raw)

    assert parsed.problem is None
    assert parsed.raw_fields == {"type": '"adr"', "id": '"0001"'}
    assert parsed.body.strip() == "body"


def test_frontmatter_that_never_closes_is_unreadable_and_keeps_no_body():
    """An unclosed fence means the whole file is header. Treating the rest as a body would
    invent a document division the writer never made."""

    parsed = madr._parse(b"---\ntype: adr\nid: x\nand then prose forever\n")

    assert parsed.problem == madr.UNREADABLE
    assert parsed.body == ""
    assert "type" in parsed.raw_fields


@pytest.mark.parametrize(
    "line",
    [
        pytest.param("no colon here", id="no colon"),
        pytest.param("  indented: value", id="leading space"),
        pytest.param("\ttabbed: value", id="leading tab"),
        pytest.param("# a comment", id="comment"),
        pytest.param("not-a*key: value", id="key the pattern refuses"),
        pytest.param("tight:value", id="no space after the colon"),
    ],
)
def test_a_header_line_that_is_not_a_field_makes_the_record_unreadable(line: str):
    """Six ways to write something that is not a field. None of them is skipped quietly:
    a header nobody can read in full is a header nobody should act on part of."""

    parsed = madr._parse(f"---\ntype: adr\n{line}\n---\nbody\n".encode())

    assert parsed.problem == madr.UNREADABLE


def test_a_repeated_key_is_ambiguous_rather_than_unreadable():
    """These are different answers and the difference is the point. Unreadable says the
    file cannot be understood; ambiguous says it can be understood two ways, which is worse
    because both readings look fine on their own."""

    parsed = madr._parse(b"---\ntype: adr\ntype: decision\n---\nbody\n")

    assert parsed.problem == madr.AMBIGUOUS


def test_ambiguous_outranks_an_unreadable_line_that_came_first():
    """Order must not decide the verdict. A file with a junk line *and* a duplicated key is
    ambiguous, not unreadable, however the two are arranged — otherwise a writer could bury
    a duplicate by putting a broken line above it."""

    both = madr._parse(b"---\nbroken line\ntype: adr\ntype: decision\n---\nbody\n")
    reversed_order = madr._parse(b"---\ntype: adr\ntype: decision\nbroken line\n---\nbody\n")

    assert both.problem == madr.AMBIGUOUS
    assert reversed_order.problem == madr.AMBIGUOUS


def test_a_key_with_nothing_after_the_colon_is_a_field_with_an_invalid_value():
    """Three answers are available here and the line gets the middle one. It is not
    unreadable — the key parsed and is kept, empty — and it is not fine, because a field
    with no value is a field somebody meant to fill in. It is schema-invalid, which is the
    answer that says the file is ours and wrong rather than unintelligible."""

    parsed = madr._parse(b"---\ntype: adr\nid:\n---\nbody\n")

    assert parsed.problem == madr.SCHEMA_INVALID
    assert parsed.raw_fields["id"] == ""


# ── _parse: which files claim to be v1, and which only look like it ─────────────────


def test_the_schema_line_alone_declares_v1():
    parsed = madr._parse(f'---\nschema: "{madr._V1}"\n---\nbody\n'.encode())

    assert parsed.declares_v1 is True and parsed.ambiguous_candidate is False


def test_a_version_number_declares_v1_only_alongside_the_madr_shape():
    """`schema_version: "1"` on its own says a version of something. Which something is the
    part that matters, and `type: adr` with an `id` is what says it."""

    shaped = madr._parse(b'---\nschema_version: "1"\ntype: "adr"\nid: "0001"\n---\nb\n')
    bare = madr._parse(b'---\nschema_version: "1"\n---\nb\n')

    assert shaped.declares_v1 is True
    assert bare.declares_v1 is False
    assert bare.ambiguous_candidate is True


def test_a_file_that_smells_like_a_record_without_declaring_one_is_ambiguous():
    """The whole reason this flag exists: a file carrying `type: adr` and an id, with no
    schema line anywhere, is either a record somebody forgot to stamp or a document that
    happens to share two field names. Both readings are live, so neither is chosen."""

    parsed = madr._parse(b"---\ntype: adr\nid: 0001\n---\nbody\n")

    assert parsed.declares_v1 is False and parsed.ambiguous_candidate is True


def test_a_broken_record_still_gets_read_for_its_own_claim_to_be_v1():
    """A file whose header has a junk line cannot be parsed into values, and refusing to
    look further would file it as somebody else's document. It is not: it says it is ours.
    So when parsing failed, the raw text is re-read for the declaration alone, quoted or
    bare, and the file is judged as a damaged record of ours rather than ignored."""

    broken = madr._parse(b'---\nschema: "urn:ai-engineering:madr:1"\nbroken line\n---\nb\n')

    assert broken.problem == madr.UNREADABLE
    assert broken.declares_v1 is True


def test_the_salvage_read_accepts_the_bare_spelling_of_the_version_too():
    broken = madr._parse(b"---\nschema_version: 1\ntype: adr\nid: 0001\nbroken\n---\nb\n")

    assert broken.problem == madr.UNREADABLE
    assert broken.declares_v1 is True


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(b"---\ntype: adr\rid: x\n---\nb\n", id="a bare carriage return"),
        pytest.param("---\ntype: adrid: x\n---\nb\n".encode(), id="next line"),
        pytest.param("---\ntype: adr id: x\n---\nb\n".encode(), id="line separator"),
        pytest.param("---\ntype: adr id: x\n---\nb\n".encode(), id="paragraph separator"),
        pytest.param(b"---\ntype: \xff\n---\nb\n", id="not utf-8 at all"),
    ],
)
def test_a_line_ending_only_some_readers_agree_about_is_refused(raw: bytes):
    """Five characters that split a line in one reader and not in another. A record whose
    field boundaries depend on who is reading it has no field boundaries, and this is the
    one place to say so — after here, everything downstream believes the split."""

    with pytest.raises(madr._Problem) as refused:
        madr._decode(raw)

    assert refused.value.result == madr.UNREADABLE


# ── _worktree_files: what git offers, and what is taken from it ──────────────────────


def test_a_repository_with_nothing_in_it_yields_nothing_rather_than_one_empty_name(
    tmp_path: Path,
):
    """`git ls-files -z` prints nothing at all for an empty repository, and splitting
    nothing on a null byte gives one empty string, not none. That empty string would be
    joined onto the root and read as the repository directory itself."""

    assert madr._worktree_files(_repo(tmp_path / "empty")) == {}


def test_a_tracked_file_is_read_whatever_is_in_it(tmp_path: Path):
    root = _repo(tmp_path / "plain")
    _write(root, "notes/thing.md", "not a record at all\n")

    assert madr._worktree_files(root) == {"notes/thing.md": b"not a record at all\n"}


def test_a_symlink_where_a_record_belongs_is_refused_and_one_anywhere_else_is_skipped(
    tmp_path: Path,
):
    """A link in `docs/adr`, or named `spec.md`, or carrying a record's numbering, is a
    record whose bytes live somewhere this function cannot vouch for. Refusing is the only
    honest answer. A link anywhere else is somebody's own arrangement and is simply not a
    record, so it is passed over rather than turned into a failure."""

    root = _repo(tmp_path / "links")
    target = _write(root, "elsewhere/real.md", "---\ntype: adr\n---\nb\n")
    (root / "notes").mkdir(parents=True, exist_ok=True)
    (root / "notes" / "link.md").symlink_to(target)

    assert "notes/link.md" not in madr._worktree_files(root)

    (root / "docs" / "adr").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "adr" / "0001-linked.md").symlink_to(target)

    with pytest.raises(madr._Problem) as refused:
        madr._worktree_files(root)
    assert refused.value.result == madr.UNREADABLE


def test_a_spec_file_that_is_a_link_is_refused_wherever_it_sits(tmp_path: Path):
    root = _repo(tmp_path / "speclink")
    target = _write(root, "elsewhere/real.md", "---\ntype: adr\n---\nb\n")
    (root / "specs" / "010-x").mkdir(parents=True, exist_ok=True)
    (root / "specs" / "010-x" / "spec.md").symlink_to(target)

    with pytest.raises(madr._Problem) as refused:
        madr._worktree_files(root)
    assert refused.value.result == madr.UNREADABLE


def test_a_name_git_still_lists_after_the_file_has_gone_is_skipped(tmp_path: Path):
    """git lists what it has been told about. A file staged and then deleted from disk is
    still a name in that list, and it is a name with no bytes behind it."""

    root = _repo(tmp_path / "gone")
    path = _write(root, "notes/vanishing.md", "text\n")
    subprocess.run(["git", "add", "notes/vanishing.md"], cwd=root, check=True)
    path.unlink()

    assert madr._worktree_files(root) == {}


# ── _worktree_files: the ignored half, where reading everything is not an option ─────


def _ignored(root: Path) -> None:
    _write(root, ".gitignore", "ignored/\n")


def test_an_ignored_file_with_no_frontmatter_is_never_opened_past_its_first_bytes(
    tmp_path: Path,
):
    """The reason any of this exists. An ignored tree is where the caches and the build
    output live, and reading all of it to find out none of it is a record would make this
    function unusable in a real repository."""

    root = _repo(tmp_path / "ignored-plain")
    _ignored(root)
    _write(root, "ignored/huge.bin", b"x" * (madr._DISCOVERY_LIMIT * 2))

    assert "ignored/huge.bin" not in madr._worktree_files(root)


def test_an_ignored_file_with_frontmatter_but_no_schema_is_not_a_record(tmp_path: Path):
    root = _repo(tmp_path / "ignored-nonschema")
    _ignored(root)
    _write(root, "ignored/note.md", "---\ntitle: a note\n---\nbody\n")

    assert "ignored/note.md" not in madr._worktree_files(root)


@pytest.mark.parametrize(
    "header",
    [
        pytest.param("schema: something\n", id="schema"),
        pytest.param("schema_version: 1\n", id="schema_version"),
    ],
)
def test_an_ignored_file_that_names_a_schema_is_taken_seriously(tmp_path: Path, header: str):
    """Either word is enough. A record hidden in an ignored directory is exactly the case
    the ambiguity checks exist for, so it has to be found before it can be objected to."""

    root = _repo(tmp_path / f"ignored-{header.split(':')[0]}")
    _ignored(root)
    _write(root, "ignored/record.md", f"---\n{header}---\nbody\n")

    assert "ignored/record.md" in madr._worktree_files(root)


def test_an_ignored_record_written_with_windows_endings_and_a_mark_is_still_found(
    tmp_path: Path,
):
    """The discovery peek does its own fence and header handling on raw bytes, separately
    from `_decode`, and the two have to agree about a byte order mark and about `\\r\\n` or
    a record written on one machine is invisible on another."""

    root = _repo(tmp_path / "ignored-crlf")
    _ignored(root)
    _write(root, "ignored/record.md", b"\xef\xbb\xbf---\r\nschema: something\r\n---\r\nbody\r\n")

    assert "ignored/record.md" in madr._worktree_files(root)


def test_an_ignored_file_whose_frontmatter_never_closes_within_the_peek_is_refused(
    tmp_path: Path,
):
    """The one case where not reading further cannot be resolved either way. The file opens
    like a record and does not close inside the window, so it is either an enormous record
    or something that merely starts like one — and silence would pick the second."""

    root = _repo(tmp_path / "ignored-open")
    _ignored(root)
    _write(root, "ignored/open.md", b"---\n" + b"x" * (madr._DISCOVERY_LIMIT + 1))

    with pytest.raises(madr._Problem) as refused:
        madr._worktree_files(root)
    assert refused.value.result == madr.UNREADABLE


def test_an_ignored_file_in_a_records_home_is_read_without_being_asked_for_a_schema(
    tmp_path: Path,
):
    """`docs/adr/…` and `specs/<one>/spec.md` are homes, and a file sitting in one is a
    record by where it is. Asking it to also announce a schema would let somebody hide a
    conflicting record by leaving the schema line off and adding the path to .gitignore."""

    root = _repo(tmp_path / "ignored-home")
    _write(root, ".gitignore", "docs/adr/0002-hidden.md\nspecs/011-x/spec.md\n")
    _write(root, "docs/adr/0002-hidden.md", "no frontmatter here\n")
    _write(root, "specs/011-x/spec.md", "no frontmatter here either\n")

    found = madr._worktree_files(root)

    assert "docs/adr/0002-hidden.md" in found
    assert "specs/011-x/spec.md" in found


def test_a_spec_file_at_the_wrong_depth_is_not_one_of_those_homes(tmp_path: Path):
    """`specs/<slug>/spec.md` is three parts exactly. `specs/spec.md` and
    `specs/a/b/spec.md` are somebody else's arrangement, and treating them as homes would
    read whatever an ignored directory happened to call `spec.md`."""

    root = _repo(tmp_path / "ignored-depth")
    _write(root, ".gitignore", "specs/\n")
    _write(root, "specs/spec.md", "no frontmatter\n")
    _write(root, "specs/010-x/deeper/spec.md", "no frontmatter\n")

    found = madr._worktree_files(root)

    assert "specs/spec.md" not in found
    assert "specs/010-x/deeper/spec.md" not in found
