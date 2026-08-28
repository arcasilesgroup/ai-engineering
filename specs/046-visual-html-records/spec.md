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
- Spec and plan are plain committed Markdown under `specs/NNN-slug/`; the approval gate is
  an ADR at the **exact digests** of those two files (`policy/skill-sequence.toml [gate]`).
- `docs/solution-intent.html` is already committed HTML this framework shows a human to
  act on — the precedent that a rendered page can live in the tree.
- The external visual-plan/visual-recap skills are MIT prose mirrored from
  BuilderIO/agent-native. Their mechanism (hosted Plan MCP, or `npx @agent-native/core`
  plus a renderer living on agent-native.com even in "local-files" mode) is excluded by the
  user's constraint; their craft — block taxonomy, diff→block mapping, budgets (3–8
  key-change tabs, ~150 excerpt lines, title ≤70 chars), grounding rules ("blocks derived
  mechanically from the real diff, never invented"; "no boilerplate prose blocks") — is
  harvestable and is what the screenshots show.
- MDX is markdown + JSX + ESM: it needs a compiler and a component framework to render,
  i.e. an npm toolchain. Not the answer.
- GitHub comments render Markdown and a limited HTML subset (e.g. `<picture>`, custom
  anchors) but not an interactive page — so a "visual PR review" on GitHub is necessarily a
  **link from the comment to a published page**, which is exactly the shape agent-native's
  own PR action uses. [unsourced: the exact tag-sanitization list was not read from a
  primary source this session; the link-not-inline conclusion holds under any subset.]
- The remote is `github.com/arcasilesgroup/ai-engineering`; GitHub Pages serves committed
  HTML from the repo as a project site. Whether Pages is enabled, and whether published
  pages are acceptable as public URLs, is a human/infra decision, not a code fact.
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
   or the recap's narrative input — using a block vocabulary documented in
   `policy/visual-pages.md`. A stdlib renderer (`ai-eng report view|recap`) extracts those
   blocks plus the mechanical facts (file-tree and diff excerpts from `git`, digests from
   the bytes) and emits one self-contained HTML page from a repo-owned template. Markdown
   stays the sole approval object — no sidecar to drift, no second digest. The PR review is
   the same recap page published through GitHub Pages and linked from a bot comment. Cost:
   one module, one template set, a block grammar with a checker, tests, skill edits, and a
   Pages decision that is not ours to make.

## Decision

Option 3. Precisely:

- **The block grammar is fenced directives inside the Markdown.** A plan carries
  ` ```visual { "block": "diagram", … } ``` ` segments (diagram, file-tree, decision-table,
  open-questions, wireframe-before-after, checklist); a plain-Markdown reader sees a fenced
  block, a browser sees a rendered surface. The renderer ignores unknown blocks loudly
  (prints them as a warning section) rather than dropping them silently — a page that
  quietly loses a block is the silent-coercion bug in a new costume.
- **Homes.** Recap pages are records: `.ai/reports/NNN-recap-<slug>.html`, the existing
  doctor-pinned shape — no new regex. Spec/plan views are derived: `.ai/views/<NNN>-<slug>.
  html`, gitignored, regenerated by one command, never approved; `doctor`'s one-home check
  grows that shape, and the shipped `.ai/.gitignore` template re-allows it. The view header
  prints the digest and date of the exact bytes it rendered, so staleness is checkable from
  the page itself.
- **Two skills, four page types.** `ai-visual-plan` turns a plan — a pasted text plan,
  another agent's plan, or `specs/NNN/plan.md` — into the visual review page; `ai-visual-
  recap` turns a branch, commit, PR diff or finished work unit into a recap page. The cycle
  verbs call them at their natural step (ai-spec/ai-plan offer the view for the gate;
  ai-build/ai-goal/ai-ship produce the recap at the hand-off). Research keeps writing
  `.ai/reports/` directly. So: research, spec, plan, recap — all HTML, all in-repo.
- **The link duty.** Every command that writes a page prints its absolute `file://` URL,
  and every skill must show that link in chat as the last line about the artifact — one
  click opens the browser. In CI the same duty prints the published URL instead.
- **Budgets as constants, guidance as policy.** `RECAP_TABS_MIN/MAX`,
  `RECAP_EXCERPT_LINES_MAX`, `PAGE_TITLE_MAX` live in `contract.py` beside the other
  numbers; the harvested editorial rules (grounding, no-boilerplate, before/after
  comparability, real content not lorem) live in `policy/visual-pages.md` with the
  Builder.io MIT attribution beside the text derived from it.
- **Visual PR review.** A CI job on `pull_request` runs `ai-eng report recap` against the
  PR base, publishes the page through GitHub Pages, and a bot comment posts a short
  Markdown summary (title, one-paragraph outcome, file count) plus the link — the exact
  shape of the screenshot, with our generator instead of the hosted Plan app. Until Pages
  is confirmed for this repo, the job degrades honestly: the page is uploaded as an
  Actions artifact and the comment says so. Publishing internal records to a public site is
  a privacy decision (rule 8); it is an open question for the human, not a default.
- **Doctrine.** `DOCTRINE_CEILING` rises 150 → 180 (user-authorized), and `AGENTS.md` gains
  four always-on rules: (a) a turn ends as Done-with-the-artifact-that-proves-it or as one
  line `BLOCKED: <what> — unblock: <one thing under a minute>`; (b) every final response
  ends with the one-line status `🟢/🟡/🔴`, and a 🟡 names its pending item legibly; (c)
  scale effort to the task; (d) do the work instead of asking whether to do it — ask only
  for a missing credential, a human-only decision, or a destructive action. Plus the link
  duty line. CONSTITUTION.md's "the spec is the sole home of phase status" is untouched:
  the status line is response format, not persisted state, and the spec records that
  reading so the next reader does not re-litigate it.

## Challenged once

Strongest realistic case against: *a second rendered surface always drifts from the real
one, and fenced JSON inside Markdown is the worst of both — uglier in the terminal than a
clean plan, less rich than the hosted editor it imitates.* The design takes both halves
seriously: drift is bounded because the page prints the digest of the bytes it rendered and
regenerates from them in one command; the terminal ugliness is real and bought on purpose,
because the alternative (a sidecar file) splits the digest gate into two objects that can
disagree, which is the exact failure spec 045 consolidated away. If the noise proves worse
than the value, the retreat is cheap and named in ## Assumptions: the grammar can move to a
sidecar in one commit, and the gate then has to say so. Second edge: raising the ceiling
reopens the doctrine to creep — accepted with the number moved to 180, not deleted; the
cap, the test and the "true in every session" bar still bite.

## Grill

TODO: when a grill round lands, replace this prompt with its declaration on its own
line — `ran: round <n>, <ISO date> — <n> min` — then one `### Q` per question with its
`**A:**` answer beside it, and what it changed. A round that attacked and found nothing
says `nothing checkable failed`. While this prompt stands undeclared, the critic step
reads the grill as not run.

## Council

TODO: when the council pass lands, replace this prompt with its declaration on its own
line — `ran: round <n>, <ISO date> — <n> min` — and name the lenses that read:
`lenses: cost, reversibility, undecidable, trust, example`. The shape below is what the
critic step reads — top-level bullets only, each heading carrying bullets or a literal
`none` line, every finding and every refutation carrying a command. The pass may
conclude; it may not approve.

### Gaps no single lens named

### Findings cut for carrying no command

### Findings the cross-read refuted, with the command that refuted them

### The two counts

- Gaps that appeared only after the cross-read: **N**
- Findings deleted, for carrying no command or for being refuted: **N**

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
  the second run leaves it byte-identical, and stdout contains the absolute `file://` URL.
- Given a plan.md carrying a ` ```visual ` diagram block, When the view renders, Then the
  page shows the diagram surface, and given a block whose `"block"` name is unknown, Then
  the page carries a visible warning section naming it — an unknown block is never silently
  dropped.
- Given a finished build, When `ai-eng report recap --spec <NNN> --base <sha>` runs, Then a
  page matching `^\.ai/reports/[0-9]{3}-recap-[^/]+\.html$` exists (doctor's existing regex
  still passes), its file list equals `git diff --name-status` for the same range, and it
  holds at most 8 key-change excerpts of at most 150 lines each.
- Given a spec id that does not exist under `specs/`, When either command runs, Then it
  exits nonzero with `INCOMPLETE` and names the missing spec, writing no page.
- Given a PR on GitHub with the recap job wired, When CI runs, Then the bot comment carries
  a short Markdown summary and exactly one link — the Pages URL if Pages is enabled, else
  the artifact URL with the comment saying Pages is off.
- Given `AGENTS.md` grown past 180 lines by a future edit, When `uv run pytest
  tests/test_contracts.py -k doctrine` runs, Then it fails — the ceiling moved, it did not
  disappear.

## Decisions

<!-- One `**D-046-NN — <the decision>**` per line, each with a `**Rationale:**` under it.
     Prefix a line with `- [X]` to claim the decision earns promotion: it constrains
     specs that do not exist yet, and `ai-eng decide` promotes only marked lines.
     `ai-eng decide` does not write here: it writes a record under docs/adr/. -->

- [X] **D-046-01 — Rendered pages are views or records, never approval objects.** Markdown
  under `specs/` and the ADR at its digests remain the sole gate; `.ai/views/` pages are
  gitignored derived output and recap pages are records of bytes already approved.
  **Rationale:** an approvable second surface would derive from the digest and break the
  exact-digest gate spec 045 consolidated the cycle around.
- [X] **D-046-02 — Page generation is a command, not a prompt; page content is skill
  authorship, not code invention.** The renderer owns template, extraction, budgets and
  diff facts; the skills own narrative, diagrams and judgement-bearing blocks, authored as
  fenced `visual` directives inside the Markdown so one file carries one digest.
  **Rationale:** rule 12 — the shape of a page always resolves the same way, so it is
  code; what a page argues is a decision, so it stays prose the critics can attack.
- [X] **D-046-03 — Every page reaches the human as a clickable link.** Commands print the
  absolute `file://` URL (or the published URL in CI); skills show it in chat beside the
  hand-off. **Rationale:** the user's stated UX bar; a page nobody clicks is a file, not a
  review surface.
- [X] **D-046-04 — A visual PR review is a link to a published page, never inlined HTML.**
  GitHub comments carry a Markdown summary plus one link; the interactive surface is the
  Pages-served recap. **Rationale:** comments cannot render an interactive page, and the
  publishing scope is a human privacy decision, so the job degrades to an artifact link
  until that decision exists.

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command. The
External-check and Second-path boxes carry a named wrinkle: the Pages URL is an outside
surface this repo does not control, and the second path for a rendered page is the
digest-header recomputation, not a second renderer.

- [ ] CI/CD — build, lint, test and security analysis on every push; deploy from the default branch
- [ ] Logs — structured JSON, one line per event, with level and service, to stdout
- [ ] Traces — only if this is our code and has more than one hop; no hop, no trace
- [ ] Errors — every uncaught exception leaves as a log with severity 17 and marks its span
- [ ] Health and data age — alive, age of the newest datum, and an independent recomputation
- [ ] External check — something outside the service verifies it and says what it could not check
- [ ] Second path — every published number recomputed by an independent route and compared
- [ ] Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI
