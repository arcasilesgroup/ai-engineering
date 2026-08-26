---
id: "039"
slug: documentation-discipline
status: draft
date: 2026-08-26
ref: ""
supersedes: ""
---

# Documentation discipline — writing for agents and readers

## Who this is for, and what it is worth to them

The repository owner (roadmap rows 8/10; this is the documentation half) and every
stranger whose skills, specs, plans and docs this framework produces. ai-engineering is a
writing machine: it authors `spec.md`, `plan.md`, `corpus.md`, `SKILL.md`, ADRs and the
Solution Intent page on every governed run. Those documents already pass mechanical limits
(fog ceiling, load tiers, output contract) but nothing codifies the *writing* itself: how
to make a document predictable to an agent (context pointers, the two loads, leading words,
pruning, completion criteria) and how to make spec prose safe for a human in controlled
language (ASD-STE100: one idea per sentence, one meaning per word). The discipline exists
in the wild (`writing-for-agents`, `technical-writer.md` in claude-agents, ASD-STE100) but
is not in this tree. This spec adds it as a reference the authoring skills load, records the
technical-writer decision, and states the file governance.

## Context and problem

**What is true today, measured in this tree on 2026-08-26:**

- The framework's own docs already meet **mechanical** craft rules: `contract.py` audits
  fog ceiling (`fog`), load tiers (`_load_tier_problems`), output contract
  (`_output_contract_problems`), anti-rationalization, appendix, Incorrect/Correct. Docs
  cannot be too dense, too long, or output-less.
- The **writing discipline** is absent: no reference names context pointers, the two loads
  (context vs cognitive), leading words, pruning, or completion criteria; and no mention of
  controlled language (ASD-STE100) exists anywhere in the repo (grep zero, verified this
  session). A spec or skill can be mechanically green and still hard for an agent to use.
- The candidate tools exist outside: `/Users/soydachi/repos/claude-agents/product/
  technical-writer.md` is a general documentation agent (API refs, READMEs, ADRs, Keep-a-
  Changelog) — it contains **no STE100**; the `writing-for-agents` skill the owner pasted
  codifies the agent-document levers; ASD-STE100 is the aerospace controlled-language
  standard. The NotebookLM research the owner cited is not reachable from this machine
  (`degraded-tool: notebooklm`), so this spec proceeds on the tree + the two given texts.
- File governance is already machine-listed: `ai-eng doctor` prints one line per file class
  with its exact home, and the `homes` recipe + `test_contract_craft` assert it; `docs/
  tools.md` is the human inventory. What is not stated is the *writing standard* for those
  files.

**The problem, in words a non-technical reader can follow:**

A framework that is always writing documents should write them the same good way every
time. Today its documents are checked for being too dense or too long, but not for whether
an agent can follow them or whether the words are controlled. Two known recipes for that —
writing so an agent uses the document reliably, and writing in controlled language so a
reader is never misled — exist but are not part of the framework. This spec makes them the
framework's documentation discipline: one reference the authoring skills load, the
technical-writer question answered, and the file governance stated.

## Options considered

1. **One references/documentation-writer.md + parseable corpus routes + the technical-writer
   decision recorded (chosen shape).** The reference carries writing-for-agents levers and
   STE100 rules; `ai-spec`, `ai-plan` and `ai-report` corpora gain a quoted route + refusal
   pointing at it (the parseable shape the harness reads); the technical-writer agent stays
   an insumo (the discipline is adopted, the vendor agent is not). Gives: the discipline
   reachable exactly where docs are written, decided, not scattered. Costs: one reference,
   three corpus additions, one fixture.
2. **Port the technical-writer agent as a framework skill.** Gives: a ready "documentation
   writer" skill. Costs: a new skill (the fifteen-skill target is deliberate), vendor
   frontmatter (`model: sonnet`, tools, memory), zero STE100 — the exact "adopt content, not
   pattern" the research warns about. Rejected.
3. **Prompt-only guidance.** Gives: zero code. Costs: the discipline stays unwritten, the
   "checked, or it rots" failure — a standard that is not a reachable reference and a
   routed rule is a standard nobody hits.

## Decision

**Option 1.** Spec 039 adds two behaviours and a decision:

### B-039-1 — The documentation discipline, as a reference

`references/documentation-writer.md` beside `ai-report` (the surface that already owns
writing and reporting): the writing-for-agents levers (context pointers and their wording,
context load vs cognitive load, leading words, pruning/single-source-of-truth, completion
criteria that are checkable and exhaustive, positive prompting over negation) plus the
STE100 controlled-language rules (one idea per sentence, one meaning per word, approved
vocabulary, short declarative sentences). It is loaded by the authoring skills through a
pointer only when they write a document — never always-loaded (context economy, spec 033).
The reference is the single source of the discipline; a spec, plan, corpus or skill is
checked against it by the existing craft lanes plus the reading human, not by a new
hard-coded prose rule.

### B-039-2 — Parseable corpus routes

`ai-spec`, `ai-plan` and `ai-report` gain, in the shape the harness parses (quoted
situations and `Not for … — …` refusals): a route that "the document must be written for
its agent-reader and its human-reader — load `references/documentation-writer.md` before
authoring", and a refusal when a doc hands an agent a vague completion bound or restates
what the environment already says. The corpus move is the checked half; the reference is
the material the route points to.

### D-039-01 — the technical-writer agent stays an insumo; the discipline is adopted.

The claude-agents `technical-writer.md` is read as evidence for what documentation skills
should do (API refs, ADRs, Keep-a-Changelog), not ported: its `model: sonnet`, tool list and
`memory: project` are runtime-specific, it contains no STE100, and the research already
classifies claude-agents as adopt-the-pattern-not-the-content. The *discipline* — and
STE100, which the technical-writer lacks — live in the reference. Anyone who wants the full
agent keeps it in claude-agents; the framework ships the standard.

### File governance (stated, not invented)

The homes are already real and machine-listed: `specs/NNN-slug/` (records), `docs/adr/`
(decisions), `.ai/` (pin, intent, receipts), `policy/` (data), `.agents/skills/` (skills),
`references/` beside each skill (disclosed material), `docs/` (page + tools inventory).
`ai-eng doctor` prints them; the `homes` recipe asserts them; `docs/tools.md` is the human
index. This spec adds the *writing standard* for those files; it does not move any home.

## Challenged once

**"A prose-discipline reference that no test enforces is exactly the 'checked, or it rots'
failure; why not enforce STE100 mechanically?"** The mechanical craft limits are already
enforced (fog, load tiers, output contract); a hard STE100 parser over the framework's own
docs would red them for corpus lines that are already optimal, and over *user* repos it
would be the same violation-of-ownership the framework forbids. The honest enforcement is
two-sided: the mechanical lanes stay, and the discipline becomes the *reachable* standard a
corpus route points at — so a doc that ignores it is a doc whose route names the reference
and the reader sees the miss. Re-adding a lighter check (a corpus-prose sentence cap) is
offered as a follow-up only if a measured run of this reference shows docs still drifting.

**"STE100 is aerospace maintenance English; specs are not maintenance manuals."** The
*controlled-language* property is the part that transfers — one idea per sentence, one
meaning per word, approved vocabulary — and it is exactly what a governed spec needs to be
unambiguous across many readers. The aerospace vocabulary list does not transfer; the
principle does. This spec names the principle and the reference keeps the concrete rules.

## Assumptions and unresolved risks

- Assumption: the reference, reachable through the corpus routes and loaded on demand,
  measurably improves the framework's own docs; this spec delivers it and the routes, and a
  later measured need may add a light prose check if drift is observed.
- Assumption: one shared reference is the right home for both writing-for-agents and STE100;
  splitting them is a trivial follow-up if a surface needs only one.
- Unresolved: whether ai-report, ai-spec, ai-plan are the only authoring surfaces; the corpus
  routes on those three are the first cut, and a later surface may point at the same
  reference.
- Unresolved: the NotebookLM research (`degraded-tool`) may contain STE100 workbook specifics
  this reference should absorb; when the notebook is reachable, fold its findings in.
- Unresolved: the inherited `madr.validate` red from ADR 0025 stays open; this spec does not
  authorise rewriting that history.

## Examples somebody can check

- **Success, reference:** Given `references/documentation-writer.md`, When `ai-report` loads
  it before authoring, Then it names context pointers, the two loads, leading words, pruning
  and the STE100 one-idea-one-sentence rule (`uv run --with pytest==9.1.1 pytest -q
  tests/test_039_documentation.py -k reference` → `1 passed`).
- **Denial, bare bound:** Given a corpus route whose doc hands an agent a vague completion
  bound ("understanding reached"), When the discipline's rule reads it, Then the route names
  the reference instead (`-k bare_bound` → `1 passed`).
- **Honest home:** Given the file-governance statement, When `ai-eng doctor` runs, Then it
  still prints one line per file class with its exact path (`just doctor` and the `homes`
  recipe pass; no home moved).

## Decisions

**D-039-01 — the documentation discipline ships as a reachable reference + parseable corpus
routes; the technical-writer agent stays an insumo, not a framework skill.**
Rationale: the framework writes on every run, so the *writing standard* is the transferable
asset; the claude-agents agent is runtime-specific, STE100-free, and the research already
classifies claude-agents as pattern-not-content. One reference + three routes is the
smallest reachable form.

**D-039-02 — file governance is the existing, machine-listed homes; this spec adds the
writing standard, it does not move or add a home.**
Rationale: doctor, the `homes` recipe and `docs/tools.md` already make the inventory real
and asserted; the gap this spec closes is the writing standard for the files, not their
location.

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command. This
specification adds one reference, three corpus routes and one fixture; no service, no URL,
no second hop — the service-shaped boxes are `not applicable`.

- [x] CI/CD — `just check` runs `tests/test_039_documentation.py` on every push (`.github/workflows/check.yml`); nothing deployed
- [x] Logs — not applicable: every verb still emits the one JSON line `ai-eng report digest` reads
- [x] Traces — not applicable: one process, no second hop
- [x] Errors — not applicable: the new path fails closed (a corpus route whose doc ignores the reference is refused by the route; no silent pass)
- [x] Health and data age — the 039 fixture runs in the gate's pytest half (`just cover`) on every push; the reference is asserted by its fixture
- [x] External check — `.github/workflows/check.yml` runs the whole gate on every push; the routes are asserted by `tests/skill_eval.py`, the independent route
- [x] Second path — the reference is read by its fixture and the routes by `skill_eval.py`, with no shared line
- [x] Security — `just security`: gitleaks, semgrep, trivy on every push, over a change that adds no dependency and no network call