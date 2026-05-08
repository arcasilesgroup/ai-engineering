"""Filesystem adapter for the :mod:`skill_app` use cases.

Walks ``.claude/skills/<name>/SKILL.md`` and ``.claude/agents/<name>.md``
in parallel via :class:`concurrent.futures.ThreadPoolExecutor` so the
hot-path budget (D-127-08, ≤200 ms over the current 50 skills) is met
on a cold cache. No third-party deps; pure stdlib + ``skill_domain``.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from skill_domain.agent_model import Agent, AgentFrontmatter
from skill_domain.skill_model import Frontmatter, Skill

_MAX_WORKERS = 8

# ---------------------------------------------------------------------------
# Frontmatter parsing — single-pass regex per file, no PyYAML
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<body>.*?)\n---\s*\n",
    re.DOTALL,
)
_FM_KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$")
_HEADING_RE = re.compile(r"^##\s+(?P<title>[^#\n]+?)\s*$", re.MULTILINE)
_EXAMPLES_INVOCATION_RE = re.compile(
    r"(?:^|\n)```|(?:^|\n)\$\s|(?:^|\n)>\s|(?:^|\n)\*\*Example\b",
    re.IGNORECASE,
)


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return ``(fields, body_after_frontmatter)``.

    A minimal YAML parser that only handles the shapes the live SKILL.md
    surface uses: ``key: value`` (quoted/unquoted scalar), and ``key:``
    followed by indented children (which we collapse to the literal
    string of children for the field). The caller only inspects ``name``
    and ``description``, so deeper structure is not reconstructed.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    fm_body = match.group("body")
    rest = text[match.end() :]
    fields: dict[str, str] = {}
    current_key: str | None = None
    current_buf: list[str] = []

    def _commit() -> None:
        nonlocal current_key, current_buf
        if current_key is None:
            return
        existing = fields.get(current_key, "")
        joined = "\n".join(line for line in current_buf if line.strip())
        if existing and joined:
            fields[current_key] = existing + "\n" + joined
        elif joined:
            fields[current_key] = joined
        elif current_key not in fields:
            fields[current_key] = ""
        current_buf = []

    for raw_line in fm_body.splitlines():
        if raw_line.startswith(" ") or raw_line.startswith("\t"):
            # Continuation / nested child of the current key.
            if current_key is not None:
                current_buf.append(raw_line.strip())
            continue
        m = _FM_KEY_RE.match(raw_line)
        if not m:
            continue
        _commit()
        current_key = m.group(1)
        value = m.group(2).strip()
        # Strip surrounding quotes for scalar values.
        if len(value) >= 2 and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")):
            value = value[1:-1]
        current_buf = [value] if value else []
    _commit()
    return fields, rest


# ---------------------------------------------------------------------------
# Token estimator — cheap, deterministic, no tokenizer dep
# ---------------------------------------------------------------------------


def _estimate_tokens(text: str) -> int:
    """Cheap token estimate: ~4 chars per token (BPE-ish heuristic)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# Anti-pattern detection (rule_10)
# ---------------------------------------------------------------------------

_METAPHOR_NAMES = ("entropy", "sentinel", "instinct", "canvas")
_TIMESTAMP_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_FIRST_PERSON_BODY_RE = re.compile(
    r"(?:^|\n)\s*(?:I\s+|We\s+|Let\s+me\s+|Let's\s+|My\s+|Our\s+)",
)


def _detect_anti_patterns(name: str, body: str) -> tuple[str, ...]:
    hits: list[str] = []
    lowered_name = name.lower()
    for metaphor in _METAPHOR_NAMES:
        if metaphor in lowered_name:
            hits.append(f"metaphor in name: {metaphor!r}")
            break
    if _TIMESTAMP_RE.search(body):
        hits.append("time-stamped prose in body")
    if _FIRST_PERSON_BODY_RE.search(body):
        hits.append("first-person prose in body")
    return tuple(hits)


# ---------------------------------------------------------------------------
# Single-skill parser
# ---------------------------------------------------------------------------


def _parse_skill_file(skill_md: Path) -> Skill | None:
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None
    fields, body = _parse_frontmatter(text)
    if not fields:
        # No frontmatter — treat as broken skill (still emit so rubric flags it).
        fm = Frontmatter(name=skill_md.parent.name, description="", extra_fields=())
        return Skill(
            path=skill_md,
            frontmatter=fm,
            body=text,
            line_count=text.count("\n") + 1,
            token_estimate=_estimate_tokens(text),
            sections=(),
            examples_count=0,
            refs_paths=(),
            anti_pattern_hits=("no frontmatter",),
            has_evals=False,
            eval_count=0,
            optimizer_committed=False,
        )
    # Skip skills that opt out of model invocation — they are manual
    # tools, not part of the AI-discovery surface graded by §2.1.
    if str(fields.get("disable-model-invocation", "")).strip().lower() == "true":
        return None
    name = fields.get("name", skill_md.parent.name).strip()
    description = fields.get("description", "").strip()
    extras = tuple(sorted(k for k in fields if k not in {"name", "description"}))
    fm = Frontmatter(name=name, description=description, extra_fields=extras)

    sections = tuple(m.group("title").strip() for m in _HEADING_RE.finditer(body))
    examples_count = _count_examples(body, sections)
    line_count = text.count("\n") + 1
    token_estimate = _estimate_tokens(text)
    refs_dir = skill_md.parent / "references"
    refs_paths = tuple(sorted(refs_dir.rglob("*.md"))) if refs_dir.is_dir() else ()
    evals_path = skill_md.parent / "evals"
    eval_count = 0
    if evals_path.is_dir():
        for jsonl in evals_path.glob("*.jsonl"):
            try:
                eval_count += sum(
                    1 for line in jsonl.read_text(encoding="utf-8").splitlines() if line.strip()
                )
            except OSError:
                continue
    anti_patterns = _detect_anti_patterns(name, body)
    return Skill(
        path=skill_md,
        frontmatter=fm,
        body=body,
        line_count=line_count,
        token_estimate=token_estimate,
        sections=sections,
        examples_count=examples_count,
        refs_paths=refs_paths,
        anti_pattern_hits=anti_patterns,
        has_evals=eval_count > 0,
        eval_count=eval_count,
        optimizer_committed=False,
    )


def _count_examples(body: str, sections: tuple[str, ...]) -> int:
    """Count invocations under the ``## Examples`` section (if present)."""
    section_lc = tuple(s.lower() for s in sections)
    if "examples" not in section_lc:
        return 0
    # Find the "## Examples" heading position and the next ## heading.
    pat = re.compile(r"^##\s+Examples\s*$", re.IGNORECASE | re.MULTILINE)
    m = pat.search(body)
    if not m:
        return 0
    start = m.end()
    rest = body[start:]
    next_h = re.search(r"^##\s+", rest, re.MULTILINE)
    block = rest[: next_h.start()] if next_h else rest
    # Count fenced code blocks as invocations; fallback to numbered/bullet items.
    invocations = len(re.findall(r"```", block)) // 2
    if invocations == 0:
        invocations = sum(
            1 for line in block.splitlines() if line.lstrip().startswith(("- $", "* $", "$ "))
        )
    return invocations


# ---------------------------------------------------------------------------
# Public API: scanners
# ---------------------------------------------------------------------------


class FilesystemSkillScanner:
    """Adapter implementing :class:`skill_app.ports.SkillScannerPort`."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def scan_skills(self) -> list[Skill]:
        if not self._root.is_dir():
            return []
        candidates = [
            d / "SKILL.md"
            for d in sorted(self._root.iterdir())
            if d.is_dir() and not d.name.startswith("_") and (d / "SKILL.md").is_file()
        ]
        if not candidates:
            return []
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            results = list(pool.map(_parse_skill_file, candidates))
        return [s for s in results if s is not None]


class FilesystemAgentScanner:
    """Adapter implementing :class:`skill_app.ports.AgentScannerPort`."""

    def __init__(self, agents_root: Path, skills_root: Path) -> None:
        self._agents_root = Path(agents_root)
        self._skills_root = Path(skills_root)

    def scan_agents(self) -> list[Agent]:
        if not self._agents_root.is_dir():
            return []
        files = sorted(p for p in self._agents_root.glob("*.md") if p.is_file())
        if not files:
            return []
        # Collect dispatch sources once (ThreadPool reads the bodies in
        # parallel) so each agent's dispatched_by list is computed cheaply.
        dispatch_sources = list(self._dispatch_source_paths())
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            source_bodies = list(pool.map(_safe_read_text, dispatch_sources))
            agent_objs = list(pool.map(_parse_agent_file, files))
        # Wire dispatched_by: per agent, which sources mention the name.
        result: list[Agent] = []
        for agent in agent_objs:
            if agent is None:
                continue
            mentions: list[Path] = []
            agent_name = agent.path.stem
            needle = agent_name.lower()
            for path, body in zip(dispatch_sources, source_bodies, strict=False):
                if body and needle in body.lower():
                    mentions.append(path)
            result.append(
                Agent(
                    path=agent.path,
                    frontmatter=agent.frontmatter,
                    body=agent.body,
                    line_count=agent.line_count,
                    dispatched_by=tuple(mentions),
                )
            )
        return result

    def scan_dispatch_sources(self) -> list[str]:
        return [
            body for body in (_safe_read_text(p) for p in self._dispatch_source_paths()) if body
        ]

    def _dispatch_source_paths(self) -> list[Path]:
        sources: list[Path] = []
        if self._skills_root.is_dir():
            sources.extend(sorted(self._skills_root.rglob("SKILL.md")))
        repo_root = self._agents_root.parent.parent
        for fname in ("AGENTS.md", "CLAUDE.md"):
            candidate = repo_root / fname
            if candidate.is_file():
                sources.append(candidate)
        return sources


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


_TOOLS_LIST_RE = re.compile(r"\[(.*)\]")


def _parse_agent_file(path: Path) -> Agent | None:
    text = _safe_read_text(path)
    if not text:
        return None
    fields, body = _parse_frontmatter(text)
    name = fields.get("name", path.stem).strip()
    description = fields.get("description", "").strip()
    model = fields.get("model")
    if model:
        model = model.strip().strip("'\"")
    raw_tools = fields.get("tools", "").strip()
    tools: tuple[str, ...] = ()
    if raw_tools:
        m = _TOOLS_LIST_RE.search(raw_tools)
        if m:
            inner = m.group(1)
            tools = tuple(t.strip().strip("'\"") for t in inner.split(",") if t.strip())
        else:
            tools = tuple(
                t.strip().strip("-").strip().strip("'\"")
                for t in raw_tools.splitlines()
                if t.strip()
            )
    extras = tuple(sorted(k for k in fields if k not in {"name", "description", "model", "tools"}))
    fm = AgentFrontmatter(
        name=name,
        description=description,
        model=model if model else None,
        tools=tools,
        extra_fields=extras,
    )
    return Agent(
        path=path,
        frontmatter=fm,
        body=body,
        line_count=text.count("\n") + 1,
        dispatched_by=(),
    )
