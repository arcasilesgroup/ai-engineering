---
name: perf-audit
description: Audit performance — payload and bundle size, data-access patterns and waterfalls, caching, assets, and compute cost — reporting only issues with a measurable, user-visible cost. Use when asked about performance, slow loads, slow queries, slow renders, bundle size, memory use, Core Web Vitals, or optimizing the app.
---

# Performance audit

Find work the system does that it does not need to do, where the cost is
**user-visible**. Micro-optimizations that save a microsecond are not findings;
120KB of JavaScript shipped to render static text is, and so is an N+1 query that
turns one page load into 200 round trips.

Read `.claude/review/CONVENTIONS.md` first — stack detection, scope,
false-positive gate, report format. The **installed-version rule** matters
especially here: caching semantics, lazy-loading defaults, and compiler behavior
change between versions, and a stale mental model produces confident, wrong
findings. Confirm the installed version's default is not already doing what you
are about to recommend.

## 1. Find the biggest cost centre first

Do not run a fixed checklist top to bottom. Establish what kind of system this is
and go where the cost actually lives:

| System | Usually dominated by |
|---|---|
| Client-heavy web app | shipped bytes, hydration, render cost |
| Server-rendered app | data fetching, cache correctness, time to first byte |
| API / service | database access patterns, serialization, connection handling |
| Batch / data pipeline | I/O per record, memory footprint, algorithmic complexity |
| CLI / desktop | startup time, blocking I/O on the main path |

Order the work by expected impact for that shape, and say in the report which
you assessed and why.

## 2. Universal checks

These apply regardless of stack, in rough order of how often they matter.

**1. Data access — the most common real finding in anything with a database**
- **N+1 patterns** — a query inside a loop over results of another query. Look
  for lazy relation access inside an iteration.
- **Waterfalls** — sequential awaits with no data dependency between them. They
  should run concurrently.
- **Over-fetching** — selecting every column to use two, loading a whole
  collection to count it, fetching a relation nobody reads.
- **Missing indexes** on columns used in filters, joins, and sorts. Check the
  schema and migrations against the queries the change introduces.
- **Unbounded result sets** — no limit, no pagination, "there will never be many
  rows" as an unstated assumption.
- The same data fetched several times in one request.

**2. Caching**
Work repeated that could be computed once — per request, per process, or across
requests. Cache keys that are too broad (serving stale or wrong data — that is a
correctness bug, report it as High) or too narrow (never hitting). Caches with no
eviction policy. Verify what the framework caches by default at the installed
version before adding or removing anything.

**3. Payload size**
What crosses the wire, in bytes. For web clients: the bundle. Importing a whole
library for one function; barrel-file imports that pull an entire index;
duplicate dependencies at different versions; heavy modules loaded eagerly that
could be loaded on interaction or when scrolled into view (editors, charts, maps,
date/locale data). For APIs: response bodies containing fields nobody consumes,
and missing compression.

**4. Assets**
Images served unoptimized, unsized, or without lazy loading below the fold.
Missing priority hints on the largest above-the-fold image — or priority applied
to many images, which defeats it. Fonts: too many weights and subsets, and
blocking loads. Large files served from the app instead of a CDN.

**5. Compute cost**
Expensive work on a hot path that could be hoisted, memoized, or moved to a
background job. Accidentally quadratic loops. Repeated recompilation — regexes,
templates, schema parsers — inside a function that runs per item. Synchronous
blocking I/O on an event loop or request thread. Unbounded memory growth:
accumulating collections, unreleased references, whole files read into memory
that could stream.

**6. Startup and connection handling**
Work at import/boot time that could be lazy. Connection pools created per request
instead of once. Missing keep-alive on outbound HTTP.

## 3. Stack-specific checks

Load the ones matching what you detected, and verify each against the installed
version.

**Component UI frameworks** — the server/client boundary is usually the
highest-leverage check where one exists: a client-boundary marker high in the
tree drags subtrees onto the client that could have stayed server-rendered, and
every module it imports joins the client bundle. Push the boundary down to the
leaf that needs interactivity. Also: large data serialized across the boundary as
props, unstable object/array/function props defeating memoization, effects that
write state and immediately cause another render, and long lists rendered without
virtualization (thousands of rows, not dozens).

Do not report missing memoization by default. Several modern frameworks memoize
automatically at the compiler level, and unnecessary memoization has its own
cost. Report it only where the memoized work is genuinely expensive **and** you
can point at what re-renders and how often.

**Server-rendered frameworks** — routes forced dynamic that did not need to be;
a slow segment with no streaming or partial rendering, so the whole response
blocks on the slowest query; data fetched after hydration that could have been
fetched during render, costing a full extra round trip.

**Interpreted languages** — hot loops in the interpreted layer that a library
call would vectorize or push into native code.

**Compiled languages** — allocation in hot loops, copies where a reference would
do, and bounds checks in a measured hot path.

## 4. Measure rather than guess

A number beats an adjective. It is the difference between a report someone acts
on and one they argue with. Where the project makes it cheap:

- Build output that prints per-route or per-bundle sizes — read it, quote it
- A bundle analyzer, if configured
- `EXPLAIN` / query plan for a suspect query
- An existing benchmark suite
- Timing around a suspect block

If you could not measure, say `estimated` and state the reasoning. Never present
an estimate as a measurement.

## 5. Method

1. Detect the stack and resolve scope per `CONVENTIONS.md`.
2. Classify the system (§1) and pick where to look first.
3. Trace the critical path end to end: what happens between the request arriving
   and the user seeing something useful, in order, and what blocks.
4. Take the measurements that are cheap to take (§4).
5. **Verify pass.** For every candidate, state the cost: bytes, a round trip, a
   blocked paint, a query count, a memory figure. If you cannot, drop it — "this
   could be faster" with no magnitude is not a finding. Confirm the installed
   version's default is not already handling it.
6. Report.

## 6. Report

Follow the output contract in `CONVENTIONS.md`. Write to
`.claude/reviews/perf-audit-<stamp>.md`.

Each finding must quantify the cost, and say whether it is measured or estimated:

- **[HIGH] Comment list issues one query per comment**
- **Where:** `src/api/thread.ts:64`
- **Trigger:** any thread view; scales with comment count
- **Consequence:** 1 + N queries — 201 round trips on a 200-comment thread,
  ~1.8s server time (measured, query log)
- **Fix:** eager-load the `author` relation in the initial query

Severity by user-visible impact: **Critical** = unusable on a normal connection
or device. **High** = a clear delay on the primary path. **Medium** = measurable
but secondary. **Low** = worth doing when nearby.

Rank findings by **impact per unit of effort**, and lead with the one change that
buys the most. If the system is genuinely fine — and for a small one it often is
— say `PASS` and do not manufacture work.
