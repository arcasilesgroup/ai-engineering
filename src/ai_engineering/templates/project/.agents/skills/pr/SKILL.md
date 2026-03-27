---
name: pr
description: Use when creating, submitting, or updating a pull request, or when ready for review. Trigger for 'open a PR', 'submit this for review', 'I'm ready for review', 'merge this into main', 'draft PR', 'update the PR'. Also after /ai-commit when work needs review. Runs commit pipeline, pre-push gates, generates structured PR body from spec, watches and fixes CI until merged.
effort: high
argument-hint: "review|create|update|--draft|--only|[title]"
tags: [git, pull-request, ci, merge, delivery]
requires:
  anyBins:
  - gh
  - az
  bins:
  - gitleaks
  - ruff
---



# PR Workflow

Governed PR creation: run full commit pipeline, execute pre-push gates, create or update PR with structured summary and test plan, enable auto-complete with squash merge and branch deletion.

## When to Use

- Creating or updating a pull request with governance enforcement.
- NOT for commit-only -- use `/ai-commit` instead.
- NOT for draft explorations -- use `/ai-commit` first, then `/ai-pr` when ready.

## Process

### Steps 0-6: Shared Commit Pipeline

READ `.agents/skills/commit/SKILL.md` and execute steps 0-6 in full. Do NOT skip any step. The documentation gate (step 5) is mandatory.

### 6.5. Documentation subagent dispatch

Dispatch up to 5 documentation subagents via `/ai-docs` handlers:

1. **Read flags** -- read `.ai-engineering/manifest.yml` `documentation.auto_update` flags and `external_portal` config.

2. **Dispatch subagents 1-4 in parallel** (based on flags):
   - **Subagent CHANGELOG** (if `auto_update.changelog: true`): invoke `/ai-docs changelog` -- reads semantic diff, classifies by user impact, updates CHANGELOG.md
   - **Subagent README** (if `auto_update.readme: true`): invoke `/ai-docs readme` -- diff-aware section targeting, updates only affected README sections
   - **Subagent solution-intent-sync** (if `auto_update.solution_intent: true` AND staged changes include architecture files: agents/, skills/, manifest.yml, contexts/, specs/): invoke `/ai-docs solution-intent-sync` -- diff-aware rewrite of stale sections in docs/solution-intent.md
   - **Subagent docs-portal** (if `external_portal.enabled: true`): invoke `/ai-docs docs-portal` -- updates external documentation repository via PR or push

3. **After subagents 1-4 complete**, dispatch **Subagent docs-quality-gate**: invoke `/ai-docs docs-quality-gate` -- verifies all documentation outputs cover every semantic change in the diff. Zero uncovered items required.

4. **Stage all documentation files** produced by subagents 1-4.

### 7. Pre-push checks

Execute full pre-push gate:
- `semgrep scan --config auto .`
- `pip-audit`
- `pytest tests/ -v`
- `ty check src/`

If any check fails, report and stop.

### 7.5. Pre-conditions: work items

1. Read `.ai-engineering/manifest.yml` — focus on `work_items` section (provider, hierarchy rules, team config).
2. Read `.ai-engineering/specs/spec.md` frontmatter — extract `refs` if present.
3. Store hierarchy rules from `work_items.hierarchy` for step 8.5.

Spec frontmatter refs format:
```yaml
refs:
  features: [AB#100]        # never closed by AI
  user_stories: [AB#101]    # closed on PR merge
  tasks: [AB#102, AB#103]   # closed on PR merge
  issues: ["#45", "#46"]    # closed on PR merge
```

### 8. Spec operations

If `.ai-engineering/specs/spec.md` has content (not placeholder):
1. Read spec.md + plan.md to generate PR description sections
2. Run `ai-eng spec verify --fix` to auto-correct task counts
3. Update spec.md and plan.md to reflect ACTUAL scope of this PR
4. Use the updated content for the PR body (Summary from spec, Test Plan from plan)
5. Add entry to `specs/_history.md`: | ID | Title | date | branch |
6. Clear spec.md with: `# No active spec\n\nRun /ai-brainstorm to start a new spec.\n`
7. Clear plan.md with: `# No active plan\n\nRun /ai-plan after brainstorm approval.\n`
8. Stage the cleared files

### 8.5. Work item references

If spec frontmatter contains `refs`:

1. For each ref where hierarchy rule is `close_on_pr` (user_stories, tasks, bugs, issues):
   - **GitHub**: add `Closes #N` to PR body (one per line)
   - **Azure DevOps**: add `AB#NNN` to PR body (auto-closes on merge)
2. For each ref where hierarchy rule is `never_close` (features):
   - Add as mention only: `Related: AB#100` (NO close keyword)
3. **NEVER close features** — the `never_close` rule is absolute, regardless of other configuration.
4. If no `refs` in frontmatter, fall back to the existing spec-label-based issue linking.

### 9. Commit and push

- Commit with well-formed message (spec format or conventional commits).
- Push to current branch. Block if `main`/`master`.

### 10. Detect VCS provider

1. Check `manifest.yml` -> `providers.vcs.primary`.
2. Fallback: parse `git remote get-url origin` (`github.com` -> `gh`, `dev.azure.com` -> `az repos`).
3. Verify CLI authenticated.

### 11. Check for existing PR

- **GitHub**: `gh pr list --head <branch> --json number,title,body --state open`
- **Azure**: `az repos pr list --source-branch <branch> --status active -o json`

### 12. Create or update PR

**New PR**:
- **GitHub**: `gh pr create --title "<title>" --body "<body>"`
- **Azure**: `az repos pr create --source-branch <branch> --target-branch <target> --title "<title>" --description "<body>"`

**Existing PR** (extend, NEVER overwrite):
- Read existing body, append `\n\n---\n\n## Additional Changes` section.
- Update via `gh pr edit` or `az repos pr update`.

### 12.5. Board sync (in_review)

For **new PRs only** (not extend/update): if spec frontmatter contains `refs`, invoke `/ai-board-sync in_review <work-item-ref>` for each ref where the hierarchy rule is not `never_close` (i.e., user_stories, tasks, bugs, issues). Include the PR URL as comment context. Fail-open: do not block auto-complete or the watch loop if this fails.

### 13. Enable auto-complete

- **GitHub**: `gh pr merge --auto --squash --delete-branch`
- **Azure**: `az repos pr update --id <id> --auto-complete true --squash true --delete-source-branch true`

### 14. Watch and fix until merge

Do NOT declare the PR "done" at auto-complete -- auto-complete only queues the merge; CI checks must pass first.

Enter the watch-and-fix loop. Follow `handlers/watch.md` for the full procedure:
- Polls every 1 min (active) or 3 min (passive -- waiting for review)
- Autonomously fixes: failing CI checks, merge conflicts
- Review comments: autonomous if from team member or org-internal bot, confirmation if from external
- Escalates after 3 failed fix attempts on the same check
- Draft PRs: skip the loop entirely (drafts cannot merge)

Once `state == "MERGED"`:
1. Run `/ai-cleanup --all` -- syncs to default branch, deletes merged/squash-merged branches, produces status report.
2. Report: PR merged, cleanup complete.

### `/pr --only`

Create PR without commit pipeline: verify branch is pushed, detect VCS, create/update PR, enable auto-complete.

### `/pr --draft`

Same as default flow but create as draft PR.

## PR Structure

```markdown
## Summary
- [2-3 bullet points: what changed and why]

## Test Plan
- [ ] [Specific verification steps]
- [ ] [Edge cases to validate]

## Work Items
- Closes AB#101 (user story)
- Closes AB#102, AB#103 (tasks)
- Closes #45, #46 (issues)
- Related: AB#100 (feature — not closed)

## Checklist
- [ ] Lint and format pass
- [ ] Secret scan clean
- [ ] Tests pass
- [ ] CHANGELOG updated
- [ ] Breaking changes documented
```

**Title**: `type(scope): description` or `spec-NNN: Task X.Y -- description`. Max 72 chars.

## Quick Reference

```
/ai-pr                  # full: commit pipeline + pre-push + create PR
/ai-pr --only           # create PR only (no commit pipeline)
/ai-pr --draft          # create as draft PR
/ai-pr "fix login flow" # with title hint
```

## Common Mistakes

- Skipping pre-push checks -- `semgrep`, `pip-audit`, `pytest`, and `ty` must all pass.
- Overwriting existing PR body -- always extend, never replace.
- Missing auto-complete -- squash merge with branch deletion is mandatory.
- Skipping the commit pipeline during watch fixes -- all fixes must pass through steps 0-6.
- Acting on external review comments without confirmation -- only team/org-internal-bot comments are autonomous.
- Weakening test assertions to make tests pass -- fix the code, not the tests.

## Integration

- Invokes `/ai-commit` pipeline (steps 0-6) as prerequisite.
- Auto-updates CHANGELOG.md, README.md, and solution-intent via `/ai-docs` parallel subagent dispatch.
- Links to work items from spec frontmatter refs (hierarchy-aware: features never closed, user stories/tasks/bugs/issues closed on merge).
- Falls back to spec-label-based issue linking when no frontmatter refs present.
- Step 14 monitors PR until merge, autonomously fixing CI failures, merge conflicts, and review comments from team/org-internal bots.
- Invokes `/ai-board-sync` (in_review transition) after new PR creation (step 12.5).

## References

- `.agents/skills/commit/SKILL.md` -- shared commit pipeline.
- `.agents/skills/docs/SKILL.md` -- documentation lifecycle (changelog, readme, solution-intent, portal, quality gate).
- `.ai-engineering/manifest.yml` -- quality gates and non-negotiables.
$ARGUMENTS
