"""A versioned migration, not a pull.

Pulling a clone was an unauthenticated code-execution channel into seven surfaces at
once. Integrity now comes from the wheel's hash, checked by tools the user already
trusts. Auto-update stays off, because a change of governance is never silent — and a
keyboard confirmation was never as good as a reviewed commit: the record of an update
is the diff of .ai/config.toml inside a pull request, signed by whoever merged it.

It never touches AGENTS.md or CONSTITUTION.md. Those are yours.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import stat
import subprocess
import sys
import tomllib
import uuid
from dataclasses import dataclass
from pathlib import Path

from ai_engineering import __version__, outcome, paths, wiring

CONFIG_FILE = "config.toml"
PIN_CHANGED = "the pin changed after the update was approved"

OWNED = ("justfile", "CLAUDE.md", ".ai/config.toml")
_VERSION = re.compile(
    r'(?m)^[ \t]*version[ \t]*=[ \t]*(?P<quote>["\'])(?P<value>[^"\']*)'
    r"(?P=quote)[ \t]*(?:#.*)?$"
)
_STRICT_VERSION = re.compile(r"(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*))*")
_MAX_VERSION = 64
_MAX_PIN_BYTES = 100_000
_REQUIRED_DIR_FD = (os.open, os.stat, os.rename, os.unlink)


class Undecidable(RuntimeError):
    """Update cannot safely derive or complete its exact change set."""


@dataclass(frozen=True, slots=True)
class _Pin:
    root: Path
    root_id: tuple[int, int]
    home_id: tuple[int, int]
    file_id: tuple[int, int]
    mode: int
    before: bytes
    after: bytes
    pinned: str


def dirty(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--", *OWNED],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise Undecidable("git could not inspect framework-owned files") from error
    if result.returncode:
        raise Undecidable("git could not inspect framework-owned files")
    return [line[3:] for line in result.stdout.splitlines() if line.strip()]


def _version(value: str) -> tuple[int, ...]:
    if (
        not isinstance(value, str)
        or len(value) > _MAX_VERSION
        or not _STRICT_VERSION.fullmatch(value)
    ):
        raise Undecidable("the version is not a strict dotted numeric version")
    parts = [int(part) for part in value.split(".")]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def migrations(pinned: str, target: str) -> list[Path]:
    """Select only an unambiguous forward chain of shipped migration ranges."""

    start, finish = _version(pinned), _version(target)
    if finish < start:
        raise Undecidable("a downgrade cannot run forward migrations")
    if finish == start:
        return []

    folder = paths.shipped("migrations")
    ranges = []
    for path in sorted(folder.glob("*/")):
        low, _, high = path.name.partition("..")
        if path.is_symlink() or not low or not high or ".." in high:
            raise Undecidable("a shipped migration range is not canonical")
        low_key, high_key = _version(low), _version(high)
        scripts = sorted(path.glob("*.py"))
        if (
            low_key >= high_key
            or not scripts
            or any(script.is_symlink() or not script.is_file() for script in scripts)
        ):
            raise Undecidable("a shipped migration range is not canonical")
        ranges.append((low_key, high_key, scripts))

    cursor = start
    steps: list[Path] = []
    # `from_key` and `to_key` rather than `low` and `high`: those two names are already the
    # string halves of a directory name twenty lines above, and reusing them here made one
    # function hold two meanings for each — which a type checker reads as a contradiction
    # and a person reads as the same thing twice.
    for from_key, to_key, scripts in sorted(ranges):
        if to_key <= start or from_key >= finish:
            continue
        starts_in_declared_line = not steps and start[: len(from_key)] == from_key
        if (from_key != cursor and not starts_in_declared_line) or to_key > finish:
            raise Undecidable("the forward migration path is not contiguous")
        steps.extend(scripts)
        cursor = to_key
    return steps


def _identity(details: os.stat_result) -> tuple[int, int]:
    return details.st_dev, details.st_ino


def _dirfd_support() -> None:
    if (
        not all(hasattr(os, name) for name in ("O_DIRECTORY", "O_NOFOLLOW"))
        or not all(function in os.supports_dir_fd for function in _REQUIRED_DIR_FD)
        or os.stat not in os.supports_follow_symlinks
    ):
        raise Undecidable("this platform cannot safely publish a repository pin")


@contextlib.contextmanager
def _pin_home(root: Path):
    """Open the resolved repository and its real .ai child without following aliases."""

    _dirfd_support()
    root_fd = home_fd = -1
    try:
        directory = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        root_fd = os.open(root, directory)
        root_details = os.fstat(root_fd)
        if _identity(root.lstat()) != _identity(root_details):
            raise OSError("the repository root is aliased")
        home_fd = os.open(".ai", directory, dir_fd=root_fd)
        home_details = os.fstat(home_fd)
        linked_home = os.stat(".ai", dir_fd=root_fd, follow_symlinks=False)
        if not stat.S_ISDIR(linked_home.st_mode) or _identity(linked_home) != _identity(
            home_details
        ):
            raise OSError("the pin home is aliased")
    except OSError as error:
        for descriptor in (home_fd, root_fd):
            if descriptor >= 0:
                with contextlib.suppress(OSError):
                    os.close(descriptor)
        raise Undecidable("the pin home is not one canonical directory") from error
    try:
        yield root_fd, home_fd, root_details, home_details
    finally:
        for descriptor in (home_fd, root_fd):
            if descriptor >= 0:
                with contextlib.suppress(OSError):
                    os.close(descriptor)


def _read_pin(home_fd: int) -> tuple[os.stat_result, bytes]:
    descriptor = -1
    try:
        flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        descriptor = os.open(CONFIG_FILE, flags, dir_fd=home_fd)
        before = os.fstat(descriptor)
        linked = os.stat(CONFIG_FILE, dir_fd=home_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or _identity(before) != _identity(linked)
            or before.st_size > _MAX_PIN_BYTES
        ):
            raise OSError("the pin is aliased or not one bounded regular file")
        chunks = []
        remaining = _MAX_PIN_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        body = b"".join(chunks)
        after = os.fstat(descriptor)
        if (
            len(body) > _MAX_PIN_BYTES
            or _identity(after) != _identity(before)
            or after.st_size != before.st_size
            or after.st_mtime_ns != before.st_mtime_ns
            or after.st_ctime_ns != before.st_ctime_ns
        ):
            raise OSError("the pin changed while it was read")
        return after, body
    except OSError as error:
        raise Undecidable("the pin cannot be read as one canonical framework version") from error
    finally:
        if descriptor >= 0:
            with contextlib.suppress(OSError):
                os.close(descriptor)


def _render_pin(body: bytes, target: str) -> tuple[str, bytes]:
    """Replace only the canonical version while preserving all other exact bytes."""

    _version(target)
    try:
        text = body.decode("utf-8")
        parsed = tomllib.loads(text)
        pinned = parsed["framework"]["version"]
        _version(pinned)
        # The alternation inside the lookahead is grouped rather than left to precedence.
        # It read `(?=^\[|\Z)` and meant `(?=(?:^\[)|\Z)`; those are the same thing here
        # and the reader has to know the rule to be sure of it, which is the whole of
        # the objection.
        section = re.search(r"(?ms)^\[framework\][^\r\n]*\r?\n(?P<body>.*?)(?=(?:^\[)|\Z)", text)
        rows = list(_VERSION.finditer(section.group("body"))) if section else []
        if not isinstance(pinned, str) or not pinned or len(rows) != 1 or section is None:
            raise ValueError("the framework version is not exact")
        row = rows[0]
        if row.group("value") != pinned:
            raise ValueError("the framework version is not exact")
        start = section.start("body") + row.start("value")
        end = section.start("body") + row.end("value")
    except (KeyError, TypeError, UnicodeError, ValueError) as error:
        raise Undecidable("the pin cannot be read as one canonical framework version") from error
    return pinned, (text[:start] + target + text[end:]).encode("utf-8")


def _observe_pin(root: Path, target: str) -> _Pin:
    with _pin_home(root) as (_, home_fd, root_details, home_details):
        file_details, before = _read_pin(home_fd)
    pinned, after = _render_pin(before, target)
    return _Pin(
        root,
        _identity(root_details),
        _identity(home_details),
        _identity(file_details),
        stat.S_IMODE(file_details.st_mode),
        before,
        after,
        pinned,
    )


def _verify_pin(snapshot: _Pin) -> None:
    with _pin_home(snapshot.root) as (_, home_fd, root_details, home_details):
        file_details, body = _read_pin(home_fd)
    if (
        _identity(root_details) != snapshot.root_id
        or _identity(home_details) != snapshot.home_id
        or _identity(file_details) != snapshot.file_id
        or body != snapshot.before
    ):
        raise Undecidable(PIN_CHANGED)


def _write_all(descriptor: int, body: bytes) -> None:
    written = 0
    while written < len(body):
        count = os.write(descriptor, body[written:])
        if count <= 0:
            raise OSError("the atomic pin write did not advance")
        written += count


def _publish_pin(snapshot: _Pin) -> None:
    """Revalidate and atomically replace the pin within the already-verified .ai dirfd."""

    temporary = f".config.toml.ai-eng-{uuid.uuid4().hex}"
    descriptor = -1
    renamed = False
    try:
        with _pin_home(snapshot.root) as (root_fd, home_fd, root_details, home_details):
            current_details, body = _read_pin(home_fd)
            if (
                _identity(root_details) != snapshot.root_id
                or _identity(home_details) != snapshot.home_id
                or _identity(current_details) != snapshot.file_id
                or body != snapshot.before
            ):
                raise Undecidable(PIN_CHANGED)
            flags = (
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
            )
            descriptor = os.open(temporary, flags, snapshot.mode, dir_fd=home_fd)
            _write_all(descriptor, snapshot.after)
            os.fchmod(descriptor, snapshot.mode)
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = -1

            # The path and bytes consent covered are checked again immediately before the
            # atomic replacement. The opaque migration scripts run before this boundary.
            linked_home = os.stat(".ai", dir_fd=root_fd, follow_symlinks=False)
            final_details, final_body = _read_pin(home_fd)
            if (
                _identity(snapshot.root.lstat()) != snapshot.root_id
                or _identity(linked_home) != snapshot.home_id
                or _identity(final_details) != snapshot.file_id
                or final_body != snapshot.before
            ):
                raise Undecidable(PIN_CHANGED)
            os.rename(temporary, CONFIG_FILE, src_dir_fd=home_fd, dst_dir_fd=home_fd)
            renamed = True
            os.fsync(home_fd)
            published, published_body = _read_pin(home_fd)
            if _identity(published) == snapshot.file_id or published_body != snapshot.after:
                raise Undecidable("the atomically published pin failed its postcondition")
    except OSError as error:
        raise Undecidable("the pin could not be published atomically") from error
    finally:
        if descriptor >= 0:
            with contextlib.suppress(OSError):
                os.close(descriptor)
        if not renamed:
            with (
                contextlib.suppress(OSError, Undecidable),
                _pin_home(snapshot.root) as (_, home_fd, _, _),
            ):
                os.unlink(temporary, dir_fd=home_fd)


def _guard_plan() -> tuple[list[dict], list[dict]]:
    """Return recorded live guards and the non-append-only subset update may rewrite."""
    try:
        receipt = wiring.receipt()
        if not isinstance(receipt, dict):
            raise TypeError("receipt is not canonical")
        rows = receipt.get("wrote", [])
        if not isinstance(rows, list):
            raise TypeError("receipt is not canonical")
        if any(
            not isinstance(row, dict)
            or not all(isinstance(row.get(key), str) for key in ("path", "kind", "how"))
            for row in rows
        ):
            raise TypeError("receipt ownership is incomplete")
        # Ownership narrows what this explicit invocation may rewrite. It does not grant
        # permission and is never proof that an update ran or succeeded.
        mine = {row["path"] for row in rows if row["kind"] == "guard"}
        found = [surface for surface in wiring.detect() if surface.get("settings") in mine]
        rewritten = [surface for surface in found if not surface.get("append_only")]
        for surface in rewritten:
            target = wiring.expand(surface["settings"])
            if target.is_symlink() or (target.exists() and not target.is_file()):
                raise OSError("a recorded guard target is not a regular file")
            if target.exists() and surface["writer"].startswith("json_"):
                wiring.read_json(target)
            elif target.exists():
                target.read_text(encoding="utf-8")
    except (KeyError, OSError, TypeError, ValueError, wiring.Unreadable) as error:
        raise Undecidable("recorded guard state cannot be safely evaluated") from error
    return found, rewritten


def main(argv: list[str]) -> outcome.Result:
    parser = argparse.ArgumentParser("ai-eng update")
    parser.add_argument("--to", default=__version__, help="the version to move this repository to")
    parser.add_argument("--force", action="store_true", help="print what would be discarded")
    parser.add_argument(
        "--dry-run", action="store_true", help="print exact changes and write nothing"
    )
    args = parser.parse_args(argv)

    root = paths.repo_root()
    if root is None:
        print("not inside a repository")
        return outcome.result("INCOMPLETE")
    pin = root / ".ai" / CONFIG_FILE
    if not pin.exists() and not pin.is_symlink():
        print("  this repository is not set up. `ai-eng init` first.")
        return outcome.result("INCOMPLETE")
    try:
        snapshot = _observe_pin(root, args.to)
    except Undecidable as why:
        print(f"  INCOMPLETE — {why}. Nothing changed.")
        return outcome.result("INCOMPLETE")
    pinned = snapshot.pinned
    print(f"  {pinned} → {args.to}")
    print(f"  would rewrite pin: {pin}")
    try:
        changes = dirty(root)
    except Undecidable as why:
        print(f"  INCOMPLETE — {why}. Nothing changed.")
        return outcome.result("INCOMPLETE")

    if changes:
        print(f"  REFUSED — these are framework-owned and have uncommitted changes: {changes}")
        print(
            "  Commit or discard them first. --force prints exactly what it would discard;"
            " it never overwrites silently."
        )
        if not args.force:
            return outcome.result("INCOMPLETE")
        print(f"  --force would discard: {changes}")
        return outcome.result("INCOMPLETE")
    if _version(pinned) == _version(args.to):
        print("  already pinned to that version. Nothing changed.")
        # A dry run may not say PASS. This branch sits above the dry-run branch and
        # returned before it, so `update --dry-run` on an already-pinned repository
        # reported "the requested operation and all applicable checks completed" for a run
        # that deliberately did nothing. `WOULD_CHANGE` reads "a complete dry run derived
        # exact changes and made none", and the empty set is an exact set: what the word
        # distinguishes is that the derivation was complete, not that it found something.
        return outcome.dry_run(exact_changes=True) if args.dry_run else outcome.result("PASS")

    try:
        steps = migrations(pinned, args.to)
        found, rewritten_plan = _guard_plan()
    except (OSError, Undecidable) as why:
        print(f"  INCOMPLETE — {why}. Nothing changed.")
        return outcome.result("INCOMPLETE")
    print(
        f"  {len(steps)} migration(s) to run: "
        f"{', '.join(step.parent.name + '/' + step.name for step in steps) or 'none'}"
    )
    if not found:
        print("  → no guard entry of ours is recorded here. `ai-eng init --global` wires one.")
    else:
        for surface in rewritten_plan:
            print(f"  would rewrite guard entry: {surface['settings']}")
        for surface in [surface for surface in found if surface.get("append_only")]:
            print(f"  would leave append-only guard untouched: {surface['settings']}")
    if args.dry_run:
        if steps:
            print(
                "  INCOMPLETE — migration scripts do not expose exact file changes. "
                "Nothing changed."
            )
            return outcome.dry_run(exact_changes=False)
        print("  dry run complete. Nothing changed.")
        return outcome.dry_run(exact_changes=True)
    if not sys.stdin.isatty():
        print("  an update is a person's decision and there is no keyboard here. Nothing changed.")
        return outcome.result("INCOMPLETE")
    if input("  Type y to run them › ").strip().lower() != "y":
        print("  nothing changed.")
        return outcome.result("CANCELLED")

    started_steps = 0
    try:
        _verify_pin(snapshot)
        for step in steps:
            _verify_pin(snapshot)
            started_steps += 1
            subprocess.run([sys.executable, str(step), str(root)], check=True, timeout=600)
            _verify_pin(snapshot)
        _publish_pin(snapshot)
    except (OSError, subprocess.SubprocessError, Undecidable) as why:
        print(f"  INCOMPLETE — update stopped before it could finish: {why}.")
        if started_steps:
            print("  Migration scripts already ran and are not transactional. Inspect the diff.")
        else:
            print("  Update wrote nothing; any concurrent user edit was preserved.")
        return outcome.result("INCOMPLETE")
    print(f"  ✓ the pin now reads {args.to} — that diff is the record of this update.")

    # What this machine chose, and never everything that happens to be installed on it.
    # This walked `detect()`, so declining Cursor at `init` and updating a week later wired
    # it — failClosed, which is what makes Cursor deny rather than advise — from a verb the
    # person ran to move a version number. And nothing was recorded, so `uninstall`
    # afterwards listed what init had written, took the consent, and left the rest running.
    if not found:
        return outcome.result("PASS")
    try:
        rewritten = wiring.install_guards(rewritten_plan)
        for name, target, detail in rewritten:
            print(f"  ✓ rewrote {target or name} ({detail})")
        # Written down, because an entry nothing recorded is an entry uninstall cannot find.
        if rewritten_plan:
            wiring.record(
                [
                    {"path": surface["settings"], "kind": "guard", "how": surface["writer"]}
                    for surface in rewritten_plan
                ]
            )
    except (KeyError, OSError, TypeError, wiring.Unreadable) as why:
        print(f"  INCOMPLETE — guard rewrite stopped before it could finish: {why}.")
        return outcome.result("INCOMPLETE")
    for surface in [s for s in found if s.get("append_only")]:
        print(
            f"  → {surface['name']} left untouched. Its trust is a hash of the whole handler "
            f"and of its position, so it is only rewritten when the entry genuinely changes."
        )
    print(
        "\n  Read the diff and make the commit. `uv tool install ai-engineering=="
        f"{args.to}` installs the wheel this pin now names."
    )
    return outcome.result("PASS")
