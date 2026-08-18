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
import sys

import pytest

from ai_engineering import spec_transaction as transaction


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
