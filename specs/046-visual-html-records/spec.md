---
id: "046"
slug: visual-html-records
status: draft
date: 2026-08-28
ref: ""
supersedes: ""
---

# Visual HTML records: pages for research, spec, plan and recap, and a visual PR review

## Who this is for, and what it is worth to them

The person at the gate and the reviewer on the PR. Today they approve a spec by reading raw
Markdown in a terminal, judge a build by scrolling a diff, and see an agent's work as chat
prose. They asked, in so many words, for the richness agent-native sells — diagrams, file
maps, annotated diffs, per-file tabs, UI before/after — but generated **in this repo, by
the skills, as HTML**, with every page handed over in chat as a clickable link that opens
the browser ("UX para quienes estamos en el otro lado"). What this is worth: a decision
scanned in one page instead of reconstructed from Markdown and scrollback, and a PR whose
shape is legible before line-by-line review starts.

## Context and facts

Each verified this session; evidence trail in `.ai/reports/021-skills-integration-roadmap.
html` (audits `SkillsAudit`, `FrameworkAudit`):

- Research already lands as self-contained HTML at `.ai/reports/NNN-name.html` — the shape
  pinned by `doctor` (`src/ai_engineering/doctor.py:795`) and `.ai/.gitignore`. This is the
  home new pages join.
- Spec and plan are plain committed Markdown under `specs/NNN-slug/`. The gate authority
  names the spec's digest (`policy/skill-sequence.toml [gate]`: "a human approval record
  carrying the specification's exact digest"); the two-file practice — spec **and** plan
  digests — lives in the ADR series (`docs/adr/0008`, `docs/adr/0009`), and the digest a
  plan is signed under is the **canonical** one, taken with the tick column masked
  (`src/ai_engineering/spec.py` `approval_bytes`/`_digest`).
- `docs/solution-intent.html` is already committed HTML this framework shows a human to
  act on — the precedent that a rendered page can live in the tree.
- The external visual-plan/visual-recap skills are MIT prose mirrored from
  BuilderIO/agent-native — verified from upstream this session, not from this tree:
  `BuilderIO/skills` `LICENSE` is MIT (c) 2026 Builder.io, `scripts/sync-agent-native-
  skills.mjs` copies the four visual skills verbatim from an agent-native checkout, and
  `.github/workflows/update-agent-native-plan-skills.yml` keeps them synced. Their
  mechanism (hosted Plan MCP, or `npx @agent-native/core` plus a renderer living on
  agent-native.com even in "local-files" mode) is excluded by the user's constraint; their
  craft — block taxonomy, diff→block mapping, budgets (3–8 key-change tabs, ~150 excerpt
  lines, title ≤70 chars), grounding rules ("blocks derived mechanically from the real
  diff, never invented"; "no boilerplate prose blocks") — is harvestable.
- MDX is markdown + JSX + ESM: it needs a compiler and a component framework to render,
  i.e. an npm toolchain. Not the answer.
- GitHub comments render Markdown and a limited HTML subset but not an interactive page —
  so a "visual PR review" on GitHub is necessarily a **link from the comment to a published
  page**. [unsourced: GitHub's exact tag-sanitization list was not read from a primary
  source this session; the link-not-inline conclusion holds under any subset.]
- GitHub Pages is **not enabled** for `arcasilesgroup/ai-engineering` (measured round 1:
  `gh api repos/arcasilesgroup/ai-engineering/pages` → 404). `.github/workflows/check.yml`
  runs with global `permissions: contents: read`, so a PR-commenting job needs a named
  permission escalation and the `ci-result` gate job lists its needs explicitly.
- The Markdown readers in this tree are **fence-blind today** (measured round 1):
  `plan_tasks` parses a numbered bold line inside a fence as a real task, a `**check**:`
  span inside a fence can rewrite the command `--tick` executes, and
  `solution_intent._specs` counts `- [x]` lines anywhere in the body. `contract.py` already
  owns a fence-aware line reader; `spec.py` does not use it.
- `AGENTS.md` is capped by `tests/test_contracts.DOCTRINE_CEILING` = 150 lines and stands
  at 104; the user explicitly authorized raising the ceiling to carry the important
  always-on rules.

## Options considered

1. **Adopt agent-native's skills as installed.** The never-inline rule then holds and the
   screenshots are the product. Cost: an OAuth'd hosted MCP or an npm CLI in the execution
   path, and a second source of truth beside the Markdown whose digest is the gate. Dies on
   the user's own constraint and on the approval model.
2. **A prose convention: the skill hand-writes a rich HTML page every time, no templates or
   renderer.** Cost: hand-authored HTML drifts per agent, blows the fog and catalog
   budgets, and the budgets live only in prompts. Rule 12 forbids it: the *shape* of a page
   always resolves the same way, so the shape is code.
3. **Skills author, a command renders, one file keeps the digest.** The skills
   (`ai-visual-plan`, `ai-visual-recap`, and the cycle verbs that call them) author content
   as fenced `visual` directive blocks **inside the existing Markdown** — spec.md, plan.md,
   or the recap narrative — using a block vocabulary documented in `policy/visual-pages.md`.
   A stdlib renderer (`ai-eng report view|recap`) extracts those blocks plus the mechanical
   facts (file-tree and diff excerpts from `git`, canonical digests from the bytes) and
   emits one self-contained HTML page from a repo-owned template. Markdown stays the sole
   approval object — no sidecar to drift, no second digest. The PR review is the same recap
   page published through GitHub Pages and linked from a bot comment. Cost: one module, one
   template set, a block grammar **with the tree's existing readers made fence-aware first**,
   tests, skill edits, and a Pages decision that is not ours to make.

## Decision

Option 3. Precisely:

- **The block grammar is fenced directives inside the Markdown, and fence-awareness is its
  precondition, not a follow-up.** A plan carries ` ```visual { "block": "diagram", … } ```
  ` segments (diagram, file-tree, decision-table, open-questions, wireframe-before-after,
  checklist). Before any block is authored into an approved plan, the three fence-blind
  readers — `plan_tasks`, `approval_bytes`, `solution_intent._specs` — stop at fences (one
  shared helper, reusing the pattern `contract.py` already owns), each with a refusal test:
  a numbered bold line, a `**check**:` span and a `- [x]` line inside a fence must be
  invisible to task parsing, field donation and intent counting respectively. The renderer
  ignores unknown blocks loudly (a visible warning section naming them) rather than dropping
  them silently — a page that quietly loses a block is the silent-coercion bug in a new
  costume.
- **Homes.** Recap pages are records: `.ai/reports/NNN-recap-<slug>.html`, matched by
  `doctor`'s existing regex (verified: the shape already fits — no new regex). Spec/plan
  views are derived: `.ai/views/<NNN>-<slug>.html`, **gitignored and never committed**, so
  `doctor`'s one-home check (which inspects tracked files only) has nothing to grow; the
  shipped pin is `skeletons.AI_GITIGNORE`, which must re-allow the views shape the same way
  the locally-grown `.ai/.gitignore` re-allows reports. The view header prints the
  **canonical** digests — the same values `_digest` computes and the ADR signs — plus the
  date and the `file://` path.
- **Two skills, four page types.** `ai-visual-plan` turns a plan — a pasted text plan,
  another agent's plan, or a `specs/NNN-slug/plan.md` — into the visual review page; `ai-visual-
  recap` turns a branch, commit, PR diff or finished work unit into a recap page. The cycle
  verbs call them at their natural step (ai-spec/ai-plan offer the view for the gate;
  ai-build/ai-goal/ai-ship produce the recap at the hand-off). Research keeps writing
  `.ai/reports/` directly. So: research, spec, plan, recap — all HTML, all in-repo.
- **The link duty.** Every command that writes a page prints its absolute `file://` URL
  and the canonical digests it rendered, and every skill must show that link in chat as the
  last line about the artifact — one click opens the browser. The printed digest is the
  recomputation: the second path is "re-run the command and diff the pages", which the
  byte-identical example below pins. In CI the same duty prints the published URL instead.
- **Budgets as constants, guidance as policy.** `RECAP_TABS_MIN/MAX`,
  `RECAP_EXCERPT_LINES_MAX`, `PAGE_TITLE_MAX` live in `contract.py` beside the other
  numbers; the harvested editorial rules (grounding, no-boilerplate, before/after
  comparability, real content not lorem) live in `policy/visual-pages.md` with the Builder.io
  MIT attribution beside the text derived from it.
- **Visual PR review.** A CI job on `pull_request` runs `ai-eng report recap` against the
  PR base, publishes the page through GitHub Pages, and a bot comment posts a short
  Markdown summary (title, one-paragraph outcome, file count) plus the link. The job needs
  `pull-requests: write` scoped to itself against the workflow's `contents: read` default,
  and it is added to `ci-result`'s needs list so it gates like everything else. Pages is
  not enabled today, so the job's first shipped shape is the honest degradation: artifact
  upload plus a comment saying Pages is off. Publishing internal records to a public site
  is a privacy decision (rule 8); it is an open question for the human, not a default.
- **Doctrine.** `DOCTRINE_CEILING` rises 150 → 180 (user-authorized), and `AGENTS.md` gains
  four always-on rules: (a) a turn ends as Done-with-the-artifact-that-proves-it or as one
  line `BLOCKED: <what> — unblock: <one thing under a minute>`; (b) every final response
  ends with the one-line status `🟢//🔴`, and a 🟡 names its pending item legibly; (c)
  scale effort to the task; (d) do the work instead of asking whether to do it — ask only
  for a missing credential, a human-only decision, or a destructive action. Plus the link
  duty line. CONSTITUTION.md's "the spec is the sole home of phase status" is untouched:
  the status line is response format, not persisted state, and the spec records that
  reading so the next reader does not re-litigate it.

## Challenged once

Strongest realistic case against: *a second rendered surface always drifts from the real
one, and fenced JSON inside Markdown is the worst of both — uglier in the terminal than a
clean plan, less rich than the hosted editor it imitates, and (per round 1, executed) a
fence-blind parser turns the grammar into a way to smuggle commands into an approved plan.*
The design takes all three halves seriously: drift is bounded because the page prints the
canonical digest of the bytes it rendered and regenerates from them in one command; the
injection risk is the reason fence-awareness is the precondition task with refusal tests,
not a note in the risks column — until those tests exist, no `visual` block may be authored
into any approved plan; the terminal ugliness is bought on purpose, because the alternative
(a sidecar file) splits the digest gate into two objects that can disagree, which is the
exact failure spec 045 consolidated away. If the noise proves worse than the value, the
retreat is cheap and named in ## Assumptions: the grammar can move to a sidecar in one
commit, and the gate then has to say so. Second edge: raising the ceiling reopens the
doctrine to creep — accepted with the number moved to 180, not deleted; the cap, the test
and the "true in every session" bar still bite.

## Grill

ran: round 1, 2026-08-28 — 15 min

### Q1: Does the fenced `visual` grammar collide with the task parser in `spec.py`, given it is not fence-aware?

**A:** WRONG, and it changed the Decision. Executed corruptions: a fenced phantom task won
the envelope collision, and a `**check**:` span inside a fence replaced the command
`--tick` would execute (`uv run rm -rf /tmp/proof-of-donation` reached `_one_command`'s
argv). Fix folded: fence-awareness for `plan_tasks`/`approval_bytes`/`solution_intent._specs`
is now the precondition task (plan task 3), with a refusal test each, and no block may be
authored into an approved plan before it lands.

### Q2: Can the spec 046 plan itself be executed by the machinery the spec relies on?

**A:** WRONG — the plan was written with unbolded fields and multi-command checks, so all
12 tasks parsed to zero fields and `spec show 046 --task 4` returned INCOMPLETE. Fix
folded: the plan is rewritten in the 045 house format — `**file**:`/`**check**:` bold
fields, exactly one runnable command per check, no `&&` in a check.

### Q3: Does `doctor` flag `.ai/views/` today, and does the shipped `.ai/.gitignore` template carry a `!reports/…` line?

**A:** WRONG on both counts — doctor check 17 inspects tracked files only, so an ignored
stray can never reach it, and `skeletons.AI_GITIGNORE` has no `!reports/` line (the local
one was hand-grown). Fix folded: views stay gitignored-derived, doctor does not grow, and
the real mechanism named is `skeletons.AI_GITIGNORE` re-allowing the views shape.

### Q4: Which digest does the view header print, and is there a command to recompute it?

**A:** WRONG as written — the ADR signs the **canonical** digest (tick column masked; raw
and canonical differ on this very plan: `3cc6ae45…` vs `9a4acdee…`), and no standalone
digest command exists. Fix folded: the header prints canonical `_digest` values, and the
recomputation is the view command itself — run it again and the pages must be
byte-identical, which the examples now pin.

### Q5: Is plan task 1's check true — does the doctrine test fail today?

**A:** WRONG — AGENTS.md is 104 ≤ 150 so nothing fails before the append, and the bare
`uv run pytest` form the plan used is not this repo's lane. Fix folded: checks use
`uv run --with pytest==9.1.1 pytest -q …` and "fails today" is re-anchored to the
mid-task order (append first, ceiling second, one commit).

### Q6: Does `policy/skill-sequence.toml [gate]` say what the spec's Context claimed?

**A:** WRONG citation — `[gate]` names the specification's digest (singular); the plan
digest lives in the ADR series practice. Fix folded into Context.

### Q7: Can a `pull_request` CI job publish through Pages and post the bot comment as wired?

**A:** UNPROVEN as written — Pages is not enabled (404), the workflow is `contents: read`,
and `ci-result` hard-codes its needs. Fix folded: the Decision now names the permission
escalation, the needs-list edit, and artifact-degradation as the first shipped shape.

### Q8: Are the external skills' MIT/mirroring claims checkable from this tree?

**A:** UNPROVEN from the tree — the claim rests on the upstream repo. Fix folded: Context
now cites the exact upstream files (`LICENSE`, `scripts/sync-agent-native-skills.mjs`,
`.github/workflows/update-agent-native-plan-skills.yml`) verified from source this session.

## Council

ran: round 1, 2026-08-28 — 24 min — `lenses: cost, reversibility, undecidable, trust, example`
— five reads, each on this specification and the tree alone, then the anonymous cross-read.
It concludes; it grants nothing.

### Gaps no single lens named

- **Every Markdown reader in this tree is fence-blind, and the grammar lands inside their input** — cost saw budgets, reversibility saw the sidecar, example saw the digests, and only the cross-read put the three probes side by side: `plan_tasks` parses a numbered bold line inside a ```visual fence as a real task (probe: 12 tasks → 13, a phantom `1`), `approval_bytes` masks the tick column there too (probe: raw digest of `specs/046-visual-html-records/plan.md` is `3cc6ae45…` where the sealed digest is `9a4acdee…`, and a `[x]` planted inside a fence leaves the sealed value identical), and `solution_intent._specs` counts `^\s*[-*]\s*\[x\]` anywhere in the body (probe: five `- [x]` lines inside one fence moved the published counter to 5/5). The spec's own precedent — `_FIELD` stopping at a heading, spec.py:319-325 — says the fix is a fence-aware stop, and it must ship in the same commit as the first block, with one test per reader.
- **The `will` banner and the capability manifest are unclaimed by any task** — the cross-read noticed that task 4 and task 5 add writers to `report`, while `uv run ai-eng report --help` scopes the verb to "the local digest read receipt, the Solution Intent page under docs/" and `policy/capabilities.toml:341` declares `write_roots = [".ai/reports"]` for `ai-report`'s digest mode. After those tasks the banner names neither `.ai/views` nor `.ai/reports/NNN-recap-*.html`, which is the exact shape `cli.py:144-147` calls a false statement about a run. One task must own the banner, the manifest and their proofs beside the doctor change.

### Findings cut for carrying no command

- whether the fenced JSON is too ugly in the terminal to be worth the single-digest property: taste, and the spec already names the reopen path in its Assumptions.
- whether GitHub's comment sanitizer admits the tags the page needs: the spec itself marks the list `[unsourced]`, and nothing in this tree can decide it.
- whether reviewers click a `file://` link once it exists: no instrument in this tree observes a click.

### Findings the cross-read refuted, with the command that refuted them

- "two more skills push the catalogue at `CATALOG_MAX`" — measured: the name+description total over `.agents/skills/ai-*/SKILL.md` is 11,208 of `contract.CATALOG_MAX = 50_000`, headroom 38,792; recompute with `uv run python -c "from ai_engineering import contract; …"` over the same glob `contract.audit` uses (contract.py:142-152).
- "a ```visual block donates a field to the task above it" — refuted: the probe moved the task count but not task 5's `check` (the block ends at the next task mark, spec.py:317-325); the surviving half is the phantom task, folded into the gap above.
- "`report view` cannot live inside `report` — the plan's `report.py:139-143` citation is to prose, not machinery" — refuted: `uv run ai-eng report --help` prints five live subcommands ({digest,issue,surfaces,intent,blocked}); the family exists and `view` joins it without touching the ten-verb assertions.

### The two counts

- Gaps that appeared only after the cross-read: **2**
- Findings deleted, for carrying no command or for being refuted: **6**

## Assumptions and unresolved risks

Assumptions (taken as true, not proved):

- The reader opens pages on the same machine as the checkout, so `file://` links work; a
  remote/SSH workstation may not resolve them — the CI path (artifact or Pages URL) is the
  fallback and is named as such.
- Fenced `visual` blocks in plan.md stay readable enough in the terminal to be worth the
  single-digest property; if they do not, the retreat is a sidecar file in one commit and
  the gate's wording changes with it.

Unresolved risks (not accepted — `ai-eng accept` is the only thing that accepts):

- Publishing recap pages through GitHub Pages may expose internal detail on a public site;
  the human must decide Pages enablement and scope before the PR-review job links anything
  permanent. Until then the job degrades to an artifact link.
- Recap grounding: a block invented from conversation instead of the diff is the failure
  the harvested guidance forbids; the renderer can enforce budgets and diff-line presence
  for `diff`/`file-tree` blocks, but narrative invention stays a review judgement. Whether
  that becomes a guard is a rule-12 question for later receipts, not this spec.
- Four doctrine rules consume ~25–30 of the 30 added ceiling lines; a fifth always-on idea
  with no home is the first sign the raise was optimistic.

## Examples somebody can check

- Given spec `046` with plan bytes, When `ai-eng report view --spec 046` runs twice with
  nothing changed, Then `.ai/views/046-visual-html-records.html` exists after the first run,
  the second run leaves it byte-identical, and stdout contains the absolute `file://` URL
  and the canonical spec and plan digests.
- Given a plan.md carrying a ` ```visual ` diagram block, When the view renders, Then the
  page shows the diagram surface, and given a block whose `"block"` name is unknown, Then
  the page carries a visible warning section naming it — an unknown block is never silently
  dropped.
- Given a fenced block containing `1. [ ] **Phantom** —`, a `**check**: \`uv run true\``
  span and five `- [x]` lines, When `plan_tasks`, `approval_bytes` and
  `solution_intent._specs` read the file, Then the task count is unchanged, the digest
  equals the same file with the fence removed of those lines' effect, and the intent
  counter does not move — each refusal pinned by a named test.
- Given a finished build, When `ai-eng report recap --spec <NNN> --base <sha>` runs, Then a
  page matching `^\.ai/reports/[0-9]{3}-recap-[^/]+\.html$` exists (doctor's existing regex
  still passes), its file list equals `git diff --name-status` for the same range, and it
  holds at most 8 key-change excerpts of at most 150 lines each.
- Given a spec id that does not exist under `specs/`, When either command runs, Then it
  exits nonzero with `INCOMPLETE` and names the missing spec, writing no page.
- Given a PR on GitHub with the recap job wired, When CI runs, Then the bot comment carries
  a short Markdown summary and exactly one link — the Pages URL if Pages is enabled, else
  the artifact URL with the comment saying Pages is off.
- Given `AGENTS.md` grown past 180 lines by a future edit, When `uv run --with
  pytest==9.1.1 pytest -q tests/test_contracts.py -k doctrine` runs, Then it fails — the
  ceiling moved, it did not disappear.

## Decisions

<!-- One `**D-046-NN — <the decision>**` per line, each with a `**Rationale:**` under it.
     Prefix a line with `- [X]` to claim the decision earns promotion: it constrains
     specs that do not exist yet, and `ai-eng decide` promotes only marked lines.
     `ai-eng decide` does not write here: it writes a record under docs/adr/. -->

- [X] **D-046-01 — Rendered pages are views or records, never approval objects.** Markdown
  under `specs/` and the ADR at its canonical digests remain the sole gate; `.ai/views/`
  pages are gitignored derived output and recap pages are records of bytes already
  approved.
  **Rationale:** an approvable second surface would derive from the digest and break the
  exact-digest gate spec 045 consolidated the cycle around.
- [X] **D-046-02 — Page generation is a command, not a prompt; page content is skill
  authorship, not code invention.** The renderer owns template, extraction, budgets and
  diff facts; the skills own narrative, diagrams and judgement-bearing blocks, authored as
  fenced `visual` directives inside the Markdown so one file carries one digest — and the
  tree's Markdown readers are fence-aware before the first block is authored.
  **Rationale:** rule 12 — the shape of a page always resolves the same way, so it is
  code; what a page argues is a decision, so it stays prose the critics can attack; and
  round 1 executed that a fence-blind reader turns the grammar into a command-injection
  path into an approved plan.
- [X] **D-046-03 — Every page reaches the human as a clickable link.** Commands print the
  absolute `file://` URL (or the published URL in CI) beside the canonical digests they
  rendered; skills show it in chat beside the hand-off.
  **Rationale:** the user's stated UX bar; a page nobody clicks is a file, not a review
  surface.
- [X] **D-046-04 — A visual PR review is a link to a published page, never inlined HTML.**
  GitHub comments carry a Markdown summary plus one link; the interactive surface is the
  Pages-served recap. **Rationale:** comments cannot render an interactive page, and the
  publishing scope is a human privacy decision, so the job degrades to an artifact link
  until that decision exists.

- [X] **D-046-05 — A correction to an approved spec moves its digest and is re-signed.**
  When the map finds a real broken reference inside approved bytes, the reference is
  fixed in the spec and a new MADR re-approves the corrected digest, superseding the old
  approval. **Rationale:** the alternative — accepting the broken pair in the map's dated
  set — keeps a false statement in the record to protect a signature; ADR 0023 is the
  precedent that the digest moves and the re-approval is the honest artifact.

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command. The
External-check and Second-path boxes carry a named wrinkle: the Pages URL is an outside
surface this repo does not control, and the second path for a rendered page is re-running
the generator and diffing the bytes, not a second renderer.

- [ ] CI/CD — build, lint, test and security analysis on every push; deploy from the default branch
- [ ] Logs — structured JSON, one line per event, with level and service, to stdout
- [ ] Traces — only if this is our code and has more than one hop; no hop, no trace
- [ ] Errors — every uncaught exception leaves as a log with severity 17 and marks its span
- [ ] Health and data age — alive, age of the newest datum, and an independent recomputation
- [ ] External check — something outside the service verifies it and says what it could not check
- [ ] Second path — every published number recomputed by an independent route and compared
- [ ] Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI
