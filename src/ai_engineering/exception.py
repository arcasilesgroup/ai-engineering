"""exception --skip "<reason>" — one design exception, granted by a person.

The bypass is deliberate, loud and human-only. It demands a confirmation on a real
keyboard, which the agent does not have, and that is the whole gate. Every concession
emits an event, and `report digest` lists them by name: a guard you bypass three times is a
guard to fix or delete, and the report says so.

Three rules this file is built around, each of them a way a bypass could go quiet:

- The grant file is reached one component at a time with nothing linked on the way. A
  redirected bypass is a grant somebody else can write.
- Nothing is left on disk after an `INCOMPLETE`. A half-verified grant is still a grant the
  guard will honour, and the person who ran this was told nothing was granted.
- A grant whose event is not observable is removed. Telemetry fails open everywhere else,
  by design — but a concession nobody can find in the record is the exact thing this verb
  exists to make findable, so here the absence of the record removes the grant rather than
  being shrugged off.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import time
from pathlib import Path

from ai_engineering import outcome, paths

WINDOW_SECONDS = 900
_TAIL_BYTES = 64 * 1024


class _Unsafe(RuntimeError):
    """The grant store could not be proved to be the one this machine owns."""


def _matches(path: Path, grant: dict[str, object]) -> bool:
    try:
        return json.loads(path.read_text(encoding="utf-8")) == grant
    except (OSError, UnicodeError, ValueError):
        return False


def anchored_store() -> Path:
    """`bypass.json` under the application home, with no link anywhere on the way.

    A symlink, junction or reparse point at any component — including the home itself —
    means the file the guard later reads is not necessarily the file this command wrote.
    That is refused rather than followed: the cure is a real directory, and it is named in
    the message.
    """

    walked = paths.home()
    for component in ("", "cache", "bypass.json"):
        walked = walked / component if component else walked
        try:
            value = walked.lstat()
        except FileNotFoundError:
            continue
        except OSError as error:
            raise _Unsafe(f"the grant store could not be read at {component or 'its home'}") from (
                error
            )
        if stat.S_ISLNK(value.st_mode) or getattr(value, "st_reparse_tag", False):
            raise _Unsafe(f"the grant store is redirected at {component or 'its home'}")
    return walked


def _record_sizes() -> dict[Path, int]:
    """How long each record file is right now, so what this command appends can be read
    back on its own. Matching on guard and reason alone would accept a line some earlier
    run left behind, which is evidence of that run and not of this one."""

    emit = paths.load("_emit")
    root = emit.repo_root()
    sizes: dict[Path, int] = {}
    for path in (emit.buffer_path(root), emit.chain_path(root)):
        if path is None:
            continue
        try:
            sizes[path] = path.stat().st_size if path.is_file() else 0
        except OSError:
            # Not zero. A length this code could not read is not a length of nothing, and
            # treating it as zero lets a `bypassed` line an earlier run left behind answer
            # for this one. The file is dropped from the comparison instead.
            continue
    return sizes


def _observable(sizes: dict[Path, int], guard: str, reason: str) -> bool:
    """Whether this concession can be found in the record it was promised to.

    Only the bytes appended since `sizes` were taken are read, so the answer is about this
    grant and no other. The event goes to the repository buffer when there is one and to the
    machine chain when there is not, so both are looked at. This is an observation, not a
    second gate: it decides only whether the grant just written may stay.
    """

    for path, before in sizes.items():
        try:
            if not path.is_file() or path.stat().st_size <= before:
                continue
            with path.open("rb") as stream:
                stream.seek(max(before, path.stat().st_size - _TAIL_BYTES))
                appended = stream.read().decode("utf-8", "replace")
        except OSError:
            continue
        for line in appended.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if (
                event.get("cls") == "bypassed"
                and event.get("name") == guard
                and event.get("data", {}).get("reason") == reason
            ):
                return True
    return False


def _write_grant(path: Path, body: bytes) -> None:
    """Write the grant through a directory handle this process proved, where it can.

    On POSIX the parent is opened `O_DIRECTORY|O_NOFOLLOW` once and the file is created
    relative to that descriptor, so nothing swapped in afterwards is reachable by the write.
    Windows has neither flag on `os.open` — `O_NOFOLLOW` is not defined there at all — so the
    check immediately above is what stands, and the residual window is named rather than
    papered over. Task 39q's matrix is where that half gets executed.
    """

    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    if hasattr(os, "O_DIRECTORY"):
        parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            descriptor = os.open(path.name, flags, 0o600, dir_fd=parent_fd)
            try:
                os.write(descriptor, body)
            finally:
                os.close(descriptor)
        finally:
            os.close(parent_fd)
        return
    descriptor = os.open(path, flags, 0o600)
    try:
        os.write(descriptor, body)
    finally:
        os.close(descriptor)


def _withdraw(path: Path, message: str) -> outcome.Result:
    """Remove the grant and say nothing was granted, which is then true."""

    try:
        path.unlink(missing_ok=True)
    except OSError:
        print(f"  INCOMPLETE: {message}, and the grant could not be removed: {path.name}")
        return outcome.result("INCOMPLETE")
    print(f"  INCOMPLETE: {message}. Nothing granted.")
    return outcome.result("INCOMPLETE")


def main(argv: list[str]) -> outcome.Result:
    parser = argparse.ArgumentParser(prog="ai-eng exception")
    parser.add_argument(
        "--skip", required=True, metavar="REASON", help="why this change does not need a plan"
    )
    parser.add_argument("--guard", default="loop_guard", choices=["loop_guard"])
    args = parser.parse_args(argv)

    if not sys.stdin.isatty():
        print("  a bypass is a person's decision, and there is no keyboard here. Nothing granted.")
        return outcome.result("INCOMPLETE")
    try:
        path = anchored_store()
    except _Unsafe as why:
        print(f"  INCOMPLETE: {why}. Nothing granted.")
        return outcome.result("INCOMPLETE")

    print(f"  This grants ONE bypass of {args.guard}, for 15 minutes, recorded against your name.")
    print(f"  Reason: {args.skip}")
    if input("  Type yes to grant it › ").strip().lower() != "yes":
        print("  nothing granted.")
        return outcome.result("CANCELLED")

    grant = {"guard": args.guard, "reason": args.skip, "expires": time.time() + WINDOW_SECONDS}
    body = json.dumps(grant).encode("utf-8")
    try:
        if not path.parent.exists():
            path.parent.mkdir(parents=True)
        # Checked again here, after the person has answered. The first check happened before
        # the prompt, and a prompt is as long as somebody takes to type: a check that far
        # from its write proves what was true when nobody was waiting.
        path = anchored_store()
        _write_grant(path, body)
    except _Unsafe as why:
        return _withdraw(path, str(why))
    except OSError:
        return _withdraw(path, "the one-time exception could not be written")
    if not _matches(path, grant):
        return _withdraw(path, "the one-time exception could not be verified")

    sizes = _record_sizes()
    paths.load("_emit").emit(args.guard, "bypassed", reason=args.skip, granted="by a person")
    if not _observable(sizes, args.guard, args.skip):
        return _withdraw(path, "the concession could not be found in the record")
    if not _matches(path, grant):
        return _withdraw(path, "the one-time exception changed after it was written")

    print(f"  ✓ granted. The next {args.guard} block passes, once, and the record says why.")
    return outcome.result("PASS")
