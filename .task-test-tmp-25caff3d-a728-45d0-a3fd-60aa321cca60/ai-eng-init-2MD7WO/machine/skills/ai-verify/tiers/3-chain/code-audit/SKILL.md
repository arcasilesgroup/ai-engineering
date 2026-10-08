---
name: code-audit
description: Review code for correctness bugs, concurrency and lifecycle errors, type-safety holes, error handling gaps, API-contract breaks, and maintainability problems, with every finding gated on a concrete failure scenario. Use when asked to review code, check a diff or branch for bugs, look for problems before committing or opening a PR, or assess code quality.
---

# Code audit

Find defects that will actually bite.

Read `.claude/review/CONVENTIONS.md` first — stack detection, scope, severity,
the false-positive gate, and the report format. The **installed-version rule** is
the single most important constraint here: verify against the installed source
before calling any framework or library API misuse. Most false positives in a
review like this come from reviewing the code as if it were an older version of
its framework.

Security is out of scope — that is `security-audit`. Accessibility is
`a11y-audit`, performance is `perf-audit`. Overlap is fine; do not go hunting
outside your lane.

## What to look for

Ordered by how often each actually causes damage. Read files fully — the bug is
usually in the interaction between two functions, not inside one.

**1. Correctness**
Logic that produces a wrong result: off-by-one and boundary conditions, inverted
or short-circuiting conditionals, null/nil/undefined reaching a dereference,
zero-values hitting a truthiness check that meant "absent" (`0`, `""`, empty
collection, `false`), index and slice assumptions, integer division and rounding,
timezone and DST handling, float comparison, mutation of shared or aliased state,
and the classic mutate-while-iterating.

**2. Async, concurrency, and ordering**
Whatever this language's concurrency model is, the failure modes rhyme:
operations awaited in the wrong order or not awaited at all; a result used before
it is ready; two paths racing on shared state with no synchronization; a lock
held across a suspension point or acquired in inconsistent order (deadlock);
cancellation that leaves work half-done; retries that are not idempotent; a
callback that closes over a value it expects to still be current and is not.

**3. Resource and lifecycle management**
Anything acquired must be released on **every** path including the error path:
file handles, sockets, DB connections and transactions, locks, subscriptions,
timers, listeners, watchers, background tasks. Look for a `close`/`unsubscribe`/
`cancel` that exists on the happy path only. In UI frameworks this is the
component-teardown path; in servers it is the request-error path.

**4. Type safety and data modeling**
Escape hatches that hide a real mismatch: unchecked casts and assertions, `any`
or its equivalent leaking through an untyped boundary, non-null assertions on
values that can genuinely be null, suppression comments with no stated reason,
optional fields treated as guaranteed. Then the deeper version: **types that
model impossible states as valid** — an object where two fields must agree and
nothing enforces it, a status enum that permits combinations the domain forbids.

**5. Error handling**
Errors swallowed silently, or logged and then execution continues with bad state.
Failures with no user-visible or caller-visible outcome. Catch blocks so broad
they hide unrelated bugs. Thrown or returned values that are not the language's
error type. Missing loading and error states for async work. Error paths that
themselves can fail. Partial writes with no rollback.

**6. API and contract changes**
A signature, return shape, status code, event payload, or DB column changed
without updating every caller — check the callers, don't assume. Behavior changes
that are technically compatible but break a documented promise. Defaults changed
underneath existing users. Migrations that are not backwards compatible with the
currently deployed code.

**7. Framework-specific semantics**
Load the checks that match the stack you detected, and verify each against the
installed version before reporting:

- **Component UI frameworks** — stale closures over props/state; missing or
  dishonest dependency arrays; effects that should have been event handlers or
  derived values; missing cleanup; unstable list keys over reorderable data;
  state updates assumed to apply synchronously; derived state duplicated into
  local state and then desynced.
- **Server frameworks** — handler signatures, middleware ordering, request
  lifecycle, what runs per-request versus once at boot, and any server/client or
  trusted/untrusted module boundary the framework defines.
- **ORMs and data layers** — lazy loading outside a session, N+1 access patterns,
  transaction boundaries that do not cover the whole unit of work, and implicit
  connection reuse across concurrent tasks.

**8. Maintainability — only where the cost is concrete**
Duplicated logic that must be changed in lockstep (name both sites). Dead code
and unused exports. Functions doing several unrelated things at a level of
abstraction their name does not suggest. Names that mislead about behavior. Magic
values repeated across files.

Do **not** report style the linter owns, formatting, or subjective preferences.
"I would have structured this differently" is not a finding.

**9. Test coverage**
Check what the project actually has first (per `CONVENTIONS.md` §1). If a test
framework is configured, treat missing coverage of genuinely risky new logic —
non-obvious branching, data transforms, parsing, money, dates — as a finding, and
name the specific case that is untested. If no framework is configured, do not
fabricate failures for missing tests: note it once in `Not covered` and, if the
change is load-bearing, recommend adding a test setup. One note, not one per file.

## Method

1. Detect the stack and resolve scope per `CONVENTIONS.md`.
2. Read every changed file **completely**, plus the files it imports from and the
   files that call it. A diff read in isolation hides most real bugs.
3. Collect candidate findings while reading — do not judge yet.
4. **Verify pass.** For each candidate, go back to the code and try to disprove
   it. Check the caller's guarantees, the type, the guard clause you skimmed. If
   it depends on framework or library behavior, check the installed source now.
   Drop what does not survive.
5. Write the report.

Step 4 is the one that determines whether this review is worth reading. Do not
skip it, and do not compress it into "looks right".

## Report

Follow the output contract in `CONVENTIONS.md`. Write to
`.claude/reviews/code-audit-<stamp>.md`.

Every finding needs a **Fix** that names the specific change — "move the
allocation above the early return at line 30 so the deferred close always runs",
not "improve the resource handling". If the right fix is genuinely a judgment
call between two approaches, give both and say which you would pick and why.

Order findings by severity, then by blast radius. Do not pad the report to look
thorough — the `Checked and clean` section is where you demonstrate coverage.
