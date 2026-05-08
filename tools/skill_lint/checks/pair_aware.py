"""Pair-aware checker — enforces brief §22.5 SKILL+agent split contract.

For every SKILL.md that has a paired agent .md (same slug), assert:

1. **No phase-narrative duplication** (MAJOR) — ≥3 consecutive matching
   ``^##`` or ``^###`` headings appearing in both bodies indicates the
   procedure narrative was duplicated. Skill owns the procedure
   summary; agent owns the identity.
2. **Dispatch threshold present** (MAJOR) — skill body must contain a
   numeric threshold rule (regex catches ``> 50``, ``≥ 5``, ``< 40%``,
   etc.) inside a ``## When to Use`` or ``## Dispatch`` section.
3. **Agent links back to skill** (MINOR) — agent body must mention
   ``skills/<slug>/SKILL.md`` so the navigation is bidirectional.
4. **Length caps from §22.3** (MAJOR / MINOR over by ≤ 10 %) — the five
   pair-targeted skills have explicit caps. Other paired skills get an
   informational line-count surfacing only.

Pure-stdlib (re + pathlib). Returns ``RubricResult`` records that
pipe into the existing ``skill_lint --check`` rendering pipeline.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

_VALID_SEVERITIES = {"OK", "INFO", "MINOR", "MAJOR", "CRITICAL"}

# Length caps per brief §22.3. (skill_cap, agent_cap).
LENGTH_CAPS: dict[str, tuple[int, int]] = {
    "ai-autopilot": (120, 60),
    "ai-verify": (120, 50),
    "ai-review": (120, 50),
    "ai-plan": (100, 50),
    "ai-guide": (80, 50),
}

# Tolerance: ≤ 10% over cap is MINOR, > 10% over cap is MAJOR.
LENGTH_TOLERANCE = 0.10

_HEADING_RE = re.compile(r"^(#{2,3}) +(.+?)\s*$", re.MULTILINE)
# Numeric threshold: catches ``> 50``, ``≥ 5``, ``< 40%``, ``<= 3``, etc.
# No ``\b`` because ``>`` / ``≥`` are not word characters in re's default
# unicode word-boundary mapping; an explicit anchor is unnecessary because
# the operator + digits sequence is already specific enough.
_THRESHOLD_RE = re.compile(r"(?:>=?|<=?|≥|≤)\s*\d+")
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


@dataclass(frozen=True)
class RubricResult:
    """Outcome of running a pair-aware check against one pair."""

    rule_name: str
    severity: str
    reason: str

    def __post_init__(self) -> None:
        if self.severity not in _VALID_SEVERITIES:
            raise ValueError(f"severity {self.severity!r} not in {sorted(_VALID_SEVERITIES)}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_body(md_path: Path) -> str:
    """Return body (post-frontmatter) of a markdown file. Empty on missing."""
    if not md_path.is_file():
        return ""
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = _FRONTMATTER_RE.search(text)
    if match:
        return text[match.end() :]
    return text


def _line_count(md_path: Path) -> int:
    if not md_path.is_file():
        return 0
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError:
        return 0
    # Match ``wc -l`` semantics (count newlines).
    return text.count("\n")


def _extract_headings(body: str) -> list[str]:
    """Return a list of normalised headings (level + text)."""
    out: list[str] = []
    for hashes, text in _HEADING_RE.findall(body):
        level = len(hashes)
        out.append(f"{level}|{text.strip().lower()}")
    return out


def _consecutive_overlap(a: list[str], b: list[str], min_run: int = 3) -> list[str]:
    """Return the longest run of headings appearing IN ORDER in both sequences.

    Brief contract: ≥3 consecutive matches → fail. We use a simple
    sliding-window scan: for each window of size ``min_run`` in ``a``,
    check whether the same sequence (in order) appears anywhere in
    ``b``. Returns the first matched run, or empty list.
    """
    if len(a) < min_run or len(b) < min_run:
        return []
    for i in range(len(a) - min_run + 1):
        window = a[i : i + min_run]
        # Walk b looking for window as a contiguous slice.
        for j in range(len(b) - min_run + 1):
            if b[j : j + min_run] == window:
                return window
    return []


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_no_phase_duplication(skill_body: str, agent_body: str) -> RubricResult:
    skill_h = _extract_headings(skill_body)
    agent_h = _extract_headings(agent_body)
    overlap = _consecutive_overlap(skill_h, agent_h)
    if overlap:
        return RubricResult(
            "pair_no_phase_duplication",
            "MAJOR",
            f"≥3 consecutive headings duplicated across skill+agent: {overlap}",
        )
    return RubricResult(
        "pair_no_phase_duplication",
        "OK",
        "no phase-narrative duplication detected",
    )


def check_dispatch_threshold(skill_body: str) -> RubricResult:
    if _THRESHOLD_RE.search(skill_body):
        return RubricResult(
            "pair_dispatch_threshold",
            "OK",
            "numeric dispatch threshold present in skill body",
        )
    return RubricResult(
        "pair_dispatch_threshold",
        "MAJOR",
        "skill body missing numeric dispatch threshold (e.g., '> 50 files')",
    )


def check_agent_links_back(agent_body: str, skill_slug: str) -> RubricResult:
    needle = f"skills/{skill_slug}/SKILL.md"
    if needle in agent_body:
        return RubricResult(
            "pair_agent_links_back",
            "OK",
            f"agent links back to {needle}",
        )
    return RubricResult(
        "pair_agent_links_back",
        "MINOR",
        f"agent missing link to {needle}",
    )


def check_length_caps(slug: str, skill_lines: int, agent_lines: int) -> RubricResult:
    caps = LENGTH_CAPS.get(slug)
    if caps is None:
        return RubricResult(
            "pair_length_caps",
            "INFO",
            f"no §22.3 cap for {slug} — skill={skill_lines} agent={agent_lines}",
        )
    skill_cap, agent_cap = caps
    skill_over = skill_lines - skill_cap
    agent_over = agent_lines - agent_cap

    severities: list[str] = []
    reasons: list[str] = []

    if skill_over > 0:
        ratio = skill_over / max(skill_cap, 1)
        sev = "MAJOR" if ratio > LENGTH_TOLERANCE else "MINOR"
        severities.append(sev)
        reasons.append(f"skill={skill_lines} (cap {skill_cap}, over by {skill_over})")
    if agent_over > 0:
        ratio = agent_over / max(agent_cap, 1)
        sev = "MAJOR" if ratio > LENGTH_TOLERANCE else "MINOR"
        severities.append(sev)
        reasons.append(f"agent={agent_lines} (cap {agent_cap}, over by {agent_over})")

    if not severities:
        return RubricResult(
            "pair_length_caps",
            "OK",
            f"within §22.3 caps (skill={skill_lines}/{skill_cap}, agent={agent_lines}/{agent_cap})",
        )
    final_severity = "MAJOR" if "MAJOR" in severities else "MINOR"
    return RubricResult(
        "pair_length_caps",
        final_severity,
        "; ".join(reasons),
    )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def _iter_pairs(skills_root: Path, agents_root: Path) -> Iterable[tuple[str, Path, Path]]:
    """Yield ``(slug, skill_md, agent_md)`` for every paired surface."""
    if not skills_root.is_dir() or not agents_root.is_dir():
        return ()
    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        agent_md = agents_root / f"{skill_dir.name}.md"
        if not agent_md.is_file():
            continue
        yield skill_dir.name, skill_md, agent_md


def check_pair_consistency(
    skills_root: Path,
    agents_root: Path,
) -> list[tuple[str, RubricResult]]:
    """Run every pair-aware check across paired surfaces.

    Returns ``[(slug, result), ...]`` so the caller can render results
    grouped by pair. Severity propagates per-result; the caller
    decides exit-code mapping.
    """
    results: list[tuple[str, RubricResult]] = []
    for slug, skill_md, agent_md in _iter_pairs(skills_root, agents_root):
        skill_body = _read_body(skill_md)
        agent_body = _read_body(agent_md)
        skill_lines = _line_count(skill_md)
        agent_lines = _line_count(agent_md)

        results.append((slug, check_no_phase_duplication(skill_body, agent_body)))
        results.append((slug, check_dispatch_threshold(skill_body)))
        results.append((slug, check_agent_links_back(agent_body, slug)))
        results.append((slug, check_length_caps(slug, skill_lines, agent_lines)))
    return results
