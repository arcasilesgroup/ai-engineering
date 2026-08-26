---
id: "040"
slug: ai-write
status: draft
date: 2026-08-26
ref: ""
supersedes: ""
---

# The ai-write skill — technical documentation with the framework's gates

## Who this is for, and what it is worth to them

The repository owner (who asked "¿por dónde lo hacemos?" for technical writing) and every
stranger who installs the wheel and needs a README, a wiki page, product documentation,
API docs or a technical post about their repository. Today the framework routes every other
kind of writing (changelog via ai-ship, specs/ADRs via ai-spec, notes via ai-note, issues
via ai-report) but the kind it produces most often — technical documentation — has **no
skill and no gates**: it is done by the session model unprompted, against no standard, with
no check that the document is true (names real files), lean (does not restate the
environment) or complete (every section ends checkably). Spec 039 gave the framework the
writing standard (`.agents/skills/ai-report/references/documentation-writer.md`: writing-for-agents + STE100); this
spec gives it the surface that applies that standard with gates — the `ai-write` skill.

## Context and problem

**What is true today, measured in this tree on 2026-08-26:**

- The writing standard exists: `.agents/skills/ai-report/references/documentation-writer.md` beside `ai-report`
  (spec 039) names context pointers, the two loads, leading words, pruning, completion
  criteria and the STE100 rules; `ai-spec`, `ai-plan` and `ai-report` route their own
  authoring to it.
- The surfaces exist for every kind of writing **except** technical documentation:
  `ai-ship` owns the changelog (`.agents/skills/ai-ship/SKILL.md:31`), `ai-spec` +
  `ai-eng decide` own specs/ADRs, `ai-note` owns findings, `ai-report` owns issues and
  "one local draft and nothing else" (its corpus refuses a log or a diff outright). README,
  wiki, docs de producto, API docs and posts have no owning skill and no capability
  declaration in `policy/capabilities.toml` (19 ids, none for this surface).
- **The name `ai-docs` is already taken by the record**: spec 010 `:414` lists `ai-docs`
  among the nineteen skills absorbed into target skills or deterministic code. The old docs
  surface was absorbed (into ai-report); the measured gap is that absorption left technical
  documentation uncovered. This spec's surface is named **`ai-write`** — a new skill, not a
  revival of the absorbed name.
- **The skill count is pinned by prose, not by a ceiling**: `tests/test_contracts.py`
  (COUNTED) pins README's "Seventeen written procedures" and AGENTS.md's "carries
  seventeen skills" to the derived count of `ai-*` skill directories. Adding a skill
  reds that test until README.md and AGENTS.md both say "eighteen". There is no numeric
  ceiling; the count is real and must move with the skill.
- **`just map` is red on main today**: 313 findings, 12 template holes, 77 accepted, 208
  real-and-unaccepted, exit 1 — including the 039 corpus routes themselves. Absorption is
  by exact accepted `(node, target)` pairs with a dated record, never automatic; a new
  skill's references join the real set until accepted. The map red is pre-existing (the
  039 block did not land its acceptances); this block accepts **its own** references
  (ai-write's and the 039 documentation routes) with the dated record, and verifies map's
  real count does not grow beyond the pre-existing 208 before the block's acceptances.
- The candidate tool, `claude-agents/product/technical-writer.md`, stays an insumo:
  runtime-specific frontmatter (`model: sonnet`, `memory: project`), zero STE100 (verified
  by the 039 challenge), and the research's domain-content principle classifies
  claude-agents as adopt-the-pattern-not-the-content.

**The problem, in words a non-technical reader can follow:**

The framework is a machine that writes documents, and it has a skill and gates for every
kind of document except the one people ask for most: the README, the wiki page, the product
docs, the technical post. Those are still written however the model happens to feel like
writing them, with nothing checking that they are true, lean or complete. This spec gives
that work a home: the `ai-write` skill applies the writing standard from spec 039, routes
every other kind of document to its existing skill, and verifies each document it writes
against the repository before it calls it done.

## Options considered

1. **A new model-invoked `ai-write` skill (chosen shape).** A skill in `.agents/skills/`
   under the existing contract (frontmatter + `corpus.md` (its Routes/Refuses)), pointing at the
   039 reference as its single standard, routing changelog/spec/note/report to their
   existing homes, and verifying every document it writes (real files, no-cache, checkable
   sections, `not-covered` when something cannot be verified). A complete capability entry
   (all mode fields: id, read_roots, write_roots, exec_allowlist, network, secrets,
   human_gate, enforcement, proof_requirements). Gives: the missing surface with the
   framework's gates, no vendor port. Costs: one skill directory, one capability entry,
   the prose count move (README/AGENTS "eighteen"), the map acceptances and the
   `skill_eval` baseline move.
2. **Amplify `ai-report` to own all technical documentation.** Gives: nothing new to
   create. Costs: `ai-report`'s contract is "issues and the one local draft"; growing it
   into a docs engine breaks its single responsibility and its own refusals, and the craft
   lanes would fight it. Rejected.
3. **Keep the claude-agents technical-writer as the docs surface.** Gives: a ready writer.
   Costs: exactly the evidence above — runtime-specific, no STE100, and a repository
   outside the framework's gates means an unverified README about a repo it did not read.
   Rejected on the same evidence.

## Decision

**Option 1.** Spec 040 adds the `ai-write` skill:

### B-040-1 — The `ai-write` skill

A model-invoked skill (description carries the trigger branches: "write the README",
"update the wiki", "document this API", "write a technical post about") whose body uses
`.agents/skills/ai-report/references/documentation-writer.md` (spec 039) as its single source of the writing
standard — progressive disclosure, no-cache (a doc never restates `--help` or config the
environment already carries), leading words, and every section ending on a checkable
completion criterion (STE100 one-idea-one-sentence). It writes into the homes the user
names (README.md, docs/, a wiki dir) and none other without consent. The skill set moves
from seventeen to eighteen; README.md ("Seventeen written procedures") and AGENTS.md
("carries seventeen skills") move to "eighteen" with it.

### B-040-2 — Routing without duplicating

`ai-write`'s corpus carries the refusal half that keeps it apart: a changelog routes
to `/ai-ship`, a spec or ADR to `/ai-spec`, a finding to `/ai-note`, an issue to
`/ai-report` — and those four skills' corpora gain the reverse route (a request for
README/wiki/product docs routes to `/ai-write`), so the routing harness sees distinct
cases, never a fork. The `skill_eval` baseline moves with the added cases, argued in the
same commit.

### B-040-3 — The verification gate and the second reader

`ai-write` verifies before done: every named file in the document exists in the tree, no
passage restates what the environment already says (no-cache), and each section ends on a
checkable completion criterion. The three states and the `not-covered` vocabulary are
**defined by the fixture and the contract** (`tests/test_040_ai_write.py`), never invented
at write time. A finished document has a second reader: the commit that lands it goes
through the normal diff review (ai-review on the change) like any other change — the skill
never auto-approves its own output.

### D-040-01 — the technical-writer purpose is adopted; the agent stays an insumo; the
surface is `ai-write`, not the absorbed `ai-docs` name.

The framework ships the skill with gates (the purpose); the claude-agents agent stays where
it is (the vendor); and the skill's name is `ai-write` because `ai-docs` is recorded as an
absorbed skill in spec 010 `:414` — reviving the name would collide with that record.

## Challenged once

**"A skill-count move and a map cleanup are scope creep for a docs skill."** The count is
pinned by prose, not a ceiling: shipping the skill without moving README/AGENTS reds the
same gate shipping it completes. The map acceptances are limited to this block's own
references (ai-write's and the 039 documentation routes) with a dated record; the 208
pre-existing real references are named as pre-existing and verified not to grow, not
cleaned here. Both are the honest cost of the surface, not creep.

**"A docs skill that 'verifies against the tree' will refuse every post about the future
or a non-code topic."** The gate names the two honest exits: a document about the tree
verifies against it (files, commands, sections), and anything unverifiable exits
`not-covered: <reason>` with the reason recorded — the same honesty rule as the verifier
(B-035-2) and the design floor (spec 038). A post is never refused for being a post; it is
refused only for claiming to be verified when it is not.

## Assumptions and unresolved risks

- Assumption: README/wiki/docs de producto/posts are the right first surface; API-reference
  generation and dashboards may join as measured need, through the same skill.
- Assumption: the routing-refusal pairs (ai-write → the four, the four → ai-write) keep the
  harness honest without forking it; the fixture and the baseline move prove it.
- Unresolved: the 208 pre-existing map reals stay one block's repair away; this block
  accepts only its own references and verifies the count does not grow.
- Unresolved: the inherited `madr.validate` red from ADR 0025 stays open; this spec does
  not authorise rewriting that history.

## Examples somebody can check

- **Success, verified doc:** Given a README that names only real files, does not restate the
  environment, and ends each section checkably, When ai-write verifies it, Then it passes
  (`uv run --with pytest==9.1.1 pytest -q tests/test_040_ai_write.py -k verified` → `1 passed`).
- **Denial, no-cache:** Given a doc that repeats the environment, When ai-write verifies
  it, Then it is refused (`-k no_cache` → `1 passed`).
- **Honest exit:** Given a post whose claims cannot be verified against the tree, When
  ai-write verifies it, Then it exits `not-covered: <reason>` (`-k not_covered` → `1 passed`).
- **Routing:** Given "update the wiki", When ai-write's corpus reads it, Then it is a taken
  route, and a changelog routes to `/ai-ship`, never here (`-k routing` → `1 passed`).
- **Count moves:** Given the skill shipped, When `tests/test_contracts.py` (COUNTED) runs,
  Then README.md and AGENTS.md say "eighteen" and the derived count matches
  (`-k count` → `1 passed`).

## Decisions

**D-040-01 — the framework's technical-documentation surface is a new `ai-write` skill
with gates; the claude-agents writer stays an insumo; `ai-docs` stays an absorbed name.**
Rationale: every other document kind has a routed, gated home; technical docs had none, and
the 039 standard had no surface to apply to. One skill reusing the standard closes the
measured gap without porting a vendor agent, and the name avoidss the spec 010 absorbed-
skill record.

**D-040-02 — ai-write verifies every document against the tree, with the vocabulary and
second reader defined by the fixture and the contract, never invented at write time.**
Rationale: a README that names a file that does not exist or restates the environment is
the false-green the framework exists to stop; the honesty rule of the verifier and the
design floor applies to the docs surface exactly as it does to them, and no document
auto-approves itself.

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command. This
specification adds one skill, one capability entry, routing refusals, the count move and
one fixture; no service, no URL, no second hop — the service-shaped boxes are
`not applicable`.

- [ ] CI/CD — ticked by the plan's gate: `just check` runs the 040 fixture once it exists (`.github/workflows/check.yml`); nothing deployed
- [x] Logs — not applicable: every verb still emits the one JSON line `ai-eng report digest` reads
- [x] Traces — not applicable: one process, no second hop
- [x] Errors — not applicable: the new path fails closed (no-cache and unverifiable claims are refused; a `not-covered` reason is the honest exit)
- [ ] Health and data age — ticked by the plan's gate: the 040 fixture runs in `just cover`'s pytest half once it exists
- [x] External check — `.github/workflows/check.yml` runs the whole gate on every push; the routing refusals are asserted by `tests/skill_eval.py` once the corpus move lands
- [ ] Second path — ticked by the plan's gate: the skill read by its fixture and the routes by `skill_eval.py`, with no shared line; the document's diff is reviewed by ai-review like any change
- [x] Security — `just security`: gitleaks, semgrep, trivy on every push, over a change that adds no dependency and no network call