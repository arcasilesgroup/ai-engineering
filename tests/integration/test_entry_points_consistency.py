"""Entry-point overlay consistency — recalibrated per spec-131 D-131-04.

spec-110 originally asserted that IDE overlays (CLAUDE.md /
copilot-instructions.md) (a) referenced AGENTS.md via a relative
markdown link and (b) did NOT restate CONSTITUTION numbered rules
verbatim. Both contracts are obsolete after spec-131:

* D-131-04 made AGENTS.md / CLAUDE.md /
  copilot-instructions.md **byte-equivalent mirrors** of
  ``templates/project/CANONICAL.md``. The overlays do not LINK to
  AGENTS.md; they CARRY the same canonical payload.
* D-131-04 rescoped CONSTITUTION.md to project-identity only. The
  "numbered rules" the original test guarded against migrated to
  CANONICAL.md §13 Hard Rules and the IDE-mirrors carry them
  verbatim (which is the spec contract, not a violation).

Closure-sweep (C1) replaces the two original assertions with the
new byte-equivalent contract: each overlay must (a) carry the
shared CANONICAL.md ``## 0. Bootstrap`` heading prefix (signal that
the canonical payload was inherited) and (b) avoid the legacy
``@AGENTS.md`` import (spec-131 D-131-14 D-131-15 anti-goal #10:
"no backwards-compat shims" — no overlay imports the canonical
mirror via the legacy include directive).
"""

from __future__ import annotations

import re
from pathlib import Path

# Repo root: tests/integration/<this file> → up 3 levels.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Overlays whose entry points must funnel into AGENTS.md.
OVERLAY_PATHS: tuple[Path, ...] = (
    REPO_ROOT / "CLAUDE.md",
    REPO_ROOT / ".github" / "copilot-instructions.md",
)

# Tolerant matcher: ``[<any text containing AGENTS.md>](<optional ./ or ../>AGENTS.md)``.
# - The link text must contain the literal ``AGENTS.md`` (escaped dot).
# - The link target must be the relative path ``AGENTS.md`` with an optional
#   single ``./`` or ``../`` prefix (one level only — overlays sit in repo root
#   or one directory deep, e.g. ``.github/``).
AGENTS_MD_LINK_RE = re.compile(r"\[[^\]]*AGENTS\.md[^\]]*\]\((?:\.{1,2}/)?AGENTS\.md\)")

# Canonical Constitution lives at repo root.
CONSTITUTION_PATH: Path = REPO_ROOT / "CONSTITUTION.md"

# Article header — line of the form ``## Article <Roman> — <Title>`` marks the
# beginning of an article body. We capture rules until the next article, the
# closing ``---`` separator, or an HTML comment block.
_ARTICLE_HEADER_RE = re.compile(r"^##\s+Article\s+")
# Numbered rule line — ``^[1-9]\.\s+(.+)`` per the spec algorithm. Rules use
# single-digit numbering today (no article exceeds 9 rules); if that ever
# changes, widen the character class.
_NUMBERED_RULE_RE = re.compile(r"^([1-9])\.\s+(.+)$")
# Lines that close an article body (we stop collecting rules at these).
_ARTICLE_TERMINATORS: tuple[str, ...] = ("---", "<!--")

# Snippet length used for the prose verbatim-substring check. A 40-character
# window is long enough to make coincidental matches in unrelated prose
# vanishingly unlikely while still tolerant of short rules (which are tested
# as a whole).
RULE_SNIPPET_LEN: int = 40

# Backtick code-span extractor. Distinctive technical identifiers that appear
# inside backticks within a numbered rule (such as the ``--no-verify`` flag
# or the suppression-comment names listed in Article VII) are the typical
# signal of duplication: an overlay that paraphrases a rule almost always
# retains the identifier verbatim. We require a minimum span length to
# avoid generic matches.
_CODE_SPAN_RE = re.compile(r"`([^`]+)`")
CODE_SPAN_MIN_LEN: int = 5


def _extract_constitution_rule_snippets(
    constitution_text: str,
) -> list[tuple[str, str, frozenset[str]]]:
    """Return ``(article_label, snippet, code_spans)`` per numbered rule.

    A "numbered rule" is a line within an article body that matches
    ``^[1-9]\\.\\s+(.+)``. For each rule the function captures:

    - ``snippet`` -- the rule's first :data:`RULE_SNIPPET_LEN` characters of
      body text (or the full body if shorter). Used for the prose verbatim
      substring check that drives the test's "verbatim wording" guarantee.
    - ``code_spans`` -- the set of distinctive backtick-quoted identifiers
      (length >= :data:`CODE_SPAN_MIN_LEN`) embedded in the rule. Used for
      the technical-identifier check that catches paraphrased duplications
      where the identifier is preserved verbatim (e.g. an overlay that
      restates ``# noqa`` / ``--no-verify`` while wording the surrounding
      prohibition differently).

    Rules without any qualifying code span yield an empty ``code_spans``
    set; the prose check still applies.
    """
    snippets: list[tuple[str, str, frozenset[str]]] = []
    in_article = False
    article_label = ""
    for raw_line in constitution_text.splitlines():
        stripped = raw_line.lstrip()
        if _ARTICLE_HEADER_RE.match(stripped):
            in_article = True
            # Keep the header text (without the leading ``## `` hashes) as a
            # human-readable label for failure messages.
            article_label = stripped.lstrip("#").strip()
            continue
        if any(stripped.startswith(term) for term in _ARTICLE_TERMINATORS):
            in_article = False
            continue
        if not in_article:
            continue
        rule_match = _NUMBERED_RULE_RE.match(stripped)
        if rule_match is None:
            continue
        rule_body = rule_match.group(2).strip()
        snippet = rule_body[:RULE_SNIPPET_LEN]
        code_spans = frozenset(
            span for span in _CODE_SPAN_RE.findall(rule_body) if len(span) >= CODE_SPAN_MIN_LEN
        )
        snippets.append((article_label, snippet, code_spans))
    return snippets


def test_overlays_carry_canonical_payload() -> None:
    """Each IDE overlay carries the canonical payload (spec-131 D-131-04).

    Renamed from ``test_overlays_reference_agents_md``: the byte-equivalent
    mirror contract replaces the legacy link-to-AGENTS.md contract. Every
    overlay must present the canonical "## 0. Bootstrap" heading prefix so
    that downstream consumers (humans, IDE bootstraps) find the canonical
    payload directly inside the overlay rather than chasing a delegation
    link.

    Asserts:
    1. Every overlay file in ``OVERLAY_PATHS`` exists at its expected path.
    2. Each overlay file contains the literal ``## 0. Bootstrap`` heading
       (the canonical payload's first §0 anchor).
    """
    missing_files: list[str] = []
    overlays_without_bootstrap: list[str] = []
    bootstrap_marker = "## 0. Bootstrap"

    for overlay_path in OVERLAY_PATHS:
        if not overlay_path.is_file():
            missing_files.append(str(overlay_path.relative_to(REPO_ROOT)))
            continue
        content = overlay_path.read_text(encoding="utf-8")
        if bootstrap_marker not in content:
            overlays_without_bootstrap.append(str(overlay_path.relative_to(REPO_ROOT)))

    assert not missing_files, (
        "Expected IDE overlay entry points are missing from the repo: "
        f"{missing_files}. Overlays must exist at the canonical paths per "
        "spec-131 D-131-04 byte-equivalent mirror contract."
    )

    assert not overlays_without_bootstrap, (
        "Each IDE overlay must carry the canonical '## 0. Bootstrap' "
        "heading inherited from CANONICAL.md (spec-131 D-131-04). Overlays "
        f"missing the marker: {overlays_without_bootstrap}."
    )


def test_overlays_no_legacy_agents_md_import() -> None:
    """No IDE overlay carries the legacy ``@AGENTS.md`` include directive.

    Renamed from ``test_overlays_no_hard_rules_duplication``: under
    the spec-131 D-131-04 byte-equivalent mirror contract the overlays
    CARRY the canonical payload (which includes the §13 Hard Rules
    table) — duplication of that payload across mirrors is the
    contract, not a violation.

    The remaining anti-pattern is the legacy ``@AGENTS.md`` import
    directive (D-131-14, D-131-15 anti-goal #10 — "no backwards-compat
    shims"). Mirrors MUST NOT pull canonical content via the legacy
    include; they must carry it inline as bytes.

    Note: the spec-131 §14 "Strict Content Contracts" authoring table
    references the literal ``@AGENTS.md`` token inside its "MUST NOT
    contain" cells (the table documents the prohibition). The check
    therefore filters out mentions wrapped in backticks inside a
    markdown table row so the authoring reference does not falsely
    flag itself.
    """
    violations: list[str] = []

    # Match any occurrence of ``@AGENTS.md`` that is NOT wrapped in
    # backticks inside a markdown table cell. The forbidden form is
    # the literal include directive (``@AGENTS.md``) appearing as
    # actionable prose, not as a code-spanned reference inside the
    # authoring-contract table.
    forbidden_re = re.compile(r"(?<!`)@AGENTS\.md(?!`)")

    for overlay_path in OVERLAY_PATHS:
        if not overlay_path.is_file():
            # Missing files are reported by ``test_overlays_carry_canonical_payload``;
            # skip them here to keep this test focused.
            continue
        overlay_rel = str(overlay_path.relative_to(REPO_ROOT))
        overlay_text = overlay_path.read_text(encoding="utf-8")
        if forbidden_re.search(overlay_text):
            violations.append(
                f"{overlay_rel}: carries forbidden '@AGENTS.md' import "
                f"directive (spec-131 D-131-14 anti-goal #10)."
            )

    assert not violations, (
        "IDE overlays must not import canonical content via the legacy "
        "'@AGENTS.md' include directive. The byte-equivalent mirror "
        "contract requires the canonical payload to live inline as bytes. "
        f"Found {len(violations)} violation(s):\n  - "
        + "\n  - ".join(violations)
        + "\nInline the canonical payload via scripts/sync_mirrors per "
        "spec-131 D-131-04."
    )
