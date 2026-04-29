"""Lockstep Python implementation of the persistence algorithm documented in
``.claude/skills/ai-research/handlers/persist-artifact.md``.

The handler is a Markdown spec consumed by an LLM agent. To validate the
algorithm with deterministic tests, this helper mirrors it 1:1. If the
handler changes, this module must follow (and vice versa).

Public API:

* :class:`Source`         -- per-source dataclass (title/url/accessed_at).
* :class:`PersistInputs`  -- aggregated inputs to ``persist_artifact``.
* :func:`should_persist`  -- decide whether to write based on Tier 3 + flag.
* :func:`persist_artifact` -- write
  ``.ai-engineering/research/<slug>-<YYYY-MM-DD>.md`` and return its path.

Notes:

* Slug derivation re-uses the Tier 3 helper's ``topic_slug`` so the slug
  always matches the NotebookLM title.
* ``created_at`` is treated as ISO 8601; the leading ``YYYY-MM-DD`` segment
  forms the filename date stamp.
* No PyYAML import: the helper hand-formats the frontmatter so the
  produced text is byte-stable for tests.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from tests.integration._ai_research_tier3_helper import topic_slug

# --- Data structures ---------------------------------------------------------


@dataclass(frozen=True)
class Source:
    """A single source in the persisted artifact."""

    title: str
    url: str
    accessed_at: str


@dataclass(frozen=True)
class PersistInputs:
    """All fields needed to write a research artifact."""

    query: str
    depth: str
    tiers_invoked: list[int]
    sources_used: list[Source] = field(default_factory=list)
    notebook_id: str | None = None
    findings: str = ""
    created_at: str = ""


# --- T-3.9: persistence trigger ---------------------------------------------


def should_persist(*, tier3_invoked: bool, persist_flag: bool) -> bool:
    """Return ``True`` when the artifact must be written.

    Mirrors ``persist-artifact.md`` §"Trigger Conditions":

    * Tier 3 was invoked -> auto-persist.
    * ``--persist`` flag set -> persist regardless of tier.
    * Otherwise -> do not persist.
    """
    return tier3_invoked or persist_flag


# --- Frontmatter formatting --------------------------------------------------


def _format_tiers(tiers: Iterable[int]) -> str:
    return "[" + ", ".join(str(t) for t in tiers) + "]"


def _format_sources_block(sources: Iterable[Source]) -> str:
    """Hand-format ``sources_used`` as a YAML-style block list."""
    lines: list[str] = ["sources_used:"]
    for source in sources:
        lines.append(f"  - title: {source.title}")
        lines.append(f"    url: {source.url}")
        lines.append(f"    accessed_at: {source.accessed_at}")
    return "\n".join(lines)


def _format_frontmatter(inputs: PersistInputs, slug: str) -> str:
    notebook_value = inputs.notebook_id if inputs.notebook_id is not None else "null"
    parts = [
        "---",
        f'query: "{inputs.query}"',
        f"depth: {inputs.depth}",
        f"tiers_invoked: {_format_tiers(inputs.tiers_invoked)}",
        _format_sources_block(inputs.sources_used),
        f"notebook_id: {notebook_value}",
        f"created_at: {inputs.created_at}",
        f"slug: {slug}",
        "---",
    ]
    return "\n".join(parts)


# --- Body formatting ---------------------------------------------------------


def _format_sources_section(sources: Iterable[Source]) -> str:
    lines = ["## Sources"]
    for index, source in enumerate(sources, start=1):
        lines.append(f"{index}. {source.title} -- {source.url} (accessed {source.accessed_at})")
    return "\n".join(lines)


def _format_notebook_section(notebook_id: str | None) -> str:
    body = f"NotebookLM notebook: {notebook_id}" if notebook_id else "_(none)_"
    return f"## Notebook Reference\n{body}"


def _format_body(inputs: PersistInputs) -> str:
    return "\n\n".join(
        [
            f"## Question\n{inputs.query}",
            f"## Findings\n{inputs.findings}",
            _format_sources_section(inputs.sources_used),
            _format_notebook_section(inputs.notebook_id),
        ]
    )


# --- T-3.10: main entry point -----------------------------------------------


_RESEARCH_DIR = (".ai-engineering", "research")


def persist_artifact(inputs: PersistInputs, *, repo_root: Path) -> Path:
    """Write the research artifact and return its path.

    Output path: ``<repo_root>/.ai-engineering/research/<slug>-<YYYY-MM-DD>.md``.

    The directory is created if missing. Existing files at the same path
    are overwritten -- callers that wish to preserve history must rotate
    upstream.
    """
    slug = topic_slug(inputs.query)
    date_part = inputs.created_at[:10]
    filename = f"{slug}-{date_part}.md"

    research_dir = Path(repo_root)
    for segment in _RESEARCH_DIR:
        research_dir = research_dir / segment
    research_dir.mkdir(parents=True, exist_ok=True)

    path = research_dir / filename

    frontmatter = _format_frontmatter(inputs, slug)
    body = _format_body(inputs)
    content = f"{frontmatter}\n\n{body}\n"
    path.write_text(content, encoding="utf-8")
    return path


__all__: Iterable[str] = (
    "PersistInputs",
    "Source",
    "persist_artifact",
    "should_persist",
)
