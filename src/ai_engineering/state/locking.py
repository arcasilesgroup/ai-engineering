"""Serialization helpers for shared local harness artifacts."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

if os.name == "nt":
    import msvcrt
else:
    import fcntl


_LOCKS_RELATIVE_PATH = Path(".ai-engineering") / "state" / "locks"


def artifact_lock_path(project_root: Path, artifact_name: str) -> Path:
    """Return the canonical sidecar lock path for a shared artifact family."""
    return project_root / _LOCKS_RELATIVE_PATH / f"{artifact_name}.lock"


def _seed_lock_file(handle: BinaryIO) -> None:
    """Ensure the lock file has one byte so Windows byte-range locking works."""
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
        os.fsync(handle.fileno())
    handle.seek(0)


def _acquire_lock(handle: BinaryIO) -> None:
    """Acquire an exclusive advisory lock on the opened lock file."""
    if os.name == "nt":
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)  # ty:ignore[unresolved-attribute]
        return
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def _release_lock(handle: BinaryIO) -> None:
    """Release an exclusive advisory lock on the opened lock file."""
    if os.name == "nt":
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)  # ty:ignore[unresolved-attribute]
        return
    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def artifact_lock(project_root: Path, artifact_name: str) -> Iterator[Path]:
    """Serialize access to a shared artifact family within one project root."""
    lock_path = artifact_lock_path(project_root, artifact_name)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        _seed_lock_file(handle)
        _acquire_lock(handle)
        try:
            yield lock_path
        finally:
            _release_lock(handle)
