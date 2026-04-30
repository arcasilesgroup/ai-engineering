# CLI reference

Complete command reference for the `ai-eng` CLI.

## Core commands

```bash
ai-eng install [TARGET]            # Bootstrap governance framework
ai-eng update [TARGET]             # Preview framework file updates (dry-run)
ai-eng update [TARGET] --apply     # Apply framework file updates
ai-eng update [TARGET] --diff      # Show unified diffs for updated files
ai-eng update [TARGET] --json      # Output report as JSON
ai-eng doctor [TARGET]             # Diagnose framework health
ai-eng doctor --fix                # Attempt repairs for fixable findings
ai-eng doctor --fix --phase hooks  # Attempt hook-specific repairs only
ai-eng doctor --fix --phase tools  # Attempt tool-specific repairs only
ai-eng doctor --json               # Output report as JSON
ai-eng validate [TARGET]           # Validate content integrity (all 6 categories)
ai-eng validate --category <cat>   # Run a specific category only
ai-eng validate --json             # Output report as JSON
ai-eng version                     # Show installed version and lifecycle status
ai-eng guide [TARGET]              # Display branch policy setup instructions
ai-eng release <VERSION>           # Create a governed release (validate, bump, PR, tag)
ai-eng release --draft             # Create pre-release
ai-eng release --dry-run           # Validate only, no changes
ai-eng release --wait              # Wait for pipeline after tagging
ai-eng release --skip-bump         # Skip version bump step
```

Release rule: treat `ai-eng release <VERSION>` as the only supported write path for framework releases.
It is responsible for updating `pyproject.toml`, `src/ai_engineering/version/registry.json`,
the source-repo `framework_version` manifests, and promoting `CHANGELOG.md` out of `Unreleased`.
Do not edit those version surfaces by hand during a normal release.

Use `--dry-run` first, then run the real release command. Reserve `--skip-bump` for recovery or
resume flows when the version bump commit already exists.

## Stack and IDE management

```bash
ai-eng stack add python            # Add a technology stack
ai-eng stack remove python         # Remove a technology stack
ai-eng stack list                  # List active stacks

ai-eng ide add vscode              # Add IDE integration
ai-eng ide remove vscode           # Remove IDE integration
ai-eng ide list                    # List active IDEs
```

## Quality gates

Git hooks invoke these automatically, but you can run them manually:

```bash
ai-eng gate pre-commit             # Format, lint, gitleaks
ai-eng gate commit-msg .git/COMMIT_EDITMSG  # Commit message validation
ai-eng gate pre-push               # Semgrep, pip-audit, tests, type-check
ai-eng gate risk-check             # Check risk acceptance status
ai-eng gate risk-check --strict    # Fail on expiring risks too
ai-eng gate all                    # Run all gates (pre-commit + pre-push + risk-check)
ai-eng gate all --strict           # Also fail on expiring risk acceptances
```

## Skills management

```bash
ai-eng skill status                # Check skill health and requirements
ai-eng skill status --all          # Include all eligible skills in output
```

## Maintenance

```bash
ai-eng maintenance report                         # Generate health report
ai-eng maintenance report --staleness-days 60      # Custom staleness threshold
ai-eng maintenance pr                              # Generate report + create PR
ai-eng maintenance branch-cleanup                  # Clean merged local branches
ai-eng maintenance branch-cleanup --dry-run        # Preview without deleting
ai-eng maintenance branch-cleanup --base develop   # Use non-default base branch
ai-eng maintenance branch-cleanup --force          # Force-delete unmerged branches
ai-eng maintenance risk-status                     # Show risk acceptance status
ai-eng maintenance repo-status                    # Repository branch and PR dashboard
ai-eng maintenance repo-status --no-prs           # Exclude open PR listing
ai-eng maintenance spec-reset                     # Archive completed specs, clear _active.md
ai-eng maintenance spec-reset --dry-run           # Report findings without modifying
ai-eng maintenance all                            # Combined maintenance dashboard
```

## AI provider management

```bash
ai-eng provider add <provider>     # Add an AI provider (claude_code, github_copilot, gemini, codex)
ai-eng provider remove <provider>  # Remove an AI provider (keeps last)
ai-eng provider list               # List active AI providers
```

## VCS provider

```bash
ai-eng vcs status                  # Show current VCS provider
ai-eng vcs set-primary <provider>  # Switch primary VCS provider (github, azure_devops)
```

## Platform setup

```bash
ai-eng setup platforms             # Detect and configure all platforms
ai-eng setup github                # Verify GitHub CLI authentication and scopes
ai-eng setup sonar                 # Configure SonarCloud / SonarQube credentials
ai-eng setup azure-devops          # Configure Azure DevOps PAT credentials
ai-eng setup sonarlint             # Configure SonarLint Connected Mode in IDEs
```
