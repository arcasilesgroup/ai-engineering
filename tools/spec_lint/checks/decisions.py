"""Decisions check — bullet-form + heading-form D-NNN-NN with rationale.

spec-131 D-131-17 contract: every entry in ``## Decisions`` carries a
decision ID matching ``D-<spec-id>-<NN>`` where ``<spec-id>`` matches
the frontmatter ``spec:`` value. Two source forms are accepted:

* **Bullet form** (spec-131 canonical):
  ``- **D-131-01 — Trim scope.** … *Rationale*: …``
* **Level-3 heading form** (spec-129 legacy archive):
  ``### D-129-01 — PR #509 scope expansion`` followed by
  ``**Rationale**: …`` later in the entry body.

Rationale prefix is accepted in both italic (``*Rationale*:``) and bold
(``**Rationale**:``) markdown so legacy specs pass without rewrite.
"""

from __future__ import annotations

import re
from pathlib import Path

from spec_lint.checks.frontmatter import CheckResult, _parse_frontmatter

# Decision-entry markers — bullet form (spec-131) and level-3 heading
# form (spec-129). ``[A-Za-z0-9-]`` covers both numeric ``131`` and
# slug-derived prefixes (``my-slug``).
_BULLET_RE = re.compile(r"^- \*\*(D-[A-Za-z0-9-]+-\d{2})\s+—")
_HEADING_RE = re.compile(r"^### (D-[A-Za-z0-9-]+-\d{2})\s+—")

# Rationale line — both italic ``*Rationale*:`` (spec-131) and bold
# ``**Rationale**:`` (spec-129) are accepted.
_RATIONALE_RE = re.compile(r"^\s*(?:\*Rationale\*|\*\*Rationale\*\*):")

# Look-ahead window when scanning for a rationale line after a decision
# marker. Covers the longest spec-131 entry observed (D-131-18, ~28
# source lines).
_RATIONALE_WINDOW = 30


def _expected_prefix(spec_id: str) -> str:
    """Compute the expected ``D-<spec-id>-`` prefix from the frontmatter value.

    * Numeric ``spec-131`` → ``D-131-``
    * Slug ``my-slug``    → ``D-my-slug-``

    The validator only checks the ID shape + prefix match; numbering is
    not required to be sequential nor monotonic (spec-131 ships D-131-18
    before D-131-17 in source order, by design).
    """
    if spec_id.startswith("spec-"):
        return f"D-{spec_id.removeprefix('spec-')}-"
    return f"D-{spec_id}-"


def _slice_section(text: str, name: str) -> list[str]:
    """Return the lines inside the ``## <name>`` block (heading excluded).

    Bounded by the next ``^## `` heading or end-of-file, whichever comes
    first.
    """
    lines = text.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if line == f"## {name}":
            start = idx + 1
            break
    if start is None:
        return []
    end = len(lines)
    for idx in range(start, len(lines)):
        if lines[idx].startswith("## "):
            end = idx
            break
    return lines[start:end]


def _is_decision_marker(line: str) -> bool:
    return bool(_BULLET_RE.match(line) or _HEADING_RE.match(line))


def _find_rationale(block_lines: list[str], start: int) -> bool:
    """Scan up to :data:`_RATIONALE_WINDOW` lines for the rationale prefix.

    Stops early when the next decision marker is encountered so an entry
    missing its own rationale never gets credit for a neighbour's.
    """
    end = min(start + _RATIONALE_WINDOW + 1, len(block_lines))
    for idx in range(start + 1, end):
        if _is_decision_marker(block_lines[idx]):
            return False
        if _RATIONALE_RE.match(block_lines[idx]):
            return True
    return False


def check_decisions(spec_path: Path) -> list[CheckResult]:
    """Validate every ``## Decisions`` entry against the contract.

    Emits:

    * ``BLOCKER decisions_section_empty`` when no decision markers are found.
    * ``BLOCKER decision_id_prefix_mismatch`` when an entry's ID does not
      start with the expected prefix derived from frontmatter ``spec:``.
    * ``BLOCKER decision_missing_rationale`` when an entry has no
      ``*Rationale*:`` or ``**Rationale**:`` line within the look-ahead
      window.
    """
    text = spec_path.read_text(encoding="utf-8")
    fields, _ = _parse_frontmatter(text)
    spec_id = (fields or {}).get("spec", "")
    expected_prefix = _expected_prefix(spec_id) if spec_id else ""

    block = _slice_section(text, "Decisions")
    if not block:
        # No section at all — sections.py emits the BLOCKER for this case;
        # decisions.py stays quiet to avoid double-counting.
        return []

    results: list[CheckResult] = []
    entries: list[tuple[int, str]] = []  # (index, decision_id)
    for idx, line in enumerate(block):
        m = _BULLET_RE.match(line)
        if m is None:
            m = _HEADING_RE.match(line)
        if m is None:
            continue
        entries.append((idx, m.group(1)))

    if not entries:
        # Decisions section exists but no recognisable entries.
        return [
            CheckResult(
                "decisions_section_empty",
                "BLOCKER",
                "## Decisions section contains no D-NNN-NN entries "
                "(neither bullet-form nor heading-form)",
            )
        ]

    for idx, decision_id in entries:
        if expected_prefix and not decision_id.startswith(expected_prefix):
            results.append(
                CheckResult(
                    "decision_id_prefix_mismatch",
                    "BLOCKER",
                    (
                        f"decision id {decision_id!r} does not match expected "
                        f"prefix {expected_prefix!r} from frontmatter spec={spec_id!r}"
                    ),
                )
            )
        if not _find_rationale(block, idx):
            results.append(
                CheckResult(
                    "decision_missing_rationale",
                    "BLOCKER",
                    (
                        f"decision {decision_id!r} has no *Rationale*: or "
                        "**Rationale**: line within "
                        f"{_RATIONALE_WINDOW} lines of its declaration"
                    ),
                )
            )

    return results
