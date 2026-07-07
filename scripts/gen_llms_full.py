#!/usr/bin/env python3
"""Regenerate llms-full.txt — the derived full-corpus cache for AI ingestion.

SSOT-PD (CONSTITUTION Prohibition 8): llms-full.txt is a *derived cache*.
This script is its named rebuild command. Run it after editing any source
below; never hand-edit the concatenated body.

    python -m scripts.gen_llms_full
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "llms-full.txt"

# Source order is contractual: it matches the header's "Regenerate from" list.
SOURCES = [
    "README.md",
    "docs/guides/getting-started.md",
    "docs/index.md",
    "docs/architecture/index.md",
    "docs/architecture/brand-tokens.md",
    "docs/persistence-doctrine.md",
    "CONSTITUTION.md",
    "AGENTS.md",
]

RULE = "=" * 64

HEADER = (
    "# {ai} engineering — full documentation corpus\n"
    "\n"
    "> Derived cache: concatenated user-facing and canonical docs for AI "
    "agent ingestion.\n"
    "> Regenerate from: README, docs/guides/getting-started, docs/index, "
    "docs/architecture/index, docs/architecture/brand-tokens, "
    "docs/persistence-doctrine, CONSTITUTION, AGENTS.\n"
    "> Rebuild command: `python -m scripts.gen_llms_full`.\n"
)


def build() -> str:
    parts = [HEADER]
    for rel in SOURCES:
        body = (REPO_ROOT / rel).read_text(encoding="utf-8").rstrip("\n")
        parts.append(f"\n\n{RULE}\n# FILE: {rel}\n{RULE}\n\n{body}\n")
    return "".join(parts)


def main() -> None:
    OUTPUT.write_text(build(), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(REPO_ROOT)} from {len(SOURCES)} sources.")


if __name__ == "__main__":
    main()
