# Handler: Tier 0 -- Local

## Purpose

Search the local context BEFORE escalating to any external source. Tier 0 is free, fast, and the primary mechanism by which prior research is reused across sessions. If Tier 0 produces ≥3 relevant hits, the agent MAY short-circuit and synthesize from local context alone.

The three local sources, in order:

1. Prior research artifacts in `.ai-engineering/research/*.md` -- topic-slug similarity match.
2. `.ai-engineering/LESSONS.md` -- keyword grep against learned patterns.
3. `.ai-engineering/state/framework-events.ndjson` -- last 30 days of `kind: skill_invoked` events filtered to `detail.skill == "ai-research"` to surface prior queries.

## Algorithm

This handler documents the algorithm that the agent (and the lockstep helper at `tests/integration/_ai_research_tier0_helper.py`) implements.

### Inputs

- `query` (string): the user's verbatim research question.
- `repo_root` (Path): repository root (defaults to the cwd the skill was invoked from).
- `now` (datetime, optional): current time, defaults to `datetime.now(tz=UTC)`. Injected by tests for determinism.
- `min_similarity` (float, default `0.7`): topic-slug similarity threshold for source 1.
- `lookback_days` (int, default `30`): event-log lookback window for source 3.

### Outputs

A `Tier0Result` shaped as:

```python
{
    "research_artifact_hits": [
        {"path": <Path>, "slug": <str>, "similarity": <float>, "title": <str|None>}
    ],
    "lessons_hits": [
        {"line_number": <int>, "snippet": <str>, "keyword": <str>}
    ],
    "prior_query_hits": [
        {"timestamp": <str>, "detail": <dict>}
    ],
    "total_hits": <int>,  # sum of len(hits) across the three sources
    "should_short_circuit": <bool>,  # total_hits >= 3
}
```

### Step 1 -- Topic-slug similarity over research artifacts

1. Compute `query_slug = slugify(query)` where:

   ```python
   import re
   def slugify(text: str) -> str:
       slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
       slug = slug.strip("-")
       return slug[:40].rstrip("-")
   ```

2. Glob `repo_root / ".ai-engineering" / "research" / "*.md"`. If the directory does not exist, return an empty list.
3. For each artifact, derive its `artifact_slug` by stripping the `-<YYYY-MM-DD>.md` suffix from the filename.
4. Compute similarity via `difflib.SequenceMatcher(None, query_slug, artifact_slug).ratio()`.
5. Keep artifacts where `similarity >= min_similarity`. Sort descending by similarity.
6. For each kept artifact, parse the YAML frontmatter (if any) and capture the `query` field as `title` for display purposes (best-effort; `None` if missing).

### Step 2 -- Keyword grep over LESSONS.md

1. Read `repo_root / ".ai-engineering" / "LESSONS.md"`. If the file does not exist, return an empty list.
2. Tokenize the query into keywords:

   ```python
   STOPWORDS = {
       "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
       "have", "has", "had", "do", "does", "did", "will", "would", "should",
       "could", "may", "might", "shall", "must", "can", "of", "to", "in",
       "on", "at", "by", "for", "with", "about", "as", "from", "and", "or",
       "but", "if", "then", "else", "what", "when", "where", "why", "how",
       "this", "that", "these", "those", "it", "its", "i", "you", "we",
       "they", "them", "their", "our", "your", "my", "me", "us",
   }
   keywords = [
       w for w in re.findall(r"[a-z0-9][a-z0-9_\-]*", query.lower())
       if len(w) >= 3 and w not in STOPWORDS
   ]
   ```

3. For each line in LESSONS.md (1-indexed), check if any keyword appears (case-insensitive substring match). If so, append `{"line_number": i, "snippet": line.strip()[:200], "keyword": <first matching keyword>}`.
4. Limit to a maximum of 10 hits to avoid context-window inflation.

### Step 3 -- Prior /ai-research invocations from framework-events.ndjson

1. Read `repo_root / ".ai-engineering" / "state" / "framework-events.ndjson"` line by line. If the file does not exist, return an empty list.
2. For each line, parse JSON (skip malformed lines silently).
3. Keep records where:
   - `record.get("kind") == "skill_invoked"`, AND
   - `record.get("detail", {}).get("skill") == "ai-research"`, AND
   - The record's timestamp (in `record.get("timestamp")` or `record.get("ts")`) is within the last `lookback_days` days from `now`.
4. Each kept record yields `{"timestamp": <str>, "detail": <dict>}`.

The timestamp parser accepts ISO 8601 with optional `Z` suffix and falls back gracefully if neither field is present (skipping the record).

### Step 4 -- Decide short-circuit

```python
total_hits = (
    len(research_artifact_hits)
    + len(lessons_hits)
    + len(prior_query_hits)
)
should_short_circuit = total_hits >= 3
```

The agent respects `should_short_circuit` as guidance; when `True`, it MAY synthesize directly from the local context rather than escalating to Tier 1+. When `False`, it MUST proceed to `tier1-free-mcps.md`.

## Implementation Reference

The Python lockstep implementation lives at `tests/integration/_ai_research_tier0_helper.py`. The helper and this handler stay in sync by design -- if either changes, the other must follow.

## Status

Phase 1 implementation. Phase 2 builds on this for Tier 1.
