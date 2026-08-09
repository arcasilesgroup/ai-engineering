"""Undoes everything the receipt lists. The no-lock-in promise, as a command.

It never touches specs/, your CONSTITUTION.md or your AGENTS.md. Those were yours from
the second they were written, and deleting somebody's record to uninstall a tool is the
behaviour this product was built to argue against.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from ai_engineering import paths, wiring

KEEPS = ("specs/", "CONSTITUTION.md", "AGENTS.md", "docs/adr/")


def strip_entries(path: Path) -> bool:
    try:
        blob = path.read_text(encoding="utf-8")
    except OSError:
        return False
    if wiring.SIGNATURE not in blob:
        return False
    data = json.loads(blob)

    def clean(node):
        if isinstance(node, list):
            return [clean(item) for item in node if wiring.SIGNATURE not in json.dumps(item)]
        if isinstance(node, dict):
            return {key: clean(value) for key, value in node.items()}
        return node

    wiring.write_json(path, clean(data))
    return True


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser("ai-eng uninstall")
    parser.add_argument("--project", action="store_true", help="also unwire this repository")
    parser.add_argument("-y", "--yes", action="store_true")
    args = parser.parse_args(argv)

    receipt = wiring.receipt()
    rows = receipt.get("wrote", [])
    print(f"  {len(rows)} things were written by this install, and every one is listed here:")
    for row in rows:
        print(f"    {row['kind']:<8} {row['path']}")
    print(f"  Kept, always: {', '.join(KEEPS)}")
    if not (
        args.yes
        or (sys.stdin.isatty() and input("\n◆ Remove them? (y/N) › ").lower().startswith("y"))
    ):
        print("  nothing removed.")
        return 1

    for row in rows:
        path = Path(row["path"])
        if row["kind"] == "guard":
            print(
                f"  ✓ entries removed from {path}"
                if strip_entries(wiring.expand(row["path"]))
                else f"  → {path} had no entry of ours"
            )
        elif row["kind"] == "link":
            for link in path.glob("ai-*"):
                link.unlink() if link.is_symlink() else None
            print(f"  ✓ symlinks removed from {path}")

    if args.project:
        root = paths.repo_root()
        if root is not None:
            subprocess.run(
                ["git", "-C", str(root), "config", "--unset", "core.hooksPath"], timeout=10
            )
            for name in (".ai/config.toml", ".ai/.gitignore", "CLAUDE.md", "justfile"):
                (root / name).unlink(missing_ok=True)
            print(f"  ✓ {root} unwired. specs/, CONSTITUTION.md and AGENTS.md are untouched.")
    print(
        f"\n  The record is still at {paths.home() / 'state'}. Delete that folder yourself "
        f"if you want it gone: it is proof of what happened, and not ours to throw away."
    )
    return 0
