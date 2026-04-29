"""RED-phase tests for spec-110 Phase 1 — entry-point overlay consistency.

Spec acceptance criteria (governance v3 harvest, Phase 1):
    1. The IDE-specific entry-point overlays (``CLAUDE.md``, ``GEMINI.md``,
       ``.github/copilot-instructions.md``) must each reference the
       canonical multi-IDE rulebook ``AGENTS.md`` via a relative markdown
       link so every assistant funnels through the same source of truth.
       Verified by :func:`test_overlays_reference_agents_md`.
    2. The same overlays must NOT restate numbered hard rules from
       ``CONSTITUTION.md`` verbatim. Hard rules live ONCE in the
       Constitution; overlays delegate to it via ``AGENTS.md``.
       Verified by :func:`test_overlays_no_hard_rules_duplication`.

Status: RED. Tasks T-1.9..T-1.11 add the AGENTS.md references and slim
the overlays after ``AGENTS.md`` is refactored in T-1.8. Both tests
deliberately fail now to drive the GREEN phase.
"""

from __future__ import annotations

import re
from pathlib import Path

# Repo root: tests/integration/<this file> → up 3 levels.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Overlays whose entry points must funnel into AGENTS.md.
OVERLAY_PATHS: tuple[Path, ...] = (
    REPO_ROOT / "CLAUDE.md",
    REPO_ROOT / "GEMINI.md",
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


def test_overlays_reference_agents_md() -> None:
    """Each IDE overlay contains a relative markdown link to ``AGENTS.md``.

    Asserts:
    1. Every overlay file in ``OVERLAY_PATHS`` exists at its expected path.
    2. Each overlay file contains at least one markdown link whose link
       text mentions ``AGENTS.md`` and whose target is the relative path
       ``AGENTS.md`` (optionally prefixed with ``./`` or ``../``).
    """
    missing_files: list[str] = []
    overlays_without_link: list[str] = []

    for overlay_path in OVERLAY_PATHS:
        if not overlay_path.is_file():
            missing_files.append(str(overlay_path.relative_to(REPO_ROOT)))
            continue

        content = overlay_path.read_text(encoding="utf-8")
        if not AGENTS_MD_LINK_RE.search(content):
            overlays_without_link.append(str(overlay_path.relative_to(REPO_ROOT)))

    assert not missing_files, (
        "Expected IDE overlay entry points are missing from the repo: "
        f"{missing_files}. Overlays must exist at the canonical paths so "
        "they can funnel into AGENTS.md per spec-110 Phase 1."
    )

    assert not overlays_without_link, (
        "Each IDE overlay must contain a relative markdown link to "
        "AGENTS.md (e.g. '[AGENTS.md](AGENTS.md)' or "
        "'[AGENTS.md](../AGENTS.md)'). Overlays missing the link: "
        f"{overlays_without_link}. Refactor them per spec-110 tasks "
        "T-1.9..T-1.11 to delegate canonical rules to AGENTS.md."
    )


def test_overlays_no_hard_rules_duplication() -> None:
    """No IDE overlay restates a CONSTITUTION numbered rule verbatim.

    Spec acceptance criterion (governance v3 harvest, Phase 1):
        Hard rules live ONCE -- in ``CONSTITUTION.md``. The IDE overlays
        (``CLAUDE.md``, ``GEMINI.md``, ``.github/copilot-instructions.md``)
        must delegate to the canonical document via ``AGENTS.md`` rather
        than copy-pasting numbered rules. Restating a rule verbatim creates
        drift risk: the overlay can fall out of sync with CONSTITUTION
        when the latter is amended. Tasks T-1.9..T-1.11 slim each overlay
        so the duplication is removed.

    Algorithm:
        1. Parse ``CONSTITUTION.md`` and capture every numbered-rule line
           inside an Article body. For each rule capture both:
             a. its first :data:`RULE_SNIPPET_LEN` characters of body text
                (the prose snippet), and
             b. every distinctive backtick-quoted code span inside the rule
                (length >= :data:`CODE_SPAN_MIN_LEN`).
        2. For every overlay in :data:`OVERLAY_PATHS`, perform a
           case-sensitive verbatim substring search for each prose snippet.
           Then check whether the overlay restates a rule's code spans
           (the technical-identifier signal): if it embeds the same
           backtick-quoted span as the rule, that counts as duplication.
        3. Fail the test with the full list of violations so authors can
           remediate every duplication in a single pass.

    The two-channel match (prose + technical identifier) catches both
    direct copy-paste and the more common paraphrased duplication where an
    overlay restates ``--no-verify`` / ``# noqa`` / ``# nosec`` while
    rewording the surrounding sentence. Tasks T-1.9..T-1.11 strip those
    sections and replace them with a delegation to ``AGENTS.md`` /
    ``CONSTITUTION.md``.
    """
    assert CONSTITUTION_PATH.is_file(), (
        f"Expected CONSTITUTION.md at {CONSTITUTION_PATH.relative_to(REPO_ROOT)} "
        "but it is missing. Run task T-1.4 (governance baseline harvest)."
    )

    constitution_text = CONSTITUTION_PATH.read_text(encoding="utf-8")
    rule_snippets = _extract_constitution_rule_snippets(constitution_text)

    assert rule_snippets, (
        "Failed to extract any numbered rules from CONSTITUTION.md. "
        "Ensure articles use the '## Article <Roman> — <Title>' header "
        "and that rules are formatted as '<digit>. <text>' lines."
    )

    violations: list[str] = []

    for overlay_path in OVERLAY_PATHS:
        if not overlay_path.is_file():
            # Missing files are reported by ``test_overlays_reference_agents_md``;
            # skip them here to keep this test focused on duplication.
            continue
        overlay_rel = str(overlay_path.relative_to(REPO_ROOT))
        overlay_text = overlay_path.read_text(encoding="utf-8")
        for article_label, snippet, code_spans in rule_snippets:
            # Prose channel: first ~40 chars of the rule appear verbatim.
            if snippet in overlay_text:
                violations.append(
                    f"{overlay_rel}: duplicates rule from {article_label!r} "
                    f"prose (first {len(snippet)} chars: {snippet!r})"
                )
            # Technical-identifier channel: a distinctive backtick-quoted
            # code span from the rule is restated in the overlay (also as a
            # backtick-quoted span). We require the same backtick wrapping
            # so that incidental mentions of common words inside a longer
            # phrase do not trigger -- only deliberate code references do.
            for span in code_spans:
                if f"`{span}`" in overlay_text:
                    violations.append(
                        f"{overlay_rel}: restates code identifier "
                        f"`{span}` from rule in {article_label!r}"
                    )

    assert not violations, (
        "IDE overlays must not restate CONSTITUTION numbered rules "
        "verbatim. Each overlay should delegate to AGENTS.md / "
        "CONSTITUTION.md instead of copy-pasting hard rules or their "
        f"distinctive technical identifiers. Found {len(violations)} "
        "duplication(s):\n  - "
        + "\n  - ".join(violations)
        + "\nRemove the duplicated text per spec-110 tasks "
        "T-1.9..T-1.11."
    )
