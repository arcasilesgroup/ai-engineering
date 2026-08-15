---
id: "015"
slug: pilot-without-instruments
status: draft
date: 2026-08-15
ref: ""
supersedes: ""
---

# The pilot without instruments

Draft. It sits in the tree because that is where a draft belongs, and it carries
`status: draft` from the first keystroke so `git clean` cannot eat it. Nothing may be
implemented from it until a human approves it at an exact digest.

Derived from the P5 contract spec 010 froze, and from the 47 requirements the evolution
proposal assigns to this wave and to the two sections that decide it: EP-053 to EP-061, the
thirteen deciding indicators EP-283 to EP-295, and the roadmap rule, admission gates and
prohibitions EP-296 to EP-320.

## Context and problem

P5 is the only wave whose exit criteria are about the product's effect rather than its
parts. It asks whether parallel work is better than sequential work, whether a fresh
reviewer catches more than a self-challenge, and whether somebody outside this repository
survives a schema change. It is also the wave with the fewest instruments, and the proposal
never equips it.

Four facts, each measured rather than argued.

**None of the thirteen deciding indicators exists by name.** Searching each of
`surface_proof_age`, `guard_p95_ms`, `mutation_score`, `adversarial_control`,
`otlp_rejected`, `spec_evidence`, `skill_eval_delta`, `repo_files_written`,
`intent_trace_coverage`, `a11y_critical_journey`, `aaa_exception_age`,
`coordination_overlap` and `report_payload_unknown` across `src/`, `hooks/`, `policy/`,
`tests/`, `justfile` and `.github/` returns zero hits for all thirteen. Eight have some
underlying mechanism; five have nothing at all. No name is published, and nothing computes
a number a person could read.

**Two of those mechanisms disagree with the indicator they would carry.**
`tests/test_contracts.py` has a check titled after p95 whose docstring says "p95 under
200 ms"; the assertion takes the middle of five sorted samples, which is the median,
against a bound four times the 50 ms the proposal states, on one dispatcher rather than per
surface. And `hooks/_otlp.py` already decides that a 2xx carrying rejected records is not
delivery — then `hooks/session.py` calls `send_tail` and discards the answer. The rule is
written, computed, and thrown away.

**Four of P5's nine requirements have no instrument anywhere.** EP-056 asks for defects,
cost, wait, conflicts, escalations and false greens; five of those six have no counter in
the tree, and the sixth — false greens — has three partial detectors
(`tests/anti_theatre.py`, the mutation floor, `readiness.py`'s INCOMPLETE) and no rate.
EP-058 requires an outside organisation and no organisation is named. EP-059 requires a
sequential baseline that was never taken, against parallel work that is P3 and unbuilt.
EP-061's second "command" — no silent retry, no shared writes, no unknown green — is an
assertion; there is no verb behind it, and the CLI's verb table lists ten, none of them
`benchmark`.

**The negative-control claim is nine-tenths untrue.** `tests/adversarial/run.py` registers
fourteen cases: thirteen attacks spread over nine gates, and exactly one negative control.
The seven recipes `just check` runs — build, lint, typecheck, test, cover, security, counts
— have no clean control of their own. EP-060 asks every gate to demonstrate one.

The harm of leaving it is not that P5 fails. It is that P5 will be reported as failed when
it is only unequipped, or — worse — that each vague requirement gets narrowed until the
repository already passes it, and the wave closes on work nobody did. Both are reporting
defects, and this product exists to refuse exactly that.

## Options considered

**A. Equip what can be equipped, and register the rest as `no-evidence` in data.** The
thirteen indicators and the fourteen prohibitions become rows in `policy/indicators.toml`.
A row carries either a command and a bound, or a `no_instrument` field with a reason and no
bound. One reader in `tests/` runs inside `just check` and fails closed, and no P5
completion claim passes while a `no_instrument` row stands.

*Gives:* the wave's unmeasured parts become visible in a diff instead of in prose, and the
distinction between "measured red" and "never measured" survives. *Costs:* one data file
and one reader; `tests/quality_gate.py` is the same shape and is small. *Risks:* a register
becomes a place to park work indefinitely. *Rules out:* closing P5 on a subset.

**B. Restate each vague requirement as the nearest thing the repository already measures.**
"Material reduction in defects" becomes the mutation score. "Every gate demonstrates a
negative control" becomes the one control the suite has. "An outside organisation" becomes
a synthetic consumer repository.

*Gives:* P5 closes, quickly, with commands that already run. *Costs:* nothing visible.
*Risks:* it cannot fail. Every restatement resolves in our favour, because we choose it
after seeing what passes. *Rules out:* nothing, which is the problem.

**C. Defer P5 entirely until P2, P3 and P4 have closed, and write nothing now.**

*Gives:* no speculative work. *Costs:* the wave arrives undefined at the moment somebody
needs it, and improvises. *Risks:* the improvisation is option B under time pressure.
*Rules out:* nothing.

## Decision

**Option A.** The deciding reason is the same one spec 011 gave against its own option B:
option B cannot fail. A criterion chosen after seeing which measurements pass is not a
criterion, and a wave that cannot go red is a wave nobody needs to run.

**Challenged once, honestly:** the strongest case against A is that a register of things we
cannot measure is a document, and this repository's doctrine is that a document which
cannot go red is not a gate. That case is real and it changes the shape. The register does
go red, and not on the missing number: it goes red on any P5 completion claim while a
`no_instrument` row stands, and on any row that acquires a bound without a command behind
it. The thing being gated is the claim, not the measurement.

## Normative contract

Reproduced in obligation from spec 010, which froze it. Where this section and spec 010
differ, spec 010 governs and this document is wrong.

P5 pilots the same `ai-spec` flow with and without human answers; compares sequential,
self-challenged and parallel work; measures defects, cost, wait, conflicts, escalations,
privacy and false greens; and exercises an external version upgrade without silent Intent
or MADR drift. A council, path lease or larger control plane may be proposed only by a
superseding specification if measured evidence shows Git and CI are insufficient. P5
completes only when parallel work improves elapsed time without worsening defects, cost,
privacy or conflicts and every claimed gate has an executed negative control.

To that this specification adds the register:

- **Each of the thirteen indicators is one row** naming the indicator, the command that
  computes it, its bound, and the wave that owns it.
- **A row nothing computes carries `no_instrument` with a reason and no bound.** A bound
  and `no_instrument` in the same row is an error, not a preference.
- **Each of the fourteen prohibitions is one row** naming what must not appear, and either
  the check that would find it or the reason no check can decide it.
- **A mechanism that exists is not an indicator that is published.** An indicator is
  published when the command in its row ran and printed the number.
- **No P5 completion claim passes while any row is `no_instrument`**, and the reader names
  every such row in its failure rather than printing a count.
- **The register is data in `policy/`; the reader is one file in `tests/`**, run by
  `just check`, failing closed. No hook learns either.

## What this closes

Each requirement must move to PROVEN by something that executes, or P5 does not close.
`NO-EVIDENCE` means no instrument exists and none is proposed in this specification.

| Requirement | Today | What closes it |
|---|---|---|
| EP-053 | NO-EVIDENCE | doctrine, not a number; D-015-06 records it as uncountable |
| EP-054 | INCOMPLETE | one fixture pair, with answers and without, compared by digest |
| EP-055 | NO-EVIDENCE | a labelled defect corpus and a stated bar; neither exists |
| EP-056 | NO-EVIDENCE | six named measures, five with no counter in the tree |
| EP-057 | INCOMPLETE | the prohibition half becomes a row; the threshold half does not |
| EP-058 | NO-EVIDENCE | a named external organisation, which does not exist yet |
| EP-059 | NO-EVIDENCE | a sequential baseline, once P3 exists to be parallel against |
| EP-060 | INCOMPLETE | one clean control per gate, or a reason a gate cannot have one |
| EP-061 | NO-EVIDENCE | three named checks in place of one assertion; no new verb |
| EP-283 | INCOMPLETE | per-surface denial-proof age, seven-day ceiling, on the receipt |
| EP-284 | INCOMPLETE | a real p95, per dispatcher, at the bound the proposal states |
| EP-285 | INCOMPLETE | the guard half publishes rows covered, never a percentage |
| EP-286 | INCOMPLETE | the control count reaching the gate count |
| EP-287 | INCOMPLETE | reading `send_tail`'s answer instead of dropping it |
| EP-288 | INCOMPLETE | `readiness.py` already decides it; the register publishes it |
| EP-289 | NO-EVIDENCE | no skill eval, no corpus, no baseline, no named approver |
| EP-290 | INCOMPLETE | doctor already refuses stray classes; the count is unpublished |
| EP-291 | NO-EVIDENCE | no BDD criterion exists, so coverage over them is undefined |
| EP-292 | NO-EVIDENCE | P2, and the critical journeys are enumerated nowhere |
| EP-293 | NO-EVIDENCE | `accept` carries owner and expiry; no AAA criterion exists to age |
| EP-294 | NO-EVIDENCE | P3: no claim, no `claimed_paths`, nothing to overlap |
| EP-295 | NO-EVIDENCE | `report.py` has no egress, so no allow-list can block one |
| EP-296 | PROVEN | spec 010 froze the order; nothing here changes it |
| EP-297 | INCOMPLETE | this specification is EP-297 applied to P5 |
| EP-298 | INCOMPLETE | precedent set once by spec 011; no check reads it |
| EP-299 | PROVEN | `contract.REPO_CEILING` bounds the tree and CI fails on the line after it |
| EP-300 | INCOMPLETE | one proof record, which is P1 work |
| EP-301 | INCOMPLETE | the guard/telemetry split holds; adapters do not exist yet |
| EP-302 | NO-EVIDENCE | nothing can check a test was red first; it stays a review criterion |
| EP-303 | NO-EVIDENCE | no BDD example exists, so nothing can require one first |
| EP-304 | PROVEN | `tests/test_contracts.py` refuses a non-stdlib import in `hooks/` |
| EP-305 | NO-EVIDENCE | judgement a review holds, which no gate can |
| EP-306 | INCOMPLETE | the chain counts denials per guard; only the window is missing |
| EP-307..EP-313, EP-315..EP-317 | INCOMPLETE | one register row each |
| EP-314, EP-319, EP-320 | NO-EVIDENCE | no script decides them; they stay prompts |
| EP-318 | PROVEN | `tests/test_contracts.py` — free text never leaves unhashed |

### The four requirements no instrument in this document reaches

Recorded here because a reader auditing the proposal will otherwise count them as
oversights, and an oversight and a refusal are different things.

**EP-056 — measure defects, cost, wait, conflicts, escalations and false greens.** Five of
the six have no counter anywhere. Escalations come closest: `hooks/_emit.py` closes the
event set at six classes, `bypassed` is one of them, and `report.py` already groups by
reason — so an escalation count is a query over a chain that exists. The other four are not
instrument gaps, they are subject gaps: there is no defect ledger, no cost accounting, no
wait clock, and conflicts require P3. *Proposed:* register `escalations` with the query that
computes it; register the other five `no_instrument`, each with its own reason.

**EP-058 — an outside organisation survives an Intent or MADR version change.** A synthetic
consumer repository upgraded across two schema versions is buildable today — `ai-eng update`
already runs forward migrations — and it proves the migration. It proves nothing about an
outside organisation, which is the only part of the requirement not already P0 work.
*Proposed:* `no_instrument`, reason "no external organisation is named". Naming one is a
decision for a person, not a cost this specification can estimate.

**EP-059 — parallel improves time without worsening defects, cost, privacy or conflicts.**
It depends on EP-056's five missing counters and on parallel work that P3 has not built.
*Proposed:* `no_instrument`, reason "no sequential baseline and no parallel execution".

**EP-061 — the exit commands.** The first, a sequential-versus-parallel benchmark, is a verb
this specification refuses to add: it would be an eleventh verb for a measurement that has
no baseline to compare against. The second is not a command. *Proposed:* record it as three
separate rows — `no_silent_retry`, `no_shared_writes`, `no_unknown_green` — of which only
the third has anything behind it today (`tests/anti_theatre.py` and `readiness.py`'s refusal
to tick a box without a fresh receipt). The other two are `no_instrument`.

## Non-goals

- No new verb, and specifically no `benchmark` verb.
- Nothing from P2, P3 or P4. The indicators those waves own are registered, not built.
- No change to the mutation floor, the coverage floor or the line ceiling.
- No external pilot arranged here. This names the requirement, not the organisation.
- No restatement of a vague requirement into one the repository already passes.

## Engineering criteria

- **KISS** — one data file and one reader, the shape `policy/quality-gate.toml` already
  uses for a rule that lives somewhere a diff cannot show.
- **YAGNI** — an indicator gets a bound when something computes it, and not before.
- **DRY** — thirteen indicators, one register; nothing records absence in a second place.
- **SOLID** — the register declares, the reader decides, and neither computes an indicator.
- **TDD** — the reader's red case is a row that gained a bound with nothing behind it.
- **BDD** — the four unequipped requirements have no observable example yet, which is
  exactly why they are `no-evidence` rather than restated.
- **Clean Code** — a row that cannot be measured says so in the file rather than being
  absent from it, because absence and zero read the same.
- **Clean Architecture** — the register is data in `policy/`, the reader is a test, and the
  hooks import nothing but the standard library.

## Risks requiring resolution, not acceptance

- **The register becomes a place to park work.** Thirteen `no_instrument` rows and nothing
  ever moves. Resolution: every row carries its reason, the reader names each standing row
  by name in its failure, and P5 cannot claim completion while one stands.
- **An indicator published from arithmetic nobody read.** `guard_p95_ms` is the live
  example: a check named after a percentile that computes a median. Resolution: each row
  names the command, and the reader runs it rather than trusting a stored number.
- **P5 closed on the parts that could be measured.** Resolution: the completion claim is one
  check across all thirteen indicators and all fourteen prohibitions, and it fails on any
  row that is not PROVEN — never on an average or a fraction.
- **The whole-tree mutation number is unknown.** The floor is stated in the `justfile` and
  the only stats file in the tree is from a scoped run, so it carries no whole-tree score.
  Resolution: a full `just mutate` before EP-285 is registered with any bound at all.

## Decisions

**D-015-01 — the thirteen indicators become rows in `policy/indicators.toml`, read by one
checker inside `just check`.**
**Rationale:** `policy/quality-gate.toml` and `tests/quality_gate.py` are already this exact
shape for this exact problem, and small. Thirteen bespoke gates would cost more and would
not make absence visible.

**D-015-02 — a row with no instrument carries `no_instrument` and a reason, and blocks any
P5 completion claim.**
**Rationale:** the failure mode is not the missing number; it is closing the wave without
it. A register that can only hold thresholds cannot record absence, so absence would live in
prose and go stale unnoticed.

**D-015-03 — `guard_p95_ms` is corrected before it is published.**
**Rationale:** the existing check measures the median of five samples against 200 ms under a
name and a docstring that both say p95. Publishing an indicator whose name disagrees with
its arithmetic is the defect the register exists to catch, committed by the register itself.

**D-015-04 — `otlp_rejected` is read where it is already computed.**
**Rationale:** `hooks/_otlp.py` already returns that a 2xx with rejected records is not
delivery, and `hooks/session.py` throws the answer away. This is the cheapest instrument in
the wave: one assignment and one place to report it.

**D-015-05 — the negative-control count is stated per gate and never averaged.**
**Rationale:** `tests/adversarial/run.py` registers thirteen attacks over nine guards and one
control, and the seven `just check` recipes have none. A single total would hide which gates
have never been shown to stay quiet.

**D-015-06 — EP-053, EP-055, EP-056, EP-058, EP-059 and EP-061 are classified `no-evidence`
and are not restated.**
**Rationale:** each is vague in a direction a rewrite would resolve in our favour. Narrowing
"reduces defects materially" to a number the suite already clears is how a wave is declared
finished on work nobody did.

**D-015-07 — EP-058 does not move until an external organisation is named.**
**Rationale:** a synthetic consumer upgraded across two schema versions proves the
migration, which is P0 work already owed. The only part of EP-058 that is new is the outside
organisation, and no synthetic repository substitutes for one.

**D-015-08 — the fourteen prohibitions become register rows; the three no script can decide
stay prompts with the reason recorded.**
**Rationale:** rule 12 says a judgement that always resolves the same way becomes a script,
and one that cannot fail closed stays a prompt with its reason written down. Eleven are
decidable by absence today. EP-314, EP-319 and EP-320 are not, and a gate that cannot go red
is worse than no gate.

## Accepted risks

None. Every risk above stays open until it is removed or accepted by an authorised human
with complete evidence and an expiry date.

## Production-ready

Nothing gets a URL until every box is ticked by observed evidence.

- [ ] CI/CD — build, lint, test and security analysis on every push; deploy from the default branch
- [ ] Logs — structured JSON, one line per event, with level and service, to stdout
- [ ] Traces — only if this is our code and has more than one hop; no hop, no trace
- [ ] Errors — every uncaught exception leaves as a log with severity 17 and marks its span
- [ ] Health and data age — alive, age of the newest datum, and an independent recomputation
- [ ] External check — something outside the service verifies it and says what it could not check
- [ ] Second path — every published number recomputed by an independent route and compared
- [ ] Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI
