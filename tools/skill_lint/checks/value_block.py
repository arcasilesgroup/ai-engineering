"""value_block checker — spec-186 Client-Value Lens adoption rule.

The five canonical chain skills (``/ai-brainstorm``, ``/ai-plan``,
``/ai-build``, ``/ai-autopilot``, ``/ai-pr``) must adopt the Client-Value
Lens by citing ``reference/value-lens.md`` at their user-facing report and
question steps (see ``.ai-engineering/reference/value-lens.md`` adoption
contract, D-186-01 through D-186-10).

Adoption marker: a chain skill "adopts the lens" iff the literal substring
``value-lens.md`` appears in its ``SKILL.md`` OR any file under its
``handlers/``.

Posture: BLOCKING. A chain skill that omits the citation surfaces as
CRITICAL and drives the CLI exit code to 1. Non-chain skills are out of
scope — they never surface as CRITICAL from this check.
"""

from __future__ import annotations

from pathlib import Path

# Reuse the RubricResult shape from the principles checker (DRY).
from skill_lint.checks.principles import RubricResult

# ── The five canonical chain skills (spec-186 D-186-06) ──────────────────
# EXACTLY these five directory names. This is the chain-skill set, NOT the
# full ``ai-*`` surface and NOT the CLAUDE.md §11 canonical chain (which
# differs — it omits ai-autopilot and includes ai-spec-draft).
CHAIN_SKILLS: tuple[str, ...] = (
    "ai-brainstorm",
    "ai-plan",
    "ai-build",
    "ai-autopilot",
    "ai-pr",
)

# ── Adoption marker (literal substring) ──────────────────────────────────
_CITATION_MARKER = "value-lens.md"


# ───────────────────────────── single-skill check ─────────────────────────


def _cites_lens(skill_dir: Path) -> bool:
    """True if ``value-lens.md`` appears in SKILL.md or any handlers/*.md.

    The marker is a literal substring match. handlers/ is walked
    recursively so nested handler layouts still count.
    """
    skill_md = skill_dir / "SKILL.md"
    if skill_md.is_file() and _CITATION_MARKER in skill_md.read_text(encoding="utf-8"):
        return True
    handlers = skill_dir / "handlers"
    if handlers.is_dir():
        for handler in sorted(handlers.rglob("*.md")):
            if handler.is_file() and _CITATION_MARKER in handler.read_text(encoding="utf-8"):
                return True
    return False


def check_value_block_citation(skill_dir: Path) -> RubricResult:
    """Run the value-lens adoption rule against a single skill directory.

    For a directory whose name is in :data:`CHAIN_SKILLS`:

    * ``OK`` — ``value-lens.md`` is cited in SKILL.md or a handlers/*.md.
    * ``CRITICAL`` — the citation is absent (blocking; adoption contract
      violated).

    For a non-chain directory the check returns ``INFO`` (out of scope) —
    it NEVER returns CRITICAL for a skill outside the chain.
    """
    name = skill_dir.name
    if name not in CHAIN_SKILLS:
        return RubricResult(
            "value_block_citation",
            "INFO",
            f"{name} is not a chain skill — value-lens adoption not required",
        )
    if _cites_lens(skill_dir):
        return RubricResult(
            "value_block_citation",
            "OK",
            f"chain skill {name} cites value-lens.md",
        )
    return RubricResult(
        "value_block_citation",
        "CRITICAL",
        f"chain skill {name} omits the value-lens.md citation",
    )


# ───────────────────────────── driver ─────────────────────────────────────


def check_value_block_citations(skills_root: Path) -> list[tuple[Path, RubricResult]]:
    """Walk every ``<skills_root>/ai-*/`` and run the value-lens check.

    Returns ``[(skill_dir_path, result), ...]`` sorted by path so CI
    output stays stable. Raises ``FileNotFoundError`` when ``skills_root``
    does not exist (matches the ``check_principles_citations`` contract).
    """
    if not skills_root.is_dir():
        raise FileNotFoundError(f"skills root {skills_root} does not exist")
    results: list[tuple[Path, RubricResult]] = []
    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        if not skill_dir.name.startswith("ai-"):
            continue
        results.append((skill_dir, check_value_block_citation(skill_dir)))
    return results
