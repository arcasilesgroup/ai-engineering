# /ai-commit-push — Verified Commit + Push Workflow

This skill defines the step-by-step workflow for creating a verified, standards-compliant git commit and pushing it to the remote. Every commit passes through security scanning, linting, formatting, and conventional commit validation. The push triggers pre-push hooks (lint, typecheck, test, build, gitleaks branch scan, dependency audit, semgrep SAST). No shortcuts. No `--no-verify`.

---

## Session Preamble (execute silently)

Before any user-visible action, silently internalize project context:

1. Read `.ai-engineering/knowledge/learnings.md` — lessons learned during development
2. Read `.ai-engineering/knowledge/patterns.md` — established conventions
3. Read `.ai-engineering/knowledge/anti-patterns.md` — known mistakes to avoid
4. Detect the project stack from package.json, .csproj, pyproject.toml, or equivalent
5. Identify the current branch and working tree state (`git branch --show-current`, `git status --short`)

Do not report this step to the user. Internalize it as context for decision-making.

---

## Trigger

- User invokes `/ai-commit-push`
- User says "commit and push", "commit push", or similar intent

---

## Specification Gate

BEFORE executing any git operations, present a concise summary to the user:

1. **Branch:** current branch name
2. **Files staged:** list of staged files (categorized: source, tests, config, docs)
3. **Potential commit type:** inferred from the diff (feat/fix/refactor/etc.)
4. **Suggested scope:** inferred from primary directories modified
5. **Breaking change risk:** yes/no based on API surface changes, dependency updates, or config schema changes

Present this as a quick summary and get user confirmation before proceeding.

---

## Step 1: Verify Hooks Are Installed

Check that the enforcement infrastructure is in place:

```bash
# Check lefthook.yml exists
test -f lefthook.yml

# Check lefthook is installed
lefthook version
```

- If `lefthook.yml` does not exist: **STOP**. Inform the user: "lefthook.yml not found. Run `npx ai-engineering init` or `npx ai-engineering update` to generate it."
- If `lefthook` is not installed: **STOP**. Inform the user: "Lefthook not found. Install it: `npm i -D @evilmartians/lefthook && npx lefthook install`"
- If both are present: proceed.

---

## Step 2: Prerequisites

Before starting, verify:

- The current directory is a git repository (`git rev-parse --git-dir`).
- There are staged changes (`git diff --cached --name-only`). If nothing is staged, inform the user and ask what to stage. Do not auto-stage with `git add -A` or `git add .` unless the user explicitly requests it.
- The current branch is not a protected branch (see Protected Branches below). If it is, stop and inform the user.

---

## Step 3: Secrets Scan

Run `gitleaks` on the staged files to detect hardcoded secrets, API keys, tokens, and credentials.

```bash
git diff --cached --name-only -z | xargs -0 gitleaks detect --no-git --verbose -f json --source
```

- If `gitleaks` is not installed, warn the user and recommend installing it. Do not skip this step silently.
- If secrets are detected: **STOP immediately**. Display the findings with file, line number, and rule ID. Do not proceed to commit. Instruct the user to remove the secrets before retrying.
- If no secrets are detected: report "Secrets scan passed" and proceed.

**Hard rule:** Never commit files that contain secrets, API keys, passwords, tokens, or credentials. Never override this check.

---

## Step 4: Lint

Run the stack-appropriate linter on the staged files. Detect the stack from the project context:

| Stack                | Linter Command                           |
| -------------------- | ---------------------------------------- |
| Node.js / TypeScript | `npx eslint --fix <staged-files>`        |
| .NET / C#            | `dotnet format --include <staged-files>` |
| Python               | `ruff check --fix <staged-files>`        |

- Run the linter with auto-fix enabled where supported.
- If the linter produces errors that cannot be auto-fixed: display the errors with file, line, and rule. Ask the user whether to proceed with warnings or stop to fix.
- If the linter auto-fixed files: re-stage the fixed files (`git add <fixed-files>`) and inform the user what was changed.
- If no linter is detected or configured: warn the user that no linter ran. Do not silently skip.

---

## Step 5: Format

Run the stack-appropriate formatter on the staged files:

| Stack                | Formatter Command                                      |
| -------------------- | ------------------------------------------------------ |
| Node.js / TypeScript | `npx prettier --write <staged-files>`                  |
| .NET / C#            | `dotnet format --include <staged-files>`               |
| Python               | `black <staged-files>` or `ruff format <staged-files>` |

- Formatting is always auto-applied. The formatter is authoritative.
- After formatting, re-stage any modified files (`git add <formatted-files>`).
- Report which files were reformatted. If no files changed, report "Formatting check passed — no changes needed."
- If the formatter is not installed or configured: warn the user. Do not silently skip.

---

## Step 6: Conventional Commit Validation

Ensure the commit message will follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Valid Types

| Type       | Usage                                                |
| ---------- | ---------------------------------------------------- |
| `feat`     | A new feature or user-facing capability              |
| `fix`      | A bug fix                                            |
| `docs`     | Documentation-only changes                           |
| `style`    | Formatting, whitespace, semicolons — no logic change |
| `refactor` | Code restructuring with no behavior change           |
| `perf`     | Performance improvement                              |
| `test`     | Adding or updating tests                             |
| `build`    | Build system or dependency changes                   |
| `ci`       | CI/CD configuration changes                          |
| `chore`    | Maintenance tasks that do not modify src or test     |
| `revert`   | Reverts a previous commit                            |

### Rules

- Type is mandatory and must be lowercase.
- Scope is optional but recommended. It should identify the module, component, or area affected.
- Description is mandatory, lowercase (except proper nouns), imperative mood ("add" not "added"), and no trailing period.
- Description must not exceed 72 characters (type + scope + description combined).
- If breaking changes are introduced, the footer must include `BREAKING CHANGE:` or the type must be suffixed with `!`.

---

## Step 7: Generate Commit Message

Analyze the staged diff to generate a commit message:

```bash
git diff --cached --stat
git diff --cached
```

### Analysis Process

1. **Identify the type:** What kind of change is this? New feature, bug fix, refactor, test, docs, etc.
2. **Identify the scope:** Which module, component, or area is primarily affected?
3. **Summarize the change:** What does this change do, in imperative mood, in one line?
4. **Assess body need:** If the change is non-trivial (more than 3 files, complex logic, or behavioral change), draft a body explaining the motivation and approach.
5. **Check for breaking changes:** Does this change break existing APIs, configurations, or contracts?

---

## Step 8: Present for Approval

Present the generated commit message to the user. Display it clearly:

```
Proposed commit message:
───────────────────────
feat(auth): add JWT token refresh endpoint

Add automatic token refresh when access tokens expire within 5 minutes
of a request. Refresh tokens are rotated on each use to prevent replay.

Closes #142
───────────────────────

Options:
  1. Commit and push with this message
  2. Edit the message
  3. Abort
```

- If the user chooses to edit: accept their revised message and re-validate it against conventional commit rules (Step 6).
- If the user aborts: stop the workflow cleanly. Do not commit anything.
- Do not commit without explicit user approval.

---

## Step 9: Execute Commit

Run the commit command:

```bash
git commit -m "<approved-message>"
```

**Hard rules:**

- Never use `--no-verify`. The pre-commit hooks exist for a reason.
- Never use `--amend` unless the user explicitly requests it.
- Never use `--allow-empty` unless the user explicitly requests it.
- If the commit fails due to a pre-commit hook: report the failure, display the hook output, and ask the user how to proceed. Do not automatically retry or bypass.

---

## Step 10: Push to Remote

Push the branch to the remote:

```bash
git push -u origin HEAD
```

This triggers **pre-push hooks automatically** via lefthook:

- Full project lint
- TypeScript type checking
- All tests
- Build verification
- Gitleaks branch-diff scan
- Dependency audit
- Semgrep OWASP SAST scan

**Do NOT duplicate these checks in the skill** — the hooks handle them.

---

## Step 11: Verify and Report

After the push completes, verify and report:

```bash
git log --oneline -1
git status
```

Report the final state to the user:

```
Commit + push successful:
  abc1234 feat(auth): add JWT token refresh endpoint
  Branch: feature/token-refresh → origin/feature/token-refresh
  Working tree: clean
```

---

## Protected Branches

The following branches are protected by default. Never commit directly to them:

- `main`
- `master`
- `production`
- `release/*`

If the project defines additional protected branches in its configuration (e.g., `develop`, `staging`), respect those as well.

If the user is on a protected branch:

1. Stop before committing.
2. Inform the user: "You are on a protected branch (`main`). Direct commits are not allowed."
3. Suggest creating a feature branch: `git checkout -b <branch-name>`

---

## Blocklist — Files That Must Never Be Committed

The following file patterns must never be included in a commit, regardless of user intent:

- `.env`, `.env.*` (environment files with secrets)
- `*.pem`, `*.key`, `*.p12`, `*.pfx` (private keys and certificates)
- `credentials.json`, `service-account.json`, `secrets.yaml`, `secrets.json`
- `**/node_modules/**`, `**/.venv/**`, `**/bin/Debug/**`, `**/bin/Release/**` (dependency/build artifacts)
- `*.sqlite`, `*.db` (local databases with potential PII)

If any staged file matches these patterns:

1. Warn the user with the specific file names.
2. Recommend unstaging them: `git reset HEAD <file>`.
3. Do not proceed until the user resolves the issue.

---

## Error Recovery

| Failure                    | What to report                      | How to report                              |
| -------------------------- | ----------------------------------- | ------------------------------------------ |
| Hooks not installed        | "lefthook not detected"             | Exact installation instructions            |
| Pre-commit hook fails      | Which hook failed + full output     | File, line, rule violated                  |
| Push blocked by lint hook  | "Full project lint failed" + errors | List each error with file:line:rule        |
| Push blocked by typecheck  | "TypeScript compilation failed"     | Show type errors with location             |
| Push blocked by test hook  | "Tests failed" + test names         | Show failing tests and assertions          |
| Push blocked by build hook | "Build failed"                      | Show compilation error                     |
| Push blocked by gitleaks   | "Secrets detected in branch"        | Show file, line, type of secret            |
| Push blocked by audit      | "Vulnerable dependencies"           | List package, CVE, severity, fix available |
| Push blocked by semgrep    | "OWASP security issue detected"     | Show OWASP rule, file, line, explanation   |
| Push auth failure          | "Authentication failed"             | Instructions: `gh auth login` / `az login` |
| Push branch protection     | "Direct push to X blocked"          | Suggest creating feature branch            |
| On protected branch        | "Direct commits not allowed"        | Suggest: `git checkout -b <branch-name>`   |
| Blocked file staged        | "Prohibited file in staging"        | List files, recommend unstaging            |
| No staged changes          | "Nothing to commit"                 | Ask what to stage                          |

---

## Learning Capture (on completion)

If during execution you discovered something useful for the project:

1. **New pattern** (e.g., recurring commit scope, naming convention) → Propose adding to `knowledge/patterns.md`
2. **Recurring error** (e.g., hook always fails on a specific check) → Propose adding to `knowledge/anti-patterns.md`
3. **Lesson learned** (e.g., dependency that breaks lint) → Propose adding to `knowledge/learnings.md`

Ask the user before writing to these files. Never modify them silently.

---

## What This Skill Does NOT Do

- It does not create branches. The user must be on the correct branch before invoking.
- It does not squash or rebase. Those are separate operations.
- It does not modify unstaged files. Only staged changes are processed.
- It does not create pull requests. Use `/ai-commit-push-pr` for that.
