"""token_budget checker — spec-187 W1 (T-6/T-7) authoring-cap lint.

Encodes the Anthropic frontmatter caps as an advisory lint (spec-187
D-187-06, research §Authoring contract):

* ``description`` <= 1024 chars (the sole routing signal; over-budget
  descriptions inflate the session routing tax).
* ``name`` <= 64 chars.
* ``name`` carries no reserved word (``anthropic`` / ``claude``).

Runs over all canonical skills (``<root>/ai-*/SKILL.md``) and agents
(``<agents_root>/*.md``). Posture: WARN-ONLY in W1 (advisory; never
drives the CLI exit code); flips to blocking in W5 (D-187-07). All reason
strings are pure ASCII so raw / non-tty writes stay cp1252-safe
(D-187-10). Pure stdlib (``re`` + ``pathlib``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

_VALID_SEVERITIES = {"OK", "INFO", "MINOR", "MAJOR", "CRITICAL"}

_DESCRIPTION_MAX_CHARS = 1024
_NAME_MAX_CHARS = 64
# Anthropic reserved words disallowed in a skill/agent name.
_RESERVED_WORDS: tuple[str, ...] = ("anthropic", "claude")


@dataclass(frozen=True)
class RubricResult:
    """Outcome of a single token-budget sub-check against a file."""

    rule_name: str
    severity: str
    reason: str

    def __post_init__(self) -> None:
        if self.severity not in _VALID_SEVERITIES:
            raise ValueError(f"severity {self.severity!r} not in {sorted(_VALID_SEVERITIES)}")


_FRONTMATTER_RE = re.compile(r"^---\n(?P<fm>.*?)\n---", re.DOTALL)
_NAME_RE = re.compile(r"^name:\s*(?P<val>.+?)\s*$", re.MULTILINE)
# description may be quoted (single/double) and may span the value on one
# line — the canonical surface keeps description on a single line.
_DESC_RE = re.compile(r"^description:\s*(?P<val>.+?)\s*$", re.MULTILINE)


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _parse_frontmatter(text: str) -> tuple[str | None, str | None]:
    """Return ``(name, description)`` from the YAML frontmatter, or Nones."""
    fm_match = _FRONTMATTER_RE.match(text)
    if not fm_match:
        return (None, None)
    fm = fm_match.group("fm")
    name_match = _NAME_RE.search(fm)
    desc_match = _DESC_RE.search(fm)
    name = _unquote(name_match.group("val")) if name_match else None
    desc = _unquote(desc_match.group("val")) if desc_match else None
    return (name, desc)


def check_file_token_budget(md_path: Path) -> list[RubricResult]:
    """Run the name/description caps against a single markdown file.

    Returns a list of ``RubricResult`` (one per triggered rule); an
    all-clear file returns a single ``OK`` result.
    """
    if not md_path.is_file():
        return [RubricResult("token_budget", "CRITICAL", f"file not found at {md_path}")]

    name, description = _parse_frontmatter(md_path.read_text(encoding="utf-8"))
    findings: list[RubricResult] = []

    if description is not None and len(description) > _DESCRIPTION_MAX_CHARS:
        findings.append(
            RubricResult(
                "token_budget_description",
                "MINOR",
                f"description is {len(description)} chars (over {_DESCRIPTION_MAX_CHARS})",
            )
        )

    if name is not None:
        if len(name) > _NAME_MAX_CHARS:
            findings.append(
                RubricResult(
                    "token_budget_name_length",
                    "MINOR",
                    f"name is {len(name)} chars (over {_NAME_MAX_CHARS})",
                )
            )
        lowered = name.lower()
        hit = next((word for word in _RESERVED_WORDS if word in lowered), None)
        if hit is not None:
            findings.append(
                RubricResult(
                    "token_budget_reserved_word",
                    "MINOR",
                    f"name contains reserved word {hit!r}",
                )
            )

    if not findings:
        findings.append(RubricResult("token_budget", "OK", "name/description within budget"))
    return findings


def check_token_budget(
    skills_root: Path,
    agents_root: Path,
) -> list[tuple[Path, RubricResult]]:
    """Walk canonical skills + agents and run the token-budget lint.

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
            for result in check_file_token_budget(skill_md):
                results.append((skill_md, result))

    if agents_root.is_dir():
        for agent_md in sorted(agents_root.glob("*.md")):
            for result in check_file_token_budget(agent_md):
                results.append((agent_md, result))

    return results


def write_findings(results: list[tuple[Path, RubricResult]], stream: TextIO) -> None:
    """Write pure-ASCII, one-line-per-finding output (D-187-10)."""
    for path, result in results:
        if result.severity == "OK":
            continue
        stream.write(f"{result.severity} token_budget {path}: {result.reason}\n")
