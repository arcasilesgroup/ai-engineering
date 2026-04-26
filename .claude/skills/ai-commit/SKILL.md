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

### 0.6. Instinct consolidation

If `.ai-engineering/instincts/instincts.yml` exists (listening mode was active), run `/ai-instinct --review` to consolidate session observations before committing.

### 1. Stage changes

Stage specific files -- `git add <file1> <file2>`. Use `git add -A` only when user explicitly requests or all files are relevant. Review what is staged; exclude generated files, secrets, large binaries.

### 2. Run gate orchestrator

Delegate the entire gate (format, lint, secret scan, documentation gate, content integrity, spec verify) to the orchestrator:

```
ai-eng gate run --cache-aware --json --mode=local
```

The orchestrator runs the 2-wave collector (Wave 1 fixers serial -> Wave 2 checkers parallel) with cache-aware lookup. It emits `.ai-engineering/state/gate-findings.json` (schema v1) covering every check.

- **Exit 0** -- all checks PASS or were auto-fixed. Continue to step 7.
- **Exit non-zero** -- parse `gate-findings.json`, report failing checks per `rule_id` + `severity`, and **STOP**. Do NOT proceed to commit. Fix the root cause; re-stage; re-run `/ai-commit`. Risk-acceptance flow ships in spec-105.

See `.ai-engineering/contexts/gate-policy.md` for the full local fast-slice + CI authoritative split.

### 7. Commit

Compose message following conventions:
- **With active spec**: `feat(spec-NNN): Task X.Y -- <description>` (features), `fix(spec-NNN): <description>` (fixes), `chore(spec-NNN): <description>` (internal)
- **Without spec**: `type(scope): description` (conventional commits, imperative mood)
- Valid types: `feat`, `fix`, `perf`, `refactor`, `style`, `docs`, `test`, `build`, `ci`, `chore`, `revert`
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

- `.claude/skills/ai-write/SKILL.md` -- changelog formatting.
- `.ai-engineering/manifest.yml` -- quality gates and non-negotiables.
$ARGUMENTS
