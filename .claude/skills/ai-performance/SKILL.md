---
name: ai-performance
description: "Multi-stack performance scanning: N+1 queries, O(n^2) patterns, memory leaks, bundle size, I/O bottlenecks."
---


# Performance

## Purpose

Multi-stack performance scanner that detects issues via static analysis + heuristics. Identifies N+1 queries, O(n^2) algorithms, memory leaks, I/O inefficiency, and bundle size problems. Part of the verify agent's 7-mode assessment. Renamed from perf-review.

## Trigger

- Command: `/ai:verify performance`
- Context: performance audit, pre-release performance check, bottleneck investigation.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"performance"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## What it Detects (by stack)

| Category | Python | .NET | TypeScript/React | Rust | SQL |
|----------|--------|------|------------------|------|-----|
| N+1 Queries | SQLAlchemy lazy loads in loops | EF Core missing .Include() | Prisma nested queries in loops | Diesel lazy associations | Correlated subqueries |
| Memory Leaks | Unclosed handles, growing lists | Undisposed IDisposable | Detached DOM refs, closures | Unbounded Vec growth | Connection pool exhaustion |
| CPU Bottlenecks | O(n^2) loops, sync I/O in async | LINQ .ToList() mid-chain | Missing useMemo/useCallback | Unnecessary clones | Full table scans |
| I/O Inefficiency | Sequential HTTP (not gather) | Sequential await (not WhenAll) | Sequential fetch (not Promise.all) | Blocking I/O in async | No connection pooling |
| Bundle/Build | -- | -- | Bundle size, tree-shaking gaps | Binary size | -- |

## Procedure

### 1. Detect Stacks

Determine which checks apply by inspecting project markers:

| Marker file | Stack activated |
|-------------|-----------------|
| `pyproject.toml`, `requirements.txt` | Python |
| `*.csproj`, `*.sln` | .NET |
| `package.json`, `tsconfig.json` | TypeScript / React |
| `Cargo.toml` | Rust |
| `*.sql`, `migrations/`, `alembic/` | SQL |

Read the install-manifest (`ai-eng manifest show`) when available. Fall back to file-system detection otherwise. Activate all matching stacks -- projects are often polyglot.

### 2. Static Analysis

Run deterministic tooling first. Tool output is ground truth; never contradict it.

- **Python**: `ruff check --select PERF` -- PERF101 (unnecessary list wrapping), PERF203 (try-except in loop), PERF401 (append vs comprehension), PERF402 (function-scope import in hot path). Add `--select C4,SIM` for comprehension and simplification opportunities.
- **Rust**: `cargo clippy -- -W clippy::perf` -- unnecessary allocations, redundant clones, inefficient iterations.
- **TypeScript**: `eslint` with `no-await-in-loop`, `@typescript-eslint/no-floating-promises`. Scan `package.json` for heavy deps (moment, full lodash).
- **.NET**: `dotnet build -warnaserror` -- CA1827 (Count vs Any), CA1826 (First vs indexer), CA1829 (Length vs Count).

### 3. Heuristic Scan

After tools run, analyze code for patterns tools cannot detect:

- **N+1 detection**: ORM query calls inside `for`/`foreach`/`.map()` loops. Trace data flow -- flag lazy-loaded relationships accessed during iteration even when the query is implicit.
- **Sequential-to-parallel**: multiple independent `await` calls in sequence. If results are not interdependent, flag for `asyncio.gather()` / `Task.WhenAll()` / `Promise.all()`.
- **Algorithmic complexity**: nested loops over the same collection (O(n^2)) -- check if a set/dict lookup replaces the inner loop. Repeated `.find()`/`.filter()`/`.includes()` inside loops.
- **Memory**: unbounded list/array growth without size caps. Missing context managers (`with`) on handles. React: objects/arrays created inside render without memoization.
- **I/O in hot paths**: synchronous file/network I/O in async functions. String formatting in DEBUG-level log calls without level guard.

### 4. Score

Rate findings by real-world impact. Path criticality determines severity:

- **Critical path**: request handlers, API endpoints, data pipelines, render functions. Affects every user.
- **Warm path**: scheduled jobs, background workers, batch processes. Matters at scale.
- **Cold path**: CLI tools, one-time scripts, admin panels. Rarely matters.

Severity assignment:
- **Blocker**: N+1 in critical path, memory leak in long-running process, O(n^2) on unbounded input.
- **Critical**: sequential I/O where parallel is trivial, missing index on high-traffic query.
- **Major**: suboptimal algorithm in warm path, bundle size regression > 20%.
- **Minor**: micro-optimizations, cold-path inefficiencies. Report only when < 5 other findings.

### 5. Report

Produce the uniform scan output contract (Score, Verdict, Findings table, Signals, Gate Check -- see verify agent). Add a **Hot Spots** section ranking top 3 files by cumulative finding severity so remediation focuses on the highest-impact areas first.

Emit after report: `ai-eng signals emit scan_complete --actor=scan --detail='{"mode":"performance","score":<N>,"findings":{...}}'`

## Profiling Guidance

Static analysis finds patterns; profiling proves impact. Recommend profiling when a finding's real-world frequency is unknown, severity is disputed, or multiple findings compete for attention.

| Stack | Quick profile | Deep profile |
|-------|--------------|--------------|
| Python | `python -m cProfile -s cumtime script.py` | `py-spy record` for flamegraphs |
| .NET | `dotnet-trace collect` | JetBrains dotTrace, VS profiler |
| TypeScript | Chrome DevTools Performance tab | `clinic flame` (Node), `0x` |
| Rust | `cargo flamegraph` | `perf record` + `perf report` |
| SQL | `EXPLAIN ANALYZE` | pg_stat_statements, slow query log |

Do not profile during skill execution -- the skill is read-only. Provide profiling commands as remediation guidance.

## Common Anti-Patterns

### N+1 Query (SQLAlchemy)

```python
# BAD: lazy load triggers SELECT per user inside loop
for user in session.query(User).all():
    print(user.posts)
# GOOD: eager load -- 2 queries total
for user in session.query(User).options(joinedload(User.posts)).all():
    print(user.posts)
```

### Sequential to Parallel (async Python)

```python
# BAD: total time = sum of all requests
a = await client.get("/a")
b = await client.get("/b")
# GOOD: total time = max of all requests
a, b = await asyncio.gather(client.get("/a"), client.get("/b"))
```

### Inner Loop Lookup (any language)

```python
# BAD: O(n*m) -- linear scan per order
for order in orders:
    cust = next(c for c in customers if c.id == order.cid)
# GOOD: O(n+m) -- dict lookup
cust_map = {c.id: c for c in customers}
for order in orders:
    cust = cust_map[order.cid]
```

## When NOT to Use

- **Micro-benchmarking**: this skill detects structural anti-patterns, not nanosecond differences.
- **Cold-path-only code**: scripts and one-time migrations with small inputs gain nothing from perf scanning.
- **Pre-design phase**: scanning code that will be rewritten is wasted effort.
- **Profiling data exists**: if flamegraphs and metrics already point to the bottleneck, skip the scan.

## Output Contract

Follows uniform scan output contract (see verify agent). Required additions beyond the standard contract:
- **Hot Spots**: top 3 files ranked by cumulative finding severity.
- **Remediation**: every finding includes a concrete fix (eager load, gather, dict lookup, etc.), not just a description.

Use context:fork for isolated execution when performing heavy analysis.

$ARGUMENTS
