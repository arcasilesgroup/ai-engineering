"""front-loading/BLUF checker — spec-189 authoring-structure lint (D-189-08).

Encodes the front-loading contract: a skill's body must open with a
bottom-line-up-front recap so weaker open-weight models get the answer
first (Liu et al. lost-in-the-middle; spec-189 research). The recap is
the BODY region between the H1 title and the first ``## `` header, and it
must be the BLUF:

* **<= 2 sentences** — the recap is a bottom-line, not a preamble. A
  region over two sentences is prose that buries the lede.
* **No list line** — a line starting with ``- ``, ``* ``, or ``N.`` in
  the recap means the bottom-line has fanned out into structure before
  the first section. Keep it 1-2 prose sentences.
* **Present** — an H1 immediately followed by ``## `` has no recap at
  all (missing BLUF).

Any violation is a MAJOR ``front_loading_bluf`` finding, mirroring the
``effort.py`` / ``token_budget.py`` posture (spec-189 D-189-08). All
reason strings are pure ASCII so a raw / non-tty write stays cp1252-safe
(D-187-10). Pure stdlib (``re`` + ``pathlib``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

_VALID_SEVERITIES = {"OK", "INFO", "MINOR", "MAJOR", "CRITICAL"}

# A recap over this many sentences buries the bottom-line.
_MAX_SENTENCES = 2


@dataclass(frozen=True)
class RubricResult:
    """Outcome of the front-loading check against a file."""

    rule_name: str
    severity: str
    reason: str

    def __post_init__(self) -> None:
        if self.severity not in _VALID_SEVERITIES:
            raise ValueError(f"severity {self.severity!r} not in {sorted(_VALID_SEVERITIES)}")


_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
# H1 title line (``# Title``) — a single leading hash, not ``##``.
_H1_RE = re.compile(r"^#\s+\S")
# First section header (``## ``) — the recap region ends here.
_H2_RE = re.compile(r"^##\s")
# A list line: bullet (``- ``/``* ``) or numbered step (``N.``).
_LIST_LINE_RE = re.compile(r"^(?:[-*]\s|\d+\.)")
# Sentence terminator followed by whitespace or end-of-string.
_SENTENCE_RE = re.compile(r"[.!?]+(?=\s|$)")


def _bluf_region(text: str) -> list[str]:
    """Return the recap-region lines between the H1 title and first ``## ``.

    Leading / trailing blank lines are stripped. When no H1 is present the
    region begins at the body start (after frontmatter).
    """
    body = _FRONTMATTER_RE.sub("", text, count=1)
    lines = body.splitlines()

    start = 0
    for idx, line in enumerate(lines):
        if _H1_RE.match(line):
            start = idx + 1
            break

    region: list[str] = []
    for line in lines[start:]:
        if _H2_RE.match(line):
            break
        region.append(line)

    # Trim surrounding blank lines.
    while region and not region[0].strip():
        region.pop(0)
    while region and not region[-1].strip():
        region.pop()
    return region


def _sentence_count(region: list[str]) -> int:
    """Count sentences across the recap region's prose lines.

    List lines are excluded from the sentence tally (they are flagged
    separately). A non-empty region with no terminal punctuation counts
    as one sentence.
    """
    prose = " ".join(
        line.strip() for line in region if line.strip() and not _LIST_LINE_RE.match(line.strip())
    )
    if not prose:
        return 0
    terminators = len(_SENTENCE_RE.findall(prose))
    return max(terminators, 1)


def check_file_frontloading(md_path: Path) -> list[RubricResult]:
    """Run the front-loading/BLUF rule against a single markdown file.

    Returns a list of ``RubricResult`` (one per triggered rule). An
    all-clear file returns a single ``OK`` result. A missing / oversized /
    list-bearing recap returns a single MAJOR ``front_loading_bluf``.
    """
    if not md_path.is_file():
        return [RubricResult("front_loading_bluf", "CRITICAL", f"file not found at {md_path}")]

    text = md_path.read_text(encoding="utf-8")
    region = _bluf_region(text)

    if not region:
        return [
            RubricResult(
                "front_loading_bluf",
                "MAJOR",
                "no BLUF recap between H1 and first ## header (add a 1-2 sentence bottom-line)",
            )
        ]

    reasons: list[str] = []
    if any(_LIST_LINE_RE.match(line.strip()) for line in region if line.strip()):
        reasons.append("BLUF recap contains a list line (keep it 1-2 prose sentences)")

    sentences = _sentence_count(region)
    if sentences > _MAX_SENTENCES:
        reasons.append(
            f"BLUF recap is {sentences} sentences "
            f"(over {_MAX_SENTENCES} - tighten to a 1-2 sentence bottom-line)"
        )

    if reasons:
        return [RubricResult("front_loading_bluf", "MAJOR", "; ".join(reasons))]

    return [RubricResult("front_loading_bluf", "OK", "BLUF recap within contract")]


def check_frontloading(
    skills_root: Path,
    agents_root: Path,
) -> list[tuple[Path, RubricResult]]:
    """Walk canonical skills + agents and run the front-loading rule.

    Returns ``[(path, RubricResult), ...]`` sorted by path. BLOCKING as of
    spec-189 T-17 (D-189-08): a MAJOR / CRITICAL drives ``skill_lint``
    exit 1 now that the fleet baseline is clean.
    """
    results: list[tuple[Path, RubricResult]] = []

    if skills_root.is_dir():
        for skill_dir in sorted(skills_root.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                continue
            for result in check_file_frontloading(skill_md):
                results.append((skill_md, result))

    if agents_root.is_dir():
        for agent_md in sorted(agents_root.glob("*.md")):
            for result in check_file_frontloading(agent_md):
                results.append((agent_md, result))

    return results


def write_findings(results: list[tuple[Path, RubricResult]], stream: TextIO) -> None:
    """Write pure-ASCII, one-line-per-finding output (D-187-10).

    Only non-OK findings are written. Output is guaranteed ASCII so a raw /
    non-tty write is cp1252-safe.
    """
    for path, result in results:
        if result.severity == "OK":
            continue
        stream.write(f"{result.severity} front_loading {path}: {result.reason}\n")
