# Handler: Watch and Fix

## Purpose

Post-PR monitoring loop with autonomous repair. Fixes CI failures, resolves merge conflicts, and handles review comments. Team members and org-internal bots are autonomous; external commenters require user confirmation. Exits when PR is merged or user stops.

## Prerequisites

- PR exists, PR number known, VCS provider detected, PR is NOT a draft.

## State (track across iterations)

- `iteration_count`: 0; `last_comment_id`: 0; `fix_attempts`: {} (map check_name -> count, resets on pass).
- `interval`: 60s (active) or 180s (passive).
- `watch_started_at`: ISO-8601 UTC at first entry (anchors the passive 4h cap).
- `last_active_action_at`: ISO-8601 UTC updated on every fix push (Step 4) or rebase push (Step 5); anchors the active 30 min cap.

## Procedure

### Step 1 -- Poll PR status

GitHub: `gh pr view <PR_NUMBER> --json state,mergeable,mergeStateStatus,statusCheckRollup,isDraft` then `gh pr checks <PR_NUMBER> --json name,state,bucket,detailsUrl`.

Azure: `az repos pr show --id <PR_ID> -o json` then `az repos pr policy list --id <PR_ID> -o json`.

### Step 2 -- Check exit condition

- `state == MERGED` (GitHub) / `status == completed` (Azure): run `/ai-cleanup --all`, EXIT.
- `state == CLOSED` / `status == abandoned`: EXIT.
- `isDraft == true`: print "Draft PR -- skipping watch loop", EXIT.

### Step 3 -- Evaluate checks

Classify pass | fail | pending. If ALL pass AND no conflicts AND no new comments: set `interval = 180s`, print status (Step 7), wait, return to Step 1.

### Step 4 -- Fix failing checks (autonomous)

For each failing check:

1. **Get failure logs:** GitHub `gh run view <RUN_ID> --log-failed`; Azure `az pipelines runs show --id <RUN_ID> -o json` then `az pipelines logs --run-id <RUN_ID>`.
2. **Diagnose** and classify: lint -> `ruff check . --fix && ruff format .`; test -> fix code (NOT test assertions); security/type/build -> read error and fix root cause.
3. **Check escalation:** `fix_attempts[check_name] >= 3` -> STOP loop, report check name + attempts + errors. Else increment.
4. **Track error message:** if same error recurs after a fix, count as repeat regardless of diff content.
5. **Apply fix; run commit pipeline** (`/ai-commit` steps 0-6). Reduced doc gate: CHANGELOG NOT required for CI-fix-only commits.
6. **Commit and push:** `git commit -m "fix(ci): resolve <check_name> (watch iteration N)"` then `git push origin <branch>`.
7. **Update** `last_active_action_at = now()`. **Reset** `interval = 60s`. Wait full interval before re-polling. Return to Step 1.

### Step 5 -- Resolve merge conflicts (autonomous)

If `mergeable == CONFLICTING` (GitHub) or merge status indicates conflict (Azure):

1. `git fetch origin <target_branch>` then `git rebase origin/<target_branch>`.
2. If rebase conflicts: READ `.gemini/skills/ai-resolve-conflicts/SKILL.md` and delegate to its category-aware logic (lock files regenerate; migrations ask user; generated files accept theirs; config AI-merge; code intent-aware). Keeps lock-file regeneration, migration ordering, and stacked-PR detection active.
3. `git push origin <branch> --force-with-lease`.
4. Update `last_active_action_at = now()`. Reset `interval = 60s`. Wait, return to Step 1.

### Step 6 -- Handle review comments

**6a. Fetch new comments.**

GitHub:
```bash
gh api repos/{owner}/{repo}/pulls/<PR_NUMBER>/comments \
  --jq '[.[] | select(.id > LAST_COMMENT_ID) | {id, path, line, body, user: .user.login}]'
gh api repos/{owner}/{repo}/pulls/<PR_NUMBER>/reviews \
  --jq '[.[] | select(.id > LAST_REVIEW_ID) | {id, state, body, user: .user.login}]'
```

Azure: `az repos pr comment list --id <PR_ID> -o json` and `az repos pr reviewer list --id <PR_ID> -o json`.

**6b. Update** `last_comment_id` to highest ID seen.

**6c. Classify commenter** (fallback chain; if API fails or membership unknown, treat as external):

| Commenter | GitHub source | Azure source | Mode |
|-----------|---------------|--------------|------|
| Org member | `gh api orgs/{org}/members` | — | AUTONOMOUS |
| Repo collaborator | `gh api repos/{owner}/{repo}/collaborators` | — | AUTONOMOUS |
| Repo owner | login matches `{owner}` | — | AUTONOMOUS |
| Org-internal bot | login ends with `[bot]` AND app installed (`installation` API) | — | AUTONOMOUS |
| Project team member | — | `az devops team list-member --team <team> --project <project>` | AUTONOMOUS |
| Everyone else | external | external | REQUIRES CONFIRMATION |

**6d. AUTONOMOUS:** read comment, apply fix, run commit pipeline (steps 0-6), push, reply "Fixed in <commit_sha>".

**6e. EXTERNAL:** present comment with file/line/content, propose fix, wait for approval. If user skips: mark seen, continue.

### Step 6.5 -- Wall-clock cap (D-104-05)

Caps run BEFORE the per-iteration status print so the loop never spins past either ceiling.

- **Active cap**: `now() - last_active_action_at > 30 min` -> STOP. Measures **inactivity since the last active action** (Step 4 fix push or Step 5 conflict push), NOT 30 min total. A loop making progress keeps resetting `last_active_action_at` and runs past 30 min.
- **Passive cap**: `now() - watch_started_at > 4h` -> STOP. The passive loop only waits for human review; longer waits should re-invoke `/ai-pr`.

The per-check `fix_attempts >= 3` STOP rule (Step 4 escalation) is preserved unchanged — wall-clock caps are **additive**.

**On cap (active or passive):**

1. Emit `.ai-engineering/state/watch-residuals.json` per D-104-06 schema v1 (same envelope as `gate-findings.json`) with one `GateFinding` per still-failing check. Helper: `ai_engineering.policy.watch_residuals.emit(failed_checks, output_path=None)`.
2. Print:
   ```
   Watch loop hit <active|passive> wall-clock cap (<minutes> min).
   <N> checks still failing: <names>
   Run: ai-eng risk accept-all .ai-engineering/state/watch-residuals.json --justification "..." --spec <spec-id> --follow-up "..."
   Or fix manually and re-invoke /ai-pr.
   ```
3. Exit code **90** (distinct from spec-101 D-101-11 exits 80/81 for Python SDK gate / SDK prereq gate). CI scripts use the integer to tell "watch timed out" from "real failure".

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
| Same check fails 3x (`fix_attempts >= 3`) | STOP. Report check + error messages + attempts |
| Active wall-clock cap (30 min since `last_active_action_at`) | STOP. Emit `watch-residuals.json`, on-cap message, exit 90 |
| Passive wall-clock cap (4h since `watch_started_at`) | STOP. Emit `watch-residuals.json`, on-cap message, exit 90 |
| Rebase conflict unresolvable | STOP. Report conflicting files |
| User interrupt | EXIT gracefully |
| PR closed/abandoned externally | EXIT with message |
| Auth or permission error | EXIT with error details |
| Draft PR detected | EXIT immediately (drafts cannot merge) |

## Behavioral negatives (Must NOT)

Canonical anti-pattern list for `/ai-pr` and the watch loop. `/ai-pr` references this section.

- Push to `main`/`master`; use `--force` (only `--force-with-lease` permitted).
- Weaken test assertions, delete or skip tests, dismiss review threads without addressing feedback.
- Skip quality gates (commit pipeline steps 0-6) on any fix push -- gates apply to every push.
- Act on external review comments without user confirmation (only team/org-internal-bots are autonomous).
- Continue polling a draft PR; poll faster than `interval`; emit silent iterations without a status block.
- Fix the same failure the same way twice -- always vary approach on retry.
