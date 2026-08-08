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
import json
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

CLASSES = ("blocked", "allowed", "bypassed", "command", "error", "session")


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
    """Stable per machine. Written once; deleting it makes `init` treat this as new."""
    receipt = home() / "machine.json"
    try:
        return json.loads(receipt.read_text())["machine_id"]
    except Exception:
        mid = uuid.uuid4().hex[:12]
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
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def head(path: Path) -> tuple[int, str]:
    """(sequence, hash) of the last link, or (0, "") for an empty chain."""
    try:
        last = ""
        with path.open("rb") as fh:
            for raw in fh:
                if raw.strip():
                    last = raw.decode()
        if last:
            ev = json.loads(last)
            return int(ev["seq"]), ev["hash"]
    except (OSError, ValueError, KeyError):
        pass
    return 0, ""


def append(path: Path, events: list[dict]) -> int:
    """Link events onto the chain at `path`. Returns the new head sequence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    seq, prev = head(path)
    lines = []
    for ev in events:
        seq += 1
        ev = {**ev, "seq": seq, "prev": prev}
        ev["hash"] = digest(ev)
        prev = ev["hash"]
        lines.append(json.dumps(ev, separators=(",", ":")))
    with path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return seq


def emit(name: str, cls: str, **data) -> None:
    """Record one decision. Never raises: a failure to record is not a reason to change
    what the caller was going to do."""
    if cls not in CLASSES:
        raise ValueError(f"unknown event class {cls!r}; the set is {CLASSES}")
    root = repo_root()
    event = {
        "ts": now(),
        "cls": cls,
        "name": name,
        "session": session_id(),
        "repo": repo_id(root),
        "machine": machine_id(),
        "data": data,
    }
    try:
        buf = buffer_path(root)
        if buf is None:
            append(chain_path(root), [event])
        else:
            buf.parent.mkdir(parents=True, exist_ok=True)
            with buf.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, separators=(",", ":")) + "\n")
    except Exception as exc:  # a failure to record never changes what the caller does
        print(f"[ai-eng] could not record {name}/{cls}: {exc}", file=sys.stderr)


def flush(root: Path | None = None) -> int:
    """Append the in-flight buffer to the durable chain and empty it. Nothing is lost:
    this is a move, not a discard."""
    buf = buffer_path(root)
    if buf is None or not buf.exists():
        return 0
    events = [json.loads(line) for line in buf.read_text().splitlines() if line.strip()]
    if events:
        append(chain_path(root), events)
    buf.write_text("")
    return len(events)
