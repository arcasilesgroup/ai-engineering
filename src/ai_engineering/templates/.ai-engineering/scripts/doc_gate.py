#!/usr/bin/env python3
"""Doc-gate: assert CHANGELOG/README accompanies code changes (brief §17).

If any changed path matches one of the watched roots
(``src/``, ``tools/``, ``.claude/skills/``), then at least one of
``CHANGELOG.md`` / ``README.md`` (case-insensitive at the repo root)
must also be in the changed set. Otherwise exit 1.

Exit 0 = OK / no docs needed. Exit 1 = changed code without docs.

No git invocation — caller passes the changed paths via
``--changed-paths`` (comma-separated). Lets the gate run identically
in pre-commit, pre-push, CI, and the orchestrator.

Usage:

```
python3 .ai-engineering/scripts/doc_gate.py \
    --changed-paths "src/foo.py,docs/readme.md"   # exit 0
python3 .ai-engineering/scripts/doc_gate.py \
    --changed-paths "src/foo.py"                  # exit 1
python3 .ai-engineering/scripts/doc_gate.py \
    --changed-paths "tools/x.py,CHANGELOG.md"     # exit 0
```
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable

WATCHED_ROOTS: tuple[str, ...] = ("src/", "tools/", ".claude/skills/")
DOC_FILES: tuple[str, ...] = ("CHANGELOG.md", "README.md")


def _normalise(paths: Iterable[str]) -> list[str]:
    """Lowercase + slash-normalise paths for matching."""
    cleaned: list[str] = []
    for raw in paths:
        p = raw.strip().replace("\\", "/")
        if not p:
            continue
        cleaned.append(p)
    return cleaned


def _matches_watched(path: str) -> bool:
    return any(path.startswith(root) for root in WATCHED_ROOTS)


def _has_doc(paths: Iterable[str]) -> bool:
    """Case-insensitive match: any path with the same basename as a doc file."""
    doc_basenames = {d.lower() for d in DOC_FILES}
    for path in paths:
        # Match either ``CHANGELOG.md`` at root or ``./CHANGELOG.md`` at root.
        # Sub-dir CHANGELOGs (e.g. ``packages/foo/CHANGELOG.md``) do not satisfy
        # the gate — the contract is the repo-root file.
        if "/" in path.lstrip("./"):
            continue
        if path.lower().lstrip("./") in doc_basenames:
            return True
    return False


def evaluate(paths: list[str]) -> tuple[bool, str]:
    """Return ``(ok, reason)``. ``ok`` False → exit 1."""
    cleaned = _normalise(paths)
    code_changed = [p for p in cleaned if _matches_watched(p)]
    if not code_changed:
        return True, "no watched paths changed — gate skipped"
    if _has_doc(cleaned):
        return True, f"{len(code_changed)} watched path(s) + doc file present — OK"
    return False, (
        f"{len(code_changed)} watched path(s) changed without CHANGELOG.md or "
        f"README.md: {sorted(code_changed)[:5]}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="doc_gate",
        description="Assert CHANGELOG/README accompanies code changes in watched roots.",
    )
    parser.add_argument(
        "--changed-paths",
        required=True,
        help="Comma-separated list of changed paths.",
    )
    args = parser.parse_args(argv)

    paths = [p.strip() for p in args.changed_paths.split(",") if p.strip()]
    ok, reason = evaluate(paths)
    sys.stdout.write(f"doc_gate: {reason}\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
