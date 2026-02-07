# /ai-commit — Verified Commit Workflow

This skill defines the step-by-step workflow for creating a verified, standards-compliant git commit. Every commit passes through security scanning, linting, formatting, and conventional commit validation before it reaches the repository. No shortcuts. No `--no-verify`.

---

## Trigger

- User invokes `/ai-commit`
- User says "commit", "commit this", "commit my changes", or similar intent

---

## Prerequisites

Before starting, verify the following:

- The current directory is a git repository (`git rev-parse --git-dir`).
- There are staged changes (`git diff --cached --name-only`). If nothing is staged, inform the user and ask what to stage. Do not auto-stage with `git add -A` or `git add .` unless the user explicitly requests it.
- The current branch is not a protected branch (see Protected Branches below). If it is, stop and inform the user.

---

## Step 1: Secrets Scan

Run `gitleaks` on the staged files to detect hardcoded secrets, API keys, tokens, and credentials.

```bash
git diff --cached --name-only -z | xargs -0 gitleaks detect --no-git --verbose -f json --source
```

- If `gitleaks` is not installed, warn the user and recommend installing it. Do not skip this step silently.
- If secrets are detected: **stop immediately**. Display the findings with file, line number, and rule ID. Do not proceed to commit. Instruct the user to remove the secrets before retrying.
- If no secrets are detected: report "Secrets scan passed" and proceed.

**Hard rule:** Never commit files that contain secrets, API keys, passwords, tokens, or credentials. Never override this check.

---

## Step 2: Lint

Run the stack-appropriate linter on the staged files. Detect the stack from the project context:

| Stack | Linter Command |
|---|---|
| Node.js / TypeScript | `npx eslint --fix <staged-files>` |
| .NET / C# | `dotnet format --include <staged-files>` |
| Python | `ruff check --fix <staged-files>` |
| Go | `golangci-lint run <staged-files>` |
| Rust | `cargo clippy --fix --allow-dirty` |

- Run the linter with auto-fix enabled where supported.
- If the linter produces errors that cannot be auto-fixed: display the errors with file, line, and rule. Ask the user whether to proceed with warnings or stop to fix.
- If the linter auto-fixed files: re-stage the fixed files (`git add <fixed-files>`) and inform the user what was changed.
- If no linter is detected or configured: warn the user that no linter ran. Do not silently skip.

---

## Step 3: Format

Run the stack-appropriate formatter on the staged files:

| Stack | Formatter Command |
|---|---|
| Node.js / TypeScript | `npx prettier --write <staged-files>` |
| .NET / C# | `dotnet format --include <staged-files>` |
| Python | `black <staged-files>` or `ruff format <staged-files>` |
| Go | `gofmt -w <staged-files>` |
| Rust | `rustfmt <staged-files>` |

- Formatting is always auto-applied. There is no "proceed with warnings" for formatting — the formatter is authoritative.
- After formatting, re-stage any modified files (`git add <formatted-files>`).
- Report which files were reformatted. If no files changed, report "Formatting check passed — no changes needed."
- If the formatter is not installed or configured: warn the user. Do not silently skip.

---

## Step 4: Conventional Commit Validation

Ensure the commit message will follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Valid Types

| Type | Usage |
|---|---|
| `feat` | A new feature or user-facing capability |
| `fix` | A bug fix |
| `docs` | Documentation-only changes |
| `style` | Formatting, whitespace, semicolons — no logic change |
| `refactor` | Code restructuring with no behavior change |
| `perf` | Performance improvement |
| `test` | Adding or updating tests |
| `build` | Build system or dependency changes |
| `ci` | CI/CD configuration changes |
| `chore` | Maintenance tasks that do not modify src or test |
| `revert` | Reverts a previous commit |

### Rules

- Type is mandatory and must be lowercase.
- Scope is optional but recommended. It should identify the module, component, or area affected.
- Description is mandatory, lowercase (except proper nouns), imperative mood ("add" not "added"), and no trailing period.
- Description must not exceed 72 characters (type + scope + description combined).
- If breaking changes are introduced, the footer must include `BREAKING CHANGE:` or the type must be suffixed with `!` (e.g., `feat!: remove legacy API`).

---

## Step 5: Generate Commit Message

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

### Output Format

```
<type>(<scope>): <description>

<body — if needed, wrapped at 72 characters>

<footer — if breaking changes or issue references>
```

---

## Step 6: Present for Approval

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
  1. Commit with this message
  2. Edit the message
  3. Abort
```

- If the user chooses to edit: accept their revised message and re-validate it against conventional commit rules (Step 4). If the revised message does not comply, inform the user and ask them to fix it.
- If the user aborts: stop the workflow cleanly. Do not commit anything.
- Do not commit without explicit user approval.

---

## Step 7: Execute Commit

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

## Step 8: Verify Commit

After the commit command completes, verify it succeeded:

```bash
git log --oneline -1
git status
```

- Confirm the commit hash and message match expectations.
- Confirm the working tree status is clean (or has only expected unstaged changes).
- Report the final state to the user:

```
Commit successful:
  abc1234 feat(auth): add JWT token refresh endpoint
  Branch: feature/token-refresh
  Working tree: clean
```

---

## Protected Branches

The following branches are protected by default. Never commit directly to them:

- `main`
- `master`
- `production`
- `release/*`
- `hotfix/*` (only if branch protection is configured)

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

| Failure | Action |
|---|---|
| Secrets detected | Stop. Display findings. Do not commit. |
| Lint errors (unfixable) | Display errors. Ask user to fix or proceed with warnings. |
| Formatter not installed | Warn. Ask user if they want to proceed without formatting. |
| Commit hook failure | Display hook output. Ask user how to proceed. Never use `--no-verify`. |
| On protected branch | Stop. Suggest creating a feature branch. |
| Blocked file staged | Warn. Recommend unstaging. Do not proceed. |
| No staged changes | Inform user. Ask what to stage. Do not auto-stage. |

---

## What This Skill Does NOT Do

- It does not push to a remote. Use `/ai-pr` or manual `git push` for that.
- It does not create branches. The user must be on the correct branch before invoking.
- It does not squash or rebase. Those are separate operations.
- It does not modify unstaged files. Only staged changes are processed.
