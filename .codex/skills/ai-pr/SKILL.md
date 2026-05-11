---
name: ai-pr
description: "Creates and updates pull requests with governance: runs the commit pipeline, enforces pre-push gates, generates structured PR body from spec, watches and fixes CI until merged. Trigger for 'open a PR', 'submit this for review', 'I am ready for review', 'merge this into main', 'draft PR', 'update the PR'. Not for commit-only flows; use /ai-commit instead. Not for narrative review; use /ai-review instead."
effort: mid
argument-hint: "review|create|update|--draft|--only|--consolidate-spec|[title]"
tags: [git, pull-request, ci, merge, delivery]
requires:
  anyBins:
  - gh
  - az
  bins:
  - gitleaks
model_tier: sonnet
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-pr/SKILL.md
edit_policy: generated-do-not-edit
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

### Step 0: Auto-branch from protected

If current branch is `main`/`master`: infer type (`feat/`, `fix/`, `chore/`, `docs/`, `refactor/`), generate slug deterministically with `python3 .ai-engineering/scripts/branch_slug.py --prefix <type>` (reads spec.md frontmatter), then `git checkout -b <output>`, report new branch.

### Step 1: Work item context (optional)

If `.ai-engineering/specs/spec.md` frontmatter has `refs`: include work item refs as commit body trailers (`Refs: AB#101, AB#102, #45`). Only include `close_on_pr` items — never features.

### Step 2: Instinct consolidation

If `.ai-engineering/observations/observations.yml` exists, run `/ai-observe --review` to consolidate session observations before committing.

### Step 3: Stage changes

`git add <file1> <file2>` selectively. Use `git add -A` only when explicitly requested. Exclude generated files, secrets, large binaries.

### Step 4: Run gate orchestrator

```
ai-eng gate run --cache-aware --json --mode=local
```

The orchestrator runs the 2-wave collector (Wave 1 fixers serial → Wave 2 checkers parallel) with cache-aware lookup, emitting `.ai-engineering/state/gate-findings.json` (schema v1) covering every check. After Wave 1 fixers rewrite files, the orchestrator re-stages the safe `S_pre & M_post` intersection (spec-105 D-105-09); pass `--no-auto-stage` to disable, or set `gates.pre_commit.auto_stage: false` in the manifest.

### Step 5: Handle gate result

- **Exit 0** — all checks PASS or auto-fixed. Continue to Step 6.
- **Exit non-zero** — parse `gate-findings.json`, report failing checks per `rule_id` + `severity`, **STOP**. Fix root cause, re-stage, re-run. Override only when remediation is tracked elsewhere and the publish window forces it: `ai-eng risk accept-all .ai-engineering/state/gate-findings.json --justification "<reason>" --spec <spec-id> --follow-up "<plan>"` writes one DEC entry per finding with severity-default TTL (see `.ai-engineering/contexts/risk-acceptance-flow.md`).

### Step 6: Confirm commit readiness

The documentation gate inside the orchestrator is mandatory. See `.ai-engineering/contexts/gate-policy.md` for the local fast-slice + CI authoritative split.

### 7. Concurrent dispatch -- docs + pre-push gate (3 lanes)

Total wall-clock = `max(docs, pre-push)`, NOT `sum`. Docs subagents and the pre-push gate run in parallel; PR description stays coherent because docs are produced and staged BEFORE PR creation.

1. **Read flags** from `.ai-engineering/manifest.yml` (`documentation.auto_update`, `external_portal`).
2. **Compute diff once** -- `git diff main...HEAD`. Pass to both docs agents.
3. **Dispatch 3 concurrent lanes**, block on `max(lane1, lane2, lane3)`:
   - **Lane 1 -- docs A1**: `/ai-docs changelog` + `/ai-docs readme` (if enabled).
   - **Lane 2 -- docs A2**: `/ai-docs solution-intent-sync` (if architecture changed) + `/ai-docs docs-portal` + `/ai-docs docs-quality-gate`. Zero uncovered items required.

- **Lane 3 -- pre-push gate**: `ai-eng gate run --cache-aware --json --mode=local` (orchestrator delivers Wave 1 fixers serial then Wave 2 checkers parallel; see step 9).

4. **Stage all docs files** produced by lanes 1-2 BEFORE PR creation. spec-104 NG-7 forbids deferring docs to a separate commit -- regulated audience requires clean audit history.

### 8. Instinct consolidation

If `.ai-engineering/observations/observations.yml` exists, run `/ai-observe --review`.

### 9. Pre-push gate (Lane 3 of step 7)

`ai-eng gate run --cache-aware --json --mode=local` orchestrates Wave 1 fixers (`ruff format` -> `ruff check --fix` -> `spec verify --fix`) then Wave 2 checkers (`gitleaks protect --staged`, `ty check src/`, `pytest -m smoke`, `ai-eng validate`, docs gate) in parallel. CI matrix runs `--mode=ci` for the authoritative gate (`semgrep` + `pip-audit` + `pytest` full + matrix). See `.ai-engineering/contexts/gate-policy.md`.

If exit non-zero, parse `.ai-engineering/state/gate-findings.json`, report findings, STOP. Do not proceed unless all medium+ severity findings are resolved or accepted via `ai-eng risk accept-all .ai-engineering/state/gate-findings.json --justification "<reason>" --spec <spec-id> --follow-up "<plan>"` (each acceptance creates a DEC entry with TTL; see `.ai-engineering/contexts/risk-acceptance-flow.md`).

### 10. Work item context

Read `.ai-engineering/manifest.yml` `work_items` and `.ai-engineering/specs/spec.md` frontmatter `refs`:

```yaml
refs:
  features: [AB#100] # never closed by AI
  user_stories: [AB#101] # closed on PR merge
  tasks: [AB#102, AB#103] # closed on PR merge
  issues: ["#45", "#46"] # closed on PR merge
```

### 11. Spec operations

If `.ai-engineering/specs/spec.md` is non-placeholder: read spec.md + plan.md to generate PR description; run `ai-eng spec verify --fix`; update spec.md/plan.md to reflect ACTUAL scope; use updated content for PR body (Summary from spec, Test Plan from plan). After PR merge, run the shared spec-consolidation handler at `.codex/skills/_shared/consolidate-spec.md` (which invokes `python .ai-engineering/scripts/spec_lifecycle.py mark_shipped <spec-id> <pr> <branch>` to walk DRAFT→APPROVED→IN_PROGRESS→SHIPPED, append the canonical 7-col `_history.md` row, and emit the `framework_operation` audit event). **Fail-open**: lifecycle write failure logs but does not block merge. Then clear spec.md and plan.md to placeholders; stage cleared files. The same handler is exposed manually via `/ai-pr --consolidate-spec` as a pre-merge override.

### 12. Work item references

If frontmatter has `refs`:

- `close_on_pr` items (user_stories, tasks, bugs, issues): GitHub `Closes #N` per line; Azure `AB#NNN` (auto-closes on merge).
- `never_close` items (features): `Related: AB#100` only -- NEVER close features (absolute rule).
- No `refs`: fall back to spec-label-based linking.

### 13. Commit, push, detect VCS, find existing PR

Commit, push to current branch (block on `main`/`master`). Detect provider via `manifest.yml` `providers.vcs.primary`, fallback to `git remote get-url origin` parsing (`github.com` -> `gh`, `dev.azure.com` -> `az repos`). Find existing PR with `gh pr list --head <branch>` or `az repos pr list --source-branch <branch>`.

### 14. Create or update PR

Runs after the 3-lane block resolves so the body is coherent (CHANGELOG/README staged, gate passed). Compose body deterministically: `python3 .ai-engineering/scripts/pr_body_compose.py [--bullets-prompt "<llm-bullets>"]` reads spec.md/plan.md frontmatter and emits Summary, Test Plan, Work Items, Checklist sections. Use `--bullets-prompt` only when the LLM needs to author Summary bullets that the spec frontmatter does not capture.

**New**: `gh pr create --title "<t>" --body "<b>"` or `az repos pr create --source-branch <b> --target-branch <t> --title "<t>" --description "<b>"`.

**Existing** (extend, NEVER overwrite): read existing body; if `## Additional Changes` exists, append a `### <date> / <commit-range>` sub-heading underneath; otherwise append `\n\n---\n\n## Additional Changes` first. Update via `gh pr edit` or `az repos pr update`.

### 15. Board sync + enable auto-complete

For new PRs with `refs`: invoke `/ai-board sync in_review <ref>` for each non-`never_close` ref (fail-open: never block on failure). Then enable auto-complete: `gh pr merge --auto --squash --delete-branch` or `az repos pr update --id <id> --auto-complete true --squash true --delete-source-branch true`.

### 16. Watch and fix until merge

Auto-complete only queues the merge -- CI must pass first. Enter the watch-and-fix loop following `handlers/watch.md`. The loop polls every 1 min (active) or 3 min (passive), autonomously fixes CI failures and merge conflicts, handles team/org-internal-bot review comments, and escalates after 3 failed attempts on the same check or wall-clock cap. Drafts skip the loop entirely.

Once `state == "MERGED"`: run `/ai-cleanup --all` and report.

### `/pr --only` / `/pr --draft`

`--only`: skip commit pipeline (verify branch pushed, detect VCS, create/update PR, enable auto-complete). `--draft`: open as draft.

## PR Structure

Title: `type(scope): description` or `spec-NNN: Task X.Y -- description` (max 72 chars). Body: `## Summary` (2-3 bullets), `## Test Plan` (verification steps), `## Work Items` (Closes AB#NNN — only `close_on_pr` items), `## Checklist` (lint/secret/tests/CHANGELOG/breaking-changes).

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
| Resume after merge | `/ai-cleanup` (auto-invoked) |

## Integration

Calls: `/ai-docs` subagents (CHANGELOG, README, portal, quality-gate), `/ai-board sync` (post-create), `gh pr create` / `az repos pr create`. Runs inline: commit pipeline (Steps 0-6 — same logic as the standalone `/ai-commit` skill, copied for chain clarity). Watches: CI via `handlers/watch.md`. Reads: `manifest.yml`, spec frontmatter for linked work items. See also: `/ai-commit` (off-chain WIP-only), `/ai-review`, `/ai-resolve-conflicts`.

$ARGUMENTS
