---
id: "001"
slug: v1-from-scratch
status: shipped
date: 2026-08-08
ref: ""
supersedes: ""
---

# ai-engineering v1.0.0, from an empty folder

## Context and problem

v0.13.0 is 2,639 committed files and 436,091 lines. Measured over its own record: of
46,625 audit events, 303 record that a control acted — 0.65% — and 43,003 say only that a
hook ran. Over its entire life the policy engine hard-blocked six times, five of them
"do not push to main", which git does natively in five lines of shell. 594 files are
byte-identical to another file, and 3,186 lines exist to keep those copies in sync; with a
single user, 65 of 139 copied files had already drifted. One layer fired 19,149 times and
wrote an empty file.

So the framework was expensive, and most of the expense bought nothing. Worse, it could
not tell you that: its hook wrapper ended in a zero exit no matter what, so a guard that
crashed reported "no objection, go ahead", and every turn stayed green.

## Options considered

1. **Refactor v0.13.0 in place.** Cheapest to start and the only option that keeps
   everything working throughout. Rejected: the 528 framework-owned files inside a user's
   repository, the six byte-identical skill trees and the fail-open wrapper are all
   structural, and each would have to be undone anyway. A refactor would carry the
   decisions that produced them.
2. **Build v1.0.0 from an empty folder, beside the frozen tag.** More work up front, and
   it forces every feature to defend its existence once more against "thousands of users"
   rather than "one user". Chosen.

## Decision

Build from empty. v0.13.0 freezes under its tag and stays installable; v1.0.0 is a new
tree of about sixty files with eight skills, eight guards and a ten-verb CLI, and nothing
is deleted anywhere until the acceptance suite is green.

The full design, with the measurements behind each choice, is the v1.0.0 design document
this repository was built from. What follows is only what a reader of the code needs.

## Decisions

```yaml
decision: One place prints the bypass recipe, and a test reads what it prints
date: 2026-08-08
rationale: >
  The wrapper printed the same bypass command for every non-security guard, while the CLI
  verb defaults its guard flag to design_gate and the grant is rejected when its guard is not
  the denying one. So a loop_guard denial handed the model a command that unblocked a
  different guard, and design_gate stated the same recipe one line before the wrapper printed
  it again. The reason it shipped is that no test anywhere asserted the content of any denial
  message: every adversarial case ends at the exit code and the harness discards stderr. That
  message is documented as written for a model to act on, which makes its text a behaviour,
  and a behaviour with no assertion is prose. One printer, one assertion, duplicate deleted.
```

```yaml
decision: A gate that ran over zero items is not a pass, applied to our own gates
date: 2026-08-08
rationale: >
  The line counter returned zero when the index listed no files, and the ceiling test then
  asserted zero was under the ceiling and passed — in the source distribution, which ships
  tests. The skill audit globbed twice, so its own no-skills tripwire did not guard the loop
  it names. This rule already existed twice here, in the IOC reader and in the anti-theatre
  harness, and was absent from both checks that needed it. It now raises, doctor converts the
  raise so its check reports could-not-evaluate rather than a false green, and the
  anti-theatre harness reads the justfile we hand a stranger: it printed a zero test count
  and a file-list lint count two lines under a comment forbidding exactly those.
```

```yaml
decision: Capability rungs replace the vendor ladder, and the risk clause is the point
date: 2026-08-08
rationale: >
  The vendor-free rule stands untouched: the tool protocol delivers each tool's name and
  schema at run time, and naming one of two equivalent vendors is endorsement. What was
  missing was not a ladder — primary-source-beats-blog and prefer-running-it were already
  steps two and three, and name-what-you-could-not-reach was already the closing paragraph —
  but two behaviours and one doctrine. The behaviours fold into step three at zero lines:
  stop on the rung that answers, and start a deep research tool before you climb so it is
  harvested last. The doctrine cost three lines because it was stated nowhere: the only
  occurrence of data-is-not-instruction in the whole product was inside the injection guard's
  denial message, so the rule existed only once the guard had already caught it. Discovery
  stays a prompt: a registry listing named seven connected servers with no tools in the
  namespace and omitted two whose tools worked, so a config parse answers "configured" when
  the question is "reachable" and cannot fail closed — rule 12's own escape clause. And the
  guard now scans tool results from the protocol, which a full match against the three web
  tool names never did.
```

```yaml
decision: No orchestrator, and no borrowed measurement to defend not having one
date: 2026-08-08
rationale: >
  Two ICLR 2026 papers were read in full. One trains a 7B policy with reinforcement learning
  to design communication topologies over a pool of worker models; the other evolves a 0.6B
  coordinator plus a ten-thousand-parameter head that reads the small model's hidden states
  and assigns a thinker, worker or verifier role per turn. Both optimise which model call
  happens next under a terminal reward on a question with a checkable answer. This product
  brokers no inference, so there is no rollout to score and no oracle to score it against;
  the second paper states on its own page ten that it cannot act on the plans it devises, and
  this product is nothing but acting on tools. The coordinator is also unobtainable — closed
  weight, interface only, routing deliberately hidden — a paid runtime dependency that
  conceals its own decisions inside a product whose deliverable is an auditable record. What
  the operator loses is fan-out: a diff too large for one context window gets serial passes,
  because a forked context is a fresh window and not more of them. The revisit trigger is
  written down rather than felt — the first time a review exhausts one window on a real diff,
  the answer is two passes, and only if that stops working does a second dispatch earn its
  lines. The papers are not cited as evidence for the deletion either: a role-split ablation
  measured in an automated loop against a checkable answer does not transfer to human-invoked
  skills with no loop and no oracle, and pasting a borrowed number in to ratify a decision
  already made is a green nobody earned.
```

```yaml
decision: Reviews are not persisted in v1, and the buy trigger is written down
date: 2026-08-08
rationale: >
  The store the operator pointed at was audited: 53,505 lines across 227 files upstream, of
  which the store itself is one file per target under an organisation and repository
  directory, behind a comment-wrapped metadata header. It is write-only on the review path —
  the operator's own store holds one review and one accounting line, and its learnings
  directory documents an index file that has never been created. Porting it costs about
  thirty-two lines and a further ceiling raise, and the read side would be enforced by a
  sentence rather than an exit code, which is the same tier as the upstream feature that
  never fired. What the operator loses is concrete and small: a second review on one branch
  re-derives findings the first made, and there is no artifact to attach to a pull request.
  Redirecting the output into a file costs zero lines today. The buy trigger: run a review
  twice on one branch, have the second repeat a finding the first made, and then it is worth
  thirty-two lines with a read the skill cannot proceed without and an exit code enforcing it.
```

```yaml
decision: One artifact, and it is the wheel
date: 2026-08-08
rationale: >
  The same handler declared in two settings files runs once, but a plugin's copy is kept
  separate, so anybody holding the framework by plugin in one place and by settings in
  another gets blocking guards firing twice. That is structurally impossible without a
  plugin. The settings file also reaches Copilot CLI and Cursor, which no plugin reaches.
  The plugin survives only as an extra for fleets under allowManagedHooksOnly, and is not
  built until an enterprise buyer asks.
```

```yaml
decision: A hook declares its class at the top of its own file
date: 2026-08-08
rationale: >
  The root pattern was an eleven-line wrapper that always exited zero. The cure is not a
  bigger wrapper: it is that guard means fails closed and telemetry means fails open, and
  you cannot write a fail-open guard without noticing, because "fails open" lives in a
  decorator called telemetry. A test reads the dispatcher table and turns CI red if a hook
  on a blocking event is not a guard.
```

```yaml
decision: Deduplicate on the call identifier, never on the call's content
date: 2026-08-08
rationale: >
  The dispatcher caches a verdict so a call delivered twice — VS Code Copilot legitimately
  reads Claude's settings file — is not decided twice. Keying that cache on the arguments
  looked equivalent and was not: it made three reads of three different files, and a retry
  loop, indistinguishable from one call, which blinded loop_guard. The fingerprint now
  carries the surface's own tool_use_id, and the cache is used only when there is one.
  Amended 2026-08-08: this shipped with the opposite outcome to the one recorded here. The
  dispatcher's fingerprint was correct for the verdict cache and wrong for loop_guard's
  repeat counter, which was reading the same value — so every repeat carried a distinct
  tool_use_id, the count was always one, and the rule never fired on the only surface
  marked proven. The counter now keys on the signature; the cache still keys on the
  identifier. And the suite did not catch it: the loop payload was built without a
  tool_use_id, which no real surface sends, so a green suite reported a dead control for as
  long as the fixture stayed unrealistic. Test-first would not have helped. The fixture was
  written before the guard and it was already wrong.
```

```yaml
decision: The line ceiling moves to 5,600, and the arithmetic is here
date: 2026-08-08
rationale: >
  The design budgeted 4,970 lines with a 5,000 ceiling. The build came in at 5,500. The
  overrun is one component: the CLI was estimated at 1,235 lines and is 2,348 — twenty-one
  assertions, ten verbs, an interactive installer and four settings writers. Every other
  bucket came in under, tests by 487. Nothing was cut to reach the new number and nothing
  was added to justify it: no guard, no assertion, no event class and no test was removed.
  The ceiling is raised deliberately, in a commit that says why, because that commit is the
  conversation the mechanism exists to force.
```

```yaml
decision: Apache-2.0, and the classifier is deleted rather than swapped
date: 2026-08-08
rationale: >
  PEP 639 makes a License-Expression field plus a "License ::" classifier a hard PyPI
  rejection for new uploads, and the release workflow would have died on the v1.0.0 tag
  after build and attestation had already succeeded — a failure that reads like an outage.
  hatchling ships LICENSE and NOTICE inside the wheel's dist-info, which satisfies Apache
  section 4(d) at zero lines. Those two files are excluded from the line ceiling because
  nobody here wrote them and nobody here can shorten them; that and the record are the
  only two exclusions, and treating either as precedent for a third would end the ceiling.
```

```yaml
decision: contract.JARGON is the single store of banned words
date: 2026-08-08
rationale: >
  policy/glossary.yml had zero consumers across src, hooks, tests, CI and the justfile,
  while its own header named two readers that do not exist: vale is not installed
  anywhere and the skill checker reads a hardcoded tuple whose ten words were identical
  in content and order. A data file with no reader that advertises a gate is not dead
  weight, it is a claimed gate that never fired — the failure this product exists to cure.
```

```yaml
decision: No vendor name appears in any SKILL.md
date: 2026-08-08
rationale: >
  Exa and Tavily sit on the same rung with no discriminator, so naming one is arbitrary
  endorsement and naming both is advertising; MCP already delivers each tool's name and
  schema into context at run time, for free. The other four were rejected on their own
  terms: academic-research-skills is CC BY-NC, which bars a commercially installable
  framework, and is 2,170 files; obscura spoofs TLS fingerprints to defeat bot detection,
  which a product whose mission is about not doing harm silently cannot instruct an agent
  to do; notebooklm-py is an unofficial cookie-jar client with an interactive login and no
  CI path; agent-browser is a good tool whose own skill is six times our line cap. The
  gain was one sentence, not six integrations: an unsourced claim must say which kind it
  is — no source exists, or there was no way to look from here.
```

```yaml
decision: The shipped security recipe is gitleaks and trivy only
date: 2026-08-08
rationale: >
  The skeleton ran semgrep against a config file nothing writes and the allow-list in
  .ai/.gitignore could not have committed, so semgrep exited 7 and just stopped on the
  first failure — `just check` had failed on line one in every repository this tool ever
  initialised, and the CI it hands the user was red on first push. Those two scanners are
  the ones that genuinely read files rather than languages. We cannot ship a credible
  cross-language static-analysis baseline in a 25-line skeleton, and a recipe that fails
  on line one teaches people the gate is noise, which is worse than one fewer scanner.
```

```yaml
decision: Languages are documented-not-proven, the same discipline surfaces already get
date: 2026-08-08
rationale: >
  policy/surfaces.toml carries a proven flag per surface and doctor prints UNPROVEN for
  anything a denial has not executed on. docs/tools.md now applies that to stacks: six are
  detected, the rest are documented only, and detection is disclosed as deciding nothing
  but what init prints. The enforcement plane was already language-neutral — the git
  hooks, the five guards and all eight skills contain no language-specific token — but two
  semgrep rules were declared for python while forbidding something in every language, so
  the whole policy scanned zero targets in a Go, Rust, C# or Java tree.
```

```yaml
decision: v1 never sits in the API data path
date: 2026-08-08
rationale: >
  The orchestrator proposed for comparison turned out to be an HTTP model router — an
  OpenAI-compatible proxy that grades an answer and escalates to a stronger model — with
  no concept of an agent, a subagent or fan-out, 2,647 lines of TypeScript, three npm
  dependencies and an always-on localhost daemon in the request path. Its verifier
  defaults to accepting unparseable output, which is a fail-open decision-maker: exactly
  what the guard decorator exists to make unwritable. No proxy, no daemon, no model
  routing and no cost telemetry. A user who wants any of it points their own base URL at
  their own proxy and needs nothing from us.
```

## Accepted risks

```yaml
id: R-001-07
finding: two-untested-branches-shipped-with-this-commit
severity: low
accepted_by: the maintainer
accepted: 2026-08-08
expires: 2026-11-06
renewals: 0
justification: >
  Two branches added here are exercised by no suite. Doctor's new could-not-evaluate
  conversion needs a tree that holds the package and no index, which costs more lines to
  construct than the branch it covers, and CI always runs inside a checkout. And OpenCode,
  one of only two proven surfaces, has no post-execute containment at all because its plugin
  wires only the before-execute hook, so the new matcher closes the hole on one of the two
  and the wiring table now says so rather than implying protection it cannot deliver. Neither
  is a false green: the first reports could-not-evaluate, the second is written down where
  doctor's coverage line reads it.
follow_up: Wire the post-execute hook in the OpenCode plugin, or keep the note. Cover the
  could-not-evaluate branch the next time doctor is edited for another reason.
```

```yaml
id: R-001-08
finding: no-guard-that-a-plan-item-claimed-done-is-done
severity: low
accepted_by: the maintainer
accepted: 2026-08-08
expires: 2027-08-08
renewals: 0
justification: >
  A plan's build order stays four-field prose bullets — file, check, rollback, done when —
  and no gate reads a tick. A "- [x]" is one bit, written by the same agent that wrote the
  work, in the same commit, and the cheapest way to satisfy any gate that reads it is one
  keystroke in a markdown file. So a guard on it would deny work whose only remediation is
  to lie, which is worse than no guard. Whether an item is genuinely done does not always
  resolve the same way, so under rule 12 it stays a prompt and this is the sentence. What
  was buildable was built instead, and it was a different control: the plan that opens
  design_gate now has to belong to the branch it opens, because the glob it replaces was
  satisfied by any plan.md ever written and had therefore been inert in this repository
  since 001 landed. The bullet also carries a runnable command where a box carries a bit.
follow_up: Revisit when a plan item is claimed done, the claim is false, and the falsehood
  was visible in the plan text alone rather than in the diff.
```

```yaml
id: R-001-09
finding: no-tdd-order-guard
severity: medium
accepted_by: the maintainer
accepted: 2026-08-08
expires: 2026-11-08
renewals: 0
justification: >
  Three refusals, one acceptance, because they share a reason. Test-first across agents
  cannot be checked here: this estate squash-merges, so the test and the implementation
  land in one commit and the authoring order is not in the history at all, and a test
  written for behaviour that already exists passes against the parent by construction — so
  the check and the work are mutually exclusive. It stays a prompt, and the substitute is
  named: a fixture that carries the fields the real surface sends. The loop_guard case was
  written before its guard shipped and the guard was still dead, because the payload was
  one no surface delivers; ordering was not the property that was missing.
  Amended the same day, and then again, because only one third of this acceptance survived
  the afternoon. The mutation refusal is withdrawn outright: `just mutate` runs on every
  push in its own CI job, mutmut 3.7.0 over the package at a floor of 59% and a fourteen-row
  runner over the guards, which mutmut cannot import without making hooks/ a package and
  paying 110 ms on the hot path. Building it found two more defects that nothing else had:
  mutmut's sandbox lives inside the repository, so the tests escaped it and rewrote this
  repository's own justfile three times; and relocating the tree showed that wiring.ours()
  identified our own settings entry by finding the string "ai-engineering" inside a
  filesystem path, which is true for one install shape and false for every other — where it
  is false, init appends a second blocking guard on every run and uninstall removes nothing.
  Three tests were green here only because this checkout is named ai-engineering.worktrees.
  The coverage refusal is withdrawn: the operator read the argument and asked for 80%
  anyway, which is his to decide, and the outcome says the argument was half wrong. The
  17% was a measurement error, and fixing the measurement alone moved it to 36% with no
  test written — that part stands. But the 2,660 lines the refusal called characterisation
  of straight-line file writers found nine defects nothing else had, and one of them handed
  every user this tool has ever initialised a CI workflow that fails on its first step. The
  gate is 80% branch coverage, the number he asked for; 95% is what landed. And mutation
  testing was run after all, by hand, 126 mutants across the four new files: 113 died on
  the first pass and twelve more after the tests were strengthened. It is not a gate and it
  is not scheduled — it was a one-off pass whose finding is that boundaries and constants
  are where tests stop being able to fail.
follow_up: Raise both floors in a commit that states the arithmetic, the same discipline as
  the line ceiling. The test plane is larger than the product, and the next commit that needs
  lines deletes a test that kills no mutant — `just mutate` now says which those are, which
  is the only reason that sentence is actionable rather than a wish. Six strict xfail markers
  name six live defects; each one is a commit, and the marker turns red the day it is fixed
  without being removed. And 1,310 mutants are still alive in the package: that number, not
  the 95%, is what is left to do.
```

```yaml
id: R-001-01
finding: three-surfaces-unproven
severity: medium
accepted_by: the maintainer
accepted: 2026-08-08
expires: 2026-11-06
renewals: 0
justification: >
  Cursor, VS Code Copilot and Copilot CLI each document a working deny and none is
  installed on the machine this was built on, so their coverage is paper. They report
  UNPROVEN rather than covered, which is the honest state, and the git hooks and CI hold
  underneath them regardless.
follow_up: Install each surface and record a real denial, then flip proven in surfaces.toml.
```

```yaml
id: R-001-02
finding: real-model-half-of-the-suite-does-not-ship
severity: medium
accepted_by: the maintainer
accepted: 2026-08-08
expires: 2026-11-06
renewals: 0
justification: >
  A buyer's CI runs the deterministic replay. The half that proves a real model under a
  real injection is actually blocked needs a key and spend, and cannot run under the
  author's subscription on somebody else's behalf.
follow_up: Publish the harness so a buyer can run it against their own key.
```
**R-001-02 grew a consequence on 2026-08-10 that nobody had noticed.** Assertion 9 demanded
a dated `real_model_at` and failed without one, so the half this risk accepts as not
shipping made `ai-eng doctor --ci` impossible to pass on any runner or any fresh machine —
found by the first CI run this branch ever had. The assertion now raises `Undecidable` when
that half has never run and fails only when its result is stale, which is this repository's
own rule that *cannot tell* is never a pass and never a failure either. The risk itself is
unchanged and so is its follow-up.

```yaml
id: R-001-03
finding: no-static-analysis-in-a-users-repository
severity: medium
accepted_by: the maintainer
accepted: 2026-08-08
expires: 2026-11-08
renewals: 0
justification: >
  The shipped security recipe is gitleaks and trivy, both of which read files rather than
  languages. Shipping a semgrep config would need an eighth landed file and a change to
  the .ai/ allow-list, and shipping a broken one made the whole gate fail on line one.
follow_up: Revisit when a user reports it, or when an ai-eng verb that prints the policy
  path finds a payer in the line budget.
```

```yaml
id: R-001-04
finding: ioc-catalogue-is-precise-not-evasion-resistant
severity: medium
accepted_by: the maintainer
accepted: 2026-08-08
expires: 2027-02-08
renewals: 0
justification: >
  The catalogue states precision as its design constraint and SECURITY.md makes no claim
  against a determined attacker. Unicode normalisation and an invisible-character strip
  would raise obfuscated recall from roughly one in ten to seven, and the character-collapse
  variant that gets it higher silently destroys two of the patterns just repaired.
follow_up: Add the normalisation pair with a measurement, and never close this by
  broadening patterns into topic matching.
```

```yaml
id: R-001-05
finding: design-gate-checks-that-a-plan-exists-not-that-it-is-good
severity: low
accepted_by: the maintainer
accepted: 2026-08-08
expires: 2027-08-08
renewals: 0
justification: >
  This is rule 12's own escape clause exercised honestly: the judgement cannot be made to
  fail closed, so it stays a prompt and the reason is written down. A script scoring a
  plan's quality would be judging judgement.
follow_up: None. /ai-review reads the plan, and a person reads the review.
```

```yaml
id: R-001-06
finding: zero-lines-of-margin-under-the-ceiling
severity: low
accepted_by: the maintainer
accepted: 2026-08-08
expires: 2026-09-08
renewals: 0
justification: >
  The ceiling held at exactly 5,600 without a raise, and every payer was found rather than
  invented: a data file with no readers, a hand-written regex parser duplicating a check the
  reader now makes unreachable, a single-use helper, a documentation page folded into the one
  that pointed at it, three lockfile ecosystems that cannot occur in this repository, and a
  semgrep rule replaced by a seven-line test that runs whether or not semgrep is installed.
  Zero margin is not slack, it is the mechanism working.
follow_up: The next commit that needs lines deletes first. The remaining candidate is
  hooks/_otlp.py at 141 lines, if no user ever configures an observability destination.
```

## Production-ready

- [x] CI/CD — `just check`, run by `.github/workflows/check.yml` on every push
- [x] Logs — one JSON line per decision, six closed classes, hash-chained: `ai-eng digest`
- [x] Traces — not applicable, and that is the rule: no second hop, no trace
- [x] Errors — recorded as their own event class and surfaced by `ai-eng digest`
- [x] Health and data age — `ai-eng doctor`, and `ai-eng audit verify` walks every link
- [x] External check — `.github/workflows/install-matrix.yml`, three OSes, a wheel we built
- [x] Second path — `doctor` reads the chain's head, `audit verify` recomputes every hash
- [x] Security — gitleaks, semgrep and trivy in `just security`; zizmor over the workflows in `.github/workflows/check.yml`; SECURITY.md ships
