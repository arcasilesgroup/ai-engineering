---
name: ai-pr
description: "Creates and updates pull requests with governance: runs the commit pipeline, enforces pre-push gates, generates structured PR body from spec, watches and fixes CI until merged. Trigger for 'open a PR', 'submit this for review', 'I am ready for review', 'merge this into main', 'draft PR', 'update the PR'. Not for commit-only flows; use /ai-commit instead. Not for narrative review; use /ai-review instead."
effort: mid
model_tier: sonnet
argument-hint: "review|create|update|--draft|--only|--consolidate-spec|[title]"
tags: [git, pull-request, ci, merge, delivery]
requires:
  bins:
    - gitleaks
  anyBins:
    - gh
    - az
---

# PR Workflow

Governed PR creation: full commit pipeline, pre-push gates, structured PR with summary + test plan, auto-complete with squash merge and branch deletion.

`/ai-pr` is the canonical chain step `brainstorm → plan → build → pr` — it runs the commit pipeline internally; the operator does NOT run `/ai-commit` first. `/ai-commit` exists as a standalone off-chain skill for WIP-only commits where no PR is wanted.

```
/ai-pr                  # full pipeline + create or update PR
/ai-pr --draft          # open as draft (no review request)
/ai-pr review           # request review on existing PR
/ai-pr update           # refresh PR body + push amended commit
```

## Process

### Decision preamble (resolve once)

Resolve before Step 0; later steps read these, never re-decide. `draft?` (`--draft`) → skip review request, consolidation (Step 14b), watch loop. `existing_pr?` (`gh pr list --head <branch>` / `az repos pr list` finds a PR) → extend, never overwrite. `placeholder_spec?` (`spec.md` = `# No active spec`) → skip spec ops + consolidation, fall back to label-based PR body.

### Steps 0-6: Inline Commit Pipeline

Step 0 — **Auto-branch** from `main`/`master`: infer type (`feat/`, `fix/`, `chore/`, `docs/`, `refactor/`), generate slug with `python3 .ai-engineering/scripts/branch_slug.py --prefix <type>`, then `git checkout -b <output>`.
Step 1 — **Work-item context (opt)**: spec.md frontmatter `refs` → commit body trailers (`Refs: AB#101, #45`); only `close_on_pr` items, never features.
Step 2 — **Instinct consolidation**: if `.ai-engineering/observations/observations.yml` exists, run `/ai-session-watch --review` before committing.
Step 3 — **Stage** selectively (`git add <file>...`). Use `git add -A` only when explicitly requested. Exclude generated files, secrets, large binaries.
Step 4 — **Run gate orchestrator**: `ai-eng gate run --cache-aware --json --mode=local`. The 2-wave collector (Wave 1 fixers serial → Wave 2 checkers parallel) emits `.ai-engineering/state/gate-findings.json` (schema v1); Wave 1 re-stages the safe `S_pre & M_post` intersection (spec-105 D-105-09; disable via `--no-auto-stage` or manifest `gates.pre_commit.auto_stage: false`).
Step 5 — **Handle gate**: exit 0 → continue. Exit non-zero → STOP, fix root cause, re-run. Publish-window override: `ai-eng risk accept-all .ai-engineering/state/gate-findings.json --justification "<reason>" --spec <id> --follow-up "<plan>"` (see `.ai-engineering/reference/risk-acceptance-flow.md`).
Step 6 — **Docs gate** inside the orchestrator is mandatory; see `.ai-engineering/reference/gate-policy.md` for the local fast-slice + CI authoritative split.

### 7. Concurrent dispatch -- docs + pre-push gate (3 lanes)

Total wall-clock = `max(docs, pre-push)`, NOT `sum`. Docs subagents and the pre-push gate run in parallel; PR description stays coherent because docs are produced and staged BEFORE PR creation.

1. **Read flags** from `.ai-engineering/manifest.yml` (`documentation.auto_update`, `external_portal`).
2. **Compute diff once** -- `git diff main...HEAD`. Pass to both docs agents.
3. **Dispatch 3 concurrent lanes**, block on `max(lane1, lane2, lane3)`:
   - **Lane 1 -- docs A1**: `/ai-docs changelog` + `/ai-docs readme` (if enabled).
   - **Lane 2 -- docs A2**: `/ai-docs solution-intent-sync` (if architecture changed) + `/ai-docs docs-portal` + `/ai-docs docs-quality-gate`. Zero uncovered items required.
   - **Lane 3 -- pre-push gate**: dispatched concurrently here; Step 9 owns the full description. Do not restate the gate command in both places.
4. **Stage all docs files** produced by lanes 1-2 BEFORE PR creation. spec-104 NG-7 forbids deferring docs to a separate commit -- regulated audience requires clean audit history.

### 9. Pre-push gate (canonical description; concurrent Lane 3 of step 7)

Dispatched concurrently with the docs lanes — total wall-clock is `max(docs, pre-push)`, not the legacy sum. `ai-eng gate run --cache-aware --json --mode=local` runs Wave 1 fixers (`ruff format` → `ruff check --fix` → `spec verify --fix`) in parallel with Wave 2 checkers (`gitleaks protect --staged`, `ty check src/`, `pytest -m smoke`, `ai-eng validate`, docs gate). CI uses `--mode=ci` (adds `semgrep`, `pip-audit`, full `pytest` matrix). Non-zero exit → parse `gate-findings.json`, report, STOP; resolve or accept via `ai-eng risk accept-all` (see `.ai-engineering/reference/risk-acceptance-flow.md`).

### 10. Work item context

Read `.ai-engineering/manifest.yml` `work_items` and spec.md frontmatter `refs` (yaml shape: `features` never close, `user_stories`/`tasks`/`bugs`/`issues` close on PR merge).

### 11. Spec operations (PR body)

If `.ai-engineering/specs/spec.md` is non-placeholder: read spec.md + plan.md to generate the PR description; run `ai-eng spec verify --fix`; update spec.md/plan.md to reflect ACTUAL scope; use the updated content for the PR body (Summary from spec, Test Plan from plan). Consolidation does NOT happen here — per D-167-07 it runs pre-merge on the feature branch in **Step 14b**, so the archive + slot-clear ride this same PR instead of a separate follow-up chore PR.

### 12. Work item references

If frontmatter has `refs`:

- `close_on_pr` items (user_stories, tasks, bugs, issues): GitHub `Closes #N` per line; Azure `AB#NNN` (auto-closes on merge).
- `never_close` items (features): `Related: AB#100` only -- NEVER close features (absolute rule).
- No `refs`: fall back to spec-label-based linking.

### 13. Commit, push, detect VCS, find existing PR

Compose the commit subject deterministically (spec-139 M8 D-139-06): derive the description from the current `.ai-engineering/specs/plan.md` task title (`grep -m1 '^- \[ \] ' .ai-engineering/specs/plan.md`) and pass it via `python3 .ai-engineering/scripts/commit_compose.py --type <type> [--task X.Y] --desc "$TASK_TITLE"`. `--desc` is mandatory; the legacy `<DESC>` placeholder fallback is deprecated for the PR pipeline. Push to current branch (block on `main`/`master`). Detect provider via `manifest.yml` `providers.vcs.primary`, fallback to `git remote get-url origin` parsing (`github.com` -> `gh`, `dev.azure.com` -> `az repos`). Find existing PR with `gh pr list --head <branch>` or `az repos pr list --source-branch <branch>`.

### 14. Create or update PR

Runs after the 3-lane block resolves so the body is coherent (CHANGELOG/README staged, gate passed). Compose body deterministically: `python3 .ai-engineering/scripts/pr_body_compose.py` reads `.ai-engineering/specs/spec.md` frontmatter (`summary:` field — mandatory per spec-139 M8 D-139-06 after the 2026-06-16 cutover) plus plan.md `[ ]` rows and emits Summary, Test Plan, Work Items, Checklist sections. **When `summary:` is present in the spec frontmatter the PR body Summary section is composed without any LLM call.** Legacy specs that predate the field fall back to `--bullets-prompt "<llm-bullets>"`; emit an advisory warning prompting the operator to backfill the spec frontmatter `summary:` field. Do NOT pass `--bullets-prompt` when the active spec already declares `summary:`.

**New**: `gh pr create --title "<t>" --body "<b>"` or `az repos pr create --source-branch <b> --target-branch <t> --title "<t>" --description "<b>"`.

**Existing** (extend, NEVER overwrite): read existing body; if `## Additional Changes` exists, append a `### <date> / <commit-range>` sub-heading underneath; otherwise append `\n\n---\n\n## Additional Changes` first. Update via `gh pr edit` or `az repos pr update`.

### 14b. Consolidate on the feature branch (pre-merge, D-167-07)

Runs after Step 14 (PR number `N` known), before Step 15 auto-complete; **skip for `--draft`** (a draft is not merging — consolidate on promotion, else it sits SHIPPED while open). If `.ai-engineering/specs/spec.md` is non-placeholder, resolve the numeric id from its frontmatter `spec:` (canonical `spec-NNN`, not the slug — spec-153 D-153-01) and run `python .ai-engineering/scripts/spec_lifecycle.py mark_shipped <spec-NNN> N <branch>` **directly** — NOT via `_shared/consolidate-spec.md`, whose SHIPPED-precondition guard would reject the still-IN_PROGRESS pre-merge spec (marking it SHIPPED as the ship-PR opens is the intent here). It walks state→SHIPPED, appends the 7-col `_history.md` row, snapshots spec.md+plan.md into `archive/spec-NNN-<slug>/`, clears both to placeholders, and emits the audit event. Then `git add` the archived+cleared files, commit `chore(spec-NNN): consolidate (archive + clear live slot)`, and push so the open PR updates. **Fail-open**: a write failure logs, never blocks. Consolidation rides the PR regardless of `gh`/`az`/web-UI merge — no separate chore PR; the same handler stays manual via `/ai-pr --consolidate-spec`, and `/ai-branch-cleanup` `reconcile_merged` is now a no-op backstop.

### 15. Board sync + enable auto-complete

For new PRs with `refs`: invoke `/ai-board sync in_review <ref>` for each non-`never_close` ref (fail-open: never block on failure). Then enable auto-complete: `gh pr merge --auto --squash --delete-branch` or `az repos pr update --id <id> --auto-complete true --squash true --delete-source-branch true`.

### 16. Watch and fix until merge

Auto-complete only queues the merge -- CI must pass first. The Step 14b consolidation commit is already part of the branch, so the CI run the loop watches is the FINAL commit set — and it now runs against the idle `# No active spec` slot (D-167-07); every spec.md-reading gate must tolerate that placeholder. Enter the watch-and-fix loop following `handlers/watch.md`. The loop polls every 1 min (active) or 3 min (passive), autonomously fixes CI failures and merge conflicts, handles team/org-internal-bot review comments, and escalates after 3 failed attempts on the same check or wall-clock cap. Drafts skip the loop entirely.

Once `state == "MERGED"`: run `/ai-branch-cleanup --all` and report.

### 17. Self-verify (terminal)

Turn "did every step run?" into a checkable post-condition — the catch for a silently-skipped consolidation (the PR #190 class). Re-read + assert; any failure → STOP loud, naming the skip. **Always** assert: the step-7 CHANGELOG/README edits rode this commit (not deferred); the Step 14 PR number resolves (`gh pr view <N>` / `az repos pr show`). **Unless** `draft?` or `placeholder_spec?` (nothing consolidated), also assert: `spec.md`/`plan.md` cleared to the `# No active spec`/`# No active plan` placeholders; `_history.md` carries the `spec-NNN` row.

### `/pr --only` / `/pr --draft`

`--only`: skip commit pipeline (verify branch pushed, detect VCS, create/update PR, enable auto-complete). `--draft`: open as draft.

## PR Structure

Title: `type(scope): description` or `spec-NNN: Task X.Y -- description` (max 72 chars). Body: `## Summary` (2-3 bullets), `## Test Plan` (verification steps), `## Work Items` (Closes AB#NNN — only `close_on_pr` items), `## Checklist` (lint/secret/tests/CHANGELOG/breaking-changes).


## Drift recovery

Exit 78 = stack drift. Run `ai-eng doctor --fix` in shell, retry. Never `--no-verify`. See .ai-engineering/reference/cli-reference.md for the 6-stack tool matrix.

## Examples

### Example 1 — open a PR after finishing a feature

User: "I'm ready for review on this branch"

```
/ai-pr
```

Runs commit pipeline (0-6), pre-push gates, generates PR body from the spec's Summary + Test Plan, opens via `gh pr create`, transitions board state, watches CI.

### Example 2 — draft PR for early feedback

User: "open a draft so the team can comment on the approach"

```
/ai-pr --draft
```

Same pipeline, but opens with `--draft` and skips the review request; reviewers get notified once `/ai-pr review` is invoked.

## Quick Reference

| Goal | Command |
|------|---------|
| Open PR (default) | `/ai-pr` |
| Open as draft | `/ai-pr --draft` |
| Skip CI watch | `/ai-pr --no-watch` |
| Update existing PR | `/ai-pr --update` |
| Resume after merge | `/ai-branch-cleanup` (auto-invoked) |

## Integration

Calls: `/ai-docs` subagents (CHANGELOG, README, portal, quality-gate), `/ai-board sync` (post-create), `gh pr create` / `az repos pr create`. Runs inline: commit pipeline (Steps 0-6 — same logic as the standalone `/ai-commit` skill, copied for chain clarity). Watches: CI via `handlers/watch.md`. Reads: `manifest.yml`, spec frontmatter for linked work items. See also: `/ai-commit` (off-chain WIP-only), `/ai-review`, `/ai-resolve-conflicts`.

$ARGUMENTS
