"""The record: identity, paths and the hash chain.

Standard library only, and executed by path rather than imported. The guards that call
it run on every tool call, so an import of the package would put ~110 ms of interpreter
work on a hot path where latency is a security property.

An event is written only when something was decided or something happened. The six
classes below are the closed set; there is deliberately no "a hook ran".
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

CLASSES = ("blocked", "allowed", "bypassed", "command", "error", "session")
EDITED = "this line was edited between the guard that wrote it and the seal"
FOREIGN = "another machine identity wrote this line into the buffer; it is not sealed as ours"
LOCK_WAIT_SECONDS = 0.05


class ChainIntegrityError(ValueError):
    """The durable chain cannot safely accept another link."""


def stable_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def home() -> Path:
    """The application folder. Everything of ours, in one place, outside every clone."""
    return Path(os.environ.get("AI_ENGINEERING_HOME") or Path.home() / ".ai-engineering")


def config(root: Path | None = None) -> dict:
    """The pin and the thresholds: this repository's .ai/config.toml over the machine's
    ~/.ai-engineering/config.toml. Delete the repository one and the framework does
    nothing here, which is the no-lock-in promise expressed as a file."""
    import tomllib

    merged: dict = {}
    root = root or repo_root()
    files = [home() / "config.toml"]
    if root is not None:
        files.append(root / ".ai" / "config.toml")
    for path in files:
        try:
            for section, values in tomllib.loads(path.read_text()).items():
                if isinstance(values, dict):
                    merged.setdefault(section, {}).update(values)
                else:
                    merged[section] = values
        except (OSError, AttributeError, TypeError, ValueError):
            continue
    return merged


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def machine_id() -> str:
    """Stable per machine. Written once; deleting it makes `init` treat this as new.

    It never writes over a receipt that is already there. It used to: any exception at all —
    a missing key, a half-written file — and it saved `{"wrote": []}` over the record of every
    file this tool has installed, from the telemetry half, whose whole contract is to fail open
    and never opine. Absent is the one case that may create it; present-and-unreadable gets a
    session-local id and leaves the file alone for `ai-eng doctor` to name."""
    receipt = home() / "machine.json"
    try:
        return json.loads(receipt.read_text())["machine_id"]
    except Exception:
        mid = uuid.uuid4().hex[:12]
        if receipt.exists():
            return mid
        data = {"machine_id": mid, "created": now(), "wrote": []}
        try:
            receipt.parent.mkdir(parents=True, exist_ok=True)
            receipt.write_text(json.dumps(data, indent=2) + "\n")
        except OSError:
            pass
        return mid


def repo_root(start: Path | None = None) -> Path | None:
    cur = (start or Path.cwd()).resolve()
    for p in (cur, *cur.parents):
        if (p / ".git").exists():
            return p
    return None


def repo_id(root: Path | None = None) -> str:
    """Derived from the sha of the first commit, so it survives clones, renames and
    forks. A path or a remote URL does not."""
    root = root or repo_root()
    if root is None:
        return "no-repo"
    cache = root / ".git" / "ai-eng-repo-id"
    try:
        return cache.read_text().strip()
    except OSError:
        pass
    try:
        out = subprocess.run(
            ["git", "rev-list", "--max-parents=0", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.split()
        rid = out[-1][:12] if out else "unborn"
    except Exception:
        rid = "unknown"
    with contextlib.suppress(OSError):
        cache.write_text(rid + "\n")
    return rid


def chain_path(root: Path | None = None) -> Path:
    return home() / "state" / repo_id(root) / f"{machine_id()}.jsonl"


def buffer_path(root: Path | None = None) -> Path | None:
    """The in-clone buffer. It is repository-local and the key that stamps it is not: a
    process with its own `AI_ENGINEERING_HOME` writes here with a key the owner of the
    default home cannot verify.

    Making the buffer follow the home was tried and reverted. `AI_ENGINEERING_HOME` is the
    only way a test isolates itself, so keying the buffer off it means the buffer is never
    exercised by anything — four suites went red proving exactly that. A feature nothing
    can test to protect a record is the wrong trade. The seal classifies such a line as
    another machine's instead, which is what it is."""

    root = root or repo_root()
    if root is None or not (root / ".ai" / "config.toml").exists():
        return None
    return root / ".ai" / "events.jsonl"


def session_id() -> str:
    sid = os.environ.get("AI_ENG_SESSION")
    if not sid:
        sid = uuid.uuid4().hex[:12]
        os.environ["AI_ENG_SESSION"] = sid
    return sid


def digest(event: dict) -> str:
    body = {k: v for k, v in event.items() if k != "hash"}
    return hashlib.sha256(stable_json(body).encode()).hexdigest()


def stamp(event: dict) -> str:
    """The mark only this machine can make on a buffered event. A digest is not enough:
    anything that can edit the buffer can recompute one over its own edit, which is a
    checksum against corruption. The key is 0600 in the application folder, outside every
    clone, so an agent that never reads it cannot rewrite the line that denied it."""
    path = home() / "buffer.key"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(mode=0o600)  # private from the moment it exists, not narrowed afterwards
        path.write_bytes(os.urandom(32))
    return hmac.new(path.read_bytes(), digest(event).encode(), hashlib.sha256).hexdigest()


def _read_head(lines) -> tuple[int, str]:
    """Read every supplied link; a corrupt chain has no safe head."""
    seq, previous = 0, ""
    for line_number, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except (UnicodeError, ValueError) as exc:
            raise ChainIntegrityError(f"chain line {line_number} is invalid JSON") from exc
        expected = seq + 1
        if not isinstance(event, dict) or type(event.get("seq")) is not int:
            raise ChainIntegrityError(f"chain sequence is invalid at line {line_number}")
        if event["seq"] != expected:
            raise ChainIntegrityError(f"chain sequence gap at line {line_number}")
        if event.get("prev") != previous:
            raise ChainIntegrityError(f"chain predecessor gap at line {line_number}")
        current = event.get("hash")
        if not isinstance(current, str) or not hmac.compare_digest(digest(event), current):
            raise ChainIntegrityError(f"chain digest mismatch at line {line_number}")
        seq, previous = expected, current
    return seq, previous


def _validated_head(path: Path) -> tuple[int, str]:
    try:
        with path.open("rb") as fh:
            return _read_head(fh)
    except FileNotFoundError:
        return 0, ""


@contextlib.contextmanager
def _exclusive(fd: int):
    """A short inter-process lock; contention loses telemetry rather than stalling work."""
    deadline = time.monotonic() + LOCK_WAIT_SECONDS
    # `sys.platform` and not `os.name`: they answer the same question at runtime, and only
    # this one is a platform check a type checker understands. Under `os.name` the two lock
    # constants read as missing attributes everywhere except Windows, because the stubs for
    # `msvcrt` are not loaded on any other platform.
    if sys.platform == "win32":
        import msvcrt

        lock, unlock = msvcrt.LK_NBLCK, msvcrt.LK_UNLCK

        def apply(mode):
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, mode, 1)

    else:
        import fcntl

        lock, unlock = fcntl.LOCK_EX | fcntl.LOCK_NB, fcntl.LOCK_UN

        def apply(mode):
            fcntl.flock(fd, mode)

    while True:
        try:
            apply(lock)
            break
        except OSError as exc:
            if time.monotonic() >= deadline:
                raise TimeoutError("chain append is busy") from exc
            time.sleep(0.001)
    try:
        yield
    finally:
        apply(unlock)


def head(path: Path) -> tuple[int, str]:
    """(sequence, hash) of a valid last link, or (0, "") when none is readable."""
    try:
        return _validated_head(path)
    except (OSError, ChainIntegrityError):
        return 0, ""


def append(path: Path, events: list[dict]) -> int:
    """Link events onto an intact chain at `path`. Returns the new head sequence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_APPEND | os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0)
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    if no_follow:
        flags |= no_follow
    elif path.is_symlink():
        raise OSError("chain path is a symlink")
    fd = os.open(path, flags, 0o600)
    try:
        with _exclusive(fd):
            with os.fdopen(fd, "rb", closefd=False) as fh:
                seq, prev = _read_head(fh)
            lines = []
            for ev in events:
                seq += 1
                ev = {**ev, "seq": seq, "prev": prev}
                ev["hash"] = digest(ev)
                prev = ev["hash"]
                lines.append(stable_json(ev))
            payload = ("\n".join(lines) + "\n").encode()
            start = os.lseek(fd, 0, os.SEEK_END)
            try:
                while payload:
                    wrote = os.write(fd, payload)
                    if not wrote:
                        raise OSError("chain append wrote no data")
                    payload = payload[wrote:]
            except BaseException:
                with contextlib.suppress(OSError):
                    os.ftruncate(fd, start)
                raise
        return seq
    finally:
        os.close(fd)


def emit(name: str, cls: str, **data) -> None:
    """Record one decision. Never raises: a failure to record is not a reason to change
    what the caller was going to do."""
    if cls not in CLASSES:
        raise ValueError(f"unknown event class {cls!r}; the set is {CLASSES}")
    try:
        root = repo_root()
        event = {
            "ts": now(),
            "cls": cls,
            "name": name,
            "session": session_id(),
            "repo": repo_id(root),
            "machine": machine_id(),
            "operation_id": str(uuid.uuid4()),
            "trace_id": str(uuid.uuid4()),
            "data": data,
        }
        buf = buffer_path(root)
        if buf is None:
            append(chain_path(root), [event])
        else:
            event["stamp"] = stamp(event)  # unstamped, it is a line the agent can rewrite
            buf.parent.mkdir(parents=True, exist_ok=True)
            with buf.open("a", encoding="utf-8") as fh:
                fh.write(stable_json(event) + "\n")
    except Exception as exc:  # a failure to record never changes what the caller does
        print(f"[ai-eng] could not record {name}/{cls}: {exc}", file=sys.stderr)


def sealable(line: str) -> dict:
    """One buffered line, ready to be linked. A line that does not carry this machine's
    stamp — edited, truncated, or not JSON at all — is sealed as the error that says so,
    with what it claimed kept beside it. Dropping it instead would delete the only
    evidence that anything touched the record, and that evidence is the whole product.

    Except when the line names a different machine. `stamp` keys off `home()/buffer.key`,
    which `AI_ENGINEERING_HOME` redirects, while the buffer is repository-local and does
    not — so any process with its own home writes here with a key this machine has never
    seen. That is not tampering, and calling it tampering made this repository's own test
    suite put 22 permanently BROKEN links into the operator's chain: `audit verify` failed
    for good and `audit --anchor` stopped emitting a footer, so no commit on that machine
    could be anchored again. A chain accusing itself of an edit it never suffered is worse
    than no chain, because the one command that detects a real edit had been spent.

    A forged `machine` field buys nothing: it changes the body, so the digest changes, and
    the line still cannot be presented as an authenticated one of ours. It only relabels an
    unverifiable line as somebody else's, which is what it is."""
    try:
        event = json.loads(line)
        if hmac.compare_digest(event.pop("stamp", ""), stamp(event)):
            return event
    except (AttributeError, TypeError, ValueError):
        event = {"data": {"line": line[:120]}}
    named = event.get("machine") if isinstance(event, dict) else None
    if isinstance(named, str) and named and named != machine_id():
        return {
            "ts": now(),
            "name": "buffer",
            **event,
            "machine": machine_id(),
            "cls": "error",
            "data": {"outcome": "foreign", "error": FOREIGN, "machine": named},
        }
    event = {"ts": now(), "name": "buffer", **event, "cls": "error"}
    event["data"] = {"outcome": "edited", "error": EDITED, "claimed": event.get("data")}
    return event


def flush(root: Path | None = None) -> int:
    """Append the in-flight buffer to the durable chain and empty it. Nothing is lost:
    this is a move, not a discard."""
    buf = buffer_path(root)
    if buf is None or not buf.exists():
        return 0
    events = [sealable(line) for line in buf.read_text().splitlines() if line.strip()]
    if events:
        append(chain_path(root), events)
    buf.write_text("")
    return len(events)
