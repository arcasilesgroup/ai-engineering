---
id: "046"
slug: visual-html-records
status: draft
date: 2026-08-28
ref: ""
---

# Plan: visual HTML records

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and
this exact `plan.md`**, recorded at their canonical digests in their own `docs/adr/`
record. One repository writer, on one branch. Each task is one atomic commit; rollback for
every task is `git revert <commit>`. Tasks 1–3 are the coupled precondition family: the
doctrine room, the constants, and fence-awareness — no `visual` block may be authored into
any approved plan before task 3 lands, per D-046-02.

**This plan is not edited while it is executed.** Each check names exactly one command,
because `ai-eng spec show --tick` executes the one command a box carries; the prose beside
each check states everything else the task must hold.

## The order, and why

Grill round 1 executed that the tree's Markdown readers are fence-blind and the grammar
lands inside their input, so fence-awareness (3) precedes the renderer (4) and every
authoring skill (10–12). The two commands (5, 6) precede the homes they write (7) and the
banner that must describe them (8). Guidance (9) precedes the skills that cite it. The PR
job (13) is last of the machinery because it consumes the recap; the smoke (14) closes the
gate.

## Tasks

1. [x] <!--t:898ccdc23073--> **Doctrine room and the four always-on rules** —
   **file**: `AGENTS.md` (same commit as `tests/test_contracts.py`: cap and text move
   together — append the rules first, watch the doctrine test go red, then raise
   `DOCTRINE_CEILING` 150 → 180 in the same commit). The four rules from the spec's
   Decision: turn = Done-with-artifact or one line `BLOCKED: … — unblock: …`; the
   🟢//🔴 status line with a legible 🟡; scale effort to the task; do the work instead of
   asking. Plus the link duty: a command that writes a page prints its absolute URL, and
   the skill shows it in chat.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_contracts.py -k doctrine`
   **rollback**: `git revert <commit>`; both files return together.
   **done when**: AGENTS.md is ≤180 lines, carries the four rules and the link duty, and
   the doctrine test is green.

2. [x] <!--t:6f769487b495--> **Budget constants** —
   **file**: `src/ai_engineering/contract.py` — add `RECAP_TABS_MIN = 3`,
   `RECAP_TABS_MAX = 8`, `RECAP_EXCERPT_LINES_MAX = 150`, `PAGE_TITLE_MAX = 70` beside
   `SKILL_FOG_CEILING`, each with the upstream source named in its comment.
   **check**: `uv run python -c "from ai_engineering import contract; print(contract.RECAP_TABS_MAX)"`
   **rollback**: `git revert`; no reader exists yet.
   **done when**: the four names import and print, and they are the only place the numbers
   live.

3. [x] <!--t:a065b4d0d56b--> **Fence-awareness before the first block** —
   **file**: `src/ai_engineering/spec.py` (shared fence-aware line stop for the task
   parser and the approval-bytes mask, reusing the pattern `contract.py` already owns)
   with matching stops in `src/ai_engineering/solution_intent.py` — three refusal tests
   land in `tests/test_mut_spec.py` first: a numbered bold task line inside a fence adds
   no task, a bold check-field inside a fence donates no command, and checked-box lines
   inside a fence move no counter.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_mut_spec.py -k fence`
   **rollback**: `git revert`; the grammar simply cannot ship without this, which is the
   point of ordering it first.
   **done when**: all three refusals pass and every existing digest on the 16 plans is
   unchanged (fence-blind behaviour only changes for files carrying fences, of which there
   are none yet).

4. [x] <!--t:e86c3014b7db--> **The pages module: extraction, loud ignorance, template** —
   **file**: `src/ai_engineering/pages.py` (new) — fenced ` ```visual ` JSON extraction,
   the block vocabulary, HTML escaping, the shared self-contained page template via
   `importlib.resources`, budgets read from `contract.py`, and the unknown-block rule: an
   unrecognized `"block"` name renders into a visible warning section, never a silent drop.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_pages.py`
   **rollback**: `git revert`; nothing imports the module yet.
   **done when**: known blocks render, the unknown block warns on the page, and a test
   proves no page carries an inline `<script>` or external URL.

5. [ ] **`ai-eng report view` — the spec/plan review page** —
   **file**: `src/ai_engineering/report.py` — subcommand `view --spec NNN` inside the
   existing family: renders `specs/NNN-slug/spec.md` + `plan.md` through `pages.py` to
   `.ai/views/<NNN>-<slug>.html`; header carries the canonical `_digest` values of both
   files plus the date; prints the absolute `file://` URL; a missing spec exits INCOMPLETE
   and writes nothing.
   **check**: `uv run ai-eng report view --spec 046`
   **rollback**: `git revert`; subcommand and its tests leave together.
   **done when**: two consecutive runs leave the page byte-identical, the printed digests
   equal `ai-eng spec show 046 --task 1`'s named digests, and `--spec 999` refuses without
   writing.

6. [ ] **`ai-eng report recap` — the post-build visual record** —
   **file**: `src/ai_engineering/report.py` and `src/ai_engineering/pages.py` — subcommand
   `recap --spec NNN --base <ref> --summary <text>`: file-tree with change flags and 3–8
   key-change diff excerpts derived mechanically from `git diff` against the base (an
   excerpt that is not a real hunk refuses), narrative from `--summary` or a `visual`
   block, canonical spec digest, the verification commands it is told, secret redaction
   before writing, output at `.ai/reports/NNN-recap-<slug>.html`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_mut_report.py -k recap`
   **rollback**: `git revert`.
   **done when**: a fixture-diff test proves the page's file list equals
   `git diff --name-status` for the range, budgets come from constants, and a fabricated
   hunk is refused.

7. [ ] **The views home in the shipped pin** —
   **file**: `src/ai_engineering/skeletons.py` — `AI_GITIGNORE` re-allows
   `!views/[0-9][0-9][0-9]-*.html` the way the local `.ai/.gitignore` re-allows reports;
   doctor does not grow (it inspects tracked files only, and views are never tracked —
   grill Q3). A test asserts the shipped template and the local pin agree on both shapes.
   **check**: `uv run python -c "from ai_engineering import skeletons; assert '!views/' in skeletons.AI_GITIGNORE"`
   **rollback**: `git revert`; fresh installs stop re-allowing views, which is the pre-state.
   **done when**: a fresh `ai-eng init` tree can hold a view page without `git add -f`.

8. [ ] **The banner and the manifest describe the new writers** —
   **file**: `src/ai_engineering/report.py` (the `will` banner: the verb now also writes
   `.ai/views/` pages and `.ai/reports/NNN-recap-*.html`) and `policy/capabilities.toml`
   (the declared write roots beside the digest mode) — council gap 2: a writer the banner
   does not name is a false statement about a run.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_capabilities.py -k report`
   **rollback**: `git revert`; the banner goes stale, which the test then catches.
   **done when**: `ai-eng report --help` names both page writers and the capability test
   proves the manifest agrees.

9. [ ] **The harvested guidance, attributed** —
   **file**: `policy/visual-pages.md` (new) — the condensed block taxonomy, the diff→block
   mapping, the grounding rules (blocks derived from real diff lines, no boilerplate,
   before/after comparability, real content not lorem), every budget referenced as
   "`contract.py` names it", headed with the Builder.io MIT (c) 2026 attribution and the
   upstream files it was verified against.
   **check**: `uv run python -c "import pathlib; t=pathlib.Path('policy/visual-pages.md').read_text(); assert 'MIT' in t and 'Builder' in t and 'contract.py' in t"`
   **rollback**: `git revert`; runtime code never reads this file.
   **done when**: the file exists, attributes, and carries zero loose budget numbers.

10. [ ] **`ai-visual-plan` — the skill that turns any plan into the review page** —
    **file**: `.agents/skills/ai-visual-plan/SKILL.md` (with `corpus.md` in the same
    commit — the contract refuses a skill without both). Trigger: "make this plan visual",
    "rich review surface", a pasted or foreign text plan needing approval review.
    Procedure: research real files first, author `visual` blocks into the plan Markdown
    (only after task 3's fence-awareness is on the branch), run `ai-eng report view`, show
    the `file://` link; planning stays read-only on source; never hand-write HTML.
    **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_skill_bounds.py`
    **rollback**: `git revert`; removes the skill directory whole.
    **done when**: the skill passes the contract and its `## Done when` is the printed link
    plus the rendered page.

11. [ ] **`ai-visual-recap` — the skill that turns a diff into the recap page** —
    **file**: `.agents/skills/ai-visual-recap/SKILL.md` + `corpus.md`. Trigger: "recap
    this PR/branch/work unit", "what did this change", the post-build hand-off. Procedure:
    scope the whole work unit, run `ai-eng report recap` with the real base, add narrative
    and UI before/after `visual` blocks grounded in the diff, show the link; skip rule for
    tiny diffs (a recap is review overhead).
    **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_skill_bounds.py`
    **rollback**: `git revert`.
    **done when**: contract-green, and one real recap page rendered through it over this
    branch's own range.

12. [ ] **The cycle verbs point at the pages** —
    **file**: `.agents/skills/ai-spec/SKILL.md` (same commit edits `ai-plan`, `ai-build`,
    `ai-goal`, `ai-ship`, `ai-research` — one edit family, link duty only). ai-spec/
    ai-plan: after writing, call `report view` and hand the human the link beside the
    Markdown. ai-build/ai-goal hand-off: call `report recap` and put the link in the
    hand-off. ai-ship: recap link into the PR body. ai-research: print the `file://` URL of
    the report it already writes. No page authoring by prose, per D-046-02.
    **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_contracts.py -k fog`
    **rollback**: `git revert`; skills return to Markdown-only pointers, which still work.
    **done when**: six skills name the command they run and the link they show, and the
    fog ratchet is green over all of them.

13. [ ] **The visual PR-review job, degrading honestly** —
    **file**: `.github/workflows/check.yml` — a `recap` job on `pull_request`: run
    `ai-eng report recap` against the PR base; `permissions: { pull-requests: write }`
    scoped to the job against the workflow's `contents: read` default; add the job to
    `ci-result`'s needs list so it gates; if Pages is enabled, publish and comment the
    URL, else upload the page as an artifact and comment that Pages is off (it is off
    today — 404). The bot comment is Markdown summary (title, outcome, file count) plus
    exactly one link, per D-046-04.
    **check**: `uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/check.yml'))"`
    **rollback**: `git revert`; the job disappears, local recaps unaffected.
    **done when**: the next real PR carries the summary-plus-link comment, and no public
    URL appears before the human Pages decision named in the spec's risks.

14. [ ] **End-to-end smoke and the changelog** —
    **file**: `CHANGELOG.md` — run the whole flow on spec 046 itself: `report view`,
    `report recap` over this branch's range, open both pages, confirm the digest headers
    against `spec show`, confirm both links open in the browser, confirm `doctor` green.
    The changelog states the clean cut: views derived, recaps records, ADR canonical
    digests still the gate, ceiling 150→180, MIT attribution in `policy/visual-pages.md`.
    **check**: `just check`
    **rollback**: `git revert` the changelog commit only; machinery reviewed in 1–13.
    **done when**: the gate is green with everything committed and the two pages for 046
    render with working links.

## What this plan is not doing, and why

- **No MDX, no npm, no hosted Plan surface** — the user's constraint and the audit.
- **No `ai-arbitrate` / `ai-watchdog` skills** — report 021 phases them separately; binding
  two independent cutovers to one gate is how a review gets hostage.
- **No enabling GitHub Pages from this plan** — task 13 degrades to artifact links; the
  public-URL privacy decision is the human's, named in the spec's unresolved risks.
- **No guard forcing a recap per build yet** — rule 12: capability and convention first;
  three receipts of the same judgement decide whether enforcement becomes code.
- **No interactive commenting on the pages** — hosted-plan comments need the hosted
  surface; feedback here is file/chat feedback applied to the Markdown, then regenerate.
- **No `visual` blocks authored before task 3 merges** — grill Q1 executed the injection
  path; the precondition is the ordering, not a warning.
