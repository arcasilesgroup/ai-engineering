"""structure checker — spec-187 W1 (T-4/T-5) structure/procedure lint.

Encodes the Anthropic authoring contract's structural levers as an
advisory lint (spec-187 D-187-06, research §Determinism):

* **Workflow procedure-ratio** — checklist / numbered / tabular steps
  outperform free prose (7.50/8 vs 5.67, arXiv 2605.20149) at fewer
  tokens. The ``## Workflow`` section is scored: if the share of
  procedure lines (``1.``/``- ``/``- [ ]``/table rows) among its
  content lines falls below the threshold, the section is flagged as
  prose-heavy.
* **Body under 500 lines** — the instruction-complexity cliff sits at
  ~500 rules; bodies over 500 lines are flagged (split into
  ``references/``).
* **References one level deep** — a relative ``.md`` reference whose
  path is more than one level deep breaks progressive disclosure.

Posture: WARN-ONLY in W1 (advisory; never drives the CLI exit code);
flips to blocking in W5 (D-187-07). All reason strings are pure ASCII so
raw / non-tty writes stay cp1252-safe (D-187-10). Pure stdlib.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

_VALID_SEVERITIES = {"OK", "INFO", "MINOR", "MAJOR", "CRITICAL"}

# Body-length cap (Anthropic: bodies < 500 lines).
_BODY_MAX_LINES = 500
# Minimum share of Workflow content lines that must be procedural.
_MIN_PROCEDURE_RATIO = 0.5
# A Workflow with fewer content lines than this is too small to score.
_MIN_WORKFLOW_LINES = 3


@dataclass(frozen=True)
class RubricResult:
    """Outcome of a single structure sub-check against a file."""

    rule_name: str
    severity: str
    reason: str

    def __post_init__(self) -> None:
        if self.severity not in _VALID_SEVERITIES:
            raise ValueError(f"severity {self.severity!r} not in {sorted(_VALID_SEVERITIES)}")


_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
_WORKFLOW_RE = re.compile(
    r"^[ \t]*##\s+Workflow\b[^\n]*\n(?P<body>.*?)(?=^[ \t]*##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
# Procedural line shapes: numbered step, bullet, checklist, or table row.
_PROCEDURE_LINE_RE = re.compile(r"^[ \t]*(\d+\.|[-*]\s|[-*]\s\[.\]|\|)")
_FENCE_RE = re.compile(r"^```")
# Relative markdown .md link (skip http(s) + anchors).
_MD_LINK_RE = re.compile(r"\]\((?!https?:)(?P<path>[^)#]+\.md)(?:#[^)]*)?\)")


def _body_after_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1)


def _procedure_ratio(section_body: str) -> tuple[float, int]:
    """Return ``(procedure_ratio, content_line_count)`` for a section.

    Content lines exclude blanks and fenced code blocks. The ratio is the
    share of content lines that match a procedural shape.
    """
    content = 0
    procedural = 0
    in_fence = False
    for raw in section_body.splitlines():
        stripped = raw.strip()
        if _FENCE_RE.match(stripped):
            in_fence = not in_fence
            continue
        if in_fence or not stripped:
            continue
        content += 1
        if _PROCEDURE_LINE_RE.match(raw):
            procedural += 1
    if content == 0:
        return (1.0, 0)
    return (procedural / content, content)


def _ref_depth(path: str) -> int:
    """Depth of a relative reference path = number of path separators.

    ``references/detail.md`` -> 1 (one level deep, OK).
    ``references/nested/deep/detail.md`` -> 3 (too deep).
    Leading ``./`` is normalised away; ``..`` segments count.
    """
    normalised = path.strip()
    if normalised.startswith("./"):
        normalised = normalised[2:]
    return normalised.count("/")


def check_file_structure(md_path: Path) -> list[RubricResult]:
    """Run all structure sub-checks against a single markdown file.

    Returns a list of ``RubricResult`` (one per triggered rule). An
    all-clear file returns a single ``OK`` result.
    """
    if not md_path.is_file():
        return [RubricResult("structure", "CRITICAL", f"file not found at {md_path}")]

    text = md_path.read_text(encoding="utf-8")
    body = _body_after_frontmatter(text)
    findings: list[RubricResult] = []

    # Body length.
    line_count = len(body.splitlines())
    if line_count > _BODY_MAX_LINES:
        findings.append(
            RubricResult(
                "structure_body_length",
                "MINOR",
                f"body is {line_count} lines (over 500 - split into references/)",
            )
        )

    # Workflow procedure-ratio.
    match = _WORKFLOW_RE.search(text)
    if match:
        ratio, content_lines = _procedure_ratio(match.group("body") or "")
        if content_lines >= _MIN_WORKFLOW_LINES and ratio < _MIN_PROCEDURE_RATIO:
            findings.append(
                RubricResult(
                    "structure_workflow_procedure",
                    "MINOR",
                    (
                        f"## Workflow is prose-heavy (procedure ratio "
                        f"{ratio:.2f} < {_MIN_PROCEDURE_RATIO:.2f}) - "
                        f"convert to numbered/checklist/table"
                    ),
                )
            )

    # Reference depth.
    deep_refs = sorted(
        {m.group("path") for m in _MD_LINK_RE.finditer(body) if _ref_depth(m.group("path")) > 1}
    )
    if deep_refs:
        findings.append(
            RubricResult(
                "structure_ref_depth",
                "MINOR",
                "references deeper than one level: " + ", ".join(deep_refs),
            )
        )

    if not findings:
        findings.append(RubricResult("structure", "OK", "structure within contract"))
    return findings


def check_structure(
    skills_root: Path,
    agents_root: Path,
) -> list[tuple[Path, RubricResult]]:
    """Walk canonical skills + agents and run the structure lint.

    Returns ``[(path, RubricResult), ...]`` sorted by path. Warn-only in
    W1 (D-187-07).
    """
    results: list[tuple[Path, RubricResult]] = []

    if skills_root.is_dir():
        for skill_dir in sorted(skills_root.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                continue
            for result in check_file_structure(skill_md):
                results.append((skill_md, result))

    if agents_root.is_dir():
        for agent_md in sorted(agents_root.glob("*.md")):
            for result in check_file_structure(agent_md):
                results.append((agent_md, result))

    return results


def write_findings(results: list[tuple[Path, RubricResult]], stream: TextIO) -> None:
    """Write pure-ASCII, one-line-per-finding output (D-187-10)."""
    for path, result in results:
        if result.severity == "OK":
            continue
        stream.write(f"{result.severity} structure {path}: {result.reason}\n")
