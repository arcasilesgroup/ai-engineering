---
id: "046"
slug: visual-html-records
status: draft
date: 2026-08-28
ref: ""
---

# Plan: visual HTML records

Implements `specs/046-visual-html-records/spec.md`. Nothing here gets a URL the framework
controls: the Pages job (task 11) publishes to GitHub's own host and is gated on a human
decision, so the CI/CD and observability tasks the plan skill makes mandatory for
URL-bearing specs are covered by that task itself plus task 12's degradation, and this
line is the reason: the only externally-addressable artifact is explicitly held behind the
privacy decision named in the spec's unresolved risks.

Order: doctrine (1) and constants (2) first — everything later cites them; the renderer
(3–5) before anything calls it; skills (7–9) after the commands exist so they can name real
verbs; the PR job (11) last because it consumes the recap.

1. [ ] **Doctrine room and the four always-on rules** —
   file: `tests/test_contracts.py` (one commit with `AGENTS.md`: cap and text move
   together). Raise `DOCTRINE_CEILING` 150 → 180; append to AGENTS.md the four rules from
   the spec's Decision (turn = Done-with-artifact or one-line `BLOCKED: … — unblock: …`;
   🟢//🔴 status line with legible 🟡; scale effort; do-the-work-not-ask) plus the link
   duty ("a command that writes a page prints its absolute URL; the skill shows it").
   check: `uv run pytest tests/test_contracts.py -k doctrine` — fails today (new AGENTS.md
   exceeds 150), green after the constant moves.
   rollback: `git revert` the one commit; both files return together.
   done when: AGENTS.md ≤180 lines carries the four rules and the link duty, and the
   ceiling test is green.

2. [ ] **Budget constants** —
   file: `src/ai_engineering/contract.py`. Add `RECAP_TABS_MIN = 3`, `RECAP_TABS_MAX = 8`,
   `RECAP_EXCERPT_LINES_MAX = 150`, `PAGE_TITLE_MAX = 70` beside `SKILL_FOG_CEILING`;
   harvested from the MIT visual-recap budgets (attribution arrives with task 6).
   check: `uv run python -c "from ai_engineering import contract; print(contract.RECAP_TABS_MAX)"`
   prints `8` — fails today (AttributeError).
   rollback: `git revert`; no reader exists yet.
   done when: the four names import and print.

3. [ ] **The visual block grammar and its loud-ignorance rule** —
   file: `src/ai_engineering/pages.py` (new module: fenced ` ```visual ` JSON block
   extraction from Markdown, the block vocabulary, unknown-block warning section, HTML
   escaping, and the shared self-contained page template authored via
   `importlib.resources` — stdlib only).
   check: `uv run python -m pytest tests/test_pages.py -k visual_block` over a new
   `tests/test_pages.py` that feeds one known block and one unknown block — fails today
   (no module), green after; the unknown block must appear in a warning section, never
   vanish.
   rollback: `git revert` both files; nothing imports the module yet.
   done when: extraction, escaping, budgets-as-constants and the loud unknown-block path
   all have passing tests.

4. [ ] **`ai-eng report view` — the spec/plan review page** —
   file: `src/ai_engineering/report.py` (subcommand `view`, inside the existing family —
   report.py:139-143 is why this is not an eleventh verb). Renders
   `specs/NNN-slug/spec.md` + `plan.md` through `pages.py` to
   `.ai/views/<NNN>-<slug>.html`; header carries the sha256 digest and date of the exact
   bytes rendered; prints the absolute `file://` URL; missing spec → `INCOMPLETE`,
   nonzero, no file.
   check: `uv run ai-eng report view --spec 046 && uv run ai-eng report view --spec 046 &&
   shasum -a 256 .ai/views/046-visual-html-records.html` twice shows one identical hash,
   and `uv run ai-eng report view --spec 999` exits nonzero naming the missing spec.
   rollback: `git revert`; subcommand and its tests leave together.
   done when: two runs are byte-identical, the URL prints, the digest header matches the
   spec bytes, and the refusal path writes nothing.

5. [ ] **`ai-eng report recap` — the post-build visual record** —
   file: `src/ai_engineering/report.py` + `src/ai_engineering/pages.py`. Builds
   `.ai/reports/NNN-recap-<slug>.html` (existing doctor regex admits the shape): file-tree
   with change flags and 3–8 key-change diff excerpts **derived mechanically from `git
   diff --name-status/-U<…>` against `--base`** (a diff block that is not a real hunk
   refuses), 1–3 paragraph narrative from `--summary` or a `visual` narrative block, the
   spec digest, the verification commands it is told, and secret redaction before writing.
   check: `uv run ai-eng report recap --spec 046 --base $(git rev-parse HEAD~1) --summary
   "…"` exits 0; the page's file list equals `git diff --name-status <base>`; excerpt count
   ≤ 8 and each ≤ 150 lines — fails today (no subcommand).
   rollback: `git revert`.
   done when: a recap of a real range renders, every budget comes from `contract.py`, and
   a fabricated diff block is refused by test.

6. [ ] **The views home in the one-home gate** —
   file: `src/ai_engineering/doctor.py` (grow the allowed shape beside the reports regex
   at doctor.py:789-795) and the shipped `.ai/.gitignore` template (find it via the
   template that re-allows `!reports/…`; the pin and doctor must agree).
   check: `uv run ai-eng doctor` green with `.ai/views/046-visual-html-records.html` on
   disk; a stray `.ai/views/notes.txt` makes it fail — today doctor flags the directory.
   rollback: `git revert` both files; views become violations again, the pre-state.
   done when: doctor accepts exactly `views/[0-9][0-9][0-9]-*.html` and nothing else there.

7. [ ] **The harvested guidance, attributed** —
   file: `policy/visual-pages.md` (new: the condensed block taxonomy, diff→block mapping,
   grounding rules, no-boilerplate, before/after comparability, budgets referenced only as
   "`contract.py` names") headed with the Builder.io MIT (c) 2026 attribution and the
   report-021 derivation note.
   check: `uv run python -c "import pathlib; t=pathlib.Path('policy/visual-pages.md').read_text(); assert 'MIT' in t and 'Builder' in t and 'contract.py' in t"`.
   rollback: `git revert`; runtime code never reads this file — it is the authoring
   reference for tasks 8–10's skills.
   done when: the file exists, attributes, and carries zero loose budget numbers.

8. [ ] **`ai-visual-plan` — the skill that turns any plan into the review page** —
   file: `.agents/skills/ai-visual-plan/SKILL.md` (with `corpus.md` in the same commit —
   the contract refuses a skill without both). Trigger: "make this plan visual", "rich
   review surface", a pasted/foreign text plan needing approval review. Procedure: research
   real files first (harvested Plan Discipline), author `visual` blocks into the plan
   Markdown, run `ai-eng report view`, show the `file://` link; planning stays read-only
   on source; never hand-write HTML.
   check: `just check` green (fog ≤11.03, frontmatter allowlist, forced-output "Done when"
   names the link, corpus Routes/Refuses) — fails today (directory absent).
   rollback: `git revert`; removes the skill directory whole.
   done when: the skill passes the contract and its `## Done when` is the printed link plus
   the rendered page.

9. [ ] **`ai-visual-recap` — the skill that turns a diff into the recap page** —
   file: `.agents/skills/ai-visual-recap/SKILL.md` + `corpus.md`. Trigger: "recap this
   PR/branch/work unit", "what did this change", post-build hand-off. Procedure: scope the
   whole work unit, run `ai-eng report recap` with the real base, add narrative and any
   UI before/after `visual` blocks from the diff, show the link; skip rule for tiny diffs
   (a recap is review overhead); grounding bar: narrative claims cite files the diff
   touches.
   check: `just check` green; plus a live pass — recap this spec's own approval-to-HEAD
   range and the link opens.
   rollback: `git revert`.
   done when: contract-green skill, and one real recap page rendered through it.

10. [ ] **The cycle verbs point at the pages** —
    file: `.agents/skills/ai-spec/SKILL.md` (one commit with `ai-plan`, `ai-build`,
    `ai-goal`, `ai-ship`, `ai-research` — same edit family, link duty only). ai-spec/
    ai-plan: after writing, call `report view` and hand the human the link beside the
    Markdown. ai-build/ai-goal hand-off: call `report recap` (via ai-visual-recap) and put
    the link in the hand-off. ai-ship: recap link into the PR body. ai-research: print the
    `file://` URL of the report it already writes. No page authoring by prose (D-046-02).
    check: `just check` green — fails if a skill names a budget number or hand-writes HTML
    instead of the command.
    rollback: `git revert`; skills return to Markdown-only pointers, which still work.
    done when: six skills name the command they run and the link they show.

11. [ ] **The visual PR-review job, degrading honestly** —
    file: `.github/workflows/check.yml` (add a `recap` job on `pull_request`: run
    `ai-eng report recap` against the PR base; if Pages is enabled for
    `arcasilesgroup/ai-engineering`, publish and comment the URL; else upload the page as
    an Actions artifact and comment saying so — D-046-04). Bot comment = Markdown summary
    (title, outcome paragraph, file count) + exactly one link.
    check: the workflow's own lint (`uv run python -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]"`) plus the
    observed behaviour on the next real PR: a comment with one link that opens the page.
    rollback: `git revert`; the job disappears, local recaps unaffected.
    done when: a PR carries the summary-plus-link comment and the linked page renders; the
    Pages-privacy decision (spec risk) is recorded in the PR or an ADR before any public
    URL appears.

12. [ ] **End-to-end smoke and the changelog** —
    file: `CHANGELOG.md`. Run the whole flow on spec 046 itself: `report view`,
    `report recap` over this plan's own range, open both pages, confirm digest headers,
    confirm both links open in the browser, confirm `doctor` green over `.ai/views/` +
    `.ai/reports/`. Changelog states the clean cut: views derived, recaps records, ADR
    digests still the gate, ceiling 150→180.
    check: `just check` fully green as the final gate, plus the human-visible pair: two
    pages, two working links.
    rollback: `git revert` the changelog commit only; machinery reviewed in 1–11.
    done when: the two pages for 046 render, budgets hold, gate green, everything committed.

## What this plan is not doing, and why

- **No MDX, no npm, no hosted Plan surface** — the user's constraint and the audit.
- **No `ai-arbitrate` / `ai-watchdog` skills** — report 021 phases them separately; binding
  two independent cutovers to one gate is how a review gets hostage.
- **No enabling GitHub Pages from this plan** — task 11 degrades to artifact links; the
  public-URL privacy decision is the human's, named in the spec's unresolved risks.
- **No guard forcing a recap per build yet** — rule 12: the capability and convention first;
  three receipts of the same judgement decide whether enforcement becomes code.
- **No interactive commenting on the pages** — hosted-plan comments need the hosted
  surface; feedback here is file/chat feedback applied to the Markdown, then regenerate.
