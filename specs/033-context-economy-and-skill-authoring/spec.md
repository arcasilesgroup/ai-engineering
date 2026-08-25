---
id: "033"
slug: context-economy-and-skill-authoring
status: draft
date: 2026-08-25
ref: ""
supersedes: "010"
---

# Context economy and skill authoring

## Who this is for, and what it is worth to them

The person who runs `/ai-goal` on this repository and approves what it produces, and every
stranger who installs the wheel for a repository they are accountable for. The research goal
(`.ai/reports/018`) marked four remaining efficiencies the external references proved and
this repository does not yet supply: trimming what enters an agent's context, extracting a
reusable skill from a costly session, a dispatcher-and-examples authoring shape, and the
installed-version rule that makes a review trust the bytes on disk, never the model's
memory. This specification supersedes parts of spec 010's target to add the four (the
research paquete 5: its N12, N14, N15 and N22).

## Context and problem

**What is true today, measured in this tree on 2026-08-25, after specs 027-032:**

- The harness hooks filter nothing that enters a session's context: tool output lands whole,
  and a 2,000-line runner log occupies the window that attention should spend on the failure
  (make-claude-code-last-longer measured the fix: head 50 + tail 50 with a mark, before the
  context reads it — the research N12). This repository has no deterministic trimmer.
- A finding that took real time is preserved (`ai-note`) and a session's routing is
  evaluated (`skill_eval`), but no tool **extracts the generalisable workflow** of a costly
  session into a reusable SKILL.md (cc-creators' `skillify`: the interview that turns a
  one-off process into a skill with its rules — the research N14). The framework grows by
  hand-editing, not by harvesting its own best sessions.
- Every SKILL.md is one file. A skill whose procedure has conditional branches writes them
  all into the body, so the body grows and the agent reads what it does not need
  (cc-creators' dispatcher + `examples/` specialisations, headstart's `references/`
  subroutine — the research N15). The load-tier rule (spec 032 B-032-4) bounds the body's
  size but does not require the *shape*: a dispatcher body that loads specialisations on
  demand.
- A review skill tells a model to reason about a dependency, and the model reasons from its
  memory of the version, not from the bytes installed (graph-engineering's installed-version
  rule: the installed source is the truth, a finding that contradicts it is dropped or
  downgraded to `unverified` — the research N22). Nothing here executes that rule.

**The problem, in words a non-technical reader can follow:**

Four things are missing from how this framework handles information. It does not trim the
noise that floods an agent's attention. It does not turn a costly session into the reusable
skill it deserves. It writes every skill as one long file instead of a short dispatcher that
loads the details it needs. And it lets a review trust what a model remembers about a
library instead of what is actually installed. The four changes in this spec add those four
tools and rules.

## Options considered

1. **Add the four as checked modules and contract rules (chosen shape).** N12 (context
   trimmer), N14 (skillify extractor), N15 (dispatcher/examples shape as a craft rule) and
   N22 (installed-version rule as a module + corpus route) land as their own TDD tasks on
   the backbone specs 028-032. Gives: four deterministic, tested caps on how the framework
   spends attention and grows. Costs: a wide block; atomic commits mitigate it.
2. **Do the trimmer alone, defer the rest.** Gives: a small first block. Costs: growing
   skills still bloat, sessions still die without becoming skills, and reviews still trust
   memory — the three inefficiencies the research paired with the trimmer. The user's rule
   is that nothing in the goal is a ceiling.
3. **Adopt the external tools as-is (make-claude's hooks, cc-creators' skillify).** Gives:
   speed. Costs: those tools are tuned to Claude Code's harness; importing their hook
   scripts would make commands this wheel cannot run claimed controls, which spec 010's
   portable-command rule refuses. The *shapes* transfer; the implementations must be this
   tree's own.

## Decision

**Option 1**, as paquete 5 of the research. The spec supersedes spec 010 only where it
extends the target with the four behaviours below; it does not weaken, drop or relabel any
normative requirement 010 already states. Each behaviour is closed, versioned, and comes
with both a positive fixture and a nearby clean control. The four are:

### B-033-1 — Context trimmer (research N12)

A `trim` module in `src/ai_engineering/` with `trim_output(text, max_lines=N)` that keeps
`head − N/2 + tail − N/2` of a tool's output, marks the elided middle
(`… N lines elided …`), never elides a line containing a failure marker, and is
deterministic — same input, same trimmed output. The `ai-note` corpus gains the rule that a
note preserves a finding, not a log; the trimmer is what a skill uses to keep the note's
evidence small.

### B-033-2 — Skillify extractor (research N14)

A `skillify` module in `src/ai_engineering/` that takes a transcript (a session or a
costly one-off procedure) and emits a **SKILL.md skeleton that passes the contract** —
`name`, `description` with a `Not for` clause, the craft sections (spec 032), and a
`## Procedure` derived from the transcript's steps with the user's corrections as `Rules`.
It is an extractor, not a copy: it names the generalisable steps, never the chat.
`ai-note`'s corpus gains the route "turn this session into a skill".

### B-033-3 — Dispatcher and examples shape (research N15)

A new craft rule in `contract.audit_one` (beside the spec 032 rules): a skill whose
procedure has conditional branches (mentions "when X, use Y") must keep the branch bodies
in `examples/` or `references/` files the body loads on demand, rather than in the body.
The rule refuses a body that grows past the tier bound *because of the branches it should
have split*; it passes a dispatcher body under the bound with its specialisations in
separate files.

### B-033-4 — Installed-version rule (research N22)

A `versions` module in `src/ai_engineering/` with `verify_against_installed(package,
claim)`: reads the installed distribution's version (from `importlib.metadata`) and returns
whether the claim matches, `unverified` when the package cannot be resolved, and `mismatch`
when it contradicts. The `ai-security` and `ai-review` corpora gain the rule: a finding that
contradicts the installed version is dropped or downgraded to `unverified`, never trusted
from memory.

## Challenged once

**"A context trimmer belongs in the harness's hooks, not in a wheel."** The harness's hooks
are somebody else's surface; this wheel cannot promise to control them. What it can promise
is a deterministic trimmer the framework's own skills use to keep notes and outputs small —
the same economy, executed where this project has the authority to enforce it. The
trimmer's rule (never elide a failure line) is what makes it safe where a naive head/tail
would hide the very line the session needed.

**"Skillify from a transcript is a copy machine for chat."** The extractor's contract
forbids copying the chat: it emits the *generalisable steps* as a procedure and the user's
corrections as rules, and the emitted skeleton must pass `contract.audit_one` to be worth
anything — a skeleton that fails the contract is the extractor's bug, not the user's prose.
The test proves a transcript produces a contract-clean skeleton, never a transcript echo.

**"Installed-version is a nice rule for reviewers but impossible to test here."** The
module resolves versions through `importlib.metadata`, which pytest can monkeypatch
deterministically in a fixture — a fake distribution, a claim that matches, a claim that
contradicts, a package that cannot be resolved. The rule is exactly as testable as the
graph-engineering implementation, and the fixture proves all three outcomes.

## Assumptions and unresolved risks

- Assumption: the trimmer's default `max_lines` (80: 40 + 40) fits what notes and runner
  output actually hold; the parameter is a documented knob.
- Assumption: `skillify`'s skeleton passes the craft contract by construction; a skill
  whose transcript has no generalisable steps emits nothing and says so.
- Unresolved: a dispatcher body's "when X" detection is a heuristic (the branch cue is
  lexically present); the rule refuses only when branches are present *and* the body is
  over the tier bound it should have split. A later spec may tighten it with measured need.
- Unresolved: the inherited `madr.validate` red from ADR 0025; recorded, not fixed here.

## Examples somebody can check

Given a 200-line tool output with one failure marker in the middle,
When `trim_output` runs with max_lines 80,
Then the failure line survives, the head and tail are kept, and the elided middle is marked
(`uv run --with pytest==9.1.1 pytest -q tests/test_trim.py` → `2 passed`).

Given a transcript of a costly one-off procedure,
When `skillify` extracts it,
Then it emits a SKILL.md skeleton that passes `contract.audit_one` and names the
generalisable steps, never the chat (`uv run --with pytest==9.1.1 pytest -q
tests/test_skillify.py` → `2 passed`).

Given a skill whose procedure has branches past the tier bound,
When the dispatcher craft rule reads it,
Then it is refused for not loading its branch bodies from examples/references; a dispatcher
body under the bound with its specialisations in separate files passes
(`uv run --with pytest==9.1.1 pytest -q tests/test_dispatcher_craft.py` → `1 passed`).

Given a finding claims a package version contradicts what is installed,
When `verify_against_installed` runs,
Then a matching claim passes, a contradicting claim is mismatch, and an unresolvable
package is unverified (`uv run --with pytest==9.1.1 pytest -q tests/test_versions.py` →
`3 passed`).

Given the repaired tree,
When `contract.audit` runs over all skills,
Then no shipped SKILL.md triggers the dispatcher rule, and the gate proves the tree clean
(`uv run --with pytest==9.1.1 pytest -q tests/test_dispatcher_craft.py` → all passed).

## Decisions

**D-033-01 — a deterministic context trimmer (keep head/tail, mark the elision, never drop
a failure line) is the framework's context-economy tool.**
Rationale: make-claude-code-last-longer measured that trimming before context reads it is
the fix for runner-log floods; the failure-line rule is what keeps it honest where a naive
head/tail would hide the answer.

**D-033-02 — skillify extracts a contract-clean SKILL.md skeleton from a costly session,
naming steps, never chat.**
Rationale: cc-creators proved the interview that turns a one-off into a skill; the contract
gate makes the skeleton worth emitting, and the "never the chat" rule keeps it honest.

**D-033-03 — the dispatcher/examples shape is a craft rule: branches past the tier bound
must split into on-demand files.**
Rationale: cc-creators' dispatcher+examples and headstart's references both proved that a
body's conditional branches are what bloat it; the rule fires only where the bloat is real
(branches present, bound crossed).

**D-033-04 — the installed-version rule is a module and a corpus route: a finding that
contradicts the installed bytes is dropped or unverified, never trusted from memory.**
Rationale: graph-engineering measured that version-memory findings are the largest source
of review noise; `importlib.metadata` makes the rule deterministic and testable.

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

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