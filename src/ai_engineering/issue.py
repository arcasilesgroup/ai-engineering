"""The governed payload behind `ai-eng report issue`.

The competing product's reporter read specs, events and included files before it drafted
anything, and what it sent was whatever that reading turned up. This one cannot do that:
the payload is an allow-list, so logs, diffs, environment, paths, hosts and remotes have no
field to arrive in. The scanners exist for the one route left — a person pasting one of
those classes into the prose — and they refuse rather than redact, because a redaction is a
guess about which half mattered.

Nothing here sends. Drafting writes one local file under `.ai/`, whose `.gitignore`
excludes everything it does not name, and prints the exact bytes with their digest.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from ai_engineering import __version__, acceptance_privacy, paths

SCHEMA = paths.policy("issue-v1.schema.json")
SCHEMA_ID = "urn:ai-engineering:issue:1"

# One home for the field list. `surface.SURFACES` learned this the expensive way: the same
# eight ids written into four files, only two of them bound, and a ninth would have left
# three copies behind. The schema is the declaration; this module reads it.
_DECLARED = json.loads(SCHEMA.read_text(encoding="utf-8"))["properties"]
FIELDS: tuple[str, ...] = tuple(_DECLARED)
KINDS: tuple[str, ...] = tuple(_DECLARED["kind"]["enum"])

# Every field whose value is prose a person wrote. These are the only ones a forbidden class
# can reach, and every one of them is scanned.
PROSE = ("title", "what_happened", "expected")


def build(
    kind: str,
    title: str,
    what_happened: str,
    expected: str,
    steps: list[str],
    now: datetime | None = None,
) -> dict:
    """Assemble the payload from what was typed, and from one fact about this package.

    `framework_version` is the only value not passed in, and it is a property of the
    software being reported rather than of the machine reporting it. Nothing reads the
    repository, the environment, the working directory or the host: a report that collects
    is a report whose author cannot say what it contains.
    """

    stamp = (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema": SCHEMA_ID,
        "schema_version": "1",
        "kind": kind,
        "title": title,
        "what_happened": what_happened,
        "expected": expected,
        "steps": list(steps),
        "framework_version": __version__,
        "created_at": stamp,
    }


def exact_bytes(payload: dict) -> bytes:
    """The bytes that would leave, and the same bytes that get written, scanned, hashed and
    shown. One serialisation, because a preview of a different rendering is a preview of
    something else."""

    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")


def digest(payload: dict) -> str:
    return hashlib.sha256(exact_bytes(payload)).hexdigest()


def draft_path(root: Path) -> Path:
    return root / ".ai" / "issue" / "draft.json"


def scan(root: Path, payload: dict) -> list[acceptance_privacy.Verdict]:
    """Two scans over the exact bytes, and a machine-path check over the prose.

    `PASS` is the only clean answer. `INCOMPLETE` — a scanner that is absent, the wrong
    version, or looking at text it cannot classify — blocks exactly like `FAIL`, because a
    bound read as clean is a bound turned into a bypass.

    The secret scan needs a directory, so it gets one that holds the payload and nothing
    else, in a temporary directory that is gone before this returns. The draft is never
    written for a scan: a refused payload that left a file behind is a payload somebody can
    still send.
    """

    findings = [
        verdict
        for field in PROSE
        for verdict in (
            acceptance_privacy.acceptance_machine_path_v1(payload.get(field)),
            acceptance_privacy.acceptance_pii_v1(payload.get(field)),
        )
        if verdict.outcome != "PASS"
    ]
    findings += [
        verdict
        for step in payload.get("steps", [])
        for verdict in (
            acceptance_privacy.acceptance_machine_path_v1(step),
            acceptance_privacy.acceptance_pii_v1(step),
        )
        if verdict.outcome != "PASS"
    ]

    # Outside the repository, and holding this payload alone. Scanning it where the draft
    # goes would mean writing the draft before deciding whether it may exist, and scanning
    # the repository instead would answer a different question — whether anything anywhere
    # holds a secret, which is `just security`'s job and not this one's.
    with tempfile.TemporaryDirectory() as area:
        holding = Path(area) / "payload.json"
        holding.write_bytes(exact_bytes(payload))
        secrets = acceptance_privacy.gitleaks_v1(Path(area))
    if secrets.outcome != "PASS":
        findings.append(secrets)
    return findings


def draft(root: Path, payload: dict) -> Path:
    """Write the local draft and show what it holds.

    The digest is printed beside the bytes so that a person confirming a send confirms one
    exact payload, and so that anything reading the receipt afterwards can tell whether the
    file changed between the preview and the confirmation.
    """

    written = draft_path(root)
    written.parent.mkdir(parents=True, exist_ok=True)
    body = exact_bytes(payload)
    written.write_bytes(body)
    print(body.decode("utf-8"))
    print(f"\n  sha256 {digest(payload)}")
    print(f"  draft  {written.relative_to(root)}  (local, gitignored, nothing has been sent)")
    return written
