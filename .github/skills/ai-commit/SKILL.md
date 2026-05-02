---
name: ai-commit
description: "Use when committing, saving, or pushing code to git. Trigger for 'commit my changes', 'save my work', 'push this to remote', 'stage these files', 'I'm done with this task', 'ship it'. Runs governed pipeline: auto-branch from protected branches, selective staging, ruff format+lint, gitleaks secret scan, documentation gate, conventional commit message, and push. Use /ai-pr instead when a pull request is the goal."
effort: medium
argument-hint: "--force|--only|[message hint]"
mode: agent
tags: [git, commit, push, hooks, delivery]
requires:
  bins:
  - gitleaks
  - ruff
mirror_family: copilot-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-commit/SKILL.md
edit_policy: generated-do-not-edit
---


# Commit Workflow

Governed commit pipeline: stage specific files, format, lint, secret-detect, compose message, and push. Honors CLAUDE.md Don't rules (binding).

## When to Use

- Committing with quality enforcement. Use `/ai-pr` instead when the goal is a pull request.

## Process

### 0. Auto-branch from protected

If current branch is `main`/`master`: infer type (`feat/`, `fix/`, `chore/`, `docs/`, `refactor/`), generate descriptive slug (kebab-case, max 50 chars), `git checkout -b <prefix>/<slug>`, report new branch.

### 1. Work item context (optional)

If `.ai-engineering/specs/spec.md` frontmatter has `refs`: include work item refs as commit body trailers (`Refs: AB#101, AB#102, #45`). Only include `close_on_pr` items — never features.

### 2. Instinct consolidation

If `.ai-engineering/instincts/instincts.yml` exists, run `/ai-instinct --review` to consolidate session observations before committing.

### 3. Stage changes

`git add <file1> <file2>` selectively. Use `git add -A` only when explicitly requested. Exclude generated files, secrets, large binaries.

### 4. Run gate orchestrator

```
ai-eng gate run --cache-aware --json --mode=local
```

The orchestrator runs the 2-wave collector (Wave 1 fixers serial -> Wave 2 checkers parallel) with cache-aware lookup, emitting `.ai-engineering/state/gate-findings.json` (schema v1) covering every check. After Wave 1 fixers rewrite files, the orchestrator re-stages the safe `S_pre & M_post` intersection (spec-105 D-105-09); pass `--no-auto-stage` to disable, or set `gates.pre_commit.auto_stage: false` in the manifest.

### 5. Handle gate result

- **Exit 0** -- all checks PASS or auto-fixed. Continue to Commit.
- **Exit non-zero** -- parse `gate-findings.json`, report failing checks per `rule_id` + `severity`, **STOP**. Fix root cause, re-stage, re-run `/ai-commit`. Override only when remediation is tracked elsewhere and the publish window forces it: `ai-eng risk accept-all .ai-engineering/state/gate-findings.json --justification "<reason>" --spec <spec-id> --follow-up "<plan>"` writes one DEC entry per finding with severity-default TTL (see `.ai-engineering/contexts/risk-acceptance-flow.md`).

### 6. Confirm commit readiness

The documentation gate inside the orchestrator is mandatory.

See `.ai-engineering/contexts/gate-policy.md` for the local fast-slice + CI authoritative split.

### 7. Commit

Compose message:

- **With active spec**: `feat(spec-NNN): Task X.Y -- <desc>`, `fix(spec-NNN): <desc>`, `chore(spec-NNN): <desc>`.
- **Without spec**: `type(scope): description` (conventional commits, imperative mood). Valid types: `feat`, `fix`, `perf`, `refactor`, `style`, `docs`, `test`, `build`, `ci`, `chore`, `revert`.
- `--force` skips preview; otherwise preview and confirm.

### 8. Push

`git push origin <current-branch>`. Block if on `main`/`master`.

### `/commit --only`
Execute the full pipeline through Commit. Skip Push.

## Quick Reference

`/ai-commit` runs the full pipeline; `/ai-commit --only` stops before push; `/ai-commit --force "msg"` skips preview and uses the provided hint.

## Integration

- **Pre-commit hooks** enforce the same checks; this skill runs them explicitly for visibility.
- **PR workflow** (`/ai-pr`) calls steps 0-6 before creating the PR.
- **Spec system** auto-corrects task counters via `ai-eng spec verify --fix` (Wave 1 fixer in step 2).
- Quality gates and non-negotiables sourced from `.ai-engineering/manifest.yml`; changelog formatting from `.github/skills/ai-write/SKILL.md`.
  $ARGUMENTS
