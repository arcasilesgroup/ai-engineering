---
name: ai-pr
description: "Use when creating pull requests: governed PR workflow with commit pipeline, pre-push gates, auto-generated summary, and auto-complete squash merge."
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

READ `.github/prompts/ai-commit.prompt.md` and execute steps 0-6 in full. Do NOT skip any step. The documentation gate (step 5) is mandatory.

### 6.5. Doc gate verification

Safety net: verify documentation gate executed correctly.
- If staged changes include `src/` or `.ai-engineering/` files (excluding `state/`): CHANGELOG.md MUST be staged.
- For governance content changes: `.ai-engineering/README.md` SHOULD be staged and mirrored.

### 6.7. Solution intent sync

If staged changes include architecture files (agents/, skills/, manifest.yml, contexts/, specs/):
- Invoke `/ai-solution-intent sync` to update `docs/solution-intent.md`
- Stage the updated file

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
- Auto-updates CHANGELOG.md and README.md via documentation gate.
- Links to work items from spec frontmatter refs (hierarchy-aware: features never closed, user stories/tasks/bugs/issues closed on merge).
- Falls back to spec-label-based issue linking when no frontmatter refs present.
- Step 14 monitors PR until merge, autonomously fixing CI failures, merge conflicts, and review comments from team/org-internal bots.

## References

- `.github/prompts/ai-commit.prompt.md` -- shared commit pipeline.
- `.github/prompts/ai-write.prompt.md` -- changelog and documentation updates.
- `.ai-engineering/manifest.yml` -- quality gates and non-negotiables.
$ARGUMENTS

---

# Handler: Watch and Fix

## Purpose

Post-PR monitoring loop with autonomous repair. Fixes CI failures, resolves merge conflicts, and handles review comments. Team members and org-internal bots are handled autonomously; external commenters require user confirmation. Exits when PR is merged or user stops.

## Prerequisites

- PR exists (created in steps 12-13)
- PR number known (from step 12 output)
- VCS provider detected (from step 10)
- PR is NOT a draft (if draft, skip this handler entirely)

## State (track across iterations)

- `iteration_count`: 0
- `last_comment_id`: 0 (highest review comment ID seen)
- `fix_attempts`: {} (map check_name -> attempt_count, resets when that check passes)
- `interval`: 60s (active) or 180s (passive)

## Procedure

### Step 1 -- Poll PR status

**GitHub:**
```bash
gh pr view <PR_NUMBER> --json state,mergeable,mergeStateStatus,statusCheckRollup,isDraft
gh pr checks <PR_NUMBER> --json name,state,bucket,detailsUrl
```

**Azure DevOps:**
```bash
az repos pr show --id <PR_ID> -o json
az repos pr policy list --id <PR_ID> -o json
```

### Step 2 -- Check exit condition

- `state == MERGED` (GitHub) or `status == completed` (Azure): run `/ai-cleanup --all`, print success, EXIT.
- `state == CLOSED` (GitHub) or `status == abandoned` (Azure): print closed, EXIT.
- `isDraft == true` (GitHub) or `isDraft` field (Azure): print "Draft PR -- skipping watch loop", EXIT.

### Step 3 -- Evaluate checks

Classify each check: pass | fail | pending.

If ALL pass AND no conflicts AND no new comments:
- Set `interval = 180s` (passive)
- Print status block (Step 7)
- Wait, return to Step 1

### Step 4 -- Fix failing checks (autonomous)

For each failing check:

1. **Get failure logs:**
   - GitHub: `gh run view <RUN_ID> --log-failed`
   - Azure: `az pipelines runs show --id <RUN_ID> -o json` then `az pipelines logs --run-id <RUN_ID>`

2. **Diagnose:** Read failure output and classify:
   - Lint failure -> `ruff check . --fix` and `ruff format .`
   - Test failure -> read test output, fix the code (NOT the test assertions)
   - Security scan failure -> read finding, fix the vulnerability
   - Type check failure -> read error, fix the type issue
   - Build failure -> read error, fix the build issue

3. **Check escalation:** `fix_attempts[check_name]`
   - >= 3 -> STOP loop. Report to user: which check, what was tried, error messages from each attempt.
   - else -> increment `fix_attempts[check_name]`

4. **Track error message:** Store the primary error message. If the same error recurs after a fix, it counts as a repeat regardless of diff content.

5. **Apply fix** to code.

6. **Run commit pipeline** (steps 0-6 from `/ai-commit`): stage, format, lint, secret scan, doc gate, spec verify.
   - Reduced doc gate: CHANGELOG is NOT required for CI-fix-only commits.

7. **Commit and push:**
   ```bash
   git commit -m "fix(ci): resolve <check_name> (watch iteration N)"
   git push origin <branch>
   ```

8. **Reset** `interval = 60s`. Wait full interval before re-polling (give CI time to pick up new commit). Return to Step 1.

### Step 5 -- Resolve merge conflicts (autonomous)

If `mergeable == CONFLICTING` (GitHub) or merge status indicates conflict (Azure):

1. `git fetch origin <target_branch>`
2. `git rebase origin/<target_branch>`
3. If rebase conflicts: read conflicting files, resolve, `git add <resolved_files>`, `git rebase --continue`
4. `git push origin <branch> --force-with-lease`
5. Reset `interval = 60s`. Wait, return to Step 1.

### Step 6 -- Handle review comments

**6a. Fetch new comments:**

GitHub:
```bash
gh api repos/{owner}/{repo}/pulls/<PR_NUMBER>/comments \
  --jq '[.[] | select(.id > LAST_COMMENT_ID) | {id, path, line, body, user: .user.login}]'
gh api repos/{owner}/{repo}/pulls/<PR_NUMBER>/reviews \
  --jq '[.[] | select(.id > LAST_REVIEW_ID) | {id, state, body, user: .user.login}]'
```

Azure DevOps:
```bash
az repos pr comment list --id <PR_ID> -o json
az repos pr reviewer list --id <PR_ID> -o json
```

**6b. Update** `last_comment_id` to highest ID seen.

**6c. Classify commenter:**

GitHub (fallback chain):
1. Org member: `gh api orgs/{org}/members --jq '.[].login'` includes commenter -> AUTONOMOUS
2. Repo collaborator: `gh api repos/{owner}/{repo}/collaborators --jq '.[].login'` includes commenter -> AUTONOMOUS
3. Repo owner: commenter matches `{owner}` -> AUTONOMOUS
4. Org-internal bot: login ends with `[bot]` AND `gh api repos/{owner}/{repo}/installation` confirms app installed -> AUTONOMOUS
5. All others (external human or external bot) -> REQUIRES CONFIRMATION

Azure DevOps:
1. Project team member: `az devops team list-member --team <team> --project <project> -o json` includes commenter -> AUTONOMOUS
2. All others -> REQUIRES CONFIRMATION

Fallback: if API call fails or membership cannot be determined, treat as external (safe default).

**6d. AUTONOMOUS comments** (team + org-internal bots):
- Read comment, understand requested change
- Apply fix, run commit pipeline (steps 0-6), push
- Reply to comment thread (if supported): "Fixed in <commit_sha>"

**6e. EXTERNAL comments** (external bots + external humans):
- Present comment to user with file, line, and content
- Propose fix
- Wait for user approval before acting
- If user skips: mark comment as seen, continue loop

### Step 7 -- Print status and wait

```
--- Watch iteration N | HH:MM:SS ---
PR #<NUMBER>: <state>
Checks: X/Y passing | Z failing | W pending
Mergeable: yes | no | conflicting
Reviews: N pending, M approved, K changes_requested
Action: <current action or "waiting">
Next poll: ~<interval>s
---
```

Increment `iteration_count`. Wait `interval` seconds. Return to Step 1.

## Escalation rules

| Condition | Action |
|-----------|--------|
| Same check fails 3x | STOP. Report: check name, error messages, fixes attempted |
| Rebase conflict unresolvable | STOP. Report conflicting files |
| User interrupt | EXIT gracefully |
| PR closed/abandoned externally | EXIT with message |
| Auth or permission error | EXIT with error details |
| Draft PR detected | EXIT immediately (drafts cannot merge) |

## Behavioral negatives (Must NOT)

- Push to `main`/`master` branches (only push to the PR source branch)
- Use `--force` (only `--force-with-lease`)
- Weaken test assertions to make tests pass
- Delete or skip tests to resolve failures
- Dismiss or resolve review threads without addressing the feedback
- Skip quality gates (commit pipeline steps 0-6) during fix iterations
- Act on external review comments without user confirmation
- Continue polling a draft PR

## Anti-patterns

- Fixing same failure the same way twice (always vary approach on retry)
- Pushing code without running the commit pipeline (quality gates apply to every push)
- Acting on external review comments without user confirmation
- Polling faster than the interval (respect CI processing time)
- Silent iterations with no status output (always print the status block)
