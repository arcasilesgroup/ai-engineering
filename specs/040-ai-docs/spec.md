---
id: "040"
slug: ai-docs
status: draft
date: 2026-08-26
ref: ""
supersedes: ""
---

# The ai-docs skill — technical documentation with the framework's gates

## Who this is for, and what it is worth to them

The repository owner (roadmap rows 8/10 folded here) and every stranger who installs the
wheel and needs a README, a wiki page, product documentation, API docs or a technical post
written about their repository. Today the framework routes every other kind of writing
(changelog via ai-ship, specs/ADRs via ai-spec, notes via ai-note, issues via ai-report)
but the one kind it produces most often — technical documentation — has **no skill and no
gates**: it is done by the session model unprompted, against no standard, with no check
that the document is true (names real files), lean (does not restate the environment) or
complete (every section ends checkably). Spec 039 gave the framework the writing standard
(`references/documentation-writer.md`: writing-for-agents + STE100); this spec gives it the
surface that applies that standard with gates — the `ai-docs` skill — so the owner's
question "¿por dónde lo hacemos?" has a governed answer that is not "the model, by hand".

## Context and problem

**What is true today, measured in this tree on 2026-08-26:**

- The writing standard exists: `references/documentation-writer.md` beside `ai-report`
  (spec 039) names context pointers, the two loads, leading words, pruning, completion
  criteria, and the STE100 controlled-language rules; `ai-spec`, `ai-plan` and `ai-report`
  route their own authoring to it.
- The surfaces exist for every kind of writing **except** technical documentation:
  `ai-ship` owns "Update the changelog" (`.agents/skills/ai-ship/SKILL.md:31`),
  `ai-spec` + `ai-eng decide` own specs/ADRs, `ai-note` owns findings, `ai-report` owns
  issues and "one local draft and nothing else" (its corpus routes everything else
  elsewhere). README, wiki, docs de producto, API docs and posts have no owning skill and
  no capability declaration in `policy/capabilities.toml` — a session model reaches for
  "write me a README" with no route, no standard and no gate (`just map` has no reference
  to any docs surface).
- The candidate tool, `claude-agents/product/technical-writer.md`, is deliberately not
  portable (D-039-01): runtime-specific frontmatter (`model: sonnet`, `memory: project`),
  zero STE100, and the research classifies claude-agents as adopt-the-pattern-not-the-
  content.

**The problem, in words a non-technical reader can follow:**

The framework is a machine that writes documents, and it has a skill and gates for every
kind of document except the one people ask for most: the README, the wiki page, the product
docs, the technical post. Those are still written however the model happens to feel like
writing them, with nothing checking that they are true, lean or complete. This spec gives
that work a home: the `ai-docs` skill applies the writing standard from spec 039, routes
every other kind of document to its existing skill, and verifies each document it writes
against the repository before it calls it done.

## Options considered

1. **A new model-invoked `ai-docs` skill (chosen shape).** A skill in `.agents/skills/`
   under the existing contract (frontmatter + `corpus.md` Routes/Refuses), pointing at the
   039 reference as its single standard, routing changelog/spec/note/report to their
   existing homes, and verifying every document it writes (real files, no-cache, checkable
   sections, `not-covered` when something cannot be verified). A capability entry in
   `policy/capabilities.toml` (read the repo, write `docs/` + `README.md`, `before_write`).
   Gives: the missing surface with the framework's gates, no vendor port. Costs: one skill
   directory + one capability entry + the routing cases that move the `skill_eval`
   baseline.
2. **Amplify `ai-report` to own all technical documentation.** Gives: nothing new to
   create. Costs: `ai-report`'s contract is "issues and the one local draft"; growing it
   into a docs engine breaks its single responsibility and its "nothing else" refusal, and
   the baseline and craft lanes would fight it. Rejected.
3. **Keep the claude-agents technical-writer as the docs surface.** Gives: a ready writer.
   Costs: exactly D-039-01 — runtime-specific, no STE100, and a repository outside the
   framework's gates means an unverified README about a repo it did not read. Rejected on
   the same evidence.

## Decision

**Option 1.** Spec 040 adds the `ai-docs` skill:

### B-040-1 — The `ai-docs` skill

A model-invoked skill (description carries the trigger branches: "write the README",
"update the wiki", "document this API", "write a technical post about") whose body uses
`references/documentation-writer.md` (spec 039) as its single source of the writing
standard — progressive disclosure, no-cache (a doc never restates `--help` or config that
the environment already carries), leading words, and every section ending on a checkable
completion criterion (STE100 one-idea-one-sentence). It writes into the homes the user
names (README.md, docs/, a wiki dir) and none other without consent; a document it cannot
verify against the repository (a named file that does not exist, a claim no command or file
supports) exits `INCOMPLETE: not-covered <reason>` rather than inventing.

### B-040-2 — Routing without duplicating

`ai-docs`'s `corpus.md` carries the refusal half that keeps it apart: a changelog routes to
`/ai-ship`, a spec or ADR to `/ai-spec`, a finding to `/ai-note`, an issue to `/ai-report` —
and those four skills' corpora gain the reverse route (a request for README/wiki/product
docs routes to `/ai-docs`), so the routing harness sees distinct cases, never a fork. The
`skill_eval` baseline moves with the added cases, argued in the same commit.

### B-040-3 — The verification gate

`ai-docs`'s procedure verifies before done: every named file in the document exists in the
tree, no passage restates what the environment already says (no-cache), and each section
ends on a checkable completion criterion. A document-level fixture
(`tests/test_040_ai_docs.py`) proves the three states — a doc naming real files and checkable
sections passes, a doc repeating the environment or naming no real path is refused, and a
claim that cannot be verified exits `not-covered`.

### D-040-01 — the technical-writer purpose is adopted; the agent stays an insumo.

Same decision as D-039-01, applied to the docs surface: the framework ships the *skill with
gates* (the purpose), the claude-agents agent stays where it is (the vendor); anyone who
wants the full agent can still call it, but the framework's own docs surface is `ai-docs`.

## Challenged once

**"A seventeenth/eighteenth skill is exactly the skill-set inflation the dogfooding resists;
a README can be written by ai-report today."** The count is not pinned (no test asserts a
skill ceiling; the audit audits what exists). The objection that matters is SRP and routes:
`ai-report`'s own corpus refuses everything but its one draft — "the log file and the diff"
is refused outright ("no field for a log or a diff") and its routes push changelog/PR to
ai-ship. A README forced through ai-report would hit its own refusals. The gap is real and
measured; the cost is one skill directory that reuses the 039 standard and a capability
entry, not new machinery.

**"A docs skill that 'verifies against the tree' will refuse every post about the future
or a non-code topic."** The gate names the two honest exits: a document about the tree
verifies against it (files, commands, sections), and anything unverifiable — a forward-
looking post, a product claim — exits `not-covered: <reason>` with the reason recorded,
exactly as 036/039 do. A post is never refused for being a post; it is refused only for
claiming to be verified when it is not, which is the false-green the framework exists to
stop.

## Assumptions and unresolved risks

- Assumption: README/wiki/docs de producto/posts are the right first surface for ai-docs;
  API-reference generation and dashboards may join as measured need, through the same skill.
- Assumption: the routing-refusal pairs (ai-docs → the four, the four → ai-docs) keep the
  harness honest without forking it; the fixture and the baseline move prove it.
- Unresolved: `docs/tools.md` (the human inventory) is updated by this spec's build so the
  new surface is discoverable; the `skill_map`'s accepted/reference bookkeeping absorbs the
  new skill's references (the map's prohibition on broken references applies; ai-docs's
  references point at real files).
- Unresolved: the inherited `madr.validate` red from ADR 0025 stays open; this spec does
  not authorise rewriting that history.

## Examples somebody can check

- **Success, verified doc:** Given a README that names only real files, does not restate the
  environment, and ends each section checkably, When ai-docs verifies it, Then it passes
  (`uv run --with pytest==9.1.1 pytest -q tests/test_040_ai_docs.py -k verified` → `1 passed`).
- **Denial, no-cache:** Given a doc that repeats the environment (`--help` output, config
  the repo already carries), When ai-docs verifies it, Then it is refused (`-k no_cache` →
  `1 passed`).
- **Honest exit:** Given a post whose claims cannot be verified against the tree, When
  ai-docs verifies it, Then it exits `not-covered: <reason>` (`-k not_covered` → `1 passed`).
- **Routing:** Given a request for "update the wiki", When ai-docs's corpus reads it, Then
  it is a taken route, and a changelog routes to `/ai-ship`, never here
  (`-k routing` → `1 passed`).

## Decisions

**D-040-01 — the framework's technical-documentation surface is a new `ai-docs` skill with
gates; the claude-agents writer stays an insumo.**
Rationale: every other document kind has a routed, gated home; technical docs had none, and
the 039 standard had no surface to apply to. One skill reusing the standard and a
capability entry closes the measured gap without porting a vendor agent.

**D-040-02 — ai-docs verifies every document against the tree, and anything unverifiable
exits `not-covered`, never a false pass.**
Rationale: a README that names a file that does not exist or restates the environment is
the false-green the framework exists to stop; the honesty rule of 036/039 applies to the
docs surface exactly as it does to the verifier and the design floor.

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command. This
specification adds one skill, one capability entry, routing refusals and one fixture; no
service, no URL, no second hop — the service-shaped boxes are `not applicable`.

- [ ] CI/CD — ticked by the plan's gate: `just check` runs the 040 fixture once it exists (`.github/workflows/check.yml`); nothing deployed
- [x] Logs — not applicable: every verb still emits the one JSON line `ai-eng report digest` reads
- [x] Traces — not applicable: one process, no second hop
- [x] Errors — not applicable: the new path fails closed (no-cache and unverifiable claims are refused; a `not-covered` reason is the honest exit)
- [ ] Health and data age — ticked by the plan's gate: the 040 fixture runs in `just cover`'s pytest half once it exists
- [x] External check — `.github/workflows/check.yml` runs the whole gate on every push; the routing refusals are asserted by `tests/skill_eval.py` once the corpus move lands
- [ ] Second path — ticked by the plan's gate: the skill read by its fixture and the routes by `skill_eval.py`, with no shared line
- [x] Security — `just security`: gitleaks, semgrep, trivy on every push, over a change that adds no dependency and no network call