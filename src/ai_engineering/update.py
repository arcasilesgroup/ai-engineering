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
import re
import subprocess
import sys
from pathlib import Path

from ai_engineering import __version__, paths, wiring

OWNED = ("justfile", "CLAUDE.md", ".ai/config.toml")


def dirty(root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--", *OWNED],
        capture_output=True,
        text=True,
        timeout=15,
    ).stdout
    return [line[3:] for line in out.splitlines() if line.strip()]


def migrations(pinned: str, target: str) -> list[Path]:
    folder = paths.shipped("migrations")
    steps = []
    for path in sorted(folder.glob("*/")):
        low, _, high = path.name.partition("..")
        if low <= target and high >= pinned:
            steps += sorted(path.glob("*.py"))
    return steps


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser("ai-eng update")
    parser.add_argument("--to", default=__version__, help="the version to move this repository to")
    parser.add_argument("--force", action="store_true", help="print what would be discarded")
    args = parser.parse_args(argv)

    root = paths.repo_root()
    if root is None:
        print("not inside a repository")
        return 1
    pin = root / ".ai" / "config.toml"
    if not pin.exists():
        print("  this repository is not set up. `ai-eng init` first.")
        return 1
    pinned = paths.load("_emit").config(root).get("framework", {}).get("version", "0.0.0")
    print(f"  {pinned} → {args.to}")

    changes = dirty(root)
    if changes:
        print(f"  REFUSED — these are framework-owned and have uncommitted changes: {changes}")
        print(
            "  Commit or discard them first. --force prints exactly what it would discard;"
            " it never overwrites silently."
        )
        if not args.force:
            return 1
        print(f"  --force would discard: {changes}")
        return 1

    steps = migrations(pinned, args.to)
    print(
        f"  {len(steps)} migration(s) to run: "
        f"{', '.join(step.parent.name + '/' + step.name for step in steps) or 'none'}"
    )
    if not sys.stdin.isatty():
        print("  an update is a person's decision and there is no keyboard here. Nothing changed.")
        return 1
    if input("  Type y to run them › ").strip().lower() != "y":
        print("  nothing changed.")
        return 1

    for step in steps:
        subprocess.run([sys.executable, str(step), str(root)], check=True, timeout=600)
    pin.write_text(
        re.sub(
            r'^version = ".*"$',
            f'version = "{args.to}"',
            pin.read_text(encoding="utf-8"),
            count=1,
            flags=re.M,
        ),
        encoding="utf-8",
    )
    print(f"  ✓ the pin now reads {args.to} — that diff is the record of this update.")

    # What this machine chose, and never everything that happens to be installed on it.
    # This walked `detect()`, so declining Cursor at `init` and updating a week later wired
    # it — failClosed, which is what makes Cursor deny rather than advise — from a verb the
    # person ran to move a version number. And nothing was recorded, so `uninstall`
    # afterwards listed what init had written, took the consent, and left the rest running.
    mine = {row["path"] for row in wiring.receipt().get("wrote", []) if row["kind"] == "guard"}
    found = [s for s in wiring.detect() if s.get("settings") in mine]
    if not found:
        print("  → no guard entry of ours is recorded here. `ai-eng init --global` wires one.")
        return 0
    rewritten = wiring.install_guards([s for s in found if not s.get("append_only")])
    for name, target, detail in rewritten:
        print(f"  ✓ rewrote {target or name} ({detail})")
    # Written down, because an entry nothing recorded is an entry uninstall cannot find.
    wiring.record(
        [
            {"path": s["settings"], "kind": "guard", "how": s["writer"]}
            for s in found
            if not s.get("append_only")
        ]
    )
    for surface in [s for s in found if s.get("append_only")]:
        print(
            f"  → {surface['name']} left untouched. Its trust is a hash of the whole handler "
            f"and of its position, so it is only rewritten when the entry genuinely changes."
        )
    print(
        "\n  Read the diff and make the commit. `uv tool install ai-engineering=="
        f"{args.to}` installs the wheel this pin now names."
    )
    return 0
