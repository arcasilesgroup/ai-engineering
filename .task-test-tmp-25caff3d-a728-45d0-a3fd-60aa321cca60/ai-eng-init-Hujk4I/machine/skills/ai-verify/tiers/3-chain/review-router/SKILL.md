---
name: review-router
description: Decide which review lanes a change actually needs, then run exactly those — instead of spawning the whole chain at every diff size. Reads the diff's shape and blast radius, maps the evidence to lanes (code, security, a11y, perf, design, build), estimates the cost, shows the routing decision, and executes it. Use when asked to "review this", "check this before I commit/merge", "is this ready", or "what should I run", and whenever a full review would cost more than the change is worth. Prefer this over full-review as the default entry point; full-review remains correct when the user explicitly asks for everything.
---

# Route the review

`full-review` spawns up to five reasoning agents that each read a real amount of code. On a
four-line diff that is more expensive than the change was, and the extra lanes return
nothing — which trains people to stop running reviews at all. This skill makes the lane
selection a decision based on evidence in the diff, rather than a habit.

You decide **which** lanes run and **how deep**. You perform no review yourself.

Two rules bound everything below:

- **Never route to zero lanes** on a diff that touches first-party source. If the change is
  genuinely trivial, that is `build-check` plus a targeted `code-audit`, not silence.
- **Name what you skipped and why**, in the output. A lane that was never run must never
  read as a lane that came back clean. This is the same failure `full-review` guards
  against when an agent dies.

## 1. Resolve scope and stack once

Per `.claude/review/CONVENTIONS.md` §1 and §3. Resolve both here, exactly once, and pass
the identical strings to every agent you spawn. Agents that resolve their own scope drift
apart and their findings stop being comparable — and in a monorepo they can legitimately
land on different stacks, which silently produces reviews of different things.

## 2. Measure the diff before you classify it

Get the shape of the change from git, not from a guess:

```bash
git diff <base>...HEAD --stat
git diff <base>...HEAD --name-only
```

Record: files changed, lines added/removed, and which subsystems are touched. Then subtract
everything `CONVENTIONS.md` §3 excludes — lockfiles, generated clients, build output,
vendored code. **A 4,000-line diff that is 3,900 lines of lockfile is a 100-line diff**,
and misreading that is the most common way a router over-spends.

If, after exclusions, the change touches no first-party source at all — docs only, config
comments, a lockfile refresh — say so and stop. Offer `build-check` alone. Do not spawn
reasoning agents to review prose.

## 3. Map evidence to lanes

A lane runs when the diff contains evidence that its class of defect is *possible*. The
signal is the file and the construct, not the topic of the commit message.

| Lane | Runs when the diff contains |
|---|---|
| `build-check` | **Always.** Fast, objective, and it gates everything else. |
| `code-audit` | **Default on.** Any first-party source change. Turn it off only when the diff is purely markup/styling with no logic. |
| `security-audit` | Auth, session, token, or crypto code · request handlers and route entry points · anything parsing external input (`JSON.parse` on a body, file upload, query params) · SQL or query construction · `env`/secrets/config plumbing · new network egress · permission checks · dependency additions |
| `a11y-audit` | Component or template files (`.tsx`, `.jsx`, `.vue`, `.svelte`, `.html`, templates) · forms, modals, menus, tabs, tooltips · `aria-*`, `role=`, `tabIndex`, keyboard handlers · anything that changes focus, color, or contrast |
| `perf-audit` | Query or fetch calls inside a loop or map · new N+1 shapes · list rendering and pagination · caching, memoization, revalidation changes · new dependencies in a client bundle · image/asset additions · anything on a hot path the build output flagged as growing |
| `design-check` | A spec exists **and** covers this change. Skip if there is no `design.md`/spec — the lane halts by design. Consider `spec-extract` instead, and say so. |
| `verify-feature` | The change completes a feature that was specified in conversation or in a spec — "did we build the right thing" is a different question from "is the code good", and no lane above asks it. |
| `second-opinion` | High-consequence and hard to falsify from inside your own reasoning: auth changes, money, migrations, anything you have already been iterating on in this session. Costs a fresh process with no cache reuse — save it for changes where being wrong is expensive. |

Evidence means you looked. Grepping the filename is enough to *consider* a lane; before
committing an expensive lane, open at least one of the files that triggered it and confirm
the construct is really there. A route based on a filename pattern that turns out to be a
test fixture is a wasted agent.

## 4. Set depth from size, not from ambition

After exclusions:

| Tier | Size | Route |
|---|---|---|
| **Trivial** | ≤ 20 lines, 1–2 files, no lane signals beyond code | `build-check` + `code-audit` scoped to the diff. Nothing else. |
| **Small** | ≤ 150 lines, one subsystem | `build-check` + `code-audit` + any lane with direct evidence (usually 0–1 more) |
| **Medium** | ≤ 600 lines, or two subsystems | The evidenced lanes, run in parallel. Typically 3. |
| **Large** | more than that, or a spec-backed feature, or a release branch | Hand the whole thing to `full-review` — that is what it is for. Do not reimplement its merge step here. |

Escalate a tier when the change touches auth, payments, migrations, or a public API
contract, regardless of line count. A twelve-line change to a permission check is not a
trivial change.

De-escalate when the diff is mechanical and uniform — a rename across forty files, a
codemod, a formatter pass. Forty files of the same edit is one edit; review the pattern
once and spot-check, rather than spawning lanes to read it forty times.

## 5. Show the decision before spending

Print the plan and the estimated cost, then run it. For **Medium** and above, ask first if
the user did not explicitly ask for a review — routing is cheap, agents are not.

```markdown
## Review plan — <scope>

**Diff:** 7 files, +182 / −34 (excluded: `pnpm-lock.yaml`, 3,908 lines)
**Stack:** <detected once, passed down>
**Tier:** Medium

| Lane | Run | Why |
|---|---|---|
| build-check | ✅ | always |
| code-audit | ✅ | 5 source files, new async control flow |
| security-audit | ✅ | `api/session.ts` — token handling changed |
| perf-audit | ✅ | query inside `map()` in `loadOrders` |
| a11y-audit | ⏭️ | no component or template files in the diff |
| design-check | ⏭️ | no spec found — run `spec-extract` if you want this lane |
| second-opinion | ⏭️ | not proposed: no money, migration or auth-model change |

**Estimated:** 3 reasoning agents + build. Roughly a third of a `full-review`.
```

Relative cost, for calibration: `build-check` is near-free; each reasoning lane is one
agent reading real code; `full-review` is up to five of those plus a merge;
`second-opinion` is a fresh process with no prompt-cache reuse (roughly $0.20–$1.00 a run).
On a subscription, a habit of full sweeps on small diffs is what burns the limit.

## 6. Execute

Run `build-check` yourself first, synchronously. It is decisive:

- **Fails on a compile or type error** → stop. Report it and ask whether to fix first.
  Reasoning review of code that does not compile is largely wasted; the file is about to
  change and half the findings evaporate with the fix.
- **Fails on lint only** → carry on, fold the findings in.
- **Passes** → carry on, and pass any size or timing output to the perf lane so it starts
  from a measurement rather than a guess.

Then spawn one `general-purpose` agent per selected lane, **all in a single message** so
they run concurrently, using the prompt shape from `full-review` §3 — same scope string,
same pre-detected stack, same "stay in your lane", same "write the report to disk and
return only the verdict, one line per finding, and the path". That last part is what keeps
this affordable.

If four or more lanes come out of step 3, stop routing and invoke `full-review` instead.
Its dedupe and global re-rank exist precisely because parallel lanes overlap at that width,
and reproducing a worse version of that merge here is the one way this skill makes things
worse rather than cheaper.

For one or two lanes, merge them yourself: read the report files, dedupe by `file:line`,
rank by real-world consequence rather than by each lane's internal severity, and write the
combined report per the conventions' output contract.

## 7. Report, including the road not taken

Whatever the outcome, the final report ends with the routing decision:

```markdown
## Not covered
- `a11y-audit` — not run: no UI files in scope
- `design-check` — not run: no spec exists
- Runtime behavior — no lane here runs the app; `feature-verify` does
```

If the user disagrees with a route, they can name a lane and you run it — an explicit
request always wins. Record the correction: a lane the user has had to ask for twice is a
signal that the mapping in §3 is wrong for this project, and it belongs in your
agent-rules file (`AGENTS.md` / `CLAUDE.md`) rather than in their memory.
