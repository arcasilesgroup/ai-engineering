---
name: perf-scanner
schedule: "0 15 * * *"
environment: worktree
layer: scanner
requires: [gh]
---

# Performance Scanner

## Prompt

Scan the codebase for common performance anti-patterns. Create a GitHub Issue for each new finding.

1. Search for N+1 query patterns: loops containing database/API calls.
2. Search for O(n²) patterns: nested loops over the same collection.
3. Search for memory leak patterns: growing collections without bounds.
4. Search for I/O bottlenecks: synchronous I/O in hot paths.
5. Search for unbounded allocations: `list.append()` in loops without size limits.

For each finding:
- Check if a GitHub Issue already exists.
- If not, create one with labels `performance`, `needs-triage`.
- Title format: `[perf] <pattern>: <file>:<line>`
- Body: code snippet, explanation of the anti-pattern, suggested fix approach.
- Priority: `p2-high` for hot path issues, `p3-normal` for cold path.

## Context

- Uses: perf skill.
- Reads: source code in `src/` and `tests/`.

## Safety

- Read-only mode: detect and create issues only.
- Do NOT modify source code.
- Maximum 10 issues per run.
- Skip findings that already have open issues.
- False positive rate is expected — label findings as `needs-review`.
