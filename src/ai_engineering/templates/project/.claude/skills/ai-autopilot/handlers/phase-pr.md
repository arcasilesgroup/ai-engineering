# Handler: PR + Deliver

## Purpose

Execute the final delivery pipeline: commit gates, push, create PR, optionally watch until merge, and clean up autopilot state. This handler reads ai-pr and ai-commit SKILL.md files and follows their instructions. It does NOT reimplement the PR pipeline.

## Prerequisites

- All sub-specs in `specs/autopilot/manifest.md` marked complete
- Final verification (Step 3 of parent skill) passed
- All sub-spec commits exist on the current branch
- Current branch is NOT main/master

## Procedure

### Step 1 -- Pre-Push Gates

Read `.claude/skills/ai-pr/SKILL.md` steps 7-7.5. Execute:

1. `ruff check .` and `ruff format --check .`
2. `gitleaks protect --staged --no-banner`
3. `pytest tests/unit/ -v`
4. `sync_command_mirrors.py --check` (if script exists)

If any check fails: fix and retry once. If still failing: STOP and report which gate failed with full output.

### Step 2 -- Push

1. Confirm current branch is not `main`/`master`. If it is: STOP.
2. `git push -u origin <current-branch>`
3. If push fails (e.g., rejected): report and STOP.

### Step 3 -- Create PR

Read `.claude/skills/ai-pr/SKILL.md` steps 10-12.

1. **Detect VCS provider**: check `manifest.yml` -> `providers.vcs.primary`, fallback to `git remote get-url origin`.
2. **Check for existing PR**: `gh pr list --head <branch> --json number --state open`.
3. **Create PR** with structured body:

```markdown
## Summary
- [What the autopilot implemented -- derived from parent spec title and scope]
- [Key architectural decisions or patterns applied]

## Sub-Specs Completed
| # | Title | Status |
|---|-------|--------|
| sub-001 | [title] | VERIFIED |
| sub-002 | [title] | VERIFIED |
| ... | ... | ... |

## Test Plan
- [ ] [Verification results from final verify pass]
- [ ] [Regression check against main]
- [ ] [Lint, type check, secret scan all clean]

## Telemetry
- Sub-specs: N completed, 0 failed
- Duration: Xm (from autopilot start to PR creation)
- Verify passes: N/N
```

If existing PR found: extend body per ai-pr protocol (append, never overwrite).

### Step 4 -- Auto-Complete

- **GitHub**: `gh pr merge --auto --squash --delete-branch`
- **Azure DevOps**: `az repos pr update --id <id> --auto-complete true --squash true --delete-source-branch true`

### Step 5 -- Watch (unless --no-watch)

If `--no-watch` flag was passed: skip to Step 6.

Read `.claude/skills/ai-pr/SKILL.md` step 14 and execute the full watch-and-fix loop:

- Poll every 60s (active) or 180s (passive)
- Autonomously fix CI failures via commit pipeline (ai-commit steps 0-6)
- Autonomously resolve merge conflicts via rebase with `--force-with-lease`
- Escalate after 3 failed fix attempts on the same check
- Exit on merge, close, or escalation

### Step 6 -- Cleanup

After merge (or immediately if `--no-watch`):

1. Delete `specs/autopilot/` directory entirely: `rm -rf .ai-engineering/specs/autopilot/`
2. Clear `specs/spec.md`:
   ```
   # No active spec

   Run /ai-brainstorm to start a new spec.
   ```
3. Clear `specs/plan.md`:
   ```
   # No active plan

   Run /ai-plan after brainstorm approval.
   ```
4. Stage and commit cleanup: `chore: clear autopilot state after spec-NNN delivery`
5. Run `/ai-cleanup --all` -- switch to default branch, pull, delete merged branch.

### Step 7 -- Final Report

```
Autopilot Complete!

Spec: spec-NNN -- [title]
Sub-specs: N completed, 0 failed
Duration: Xm
PR: #NNN (merged|pending)

Sub-specs delivered:
1. sub-001: [title] -- VERIFIED
2. sub-002: [title] -- VERIFIED
...
```

## Output

- PR created (and merged if watch enabled)
- `specs/autopilot/` cleaned up
- `specs/spec.md` and `specs/plan.md` reset to placeholders
- Repository on default branch, up to date

## Failure Modes

| Condition | Action |
|-----------|--------|
| Pre-push gate fails 2x | STOP. Report gate name and output |
| Push rejected | STOP. Report error |
| PR creation fails | STOP. Report VCS provider error |
| Watch loop escalates (3x same check) | STOP per watch.md protocol |
| Cleanup fails | Warn but do not block -- PR is already delivered |
