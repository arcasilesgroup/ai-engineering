#!/usr/bin/env python3
"""Green now requires proof of work, not absence of failure.

The previous system's flagship gate came back green for ten days in a row without
running. Teaching this framework each tool's output format is exactly the router that
`just` exists to delete, so the contract moves to the interface: each repository prints
`RAN <name>=<n>` lines that it owns, and all this verifies is that they exist and are at
least one.

Usage: just check | tee check.log && python tests/anti_theatre.py check.log
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAN = re.compile(r"^RAN\s+([\w.-]+)=(\d+)\s*$", re.M)
# This check only ever runs on this repository — it is not in the wheel and does not reach
# a user's. So it covers the two manifests that can appear here, and no more.
MANIFESTS = {
    "pyproject.toml": ("uv.lock", "poetry.lock", "requirements.txt"),
    "package.json": ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb"),
}


def dependency_free(manifest: Path) -> bool:
    """A project that declares no dependencies has nothing to lock, and demanding a
    lockfile from it would teach people to commit an empty one."""
    text = manifest.read_text(errors="replace")
    if manifest.name == "pyproject.toml":
        import tomllib

        parsed = tomllib.loads(text)
        project = parsed.get("project", {})
        # dependency-groups is top level, not under project, and it is where uv puts dev
        # tools by default — missing it waives the modern layout while checking the old one.
        return not (
            project.get("dependencies")
            or project.get("optional-dependencies")
            or parsed.get("dependency-groups")
        )
    return False


def die(message: str) -> None:
    sys.stderr.write(f"anti-theatre: {message}\n")
    raise SystemExit(1)


def main(log: Path, root: Path) -> int:
    counts = {name: int(number) for name, number in RAN.findall(log.read_text(errors="replace"))}
    if not counts:
        die("check printed no RAN lines. It did not prove it ran. The green is a lie.")
    for name, number in counts.items():
        if number < 1:
            die(f"RAN {name}={number}: it ran over zero items, which is not a pass.")

    for manifest, lockfiles in MANIFESTS.items():
        for found in root.rglob(manifest):
            if any(part in {".git", "node_modules", ".venv"} for part in found.parts):
                continue
            if any((found.parent / lock).exists() for lock in lockfiles):
                continue
            if dependency_free(found):
                continue  # nothing to pin is not the same as nothing pinned
            die(
                f"{found}: there are dependencies and no lockfile, so the vulnerability "
                f"scan over it is silently empty."
            )

    print(
        f"anti-theatre: {len(counts)} RAN lines, all over at least one item — "
        f"{', '.join(f'{k}={v}' for k, v in sorted(counts.items()))}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2] if len(sys.argv) > 2 else ".")))
