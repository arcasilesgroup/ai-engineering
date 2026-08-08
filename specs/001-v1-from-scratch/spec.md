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

## Production-ready

- [x] CI/CD — check.yml runs the gate, the suite and the install matrix on every push
- [x] Logs — one JSON line per decision, six closed classes, hash-chained
- [x] Traces — not applicable, and that is the rule: no second hop, no trace
- [x] Errors — recorded as their own event class and surfaced by `ai-eng digest`
- [x] Health and data age — `ai-eng doctor`, and `ai-eng audit verify` walks every link
- [x] External check — the install matrix runs a stranger's first five minutes on three OSes
- [x] Second path — `doctor` reads the chain's head, `audit verify` recomputes every hash
- [x] Security — gitleaks, semgrep, trivy and zizmor in `just check`; SECURITY.md ships
