"""Lockstep Python implementation of the Tier 0 algorithm documented in
``.claude/skills/ai-research/handlers/tier0-local.md``.

The handler is a Markdown spec consumed by an LLM agent. To validate the
algorithm with deterministic tests, we keep this Python helper in sync with
the handler. If the handler changes, this module must follow (and vice versa).

Public API:

* :func:`slugify`   -- convert a query string to a URL-safe slug.
* :func:`tokenize_query` -- extract keyword tokens (3+ chars, no stopwords).
* :func:`tier0_local` -- run the full Tier 0 algorithm and return a result dict.

The helper takes ``repo_root`` so tests can point it at a fixture directory.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path

# --- Stopwords used by the keyword extractor ---------------------------------

_STOPWORDS: frozenset[str] = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "should",
        "could",
        "may",
        "might",
        "shall",
        "must",
        "can",
        "of",
        "to",
        "in",
        "on",
        "at",
        "by",
        "for",
        "with",
        "about",
        "as",
        "from",
        "and",
        "or",
        "but",
        "if",
        "then",
        "else",
        "what",
        "when",
        "where",
        "why",
        "how",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "i",
        "you",
        "we",
        "they",
        "them",
        "their",
        "our",
        "your",
        "my",
        "me",
        "us",
    }
)

# --- Result types ------------------------------------------------------------


@dataclass(frozen=True)
class Tier0Result:
    """Structured result of a Tier 0 local search."""

    research_artifact_hits: list[dict]
    lessons_hits: list[dict]
    prior_query_hits: list[dict]

    @property
    def total_hits(self) -> int:
        return (
            len(self.research_artifact_hits) + len(self.lessons_hits) + len(self.prior_query_hits)
        )

    @property
    def should_short_circuit(self) -> bool:
        """True when ≥3 local hits were found (handler short-circuit gate)."""
        return self.total_hits >= 3


# --- Slugification & tokenization -------------------------------------------


def slugify(text: str) -> str:
    """Convert a query string into a URL-safe topic slug.

    Algorithm:

    1. Lowercase.
    2. Replace any run of non-``[a-z0-9]`` chars with a single dash.
    3. Strip leading/trailing dashes.
    4. Truncate to 40 chars and strip a trailing dash again.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    slug = slug.strip("-")
    return slug[:40].rstrip("-")


def tokenize_query(query: str) -> list[str]:
    """Extract keyword tokens from a query, suitable for keyword grep.

    Returns lowercased tokens of length ≥3 that are not in the stopword list.
    Tokens may contain ``a-z0-9_-``.
    """
    return [
        word
        for word in re.findall(r"[a-z0-9][a-z0-9_\-]*", query.lower())
        if len(word) >= 3 and word not in _STOPWORDS
    ]


# --- Source 1: research artifact slug-similarity match -----------------------


_DATE_SUFFIX = re.compile(r"-\d{4}-\d{2}-\d{2}\.md$")


def _strip_date_suffix(filename: str) -> str:
    """Strip ``-YYYY-MM-DD.md`` from a filename and return the bare slug."""
    return _DATE_SUFFIX.sub("", filename)


def _read_artifact_title(path: Path) -> str | None:
    """Extract the ``query`` field from a research artifact's YAML frontmatter.

    Best-effort: if the file has no frontmatter or no ``query`` key, return
    ``None``. Avoids importing PyYAML for a minimal use case.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    if not text.startswith("---"):
        return None

    # Locate the closing fence (``\n---``) so we don't accidentally read body.
    end_marker = text.find("\n---", 3)
    if end_marker == -1:
        return None

    block = text[3:end_marker]
    for raw in block.splitlines():
        stripped = raw.strip()
        if stripped.startswith("query:"):
            value = stripped.split(":", 1)[1].strip()
            return value.strip("\"'")
    return None


def find_research_artifact_hits(
    query: str,
    research_dir: Path,
    *,
    min_similarity: float = 0.7,
) -> list[dict]:
    """Glob research artifacts and return ones with slug similarity ≥ threshold.

    Hits are sorted by descending similarity. ``research_dir`` is allowed to
    not exist -- the function returns an empty list in that case.
    """
    if not research_dir.is_dir():
        return []

    query_slug = slugify(query)
    if not query_slug:
        return []

    hits: list[dict] = []
    for artifact in sorted(research_dir.glob("*.md")):
        artifact_slug = _strip_date_suffix(artifact.name)
        if not artifact_slug:
            continue
        similarity = SequenceMatcher(None, query_slug, artifact_slug).ratio()
        if similarity >= min_similarity:
            hits.append(
                {
                    "path": artifact,
                    "slug": artifact_slug,
                    "similarity": round(similarity, 4),
                    "title": _read_artifact_title(artifact),
                }
            )

    hits.sort(key=lambda h: h["similarity"], reverse=True)
    return hits


# --- Source 2: keyword grep over LESSONS.md ----------------------------------


def find_lessons_hits(
    query: str,
    lessons_path: Path,
    *,
    max_hits: int = 10,
) -> list[dict]:
    """Grep ``LESSONS.md`` for any keyword from the query.

    Returns up to ``max_hits`` matches in file order. Each hit records the
    1-indexed line number, a 200-char snippet, and the first matching keyword.
    """
    if not lessons_path.is_file():
        return []

    keywords = tokenize_query(query)
    if not keywords:
        return []

    hits: list[dict] = []
    try:
        text = lessons_path.read_text(encoding="utf-8")
    except OSError:
        return []

    for index, line in enumerate(text.splitlines(), start=1):
        line_lower = line.lower()
        for keyword in keywords:
            if keyword in line_lower:
                hits.append(
                    {
                        "line_number": index,
                        "snippet": line.strip()[:200],
                        "keyword": keyword,
                    }
                )
                break  # one hit per line is enough
        if len(hits) >= max_hits:
            break
    return hits


# --- Source 3: prior /ai-research invocations from framework-events ----------


def _parse_event_timestamp(record: dict) -> datetime | None:
    """Best-effort timestamp parser. Accepts ``timestamp`` or ``ts``.

    Returns None if neither field is present or the value is malformed.
    """
    raw = record.get("timestamp") or record.get("ts")
    if not raw or not isinstance(raw, str):
        return None
    candidate = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def find_prior_query_hits(
    events_path: Path,
    *,
    now: datetime | None = None,
    lookback_days: int = 30,
) -> list[dict]:
    """Parse framework-events.ndjson and surface prior /ai-research events.

    Filters to ``kind == "skill_invoked"`` AND ``detail.skill == "ai-research"``
    AND timestamp within the last ``lookback_days`` days from ``now`` (default:
    current UTC time). Malformed JSON lines are skipped silently.
    """
    if not events_path.is_file():
        return []

    if now is None:
        now = datetime.now(tz=UTC)
    cutoff = now - timedelta(days=lookback_days)

    hits: list[dict] = []
    try:
        text = events_path.read_text(encoding="utf-8")
    except OSError:
        return []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        if record.get("kind") != "skill_invoked":
            continue
        detail = record.get("detail")
        if not isinstance(detail, dict):
            continue
        if detail.get("skill") != "ai-research":
            continue
        ts_parsed = _parse_event_timestamp(record)
        if ts_parsed is None or ts_parsed < cutoff:
            continue
        ts_raw = record.get("timestamp") or record.get("ts")
        hits.append({"timestamp": ts_raw, "detail": detail})
    return hits


# --- Top-level orchestrator --------------------------------------------------


def tier0_local(
    query: str,
    *,
    repo_root: Path,
    now: datetime | None = None,
    min_similarity: float = 0.7,
    lookback_days: int = 30,
) -> Tier0Result:
    """Run the full Tier 0 local-context search and return a Tier0Result.

    ``repo_root`` is the repository root the agent was invoked from. The
    helper resolves the three default local source paths under it:
    ``.ai-engineering/research/``, ``.ai-engineering/LESSONS.md``, and
    ``.ai-engineering/state/framework-events.ndjson``.
    """
    repo_root = Path(repo_root)
    research_dir = repo_root / ".ai-engineering" / "research"
    lessons_path = repo_root / ".ai-engineering" / "LESSONS.md"
    events_path = repo_root / ".ai-engineering" / "state" / "framework-events.ndjson"

    artifact_hits = find_research_artifact_hits(query, research_dir, min_similarity=min_similarity)
    lessons_hits = find_lessons_hits(query, lessons_path)
    prior_query_hits = find_prior_query_hits(events_path, now=now, lookback_days=lookback_days)

    return Tier0Result(
        research_artifact_hits=artifact_hits,
        lessons_hits=lessons_hits,
        prior_query_hits=prior_query_hits,
    )


__all__: Iterable[str] = (
    "Tier0Result",
    "find_lessons_hits",
    "find_prior_query_hits",
    "find_research_artifact_hits",
    "slugify",
    "tier0_local",
    "tokenize_query",
)
