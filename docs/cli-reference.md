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
ai-eng doctor --fix-hooks          # Reinstall git hooks
ai-eng doctor --fix-tools          # Install missing tools
ai-eng doctor --json               # Output report as JSON
ai-eng validate [TARGET]           # Validate content integrity (all 6 categories)
ai-eng validate --category <cat>   # Run a specific category only
ai-eng validate --json             # Output report as JSON
ai-eng version                     # Show installed version and lifecycle status
```

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
```

## Skills management

```bash
ai-eng skill list                  # List remote skill sources
ai-eng skill sync                  # Sync from remote sources
ai-eng skill sync --offline        # Use cached content only
ai-eng skill add <url>             # Add a remote skill source
ai-eng skill remove <url>          # Remove a remote skill source
ai-eng skill status                # Check skill health and requirements
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
ai-eng maintenance pipeline-compliance             # Scan pipelines for risk gates
ai-eng maintenance pipeline-compliance --suggest   # Show injection snippets for fixes
```

## VCS provider

```bash
ai-eng vcs status                  # Show current VCS provider
ai-eng vcs set-primary <provider>  # Switch primary VCS provider (github, azure_devops)
```

## Review

```bash
ai-eng review pr                   # Run AI-assisted PR review
```

## CI/CD

```bash
ai-eng cicd regenerate             # Generate or update CI/CD workflows
```
