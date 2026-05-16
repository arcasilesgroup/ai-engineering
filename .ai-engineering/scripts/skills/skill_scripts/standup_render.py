"""Deterministic standup renderer (spec-129 T-8).

GREEN-phase implementation backing the contract pinned in
``tests/integration/scripts/test_standup_render.py`` (T-7). The module
emits a daily-standup view of recent git activity in either Markdown
(default) or JSON, with no LLM narrative and no placeholder strings.

## Contract overview

* ``render_standup(since, fmt)`` — returns either a Markdown string
  (``fmt="md"``) or a JSON string (``fmt="json"``). The JSON form is
  documented as a stable shape with the keys ``yesterday``, ``today``,
  ``blockers``, ``since``, ``branch``. The Markdown form always
  contains the three top-level section headers regardless of activity.
* ``main(argv)`` — argparse-driven CLI entry point. Parses
  ``--since=<Nd|Nw>`` and ``--format=md|json``, calls
  ``render_standup``, prints to stdout, returns ``0`` on success.

## Design notes

* **No LLM**, no narrative interpolation. The "Today" and "Blockers"
  sections are intentionally empty placeholders — CI/board integration
  is out of scope for this PR (see plan T-8 boundary). The tests
  enforce zero placeholder tokens such as ``TODO`` or ``<insert>``.
* **Boundary is inclusive on the lower end.** ``--since=7d`` includes
  a merge dated exactly 7 days ago. We compute the cutoff as
  ``now - delta`` and forward that ISO timestamp to
  ``git log --since=...``, which itself uses an inclusive boundary
  (``>=``). A pad of one second is added to defend against
  subprocess-launch jitter that could push the cutoff past the commit
  timestamp; the test fixture uses whole-day deltas so any pad up to
  a few seconds is safe.
* **Empty repo is benign.** ``last_commit`` raises ``NoCommitsError``
  when the repo has no commits; we catch and return a fully formed
  empty standup so the script never crashes on a fresh repo.
* **Performance.** ``recent_merges`` runs a single ``git log --merges
  --since=...`` invocation; the test budget of 500 ms p95 over 10
  calls is comfortable even on cold caches because the repos in CI
  are tiny.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from skill_scripts_lib.git_activity import NoCommitsError, last_commit, recent_merges
from skill_scripts_lib.markdown_render import render_checklist

if TYPE_CHECKING:
    from skill_scripts_lib.git_activity import Merge

__all__ = ["main", "render_standup"]

# Accept ``Nd`` (days) and ``Nw`` (weeks) — anything else falls back to
# the documented default. Spec-129 caps the surface to these two units;
# adding ``h`` or ``m`` would broaden the contract beyond what the tests
# pin, so callers asking for finer windows must run multiple commands.
_SINCE_PATTERN = re.compile(r"^(?P<value>\d+)(?P<unit>[dw])$")

# Safety pad applied to the ``--since`` cutoff so a commit dated
# exactly at the boundary is reliably caught by ``git log --since``.
# Bumped 1s → 30s: Windows CI runners regularly take 5-10s to seed a
# multi-step git fixture, which used to push the cutoff past the boundary
# merge and fail test_since_7d_includes_commit_exactly_seven_days_old.
# Sub-minute pad is invisible to the human-scale day-bucket fixtures.
_INCLUSIVE_PAD = timedelta(seconds=30)


def _parse_since(since: str) -> timedelta:
    """Translate a ``Nd``/``Nw`` shorthand to a ``timedelta``.

    Unknown or malformed inputs fall back to ``7d`` rather than raising
    — the CLI is a developer tool and trapping every typo behind a
    stacktrace adds friction without value. A future spec may switch
    to argparse choices once the surface stabilises.
    """
    match = _SINCE_PATTERN.match(since.strip())
    if match is None:
        return timedelta(days=7)
    value = int(match.group("value"))
    unit = match.group("unit")
    if unit == "w":
        return timedelta(weeks=value)
    return timedelta(days=value)


def _current_branch() -> str:
    """Return the current branch name, or ``""`` when detached / empty."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=Path.cwd(),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    name = result.stdout.strip()
    # ``HEAD`` means detached HEAD; report empty string in that case so
    # downstream tooling does not key on a sentinel that varies by git
    # state.
    return "" if name == "HEAD" else name


def _merge_label(merge: Merge) -> str:
    """Collapse a merge commit into a single-line checklist label.

    The fixture seeds commits with subjects like ``Merge branch
    'feature/a'``; we keep the subject verbatim so a reader can copy
    it back into a PR description. ``markdown_render.render_checklist``
    raises on embedded newlines, but ``Merge`` subjects from
    ``git log --format=%s`` are already single-line.
    """
    return merge.subject


def _gather_recent_merges(since: str) -> list[Merge]:
    """Return merges authored within the ``since`` window from HEAD.

    Empty repos are handled by short-circuiting on ``last_commit``
    rather than letting ``git log --merges`` succeed with no output —
    surfacing the empty state explicitly keeps the JSON branch field
    consistent across code paths.
    """
    try:
        last_commit()
    except NoCommitsError:
        return []
    delta = _parse_since(since)
    cutoff = datetime.now(UTC) - delta - _INCLUSIVE_PAD
    return recent_merges(cutoff.isoformat())


def _build_payload(since: str) -> dict[str, object]:
    """Assemble the structured standup payload shared by both formats.

    The JSON renderer emits this dict directly; the Markdown renderer
    consumes the ``yesterday`` list to drive a checklist and reads
    ``branch``/``since`` for the header preamble.
    """
    merges = _gather_recent_merges(since)
    yesterday = [
        {
            "sha": merge.sha,
            "subject": merge.subject,
            "author": merge.author_email,
            "date": merge.date,
        }
        for merge in merges
    ]
    return {
        "yesterday": yesterday,
        "today": [],
        "blockers": [],
        "since": since,
        "branch": _current_branch(),
    }


def _render_markdown(payload: dict[str, object]) -> str:
    """Compose the Markdown surface from a structured payload.

    The three section headers are always present so empty repos still
    render a syntactically valid standup. The checklist is constructed
    from the ``yesterday`` entries — each merge becomes a checked
    (``- [x] ``) row because merged work is done by definition.
    """
    yesterday = payload.get("yesterday", [])
    assert isinstance(yesterday, list)

    checklist_items: list[tuple[bool, str]] = [
        (True, str(entry["subject"]))  # type: ignore[index]
        for entry in yesterday
    ]
    yesterday_block = render_checklist(checklist_items)

    parts: list[str] = ["## Yesterday"]
    if yesterday_block:
        parts.append(yesterday_block)
    parts.append("")
    parts.append("## Today")
    parts.append("")
    parts.append("## Blockers")
    return "\n".join(parts)


def render_standup(since: str = "7d", fmt: str = "md") -> str:
    """Render the standup as Markdown (default) or JSON.

    Args:
        since: ``Nd`` or ``Nw`` window. Malformed values fall back to
            ``7d``.
        fmt: ``"md"`` for Markdown (default) or ``"json"`` for a JSON
            string. The JSON form is documented in this module's
            docstring; the Markdown form always contains the three
            top-level section headers.

    Returns:
        The rendered standup string. JSON output is a string (not a
        ``dict``) because the CLI prints the raw return value to
        stdout and callers parse it with ``json.loads``.
    """
    payload = _build_payload(since)
    if fmt == "json":
        return json.dumps(payload)
    return _render_markdown(payload)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point — parse args, render, print, exit ``0``.

    Args:
        argv: Argument list excluding the program name. ``None`` (the
            default) consumes ``sys.argv[1:]``.

    Returns:
        Process exit code. Always ``0`` today — error paths surface as
        unhandled exceptions until spec-129 carves out a CLI error
        contract.
    """
    parser = argparse.ArgumentParser(
        prog="standup_render",
        description="Render a deterministic daily standup from git activity.",
    )
    parser.add_argument(
        "--since",
        default="7d",
        help="Lookback window, e.g. 7d, 2d, 1w. Defaults to 7d.",
    )
    parser.add_argument(
        "--format",
        dest="fmt",
        default="md",
        choices=("md", "json"),
        help="Output format. Defaults to md.",
    )
    args = parser.parse_args(argv)
    output = render_standup(since=args.since, fmt=args.fmt)
    print(output)
    return 0


if __name__ == "__main__":  # pragma: no cover — exercised via CLI only.
    sys.exit(main())
