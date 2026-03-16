---
name: commit
description: "Execute governed commit workflow: stage, lint, secret-detect, commit, and push current branch."
argument-hint: "--only|[msg]"
metadata:
  version: 1.0.0
  tags: [git, commit, push, hooks]
  ai-engineering:
    requires:
      bins: [gitleaks, ruff]
    scope: read-write
    token_estimate: 800
---

# Commit Workflow

## Purpose

Execute the `/commit` governed workflow: stage all changes, run mandatory pre-commit checks, commit with a well-formed message, and push to the current branch. The `--only` variant stages and commits without pushing.

## Trigger

- Command: `/commit` or `/commit --only`
- Context: user requests committing current changes with governance enforcement.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"commit"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## When NOT to Use

- **Creating pull requests** — use `/pr` instead. Commit pushes to current branch; PR creates a pull request.
- **Governance content changes without active spec** — create a spec first with `spec`.

## Preconditions (MUST verify before proceeding)

- **Required binaries**: `gitleaks`, `ruff` — all must be available on PATH.
- Abort with remediation guidance if missing. Run `ai-eng doctor --fix-tools` to auto-install.

## Procedure

### `/commit` (default: stage + commit + push)

0. **Auto-branch from protected** — if current branch is `main` or `master`:
   a. Analyze pending changes (`git diff --stat` + file paths) to infer change type.
   b. Select prefix: `feat/` | `fix/` | `chore/` | `docs/` | `refactor/` based on change type.
   c. Generate a descriptive slug (kebab-case, max 50 chars) from the changes.
   d. Create branch: `git checkout -b <prefix>/<slug>`.
   e. Report: "Auto-created branch: `<branch-name>`" and continue.
   If NOT on a protected branch, skip this step.

1. **Stage changes** — `git add -A` (or selective staging if user specifies files).
2. **Run formatter** — `ruff format .` to auto-fix formatting.
3. **Run linter** — `ruff check . --fix` to auto-fix safe lint issues. If unfixable issues remain, report and stop.
4. **Run secret detection** — `gitleaks protect --staged --no-banner`. If secrets found, report and stop.
5. **Documentation gate** — evaluate and update documentation for OSS GitHub users.
   a. Analyze staged changes and classify documentation scope:
   - **CHANGELOG + README**: new features, breaking changes, new CLI commands, skill/agent additions or removals, config schema changes, architecture changes visible to users.
   - **CHANGELOG only**: any other functional change — src/ modifications, API changes, dependency bumps with behavioral impact, governance surface changes, workflow behavior changes.
   - **No updates needed**: changes with zero functional impact — typo fixes in comments, whitespace-only changes, test-only additions that don't change public behavior, CI config formatting. Log: "Documentation gate evaluated — no functional changes detected."
     b. Update **CHANGELOG.md** (when scope requires it):
   - If `CHANGELOG.md` exists: add entries to `[Unreleased]` section per `skills/changelog/SKILL.md` format. Stage the updated file.
   - If `CHANGELOG.md` does NOT exist: create it following Keep a Changelog format. Stage the new file.
     c. Update **README.md** (when scope includes README):
   - If `README.md` exists AND changes include new features, breaking changes, new CLI commands, or skill catalog changes: update relevant sections. Stage the updated file.
   - If `README.md` does NOT exist AND changes are non-trivial: create it targeting OSS GitHub audience. Stage the new file.
     d. **External documentation portal**:
   - Read `manifest.yml → documentation.external_portal`.
   - If `enabled: false` or `source` is null: skip silently.
   - If `enabled: true` and `source` is set:
     - **Local path** (source exists as local directory): update relevant doc files in-place, stage changes in that repo.
     - **Git URL** (source starts with `https://` or `git@`): clone to temp directory if not already local. Then apply `update_method`:
       - `"pr"`: create branch, commit changes, push, create PR with auto-complete (use VCS-appropriate CLI), report PR URL.
       - `"push"`: commit changes, push directly to main branch.
     - Report what was updated and where.
   e. **Governance documentation gate** — if staged changes include files in `.ai-engineering/agents/`, `.ai-engineering/skills/`, `.ai-engineering/standards/`, or `.ai-engineering/runbooks/`:
   - Update `.ai-engineering/README.md` to reflect current governance structure (agents, skills, workflow).
   - Mirror the updated file to `src/ai_engineering/templates/.ai-engineering/README.md`.
   - Stage both files.
   - If no governance content changes detected, skip silently.
6. **Spec verify** — if an active spec exists, run `ai-eng spec verify` to auto-correct task counters before committing.
7. **Commit** — `git commit -m "<message>"` with a well-formed commit message following project conventions.
   - If active spec exists, use format: `spec-NNN: Task X.Y — <description>`.
   - Otherwise, use conventional commit format: `type(scope): description`.
8. **Push** — `git push origin <current-branch>`.
   - If current branch is `main` or `master`, **block** and report protected branch violation.

### `/commit --only` (stage + commit, no push)

Follow steps 1–6 above. Skip step 7.

## Examples

### Example 1: Standard feature commit

User says: "Run /commit with message spec-031: Task 2.1 — add examples to skills."
Actions:

1. Stage changes and run formatter, linter, and gitleaks on staged content.
2. Evaluate documentation gate, commit with provided message, and push current branch.
   Result: Commit is created and pushed, or workflow stops with a clear remediation if any gate fails.

## Output Contract

- Terminal output showing each step's result (pass/fail).
- On success: commit hash and branch name displayed.
- On failure: specific check that failed with remediation guidance.

## Governance Notes

- Protected branch push is always blocked. No exceptions.
- Secret detection (`gitleaks`) failure is a hard stop. No bypass.
- Formatter and linter run with auto-fix before checking; only unfixable issues block.
- If `ruff` or `gitleaks` is not installed, attempt auto-remediation: `uv tool install ruff` / `brew install gitleaks` / `winget install gitleaks` as appropriate.
- All quality gate failures must be fixed locally before retrying.

## References

- `standards/framework/core.md` — non-negotiables and enforcement rules.
- `standards/framework/stacks/python.md` — Python-specific checks.
- `standards/framework/quality/core.md` — gate structure (pre-commit gate).
- `skills/changelog/SKILL.md` — changelog entry formatting (used by documentation gate).
- `skills/document/SKILL.md` — README and documentation update procedure for OSS GitHub users (used by documentation gate).
- `skills/pr/SKILL.md` — PR workflow.
- `agents/operate.md` — agent that validates commit workflow execution.
