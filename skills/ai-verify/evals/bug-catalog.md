# What to plant

A pack that only contains obvious defects tells you your reviewer can read. The useful
packs are graded: a few gimmes to prove the thing is running at all, then the near-misses
that separate a working review skill from one that merely sounds plausible.

Aim for a spread across three tiers and at least three lanes.

---

## Tier 1 — proves it is running

If these are missed, nothing else in the score means anything. Two per pack is plenty.

| Class | Edit | Lane |
|---|---|---|
| Inverted condition | flip a `!` or swap `===`/`!==` on a guard | code-audit |
| Null deref | remove a `?.` or an early return on a value that is genuinely nullable | code-audit |
| Off-by-one | `<=` for `<`, `+ 1` on a slice bound | code-audit |
| Unparameterised query | interpolate user input into SQL/NoSQL query text | security-audit |
| Missing accessible name | delete the `aria-label` from an icon-only control | a11y-audit |
| Query in a loop | replace a batched fetch with a per-item `await` | perf-audit |

## Tier 2 — the near-misses

These read as correct code. They are where a review skill earns its cost, and where a
cheaper model quietly stops finding things.

| Class | Edit | Why it hides |
|---|---|---|
| Authorization downgrade | `requireAdmin` → `requireUser`; owner check → authenticated check | Both lines are a permission check. Only one is the right one. |
| Wrong role compared | `role !== "admin"` → `role === "viewer"` | Still a role check, still throws for some users, passes for the wrong ones. |
| Check-then-write race | move a write outside the transaction or the lock it was inside | The code still checks. It checks at the wrong time. |
| Missing cache invalidation | delete the `revalidate`/`invalidate` after a write | Nothing errors. Readers just get stale data forever. |
| Client-side-only validation | delete the server-side re-check, keep the form validation | The happy path is identical, and every test passes. |
| Swallowed error | `catch { return null }` where it used to rethrow | Failure becomes an empty state instead of an error. |
| Unawaited promise | drop an `await` on a call whose result is not used | Works in dev, drops writes under load. |
| Silent truncation | lower a limit, or `slice` a result set without saying so | Output looks complete. It is not. |
| Near-miss substitution | implement an adjacent requirement — a fixed price ID instead of a percentage discount | Both are "pricing". Only one was asked for. This one belongs to `verify-feature`, not to a code lane. |

Plant at least two Tier 2 defects. A pack that scores 100% and contains none of them has
told you almost nothing.

## Tier 3 — the traps

These test **precision**, not recall. They are correct code that pattern-matches as a
defect, and a reviewer that flags them is telling you its false-positive gate is decorative.

Record them in the pack with `"trap": true` and no `replace` — or simply leave the code
alone and remember what you are watching for. They should appear in the scorer's
adjudication list, where you mark them `noise`.

- A `dangerouslySetInnerHTML` / `innerHTML` on a value that is genuinely a constant
- A raw SQL string with no interpolation at all
- A loop containing an `await` on something that is **not** I/O
- A missing `try/catch` where the caller demonstrably handles it
- A framework API that is correct in the installed version and looked wrong two versions
  ago — the single best test of whether `CONVENTIONS.md` §2 is actually being applied
- A pattern used consistently across the codebase that ships and works

That last pair is worth building a whole pack around if your project uses a fast-moving
dependency. It is the highest-volume source of false positives in real reviews, and no
amount of recall makes up for a reviewer that flags working code every run.

---

## Coverage by lane

One or two defects per lane you actually installed. Do not plant for lanes you do not run.

| Lane | Plant |
|---|---|
| `code-audit` | inverted condition, off-by-one, swallowed error, unawaited promise, lifecycle/cleanup removal |
| `security-audit` | authorization downgrade, injection, secret in source, missing server-side re-check, unbounded input reaching a dangerous sink |
| `a11y-audit` | removed accessible name, keyboard trap, focus never moved to a dialog, contrast dropped below AA, heading level skipped |
| `perf-audit` | N+1, removed cache, unbounded payload, blocking work on a hot path, a heavy dependency added to a client bundle |
| `design-check` | delete one requirement's implementation entirely; implement a requirement *differently* than the spec states |
| `verify-feature` | drop a requirement from the middle of a feature; add something nobody asked for |
| `build-check` | a real type error — it should be the only lane that reports it, and it should stop the chain |

---

## Rules for a defect worth planting

**One edit, one defect.** A bug that changes five things scores ambiguously — you cannot
tell which part the reviewer saw.

**It must be genuinely wrong.** If you find yourself arguing that the planted version is
defensible, it is a style opinion, and a reviewer that skips it is right.

**It must be reachable.** A defect in dead code is not a defect, and a good reviewer will
correctly ignore it. That is a bug in your pack, not in the skill.

**Vary severity.** A pack of six criticals does not tell you whether the severity bar in
`CONVENTIONS.md` §4 is being applied. Include something that should honestly come back as
Low — and check that it did not come back as High.

**Steal from your own history.** `git log --grep=fix` is the best pack generator you have.
Defects you actually shipped are the distribution your reviewer needs to cover; defects you
invented are the distribution you already know how to avoid.
