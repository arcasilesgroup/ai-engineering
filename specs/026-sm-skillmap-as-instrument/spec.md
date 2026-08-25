---
id: "026"
slug: sm-skillmap-as-instrument
status: draft
date: 2026-08-25
ref: ""
supersedes: ""
---

# skill-map as the reference-integrity instrument

## Who this is for, and what it is worth to them

The maintainer who dogfoods the governed cycle and who, this month, has been told to lean
on `sm` (skill-map.ai) to keep the framework's skills, corpus, specs and ADRs honest about
their dependencies, integrations, formats and standards. Today that person has no checked
answer to "are the links in this tree real?" — a renamed skill, a re-homed corpus or a
reference to a spec that never landed goes unnoticed until a reader follows the link and
hits a dead end, or until a future spec builds on a document that anatomically is not
there.

The stranger who installs the wheel and whose surface shows a catalogue of skills. The
links between the skills' own documents — what a stage references, what follows it — are
part of what the map shows them. Right now nothing checks that those links survive a
rename or a move.

When this is done, `sm scan/check` is one more habit in the gate: a deterministic
reference-integrity sweep whose findings a person reads beside the lint and the tests,
with the template pattern `NNN-slug` excluded because it is a demo hole and not a
missing file.

## Context and problem

`sm` (skill-map.ai, v1.12.2) is executable-only, already installed on this machine and
already scanning this repository. Verified in this session with `sm scan` (156 nodes, 57
findings) and `sm check --json`:

- **40 findings are real: a genuinely missing reference.** They point at files that do
  not exist in the graph or on disk — `CHANGELOG.md → plan.md/spec.md`,
  `docs/adr/*.md → docs/adr/spec.md / plan.md / council.md / challenge.md`,
  `docs/audit-2026-08-16.md → docs/specs/010/plan.md / docs/corpus.md`, and two dozen
  `specs/NNN-*/SKILL.md` / `DESIGN.md` / `docs/thesis.md` links inside shipped records.
  Each is the exact failure the map exists to catch: a reference a reader would hit.
- **13 are template false positives.** They point at `specs/NNN-slug/spec.md`,
  `specs/NNN-slug/plan.md`, `…/council.md` and `…/challenge.md` — the framework's own
  demonstration pattern (`NNN-slug` is a hole, not a destination). A deterministic
  analyzer cannot tell these apart from a real missing target without an explicit
  exclusion list.
- **4 are deliberate redundancies** (severity `info`), where one target is reached twice
  and the spec itself declares the overlap intentional (e.g. `specs/023`).

The problem, in one sentence: the framework sells traceability that nobody checks, and the
one tool that would check it is already running but has no home in the gate, no exclusion
for its known false positives, and no record of what the 40 real defects are.

This is not AIX. It does not propose to build an instrument: it proposes to feed into the
cycle what the instrument already measured, and to make the instrument fail closed with a
test.

## Options considered

1. **Adopt `sm scan/check` as a gate recipe, with an explicit `NNN-slug` exclusion, and
   record the 40 real defects as a dated acceptance or a fix block.** The instrument
   already runs; the exclusion is a small data file (not a suppression — the analyzer
   still runs, it just knows the template hole is not a target). `just` gains one recipe
   (`map`) that runs `sm scan && sm check --json` and drinks a rendered digest. The 40
   defects become a checklist in a plan, fixed in the tree or accepted with a dated
   record. Costs: the wheel must not require `sm` at install — so it is bracketed:
   `just map` runs it when present and skips with a printed note when absent (the
   stranger install has no `sm` and the gate must still pass false-closed). A
   competitor must not be able to pass without the check. The live check is a habit on
   the maintainer machine, not a contract the install must seal.

2. **Treat `sm` as a manual investigative tool and fix the 40 by hand, no gate recipe.**
   Cheapest to ship; but the three-four overlap that `sm` caught once becomes opaque
   the next time a rename happens, and `docs/audit` keeps a checklist nobody is forced
   to read. It fixes today's rot and guarantees next week's. Loses on continuity.

3. **Do nothing — the repository already trusts prose.** This is the status quo that led
   to 40 dead references accumulating in the tree. Loses.

## Decision

Option 1, with the boundary stated in it. `sm` becomes a **reference-integrity
instrument**: the repository's own determinism check, the same way `sm check` is a
deterministic analyzer and `just check` runs it. Concretely:

- `just map` runs `sm scan` then `sm check --json`, and renders a digest;
- the `NNN-slug` pattern is carried in a data file (a set of allowed missing-target
  prefixes under the framework's docs), so the analyzer still reports it but the gate
  holds it as a known hole, not a fail;
- the four redundant `info` findings are recorded (if severity) as deliberate, not
  suppressed;
- the 40 real defects are not fixed in this trip. They are tracked (a plan block named
  in a future spec or accepted in a record), and this spec states that the instrument's
  first honest egregious finding is that 40 real links are dead. They leave the tree
  visible, not the tool.
- the wheel does not depend on `sm`; a Justfile recipe that DETECTS `sm` runs it, and
  one that cannot (a stranger machine) prints that map is not installed and still fails
  closed — the gate is the tree's own single recipe, not a requirement the install
  forces.

Because this decides how every future link in the framework's docs is checked, record it
as a decision with its own ADR once approved: propose `ai-eng decide --madr "skill-map is
the reference-integrity instrument of the governed cycle"` — a proposal, not this spec's
own approval.

## Challenged once

`sm`** — a stranger installs the source, and the gate looks green only because the
bracket the reader is invited to run by its own
`map` recipe is not on the stranger's machine, and the verdict comes back in prose
printed at run time, not in a failure the tree exports.
`sm`** — a stranger installs the source, `just a recipe seen at 01:00 is deemed green`
only because the elif branch notes "sm not installed". The second strongest: the 40 real
defects stay broken, so "adopting an instrument" changes no user-visible outcome except
a recipe line.

Both are real and neither defeats the decision. On the first: the install contract has
always been "stranger can install without a gate"; nothing in this spec changes that —
the `map` recipe is bracketed, exactly as each security scanner that is not in the wheel
is bracketed today (trivy, gitleaks, semgrep are `--with` runner choices; the gate never
requires them on the stranger's machine). The check is the maintainer's habit; the
tree's truth is the tree contract. On the second: the reason the 40 are never silently
"fixed" in this trip is exactly that fixing them needs evidence per link (which file
should it point at?), and evidence requires a reader, not a sweep. The spec orders the
fix into a tracked block with a record, not into this decision.

## Assumptions and unresolved risks

Assumed without proof: a maintainer will run `sm scan/check` in the gate and read the
44 real-vs-template digest it renders; the exclusion list is data, reloadable but
opinionated; and the wheel must not hard-depend on `sm` — the bracket and the printed
note are the designed stranger path.

Open: whether `NNN-slug` is the only template hole (a reader would confirm against the
codebooks); whether the 40 defects get fixed inline or in a plan block; and whether the
intentional `info` redundancies stay `info` or are suppressed. None of these stops the
instrument; all are review-visible.

## Examples somebody can check

Given the `map` case, When `just map` runs, Then it runs `sm scan` and
`sm check --json` and exits non-zero if the digest contains a real reference-broken
finding, and 0 once the 13 template holes are excluded and the 40 real defects are either
fixed or tracked. Checked by the recipe output being a digest, not a free text.

Given the exclusion list `NNN-slug` is present, When a template hole is scanned, Then it
is reported by the analyzer but excluded by the gate with a code footer that says
"template demo", not `✕`. Same recipe, checked by its digest.

Given the wheel is installed on a machine with no `sm`, When `just map` runs,
Then it prints "map not exercised; sm missing" and the stranger gate is still green —
the install never requires the instrument.

## Decisions

**D-026-01 — skill-map is the reference-integrity instrument of the governed tree.**
`just map` runs `sm scan && sm check --json`, carries the `NNN` template-hole exclusion
as data, and the stranger install skips the map with a printed note rather than failing.

**Rationale:** the instrument already exists and already works in this repo; the gap is
that nothing gates on it and its template false positives and real defects are
indistinguishable to a reader.

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command. This
specification changes a Justfile recipe and adds a data file; there is no network service
to deploy, so the deployment boxes are N/A and the gate is `just check` green.

- [ ] CI/CD — build, lint, test and security analysis on every push; deploy from the default branch
- [ ] Logs — structured JSON, one line per event, with level and service, to stdout
- [ ] Traces — only if this is our code and has more than one hop; no hop, no trace
- [ ] Errors — every uncaught exception leaves as a log with severity 17 and marks its span
- [ ] Health and data age — alive, age of the newest datum, and an independent recomputation
- [ ] External check — something outside the service verifies it and says what it could not check
- [ ] Second path — every published number recomputed by an independent route and compared
- [ ] Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI