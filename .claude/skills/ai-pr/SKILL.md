---
name: ai-pr
version: 4.0.0
description: "Use when creating pull requests: governed PR workflow with commit pipeline, pre-push gates, auto-generated summary, and auto-complete squash merge."
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

READ `.claude/skills/ai-commit/SKILL.md` and execute steps 0-6 in full. Do NOT skip any step. The documentation gate (step 5) is mandatory.

### 6.5. Doc gate verification

Safety net: verify documentation gate executed correctly.
- If staged changes include `src/` or `.ai-engineering/` files (excluding `state/`): CHANGELOG.md MUST be staged.
- For governance content changes: `.ai-engineering/README.md` SHOULD be staged and mirrored.

### 7. Pre-push checks

Execute full pre-push gate:
- `semgrep scan --config auto .`
- `pip-audit`
- `pytest tests/ -v`
- `ty check src/`

If any check fails, report and stop.

### 8. Spec operations

- If active spec: run `ai-eng spec verify` then `ai-eng spec catalog`.

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

## Integration

- Invokes `/ai-commit` pipeline (steps 0-6) as prerequisite.
- Auto-updates CHANGELOG.md and README.md via documentation gate.
- Links to issues: GitHub `Closes #N`, Azure DevOps `AB#NNN`.

## References

- `.claude/skills/ai-commit/SKILL.md` -- shared commit pipeline.
- `.claude/skills/ai-document/SKILL.md` -- changelog and documentation updates.
- `standards/framework/core.md` -- non-negotiables.
$ARGUMENTS
