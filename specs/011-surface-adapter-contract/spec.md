---
id: "011"
slug: surface-adapter-contract
status: draft
date: 2026-08-15
ref: ""
supersedes: ""
---

# The surface adapter contract

Draft. It is in the tree because that is where a draft belongs — this repository has
no `drafts/`, and a spec carries `status: draft` from the first keystroke so that
`git clean` cannot eat it. Nothing may be implemented from it until a human approves
it at an exact digest, and approving it approves no plan.

Derived from the P1 contract spec 010 froze, and from the 28 requirements the interim
audit of `evolution-proposal` records as unmet in that area.

## Context and problem

This product claims to work across eight editors and command lines. A person installs it
once and expects the guards to be there in each of them. Today the product reports that
claim as a single word per surface — BLOCKS, INERT, UNPROVEN or ADVISES — and that one
word is being asked to answer three different questions at once:

1. **Discovery** — can the surface see the skills at all?
2. **Invocation** — can somebody actually run one from inside it?
3. **Enforcement** — has a denial ever executed there?

They are not the same question, and the answers routinely differ. A surface can list the
skills and be unable to run them. It can run them and never be able to stop anything. The
audit found this collapse in the code: `doctor.py:808-822` derives one coverage word per
row, and there is no invocation state anywhere (EP-019, EP-208).

Three specific facts make it worse, all of them measured rather than argued:

- **One surface has an executed denial from a wheel-installed artifact.** The install
  matrix denies `--no-verify` from the installed wheel on three operating systems
  (`install-matrix.yml:412-430`). Nothing equivalent runs for the other seven.
- **OpenCode's `proven = true` rests on prose.** The flag lives in `policy/surfaces.toml`
  and the plugin is only type-checked (`justfile:29`); no denial has executed there
  (EP-202). A flag a person typed is not a receipt.
- **Two surfaces the proposal describes as having native routers have none.** No `/ai-*`
  router is generated anywhere; `wiring.py:220` writes only the guard plugin (EP-014,
  EP-017, EP-205, EP-212). Codex has no `agents/openai.yaml` and nothing proves `/skills`
  discovery or `$ai-*` invocation (EP-015, EP-018, EP-213).

The harm of leaving it: the coverage block is the single screen a person reads to decide
whether they are protected. Today it can say a reassuring word about a surface where
nothing has ever been stopped. That is the exact failure this product exists to cure,
sitting inside the product's own report.

## Options considered

**A. One versioned adapter per surface, with three separate receipts.** Each surface gets
a declared adapter carrying its detection signal, its payload and lifecycle translations,
its heartbeat and its trust ceremony. Discovery, invocation and enforcement are recorded
as three states with three receipts, each earned by something that executed from a
wheel-installed artifact.

*Gives:* the coverage screen stops overstating, because a word can only be printed for a
state that has a receipt. Adding a surface becomes a declared adapter rather than a new
branch in the installer. *Costs:* eight adapters, and a receipt format per state. *Risks:*
the adapter surface area is where fail-open bugs hide — a translation that does not know a
value must fail closed, or a guard silently allows. *Rules out:* keeping `proven` as a
hand-set flag.

**B. Extend the existing table with more flags and keep one coverage word.** Add
`native_slash`, `skill_selector`, `command_adapter` and `invocation` to
`policy/surfaces.toml` (EP-013) and let doctor read them.

*Gives:* a much smaller change, no new format. *Costs:* the flags are still written by us
rather than earned. *Risks:* it reproduces the current defect with more columns — the
audit found `proven` is already a static bool (EP-147, EP-196), and four more static bools
do not make it a measurement. *Rules out:* nothing, which is the problem.

## Decision

**Option A.** The deciding reason is not that it is more complete: it is that option B
cannot fail. A flag we set cannot contradict us, so it can never turn the screen red, and
a report that cannot go red is a report nobody needs to read.

**Challenged once, honestly:** the strongest case against A is that eight adapters is a
large surface for a product whose whole doctrine is deletion, and seven of those surfaces
have never had a denial executed — so we would be building translation machinery for
capabilities we cannot yet prove exist. That case is real and it changes the shape: the
adapters land one at a time, each with its own executed denial before the next begins, and
a surface whose denial cannot be executed keeps `pi`/`zed`'s T3 answer — enforcement not
applicable — rather than acquiring an adapter that pretends.

## Normative contract

Reproduced in obligation from spec-010, which froze it. Where this section and spec-010
differ, spec-010 governs and this document is wrong.

The eight surface IDs remain `claude-code`, `opencode`, `codex-cli`, `cursor`,
`copilot-cli`, `vscode-copilot`, `pi` and `zed`. No context creates a new ID or inherits
another's proof. `pi` and `zed` stay instruction-only T3 until a stable native hook exists.

Each versioned adapter must:

- **detect only a native signal it did not write or cause.** Inability to detect is stated
  explicitly and is never self-fabricated presence.
- **preserve every foreign config entry and byte-significant value.** Unreadable or
  unmergeable foreign config causes no write and returns `INCOMPLETE`.
- **declare explicit bidirectional translations** for canonical payload fields, lifecycle
  event, exit meaning and allow/deny/error reply. An unknown value on either side fails
  closed.
- **expose a heartbeat distinguishing installed, loaded and recently observed**, and a
  trust ceremony where the surface requires trust.
- **prove negative behaviour from a wheel-installed artifact** — omitted adapter,
  malformed payload, guard crash and denial.
- **report discovery, invocation and enforcement as separate states and receipts.**

Visibility never proves invocation; invocation never proves denial. A T3 surface reports
enforcement not applicable and cannot earn denial proof.

OpenCode uses minimal global `/ai-*` routers pointing at the canonical installed skills.
Routers contain no copied body and carry a receipt, a content hash, a doctor check and an
exact uninstall. Codex restores wheel-owned links under `$HOME/.agents/skills`, proves both
`/skills` discovery and `$ai-*` invocation, and supplies the canonical `agents/openai.yaml`.
None of those artifacts alone proves enforcement.

## What this closes

The 28 requirements the interim audit records as unmet in this area. Each must move to
PROVEN by something that executes, or the wave does not close.

| Requirement | Today | What closes it |
|---|---|---|
| EP-012 | INCOMPLETE | every layer proved from the installed wheel, not only CLI/transaction/register |
| EP-013 | NO-EVIDENCE | the four adapter fields, earned rather than declared |
| EP-014, EP-017, EP-205, EP-212 | NO-EVIDENCE | generated `/ai-*` routers with receipt, hash, doctor check and uninstall |
| EP-015, EP-018, EP-213 | INCOMPLETE | Codex links, `agents/openai.yaml`, executed `/skills` and `$ai-*` proof |
| EP-016, EP-147, EP-277 | INCOMPLETE | a receipt carrying surface id, version, adapter version and deny protocol |
| EP-019, EP-208 | INCOMPLETE | discovery, invocation and enforcement as three states |
| EP-020 | INCOMPLETE | the `surface proof` command the exit criteria name and that does not exist |
| EP-081, EP-300, EP-301 | INCOMPLETE | one adapter contract, translations that fail closed |
| EP-196, EP-202 | INCOMPLETE | `proven` earned by an executed denial, never set by hand |
| EP-206, EP-209, EP-210, EP-214, EP-215 | INCOMPLETE | per-surface pinned versions and executed denials |
| EP-207 | NO-EVIDENCE | either a Codex-app row with real evidence, or an explicit refusal to claim one |
| EP-278, EP-283 | INCOMPLETE | p95 guard latency and per-surface denial-proof age |

## Non-goals

- No new surface ID, and no ninth surface.
- Nothing from P2 (craft, UX, governed reporting), P3 (coordination), P4 (security and
  release evidence) or P5 (external pilot).
- No change to the guard/telemetry contract, the dispatcher, or the record verbs.
- No adapter for a surface whose denial cannot be executed. It keeps the T3 answer.

## Engineering criteria

- **KISS** — one adapter shape for eight surfaces, not eight shapes.
- **YAGNI** — an adapter lands when its denial can execute, not before.
- **DRY** — the routers point at the canonical skills; no body is ever copied.
- **SOLID** — the adapter translates and does not decide; the guard decides.
- **TDD** — the negative fixture for each adapter is red before the adapter exists.
- **Clean Code** — a translation that meets an unknown value fails closed and says so.
- **Clean Architecture** — policy stays data in `policy/`, adapters stay code, and the
  hooks keep importing nothing but the standard library.

## Risks requiring resolution, not acceptance

- **A translation that fails open.** The adapter layer is where an allow can be
  manufactured from a value nobody recognised. Resolution: every translation table is
  closed, and the unknown branch is a tested denial rather than a default.
- **A receipt that outlives its truth.** A denial proved once and cached forever is the
  freshness defect the readiness work already met. Resolution: per-surface proof age, with
  a ceiling, reported next to the state.
- **Seven surfaces whose denial may not be executable at all.** If a surface has no hook
  that can stop a call, no adapter makes one. Resolution: the wave states which surfaces
  reached enforcement and which stayed T3, and never averages them into a total.

## Decisions

**D-011-01 — `proven` stops being a field anybody can write.**
**Rationale:** the audit measured OpenCode carrying `proven = true` with no denial ever
executed there. A flag that cannot contradict the person who set it is documentation.

**D-011-02 — adapters land one at a time, each behind its own executed denial.**
**Rationale:** the alternative is eight adapters landing together, of which seven are
unprovable, which is how a wave gets declared finished on work nobody could verify.

**D-011-03 — a surface that cannot deny reports enforcement not applicable.**
**Rationale:** spec-010 already froze this for `pi` and `zed`. Extending it as the general
answer keeps an unprovable surface from acquiring a reassuring word.

## Accepted risks

None. Every risk above stays open until removed or accepted by an authorised human with
complete evidence and an expiry date.

## Production-ready

Nothing gets a URL until every box is ticked by observed evidence.

- [ ] CI/CD — build, lint, test and security analysis on every push; deploy from the default branch
- [ ] Logs — structured JSON, one line per event, with level and service, to stdout
- [ ] Traces — only if this is our code and has more than one hop; no hop, no trace
- [ ] Errors — every uncaught exception leaves as a log with severity 17 and marks its span
- [ ] Health and data age — alive, age of newest datum, and independent recomputation
- [ ] External check — something outside the service verifies it and states its limits
- [ ] Second path — every published number is independently recomputed and compared
- [ ] Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI
