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
- `watch_started_at`: ISO-8601 UTC timestamp captured on first entry (anchors the passive 4h cap)
- `last_active_action_at`: ISO-8601 UTC timestamp updated on every active action (fix push in Step 4 or rebase push in Step 5); anchors the active 30 min cap

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

8. **Update** `last_active_action_at = now()` (active-phase 30-min cap reset). **Reset** `interval = 60s`. Wait full interval before re-polling (give CI time to pick up new commit). Return to Step 1.

### Step 5 -- Resolve merge conflicts (autonomous)

If `mergeable == CONFLICTING` (GitHub) or merge status indicates conflict (Azure):

1. `git fetch origin <target_branch>`
2. `git rebase origin/<target_branch>`
3. If rebase conflicts: READ `.claude/skills/ai-resolve-conflicts/SKILL.md` and delegate conflict resolution to its category-aware logic (lock files → regenerate, migrations → ask user, generated files → accept theirs, config → AI merge, code → intent-aware resolution). This ensures lock-file regeneration, migration ordering safety, and stacked-PR detection are active during automated repair.
4. `git push origin <branch> --force-with-lease`
5. Update `last_active_action_at = now()` (active-phase 30-min cap reset). Reset `interval = 60s`. Wait, return to Step 1.

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

### Step 6.5 -- Wall-clock cap (D-104-05)

Two wall-clock bounds run BEFORE the per-iteration status print, so the loop never spins past either ceiling.

**Active phase cap**: `now() - last_active_action_at > 30 min` -> STOP. Semantics: this measures **inactivity since the last active action** (the most recent fix push in Step 4 or conflict push in Step 5), NOT 30 min total since the watch started. A loop that is making progress (a fix lands every few minutes) keeps resetting `last_active_action_at` and is allowed to continue past 30 min total without truncation. The cap fires only when no active action has happened for 30 minutes (no progress / inactivity).

**Passive phase cap**: `now() - watch_started_at > 4h` -> STOP. The passive loop only waits for human review. 4h is a generous bound for a working session; longer waits should re-invoke `/ai-pr` afresh.

The per-check `fix_attempts >= 3` STOP rule (Step 4 escalation) is preserved unchanged — the wall-clock caps are **additive**, not a replacement.

**On cap (either active or passive):**

1. Emit `.ai-engineering/state/watch-residuals.json` per D-104-06 schema v1 (same envelope as `gate-findings.json`) with one `GateFinding` entry per still-failing check. The watch loop fixer agent owns this emit; the `ai-eng` CLI helper used is `ai_engineering.policy.watch_residuals.emit(failed_checks, output_path=None)`.

2. Print the actionable on-cap message:

   ```
   Watch loop hit <active|passive> wall-clock cap (<minutes> min).
   <N> checks still failing: <names>
   Run: ai-eng risk accept-all .ai-engineering/state/watch-residuals.json --justification "..."
   Or fix manually and re-invoke /ai-pr.
   ```

3. Exit code **90**. This is **distinct from spec-101 D-101-11 exits 80 and 81** (Python SDK gate / SDK prereq gate). Cross-spec contract: spec-101 reserves 80/81; spec-104 D-104-05 reserves 90 for the wall-clock cap. CI scripts depend on the integer to tell "watch timed out" from "real failure".

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
| Same check fails 3x (`fix_attempts >= 3`) | STOP. Report: check name, error messages, fixes attempted |
| Active wall-clock cap (30 min since `last_active_action_at`) | STOP. Emit `watch-residuals.json`, print on-cap message, exit code 90 |
| Passive wall-clock cap (4h since `watch_started_at`) | STOP. Emit `watch-residuals.json`, print on-cap message, exit code 90 |
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
