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
ai-eng check [TARGET]              # Validate content integrity (all 6 categories) — renamed from `validate` (spec-132 D-132-02)
ai-eng check --category <cat>      # Run a specific category only
ai-eng check --json                # Output report as JSON
ai-eng version                     # Show installed version and lifecycle status
ai-eng release <VERSION>           # Create a governed release (validate, bump, PR, tag)
ai-eng release --draft             # Create pre-release
ai-eng release --dry-run           # Validate only, no changes
ai-eng release --wait              # Wait for pipeline after tagging
ai-eng release --skip-bump         # Skip version bump step
```

Release rule: ai-eng release <VERSION> is the sole authority for framework releases.
It is responsible for updating `pyproject.toml`, `src/ai_engineering/version/registry.json`,
the source-repo `framework_version` manifests, and promoting `CHANGELOG.md` out of `Unreleased`.
Do not edit those version surfaces by hand during a normal release.

Release path: use `--dry-run` first, then run the real release command to create the governed
`release/v<VERSION>` branch and release commit. After merge, the tag-triggered Release workflow
publishes the release: it validates on TestPyPI before PyPI Trusted Publishing, then attaches the
provenance packet (checksums, SBOM, attestations, and release notes) to the GitHub Release.
`workflow_dispatch` is a protected recovery dispatch only; it is not the normal release path.
legacy automated release tooling and manual CI commit-back are hard-removed, so CI never invents a release commit.
Reserve `--skip-bump` for recovery or resume flows when the version bump commit already exists.

## Configuration (stack / IDE / provider / VCS)

Mutating subcommands collapse into `ai-eng config` per spec-132
D-132-04. The standalone `stack`, `ide`, `provider`, and `vcs` verbs
are removed; their list / status flows live under
`ai-eng config <resource> <verb>`.

```bash
ai-eng config                      # Interactive reconfigure (re-runs the install wizard)
ai-eng config stack list           # List active stacks (was `ai-eng stack list`)
ai-eng config ide list             # List active IDEs (was `ai-eng ide list`)
ai-eng config provider list        # List active AI providers (was `ai-eng provider list`)
ai-eng config vcs status           # Show current VCS provider (was `ai-eng vcs status`)
```

## Audit and observability

The audit chain is the append-only ledger at
`.ai-engineering/state/framework-events.ndjson` plus the
SQLite-projection at `.ai-engineering/state/audit-index.sqlite`
(spec-120 D-120-04). All commands are read-only.

```bash
ai-eng audit verify                           # Verify hash chain (events + decisions)
ai-eng audit verify --decisions               # Decision ledger only
ai-eng audit index                            # Build / refresh the SQLite projection
ai-eng audit index --force                    # Rebuild from scratch
ai-eng audit query "SELECT ..."               # Run a read-only SQL query
ai-eng audit tokens --by skill                # Token usage by skill
ai-eng audit tokens --by agent                # Token usage by agent
ai-eng audit tokens --by session              # Token usage by session
ai-eng audit replay --session <id>            # Walk a session as a span tree
ai-eng audit otel-export --trace <id>         # Export trace as OTLP/JSON
```

> Spec-122-b (sub-002) also planned `audit retention`, `rotate`,
> `compress`, `verify-chain`, `health`, `vacuum` subcommands as part of
> the unified `state.db` rollout. Those landed as infrastructure
> primitives in sub-002; the user-facing CLI verbs are queued for a
> follow-up release once the rotation policy is finalised.

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

## Issue board sync

```bash
ai-eng issue sync                  # Sync GitHub Projects board with the local ledger
                                   # (renamed from `ai-eng work-item sync` per D-132-03)
```

## Source-repo developer helpers

```bash
ai-eng dev sync                    # Re-sync IDE mirrors (replaces `ai-eng sync`, D-132-10)
                                   # Hidden in consumer projects; visible only in the
                                   # source repo when `[tool.aiengineering.source_repo]`
                                   # is set in pyproject.toml.
```

## Platform setup

```bash
ai-eng setup platforms             # Detect and configure all platforms
ai-eng setup github                # Verify GitHub CLI authentication and scopes
ai-eng setup sonar                 # Configure SonarCloud / SonarQube credentials
ai-eng setup azure-devops          # Configure Azure DevOps PAT credentials
ai-eng setup sonarlint             # Configure SonarLint Connected Mode in IDEs
```
