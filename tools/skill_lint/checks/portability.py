"""portability checker — spec-187 W1 (T-2/T-3) model-portability lint.

Structural neutrality lint (no live-model runs — spec-187 Non-Goals).
Flags canonical prose that quietly assumes the Claude Code host:

* **Un-gated Claude-only tool literals** — bare occurrences of the
  Claude tool names (``Read``/``Write``/``Edit``/``Bash``/``Glob``/
  ``Grep``/``Task``/…) in body prose, where the line carries no
  portability qualifier ("or the engine equivalent", "host-provided",
  a tool-name map, …). Other function-calling harnesses (Kimi/GLM/
  DeepSeek/Qwen/MiMo) name their tools differently, so an un-gated
  literal is a portability hazard (spec-187 research §Cross-model).
* **Un-gated ``/ai-*`` dispatch idioms** — a slash-command written as
  *bare prose* (not inline code, not code-fenced) assumes a host slash
  layer. On a host without one the skill body must be invoked directly.

Posture: WARN-ONLY in W1 (advisory; never drives the CLI exit code).
Flips to blocking in W5 (D-187-07). Findings are inspected outside
inline-code spans and fenced code blocks to keep noise down; a line
carrying a documented gate phrase suppresses its findings.

All reason strings are pure ASCII so a raw / non-tty write is cp1252
safe (spec-187 D-187-10). Pure stdlib (``re`` + ``pathlib``).
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


# Claude-native tool literals (the host tool surface). Word-boundary
# matched in prose so ordinary English ("read the file") is not caught —
# only the capitalised tool-name form is flagged.
_CLAUDE_TOOL_LITERALS: tuple[str, ...] = (
    "Read",
    "Write",
    "Edit",
    "MultiEdit",
    "NotebookEdit",
    "Bash",
    "Glob",
    "Grep",
    "Task",
    "WebFetch",
    "WebSearch",
    "TodoWrite",
)

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

_TOOL_RE = re.compile(r"\b(" + "|".join(_CLAUDE_TOOL_LITERALS) + r")\b")
# Bare /ai-* token (a leading slash-command) — matched only in residual
# prose after inline-code / fenced-code stripping.
_SLASH_RE = re.compile(r"(?<![\w`])(/ai-[a-z][a-z0-9-]*)")
_FENCE_RE = re.compile(r"^```")
_INLINE_CODE_RE = re.compile(r"`[^`]*`")
_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)


def _prose_lines(text: str) -> list[str]:
    """Return body lines outside frontmatter and fenced code blocks.

    Inline-code spans are stripped per-line so a ``/ai-*`` or tool
    literal written as code is not flagged.
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


def check_file_portability(md_path: Path) -> RubricResult:
    """Run the portability rule against a single markdown file.

    Returns a single roll-up ``RubricResult``:

    * ``OK`` — no un-gated literal / idiom found.
    * ``MINOR`` — one or more un-gated Claude-only tool literals or bare
      ``/ai-*`` dispatch idioms found (advisory / warn-only in W1).
    * ``CRITICAL`` — the file is unreadable.
    """
    if not md_path.is_file():
        return RubricResult("portability", "CRITICAL", f"file not found at {md_path}")

    text = md_path.read_text(encoding="utf-8")
    tool_hits: set[str] = set()
    slash_hits: set[str] = set()
    for line in _prose_lines(text):
        if _has_gate(line):
            continue
        for match in _TOOL_RE.finditer(line):
            tool_hits.add(match.group(1))
        for match in _SLASH_RE.finditer(line):
            slash_hits.add(match.group(1))

    if not tool_hits and not slash_hits:
        return RubricResult("portability", "OK", "no un-gated Claude-only literal or /ai-* idiom")

    parts: list[str] = []
    if tool_hits:
        parts.append("un-gated tool literals: " + ", ".join(sorted(tool_hits)))
    if slash_hits:
        parts.append("bare /ai-* dispatch idioms: " + ", ".join(sorted(slash_hits)))
    return RubricResult("portability", "MINOR", "; ".join(parts))


def check_portability(
    skills_root: Path,
    agents_root: Path,
) -> list[tuple[Path, RubricResult]]:
    """Walk canonical skills + agents and run the portability rule.

    Returns ``[(path, RubricResult), ...]`` sorted by path. Warn-only in
    W1 — the CLI surfaces counts but the check never drives the exit code
    (D-187-07).
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

    Only non-OK findings are written (warn-only surface). Output is
    guaranteed ASCII so a raw / non-tty write is cp1252-safe (D-187-10).
    """
    for path, result in results:
        if result.severity == "OK":
            continue
        stream.write(f"{result.severity} portability {path}: {result.reason}\n")
