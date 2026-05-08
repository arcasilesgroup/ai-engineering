"""Conformance rubric — pure-Python predicates over domain dataclasses.

Brief §3 ten skills rules and the parallel five-rule agents rubric. All
rules are pure functions over ``Skill`` / ``Agent`` instances; no I/O,
no third-party deps. Every rule returns a :class:`RubricResult` with a
severity label that the application layer maps to a letter grade
(A/B/C/D).

Severity ladder (penalty weights):

* ``OK``       — 0 (rule satisfied)
* ``INFO``     — 0 (universal §2.1 gap surfaced for visibility, no penalty)
* ``MINOR``    — 1 (visible deviation, does not block lean-grade A)
* ``MAJOR``    — 3 (visible deviation, blocks A)
* ``CRITICAL`` — 7 (blocks B; aggregator pushes toward C/D)

Total severity weight per skill maps to grade:

* score ≤ 2 → A
* score ≤ 4 → B
* score ≤ 9 → C
* score > 9 → D

Calibration target = brief §2.1 baseline (28 A / 14 B / 6 C / 1 D over
the 50-skill surface as of 2026-05-08). Universal-gap rules (5/6/8/9)
return ``INFO`` rather than ``MINOR`` so they remain visible in the
report without penalising every skill out of Grade A on the M1
baseline. M2 closes the Examples gap; M6 closes the evals gap.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from skill_domain.agent_model import Agent
from skill_domain.skill_model import Skill

# ---------------------------------------------------------------------------
# Severity ladder
# ---------------------------------------------------------------------------

SEVERITY_WEIGHTS = {"OK": 0, "INFO": 0, "MINOR": 1, "MAJOR": 3, "CRITICAL": 7}

# Score → grade mapping. Calibrated against the live ``.claude/skills/``
# surface so the baseline reproduces brief §2.1.
GRADE_THRESHOLDS = (
    (2, "A"),
    (4, "B"),
    (9, "C"),
    (10**6, "D"),
)


def grade_for_score(score: int) -> str:
    for ceiling, letter in GRADE_THRESHOLDS:
        if score <= ceiling:
            return letter
    return "D"


# ---------------------------------------------------------------------------
# Rubric primitives
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RubricResult:
    """Outcome of evaluating one rule against one target."""

    rule_name: str
    severity: str
    reason: str

    @property
    def weight(self) -> int:
        return SEVERITY_WEIGHTS[self.severity]


@dataclass(frozen=True)
class Rule:
    """A named predicate over a target (``Skill`` or ``Agent``).

    The predicate is typed as ``Callable[..., RubricResult]`` because
    ``SKILL_RULES`` carries skill predicates and ``AGENT_RULES`` carries
    agent predicates; the use case applies the rule to a target of the
    matching type, so the dispatch is type-safe by construction.
    """

    name: str
    predicate: Callable[[Any], RubricResult]

    def evaluate(self, target: Skill | Agent) -> RubricResult:
        return self.predicate(target)


# ---------------------------------------------------------------------------
# Anthropic-standard regex constants (referenced by rule_1)
# ---------------------------------------------------------------------------

_NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
_BANNED_SUBSTRINGS = ("claude", "anthropic")
_XML_TAG_RE = re.compile(r"<[a-zA-Z][^>]*>")
_DESCRIPTION_MAX_CHARS = 1024

# Frontmatter fields beyond ``name`` and ``description`` that are common
# in the live surface but technically violate the Anthropic minimum
# spec. Treated as INFO (visible, no penalty) for ≤2 extras.
_TOLERATED_EXTRA_FIELDS = frozenset(
    {
        "effort",
        "argument-hint",
        "tags",
        "requires",
    }
)
# Agent-shape frontmatter fields. When a SKILL.md carries these, the
# skill is misclassified as an agent (rule 1 CRITICAL).
_AGENT_SHAPE_FIELDS = frozenset({"model", "color", "tools"})

# ---------------------------------------------------------------------------
# Skills rubric (10 rules per brief §3)
# ---------------------------------------------------------------------------


def _rule_1_frontmatter_valid(skill: Skill) -> RubricResult:
    """Frontmatter has only ``name``+``description``; both pass Anthropic checks."""
    name = skill.frontmatter.name
    description = skill.frontmatter.description
    extras = skill.frontmatter.extra_fields

    if not name or not _NAME_RE.match(name):
        return RubricResult(
            "rule_1_frontmatter_valid",
            "CRITICAL",
            f"name {name!r} does not match {_NAME_RE.pattern}",
        )
    lowered = name.lower()
    for banned in _BANNED_SUBSTRINGS:
        if banned in lowered:
            return RubricResult(
                "rule_1_frontmatter_valid",
                "CRITICAL",
                f"name contains banned substring {banned!r}",
            )
    if not description:
        return RubricResult(
            "rule_1_frontmatter_valid",
            "CRITICAL",
            "description is empty",
        )
    if len(description) > _DESCRIPTION_MAX_CHARS:
        return RubricResult(
            "rule_1_frontmatter_valid",
            "MAJOR",
            f"description {len(description)} chars > {_DESCRIPTION_MAX_CHARS}",
        )
    if _XML_TAG_RE.search(description):
        return RubricResult(
            "rule_1_frontmatter_valid",
            "MAJOR",
            "description contains XML-like tags",
        )

    # Extra-field violation classification.
    if extras:
        agent_shape = [f for f in extras if f in _AGENT_SHAPE_FIELDS]
        non_tolerated = [
            f for f in extras if f not in _TOLERATED_EXTRA_FIELDS and f not in _AGENT_SHAPE_FIELDS
        ]
        # Skill carrying agent-style frontmatter is the Anthropic
        # taxonomy violation called out in §3 rule 1: skills declare
        # invocation contracts; agents declare model + tools + color.
        if len(agent_shape) >= 2:
            return RubricResult(
                "rule_1_frontmatter_valid",
                "CRITICAL",
                (
                    "frontmatter carries agent-shape fields "
                    f"{sorted(agent_shape)!r} — skill misclassified as agent"
                ),
            )
        if agent_shape:
            return RubricResult(
                "rule_1_frontmatter_valid",
                "MAJOR",
                f"frontmatter has agent-shape field {sorted(agent_shape)!r}",
            )
        if non_tolerated:
            return RubricResult(
                "rule_1_frontmatter_valid",
                "MAJOR",
                f"frontmatter has non-standard fields {non_tolerated!r}",
            )
        if len(extras) >= 5:
            return RubricResult(
                "rule_1_frontmatter_valid",
                "MAJOR",
                f"frontmatter has {len(extras)} extra fields {sorted(extras)!r}",
            )
        if len(extras) == 4:
            return RubricResult(
                "rule_1_frontmatter_valid",
                "MINOR",
                f"frontmatter has 4 extra fields {sorted(extras)!r}",
            )
        # 1-3 tolerated extras → INFO (visible, not penalised at M1).
        return RubricResult(
            "rule_1_frontmatter_valid",
            "INFO",
            f"frontmatter has tolerated extra fields {sorted(extras)!r}",
        )
    return RubricResult("rule_1_frontmatter_valid", "OK", "frontmatter clean")


# Match straight or curly single quotes (and double quotes) wrapping a
# trigger phrase. Unicode left/right single quotation marks come in via
# explicit ``\uXXXX`` escapes (U+2018, U+2019) so the source stays
# ASCII-clean.
_QUOTE_CHARS = "'\u2018\u2019\""
_TRIGGER_PHRASE_PATTERNS = (
    re.compile(r"trigger\s+(?:for|when|on)", re.IGNORECASE),
    re.compile(f"[{_QUOTE_CHARS}]([^{_QUOTE_CHARS}]{{3,80}})[{_QUOTE_CHARS}]"),
)


_USE_FOR_RE = re.compile(
    r"(?:use\s+for|use\s+after|use\s+at|use\s+when|trigger\s+(?:for|on|when))[:\s]+([^.]+)",
    re.IGNORECASE,
)


def _count_trigger_phrases(description: str) -> int:
    """Heuristic count of trigger phrases.

    Two complementary signals:

    * Quoted phrases (Anthropic canonical: ``Trigger for 'foo', 'bar'.``)
    * Comma-separated items in a ``Use for: …`` / ``Use when: …`` clause.
    """
    quoted = sum(1 for m in _TRIGGER_PHRASE_PATTERNS[1].findall(description) if 3 <= len(m) <= 80)
    if quoted:
        return quoted
    # Fallback: count comma-separated items after "Use for" / "Use when".
    fallback = 0
    for match in _USE_FOR_RE.finditer(description):
        clause = match.group(1)
        items = [item.strip() for item in clause.split(",") if item.strip()]
        fallback = max(fallback, len(items))
    return fallback


_FIRST_SECOND_PERSON_RE = re.compile(
    r"\b(?:I|me|my|we|us|our|you|your|yours)\b",
)


def _rule_2_third_person_cso_three_triggers(skill: Skill) -> RubricResult:
    description = skill.frontmatter.description
    triggers = _count_trigger_phrases(description)
    has_use_when = bool(
        re.search(
            r"\b(?:use\s+when|trigger\s+for|trigger\s+when|use\s+after|use\s+at|use\s+for)\b",
            description,
            re.IGNORECASE,
        )
    )
    if triggers == 0 and not has_use_when:
        return RubricResult(
            "rule_2_third_person_cso_three_triggers",
            "CRITICAL",
            "description has no trigger phrases and no 'Use when …' clause",
        )
    if triggers == 0:
        # Has Use-when but no enumerated triggers.
        return RubricResult(
            "rule_2_third_person_cso_three_triggers",
            "MAJOR",
            "description has 'Use when' clause but no enumerated triggers",
        )
    if triggers < 3:
        return RubricResult(
            "rule_2_third_person_cso_three_triggers",
            "MINOR",
            f"description has {triggers} trigger phrase(s) (<3)",
        )
    # First-/second-person pronouns in conversational context (e.g.,
    # "Use when something breaks and you need …") are not penalised at
    # M1 baseline — descriptions like ai-debug ("Use when something is
    # broken and you need to find out why") are §2.1 Grade-A exemplars.
    return RubricResult(
        "rule_2_third_person_cso_three_triggers",
        "OK",
        f"{triggers} triggers, CSO",
    )


_NEGATIVE_SCOPE_HINTS = (
    "not for",
    "do not use",
    "don't use",
    "use instead",
    "instead of",
)


def _rule_3_negative_scoping(skill: Skill) -> RubricResult:
    desc = skill.frontmatter.description.lower()
    body = skill.body.lower()
    if any(h in desc for h in _NEGATIVE_SCOPE_HINTS):
        return RubricResult("rule_3_negative_scoping", "OK", "negative scoping in description")
    # Body fallback — many current skills include a "NOT for" line in
    # ## When to Use. M1 baseline accepts body-only as OK; M2 tightens
    # by requiring the "Not for" clause in the description itself.
    if any(h in body for h in _NEGATIVE_SCOPE_HINTS):
        return RubricResult(
            "rule_3_negative_scoping",
            "INFO",
            "negative scoping only in body, not description",
        )
    return RubricResult(
        "rule_3_negative_scoping",
        "MINOR",
        "no negative scoping found — adjacent skills risk confusion",
    )


def _rule_4_line_and_token_budget(skill: Skill) -> RubricResult:
    if skill.line_count > 500:
        return RubricResult(
            "rule_4_line_and_token_budget",
            "CRITICAL",
            f"{skill.line_count} lines > 500 hard cap",
        )
    if skill.token_estimate > 5000:
        return RubricResult(
            "rule_4_line_and_token_budget",
            "CRITICAL",
            f"{skill.token_estimate} tokens > 5000 cap",
        )
    if skill.line_count > 200:
        return RubricResult(
            "rule_4_line_and_token_budget",
            "MAJOR",
            f"{skill.line_count} lines well over ≤120 lean target",
        )
    if skill.line_count > 120:
        return RubricResult(
            "rule_4_line_and_token_budget",
            "MINOR",
            f"{skill.line_count} lines > 120 lean target",
        )
    return RubricResult("rule_4_line_and_token_budget", "OK", f"{skill.line_count} lines")


_REQUIRED_SECTIONS = ("Quick start", "Workflow", "Examples", "Integration")


def _rule_5_required_sections(skill: Skill) -> RubricResult:
    """Required: ## Quick start, ## Workflow, ## Examples, ## Integration.

    Lenient match: ``## Process`` accepted as ``Workflow`` synonym;
    ``## Purpose`` accepted as ``Quick start`` synonym for the M1
    baseline (M2 will tighten).
    """
    sections_lower = tuple(s.lower() for s in skill.sections)
    missing: list[str] = []
    for required in _REQUIRED_SECTIONS:
        rl = required.lower()
        if rl in sections_lower:
            continue
        # Synonyms accepted at M1 baseline.
        if rl == "quick start" and ("purpose" in sections_lower or "overview" in sections_lower):
            continue
        if rl == "workflow" and (
            "process" in sections_lower
            or "workflow (deterministic where possible)" in sections_lower
        ):
            continue
        missing.append(required)
    if not missing:
        return RubricResult("rule_5_required_sections", "OK", "all required sections present")
    # Examples is the universal §2.1 gap (0/50 ship it). Subtract it
    # from the effective-missing count so it never penalises a skill
    # that is otherwise well-structured. Rule 6 still surfaces the
    # missing examples as INFO.
    examples_only = missing == ["Examples"]
    effective = [m for m in missing if m != "Examples"]
    if examples_only:
        return RubricResult(
            "rule_5_required_sections",
            "INFO",
            "missing section: Examples (universal §2.1 gap)",
        )
    if not effective:
        # Should not happen given examples_only branch above.
        return RubricResult(
            "rule_5_required_sections",
            "INFO",
            f"missing sections: {', '.join(missing)}",
        )
    n = len(effective)
    if n == 1:
        return RubricResult(
            "rule_5_required_sections",
            "MINOR",
            f"missing section: {effective[0]} (Examples also missing — universal gap)",
        )
    if n == 2:
        return RubricResult(
            "rule_5_required_sections",
            "MAJOR",
            f"missing sections: {', '.join(effective)}",
        )
    # 3+ effective sections missing. If the body still has substantial
    # structure (≥5 ## headings), the skill ships custom-named sections
    # rather than the canonical rubric set — MAJOR rather than CRITICAL.
    if len(skill.sections) >= 5:
        return RubricResult(
            "rule_5_required_sections",
            "MAJOR",
            f"missing canonical sections {', '.join(effective)} "
            f"(body uses {len(skill.sections)} custom-named sections)",
        )
    return RubricResult(
        "rule_5_required_sections",
        "CRITICAL",
        f"missing sections: {', '.join(effective)}",
    )


def _rule_6_examples_count(skill: Skill) -> RubricResult:
    if skill.examples_count >= 2:
        return RubricResult(
            "rule_6_examples_count",
            "OK",
            f"{skill.examples_count} examples",
        )
    if skill.examples_count == 1:
        return RubricResult(
            "rule_6_examples_count",
            "MINOR",
            "only 1 example (need ≥2)",
        )
    # Universal §2.1 gap — visible (INFO), not penalised at M1 baseline.
    return RubricResult(
        "rule_6_examples_count",
        "INFO",
        "no ## Examples section — universal §2.1 gap",
    )


def _rule_7_refs_nesting_with_toc(skill: Skill) -> RubricResult:
    """References >100 lines live in `references/` one level deep with TOC."""
    if not skill.refs_paths:
        return RubricResult(
            "rule_7_refs_nesting_with_toc",
            "OK",
            "no references/ directory (rule not triggered)",
        )
    # Live in references/ one level deep — flatness check.
    deeply_nested = [p for p in skill.refs_paths if len(p.parts) > 1 and "references" in p.parts]
    if any(len(p.relative_to(p.parts[0]).parts) > 2 for p in deeply_nested):
        return RubricResult(
            "rule_7_refs_nesting_with_toc",
            "MAJOR",
            "references/ contains deeply-nested files (>1 level deep)",
        )
    return RubricResult(
        "rule_7_refs_nesting_with_toc",
        "OK",
        f"{len(skill.refs_paths)} reference(s), flat layout",
    )


def _rule_8_evals_present_threshold(skill: Skill) -> RubricResult:
    if skill.eval_count >= 3:
        return RubricResult(
            "rule_8_evals_present_threshold",
            "OK",
            f"{skill.eval_count} eval cases",
        )
    if skill.eval_count == 0:
        # Universal §2.1 gap (M6 ships eval harness) — visible (INFO),
        # not penalised at the M1 baseline.
        return RubricResult(
            "rule_8_evals_present_threshold",
            "INFO",
            "no evals/<skill>.jsonl — M6 ships eval harness",
        )
    return RubricResult(
        "rule_8_evals_present_threshold",
        "MINOR",
        f"only {skill.eval_count} eval cases (<3)",
    )


def _rule_9_optimizer_committed(skill: Skill) -> RubricResult:
    if skill.optimizer_committed:
        return RubricResult(
            "rule_9_optimizer_committed",
            "OK",
            "description optimized via run_loop",
        )
    # Universal §2.1 gap (M2 closes optimizer pass) — INFO at M1.
    return RubricResult(
        "rule_9_optimizer_committed",
        "INFO",
        "description not yet optimized via run_loop",
    )


def _rule_10_no_anti_patterns(skill: Skill) -> RubricResult:
    hits = list(skill.anti_pattern_hits)
    agent_shape = bool(set(skill.frontmatter.extra_fields) & _AGENT_SHAPE_FIELDS)
    if not hits:
        return RubricResult("rule_10_no_anti_patterns", "OK", "no anti-patterns")
    # Metaphor in name is the heaviest anti-pattern signal (per §2.4
    # bottom-10 list — historical metaphor names retired in M4 rename).
    metaphor_hit = next((h for h in hits if h.startswith("metaphor in name")), None)
    # Metaphor name + agent-shape frontmatter is the §2.1 D-grade
    # signature ("broken — implementation prose, no triggers"): the
    # skill is misnamed AND mis-classified.
    if metaphor_hit and agent_shape:
        return RubricResult(
            "rule_10_no_anti_patterns",
            "CRITICAL",
            f"metaphor name {metaphor_hit!r} + agent-shape frontmatter",
        )
    if metaphor_hit and len(hits) >= 2:
        return RubricResult(
            "rule_10_no_anti_patterns",
            "MAJOR",
            f"anti-patterns: {', '.join(hits)}",
        )
    if metaphor_hit:
        return RubricResult(
            "rule_10_no_anti_patterns",
            "MAJOR",
            f"anti-pattern: {metaphor_hit}",
        )
    if len(hits) == 1:
        return RubricResult(
            "rule_10_no_anti_patterns",
            "MINOR",
            f"anti-pattern: {hits[0]}",
        )
    if len(hits) <= 3:
        return RubricResult(
            "rule_10_no_anti_patterns",
            "MAJOR",
            f"anti-patterns: {', '.join(hits)}",
        )
    return RubricResult(
        "rule_10_no_anti_patterns",
        "CRITICAL",
        f"anti-patterns ({len(hits)}): {', '.join(hits[:5])}",
    )


SKILL_RULES: tuple[Rule, ...] = (
    Rule("rule_1_frontmatter_valid", _rule_1_frontmatter_valid),
    Rule("rule_2_third_person_cso_three_triggers", _rule_2_third_person_cso_three_triggers),
    Rule("rule_3_negative_scoping", _rule_3_negative_scoping),
    Rule("rule_4_line_and_token_budget", _rule_4_line_and_token_budget),
    Rule("rule_5_required_sections", _rule_5_required_sections),
    Rule("rule_6_examples_count", _rule_6_examples_count),
    Rule("rule_7_refs_nesting_with_toc", _rule_7_refs_nesting_with_toc),
    Rule("rule_8_evals_present_threshold", _rule_8_evals_present_threshold),
    Rule("rule_9_optimizer_committed", _rule_9_optimizer_committed),
    Rule("rule_10_no_anti_patterns", _rule_10_no_anti_patterns),
)


# ---------------------------------------------------------------------------
# Agents rubric (5 rules per umbrella spec §3 / brief §22)
# ---------------------------------------------------------------------------


def _agent_rule_1_cso_third_person(agent: Agent) -> RubricResult:
    """Agent rule 1: CSO third-person description, ≤1024 chars.

    Agent descriptions follow a different convention than skills —
    they are typically a noun-phrase identity statement ("Correctness
    specialist reviewer. …") rather than a "Use when …" trigger
    clause. The rubric accepts either shape. Banned substrings
    (``claude``, ``anthropic``) and XML-like tags inherit the
    Anthropic standard.
    """
    description = agent.frontmatter.description
    if not description:
        return RubricResult(
            "agent_rule_1_cso_third_person",
            "CRITICAL",
            "agent has empty description",
        )
    if len(description) > _DESCRIPTION_MAX_CHARS:
        return RubricResult(
            "agent_rule_1_cso_third_person",
            "MAJOR",
            f"description {len(description)} chars > {_DESCRIPTION_MAX_CHARS}",
        )
    lowered = description.lower()
    for banned in _BANNED_SUBSTRINGS:
        if banned in lowered:
            return RubricResult(
                "agent_rule_1_cso_third_person",
                "MAJOR",
                f"description contains banned substring {banned!r}",
            )
    if _XML_TAG_RE.search(description):
        return RubricResult(
            "agent_rule_1_cso_third_person",
            "MINOR",
            "description contains XML-like tags",
        )
    if _FIRST_SECOND_PERSON_RE.search(description):
        return RubricResult(
            "agent_rule_1_cso_third_person",
            "MINOR",
            "description uses first/second-person pronouns",
        )
    return RubricResult(
        "agent_rule_1_cso_third_person",
        "OK",
        f"CSO third-person ({len(description)} chars)",
    )


def _agent_rule_2_tools_whitelist(agent: Agent) -> RubricResult:
    if not agent.frontmatter.tools:
        return RubricResult(
            "agent_rule_2_tools_whitelist",
            "MAJOR",
            "agent missing explicit ``tools:`` whitelist",
        )
    return RubricResult(
        "agent_rule_2_tools_whitelist",
        "OK",
        f"tools: {', '.join(agent.frontmatter.tools)}",
    )


def _agent_rule_3_model_declared(agent: Agent) -> RubricResult:
    model = agent.frontmatter.model
    if model is None:
        return RubricResult(
            "agent_rule_3_model_declared",
            "MAJOR",
            "agent missing ``model:`` declaration",
        )
    if model not in {"opus", "sonnet", "haiku"}:
        return RubricResult(
            "agent_rule_3_model_declared",
            "MINOR",
            f"model {model!r} is not opus/sonnet/haiku",
        )
    return RubricResult("agent_rule_3_model_declared", "OK", f"model={model}")


def _agent_rule_4_dispatch_source(agent: Agent) -> RubricResult:
    if agent.dispatched_by:
        return RubricResult(
            "agent_rule_4_dispatch_source",
            "OK",
            f"dispatched by {len(agent.dispatched_by)} source(s)",
        )
    return RubricResult(
        "agent_rule_4_dispatch_source",
        "MAJOR",
        "no dispatch source references — agent appears orphaned",
    )


def _agent_rule_5_no_orphan(agent: Agent) -> RubricResult:
    """Soft check — at least one mention in dispatch sources."""
    if agent.dispatched_by:
        return RubricResult("agent_rule_5_no_orphan", "OK", "non-orphan")
    return RubricResult(
        "agent_rule_5_no_orphan",
        "CRITICAL",
        "agent file is not referenced anywhere — orphan",
    )


AGENT_RULES: tuple[Rule, ...] = (
    Rule("agent_rule_1_cso_third_person", _agent_rule_1_cso_third_person),
    Rule("agent_rule_2_tools_whitelist", _agent_rule_2_tools_whitelist),
    Rule("agent_rule_3_model_declared", _agent_rule_3_model_declared),
    Rule("agent_rule_4_dispatch_source", _agent_rule_4_dispatch_source),
    Rule("agent_rule_5_no_orphan", _agent_rule_5_no_orphan),
)
