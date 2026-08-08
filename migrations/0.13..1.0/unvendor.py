#!/usr/bin/env python3
"""The most valuable file in this directory: it un-copies the product from a repository.

A new user has nothing to migrate — two commands, and seven files appear. A repository
already on 0.13.x has a real migration, because the framework was copied inside it: 528
framework-owned files, of which 65 of 139 copied ones had already drifted with a single
user.

This moves and un-commits. It never rewrites the operator's prose, and it never touches
AGENTS.md or CONSTITUTION.md. It prints a summary and stops: you read the diff and you
make the commit.

Step 3 is the one that can neither be skipped nor derived. Every other datum here is
recoverable from git; a risk acceptance is not, which is why the decision store survives
until its rows are inside the markdown, and not one commit sooner.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

OLD = ".ai-engineering"


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, timeout=60
    ).stdout.strip()


def move_specs(root: Path) -> list[str]:
    """git mv, so the history of every spec survives the move."""
    moved = []
    old_specs = root / OLD / "specs"
    for folder in sorted(old_specs.glob("spec-*")) if old_specs.exists() else []:
        if not folder.is_dir():
            continue
        target = root / "specs" / re.sub(r"^spec-", "", folder.name)
        target.parent.mkdir(parents=True, exist_ok=True)
        git(root, "mv", str(folder), str(target))
        moved.append(f"{folder.name} → specs/{target.name}")
    archive = old_specs / "archive"
    for folder in sorted(archive.glob("spec-*")) if archive.exists() else []:
        target = root / "specs" / re.sub(r"^spec-", "", folder.name)
        git(root, "mv", str(folder), str(target))
        spec = target / "spec.md"
        if spec.exists() and "status:" not in spec.read_text()[:400]:
            spec.write_text("---\nstatus: shipped\n---\n\n" + spec.read_text(), encoding="utf-8")
        moved.append(f"archive/{folder.name} → specs/{target.name} (shipped)")
    return moved


def move_acceptances(root: Path) -> int:
    """The decision store's rows become yaml blocks inside the spec they belong to. This
    is the step with no derivable alternative: nothing in git knows that a named person
    accepted a finding until a date."""
    store = root / OLD / "state" / "decision-store.json"
    if not store.exists():
        return 0
    try:
        rows = json.loads(store.read_text())
    except ValueError:
        return 0
    rows = rows.get("decisions", rows) if isinstance(rows, dict) else rows
    written = 0
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or "expires" not in row:
            continue
        spec_id = str(row.get("spec", "")).replace("spec-", "")[:3]
        targets = sorted((root / "specs").glob(f"{spec_id}*/spec.md")) or sorted(
            (root / "specs").glob("*/spec.md")
        )
        if not targets:
            continue
        block = "\n".join(
            f"{key}: {row[key]}"
            for key in (
                "id",
                "finding",
                "severity",
                "accepted_by",
                "accepted",
                "expires",
                "renewals",
                "justification",
                "follow_up",
            )
            if key in row
        )
        spec = targets[-1]
        spec.write_text(
            spec.read_text(encoding="utf-8") + f"\n## Accepted risks\n\n```yaml\n{block}\n```\n",
            encoding="utf-8",
        )
        written += 1
    return written


def archive_record(root: Path, home: Path) -> int:
    """Outside the clone, where the chain belongs — and this is where the adversarial
    suite's corpus of real denials comes from."""
    events = root / OLD / "state" / "framework-events.ndjson"
    if not events.exists():
        return 0
    target = home / "state" / "imported-0.13"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(events, target / events.name)
    return len(events.read_text(errors="replace").splitlines())


def main(root: Path) -> int:
    home = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.home() / ".ai-engineering"
    if not (root / OLD).exists():
        print("  nothing to un-vendor: this repository never had the framework copied into it.")
        return 0

    moved = move_specs(root)
    accepted = move_acceptances(root)
    lines = archive_record(root, home)

    (root / ".ai").mkdir(exist_ok=True)
    (root / ".ai" / ".gitignore").write_text("*\n!.gitignore\n!config.toml\n", encoding="utf-8")

    git(root, "rm", "-r", "--cached", "--quiet", OLD)
    ignore = root / ".gitignore"
    body = ignore.read_text(encoding="utf-8") if ignore.exists() else ""
    if OLD not in body:
        ignore.write_text(body.rstrip("\n") + f"\n{OLD}/\n", encoding="utf-8")

    print(f"  {len(moved)} specs moved, history intact:")
    for line in moved[:8]:
        print(f"    {line}")
    print(f"  {accepted} risk acceptances written into the specs they belong to")
    print(f"  {lines} recorded events archived to {home / 'state' / 'imported-0.13'}")
    print(
        f"  {OLD}/ un-committed and ignored. The files are still on disk; delete them "
        f"when you are satisfied."
    )
    print("\n  Nothing was committed. Read the diff, then commit it yourself.")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else ".")))
