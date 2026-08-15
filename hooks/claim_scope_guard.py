"""Writing outside the paths this writer claimed.

A claim says which paths one writer may change while it is held. Two agents that each
claimed different paths can work at the same time; two that write wherever they like
cannot, and the second one finds out at the merge. So the claim is enforced where the write
happens, not where the conflict appears.

No claim in force means no opinion: every repository that has never coordinated writes as
it always did. A claim that cannot be read is the opposite — somebody may hold this work,
and the one thing that must not happen is writing anyway.
"""

from __future__ import annotations

import json
from pathlib import Path

from _emit import repo_root
from _wrap import guard

CLAIM = Path(".ai") / "claim.json"
MAX_BYTES = 100_000


def held(root: Path) -> dict | None:
    """The claim in force, or None when there is none. A file that exists and cannot be
    parsed raises: the caller turns that into a denial, because "unreadable" and "absent"
    must not be the same answer."""

    where = root / CLAIM
    if not where.is_file():
        return None
    body = where.read_text(encoding="utf-8", errors="strict")[:MAX_BYTES]
    record = json.loads(body)
    if not isinstance(record, dict) or not isinstance(record.get("paths"), list):
        raise ValueError("a claim record with no paths")
    return record


def decide(root: Path, target: str) -> str | None:
    """None to allow, a sentence to deny. The sentence names the item and the paths,
    because the person reading it is choosing between widening the claim and taking a
    different task, and neither is possible from the word "denied"."""

    try:
        claim = held(root)
    except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return f"a claim is present and could not be read: {CLAIM}. Fix it or remove it."
    if claim is None:
        return None
    if not target:
        return None

    # Resolved, not compared as text: `src/thing.py/../../elsewhere.py` is inside the claim
    # by string and outside it by path, and the string is the one an attacker writes.
    try:
        inside = Path(target).resolve().relative_to(Path(root).resolve())
    except (ValueError, OSError):
        return (
            f"{claim.get('item', 'this claim')} is held over "
            f"{', '.join(claim['paths'])} and this write is outside the repository."
        )

    posix = inside.as_posix()
    for claimed in claim["paths"]:
        wanted = str(claimed).rstrip("/")
        if posix == wanted or posix.startswith(f"{wanted}/"):
            return None
    return (
        f"{claim.get('item', 'this claim')} claims {', '.join(claim['paths'])} and this "
        f"write is to {posix}. Widen the claim, or take a task that owns this path."
    )


@guard("claim_scope_guard")
def run(payload: dict) -> str | None:
    root = repo_root()
    if root is None:
        return None
    return decide(root, (payload.get("tool_input") or {}).get("file_path", ""))
