"""Walking the chain, link by link.

Not the same job as doctor: doctor looks at the chain's head and whether it is writable
and takes a second, and runs every session. This walks the whole history, and runs in
CI and on the day somebody asks you for proof.

The anchor is what makes losing the laptop survivable. The commit-msg hook writes the
(repository, machine) pair, the sequence number and the head's first twelve characters
into every commit, so git history — immutable and replicated — carries a tamper-evident
checkpoint. Lose the machine and you lose the event bodies, not the proof of the head.

Solution Intent is current-state evidence, not chain metadata. When its canonical record
exists, audit validates that record and reads every relation target again; an event that
says those relations passed cannot make changed or missing bytes green.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from ai_engineering import paths

ANCHOR = re.compile(r"^Ai-Eng-Anchor: (\S+)/(\S+) seq=(\d+) head=([0-9a-f]{12})$", re.M)
INTENT_HOME = ".ai/intent.md"
INTENT_INCOMPLETE_PREFIX = f"Solution Intent at {INTENT_HOME} is INCOMPLETE: "


def read(root: Path | None) -> list[dict]:
    emit = paths.load("_emit")
    try:
        lines = emit.chain_path(root).read_text().splitlines()
    except OSError:
        return []
    out = []
    for line in filter(str.strip, lines):
        try:
            out.append(json.loads(line))
        except ValueError:
            # A hook killed mid-append leaves half a line behind. Doctor may skip it; here
            # skipping is how a chain cut at the end walks clean and reports itself intact.
            out.append({"ts": "?", "cls": "unreadable", "name": "?", "hash": ""})
    return out


def verify_intent(root: Path) -> list[str]:
    """Recompute Intent health from its current home and relation target bytes."""
    from ai_engineering import intent

    source = root / INTENT_HOME
    if not source.is_file():
        return [
            INTENT_INCOMPLETE_PREFIX
            + f"INTENT_HOME_MISSING — Solution Intent is missing at {INTENT_HOME}"
        ]
    result = intent.validate(source, root)
    if result.outcome == "PASS":
        return []
    return [INTENT_INCOMPLETE_PREFIX + f"{result.code} — {result.reason}"]


def verify(root: Path | None, anchors: bool) -> list[str]:
    emit = paths.load("_emit")
    problems = []
    prev = ""
    for seq, event in enumerate(read(root), 1):
        if event.get("cls") == "unreadable":
            problems.append(f"link {seq}: the line is not JSON — a write was cut here")
            continue
        if (event.get("data") or {}).get("outcome") == "edited":
            # Sealed truthfully, so every hash below matches. Without this line the one
            # command README.md offers as the tamper detector exits 0 over a rewritten event.
            problems.append(f"link {seq}: it arrived edited before it was sealed")
        if event.get("seq") != seq:
            problems.append(f"link {seq}: the sequence jumps to {event.get('seq')}")
        if event.get("prev") != prev:
            problems.append(f"link {seq}: it does not extend the link before it")
        body = {k: v for k, v in event.items() if k != "hash"}
        if emit.digest(body) != event.get("hash"):
            problems.append(f"link {seq}: the hash does not match its own body — it was edited")
        prev = event.get("hash", "")
    if anchors and root is not None:
        known = {e["hash"][:12] for e in read(root)}
        log = subprocess.run(
            ["git", "-C", str(root), "log", "--format=%B%x00", "-n", "200"],
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        for _, machine, number, head in ANCHOR.findall(log):
            if machine == emit.machine_id() and head not in known:
                problems.append(
                    f"a commit anchors head {head} at seq {number}, and this chain "
                    f"has no such link: the record was truncated or replaced"
                )
    if root is not None:
        problems.extend(verify_intent(root))
    return problems


def replay(root: Path | None, session: str) -> list[str]:
    rows = []
    for event in read(root):
        if session and event.get("session") != session:
            continue
        data = event.get("data") or {}
        detail = data.get("reason") or data.get("error") or data.get("verb") or ""
        rows.append(f"  {event['ts']}  {event['cls']:<9} {event['name']:<16} {detail}")
    return rows


def anchor_line(root: Path | None) -> str:
    emit = paths.load("_emit")
    seq, head = emit.head(emit.chain_path(root))
    return f"\nAi-Eng-Anchor: {emit.repo_id(root)}/{emit.machine_id()} seq={seq} head={head[:12]}\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser("ai-eng audit")
    parser.add_argument("action", nargs="?", default="verify", choices=["verify", "replay"])
    parser.add_argument("--anchors", action="store_true", help="also check the anchors in git")
    parser.add_argument("--session", default="")
    parser.add_argument("--anchor", action="store_true", help="print the footer for commit-msg")
    args = parser.parse_args(argv)

    root = paths.repo_root()
    if args.anchor:
        print(anchor_line(root), end="")
        return 0
    if args.action == "replay":
        rows = replay(root, args.session)
        print("\n".join(rows) if rows else "  nothing recorded for that session")
        return 0
    problems = verify(root, args.anchors)
    if problems:
        print(
            "\n".join(
                f"  {'INCOMPLETE' if line.startswith(INTENT_INCOMPLETE_PREFIX) else 'BROKEN'}  "
                f"{line}"
                for line in problems
            )
        )
        return 1
    print(f"  ✓ {len(read(root))} links, intact, and each one extends the one before it.")
    return 0
