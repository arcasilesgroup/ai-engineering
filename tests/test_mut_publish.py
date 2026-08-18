"""The exclusive rename, and every answer the kernel can give it.

`_rename_noreplace_posix` carried 39 surviving mutants. It is nine lines of `ctypes` and a
list of error numbers, and it is the single point where a spec directory becomes canonical:
the whole transaction is built so that this call either publishes or does nothing.

`os.rename` cannot be used here, and the reason is the whole design. POSIX rename replaces
the destination silently, so two writers publishing spec 011 at the same moment both
succeed and one directory disappears with nothing raised anywhere. `renameat2` on Linux and
`renameatx_np` on macOS refuse instead, and the refusal is what makes the second writer
find out.

So the error numbers are not interchangeable and the three exceptions are not one exception
with three messages. `Collision` means somebody else got there first, which is ordinary and
recoverable. `Unsupported` means this filesystem cannot make the promise — a network mount,
an old kernel — and the caller falls back to a different backend rather than proceeding.
`Unsafe` means the call failed for a reason nobody enumerated, and there is nothing to do
with that but stop.

These drive the real function with a stand-in for the C symbol, because the branches worth
pinning are the ones a working filesystem never produces.
"""

from __future__ import annotations

import ctypes
import errno
import os
import pathlib
import sys

import pytest

from ai_engineering import spec_transaction as transaction


def _root(tmp_path):
    root = tmp_path / "repo"
    (root / ".ai").mkdir(parents=True)
    (root / ".ai" / "intent.md").write_bytes(b'{"authority":"local"}\n')
    (root / "specs").mkdir()
    return root


def _answering(code: int, monkeypatch) -> None:
    """Stand in for the kernel: return failure and set the errno this case is about."""

    def fake(*_args: object) -> int:
        ctypes.set_errno(code)
        return -1

    fake.argtypes = None  # type: ignore[attr-defined]
    fake.restype = None  # type: ignore[attr-defined]

    class Library:
        def __getattr__(self, _name: str):
            return fake

    monkeypatch.setattr(ctypes, "CDLL", lambda *_a, **_k: Library())


def _renaming() -> None:
    transaction._rename_noreplace_posix(-1, "source", -1, "destination")


@pytest.mark.skipif(os.name != "posix", reason="the POSIX primitive is what this is about")
def test_a_destination_that_already_exists_is_a_collision_and_not_a_failure(monkeypatch):
    """The case the whole design exists for. `os.rename` would replace it silently and both
    writers would succeed, with one spec directory gone and nothing raised anywhere."""

    _answering(errno.EEXIST, monkeypatch)

    with pytest.raises(transaction.Collision):
        _renaming()


@pytest.mark.skipif(os.name != "posix", reason="the POSIX primitive is what this is about")
def test_a_non_empty_destination_is_the_same_collision(monkeypatch):
    """Linux says EEXIST and some filesystems say ENOTEMPTY for the same situation. Which
    one arrives is a fact about the filesystem, and the caller is asking about the spec."""

    _answering(errno.ENOTEMPTY, monkeypatch)

    with pytest.raises(transaction.Collision):
        _renaming()


@pytest.mark.skipif(os.name != "posix", reason="the POSIX primitive is what this is about")
@pytest.mark.parametrize("name", ["EINVAL", "ENOSYS", "ENOTSUP", "EOPNOTSUPP"])
def test_a_filesystem_that_cannot_promise_this_says_unsupported(name: str, monkeypatch):
    """Four numbers for one answer: this mount cannot make the promise. A network mount or
    an older kernel is not a collision and it is not a bug — it is a reason to use another
    backend, and calling it anything else sends the caller down the wrong path.

    `ENOTSUP` and `EOPNOTSUPP` are the same value on Linux and different on other hosts, and
    both are read from `errno` rather than written down here for that reason."""

    code = getattr(errno, name, None)
    if code is None:
        pytest.skip(f"{name} does not exist on this host")
    _answering(code, monkeypatch)

    with pytest.raises(transaction.Unsupported):
        _renaming()


@pytest.mark.skipif(os.name != "posix", reason="the POSIX primitive is what this is about")
def test_any_other_error_number_is_unsafe_and_names_it(monkeypatch):
    """Nobody enumerated this one. Treating an unknown failure as a collision would tell the
    caller to back off from a spec that is not there; treating it as unsupported would send
    it to a backend that has the same problem. Stopping is the only honest answer, and the
    number goes in the message because it is the only thing anybody can act on."""

    _answering(errno.EIO, monkeypatch)

    with pytest.raises(transaction.Unsafe) as refused:
        _renaming()

    assert str(errno.EIO) in str(refused.value)


@pytest.mark.skipif(os.name != "posix", reason="the POSIX primitive is what this is about")
def test_a_host_without_the_symbol_is_unsupported_rather_than_a_crash(monkeypatch):
    """`getattr(library, name, None)` and not a bare lookup. A libc without the symbol
    raises `AttributeError` out of a function whose callers are watching for three
    exceptions, and none of them is that one."""

    class Empty:
        def __getattr__(self, name: str):
            raise AttributeError(name)

    monkeypatch.setattr(ctypes, "CDLL", lambda *_a, **_k: Empty())

    with pytest.raises(transaction.Unsupported):
        _renaming()


@pytest.mark.skipif(os.name != "posix", reason="the POSIX primitive is what this is about")
def test_a_posix_host_that_is_neither_linux_nor_darwin_is_unsupported(monkeypatch):
    """The flag differs per kernel and there is no portable spelling. Guessing one would
    pass some other number to a real syscall, which is worse than declining."""

    monkeypatch.setattr(sys, "platform", "sunos5")

    with pytest.raises(transaction.Unsupported):
        _renaming()


@pytest.mark.skipif(os.name != "posix", reason="the POSIX primitive is what this is about")
def test_a_successful_call_returns_without_reading_a_stale_errno(monkeypatch):
    """`set_errno(0)` before the call. errno is only meaningful after a failure, and a
    leftover value from anything earlier in the process would make a successful publish
    raise `Collision` — the one failure mode that looks exactly like correct behaviour."""

    ctypes.set_errno(errno.EEXIST)

    def succeeding(*_args: object) -> int:
        return 0

    class Library:
        def __getattr__(self, _name: str):
            return succeeding

    monkeypatch.setattr(ctypes, "CDLL", lambda *_a, **_k: Library())

    assert _renaming() is None


# --- _parts and _component: what a name has to be before anything opens it -------------
#
# Every path this module touches goes through these two first, and they are the reason the
# rest of the file can use `dir_fd` and short names instead of joining strings. A name that
# reaches `os.open` with a `..` in it walks out of the transaction home, and no amount of
# care downstream puts it back.
#
# The line worth reading twice is the one that checks the spelling *before* `PurePosixPath`
# sees it. `a/./b` and `a//b` lose their dot and empty segments during parsing, so a check
# written after the parse never sees the spelling it exists to refuse — and this module
# would then accept a name it believes it rejected.


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("", id="empty"),
        pytest.param("/absolute", id="absolute"),
        pytest.param("a/../b", id="a walk upwards"),
        pytest.param("..", id="just upwards"),
        pytest.param(".", id="here"),
        pytest.param("a//b", id="an empty segment"),
        pytest.param("a/./b", id="a dot segment"),
        pytest.param("a/b/", id="a trailing slash"),
        pytest.param("a\\b", id="a backslash"),
        pytest.param("a\x00b", id="a null byte"),
    ],
)
def test_a_name_that_is_not_a_canonical_relative_path_is_refused(value: str):
    """Ten spellings, and the two in the middle are the reason the check reads the raw
    string first. `a//b` and `a/./b` are normalised away by the parser, so a check written
    after it never sees them and this module accepts a name it believes it rejects."""

    with pytest.raises(transaction.Unsafe):
        transaction._parts(value)


def test_a_value_that_is_not_a_string_is_refused_rather_than_coerced():
    """`None` and a `Path` both stringify into something that looks like a path. Coercing
    either would let a caller's type confusion arrive as a filesystem operation."""

    for value in (None, 7, b"bytes", pathlib.PurePosixPath("a/b")):
        with pytest.raises(transaction.Unsafe):
            transaction._parts(value)  # type: ignore[arg-type]


def test_an_ordinary_relative_path_survives_with_its_parts_in_order():
    assert transaction._parts("specs/001-first/spec.md") == ("specs", "001-first", "spec.md")


def test_a_component_is_one_segment_and_a_path_is_not_one():
    """`stage` takes a name, not a path, because it opens it against a directory descriptor.
    A two-segment name there is a write one level away from where the caller thinks."""

    assert transaction._component("spec.md") == "spec.md"
    with pytest.raises(transaction.Unsafe):
        transaction._component("nested/spec.md")


def test_a_pending_name_has_to_say_it_is_pending():
    """The prefix is what tells a crashed transaction's leftovers apart from a published
    directory. Without it, cleanup either removes somebody's spec or leaves rubbish that
    every later inventory has to explain."""

    assert transaction._component("pending-first", pending=True) == "pending-first"
    with pytest.raises(transaction.Unsafe):
        transaction._component("001-first", pending=True)


def test_a_transaction_home_may_be_nested_and_not_deep():
    """`specs` for a spec and `specs/NNN-slug` for a record beside it are both homes. The
    bound is there so that "walk it one component at a time" cannot become an unbounded
    walk of somebody else's directory tree."""

    assert transaction._home_relative("specs/001-first") == "specs/001-first"
    with pytest.raises(transaction.Unsafe):
        transaction._home_relative("a/b/c/d/e")


# --- staging: what a pending entry has to be before it can ever be published ----------


def test_a_body_that_is_not_bytes_is_refused_before_a_directory_is_created(tmp_path):
    """Refused first, so a rejected stage leaves nothing behind. A string here would be
    encoded by whatever default the host has, and the digest downstream would be over bytes
    nobody chose."""

    root = _root(tmp_path)
    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        inventory = writer.inventory()
        with pytest.raises(transaction.Unsafe):
            writer.stage(inventory, "pending-x", "spec.md", "not bytes")  # type: ignore[arg-type]
        assert not list((root / "specs").glob("pending-*"))


def test_staging_the_same_pending_name_twice_is_refused_by_the_filesystem(tmp_path):
    """`os.mkdir` and not `makedirs(exist_ok=True)`. Two writers with the same name would
    otherwise share a pending directory and each publish the other's file."""

    root = _root(tmp_path)
    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        inventory = writer.inventory()
        writer.stage(inventory, "pending-twice", "spec.md", b"first\n")
        with pytest.raises(transaction.Collision):
            writer.stage(writer.inventory(), "pending-twice", "spec.md", b"second\n")


def test_a_staged_file_is_written_whole_and_read_back_as_itself(tmp_path):
    """The write loop advances a memoryview until it is empty, because one `os.write` is
    allowed to take less than it was given. Stopping after the first would publish a spec
    that ends wherever the kernel felt like."""

    root = _root(tmp_path)
    body = b"x" * 200_000
    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        pending = writer.stage(writer.inventory(), "pending-big", "spec.md", body)
        writer.publish(pending, "001-big")

    assert (root / "specs" / "001-big" / "spec.md").read_bytes() == body


def test_an_inventory_taken_before_someone_else_wrote_cannot_be_used_to_stage(tmp_path):
    """The inventory is a claim about the namespace at a moment. Staging against a stale one
    is how two writers each believe they know what is there."""

    root = _root(tmp_path)
    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        stale = writer.inventory()
        writer.stage(stale, "pending-one", "spec.md", b"one\n")
        with pytest.raises(transaction.Unsafe):
            writer.stage(stale, "pending-two", "spec.md", b"two\n")


# --- read, and re-proving a pending entry that was already staged --------------------
#
# `_PosixWriter.read` carried 34 more survivors and `_require_pending` another 29. They are
# the two places where this module refuses to trust something it already saw.
#
# `read` is bounded, and the bound is checked twice: once against the size the file claims
# before anything is read, and once against the bytes that actually arrived. A file that
# grows between the two would otherwise be read in full, and a bound that describes a moment
# that has passed is not a bound.
#
# `_require_pending` re-opens a directory this transaction created moments ago and proves it
# is still the same one: the directory's identity, the exact set of names inside it, the
# file's identity, its link count, its size, and finally its bytes. All six, because a
# staged entry becomes canonical with a rename that cannot be undone — this is the last
# moment anything can be checked, and after it the only evidence left is what was checked
# here.


def test_a_read_bound_that_is_not_a_count_is_refused(tmp_path):
    """A boolean is an integer in Python and is not a byte count anywhere. `maximum=True`
    would read one byte and report the file as over its bound."""

    root = _root(tmp_path)
    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        for bad in (-1, True, "100", 1.5, None):
            with pytest.raises(transaction.Unsafe):
                writer.read(".ai/intent.md", maximum=bad)


def test_a_file_over_its_bound_is_refused_before_it_is_read(tmp_path):
    root = _root(tmp_path)
    (root / "specs" / "big.md").write_bytes(b"x" * 200)

    with (
        transaction.writer(root, ".ai/intent.md", "specs") as writer,
        pytest.raises(transaction.Unsafe),
    ):
        writer.read("specs/big.md", maximum=100)


def test_a_file_exactly_at_its_bound_is_read(tmp_path):
    """The boundary itself, in the direction that matters. An off-by-one here refuses a file
    somebody sized deliberately."""

    root = _root(tmp_path)
    (root / "specs" / "exact.md").write_bytes(b"x" * 100)

    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        assert writer.read("specs/exact.md", maximum=100).body == b"x" * 100


def test_an_empty_file_reads_as_empty_rather_than_refusing(tmp_path):
    root = _root(tmp_path)
    (root / "specs" / "empty.md").write_bytes(b"")

    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        assert writer.read("specs/empty.md", maximum=100).body == b""


def test_a_path_that_is_not_canonical_never_reaches_the_filesystem(tmp_path):
    """The same `_parts` rules as everything else in this module, applied at the read. A
    read is not a write and still cannot be allowed to walk out of the repository."""

    root = _root(tmp_path)
    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        for bad in ("../outside.md", "/etc/passwd", "specs/../../x", "specs//a.md"):
            with pytest.raises(transaction.Unsafe):
                writer.read(bad, maximum=100)


def test_a_pending_entry_is_re_proved_before_it_can_publish(tmp_path):
    """The clean control for the six checks below: an untouched pending entry publishes."""

    root = _root(tmp_path)
    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        pending = writer.stage(writer.inventory(), "pending-ok", "spec.md", b"body\n")
        writer.publish(pending, "001-ok")

    assert (root / "specs" / "001-ok" / "spec.md").read_bytes() == b"body\n"


def test_a_pending_file_edited_after_staging_is_refused_at_publish(tmp_path):
    """The bytes are re-read and compared, not trusted from the stage. Between staging and
    publishing there is a window, and this is a directory inside the repository that
    anything with the person's permissions can write to."""

    root = _root(tmp_path)
    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        pending = writer.stage(writer.inventory(), "pending-edited", "spec.md", b"body\n")
        (root / "specs" / "pending-edited" / "spec.md").write_bytes(b"other\n")

        with pytest.raises(transaction.Unsafe):
            writer.publish(pending, "001-edited")

    assert not (root / "specs" / "001-edited").exists()


def test_a_pending_file_replaced_with_a_different_file_is_refused(tmp_path):
    """Same bytes, different inode. Identity is checked as well as content, because a
    replacement carrying identical bytes is still a file this transaction did not write —
    and the next thing that happens to it is a rename nobody can undo."""

    root = _root(tmp_path)
    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        pending = writer.stage(writer.inventory(), "pending-swapped", "spec.md", b"body\n")
        here = root / "specs" / "pending-swapped" / "spec.md"
        replacement = root / "specs" / "pending-swapped" / "other"
        replacement.write_bytes(b"body\n")
        replacement.replace(here)

        with pytest.raises(transaction.Unsafe):
            writer.publish(pending, "001-swapped")


def test_an_extra_file_appearing_beside_the_pending_one_is_refused(tmp_path):
    """The name set is compared exactly, not searched for the expected one. A directory that
    gained a file is a directory somebody wrote to, and publishing it would make whatever
    they left part of the spec."""

    root = _root(tmp_path)
    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        pending = writer.stage(writer.inventory(), "pending-extra", "spec.md", b"body\n")
        (root / "specs" / "pending-extra" / "surprise.md").write_bytes(b"x\n")

        with pytest.raises(transaction.Unsafe):
            writer.publish(pending, "001-extra")


def test_a_pending_directory_replaced_wholesale_is_refused(tmp_path):
    """The directory's own identity, checked first. Recreating it with the right name and
    the right file inside would pass every content check and still be a directory this
    transaction never made."""

    root = _root(tmp_path)
    with transaction.writer(root, ".ai/intent.md", "specs") as writer:
        pending = writer.stage(writer.inventory(), "pending-remade", "spec.md", b"body\n")
        here = root / "specs" / "pending-remade"
        (here / "spec.md").unlink()
        here.rmdir()
        here.mkdir()
        (here / "spec.md").write_bytes(b"body\n")

        with pytest.raises(transaction.Unsafe):
            writer.publish(pending, "001-remade")
