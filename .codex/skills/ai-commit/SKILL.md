---
name: ai-commit
description: "Use when committing, saving, or pushing code to git. Trigger for 'commit my changes', 'save my work', 'push this to remote', 'stage these files', 'I'm done with this task', 'ship it'. Runs governed pipeline: auto-branch from protected branches, selective staging, ruff format+lint, gitleaks secret scan, documentation gate, conventional commit message, and push. Use /ai-pr instead when a pull request is the goal."
effort: medium
argument-hint: "--force|--only|[message hint]"
tags: [git, commit, push, hooks, delivery]
requires:
  bins:
  - gitleaks
  - ruff
---



# Commit Workflow

Governed commit pipeline: stage specific files, format, lint, secret-detect, compose message, and push. NEVER uses `--no-verify` -- hooks exist to catch problems before they reach the repo. NEVER pushes to `main` or `master` -- protected branches require PR review for auditability.

## When to Use

- Committing current changes with quality enforcement.
- NOT for creating PRs -- use `/ai-pr` instead.

## Process

### 0. Auto-branch from protected

If current branch is `main` or `master`:
1. Analyze pending changes to infer type (`feat/`, `fix/`, `chore/`, `docs/`, `refactor/`).
2. Generate descriptive slug (kebab-case, max 50 chars).
3. Create branch: `git checkout -b <prefix>/<slug>`.
4. Report: "Auto-created branch: `<branch-name>`."

### 0.5. Work item context (optional)

If `.ai-engineering/specs/spec.md` has frontmatter with `refs`:
1. Read the refs (features, user_stories, tasks, issues)
2. Include work item references in the commit message body as trailers:
   ```
   Refs: AB#101, AB#102, #45
   ```
3. Only include refs for items that are `close_on_pr` in the hierarchy — do NOT include features.

### 1. Stage changes

Stage specific files -- `git add <file1> <file2>`. Use `git add -A` only when user explicitly requests or all files are relevant. Review what is staged; exclude generated files, secrets, large binaries.

### 2. Format

Run `ruff format .` to auto-fix formatting.

### 3. Lint

Run `ruff check . --fix` to auto-fix safe issues. If unfixable issues remain, report and stop.

### 4. Secret scan

Run `gitleaks protect --staged --no-banner`. If secrets found, report and **stop**. No bypass.

### 5. Documentation gate

Evaluate staged changes and classify scope:

| Scope | Trigger | Updates |
|-------|---------|---------|
| CHANGELOG + README | New features, breaking changes, CLI commands, skill additions/removals | Both files |
| CHANGELOG only | Any other functional change in `src/`, API, deps, governance | CHANGELOG.md |
| None | Typo fixes, whitespace, test-only, CI formatting | Skip silently |

- If `CHANGELOG.md` exists: add entries to `[Unreleased]`. If not: create per Keep a Changelog format.
- If README update needed and `README.md` exists: update relevant sections.
- External portal: read `manifest.yml` -> `documentation.external_portal`. If enabled, apply `update_method` (`pr` or `push`).
- Governance doc gate: if changes touch agents/skills/standards, update `.ai-engineering/README.md` and mirror to templates.

### 5.5. Content integrity check

If any file under `.ai-engineering/` was created, deleted, or renamed in the staged changes, run `ai-eng validate` to verify manifest counters, decision-store schema, and spec structure. If validation fails, report and stop.

### 6. Spec verify

If active spec exists, run `ai-eng spec verify` to auto-correct task counters.

### 7. Commit

Compose message following conventions:
- **With active spec**: `spec-NNN: Task X.Y -- <description>`
- **Without spec**: `type(scope): description` (conventional commits, imperative mood)
- If user provides `--force`, skip preview. Otherwise, preview message and confirm.

### 8. Push

`git push origin <current-branch>`. Block if on `main` or `master`.

### `/commit --only`

Execute steps 1-7. Skip push.

## Quick Reference

```
/ai-commit                   # full: stage + lint + scan + commit + push
/ai-commit --only            # commit without push
/ai-commit --force "msg"     # skip preview, use provided message hint
```

## Common Mistakes

- Using `git add -A` blindly -- always review staged files for secrets and binaries.
- Committing on `main` -- the skill auto-branches, but verify.
- Skipping documentation gate -- CHANGELOG updates are mandatory for functional changes.

## Integration

- **Pre-commit hooks** enforce the same checks. This skill runs them explicitly for visibility.
- **PR workflow** (`/ai-pr`) calls this pipeline as steps 0-6 before creating the PR.
- **Spec system** auto-corrects task counters in step 6.

## References

- `.codex/skills/ai-write/SKILL.md` -- changelog formatting.
- `.ai-engineering/manifest.yml` -- quality gates and non-negotiables.
$ARGUMENTS
