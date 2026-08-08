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
  Caught by the adversarial suite, not by review.
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
finding: four-lines-of-margin-under-the-ceiling
severity: low
accepted_by: the maintainer
accepted: 2026-08-08
expires: 2026-09-08
renewals: 0
justification: >
  The ceiling held at 5,600 without a raise: the payers were found rather than invented —
  a data file with no readers, a hand-written regex parser duplicating a check the reader
  now makes unreachable, a single-use helper and a documentation file folded into the one
  that pointed at it. Four lines is not margin, it is a warning.
follow_up: The next commit that needs lines deletes first. In order: the guard-exits-zero
  semgrep rule if a test replaces it, and hooks/_otlp.py if no user ever configures a
  destination.
```

## Production-ready

- [x] CI/CD — check.yml runs the gate, the suite and the install matrix on every push
- [x] Logs — one JSON line per decision, six closed classes, hash-chained
- [x] Traces — not applicable, and that is the rule: no second hop, no trace
- [x] Errors — recorded as their own event class and surfaced by `ai-eng digest`
- [x] Health and data age — `ai-eng doctor`, and `ai-eng audit verify` walks every link
- [x] External check — the install matrix runs a stranger's first five minutes on three OSes
- [x] Second path — `doctor` reads the chain's head, `audit verify` recomputes every hash
- [x] Security — gitleaks, semgrep, trivy and zizmor in `just check`; SECURITY.md ships
