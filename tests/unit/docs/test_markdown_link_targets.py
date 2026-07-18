"""spec-187 W4 (T-48, D-187-04): the canonical `.md` surface carries no broken
relative-`.md` links.

After the W1 dead-surface purge (reference triad, predecessor drafts,
ai-analyze-permissions, reviewer/verifier flat stubs), a lingering
`[text](path.md)` pointing at a deleted file would be a silent dangling
reference. This test resolves every relative markdown link across the
author-owned documentation surface and asserts the target exists, so a
dangling link is a red gate instead of a review opinion.

Scope: relative `.md` link targets only. External links (`http(s)://`,
`mailto:`), pure anchors (`#...`), and non-`.md` targets are out of scope
(they have their own contracts). Generated mirrors are not scanned here —
they regenerate byte-for-byte from the canonical source under test.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# Author-owned canonical documentation surface.
_SCAN_FILES = ("CLAUDE.md", "AGENTS.md", "README.md", "CONSTITUTION.md", "SOUL.md")
_SCAN_DIRS = ("docs", ".ai-engineering/reference", ".claude/skills", ".claude/agents")

_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#")


def _canonical_docs() -> list[Path]:
    files = [ROOT / name for name in _SCAN_FILES if (ROOT / name).is_file()]
    for rel in _SCAN_DIRS:
        base = ROOT / rel
        if base.is_dir():
            files.extend(sorted(base.rglob("*.md")))
    return files


def _relative_md_links(text: str) -> list[str]:
    links: list[str] = []
    for match in _LINK_RE.finditer(text):
        target = match.group(1).strip()
        if target.startswith(_EXTERNAL_PREFIXES):
            continue
        # Drop an optional "title" and any trailing anchor.
        target = target.split(" ", 1)[0].split("#", 1)[0]
        if target.endswith(".md"):
            links.append(target)
    return links


def test_no_broken_relative_md_links() -> None:
    broken: list[str] = []
    for doc in _canonical_docs():
        text = doc.read_text(encoding="utf-8", errors="replace")
        for target in _relative_md_links(text):
            resolved = (doc.parent / target).resolve()
            if not resolved.exists():
                broken.append(f"{doc.relative_to(ROOT)} -> {target}")
    assert not broken, "broken relative .md links:\n" + "\n".join(broken)
