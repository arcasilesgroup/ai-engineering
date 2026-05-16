"""References check — prefix convention + pr-shape validation.

spec-schema.md §"Reference Prefix Convention": each ``## References``
entry uses ``- <prefix>: <target>`` where ``<prefix>`` is one of
``pr`` / ``work-item`` / ``doc`` / ``research``. The ``pr:`` target
must match ``<owner>/<repo>#<number>`` or be a full URL. Bare NotebookLM
UUIDs under ``research:`` emit ``ADVISORY`` (not ``BLOCKER``) so
operator-supplied artefact references do not block the gate.
"""

from __future__ import annotations

import re
from pathlib import Path

from spec_lint.checks.decisions import _slice_section
from spec_lint.checks.frontmatter import CheckResult

RECOGNIZED_PREFIXES = frozenset({"pr", "work-item", "doc", "research"})

# PR shape: ``<owner>/<repo>#<number>`` or any ``http(s)://`` URL.
_PR_SHAPE_RE = re.compile(r"^(?:[\w.-]+/[\w.-]+#\d+|https?://\S+)$")

# Reference-list line: ``- <prefix>: <target>``. Trailing content
# after the target (e.g. inline commentary) is captured verbatim so
# the validator inspects only the target token.
_REF_RE = re.compile(r"^- ([A-Za-z][A-Za-z0-9-]*): (.+)$")

# Acceptable research target shape: a repo-relative path under
# ``.ai-engineering/runtime/research/`` ending in ``.md`` (D-136-08:
# cache target relocated to gitignored runtime path). Anything else
# under the ``research:`` prefix (e.g. NotebookLM UUIDs) emits ADVISORY.
_RESEARCH_MD_RE = re.compile(r"^\.ai-engineering/runtime/research/.+\.md$")


def check_references(spec_path: Path) -> list[CheckResult]:
    """Validate every entry in the optional ``## References`` section.

    Emits:

    * ``BLOCKER references_unknown_prefix`` for any prefix outside
      :data:`RECOGNIZED_PREFIXES`.
    * ``BLOCKER references_pr_shape`` when a ``pr:`` target does not
      match the ``<owner>/<repo>#<number>`` or URL shape.
    * ``ADVISORY references_research_shape`` when a ``research:`` target
      is neither a ``.ai-engineering/runtime/research/*.md`` path nor a URL.
    """
    text = spec_path.read_text(encoding="utf-8")
    block = _slice_section(text, "References")
    if not block:
        # ``## References`` is optional — absence is fine.
        return []

    results: list[CheckResult] = []
    for line in block:
        match = _REF_RE.match(line)
        if match is None:
            continue
        prefix, target = match.group(1), match.group(2).strip()
        if prefix not in RECOGNIZED_PREFIXES:
            results.append(
                CheckResult(
                    "references_unknown_prefix",
                    "BLOCKER",
                    (f"reference prefix {prefix!r} not in {sorted(RECOGNIZED_PREFIXES)}"),
                )
            )
            continue
        if prefix == "pr" and not _PR_SHAPE_RE.match(target):
            results.append(
                CheckResult(
                    "references_pr_shape",
                    "BLOCKER",
                    (
                        f"pr reference target {target!r} does not match "
                        "<owner>/<repo>#<n> or URL shape"
                    ),
                )
            )
            continue
        if prefix == "research":
            if _RESEARCH_MD_RE.match(target):
                continue
            if target.startswith(("http://", "https://")):
                continue
            results.append(
                CheckResult(
                    "references_research_shape",
                    "ADVISORY",
                    (
                        f"research reference target {target!r} is neither "
                        "a .ai-engineering/runtime/research/*.md path nor a URL"
                    ),
                )
            )

    return results
