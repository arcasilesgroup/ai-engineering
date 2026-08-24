---
id: "024"
slug: autonomy-and-install
status: draft
date: 2026-08-24
ref: ""
supersedes: ""
---

# Autonomy and install

## Who this is for, and what it is worth to them

The repository owner, who signs specifications and accepts risks, and the stranger who
installs this wheel on a fresh machine and expects it to govern the repository they are
standing in.

The research report `.ai/reports/006-autonomy-and-install-research.html` [R, cited below
as "report 006"] was written
for this specification: it says, in its own opening words, that it is "the research input
for the next spec and plan", that "the brainstorming half of that spec is the discovery
step of `/ai-spec`", and that it "feeds [it] rather than replaces [it]". This record is
that spec. It decides which of the report's decision-ready options land in this wave, in
whose home they land, and which are written down as constraints on specifications that do
not exist yet.

## Context and problem

For a non-technical reader: `ai-eng init` today sets up the machine and, only if you
remember to pass `--project`, also sets up the repository you are standing in. New clones
start with no safety floor at all until someone runs `init --project` in them. The sixteen
skills are measured one file at a time, but nothing measures the whole catalogue a surface
actually loads, so a future skill could silently stop being visible on one
editor. The project's own rule is that everything open source is in English; the record
disagrees in three committed places. Two of the five gaps the research names — per-stack
security lanes and a PII lane — are already committed to a later security wave (P4) by
specification 010, but nothing says what lands now.

What is true today, read from the tree rather than from the report:

1. **Hooks are per-repository, deliberately.** `src/ai_engineering/wiring.py` `wire_git`
   writes `core.hooksPath`, `ai.managed` and `ai.eng` into the *repository's* git config
   (verified in `wire_git`, lines 668-674), and its docstring refuses a global
   `core.hooksPath` in the words "that would impose our commit convention on every foreign
   clone on the machine, forks included". A new clone has nothing of this until a person
   runs `init --project`.
2. **`init` requires `--project` to be remembered.** `init.py` `main` runs
   `global_step` unconditionally and `project_step` only when `args.project is not None`
   (verified in `main`, lines 836-839, and in the `parse` help). There is no context
   detection: run inside a repository and it still does global-only unless you say
   `--project .`.
3. **Skills are measured per file, not per catalog.** `contract.py`
   `DESCRIPTION_MAX = 1000` and `audit_one` checks name, description, the `Not for`
   clause and the two corpus sections (verified). Nothing sums `name + description`
   across the catalogue, so nothing enforces the 50 KB catalog budget that Zed documents
   and the open Agent Skills specification implies for per-surface loading [R].
4. **The English rule has three committed exceptions.** `docs/tools.md` is a Spanish
   cheat-sheet (read this session: "Guía rápida de comandos"), the generated
   `docs/solution-intent.html` is Spanish, and `.ai/reports/001-005` are Spanish
   archives. The tree's own rule, stated in `AGENTS.md` ("the project is always in
   English because it is open source") and in report 006, is contradicted by committed,
   reviewed artifacts.
5. **Two lanes and one verifier are already committed elsewhere.** Spec 010's P4
   normatively requires "pinned stack-appropriate scanner lanes" (verified in
   `specs/010` `### P4 — security and release evidence`) and its P1/P2 require the
   surface adapter contract. The threat model names the supply-chain verifier gap:
   `policy/threat-model.toml` `supply-chain` boundary has `reason` saying exactly
   "what is still missing is the half `EP-047` and `EP-280` name that no local work can
   reach: nobody has fetched a published artefact from the index and checked it against
   either" (verified).
6. **The working tree already carries one uncommitted fix in this territory.** The
   shared-skills-root collision handling in `init.py` / `wiring.py` — a name-and-skip
   rule for foreign folders — is currently uncommitted on branch
   `spec/023-council-substitution` (verified in the working tree this session). It is
   part of the same autonomy-and-install wave this spec covers, and it must land in its
   own commit; this spec neither folds it in nor rewrites it.

The harm of leaving it unchanged: every new clone starts ungoverned, so the moment a
stranger clones a repository is exactly the moment nothing of the framework runs; `init`
asks the person to remember a split the tool could detect; the skills guarantee is "not
one word over" in one file but not across the catalogue a surface actually reads; and
the project that sells "English always" violates its own committed record in three
places, which is the failure this product says it exists to cure — a rule that is not
checked is a rule that is not kept.

## Options considered

1. **Ship the full research block now: all five options plus the English fix in one
   wave.** Gives everything at once; costs a very large single change against the
   repository's own rule 1 ("no code before an approved plan", and the one-commit-one-
   change doctrine), two new pinned scanner rule sets (per-stack SAST) and a PII scanner
   whose very choice the research marks `unsourced` — a heuristic that must not over-
   block. It rules out keeping the wave reversible, and it would land the two P4 lanes
   ahead of the P4 wave they were designed inside, ahead of the pinning machinery that
   wave introduces. *Not chosen.*
2. **Ship the four automations that stay inside the installer's already declared write
   scope and are reversible, defer the two lanes to P4, and keep the supply-chain
   verifier open with a dated next action.** Costs the two deferred lanes now (they were
   already committed to P4 by spec 010); gains the audience of the research now:
   templateDir opt-in for new clones, context-aware `init`, a measurable catalogue
   budget, and the English rule restored in the record. *Chosen.*
3. **Change nothing; treat the research as information.** Cheapest; keeps every gap
   exactly as listed, and abandons the entire exercise, because a report neither governs
   nor installs anything. The research exists precisely because the gaps above are
   cheaper to close now than to keep paying.

## Decision

Choose option 2, as a wave with the following parts, each landed in its own reviewed commit:

- **D-024-01 — hybrid hook model, opt-in `init.templateDir`, never a global
  `core.hooksPath`.** Keep the per-repository `core.hooksPath` floor exactly as
  `wiring.wire_git` builds it. Add an *opt-in* machine-scope step that writes
  `git config --global init.templateDir` to a directory this product owns, so *new*
  clones start with the hooks already in place. The template hooks pass cleanly on a
  repository that never opted into the configuration (the "skip-on-missing-config"
  behaviour pre-commit documents [R]), and the opt-in is a person at the keyboard, not a
  default. `uninstall` removes the template directory and the global key. A global
  `core.hooksPath` remains forbidden (it is already forbidden in `wire_git`).
- **D-024-02: `init` becomes context-aware.** Run inside a repository, `init` offers
  the project half after the global half; run outside, global only. `--global`,
  `--project`, `--no-project`, `--dry-run`, `-y` keep their meaning. The only behavior
  change is that the split stops needing to be remembered: `init` in a directory that
  `git rev-parse --is-inside-work-tree` answers yes for offers the project step.
- **D-024-03: a measurable catalogue budget.** `contract.py` gains one assertion that
  the sum of every `ai-*` skill's `name + description` stays under the catalogue budget
  a surface actually enforces (Zed's 50 KB is the smallest documented one [R]). The
  per-file `DESCRIPTION_MAX` stays 1000; the divergence from the open standard's 1,024
  character cap is deliberate and recorded (see Decisions).
- **D-024-04: English-first in the record.** Translate `docs/tools.md` and regenerate
  `docs/solution-intent.html` from its generator in English. Reports 001-005 stay as
  preserved archival records, with a note in this spec and in the changelog that they
  are historical snapshots deliberately not rewritten. The generator is
  `src/ai_engineering/solution_intent.py` [R].
- **D-024-05: P4 owns the per-stack and PII lanes.** The two lanes spec 010 already
  commits to P4 — pinned stack-appropriate scanner rule sets, and the PII scanning
  lane at the git floor — remain P4 work. This spec records the constraint that they
  land there, and declines to spend the P0.5 budget on them now.

The supply-chain verifier (`EP-047` / `EP-280`) is not a decision this wave can make: it
requires a published release and network access to fetch it, and no local work can satisfy
it [R]. It stays open, named in the threat model and in this spec's risks, with the
next action being the first release that is actually published from this tree.

## Challenged once

**Failure case: splitting into "now" and "P4" lets the PII lane evaporate.** The report
calls PII "the one genuine security gap" and the One Page reads like an argument to close
it now. If this spec defers it, a future release can merge another wave without ever
coming back to it, and the gap stays open. — Justice ahead: the two lanes are already
normatively assigned to P4 by spec 010 (verified) — they are not abandoned, just
sequenced. But that was written before a wave, and a proposal that is not executed is a
proposal. So the spec hardens the commitment: the future P4 spec *must not* drop the
lane, and the record in the Decisions section keeps a line in this spec with the exact
P4 dependency. If, when P4 plans, the lane still has no published scanner to pin, the
rules require a superseding specification before the lane is dropped — "may not decide
whether a requirement lands" (spec 010). The failure case defeats only a slightly
weaker version of this choice; the version with the recorded P4 dependency keeps the
commitment. Kept.

## Assumptions and unresolved risks

**Assumptions** (taken as true without proof, must be re-checked before they become
facts):

1. Zed's 50 KB catalogue budget is the smallest documented budget across the eight tabled
   surfaces, and a skill catalogue that fits it fits every surface. (Fits the research;
   not independently verified against the other seven vendors this session.)
2. `init.templateDir` does not interfere with a repository that later runs
   `init --project`: the per-repo `core.hooksPath` set by `wire_git` wins for governed
   repositories, and the template hooks sit unused in `.git/hooks/` but harmless. This is
   plain reading of git's own precedence, but nobody has run the two in sequence on a
   real clone this session.
3. The translator / regeneration can produce faithful English for the two artifacts
   without loss of meaning. The generator is a template, so regeneration is mechanical;
   the translation of `tools.md` involves judgement over command names.

**Unresolved risks** (each open, not acceptance; owners and green results not invented):

- `EP-047`/`EP-280` supply-chain verifier — cannot close without a published release and
  network; next action: the first release from this index, then `fetch + verify
  attestation + SBOM against the index bytes`. No owner invented; it is named in
  `policy/threat-model.toml`.
- The per-stack and PII lanes are deferred to P4; the report marks the PII scanner
  choice as `unsourced` there, and nothing here asserts a scanner exists to pin.
- Opening the machine's git config with a new global key is a new writable surface for
  `init .` to manage; `uninstall` must remove it. The receipt grows a row for it.
- The shared-root collision fix already in the working tree is uncommitted; this spec takes it
  as a true current fact and depends on the fixes landing in their own commit before the
  automations this spec decides can be measured. If it is reverted, D-024-03's tests
  will red and the spec's claim of "sixteen skills and four guards" is unmeasured.

**What is not true**: there is no approval of anything in this spec yet; the
production-ready boxes below are all still unticked; and report 006 changes nothing on its
own (its own footer says so: "Research report. Not a spec, a plan, an approval, a PASS or
   a risk acceptance. It changes nothing.").

## Examples somebody can check

Given a machine where `ai-eng init --hooks-template` has been run and a new repository is
`git clone`d, When the first commit is staged and made, Then the pre-commit callback runs
without any additional command and the repository is unchanged. Checked by
`ai-eng doctor` in that clone, which shows `git hook` at `ok`.

Given a terminal inside a git worktree, When `ai-eng init` is run with no flags and a
person is answering, Then it asks whether to set up this repository and writes the project
files only on that yes. Checked by `uv run pytest -q
  tests/test_stranger_install.py::test_bare_init_inside_a_repo_offers_the_project_step`,
and its two neighbours pin the denial: `ai-eng init -y` inside a repo stays global-only,
and `echo n | ai-eng init` skips the project step and reports `CANCELLED`.

Given a machine with the wheel installed, When `ai-eng init --global` runs (as opposed to
the opt-in template flag), Then the global step does not write `core.hooksPath` at machine
scope; the per-repo row is the only hooksPath a person writes. Checked by `uv run pytest -q
  tests/test_stranger_install.py::test_hooks_template_writes_the_template_and_never_a_global_hooks_path`.

Given a future skill whose name plus description would exceed the 50 KB catalogue budget,
When `just check` runs the skills audit, Then the check fails naming the catalogue budget
and the top contributor. Checked by `uv run --with pytest==9.1.1 pytest -q
  tests/test_contracts.py::test_the_catalogue_fits_the_smallest_documented_budget`,
whose assertion refuses a synthetic seventeenth skill over the budget.

Given a future `policy/surfaces.toml` row whose vendor documents a catalogue budget
smaller than the verified 50 KB constant, When the audit assertion runs, Then the result
is `INCOMPLETE` naming the surface and its budget rather than silently assuming 50 KB
fits it. Checked by the same catalogue test, which cannot pass on a surface with a smaller
documented budget.

Given the tree after the English work lands, When a reader runs `grep -r "Guía rápida"
docs/`, Then nothing matches except the preserved `.ai/reports/` archives. Checked by
`uv run --with pytest==9.1.1 pytest -q tests/test_quality_gate.py::test_no_spanish_in_docs`, and
regeneration of `docs/solution-intent.html` from `ai-eng report intent --html` carries no Spanish.

## Decisions

**D-024-01 — keep the per-repository hook floor; add an opt-in `init.templateDir`
  so new clones start with hooks; never set a global `core.hooksPath`.**
**Rationale:** the research documents that git itself warns against a global/System hook
install on untrusted repositories, pre-commit's own docs say the same, and the middle
ground — a template that copies into *new* clones only — is the documented compromise.
It reverses nothing that was shipped; `wire_git` keeps building the per-repo floor. Like
the global hooks it does not replace, the template only exists where a person said
"yes".

**D-024-02 — `init` becomes context-aware: inside a repository it offers the project
   step after the global step; outside it does global only. Flags stay exact.**
**Rationale:** the manual split is the exact thing a person has to remember, and the
repo's own drift ("init says what it did" spec 005) shows the tool works best when the
default is the right thing. Keeping `-y` and `--project PATH`/`--no-project` as the
explicit forms preserves the no-surprise promise for scripts: context-awareness is
added only when a human is answering, never to an unattended run. (Caveat recorded: the
unattended `-y` inside a repo must not suddenly take the project half — it stays global-
only today.)

**D-024-03 — a measurable catalogue budget in `contract.py`; the sum of every skill's
   `name + description` stays inside the smallest documented catalogue budget.
   `DESCRIPTION_MAX` stays 1000 and the open standard's 1,024 is deliberately not
   adopted.**
**Rationale:** "not one word over" is currently true per file and unmeasured across a
catalogue; a surface that drops a skill silently is the exact failure the project
exists to expose. The 1,000-character budget is a deliberate, recorded divergence — the
contract's other checks (the `Not for` clause, corpus) are already stricter than the
open specification —
see research 5.2 [R]. The consequences of a future surface with a
lower budget become `INCOMPLETE`, not a silent drop.

**D-024-04 — the record is English again: translate `docs/tools.md`, regenerate
   `docs/solution-intent.html` from its generator in English. Reports 001-005 stay
   as preserved historical records, with the note in this spec and in the
   changelog.**
**Rationale:** the project's own rule is English-always for open source; the three
exceptions now violate it in committed, reviewed artifacts. History is not revised —
001-005 are dated snapshots of prior states and "never rewrite history" is the
constitution's own rule; the note is the fix, and the changelog carries it.

**D-024-05 — the PII lane is a file-boundary lane, not a guard, is already P4 work
   in spec 010, and is deferred, with the P4 dependency recorded here.**
**Rationale:** the research's own option 5 says the fix is "a scanning lane, not a
fifth guard" — data never to be written is caught at the file boundary, and the
guard layer decides calls. The PII lane and per-stack SAST both land inside P4's
"pinned stack-appropriate scanner lanes" contract (spec 010, `### P4`). Shipping them
ahead of the P4 wave would spend the whole wave budget on two lanes that P4 must
own. Defer is a scheduling decision, not a repeal.

## Accepted risks

Nothing accepted in this draft. The risk rows this wave depends on (the supply-chain
verifier, R-007-02 `fix-never-run-off-linux`) are re-read from where they already live;
an acceptance requires the person who owns them.

## Production-ready

Nothing gets a URL until every box is ticked by a command, and each here is unticked
this draft:

- [ ] CI/CD — `just check` on every push of this spec's future plan; this commit carries
  no CI change
- [ ] Logs — `ai-eng report digest` covers the new opt-in runs; `--hooks-template`
  writes one command event
- [ ] Traces — one process, no second hop, no trace (the existing rule held)
- [ ] Errors — the new `init` context path reports `INCOMPLETE` on an
  unreadable `project` case; the old errors keep their reasons
- [ ] Health and data age — `ai-eng doctor` gains one assertion if the legacy
  `init --hooks-template` writes a key (D1), and the 25 existing stay quoted as they are
- [ ] External check — the install matrix grows a templateDir row per platform once
  the fix is on (mirror of R-007-02, now with a real `--fix` path)
- [ ] Second path — the catalogue budget is both asserted in CI and named in
  report; the harness of report is currently local (spec 010 P2) so this second
  path is the testsuite's own run, not a second web path
- [ ] Security — `just security` covers the new tree; PII stays in P4 as decided

## Linked records

- This spec reads `specs/010` (P0-P5 wave contracts) and record
  `specs/007` (install) as the immediate family.
- The supply-chain boundary is `policy/threat-model.toml` / `src/ai_engineering/sbom.py`, naming
  `EP-047` and `EP-280`.
- The English objections are evidenced in `docs/tools.md` and the generator
  `src/ai_engineering/solution_intent.py`.