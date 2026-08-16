"""Native, fail-closed filesystem primitives for publishing one directory without replacing
anything. Two callers use it: `spec new`, whose home is `specs`, and the acceptance writer,
whose home is `specs/NNN-slug` beside the spec the decision belongs to. The module keeps its
original name; renaming it would drag a second product home into one commit, and the scope
this sentence states is the honest version of that trade."""

from __future__ import annotations

import contextlib
import ctypes
import errno
import os
import stat
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any


class TransactionError(RuntimeError):
    """A native transaction boundary could not be proved safe."""


class Busy(TransactionError):
    """Another writer owns the existing authority-file lock."""


class Unsafe(TransactionError):
    """A path, identity, byte, or postcondition check was inconclusive."""


class Collision(TransactionError):
    """A no-replace create or publication found an existing entry."""


class Unsupported(TransactionError):
    """The host cannot provide the required native guarantee."""


@dataclass(frozen=True, slots=True)
class Generation:
    """Materialized identity and generation for one filesystem entry."""

    path: str
    identity: tuple[int, int]
    size: int
    mtime_ns: int
    ctime_ns: int


@dataclass(frozen=True, slots=True)
class Observation:
    """A bounded regular-file read and every parent generation used to reach it."""

    path: str
    body: bytes
    generation: Generation
    parents: tuple[Generation, ...]
    maximum: int


@dataclass(slots=True)
class Inventory:
    """A single-use exact snapshot of the retained canonical namespace."""

    names: tuple[str, ...]
    pending: tuple[str, ...]
    generation: Generation
    _owner: object = field(repr=False)
    consumed: bool = False


@dataclass(frozen=True, slots=True)
class Pending:
    """An owned, noncanonical staged directory."""

    name: str
    filename: str
    body: bytes
    directory_identity: tuple[int, int]
    file_identity: tuple[int, int]
    expected_names: tuple[str, ...]
    home_generation: Generation


@dataclass(frozen=True, slots=True)
class Published:
    """The expected identity and bytes at one canonical final entry."""

    name: str
    filename: str
    body: bytes
    directory_identity: tuple[int, int]
    file_identity: tuple[int, int]


@dataclass(slots=True)
class _PendingHandles:
    directory: int
    child: int
    # `consumed` means the child handle is gone, so this pending can never be published
    # again. `published` means the rename actually committed. They are two facts because a
    # refused publication is the first without being the second, and the cleanup that has to
    # run in exactly that case cannot tell them apart from one flag.
    consumed: bool = False
    published: bool = False


_SPELLING_LIMIT = 4_096
_INVENTORY_LIMIT = 4_096


def _parts(value: str) -> tuple[str, ...]:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise Unsafe("path is not a canonical relative path")
    # Read the spelling before PurePosixPath normalizes it. `a/./b` and `a//b` drop their
    # empty and dot segments during parsing, so the check below would never see a spelling
    # this module exists to refuse.
    if any(segment in {"", ".", ".."} for segment in value.split("/")):
        raise Unsafe("path is not a canonical relative path")
    path = PurePosixPath(value)
    parts = path.parts
    if path.is_absolute() or not parts or any(part in {"", ".", ".."} for part in parts):
        raise Unsafe("path is not a canonical relative path")
    return parts


def _component(value: str, *, pending: bool = False) -> str:
    parts = _parts(value)
    if len(parts) != 1 or (pending and not value.startswith("pending-")):
        raise Unsafe("entry name is not canonical")
    return value


# A transaction home may be nested — `specs` for a spec, `specs/NNN-slug` for an acceptance
# record beside its spec — but it is never deep. The bound is here so that "walk it one
# component at a time" cannot become an unbounded walk of somebody else's directory tree.
_HOME_COMPONENT_LIMIT = 4


def _home_relative(value: str) -> str:
    parts = _parts(value)
    if len(parts) > _HOME_COMPONENT_LIMIT:
        raise Unsafe("transaction home is deeper than the bound")
    return "/".join(parts)


def _same_identity(left: Generation, right: Generation) -> bool:
    return left.identity == right.identity


def _stable_windows_identity(volume: int, file_id: bytes) -> tuple[int, int]:
    if not 0 < volume < 1 << 64 or len(file_id) != 16:
        raise Unsupported("filesystem returned no 64/128-bit file identity")
    identity = int.from_bytes(file_id, "little")
    if not identity:
        raise Unsupported("filesystem returned no 64/128-bit file identity")
    return volume, identity


def _generation_posix(path: str, value: os.stat_result) -> Generation:
    return Generation(
        path=path,
        identity=(value.st_dev, value.st_ino),
        size=value.st_size,
        mtime_ns=value.st_mtime_ns,
        ctime_ns=value.st_ctime_ns,
    )


def _directory_flags() -> int:
    required = ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")
    if not all(hasattr(os, name) for name in required):
        raise Unsupported("descriptor-relative no-follow directories are unavailable")
    return (
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
    )


def _file_flags(access: int) -> int:
    if not all(hasattr(os, name) for name in ("O_NOFOLLOW", "O_NONBLOCK")):
        raise Unsupported("nonblocking no-follow files are unavailable")
    return access | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)


def _translate_open(error: OSError, message: str) -> TransactionError:
    if error.errno in {errno.EEXIST, errno.ENOTEMPTY}:
        return Collision(message)
    if error.errno in {
        errno.ELOOP,
        errno.ENOTDIR,
        errno.ENOENT,
        errno.EACCES,
        errno.EPERM,
    }:
        return Unsafe(message)
    return Unsafe(f"{message}: native error {error.errno}")


def _bounded_directory_names(parent_fd: int, *, maximum: int = _SPELLING_LIMIT) -> tuple[str, ...]:
    names: list[str] = []
    try:
        with os.scandir(parent_fd) as entries:
            for count, entry in enumerate(entries, start=1):
                if count > maximum:
                    raise Unsafe("directory exceeds the bounded spelling check")
                names.append(entry.name)
    except TransactionError:
        raise
    except OSError as error:
        raise Unsafe(f"directory spelling could not be read: native error {error.errno}") from error
    return tuple(names)


def _require_exact_entry(parent_fd: int, name: str) -> None:
    if name not in _bounded_directory_names(parent_fd):
        raise Unsafe("filesystem resolved a missing or differently spelled entry")


def _require_descriptor_entry(parent_fd: int, name: str, descriptor: int) -> None:
    _require_exact_entry(parent_fd, name)
    try:
        linked = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        opened = os.fstat(descriptor)
    except OSError as error:
        raise Unsafe(
            f"opened entry identity could not be proved: native error {error.errno}"
        ) from error
    if (linked.st_dev, linked.st_ino) != (opened.st_dev, opened.st_ino):
        raise Unsafe("opened entry identity differs from its exact directory entry")


def _open_directory(parent_fd: int, name: str) -> int:
    _require_exact_entry(parent_fd, name)
    try:
        descriptor = os.open(name, _directory_flags(), dir_fd=parent_fd)
    except OSError as error:
        raise _translate_open(error, "directory could not be opened safely") from error
    try:
        value = os.fstat(descriptor)
    except OSError as error:
        os.close(descriptor)
        raise Unsafe(f"directory identity could not be read: native error {error.errno}") from error
    if not stat.S_ISDIR(value.st_mode):
        os.close(descriptor)
        raise Unsafe("opened entry is not a directory")
    try:
        _require_descriptor_entry(parent_fd, name, descriptor)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _open_absolute_directory(path: Path) -> int:
    if not path.is_absolute():
        raise Unsafe("transaction root is not absolute")
    try:
        current = os.open(os.path.sep, _directory_flags())
    except OSError as error:
        raise _translate_open(error, "filesystem root could not be opened safely") from error
    try:
        for part in path.parts[1:]:
            if part in {"", os.path.sep}:
                continue
            next_fd = _open_directory(current, part)
            os.close(current)
            current = next_fd
        return current
    except BaseException:
        os.close(current)
        raise


def _fsync(descriptor: int, message: str) -> None:
    try:
        os.fsync(descriptor)
    except OSError as error:
        raise Unsafe(f"{message}: native error {error.errno}") from error


class _PosixWriter:
    def __init__(self, root: Path, authority: str, home: str) -> None:
        self._root_path = Path(os.path.abspath(os.fspath(root)))
        self._authority = "/".join(_parts(authority))
        self._home = _home_relative(home)
        self._root_fd = -1
        self._home_fd = -1
        self._authority_fd = -1
        self._root_generation: Generation | None = None
        self._home_generation: Generation | None = None
        self._home_generations: tuple[Generation, ...] = ()
        self._authority_generation: Generation | None = None
        self._authority_parents: tuple[Generation, ...] = ()
        self._inventory_owner = object()

    def __enter__(self) -> _PosixWriter:
        if os.name != "posix":
            raise Unsupported("POSIX transaction backend is unavailable")
        try:
            self._root_fd = _open_absolute_directory(self._root_path)
            root_value = os.fstat(self._root_fd)
            self._root_generation = _generation_posix(".", root_value)
            self._home_fd, self._home_generations = self._walk_home(self._home)
            self._home_generation = self._home_generations[-1]
            self._authority_fd, self._authority_parents = self._open_regular(
                self._authority, os.O_RDONLY
            )
            self._authority_generation = _generation_posix(
                self._authority, os.fstat(self._authority_fd)
            )
            self._lock_authority()
            self._require_canonical_authority()
            self._require_canonical_home()
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *_error: object) -> None:
        for attribute in ("_authority_fd", "_home_fd", "_root_fd"):
            descriptor = getattr(self, attribute)
            if descriptor >= 0:
                with contextlib.suppress(OSError):
                    os.close(descriptor)
                setattr(self, attribute, -1)

    def _lock_authority(self) -> None:
        try:
            import fcntl
        except ImportError as error:
            raise Unsupported("kernel file locking is unavailable") from error
        try:
            fcntl.flock(self._authority_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            if error.errno in {errno.EACCES, errno.EAGAIN}:
                raise Busy("the authority file is locked by another writer") from error
            raise Unsafe(f"authority lock failed: native error {error.errno}") from error

    def _walk_parent(self, relative: str) -> tuple[int, str, tuple[Generation, ...]]:
        parts = _parts(relative)
        current = os.dup(self._root_fd)
        parents = [_generation_posix(".", os.fstat(current))]
        walked: list[str] = []
        try:
            for part in parts[:-1]:
                next_fd = _open_directory(current, part)
                os.close(current)
                current = next_fd
                walked.append(part)
                parents.append(_generation_posix("/".join(walked), os.fstat(current)))
            return current, parts[-1], tuple(parents)
        except BaseException:
            os.close(current)
            raise

    def _walk_home(
        self, relative: str, *, anchor: int | None = None
    ) -> tuple[int, tuple[Generation, ...]]:
        """Open the transaction home one exact component at a time, recording what each
        component was. A nested home has ancestors, and an ancestor that can be swapped
        between the opening walk and the revalidating walk is a hole no leaf check closes.
        """

        current = os.dup(self._root_fd if anchor is None else anchor)
        generations: list[Generation] = []
        walked: list[str] = []
        try:
            for part in _parts(relative):
                next_fd = _open_directory(current, part)
                os.close(current)
                current = next_fd
                walked.append(part)
                generations.append(_generation_posix("/".join(walked), os.fstat(current)))
            return current, tuple(generations)
        except BaseException:
            os.close(current)
            raise

    def _parent_generations(self, relative: str) -> tuple[Generation, ...]:
        parent_fd, _name, parents = self._walk_parent(relative)
        os.close(parent_fd)
        return parents

    def _open_regular(self, relative: str, access: int) -> tuple[int, tuple[Generation, ...]]:
        parent_fd, name, parents = self._walk_parent(relative)
        try:
            _require_exact_entry(parent_fd, name)
            descriptor = os.open(name, _file_flags(access), dir_fd=parent_fd)
        except OSError as error:
            os.close(parent_fd)
            raise _translate_open(error, "file could not be opened safely") from error
        except BaseException:
            os.close(parent_fd)
            raise
        try:
            _require_descriptor_entry(parent_fd, name, descriptor)
        except BaseException:
            os.close(descriptor)
            os.close(parent_fd)
            raise
        os.close(parent_fd)
        try:
            value = os.fstat(descriptor)
        except OSError as error:
            os.close(descriptor)
            raise Unsafe(f"file identity could not be read: native error {error.errno}") from error
        if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
            os.close(descriptor)
            raise Unsafe("opened entry is not one singly linked regular file")
        return descriptor, parents

    def _require_canonical_home(self) -> None:
        if self._root_generation is None or not self._home_generations:
            raise Unsafe("writer is not open")
        try:
            root_fd = _open_absolute_directory(self._root_path)
        except OSError as error:
            raise _translate_open(error, "canonical root changed") from error
        try:
            root_now = _generation_posix(".", os.fstat(root_fd))
            if not _same_identity(root_now, self._root_generation):
                raise Unsafe("canonical root identity changed")
            current, now = self._walk_home(self._home, anchor=root_fd)
            os.close(current)
            if len(now) != len(self._home_generations) or not all(
                _same_identity(seen, before)
                for seen, before in zip(now, self._home_generations, strict=True)
            ):
                raise Unsafe("canonical transaction home identity changed")
        finally:
            os.close(root_fd)

    def _require_canonical_authority(self) -> None:
        if self._authority_generation is None:
            raise Unsafe("writer has no locked authority generation")
        descriptor, parents = self._open_regular(self._authority, os.O_RDONLY)
        try:
            locked = _generation_posix(self._authority, os.fstat(self._authority_fd))
            canonical = _generation_posix(self._authority, os.fstat(descriptor))
            if (
                locked != self._authority_generation
                or canonical != self._authority_generation
                or parents != self._authority_parents
            ):
                raise Unsafe("canonical authority changed outside its writer lock")
        finally:
            os.close(descriptor)

    def read(self, relative: str, *, maximum: int) -> Observation:
        if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 0:
            raise Unsafe("read bound is invalid")
        canonical = "/".join(_parts(relative))
        if canonical == self._authority:
            self._require_canonical_authority()
        descriptor, parents = self._open_regular(canonical, os.O_RDONLY)
        try:
            before_value = os.fstat(descriptor)
            before = _generation_posix(canonical, before_value)
            if canonical == self._authority and (
                before != self._authority_generation or parents != self._authority_parents
            ):
                raise Unsafe("read did not use the locked canonical authority")
            if before.size > maximum:
                raise Unsafe("regular file exceeds its read bound")
            chunks: list[bytes] = []
            remaining = maximum + 1
            while remaining:
                chunk = os.read(descriptor, min(65_536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            body = b"".join(chunks)
            if len(body) > maximum:
                raise Unsafe("regular file changed beyond its read bound")
            after = _generation_posix(canonical, os.fstat(descriptor))
            if (
                before != after
                or len(body) != before.size
                or self._parent_generations(canonical) != parents
            ):
                raise Unsafe("regular file changed while it was read")
            return Observation(canonical, body, after, parents, maximum)
        except BlockingIOError as error:
            raise Unsafe("regular file read would block") from error
        finally:
            os.close(descriptor)

    def unchanged(self, observation: Observation) -> bool:
        try:
            return self.read(observation.path, maximum=observation.maximum) == observation
        except TransactionError:
            return False

    def _inventory_snapshot(self) -> tuple[tuple[str, ...], Generation]:
        try:
            before = _generation_posix(self._home, os.fstat(self._home_fd))
            names = tuple(sorted(_bounded_directory_names(self._home_fd, maximum=_INVENTORY_LIMIT)))
            after = _generation_posix(self._home, os.fstat(self._home_fd))
        except TransactionError:
            raise
        except OSError as error:
            raise Unsafe(
                f"transaction namespace could not be inventoried: native error {error.errno}"
            ) from error
        if before != after:
            raise Unsafe("transaction namespace changed while it was inventoried")
        return names, after

    def inventory(self) -> Inventory:
        self._require_canonical_authority()
        self._require_canonical_home()
        names, generation = self._inventory_snapshot()
        pending = tuple(name for name in names if name.startswith("pending-"))
        return Inventory(names, pending, generation, self._inventory_owner)

    def _consume_inventory(self, inventory: Inventory) -> tuple[str, ...]:
        if (
            not isinstance(inventory, Inventory)
            or inventory._owner is not self._inventory_owner
            or inventory.consumed
        ):
            raise Unsafe("inventory is not an unused capability from this writer")
        self._require_canonical_authority()
        self._require_canonical_home()
        names, generation = self._inventory_snapshot()
        if names != inventory.names or generation != inventory.generation:
            raise Unsafe("transaction namespace changed after inventory")
        inventory.consumed = True
        return names

    def stage(self, inventory: Inventory, name: str, filename: str, body: bytes) -> Pending:
        name = _component(name, pending=True)
        filename = _component(filename)
        if not isinstance(body, bytes):
            raise Unsafe("staged content must be bytes")
        names = self._consume_inventory(inventory)
        expected_names = tuple(sorted((*names, name)))
        try:
            os.mkdir(name, mode=0o700, dir_fd=self._home_fd)
        except OSError as error:
            raise _translate_open(error, "pending directory could not be created") from error
        pending_fd = _open_directory(self._home_fd, name)
        file_fd = -1
        try:
            flags = _file_flags(os.O_WRONLY | os.O_CREAT | os.O_EXCL)
            try:
                file_fd = os.open(filename, flags, 0o600, dir_fd=pending_fd)
            except OSError as error:
                raise _translate_open(error, "pending file could not be created") from error
            _require_descriptor_entry(pending_fd, filename, file_fd)
            view = memoryview(body)
            while view:
                try:
                    written = os.write(file_fd, view)
                except BlockingIOError as error:
                    raise Unsafe("pending file write would block") from error
                if written <= 0:
                    raise Unsafe("pending file write made no progress")
                view = view[written:]
            _fsync(file_fd, "pending file could not be flushed")
            file_value = os.fstat(file_fd)
            if not stat.S_ISREG(file_value.st_mode) or file_value.st_nlink != 1:
                raise Unsafe("pending file is not one singly linked regular file")
            file_identity = (file_value.st_dev, file_value.st_ino)
            _fsync(pending_fd, "pending directory could not be flushed")
            _fsync(self._home_fd, "transaction home could not be flushed")
            directory_value = os.fstat(pending_fd)
            actual_names, home_generation = self._inventory_snapshot()
            if actual_names != expected_names:
                raise Unsafe("transaction namespace changed while pending was staged")
            return Pending(
                name,
                filename,
                body,
                (directory_value.st_dev, directory_value.st_ino),
                file_identity,
                expected_names,
                home_generation,
            )
        except BaseException:
            # The directory exists from the `mkdir` above, so every failure below this line
            # leaves it behind — a flush that fails, a namespace that moves, an interrupt.
            # A leftover `pending-` wedges its ordinal for good: the next attempt allocates
            # the same name and cannot create it. The caller's cleanup only starts once
            # `stage` has returned, so this window is `stage`'s own to close.
            with contextlib.suppress(OSError):
                os.unlink(filename, dir_fd=pending_fd)
            with contextlib.suppress(OSError):
                os.rmdir(name, dir_fd=self._home_fd)
            raise
        finally:
            if file_fd >= 0:
                os.close(file_fd)
            os.close(pending_fd)

    def _require_pending(self, pending: Pending) -> None:
        pending_fd = _open_directory(self._home_fd, _component(pending.name, pending=True))
        file_fd = -1
        try:
            directory_value = os.fstat(pending_fd)
            if (directory_value.st_dev, directory_value.st_ino) != pending.directory_identity:
                raise Unsafe("pending directory identity changed")
            names = _bounded_directory_names(pending_fd)
            if names != (pending.filename,):
                raise Unsafe("pending directory contents changed")
            try:
                file_fd = os.open(
                    _component(pending.filename), _file_flags(os.O_RDONLY), dir_fd=pending_fd
                )
            except OSError as error:
                raise _translate_open(error, "pending file could not be reopened") from error
            file_value = os.fstat(file_fd)
            if (
                not stat.S_ISREG(file_value.st_mode)
                or file_value.st_nlink != 1
                or (file_value.st_dev, file_value.st_ino) != pending.file_identity
                or file_value.st_size != len(pending.body)
            ):
                raise Unsafe("pending file identity changed")
            if _read_exact_posix(file_fd, len(pending.body)) != pending.body:
                raise Unsafe("pending file bytes changed")
        finally:
            if file_fd >= 0:
                os.close(file_fd)
            os.close(pending_fd)

    def discard(self, pending: Pending) -> None:
        """Remove only the staging entry this writer created.

        There is still no pathname cleanup API here, and there will not be: a caller able to
        name any path for removal is a caller able to remove somebody else's. This proves
        the entry is the one it staged — same directory identity, same file identity, same
        bytes — and then removes it through the home descriptor it already holds. The
        residual window is narrow and named: between that proof and the `rmdir`, only an
        empty directory at the owned name can be removed at all.
        """

        self._require_canonical_authority()
        self._require_canonical_home()
        self._require_pending(pending)
        pending_fd = _open_directory(self._home_fd, _component(pending.name, pending=True))
        try:
            value = os.fstat(pending_fd)
            if (value.st_dev, value.st_ino) != pending.directory_identity:
                raise Unsafe("pending directory identity changed")
            try:
                os.unlink(pending.filename, dir_fd=pending_fd)
            except OSError as error:
                raise _translate_open(error, "pending file could not be removed") from error
        finally:
            os.close(pending_fd)
        try:
            os.rmdir(pending.name, dir_fd=self._home_fd)
        except OSError as error:
            raise _translate_open(error, "pending directory could not be removed") from error

    def publish(self, pending: Pending, final: str) -> Published:
        final = _component(final)
        self._require_canonical_authority()
        self._require_pending(pending)
        self._require_canonical_home()
        names, generation = self._inventory_snapshot()
        if names != pending.expected_names or generation != pending.home_generation:
            raise Unsafe("transaction namespace changed after pending was staged")
        published = Published(
            final,
            pending.filename,
            pending.body,
            pending.directory_identity,
            pending.file_identity,
        )
        _publish_noreplace("posix", self._home_fd, pending.name, self._home_fd, final)
        return published


def _read_exact_posix(descriptor: int, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size + 1
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
    except (BlockingIOError, OSError) as error:
        raise Unsafe("regular file could not be reread without blocking") from error
    body = b"".join(chunks)
    if len(body) != size:
        raise Unsafe("regular file length changed")
    return body


def _rename_noreplace_posix(
    source_fd: int, source: str, destination_fd: int, destination: str
) -> None:
    """Publish one directory with the host's native exclusive rename primitive."""
    if os.name != "posix":
        raise Unsupported("POSIX exclusive rename is unavailable")
    library = ctypes.CDLL(None, use_errno=True)
    encoded_source = os.fsencode(source)
    encoded_destination = os.fsencode(destination)
    if sys.platform.startswith("linux"):
        function = getattr(library, "renameat2", None)
        flag = 1  # RENAME_NOREPLACE
    elif sys.platform == "darwin":
        function = getattr(library, "renameatx_np", None)
        flag = 0x00000004  # RENAME_EXCL
    else:
        raise Unsupported("host has no supported exclusive directory rename")
    if function is None:
        raise Unsupported("native exclusive directory rename symbol is unavailable")
    function.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    function.restype = ctypes.c_int
    ctypes.set_errno(0)
    result = function(source_fd, encoded_source, destination_fd, encoded_destination, flag)
    if result == 0:
        return
    code = ctypes.get_errno()
    if code in {errno.EEXIST, errno.ENOTEMPTY}:
        raise Collision("canonical destination already exists")
    unsupported = {errno.EINVAL, errno.ENOSYS}
    unsupported.update(
        value
        for value in (getattr(errno, "ENOTSUP", None), getattr(errno, "EOPNOTSUPP", None))
        if value is not None
    )
    if code in unsupported:
        raise Unsupported("filesystem cannot publish with no-replace semantics")
    raise Unsafe(f"exclusive directory publish failed: native error {code}")


def _publish_noreplace(
    backend: str,
    source_handle: int,
    source_name: str | None,
    home_handle: int,
    final: str,
) -> None:
    """The single platform seam whose native rename is the final publication syscall."""
    if backend == "posix" and source_name is not None:
        _rename_noreplace_posix(source_handle, source_name, home_handle, final)
        return
    if backend == "windows" and source_name is None:
        function = globals().get("_win_publish")
        if callable(function):
            function(source_handle, home_handle, final)
            return
        raise Unsupported("Windows handle rename is unavailable")
    raise Unsupported("native publication backend contract is invalid")


def _publish_windows_pending(
    state: _PendingHandles,
    home_handle: int,
    final: str,
    close_child: Any,
) -> None:
    if state.consumed or not state.child:
        raise Unsafe("pending Windows publication has already been consumed")
    if not close_child(state.child):
        raise Unsafe("pending child handle could not be closed before publication")
    state.child = 0
    state.consumed = True
    _publish_noreplace("windows", state.directory, None, home_handle, final)
    state.published = True


# The Windows backend uses NT relative opens so staging cannot be redirected through a
# renamed parent. The small wrappers stay here because optional packages would make the
# publication guarantee depend on the environment being repaired.
if sys.platform == "win32":
    from ctypes import wintypes

    _INVALID_HANDLE = ctypes.c_void_p(-1).value
    _FILE_ATTRIBUTE_DIRECTORY = 0x10
    _FILE_ATTRIBUTE_REPARSE_POINT = 0x400
    _FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    _FILE_LIST_DIRECTORY = 0x0001
    _FILE_READ_ATTRIBUTES = 0x0080
    _SYNCHRONIZE = 0x00100000
    _DELETE = 0x00010000
    _GENERIC_READ = 0x80000000
    _GENERIC_WRITE = 0x40000000
    _FILE_SHARE_READ = 0x1
    _FILE_SHARE_WRITE = 0x2
    _OPEN_EXISTING = 3
    _LOCKFILE_FAIL_IMMEDIATELY = 0x1
    _LOCKFILE_EXCLUSIVE_LOCK = 0x2
    _FILE_CREATE = 2
    _FILE_OPEN = 1
    _FILE_DIRECTORY_FILE = 0x1
    _FILE_NON_DIRECTORY_FILE = 0x40
    _FILE_SYNCHRONOUS_IO_NONALERT = 0x20
    _FILE_OPEN_REPARSE_POINT = 0x00200000
    _FILE_TYPE_DISK = 0x1
    _ERROR_NO_MORE_FILES = 18
    _FILE_BEGIN = 0

    class _FILE_BASIC_INFO(ctypes.Structure):
        _fields_ = [
            ("creation_time", ctypes.c_longlong),
            ("last_access_time", ctypes.c_longlong),
            ("last_write_time", ctypes.c_longlong),
            ("change_time", ctypes.c_longlong),
            ("attributes", wintypes.DWORD),
        ]

    class _FILE_STANDARD_INFO(ctypes.Structure):
        _fields_ = [
            ("allocation_size", ctypes.c_longlong),
            ("end_of_file", ctypes.c_longlong),
            ("number_of_links", wintypes.DWORD),
            ("delete_pending", wintypes.BYTE),
            ("directory", wintypes.BYTE),
        ]

    class _FILE_ID_128(ctypes.Structure):
        _fields_ = [("identifier", wintypes.BYTE * 16)]

    class _FILE_ID_INFO(ctypes.Structure):
        _fields_ = [
            ("volume_serial_number", ctypes.c_ulonglong),
            ("file_id", _FILE_ID_128),
        ]

    class _OVERLAPPED(ctypes.Structure):
        _fields_ = [
            ("internal", ctypes.c_void_p),
            ("internal_high", ctypes.c_void_p),
            ("offset", wintypes.DWORD),
            ("offset_high", wintypes.DWORD),
            ("event", wintypes.HANDLE),
        ]

    class _UNICODE_STRING(ctypes.Structure):
        _fields_ = [
            ("length", wintypes.USHORT),
            ("maximum_length", wintypes.USHORT),
            ("buffer", wintypes.LPWSTR),
        ]

    class _OBJECT_ATTRIBUTES(ctypes.Structure):
        _fields_ = [
            ("length", wintypes.ULONG),
            ("root_directory", wintypes.HANDLE),
            ("object_name", ctypes.POINTER(_UNICODE_STRING)),
            ("attributes", wintypes.ULONG),
            ("security_descriptor", ctypes.c_void_p),
            ("security_quality_of_service", ctypes.c_void_p),
        ]

    class _IO_STATUS_BLOCK(ctypes.Structure):
        _fields_ = [("status", ctypes.c_void_p), ("information", ctypes.c_size_t)]

    class _FILE_RENAME_INFO(ctypes.Structure):
        _fields_ = [
            ("replace_if_exists", wintypes.BOOL),
            ("root_directory", wintypes.HANDLE),
            ("file_name_length", wintypes.DWORD),
            ("file_name", wintypes.WCHAR * 1),
        ]

    class _FILE_ID_BOTH_DIR_INFO(ctypes.Structure):
        _fields_ = [
            ("next_entry_offset", wintypes.DWORD),
            ("file_index", wintypes.DWORD),
            ("creation_time", ctypes.c_longlong),
            ("last_access_time", ctypes.c_longlong),
            ("last_write_time", ctypes.c_longlong),
            ("change_time", ctypes.c_longlong),
            ("end_of_file", ctypes.c_longlong),
            ("allocation_size", ctypes.c_longlong),
            ("attributes", wintypes.DWORD),
            ("file_name_length", wintypes.DWORD),
            ("ea_size", wintypes.DWORD),
            ("short_name_length", ctypes.c_byte),
            ("short_name", wintypes.WCHAR * 12),
            ("file_id", ctypes.c_longlong),
            ("file_name", wintypes.WCHAR * 1),
        ]

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _ntdll = ctypes.WinDLL("ntdll")

    _kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    _kernel32.CreateFileW.restype = wintypes.HANDLE
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _kernel32.CloseHandle.restype = wintypes.BOOL
    _kernel32.GetFileInformationByHandleEx.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    _kernel32.GetFileInformationByHandleEx.restype = wintypes.BOOL
    _kernel32.GetFileSizeEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    _kernel32.GetFileSizeEx.restype = wintypes.BOOL
    _kernel32.GetFileType.argtypes = [wintypes.HANDLE]
    _kernel32.GetFileType.restype = wintypes.DWORD
    _kernel32.SetFilePointerEx.argtypes = [
        wintypes.HANDLE,
        ctypes.c_longlong,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    _kernel32.SetFilePointerEx.restype = wintypes.BOOL
    _kernel32.LockFileEx.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
    ]
    _kernel32.LockFileEx.restype = wintypes.BOOL
    _kernel32.ReadFile.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    _kernel32.ReadFile.restype = wintypes.BOOL
    _kernel32.WriteFile.argtypes = _kernel32.ReadFile.argtypes
    _kernel32.WriteFile.restype = wintypes.BOOL
    _kernel32.FlushFileBuffers.argtypes = [wintypes.HANDLE]
    _kernel32.FlushFileBuffers.restype = wintypes.BOOL
    _kernel32.SetFileInformationByHandle.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    _kernel32.SetFileInformationByHandle.restype = wintypes.BOOL
    _ntdll.NtCreateFile.argtypes = [
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    _ntdll.NtCreateFile.restype = wintypes.LONG
    _ntdll.RtlNtStatusToDosError.argtypes = [wintypes.LONG]
    _ntdll.RtlNtStatusToDosError.restype = wintypes.ULONG


def _windows_unavailable() -> Unsupported:
    return Unsupported("Windows native transaction APIs are unavailable")


if sys.platform == "win32":

    def _win_close(handle: int) -> bool:
        if handle not in {0, _INVALID_HANDLE}:
            return bool(_kernel32.CloseHandle(wintypes.HANDLE(handle)))
        return True

    def _win_error(message: str, code: int | None = None) -> TransactionError:
        value = ctypes.get_last_error() if code is None else code
        if value in {32, 33}:
            return Busy(message)
        if value in {80, 183}:
            return Collision(message)
        if value in {1, 50, 87, 120}:
            return Unsupported(message)
        return Unsafe(f"{message}: native error {value}")

    def _win_directory_names(handle: int, *, maximum: int = _SPELLING_LIMIT) -> tuple[str, ...]:
        names: list[str] = []
        information_class = 11  # FileIdBothDirectoryRestartInfo
        while len(names) <= maximum:
            raw = ctypes.create_string_buffer(65_536)
            if not _kernel32.GetFileInformationByHandleEx(
                handle, information_class, raw, ctypes.sizeof(raw)
            ):
                code = ctypes.get_last_error()
                if code == _ERROR_NO_MORE_FILES:
                    return tuple(names)
                raise _win_error("directory contents could not be enumerated", code)
            information_class = 10  # FileIdBothDirectoryInfo
            offset = 0
            while True:
                if offset + ctypes.sizeof(_FILE_ID_BOTH_DIR_INFO) > ctypes.sizeof(raw):
                    raise Unsafe("directory enumeration returned an invalid record")
                address = ctypes.addressof(raw) + offset
                entry = ctypes.cast(address, ctypes.POINTER(_FILE_ID_BOTH_DIR_INFO)).contents
                if entry.file_name_length % 2:
                    raise Unsafe("directory enumeration returned an invalid name")
                name_end = offset + _FILE_ID_BOTH_DIR_INFO.file_name.offset + entry.file_name_length
                if name_end > ctypes.sizeof(raw):
                    raise Unsafe("directory enumeration exceeded its native buffer")
                name = ctypes.wstring_at(
                    address + _FILE_ID_BOTH_DIR_INFO.file_name.offset,
                    entry.file_name_length // 2,
                )
                if name not in {".", ".."}:
                    names.append(name)
                if len(names) > maximum:
                    raise Unsafe("directory contains more entries than the bounded transaction")
                if entry.next_entry_offset == 0:
                    break
                if entry.next_entry_offset < _FILE_ID_BOTH_DIR_INFO.file_name.offset:
                    raise Unsafe("directory enumeration returned an invalid offset")
                offset += entry.next_entry_offset
        raise Unsafe("directory enumeration exceeded its bound")

    def _win_generation(handle: int, path: str) -> Generation:
        basic = _FILE_BASIC_INFO()
        standard = _FILE_STANDARD_INFO()
        identity_info = _FILE_ID_INFO()
        if not _kernel32.GetFileInformationByHandleEx(
            handle, 0, ctypes.byref(basic), ctypes.sizeof(basic)
        ):
            raise _win_error("file generation could not be read")
        if not _kernel32.GetFileInformationByHandleEx(
            handle, 1, ctypes.byref(standard), ctypes.sizeof(standard)
        ):
            raise _win_error("file shape could not be read")
        if not _kernel32.GetFileInformationByHandleEx(
            handle, 18, ctypes.byref(identity_info), ctypes.sizeof(identity_info)
        ):
            code = ctypes.get_last_error()
            if code in {1, 50, 87, 120}:
                raise Unsupported("filesystem has no stable 128-bit file identity")
            raise _win_error("128-bit file identity could not be read", code)
        if basic.attributes & _FILE_ATTRIBUTE_REPARSE_POINT:
            raise Unsafe("reparse points are not transaction entries")
        is_directory = bool(basic.attributes & _FILE_ATTRIBUTE_DIRECTORY)
        if standard.delete_pending or bool(standard.directory) != is_directory:
            raise Unsafe("opened entry has an unstable filesystem shape")
        if not is_directory and (
            standard.number_of_links != 1 or _kernel32.GetFileType(handle) != _FILE_TYPE_DISK
        ):
            raise Unsafe("opened entry is not one singly linked regular file")
        identity = _stable_windows_identity(
            int(identity_info.volume_serial_number), bytes(identity_info.file_id.identifier)
        )
        size = int(standard.end_of_file)
        return Generation(
            path, identity, size, basic.last_write_time * 100, basic.change_time * 100
        )

    def _win_component(value: str) -> str:
        value = _component(value)
        if value[-1] in {" ", "."} or any(mark in value for mark in '<>:"|?*'):
            raise Unsafe("entry name has a Windows filesystem alias")
        stem = value.split(".", 1)[0].upper()
        reserved = {"CON", "PRN", "AUX", "NUL"}
        reserved.update(f"COM{number}" for number in range(1, 10))
        reserved.update(f"LPT{number}" for number in range(1, 10))
        if stem in reserved:
            raise Unsafe("entry name is a reserved Windows filesystem alias")
        return value

    def _win_open_root(path: Path) -> int:
        drive, tail = os.path.splitdrive(os.fspath(path))
        if len(drive) != 2 or drive[1] != ":" or not tail.startswith(("\\", "/")):
            raise Unsupported("transaction root is not on a canonical local Windows volume")
        handle = _kernel32.CreateFileW(
            drive + "\\",
            _FILE_LIST_DIRECTORY | _FILE_READ_ATTRIBUTES | _SYNCHRONIZE,
            _FILE_SHARE_READ | _FILE_SHARE_WRITE,
            None,
            _OPEN_EXISTING,
            _FILE_FLAG_BACKUP_SEMANTICS | _FILE_FLAG_OPEN_REPARSE_POINT,
            None,
        )
        if handle == _INVALID_HANDLE:
            raise _win_error("canonical volume root could not be opened")
        try:
            _win_generation(handle, ".")
            for part in tail.replace("\\", "/").split("/"):
                if not part:
                    continue
                next_handle = _win_nt_open(handle, part, directory=True)
                _win_close(handle)
                handle = next_handle
            return handle
        except BaseException:
            _win_close(handle)
            raise

    def _win_nt_open(
        parent: int,
        name: str,
        *,
        directory: bool,
        create: bool = False,
        write: bool = False,
        delete: bool = False,
    ) -> int:
        name = _win_component(name)
        buffer = ctypes.create_unicode_buffer(name)
        encoded_bytes = len(name.encode("utf-16-le"))
        unicode_name = _UNICODE_STRING(encoded_bytes, encoded_bytes, buffer)
        attributes = _OBJECT_ATTRIBUTES(
            ctypes.sizeof(_OBJECT_ATTRIBUTES),
            wintypes.HANDLE(parent),
            ctypes.pointer(unicode_name),
            0,
            None,
            None,
        )
        status_block = _IO_STATUS_BLOCK()
        result = wintypes.HANDLE()
        access = _FILE_READ_ATTRIBUTES | _SYNCHRONIZE
        if directory:
            access |= _FILE_LIST_DIRECTORY
        else:
            access |= _GENERIC_READ | (_GENERIC_WRITE if write else 0)
        if delete:
            access |= _DELETE
        options = _FILE_SYNCHRONOUS_IO_NONALERT | _FILE_OPEN_REPARSE_POINT
        options |= _FILE_DIRECTORY_FILE if directory else _FILE_NON_DIRECTORY_FILE
        status = _ntdll.NtCreateFile(
            ctypes.byref(result),
            access,
            ctypes.byref(attributes),
            ctypes.byref(status_block),
            None,
            0,
            _FILE_SHARE_READ | (_FILE_SHARE_WRITE if directory else 0),
            _FILE_CREATE if create else _FILE_OPEN,
            options,
            None,
            0,
        )
        if status < 0:
            code = _ntdll.RtlNtStatusToDosError(status)
            raise _win_error("relative native open failed", code)
        handle = result.value
        try:
            _win_generation(handle, name)
            if name not in _win_directory_names(parent):
                raise Unsafe("relative open used a filesystem name alias")
        except BaseException:
            _win_close(handle)
            raise
        return handle

    def _win_write(handle: int, body: bytes) -> None:
        offset = 0
        while offset < len(body):
            chunk = body[offset : offset + 65_536]
            written = wintypes.DWORD()
            buffer = ctypes.create_string_buffer(chunk)
            if not _kernel32.WriteFile(handle, buffer, len(chunk), ctypes.byref(written), None):
                raise _win_error("pending file write failed")
            if written.value == 0:
                raise Unsafe("pending file write made no progress")
            offset += written.value
        if not _kernel32.FlushFileBuffers(handle):
            raise _win_error("pending file could not be flushed")

    def _win_read(handle: int, maximum: int) -> bytes:
        if not _kernel32.SetFilePointerEx(handle, 0, None, _FILE_BEGIN):
            raise _win_error("regular file position could not be reset")
        size = ctypes.c_longlong()
        if not _kernel32.GetFileSizeEx(handle, ctypes.byref(size)):
            raise _win_error("regular file size could not be read")
        if size.value < 0 or size.value > maximum:
            raise Unsafe("regular file exceeds its read bound")
        body = bytearray()
        while len(body) <= maximum:
            wanted = min(65_536, maximum + 1 - len(body))
            if wanted == 0:
                break
            buffer = ctypes.create_string_buffer(wanted)
            read = wintypes.DWORD()
            if not _kernel32.ReadFile(handle, buffer, wanted, ctypes.byref(read), None):
                raise _win_error("regular file read failed")
            if read.value == 0:
                break
            body.extend(buffer.raw[: read.value])
        if len(body) > maximum or len(body) != size.value:
            raise Unsafe("regular file changed while it was read")
        return bytes(body)

    def _win_publish(handle: int, home_handle: int, final: str) -> None:
        encoded = final.encode("utf-16-le")
        size = ctypes.sizeof(_FILE_RENAME_INFO) + len(encoded)
        raw = ctypes.create_string_buffer(size)
        info = ctypes.cast(raw, ctypes.POINTER(_FILE_RENAME_INFO)).contents
        info.replace_if_exists = False
        info.root_directory = wintypes.HANDLE(home_handle)
        info.file_name_length = len(encoded)
        ctypes.memmove(
            ctypes.addressof(raw) + _FILE_RENAME_INFO.file_name.offset, encoded, len(encoded)
        )
        if not _kernel32.SetFileInformationByHandle(handle, 3, raw, size):
            raise _win_error("exclusive directory publish failed")

    class _WindowsWriter:
        def __init__(self, root: Path, authority: str, home: str) -> None:
            self._root_path = Path(os.path.abspath(os.fspath(root)))
            self._authority = "/".join(_parts(authority))
            self._home = _home_relative(home)
            self._root = 0
            self._home_handle = 0
            self._authority_handle = 0
            self._root_generation: Generation | None = None
            self._home_generation: Generation | None = None
            self._home_generations: tuple[Generation, ...] = ()
            self._authority_generation: Generation | None = None
            self._authority_parents: tuple[Generation, ...] = ()
            self._pending_handles: dict[tuple[int, int], _PendingHandles] = {}
            self._inventory_owner = object()

        def __enter__(self) -> _WindowsWriter:
            try:
                self._root = _win_open_root(self._root_path)
                self._root_generation = _win_generation(self._root, ".")
                self._home_handle, home_parents = self._walk_directory(self._home)
                self._home_generations = home_parents[1:]
                self._home_generation = self._home_generations[-1]
                parent, name, self._authority_parents = self._walk_parent(self._authority)
                try:
                    self._authority_handle = _win_nt_open(parent, name, directory=False)
                finally:
                    if parent != self._root:
                        _win_close(parent)
                self._authority_generation = _win_generation(
                    self._authority_handle, self._authority
                )
                overlap = _OVERLAPPED()
                if not _kernel32.LockFileEx(
                    self._authority_handle,
                    _LOCKFILE_EXCLUSIVE_LOCK | _LOCKFILE_FAIL_IMMEDIATELY,
                    0,
                    0xFFFFFFFF,
                    0xFFFFFFFF,
                    ctypes.byref(overlap),
                ):
                    raise _win_error("the authority file could not be locked")
                self._require_canonical_authority()
                self._require_canonical_home()
                return self
            except BaseException:
                self.__exit__(None, None, None)
                raise

        def __exit__(self, *_error: object) -> None:
            for state in self._pending_handles.values():
                _win_close(state.child)
                _win_close(state.directory)
            self._pending_handles.clear()
            for attribute in ("_authority_handle", "_home_handle", "_root"):
                _win_close(getattr(self, attribute))
                setattr(self, attribute, 0)

        def _walk_directory(self, relative: str) -> tuple[int, tuple[Generation, ...]]:
            current = self._root
            owned = False
            parents = [self._root_generation or _win_generation(current, ".")]
            walked: list[str] = []
            try:
                for part in _parts(relative):
                    next_handle = _win_nt_open(current, part, directory=True)
                    if owned:
                        _win_close(current)
                    current = next_handle
                    owned = True
                    walked.append(part)
                    parents.append(_win_generation(current, "/".join(walked)))
                return current, tuple(parents)
            except BaseException:
                if owned:
                    _win_close(current)
                raise

        def _walk_parent(self, relative: str) -> tuple[int, str, tuple[Generation, ...]]:
            parts = _parts(relative)
            if len(parts) == 1:
                return self._root, parts[0], (self._root_generation,)
            handle, parents = self._walk_directory("/".join(parts[:-1]))
            return handle, parts[-1], parents

        def _parent_generations(self, relative: str) -> tuple[Generation, ...]:
            parent, _name, parents = self._walk_parent(relative)
            if parent != self._root:
                _win_close(parent)
            return parents

        def _require_canonical_home(self) -> None:
            if self._root_generation is None or not self._home_generations:
                raise Unsafe("writer is not open")
            root = _win_open_root(self._root_path)
            try:
                if not _same_identity(_win_generation(root, "."), self._root_generation):
                    raise Unsafe("canonical root identity changed")
            finally:
                _win_close(root)
            home, parents = self._walk_directory(self._home)
            try:
                now = parents[1:]
                if len(now) != len(self._home_generations) or not all(
                    _same_identity(seen, before)
                    for seen, before in zip(now, self._home_generations, strict=True)
                ):
                    raise Unsafe("canonical transaction home identity changed")
            finally:
                _win_close(home)

        def _require_canonical_authority(self) -> None:
            if self._authority_generation is None:
                raise Unsafe("writer has no locked authority generation")
            parent, name, parents = self._walk_parent(self._authority)
            try:
                canonical = _win_nt_open(parent, name, directory=False)
            finally:
                if parent != self._root:
                    _win_close(parent)
            try:
                locked = _win_generation(self._authority_handle, self._authority)
                current = _win_generation(canonical, self._authority)
                if (
                    locked != self._authority_generation
                    or current != self._authority_generation
                    or parents != self._authority_parents
                ):
                    raise Unsafe("canonical authority changed outside its writer lock")
            finally:
                _win_close(canonical)

        def read(self, relative: str, *, maximum: int) -> Observation:
            if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 0:
                raise Unsafe("read bound is invalid")
            canonical = "/".join(_parts(relative))
            if canonical == self._authority:
                self._require_canonical_authority()
            parent, name, parents = self._walk_parent(canonical)
            try:
                handle = _win_nt_open(parent, name, directory=False)
            finally:
                if parent != self._root:
                    _win_close(parent)
            try:
                before = _win_generation(handle, canonical)
                if canonical == self._authority and (
                    before != self._authority_generation or parents != self._authority_parents
                ):
                    raise Unsafe("read did not use the locked canonical authority")
                if before.size > maximum:
                    raise Unsafe("regular file exceeds its read bound")
                body = _win_read(handle, maximum)
                after = _win_generation(handle, canonical)
                if before != after or self._parent_generations(canonical) != parents:
                    raise Unsafe("regular file changed while it was read")
                return Observation(canonical, body, after, parents, maximum)
            finally:
                _win_close(handle)

        def unchanged(self, observation: Observation) -> bool:
            try:
                return self.read(observation.path, maximum=observation.maximum) == observation
            except TransactionError:
                return False

        def _inventory_snapshot(self) -> tuple[tuple[str, ...], Generation]:
            before = _win_generation(self._home_handle, self._home)
            names = tuple(sorted(_win_directory_names(self._home_handle, maximum=_INVENTORY_LIMIT)))
            after = _win_generation(self._home_handle, self._home)
            if before != after:
                raise Unsafe("transaction namespace changed while it was inventoried")
            return names, after

        def inventory(self) -> Inventory:
            self._require_canonical_authority()
            self._require_canonical_home()
            names, generation = self._inventory_snapshot()
            pending = tuple(name for name in names if name.startswith("pending-"))
            return Inventory(names, pending, generation, self._inventory_owner)

        def _consume_inventory(self, inventory: Inventory) -> tuple[str, ...]:
            if (
                not isinstance(inventory, Inventory)
                or inventory._owner is not self._inventory_owner
                or inventory.consumed
            ):
                raise Unsafe("inventory is not an unused capability from this writer")
            self._require_canonical_authority()
            self._require_canonical_home()
            names, generation = self._inventory_snapshot()
            if names != inventory.names or generation != inventory.generation:
                raise Unsafe("transaction namespace changed after inventory")
            inventory.consumed = True
            return names

        def stage(self, inventory: Inventory, name: str, filename: str, body: bytes) -> Pending:
            name = _component(name, pending=True)
            filename = _component(filename)
            if not isinstance(body, bytes):
                raise Unsafe("staged content must be bytes")
            names = self._consume_inventory(inventory)
            expected_names = tuple(sorted((*names, name)))
            directory = _win_nt_open(
                self._home_handle, name, directory=True, create=True, delete=True
            )
            file_handle = 0
            try:
                file_handle = _win_nt_open(
                    directory, filename, directory=False, create=True, write=True, delete=True
                )
                _win_write(file_handle, body)
                file_generation = _win_generation(file_handle, filename)
                directory_generation = _win_generation(directory, name)
                actual_names, home_generation = self._inventory_snapshot()
                if actual_names != expected_names:
                    raise Unsafe("transaction namespace changed while pending was staged")
                pending = Pending(
                    name,
                    filename,
                    body,
                    directory_generation.identity,
                    file_generation.identity,
                    expected_names,
                    home_generation,
                )
                self._pending_handles[pending.directory_identity] = _PendingHandles(
                    directory, file_handle
                )
                directory = 0
                file_handle = 0
                return pending
            finally:
                _win_close(file_handle)
                _win_close(directory)

        def discard(self, pending: Pending) -> None:
            """The same promise as the POSIX side, kept with the handles already owned.

            Windows deletes through a handle rather than a name, so nothing here constructs
            a path at all: both handles were opened with `DELETE`, are marked for deletion,
            and go away when they close.
            """

            self._require_canonical_authority()
            state = self._pending_handles.get(pending.directory_identity)
            if state is None or state.published:
                raise Unsafe("pending directory handle is not owned by this writer")
            if (
                _win_generation(state.directory, pending.name).identity
                != pending.directory_identity
            ):
                raise Unsafe("pending directory identity changed")
            if not state.child:
                # A refused publication closes the child before its rename. The file is
                # still there, and a directory with a file in it cannot be marked for
                # deletion, so the handle is reopened through the directory handle already
                # owned — no pathname is constructed, and the identity check below still
                # decides whether this is the entry that was staged.
                state.child = _win_nt_open(
                    state.directory, pending.filename, directory=False, delete=True
                )
            if _win_generation(state.child, pending.filename).identity != pending.file_identity:
                raise Unsafe("pending file identity changed")

            def _mark(handle: int) -> None:
                disposition = ctypes.c_byte(1)
                if not _kernel32.SetFileInformationByHandle(
                    handle, 4, ctypes.byref(disposition), ctypes.sizeof(disposition)
                ):
                    raise _win_error("pending entry could not be marked for deletion")

            # Order matters and only in one direction. A file marked for deletion keeps its
            # directory entry until its last handle closes, so marking the directory while
            # the child is still open asks Windows to delete a non-empty directory and it
            # refuses — turning the one path that guarantees nothing is left behind into
            # the path that leaves something behind.
            _mark(state.child)
            _win_close(state.child)
            state.child = 0
            _mark(state.directory)
            state.consumed = True
            _win_close(state.directory)
            state.directory = 0
            self._pending_handles.pop(pending.directory_identity, None)

        def publish(self, pending: Pending, final: str) -> Published:
            final = _win_component(final)
            self._require_canonical_authority()
            state = self._pending_handles.get(pending.directory_identity)
            if state is None or state.consumed:
                raise Unsafe("pending directory handle is not owned by this writer")
            if (
                _win_generation(state.directory, pending.name).identity
                != pending.directory_identity
            ):
                raise Unsafe("pending directory identity changed")
            if _win_directory_names(state.directory) != (pending.filename,):
                raise Unsafe("pending directory contents changed")
            if _win_generation(state.child, pending.filename).identity != pending.file_identity:
                raise Unsafe("pending file identity changed")
            if _win_read(state.child, len(pending.body)) != pending.body:
                raise Unsafe("pending file bytes changed")
            self._require_canonical_home()
            names, generation = self._inventory_snapshot()
            if names != pending.expected_names or generation != pending.home_generation:
                raise Unsafe("transaction namespace changed after pending was staged")
            published = Published(
                final,
                pending.filename,
                pending.body,
                pending.directory_identity,
                pending.file_identity,
            )
            _publish_windows_pending(state, self._home_handle, final, _win_close)
            return published


@contextlib.contextmanager
def writer(root: Path, authority: str, home: str) -> Iterator[Any]:
    """Open the platform backend while holding the existing authority-file lock."""
    implementation: Any
    if os.name == "posix":
        implementation = _PosixWriter(root, authority, home)
    elif sys.platform == "win32":
        implementation = _WindowsWriter(root, authority, home)
    else:
        raise Unsupported("host has no native spec transaction backend")
    with implementation as active:
        yield active
