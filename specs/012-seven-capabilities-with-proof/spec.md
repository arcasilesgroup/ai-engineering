---
id: "012"
slug: seven-capabilities-with-proof
status: draft
date: 2026-08-15
ref: ""
supersedes: ""
---

# Seven capabilities, and the corpus that exists before each one

Draft. It carries `status: draft` from the first keystroke and lives in `specs/` because
this repository has no `drafts/` — a draft in an uncommitted directory is what
`git clean -ndx` eats. Nothing may be built from it until a human approves it at an exact
digest, and approving it approves no plan.

Derived from the P2 wave of `.ai/reports/evolution-proposal/index.html`, its CLI and
`ai-design` sections, and its fifteen-skill catalogue; and from the extraction that
numbers it: EP-021..EP-029, EP-103..EP-134, EP-219..EP-236 and EP-237..EP-257.

## Context and problem

The catalogue is meant to go from eight capabilities to fifteen in this wave. Seven files
would nearly double the surface a person routes through, and today nothing in this
repository can tell a good one from a plausible one.

These are the measurements, not the argument:

- **The declaration is complete and the executor is not.** `policy/capabilities.toml`
  declares fifteen capability ids across eighteen modes, each mode carrying `read_roots`,
  `write_roots`, `exec_allowlist`, `network`, `secrets` and `human_gate` plus its
  enforcement list and proof requirements. `capability.preflight` validates all of it and
  then returns `INCOMPLETE` on every branch: a fully declared, fully in-scope action still
  ends at `CAPABILITY_ENFORCEMENT_UNAVAILABLE`, because no executor owns the operation.
  `ai-eng doctor` assertion 23 now reports that state; building the executor is P4 work,
  and this wave must not read its absence as a reason to widen the catalogue.
- **Seven of the fifteen have no file.** `.agents/skills/` holds `ai-debug`, `ai-explore`,
  `ai-note`, `ai-plan`, `ai-research`, `ai-review`, `ai-ship` and `ai-spec`. `ai-build`,
  `ai-design`, `ai-animation`, `ai-security`, `ai-test`, `ai-verify` and `ai-report` are
  declared and absent (EP-098).
- **The admission rule the proposal states has no check.** `contract.audit_one` checks the
  frontmatter fields, the line ceiling in `contract.CEILING`, the description length, the
  "Not for" clause and a jargon list. It does not look for a corpus, for a case where the
  skill must refuse, or for any routing evidence. So EP-100 and EP-101 — a skill enters
  because it has a distinguishable trigger, its own artefact, a refusal case and a routing
  evaluation — are prose that `just check` cannot fail on.
- **One of the seven is already promising itself in the product's output.**
  `src/ai_engineering/report.py` prints that `report issue` is planned for P2 and is not
  implemented, and returns `INCOMPLETE`. That is honest today and becomes a lie the moment
  anything half-builds it.
- **`ai-review` has five lenses and neither of the two this wave needs.**
  `.agents/skills/ai-review/references/` holds `correctness`, `security`, `performance`,
  `testing` and `compatibility`. There is no frontend lens and no motion lens (EP-022,
  EP-125, EP-251).
- **The CLI half of this wave is further along than the wave text assumes.** `cli.py`
  already emits the exact twelve-field JSON v1 envelope EP-232 names — `schema_version`,
  `command`, `operation_id`, `started_at`, `finished_at`, `outcome`, `summary`, `changes`,
  `checks`, `remaining`, `next_actions`, `error`. `ui.will`, `ui.running` (which raises
  rather than print an uncounted step) and `ui.cure` (which raises on a bypass word) cover
  EP-222, EP-223 and EP-226. `ui.plain` honours `NO_COLOR` and `TERM=dumb`.
  `policy/outcome-v1.schema.json` pins the seven outcomes, the exit codes, and
  `unknown_normalizes_to: INCOMPLETE`. Two things are genuinely missing: `--debug` and
  `--non-interactive` appear nowhere in `src/`, `hooks/`, `tests/` or `policy/` (EP-233,
  EP-236).
- **EP-257 is already done and should stop being counted.** The guard is
  `hooks/change_scope_guard.py`. There is no `design_gate.py`; P0 hard-renamed it with no
  alias, the CHANGELOG records it, and `tests/test_hooks.py` pins the rename by name.

The harm of leaving it: seven skill files land, each one readable, none of them
falsifiable, and the catalogue that AGENTS.md says ended at 528 files last time starts
again — this time inside the product that exists to stop exactly that.

## Options considered

**A. Admission gate first, then one capability per change.** `contract.audit_one` gains two
checks: a skill directory must carry a positive corpus and a negative corpus holding at
least one case where the capability must refuse. No skill file lands before both exist.
Capabilities land one at a time, in an order set by which absence is most measurable.

*Gives:* every new capability is judged by something that can go red, and the wave can
close with fewer than seven skills and still be honest. *Costs:* two checks, a corpus
format, and seven separate landings instead of one. *Risks:* a corpus written by the same
author who wrote the skill passes trivially. *Rules out:* shipping a capability because its
name was on a list.

**B. Write the seven bodies now and add evaluation after.** The proposal's own text for
each skill is detailed enough to write from directly, and the corpus follows once the shape
settles.

*Gives:* the fastest visible progress and the smallest immediate diff. *Costs:* nothing
checks the seven, so the "No hace" column of each one — the half that prevents the wrong
skill firing — is decoration. *Risks:* this is the failure the audit already found on the
other side of the product, where `proven = true` was a field somebody typed (spec 011,
D-011-01). *Rules out:* nothing, which is the problem.

**C. Add none. Fold the work into the eight that exist.** `ai-test` into `ai-build`,
`ai-verify` into `ai-review`, `ai-animation` into `ai-design`, and `ai-report` into the
`report` verb.

*Gives:* no new routing surface at all, and it is what the proposal itself says should
happen to three of the seven if their evaluation does not hold (EP-117, EP-122, EP-252).
*Costs:* `ai-report`, `ai-design` and `ai-security` have artefacts nothing else produces —
a governed payload, a rendered accessibility record, a threat model — so folding them means
not doing the work. *Rules out:* the three genuinely distinct capabilities.

## Decision

**Option A, with option C kept live for three of the seven.** The deciding reason is that
option B cannot fail: a skill file with no negative corpus produces no red line for
anybody, so the wave would close on seven files nobody could contradict.

`ai-animation`, `ai-test` and `ai-verify` keep C as their exit condition rather than as a
caveat, because the proposal already writes their absorption clause and a clause with no
consequence is a sentence. If the routing evidence does not distinguish them, they are
absorbed and no file ships.

**Challenged once, honestly:** the strongest case against A is that an admission gate is
itself machinery, and a wave can spend seven weeks building a corpus format and shipping
zero capabilities — which is worse than shipping seven imperfect files. That case is real
and it changes the shape. The gate is two checks inside the function that already audits
skills, not a new module; the corpus is plain files inside the skill's own directory, not a
registry; and the first capability through the gate is `ai-report`, because its absence is
the one the product currently prints, and its exit criterion is an exit code rather than an
opinion.

## Normative contract

Where this section and spec 010 differ, spec 010 governs and this document is wrong.

**Admission.** One capability per change. A capability may land only with all of: a
`SKILL.md` inside `contract.CEILING`; a positive corpus; a negative corpus holding at least
one case where it must refuse to act; a routing record naming which capability wins each
neighbouring case; and its mode already declared in `policy/capabilities.toml`. Missing any
one of those, no file lands. `contract.audit_one` checks the corpus and the refusal case,
and `just check` fails when either is absent.

**The ten verbs stay ten.** No `build`, `design`, `security` or `verify` verb (EP-227,
EP-228). These seven are skills. Anything they need from the CLI arrives as a subcommand of
an existing verb, as `report surfaces` did in spec 011.

**Governed reporting.** `ai-eng report issue` builds a payload against a closed schema,
writes the draft locally and gitignored, populates it from an allow-list of fields and
never by collection, scans it twice, and shows the exact bytes with their SHA-256 before
anything leaves. Submit is a separate action a person confirms. An autonomous process may
invoke submit only where a versioned organisational policy pre-authorises that incident
type and that destination, and never under a regulated profile. A security finding routes
to private disclosure and never to a public issue. The payload never carries logs, diff,
source, specs, chain, environment, paths, host, user, email, IP, remotes or client data
(EP-024, EP-131, EP-132, EP-270..EP-275). One red fixture per forbidden class — machine
path, personal data, secret — exists before the code that rejects it.

**`ai-design` is one gateway that loads one route.** `shape` reads the spec, the Solution
Intent, the audience and the existing system and classifies the work. `system-build`
produces tokens, components, states, true content and a mobile-first implementation, adding
a dependency only where the current stack cannot answer. `imagery` is opt-in. `verify`
measures the rendered result rather than the declared CSS — geometry, contrast over real
backgrounds, overflow, collisions, typography, states and journeys — desktop and mobile in
one batch, at most two automatic rounds (EP-237..EP-242). No `DESIGN.md` substitutes for a
spec, a MADR or the Solution Intent (EP-247).

**Accessibility is evidence, not a scanner result.** The definition of done in EP-248 lands
as an enumerated list where each item names the command or the observation that satisfied
it, and a manual item records the person and the date. AA is the release floor and the only
level a gate blocks on. An AAA criterion that is not viable keeps reason, owner, expiry and
its AA evidence (EP-249). Axe output and a contrast ratio are filters; neither, alone or
together, declares conformance (EP-250).

**Motion has one owner.** `ai-animation` owns curves, duration, gestures, interruptibility,
reduced motion and the performance budget, and loads only where the request or the diff
carries real motion. `ai-review` gains frontend and motion lenses that load only when the
diff touches them, judge fidelity, and neither redesign nor repair (EP-120, EP-121, EP-125,
EP-126, EP-251).

**Generated imagery is classified.** Opt-in only. Output loses EXIF, passes a type and
malware scan, and is sanitised when it is SVG. Its asset card keeps provider, model, prompt
digest, sources and licence. Text recovered by OCR is data and never an instruction. An
external provider requires classification, approved residency and retention, and consent.
An image proves nothing about alt text, contrast, trademark, copyright or accessibility
(EP-253..EP-256).

**Each recovered skill states what it will not do, and a fixture holds it to that.**
`ai-build` does not widen scope, self-approve, publish or deploy. `ai-test` does not change
production code and hands it to `ai-build` when a test demands one. `ai-security` does not
replace guards or CI, does not accept risk and does not declare compliance. `ai-verify`
runs allowlists without `--fix` and returns to debug or build on failure (EP-111, EP-112,
EP-115, EP-116, EP-123, EP-124, EP-127, EP-128).

**The CLI work this wave owns is narrow.** `--non-interactive` fails when a decision is
missing and never infers consent (EP-236). `--debug` is the only route by which a traceback
reaches a person; without it an error carries its stable code, human message, `retryable`
and `cure` and nothing else (EP-233). Rich, plain/no-TTY and `--json` return the same
outcome and the same exit code for the same run, proved by executing each command in all
three (EP-025, EP-234). `--json` emits one object on stdout with no chrome, prompt or ANSI
(EP-230). JSONL stays unbuilt until a long operation has a real consumer (EP-231).

## What this closes

Each row must move by something that executes, or the wave does not close. "Today" is what
was measured in this tree, not what was assumed.

| Requirement | Today | What closes it |
|---|---|---|
| EP-021, EP-100, EP-101 | NO CHECK | corpus and refusal checks in `contract.audit_one` |
| EP-022, EP-118, EP-119 | NO FILE | `ai-design`: one gateway, four routes, AA floor |
| EP-023, EP-111, EP-112 | NO FILE | `ai-build`, with its refusals as red fixtures |
| EP-115, EP-116, EP-117 | NO FILE | `ai-test`, or absorption if routing does not hold |
| EP-127, EP-128 | NO FILE | `ai-verify`, allowlists run without `--fix` |
| EP-123, EP-124 | NO FILE | `ai-security` with stated limits; its pack is P4 |
| EP-024, EP-131, EP-132 | STUB | a closed payload that sends nothing on its own |
| EP-270..EP-275 | STUB | local draft, two scans, byte preview, private route |
| EP-027 | NO FILE | one red fixture each for path, personal data, secret |
| EP-025, EP-234 | PARTIAL | one outcome and exit code across all three renderings |
| EP-233, EP-236 | ABSENT | `--debug` for tracebacks; `--non-interactive` that refuses |
| EP-026, EP-029 | NO CHECK | a routing evaluation per capability — see the limits |
| EP-028, EP-248 | NO FILE | rendered evidence, one command or observation per item |
| EP-249, EP-250 | NO FILE | AAA exceptions with owner and expiry; scanners as filters |
| EP-120, EP-121, EP-251 | NO FILE | `ai-animation`, loaded only where motion is real |
| EP-122, EP-252 | NO FILE | absorption written as an exit condition, not a caveat |
| EP-125, EP-126 | PARTIAL | frontend and motion lenses in `ai-review/references/` |
| EP-237..EP-247 | NO FILE | the four routes; the rejected list as a negative corpus |
| EP-253..EP-256 | NO FILE | classification, EXIF stripped, asset card, OCR as data |
| EP-103..EP-110 | PROSE | one refusal fixture per skill that already exists |
| EP-129, EP-130, EP-133, EP-134 | PROSE | the same, for `ai-note` and `ai-ship` |
| EP-219..EP-232, EP-235 | DONE | `cli.py`, `ui.py`, `policy/outcome-v1.schema.json` |
| EP-257 | DONE | `hooks/change_scope_guard.py`; landed in P0, recorded in the CHANGELOG |

### Five requirements cannot be made green as written

Recorded so that a reader auditing the proposal counts them as open questions rather than
as misses. Each needs a decision that is not this document's to take.

**EP-022 — "WCAG 2.2 AAA target, AA release floor".** A target has no pass condition. AA is
a set of numbered criteria a command can check; AAA as stated is an aspiration, and a gate
cannot block on an aspiration without blocking on taste. D-012-05 fixes the floor and
records the rest, but whether AAA ever becomes blocking, and against which criteria, is
undecided.

**EP-026 — the seven skills "do not collide".** No threshold, no measurement and no prompt
set. Two descriptions can share a phrase and still route correctly; two can be disjoint on
paper and both fire. Until somebody states what is counted and what number fails, this
cannot go red.

**EP-029 — `skill eval: approved corpus`.** "Approved" names no approver, no format, no
location and no command, and there is no evaluation runner in this repository —
`contract.audit_one` is the only thing that reads a skill file at all. This spec builds the
corpus checks; who approves a corpus, and against what, is open.

**EP-117, EP-122, EP-252 — "distinct value from ai-build", "better routing than a
reference".** Three absorption clauses, no comparison defined: no baseline, no sample, no
margin. D-012-04 makes the clause an exit condition so that it has a consequence; the
comparison itself still has to be specified before it can be run.

**EP-119, EP-239, EP-241, EP-246 — "imposes no style", "material visual decision", "reduces
uncertainty", "agency look".** These are judgements written as constraints. A check for any
of them would be a check on taste, and this product does not ship one. They belong in the
skill body as guidance, and nothing in `just check` may claim to enforce them.

## Non-goals

- Nothing from P3 (coordination), P4 (security evidence pack, SBOM, provenance) or P5
  (external pilot). `ai-security` lands here as a skill with limits; its evidence pack does
  not.
- No eleventh verb, and no change to the ten.
- No surface or adapter work. That is spec 011.
- No imagegen provider integration, no live browser control plane, no parallel `DESIGN.md`.
- No skill that exists to occupy a name. A capability whose routing evidence does not hold
  is absorbed without a shim.

## Engineering criteria

- **KISS** — the admission gate is two checks in the function that already audits skills.
- **YAGNI** — a capability lands when its corpus and its refusal case exist, not because it
  is on a list of fifteen.
- **DRY** — one corpus location per capability, inside its own directory; no registry, no
  second copy, no mirror.
- **SOLID** — the skill guides judgement, the CLI keeps facts and evidence, the guard
  decides. `report issue` builds and shows; it does not send on its own authority.
- **TDD** — the refusal fixture is red before the capability's file exists, and the unsafe
  report fixture is red before the scanner that rejects it.
- **Clean Code** — every "No hace" line in a shipped skill maps to a named negative case, or
  it is deleted rather than left as decoration.
- **Clean Architecture** — capability scope stays data in `policy/`, the skills stay text,
  and the hooks keep importing nothing but the standard library.

## Risks requiring resolution, not acceptance

- **A corpus written to pass.** The same author writes the skill and the cases that judge
  it. Resolution: each capability's negative corpus draws its cases from the positive corpus
  of the neighbouring capability, so a collision appears as a failing case in a file
  somebody else wrote.
- **Seven skills plus their corpora against the line ceiling.** `contract.REPO_CEILING`
  bounds the tree and CI fails on the line after it. Resolution: the arithmetic for each
  capability is presented before its file lands; the ceiling moves only in a commit that
  states why, and the work is never scoped down to fit the number. The number is not quoted
  here, because a live counter in prose goes stale on the next commit.
- **Accessibility evidence that is a screenshot.** A rendered image is the easiest thing to
  produce and proves nothing (EP-256). Resolution: every item in the definition of done
  names a command or a stated observation, a manual item names the person and the date, and
  no item is satisfied by a scanner alone.
- **A report draft that leaks by field name rather than by content.** An allow-list is only
  as good as the fields on it. Resolution: the byte-exact preview and its SHA-256 are shown
  before any send, and the fixtures for path, personal data and secret run against the
  assembled payload rather than against the schema.

## Decisions

**D-012-01 — no skill file lands before its corpus and its refusal case.**
**Rationale:** `contract.audit_one` today checks format and vocabulary only, so a skill that
routes wrongly passes every gate this repository has. A file nothing can contradict is
documentation, and doubling the catalogue with documentation is how the previous version
reached 528 files.

**D-012-02 — the admission checks live inside `contract.audit_one` and run in `just check`.**
**Rationale:** rule 12 — a judgement that resolves the same way three times becomes a
script, and the script has one check and fails closed. A separate evaluation tool outside
the gate is a gate nobody runs.

**D-012-03 — `ai-report` is the first capability through the gate.**
**Rationale:** it is the only one of the seven whose absence the product already prints, it
is the one whose failure mode is data leaving the machine, and its exit criterion is an exit
code on an unsafe fixture rather than an opinion about quality.

**D-012-04 — `ai-animation`, `ai-test` and `ai-verify` carry absorption as an exit
condition.**
**Rationale:** EP-117, EP-122 and EP-252 already state that each survives only if its
evaluation shows distinct routing. Left as a caveat it never fires. As an exit condition the
wave can close with five capabilities and be honest, instead of closing with seven and being
unverified.

**D-012-05 — AA is the release floor and the only level a gate blocks on; AAA is recorded
per criterion.**
**Rationale:** EP-022 asks for an AAA target with no pass condition. A gate that blocks on
an undefined target blocks on whoever is reading it that day, and EP-249 already supplies
the honest alternative: reason, owner, expiry and the AA evidence beside it.

**D-012-06 — the CLI part of this wave is two flags and one equivalence proof, not a
rewrite.**
**Rationale:** the JSON v1 envelope, the will/running/cure lines, the seven outcomes and the
`NO_COLOR`/`TERM=dumb` handling were measured present in `cli.py`, `ui.py` and
`policy/outcome-v1.schema.json`. Re-specifying them would spend the wave rebuilding code
that already runs, and EP-025's actual gap is that nothing proves the three renderings
agree.

**D-012-07 — EP-257 is closed, not pending.**
**Rationale:** `hooks/change_scope_guard.py` exists, no `design_gate` remains, and the
rename is pinned by a test named after it. Carrying a done requirement as open makes every
other open item look negotiable.

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
