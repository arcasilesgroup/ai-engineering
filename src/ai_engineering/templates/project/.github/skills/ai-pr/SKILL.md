---
name: ai-pr
description: Use when creating, submitting, or updating a pull request, or when ready for review. Trigger for 'open a PR', 'submit this for review', 'I'm ready for review', 'merge this into main', 'draft PR', 'update the PR'. Also after /ai-commit when work needs review. Runs commit pipeline, pre-push gates, generates structured PR body from spec, watches and fixes CI until merged.
effort: high
argument-hint: "review|create|update|--draft|--only|[title]"
mode: agent
tags: [git, pull-request, ci, merge, delivery]
requires:
  anyBins:
  - gh
  - az
  bins:
  - gitleaks
---


# PR Workflow

Governed PR creation: run full commit pipeline, execute pre-push gates, create or update PR with structured summary and test plan, enable auto-complete with squash merge and branch deletion.

## When to Use

- Creating or updating a PR with governance enforcement. Use `/ai-commit` for commit-only or draft explorations.

## Process

### Steps 0-6: Shared Commit Pipeline

READ `.github/skills/ai-commit/SKILL.md` and execute steps 0-6 in full. The documentation gate in the shared commit pipeline is mandatory.

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

If `.ai-engineering/instincts/instincts.yml` exists, run `/ai-instinct --review`.

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

If `.ai-engineering/specs/spec.md` is non-placeholder: read spec.md + plan.md to generate PR description; run `ai-eng spec verify --fix`; update spec.md/plan.md to reflect ACTUAL scope; use updated content for PR body (Summary from spec, Test Plan from plan); add entry to `specs/_history.md` (`| ID | Title | date | branch |`); clear spec.md and plan.md to placeholders; stage cleared files.

### 12. Work item references

If frontmatter has `refs`:

- `close_on_pr` items (user_stories, tasks, bugs, issues): GitHub `Closes #N` per line; Azure `AB#NNN` (auto-closes on merge).
- `never_close` items (features): `Related: AB#100` only -- NEVER close features (absolute rule).
- No `refs`: fall back to spec-label-based linking.

### 13. Commit, push, detect VCS, find existing PR

Commit, push to current branch (block on `main`/`master`). Detect provider via `manifest.yml` `providers.vcs.primary`, fallback to `git remote get-url origin` parsing (`github.com` -> `gh`, `dev.azure.com` -> `az repos`). Find existing PR with `gh pr list --head <branch>` or `az repos pr list --source-branch <branch>`.

### 14. Create or update PR

Runs after the 3-lane block resolves so the body is coherent (CHANGELOG/README staged, gate passed).

**New**: `gh pr create --title "<t>" --body "<b>"` or `az repos pr create --source-branch <b> --target-branch <t> --title "<t>" --description "<b>"`.

**Existing** (extend, NEVER overwrite): read existing body; if `## Additional Changes` exists, append a `### <date> / <commit-range>` sub-heading underneath; otherwise append `\n\n---\n\n## Additional Changes` first. Update via `gh pr edit` or `az repos pr update`.

### 15. Board sync + enable auto-complete

For new PRs with `refs`: invoke `/ai-board-sync in_review <ref>` for each non-`never_close` ref (fail-open: never block on failure). Then enable auto-complete: `gh pr merge --auto --squash --delete-branch` or `az repos pr update --id <id> --auto-complete true --squash true --delete-source-branch true`.

### 16. Watch and fix until merge

Auto-complete only queues the merge -- CI must pass first. Enter the watch-and-fix loop following `handlers/watch.md`. The loop polls every 1 min (active) or 3 min (passive), autonomously fixes CI failures and merge conflicts, handles team/org-internal-bot review comments, and escalates after 3 failed attempts on the same check or wall-clock cap. Drafts skip the loop entirely.

Once `state == "MERGED"`: run `/ai-cleanup --all` and report.

### `/pr --only` / `/pr --draft`

`--only`: create PR without commit pipeline (verify branch is pushed, detect VCS, create/update PR, enable auto-complete). `--draft`: same as default but create as draft.

## PR Structure

```markdown
## Summary

- [2-3 bullets: what changed and why]

## Test Plan

- [ ] [Specific verification steps + edge cases]

## Work Items

- Closes AB#101 (user story), Closes AB#102 (task), Closes #45 (issue)
- Related: AB#100 (feature — never closed)

## Checklist

- [ ] Lint/format pass, secret scan clean, tests pass, CHANGELOG updated, breaking changes documented
```

**Title**: `type(scope): description` or `spec-NNN: Task X.Y -- description`. Max 72 chars.

## Quick Reference

`/ai-pr` runs the full commit pipeline + pre-push gate + PR flow; `/ai-pr --only` skips the commit pipeline; `/ai-pr --draft` opens a draft; `/ai-pr "title hint"` seeds the PR title.

## Integration

- Invokes `/ai-commit` pipeline (steps 0-6) as prerequisite; consolidates `/ai-docs` subagents (CHANGELOG+README, docs-portal+quality-gate); invokes `/ai-board-sync` after new PR creation (step 15).
- Links work items from frontmatter refs (features never closed; user stories/tasks/bugs/issues closed on merge).
- Step 14 monitors PR via `handlers/watch.md`. Quality gates and non-negotiables sourced from `.ai-engineering/manifest.yml`.
  $ARGUMENTS
