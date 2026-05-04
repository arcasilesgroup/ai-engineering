---
name: ai-remember
description: Recall episodic and semantic memory across sessions. Trigger for 'do you remember', 'what did we do last time', 'recall', 'memory of', 'cross-session lookup', 'find prior episode', 'have we seen this before', 'recordar', 'memoria de'. Returns top-K results combining episodes (past sessions) and knowledge objects (lessons, decisions, instincts) ranked by decayed_importance times cosine similarity. Powered by spec-118 memory layer (sqlite-vec + fastembed).
model: sonnet
effort: low
color: cyan
argument-hint: "<query> [--kind=episode|knowledge] [--since=7d] [--top-k=10] [--debug]"
mode: agent
tags: [meta, memory, retrieval, cross-session]
tools: Bash
mirror_family: copilot-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-remember/SKILL.md
edit_policy: generated-do-not-edit
---


# Remember

## Purpose

Cross-session retrieval. Reads spec-118 memory layer (.ai-engineering/state/memory.db) and returns the top-K relevant prior episodes and knowledge objects ranked by decayed_importance * cosine_similarity.

Distinct from:
- /ai-instinct - consolidates observations into rules.
- /ai-learn - extracts lessons from merged PRs.

## When to Use

- User asks about prior work: "did we do this before", "what was the decision on X", "remember when".
- Before starting a task: pre-flight memory lookup for context.
- Mid-debug: search for similar past failures + recoveries.

## Process

1. Run: uv run ai-eng memory remember "<query>" --top-k 10 --json
2. Parse JSON. Each result has: target_kind, target_id, score, cosine, decayed_importance, summary, source_path.
3. Render compact bulleted list to user. Show top 5 by default; offer --debug to expand all with similarity scores.
4. If status is no_vectors, instruct: uv sync --extra memory && uv run ai-eng memory warmup.

## Output Format

remembered (count, durationms):
- [episode] id_short (score=s) -- summary truncated
- [lesson]  hash_short (score=s) -- text (source: path)

## Failure Modes

- no_vectors: sqlite-vec not loaded. Tell user to install with uv sync --extra memory.
- Empty results: corpus may be too small. Tell user to run ai-eng memory ingest --source all first.
- EmbeddingDimMismatch: model upgraded. Tell user to run ai-eng memory repair --rebuild-vectors.

## Integration

- Calls: ai-eng memory remember (canonical CLI at .ai-engineering/scripts/memory/cli.py).
- Reads: .ai-engineering/state/memory.db (gitignored, per-user).
- Audit: every retrieval emits memory_event/memory_retrieved to framework-events.ndjson.
