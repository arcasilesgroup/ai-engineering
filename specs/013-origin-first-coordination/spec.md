---
id: "013"
slug: origin-first-coordination
status: draft
date: 2026-08-15
ref: ""
supersedes: ""
---

# Writers coordinated by Git, not by another platform

Draft. Nothing may be implemented from it until a human approves it at an exact digest,
and approving it approves no plan. It derives from the P3 contract spec 010 froze, from
the P3 card of `.ai/reports/evolution-proposal/index.html`, and from that document's
unassigned section on origin-first multi-agent orchestration.

## Context and problem

Today this repository has one writer. That is not a habit, it is a written constraint.
`.ai/intent.md` carries it in `solution_intent.fixed_constraints`:

> "Until a separately approved P3 plan proves safe coordination, one writer owns
> repository changes."

`specs/011-surface-adapter-contract/plan.md` repeats it as a working rule: "There is
exactly one repository writer." Spec 010 states the widest version: before P3 is proven,
exactly one writer may edit the entire repository, regardless of worktree, branch, path
or task.

Two things are true about that constraint, and both matter.

**It is only a sentence.** `grep -rn fixed_constraints` over `src/`, `hooks/`, `policy/`,
`tests/` and `.github/` finds it in exactly one place that is not a test fixture:
`policy/intent-v1.schema.json`, where it is a required array of strings. The schema checks
that the array exists. Nothing reads what the strings say, and no guard, no check and no
workflow fails when a second writer starts. The rule holds because one person is running
one session, not because anything stops two.

**None of the machinery that would replace it exists.** Each of these was run, not assumed:

- `grep -rn claimed_paths src/ hooks/ policy/ .github/` returns nothing. The only hits in
  the tree are spec 010's own prose and a local variable of the same name in
  `tests/test_p0_completeness.py`.
- No `merge_group` trigger exists. `.github/workflows/` holds three files — `check.yml`,
  `install-matrix.yml`, `release.yml` — and `check.yml` triggers on push and pull_request
  only.
- Nothing in `src/ai_engineering/` pushes, claims a branch or opens a pull request. The
  ten verbs are `init`, `doctor`, `update`, `spec`, `decide`, `accept`, `audit`, `report`,
  `exception`, `uninstall`.
- The repository already asserts P3 has not started: `tests/test_p0_completeness.py` lists
  `merge_group` in `LATER_WAVES`, and the test goes red if the P0 contract names it.

Three things exist that are close enough to be mistaken for it, and are not it:

- `src/ai_engineering/spec_transaction.py` is a fail-closed native transaction with an
  authority-file lock, a no-replace publication and an explicit `Unsupported` when the host
  cannot give the guarantee. It is a correct claim primitive for one directory, on one
  filesystem, on one host. It never speaks to a remote.
- `hooks/change_scope_guard.py` blocks the fourth changed file on a branch with no plan.
  That is scope by count. `claimed_paths` is scope by declared path, and the guard cannot
  express it.
- `git-hooks/pre-push` runs gitleaks over exactly the commits being pushed and refuses a
  push to a protected branch. That is part of one checkpoint scan. The personal-data and
  machine-path checks live in `src/ai_engineering/acceptance_privacy.py` and run over
  acceptance records, not over a staged diff.

The harm of leaving it: every additional agent this product wants to govern is currently
governed by being forbidden. A second writer is not blocked, it is unmentioned. The first
time two of them run, the failure is a lost commit, and the record will say nothing
happened.

## Options considered

**A. The remote branch ref is the lock.** A task claims work by creating one remote branch
with a compare-and-swap push against the exact SHA it fetched. The loser's push is
rejected by the server. A draft pull request is created with the claim. `claimed_paths` is
declared in the plan, enforced by a guard at write time and again by CI over the pushed
diff. The dependency DAG is computed from declared overlaps, imports, lockfiles,
migrations, schemas and exclusive resources. The combined result is proved by a merge
queue, with `merge_group` added to `check.yml`.

*Gives:* the arbiter is a server this project already depends on, and a lost race produces
a rejected push, which is a receipt rather than a silence. *Costs:* the merge queue and
branch protection are platform settings, not files in this tree — `.github/` holds only
`workflows/`. *Risks:* a compare-and-swap is only as good as the fetch before it, and the
tempting repair for a stale SHA is a silent rebase. *Rules out:* any lock that lives on a
writer's own disk.

**B. Generalise the existing native transaction into a shared claim tree.** Extend
`spec_transaction.py`'s authority-file lock to a committed `claims/` directory, so claiming
is a no-replace create in the repository.

*Gives:* the code already exists, is fail-closed and is already tested. No new platform
dependency. *Costs:* two agents on two machines cannot see each other's file until one of
them pushes, so the lock resolves the collision after it has already happened. *Risks:* it
would read as coordination while providing none — a control that cannot fail, which is the
defect this repository exists to cure. *Rules out:* nothing, which is the problem.

## Decision

**Option A.** The deciding reason is not that origin is elegant. It is that option B cannot
lose a race: a create that only ever meets itself always succeeds, so it can never turn
anything red.

**Challenged once, honestly:** the strongest case against A is that it contradicts this
wave's own headline — coordinate writers with Git, not with another platform — because a
merge queue is a platform feature, not a Git feature. That case is real and it changes the
shape. The claim, the compare-and-swap push, the `claimed_paths` guard and the DAG are
plain Git and run against any remote. Only the final-combination proof uses the queue, and
where no queue is configured the wave reports the combined result UNPROVEN rather than
printing a green it did not earn.

### Three requirements this decision cannot state crisply

Written here rather than quietly sharpened, because inventing a crisp version of a vague
requirement is how a wave closes on work nobody specified.

**EP-034 and EP-195 — "semantic conflict".** Both require a fresh reviewer when one occurs.
Neither says what one is, and nothing in the tree detects one. Rule 12 turns a judgement
into a script after it has resolved the same way three times; this judgement has not
resolved once. No detector ships. The fresh reviewer stays a human ask.

**Spec 010 and EP-189 — "the checks affected by the actual diff".** `just check` runs
build, lint, typecheck, test, cover, security and counts — all of them, every time. There
is no map in this repository from a changed file to the checks it affects. Until such a map
exists with its own test, "affected checks" means `just check` in full.

**EP-195 — "council only after evidence that it improves the result".** No benchmark is
named, and no metric of "the result" exists. It stays a non-goal, not a plan.

## Normative contract

Reproduced in obligation from spec 010, which froze it. Where this section and spec 010
differ, spec 010 governs and this document is wrong.

- **Fetch before claim.** A claim carries the exact base SHA it fetched.
- **One task, one work item.** The work-item ID is opaque and non-personal.
- **One remote branch, one worktree, one writer.** Reviewers may be many; writers may not.
- **The claim is a compare-and-swap against that exact SHA.** A stale SHA is a refusal. It
  is never repaired by a rebase and never retried in a loop.
- **A draft pull request is created with the claim.** Draft means visible, not ready; it
  declares no readiness.
- **`claimed_paths` is enforced on every write and every commit**, and again by CI over the
  pushed diff. A write outside the claim is denied.
- **The DAG is deterministic.** Imports, lockfiles, migrations and schemas create explicit
  edges; exclusive resources serialize; a stable topological order is recorded; any cycle
  is `INCOMPLETE`.
- **Every checkpoint carries three receipts before it is published:** staged content
  scanned for secrets, personal data and machine paths; proof the diff stays inside
  `claimed_paths`; the checks the diff affects, executed. A checkpoint missing any of them
  cannot be claimed or published.
- **Every push is fast-forward or compare-and-swap against an exact SHA.** Never a bare
  force.
- **CI checks claims, the DAG, `just check` and evidence, and runs on `merge_group`** for
  the combined result.
- **No coordination record carries a prompt, reasoning, client, user, hostname, absolute
  path or provider payload.**
- **Versioned adversarial fixtures cover five cases:** a two-writer claim race with exactly
  one winner; a stale base SHA; an out-of-scope write; two disjoint claims integrating;
  overlapping claims blocked and visible at the merge gate. They execute against a real
  remote protocol. Until all pass, P3 is `INCOMPLETE` and the one-writer rule remains.

## What this closes

Each row must move to PROVEN by something that executes, or the wave does not close.
"Today" is the state measured in this tree on 2026-08-15, by the greps named in Context.

| Requirement | Today | What closes it |
|---|---|---|
| EP-030 | INCOMPLETE | scope held to real concurrency against origin and CI; no second flow, no second handler |
| EP-031, EP-182 | NO-EVIDENCE | one task, one remote branch with a CAS lease, one worktree, one writer; nothing in `src/` pushes today |
| EP-032, EP-187 | NO-EVIDENCE | a deterministic DAG over overlaps, imports, lockfiles, migrations, schemas and exclusive resources |
| EP-033, EP-185 | NO-EVIDENCE | `merge_group` added to `check.yml`, and a merge queue that proves the combined result |
| EP-034 | NO-EVIDENCE | an explicit refusal to claim a detector; the fresh reviewer stays a human ask, recorded as a non-goal |
| EP-035 | NO-EVIDENCE | authority envelope, council roles and budget/TTL recorded as non-goals with EP-173's own reopening trigger |
| EP-036 | NO-EVIDENCE | the claim-race fixture against a real remote, with exactly one winner and one refusal receipt |
| EP-037 | NO-EVIDENCE | the out-of-scope write fixture, denied by the guard and independently by CI |
| EP-038 | NO-EVIDENCE | the two-disjoint-claims fixture integrating through the queue with no conflict |
| EP-039 | NO-EVIDENCE | the overlapping-claims fixture, blocked and visible at the merge gate rather than merged |
| EP-040 | NO-EVIDENCE | an orchestration adversarial suite beside `tests/adversarial/run.py`, plus `merge_group: just check` |
| EP-179 | INCOMPLETE | a contract that names snapshot, checkpoint freshness and final-combination correctness as three separate things |
| EP-180 | INCOMPLETE | spec, plan and MADR carrying tasks, claimed paths, deps, base SHA and role |
| EP-181 | INCOMPLETE | Solution Intent stays durable context; no runtime coordination field is added to `policy/intent-v1.schema.json` |
| EP-183 | NO-EVIDENCE | a draft PR opened by the claim itself, carrying visibility and no readiness |
| EP-184 | NO-EVIDENCE | CI that checks claims, the DAG, `just check` and evidence on the branch |
| EP-186 | NO-EVIDENCE | fetch-before-claim, plan approval, PR-ready, merge queue and merge, automated |
| EP-188 | NO-EVIDENCE | a write guard on `claimed_paths` plus a CI check for duplicate claims; `change_scope_guard.py` counts files, not paths |
| EP-189 | INCOMPLETE | the checkpoint's three receipts; `git-hooks/pre-push` covers secrets only, and `acceptance_privacy.py` never sees a staged diff |
| EP-190 | NO-EVIDENCE | fast-forward or CAS push; `force-with-lease` appears nowhere in `src/`, `hooks/` or `.github/` |
| EP-191 | NON-GOAL | a fixture that fails if any background rebase or per-commit publication appears |
| EP-192 | NON-GOAL | a fixture that fails if an ownership store, heartbeat or TTL takeover appears |
| EP-193 | NON-GOAL | a fixture that fails when a coordination record carries any of the seven forbidden fields |
| EP-194 | NON-GOAL | the branch CAS owning the work item, with a hard path lease refused until a real collision is on record |
| EP-195 | NON-GOAL | council refused; no benchmark defines "improves the result", so nothing can prove it does |

## Non-goals

Each carries the document's own reasoning, not ours.

- **No background rebase, and no publishing every local commit** (EP-191). The document's
  premise is that continuous synchronisation promises a freshness no agent has: every agent
  works on a snapshot. The contract separates visibility from checkpoints instead.
- **No ownership database, no heartbeat, no automatic TTL takeover** (EP-192). The branch
  CAS owns the work item. A second store is a second source of truth that can disagree with
  the ref, and then something has to decide which one lied.
- **No hard path lease** (EP-194). `claimed_paths` and the DAG prevent overlaps; a lease
  arrives only after a real collision between orchestrators. There is none to point at.
- **No authority envelope, no council roles, no budget/TTL** (EP-035, EP-173). They stay out
  until an independent autonomous orchestrator consumes them *and* a test exists that the
  simple flow cannot pass. That is the trigger the document states, and it is written here
  so the deferral can end.
- **No council by default** (EP-195). A second model must find a measurable gap, not
  manufacture consensus, and no benchmark defines the improvement it would show.
- **No prompt, reasoning, client, user, hostname, absolute path or provider payload in any
  coordination record** (EP-193). The repository already holds this line for its other
  records: `acceptance_privacy.py` treats a machine path as a conclusive `FAIL` and refuses
  to guess on any other absolute path.
- **No lifting of the one-writer constraint by this document.** See the first risk.
- **Nothing from P1 (spec 011), P2, P4 or P5.**
- **No change to the guard/telemetry contract, the dispatcher, or the ten verbs.**

## Engineering criteria

- **KISS** — one lock, and it is a ref the server already arbitrates.
- **YAGNI** — the envelope, the council and the lease wait for the collision that needs them.
- **DRY** — the claim's base SHA is recorded once, in the claim, and read everywhere.
- **SOLID** — the claim states scope; the guard enforces it; CI re-derives it. None of the
  three decides for another.
- **TDD** — all five adversarial fixtures are red against a real remote before any
  coordination code exists.
- **Clean Code** — a stale SHA is a refusal with a reason, never a retry loop.
- **Clean Architecture** — coordination state lives in Git refs and CI, never in a new
  store; the hooks keep importing nothing but the standard library.

## Risks requiring resolution, not acceptance

- **This wave changes a constraint it cannot grant itself.** `.ai/intent.md` conditions the
  lift on "a separately approved P3 plan", and this is a spec, not a plan. A document that
  authorises its own escape from the rule that governs it is the exact self-authorisation
  the guards exist to stop. Resolution: the authority named in `.ai/intent.md` approves a P3
  plan at an exact digest, and the constraint text in `fixed_constraints` changes in the
  same commit that makes a second writer possible — not before, and not in this file. Until
  that commit exists, one writer, whatever this spec says.
- **A constraint nothing enforces.** Even after the text changes, `fixed_constraints` is
  read by no guard today. Resolution: whatever replaces the one-writer sentence arrives with
  a check that fails, or the sentence has been swapped for another sentence.
- **A claim that races on a stale fetch.** Compare-and-swap is only as good as the fetch
  before it. Resolution: the expected SHA is recorded in the claim and a mismatch is a
  refusal with no automatic repair, proved by the stale-SHA fixture.
- **A guard that cannot see a write.** A `claimed_paths` hook stops the tools the dispatcher
  covers; a shell redirect is outside it. `change_scope_guard.py` already has this ceiling.
  Resolution: the same claim check runs in CI over the pushed diff, so the branch fails even
  when the local guard never ran.
- **Correctness resting on settings that are not files.** The merge queue and branch
  protection live in platform configuration. `.github/` in this tree holds only `workflows/`,
  so `just check` cannot read them. Resolution: either `ai-eng doctor` reads the live
  configuration and fails when the queue is off, or the combined result reports UNPROVEN. A
  green that assumes a setting is the failure this product cures.
- **A suite that proves the fixture instead of the protocol.** Spec 010 requires the five
  cases to pass from the real remote protocol before P3 stops being `INCOMPLETE`.
  Resolution: the five fixtures execute against a real remote. A local fake proves only that
  the fake behaves.
- **"Semantic conflict" has no detector, and two requirements assume one.** EP-034 and
  EP-195 both depend on it. Resolution: none is invented here; the refusal is recorded, and
  if a detector is ever needed the evidence for it arrives first.

## Decisions

**D-013-01 — The remote branch ref is the lock, and there is no other lock.**
**Rationale:** a lock on a writer's own disk is invisible to the writer it should stop.
`spec_transaction.py`'s authority-file lock is fail-closed and correct for one directory on
one host; two agents on two machines never meet it.

**D-013-02 — A claim is a compare-and-swap against the exact fetched base SHA, and a stale
SHA is a refusal, never a rebase.**
**Rationale:** repairing a lost race hides it. EP-036 asks for exactly one winner, and a
winner is only meaningful if the loser produces a receipt.

**D-013-03 — `claimed_paths` is enforced twice: by a guard at write time and by CI over the
pushed diff.**
**Rationale:** `hooks/change_scope_guard.py` shows the ceiling of a hook-only control. The
branch is where every write ends up regardless of the tool that made it.

**D-013-04 — No semantic-conflict detector ships in this wave.**
**Rationale:** EP-034 and EP-195 both require one and neither defines it. Rule 12 promotes a
judgement to a script after it resolves the same way three times; this one has not resolved
once.

**D-013-05 — "The checks affected by the diff" means `just check` in full until a
file-to-check map exists with its own test.**
**Rationale:** the recipe runs everything today. A selector without a map is a way to skip a
check quietly, and the minutes it saves cost less than the check it drops.

**D-013-06 — The authority envelope, council roles and budget/TTL stay out, and the
condition for reopening them is written down here.**
**Rationale:** EP-173 states the trigger — an independent autonomous orchestrator that
consumes them, plus a test the simple flow cannot pass. A deferral without a written trigger
is a deferral that never ends.

**D-013-07 — This spec does not lift the one-writer constraint, and no plan derived from it
may lift it without a human approval recorded at an exact digest.**
**Rationale:** `.ai/intent.md` makes the lift conditional on an approved P3 plan. Letting
the spec that wants the change also grant it removes the only step where a person is
required.

**D-013-08 — Where no merge queue is configured, the combined result is UNPROVEN.**
**Rationale:** the alternative is inferring a green from the absence of a check, and
`.github/` cannot see the setting that would make the inference true.

## Accepted risks

None. Every risk above stays open until it is removed by work or accepted by an authorised
human with complete evidence and an expiry date.

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command.

- [ ] CI/CD — build, lint, test and security analysis on every push; deploy from the default branch
- [ ] Logs — structured JSON, one line per event, with level and service, to stdout
- [ ] Traces — only if this is our code and has more than one hop; no hop, no trace
- [ ] Errors — every uncaught exception leaves as a log with severity 17 and marks its span
- [ ] Health and data age — alive, age of the newest datum, and an independent recomputation
- [ ] External check — something outside the service verifies it and says what it could not check
- [ ] Second path — every published number recomputed by an independent route and compared
- [ ] Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI
