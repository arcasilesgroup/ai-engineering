"""portability checker — spec-187 model-portability lint (W1 T-2/T-3, W5 flip).

Structural neutrality lint (no live-model runs — spec-187 Non-Goals).
Flags canonical prose that quietly assumes the Claude Code host: a bare
Claude tool literal used *as a tool* (a call form, a "tool"-qualified
mention, an arrow/slash tool map, or a clause-leading imperative command).
Other function-calling harnesses (Kimi/GLM/DeepSeek/Qwen/MiMo) name their
tools differently, so an un-gated tool literal is a portability hazard
(spec-187 research SS Cross-model).

W5 tuning (D-187-07 flip to blocking):

* **Ambiguous English-verb literals are NOT matched.** ``Read`` / ``Write``
  / ``Edit`` are everyday English verbs ("Read the spec", "Write the
  report") — matching them produced ~47 false positives dominated by
  sentence-leading prose. They are dropped from the literal set. So are
  ``Task`` / ``Agent``: in this repo they are core *domain* vocabulary
  ("Task statuses", "the build agent") rather than tool references.
* **Only distinctive Claude tool names are matched** — ``Bash`` / ``Glob``
  / ``Grep`` / ``TodoWrite`` / ``NotebookEdit`` / ``MultiEdit`` /
  ``WebFetch`` / ``WebSearch`` plus the MCP ``mcp__*`` literal — and only
  when a **tool signal** is present (a ``(`` call form, the word "tool" on
  the line, a ``->``/arrow map, a ``Grep/Glob`` slash pair, or the literal
  leading the clause as an imperative command). This flags genuine tool
  usage while leaving ordinary prose alone.
* **``/ai-*`` slash idioms and ``$ARGUMENTS`` are NOT flagged.** They are
  documented harness-provided conventions (AGENTS.md portable fence, W4),
  not portability hazards, so the lint does not treat them as findings.

A line carrying a documented gate phrase ("or the engine equivalent",
"host-provided", a tool-name/family map, ...) suppresses its findings.

Posture: BLOCKING in W5 (D-187-07) — a genuine tool-literal finding is
MAJOR and drives the CLI exit code. All reason strings are pure ASCII so a
raw / non-tty write is cp1252 safe (spec-187 D-187-10). Pure stdlib
(``re`` + ``pathlib``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

_VALID_SEVERITIES = {"OK", "INFO", "MINOR", "MAJOR", "CRITICAL"}


@dataclass(frozen=True)
class RubricResult:
    """Outcome of a single portability check against a file."""

    rule_name: str
    severity: str
    reason: str

    def __post_init__(self) -> None:
        if self.severity not in _VALID_SEVERITIES:
            raise ValueError(f"severity {self.severity!r} not in {sorted(_VALID_SEVERITIES)}")


# Distinctive Claude-native tool literals (case-sensitive, word-boundary).
# Ambiguous English words (Read/Write/Edit/Task/Agent) are deliberately
# excluded — see the module docstring.
_TOOL_LITERALS: tuple[str, ...] = (
    "Bash",
    "Glob",
    "Grep",
    "TodoWrite",
    "NotebookEdit",
    "MultiEdit",
    "WebFetch",
    "WebSearch",
)
_TOOL_ALT = "|".join(_TOOL_LITERALS)

# A finding is suppressed when its line carries a portability qualifier —
# the author has already signalled the host-neutral escape hatch.
_GATE_PHRASES: tuple[str, ...] = (
    "engine equivalent",
    "or equivalent",
    "host equivalent",
    "host-provided",
    "host provided",
    "engine-neutral",
    "engine neutral",
    "tool-name map",
    "tool name map",
    "family map",
    "whatever lifecycle",
    "slash layer",
    "on a host without",
    "or the engine",
)

_LITERAL_RE = re.compile(r"\b(" + _TOOL_ALT + r")\b")
# MCP tool literal (``mcp__server__tool``) — unambiguous tool reference.
_MCP_RE = re.compile(r"\bmcp__[A-Za-z0-9_]+\b")
# A tool literal slash-joined with another tool literal ("Grep/Glob").
_SLASH_PAIR_RE = re.compile(r"\b(" + _TOOL_ALT + r")\s*/\s*(" + _TOOL_ALT + r")\b")
# A tool literal leading the clause (optionally after a list/step marker
# and/or bold lead-in) — an imperative tool command ("Grep every ...").
_CLAUSE_START_RE = re.compile(r"^[ \t]*(?:(?:[-*>]|\d+[.)])\s+)?(?:\*\*\s*)?(" + _TOOL_ALT + r")\b")
_FENCE_RE = re.compile(r"^```")
_INLINE_CODE_RE = re.compile(r"`[^`]*`")
_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)


def _prose_lines(text: str) -> list[str]:
    """Return body lines outside frontmatter and fenced code blocks.

    Inline-code spans are stripped per-line so a tool literal written as
    code is not flagged.
    """
    body = _FRONTMATTER_RE.sub("", text, count=1)
    lines: list[str] = []
    in_fence = False
    for raw in body.splitlines():
        if _FENCE_RE.match(raw.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        lines.append(_INLINE_CODE_RE.sub(" ", raw))
    return lines


def _has_gate(line: str) -> bool:
    lowered = line.lower()
    return any(phrase in lowered for phrase in _GATE_PHRASES)


def _flagged_tool_literals(line: str) -> set[str]:
    """Return the set of tool literals used *as tools* on this line.

    A literal counts only when a tool signal is present: an MCP literal, a
    slash-joined tool pair, the word "tool" on the line, a ``(`` call form,
    an arrow map, or the literal leading the clause. Bare occurrences of an
    ambiguous English word are already excluded by the literal set.
    """
    flagged: set[str] = set()

    # MCP literals are unambiguous tool references.
    for match in _MCP_RE.finditer(line):
        flagged.add(match.group(0))

    # Slash-joined tool pairs — both sides are tool references.
    for match in _SLASH_PAIR_RE.finditer(line):
        flagged.add(match.group(1))
        flagged.add(match.group(2))

    has_tool_word = "tool" in line.lower()
    is_table_row = line.lstrip().startswith("|")
    clause = None if is_table_row else _CLAUSE_START_RE.match(line)
    if clause is not None:
        flagged.add(clause.group(1))

    for match in _LITERAL_RE.finditer(line):
        name = match.group(1)
        end = match.end(1)
        rest = line[end:].lstrip()
        call_form = line[end : end + 1] == "("  # Grep(
        arrow_map = rest.startswith("->") or rest.startswith("→")  # Glob -> / Glob →
        if call_form or has_tool_word or arrow_map:  # or "the Bash tool"
            flagged.add(name)

    return flagged


def check_file_portability(md_path: Path) -> RubricResult:
    """Run the portability rule against a single markdown file.

    Returns a single roll-up ``RubricResult``:

    * ``OK`` — no un-gated tool literal found.
    * ``MAJOR`` — one or more un-gated Claude-only tool literals used as
      tools (blocking in W5, D-187-07).
    * ``CRITICAL`` — the file is unreadable.
    """
    if not md_path.is_file():
        return RubricResult("portability", "CRITICAL", f"file not found at {md_path}")

    text = md_path.read_text(encoding="utf-8")
    tool_hits: set[str] = set()
    for line in _prose_lines(text):
        if _has_gate(line):
            continue
        tool_hits |= _flagged_tool_literals(line)

    if not tool_hits:
        return RubricResult("portability", "OK", "no un-gated Claude-only tool literal")

    return RubricResult(
        "portability",
        "MAJOR",
        "un-gated tool literals: " + ", ".join(sorted(tool_hits)),
    )


def check_portability(
    skills_root: Path,
    agents_root: Path,
) -> list[tuple[Path, RubricResult]]:
    """Walk canonical skills + agents and run the portability rule.

    Returns ``[(path, RubricResult), ...]`` sorted by path. Blocking in W5
    — a MAJOR finding drives the CLI exit code (D-187-07).
    """
    results: list[tuple[Path, RubricResult]] = []

    if skills_root.is_dir():
        for skill_dir in sorted(skills_root.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                continue
            results.append((skill_md, check_file_portability(skill_md)))

    if agents_root.is_dir():
        for agent_md in sorted(agents_root.glob("*.md")):
            results.append((agent_md, check_file_portability(agent_md)))

    return results


def write_findings(results: list[tuple[Path, RubricResult]], stream: TextIO) -> None:
    """Write pure-ASCII, one-line-per-finding output to ``stream``.

    Only non-OK findings are written. Output is guaranteed ASCII so a raw /
    non-tty write is cp1252-safe (D-187-10).
    """
    for path, result in results:
        if result.severity == "OK":
            continue
        stream.write(f"{result.severity} portability {path}: {result.reason}\n")
