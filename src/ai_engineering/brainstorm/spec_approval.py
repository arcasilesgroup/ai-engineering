"""Spec / plan approval handler — writes decisions to ``state.db``.

Spec-138 M3.T1 + M3.T2: when ``/ai-brainstorm`` marks a spec
``status: approved`` (or ``/ai-plan`` finalises a plan that introduces
new ``D-NNN-NN`` rows), this handler parses the markdown's ``##
Decisions`` section and UPSERTs every ``D-<spec>-<NN>`` reference into
``state.db.decisions``. Idempotent on re-run.

Hexagonal split
---------------

* **Domain (this module)** — pure parser + UPSERT delegation. Accepts a
  ``Path`` to ``spec.md`` (or ``plan.md``) and the project root. No
  subprocess, no LLM, no observability emission.
* **Adapter (skill handler)** — the ``/ai-brainstorm`` and ``/ai-plan``
  skill files invoke this entry point at approval time. They are the
  callers; this module is the callee.

Title + rationale heuristic
---------------------------

The canonical spec decision line looks like::

    - **D-138-01 — Short title.** Body sentence. Rationale: long-form prose...

The parser extracts:

* ``decision_id`` from the ``D-<spec>-<NN>`` capture group.
* ``title`` from the bolded title between em-dashes (``— Title.``). Fall
  back to the trimmed line if the bolded form is missing.
* ``rationale`` from the substring after a literal ``Rationale:`` /
  ``**Rationale**:`` / ``*Rationale*:`` marker on the same line OR the
  next non-blank line. ``None`` when absent.

Anything past the first matching line per ``decision_id`` is ignored
(idempotency at parse time).
"""

from __future__ import annotations

import re
from pathlib import Path

from ai_engineering.state.state_db import upsert_decision_rows_raw

__all__ = [
    "extract_decisions",
    "handle_spec_approval",
]


# Canonical regex for governance decision IDs: ``D-<spec>-<NN>[a-z]?``.
# Mirrors the regex in ``decisions_cmd.py`` (D-NNN-NN[a-z]).
_DECISION_ID_RE = re.compile(r"\bD-(?P<spec>\d{3})-(?P<num>\d{2}[a-z]?)\b")

# Extract a bolded title that follows the em-dash on the same line. The
# spec convention is ``**D-138-01 — Short title.**`` — we capture the
# portion after the em-dash and stop at the first period or closing
# ``**``. Bounded quantifier {1,300} satisfies Sonar S5852.
_TITLE_AFTER_DASH_RE = re.compile(r"[—-]\s*(?P<title>[^*.\n]{1,300})")

# Rationale prefix variants. The captured group is the trailing text on
# the same line (may be empty when the rationale spans to the next line).
_RATIONALE_INLINE_RE = re.compile(
    r"(?:\*{1,2}Rationale\*{1,2}|Rationale)\s*[:\-]\s*(?P<text>.{1,2000})",
    re.IGNORECASE,
)


def _extract_title(line: str, decision_id: str) -> str:
    """Pull a short title out of a spec ``## Decisions`` bullet.

    The expected shape is ``- **D-138-01 — Short title.** body``.
    When the bolded title is absent we fall back to the first 200 chars
    of the trimmed line as the title (matches ``decisions_cmd._scan_decisions``).
    """
    # Trim out the decision_id prefix so the em-dash regex anchors cleanly.
    cursor = line.find(decision_id)
    if cursor == -1:
        return line.strip()[:200]
    tail = line[cursor + len(decision_id) :]
    match = _TITLE_AFTER_DASH_RE.search(tail)
    if match is None:
        return line.strip()[:200]
    return match.group("title").strip()[:200]


def _join_continuation_lines(line: str, next_lines: list[str]) -> str:
    """Join continuation lines indented under a markdown list bullet.

    Markdown source frequently wraps long bullet entries at 80 chars; the
    continuation lines start with whitespace and belong to the same
    logical entry. We keep merging until we hit a blank line, the next
    top-level bullet (``- ``), or a heading. The result is one logical
    line suitable for regex extraction.
    """
    parts: list[str] = [line.rstrip()]
    for follow_up in next_lines:
        if not follow_up:
            break  # blank line ends the bullet
        if follow_up.startswith(("-", "#", "|")) and not follow_up.startswith(("- ", "-\t")):
            break
        if follow_up.startswith("- "):
            break  # next top-level bullet
        if not follow_up.startswith((" ", "\t")):
            break  # next paragraph; stop
        parts.append(follow_up.strip())
    return " ".join(parts)


def _extract_rationale(line: str, next_lines: list[str]) -> str | None:
    """Find the rationale string for a decision line.

    Order of resolution:

    1. ``Rationale: ...`` substring on the same line (including wrapped
       continuation lines indented under the bullet).
    2. The next non-blank line starting with ``*Rationale*:`` /
       ``**Rationale**:`` / ``Rationale:``.
    3. ``None`` when no marker is found within the first 5 follow-up
       lines.
    """
    # Join wrapped continuation lines so a Rationale: that spans two
    # source lines is detected verbatim.
    joined = _join_continuation_lines(line, next_lines)
    match = _RATIONALE_INLINE_RE.search(joined)
    if match is not None:
        return match.group("text").strip()[:2000] or None

    lookahead = 0
    for follow_up in next_lines:
        lookahead += 1
        if lookahead > 5:
            break
        stripped = follow_up.strip()
        if not stripped:
            continue
        match = _RATIONALE_INLINE_RE.match(stripped)
        if match is not None:
            return match.group("text").strip()[:2000] or None
    return None


def extract_decisions(
    spec_path: Path,
    *,
    default_spec_id: str | None = None,
) -> list[dict[str, str | None]]:
    """Parse ``spec.md`` / ``plan.md`` and return decision rows.

    The function reads only the ``## Decisions`` section -- any
    ``D-NNN-NN`` references outside that block are ignored. Each
    ``decision_id`` produces a single row (first hit wins).

    Args:
        spec_path: Path to a markdown file (typically
            ``.ai-engineering/specs/spec.md`` or ``plan.md``).
        default_spec_id: Spec id to use when the parsed ``D-NNN`` does
            not match the spec front-matter. Optional convenience for
            tests; in production we always derive ``spec_id`` from the
            decision marker itself (``D-138-01`` -> ``spec-138``).

    Returns:
        List of row dicts ready for :func:`upsert_decision_rows_raw`.
    """
    if not spec_path.is_file():
        return []
    try:
        content = spec_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines = content.splitlines()
    # Locate the ``## Decisions`` heading and bound the scan to the next
    # ``## `` heading so we never pull D-IDs out of unrelated sections.
    start = None
    for index, raw in enumerate(lines):
        if raw.strip().lower().startswith("## decisions"):
            start = index + 1
            break
    if start is None:
        return []

    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    section = lines[start:end]

    found: dict[str, dict[str, str | None]] = {}
    for offset, raw_line in enumerate(section):
        for match in _DECISION_ID_RE.finditer(raw_line):
            decision_id = f"D-{match.group('spec')}-{match.group('num')}"
            if decision_id in found:
                continue
            title = _extract_title(raw_line, decision_id)
            rationale = _extract_rationale(raw_line, section[offset + 1 :])
            spec_id = default_spec_id or f"spec-{match.group('spec')}"
            found[decision_id] = {
                "decision_id": decision_id,
                "spec_id": spec_id,
                "status": "active",
                "title": title,
                "rationale": rationale,
                "context": f"{spec_path.name}:{start + offset + 1}",
                "consequences": None,
                "superseded_by": None,
            }
    return list(found.values())


def handle_spec_approval(
    project_root: Path,
    spec_path: Path,
    *,
    default_spec_id: str | None = None,
) -> int:
    """UPSERT every decision found in ``spec_path`` into ``state.db.decisions``.

    Spec-138 M3.T1 + M3.T2 entry point. Idempotent on duplicate
    ``decision_id`` values (the canonical UPSERT clause keeps the latest
    payload). Returns the number of rows attempted so callers can log a
    summary line in the skill handler.

    Args:
        project_root: Repository root holding ``.ai-engineering/``.
        spec_path: Path to ``spec.md`` or ``plan.md``.
        default_spec_id: Override the parsed spec id (test hook).

    Returns:
        Count of rows upserted (0 when the file is missing or carries
        no decisions).
    """
    rows = extract_decisions(spec_path, default_spec_id=default_spec_id)
    if not rows:
        return 0
    return upsert_decision_rows_raw(project_root, rows)
