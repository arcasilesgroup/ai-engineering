"""Input Guard — Dual-Plane Probabilistic-Plane entry filter.

Scans incoming prompts for PII patterns and known agent-manipulation
signatures BEFORE the prompt reaches the LLM. Refuses (exit 2) when a
pattern matches; logs (exit 1) when ambiguous.

Stays deterministic by design — the policy engine + immutable audit log
provide the rest of the Dual-Plane guarantees (ADR-0002).
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class GuardRule:
    name: str
    pattern: re.Pattern[str]
    severity: str  # critical | high | medium | low


# PII surface
PII_RULES: tuple[GuardRule, ...] = (
    GuardRule("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "high"),
    GuardRule(
        "credit_card",
        re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
        "high",
    ),
    GuardRule(
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "low",
    ),
)

# Manipulation signatures (curated, not exhaustive — defence in depth).
MANIP_RULES: tuple[GuardRule, ...] = (
    GuardRule(
        "ignore_previous_instructions",
        re.compile(
            r"\b(ignore|disregard)\s+(?:all\s+)?(?:previous|prior|earlier)\s+(?:instructions?|rules?|prompts?)",
            re.IGNORECASE,
        ),
        "high",
    ),
    GuardRule(
        "system_role_override",
        re.compile(r"\bsystem\s*[:>]\s*you\s+are\s+now", re.IGNORECASE),
        "high",
    ),
    GuardRule(
        "credential_extraction",
        re.compile(
            r"\b(?:reveal|leak|print|dump)\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions|secrets?|api\s*keys?)",
            re.IGNORECASE,
        ),
        "critical",
    ),
)


@dataclass(frozen=True)
class GuardFinding:
    rule: GuardRule
    snippet: str


def scan(text: str, rules: Iterable[GuardRule]) -> list[GuardFinding]:
    findings: list[GuardFinding] = []
    for rule in rules:
        for match in rule.pattern.finditer(text):
            findings.append(GuardFinding(rule=rule, snippet=match.group(0)))
    return findings


def evaluate(text: str) -> int:
    pii = scan(text, PII_RULES)
    manip = scan(text, MANIP_RULES)
    high_or_critical = [f for f in (pii + manip) if f.rule.severity in {"critical", "high"}]
    if high_or_critical:
        for f in high_or_critical:
            sys.stderr.write(f"[input-guard] BLOCK rule={f.rule.name} severity={f.rule.severity}\n")
        return 2  # block + show to model
    if pii or manip:
        for f in pii + manip:
            sys.stderr.write(f"[input-guard] WARN rule={f.rule.name} severity={f.rule.severity}\n")
        return 1  # warn user only
    return 0


def main(argv: list[str]) -> int:
    text = sys.stdin.read() if not sys.stdin.isatty() else " ".join(argv[1:])
    return evaluate(text)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
