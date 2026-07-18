# CLI reference

Complete command reference for the `ai-eng` CLI. Every visible top-level
command and group is listed below with a one-line description derived from
the live Typer help text. Hidden framework-internal verbs (`release`, `dev`,
`internal`, and removed-command tombstones) are intentionally omitted.

## Core commands

```bash
ai-eng install [TARGET]            # Install the ai-engineering governance framework
ai-eng update [TARGET]             # Update framework-managed governance files (dry-run by default)
ai-eng update [TARGET] --apply     # Apply framework file updates
ai-eng update [TARGET] --diff      # Show unified diffs for updated files
ai-eng update [TARGET] --json      # Output report as JSON
ai-eng doctor [TARGET]             # Diagnose and optionally fix framework health
ai-eng doctor --fix                # Attempt repairs for fixable findings
ai-eng doctor --fix --phase hooks  # Attempt hook-specific repairs only
ai-eng doctor --fix --phase tools  # Attempt tool-specific repairs only
ai-eng doctor --json               # Output report as JSON
ai-eng check [TARGET]              # Run content-integrity health checks across governance categories
ai-eng check --category <cat>      # Run a specific category only
ai-eng check --json                # Output report as JSON
ai-eng verify                      # Run every verification specialist and emit a scored report
ai-eng status                      # Show a summary of the installed framework configuration
```

## Version

```bash
ai-eng version                     # Show version and lifecycle status
ai-eng version upgrade             # Upgrade ai-engineering using the detected install method
```

## Commit & PR (off-chain)

Standalone WIP checkpoints outside the canonical spec chain (D-131-07).

```bash
ai-eng commit                      # Standalone off-chain commit
ai-eng pr                          # Standalone off-chain PR open
```

## Configuration (stack / Surface / VCS)

Mutating list/status flows live under `ai-eng config <resource> <verb>`.
Spec-133 D-133-16 collapsed the former `ide` and `provider` axes into
`surface`.

```bash
ai-eng config                      # Inspect the current stacks/Surfaces/VCS configuration
ai-eng config reconfigure          # Re-run the interactive configuration wizard
ai-eng config stack list           # List active technology stacks
ai-eng config surface list         # List available Surfaces, checked against the enabled set
ai-eng config vcs status           # Show current VCS provider configuration and availability
```

## Quality gates

Git hooks invoke these automatically, but you can run them manually:

```bash
ai-eng gate pre-commit             # Format, lint, gitleaks
ai-eng gate commit-msg .git/COMMIT_EDITMSG  # Commit message format validation
ai-eng gate pre-push               # Pre-push gate checks (semgrep, pip-audit, tests, type-check)
ai-eng gate risk-check             # Check risk acceptance status (expired + expiring-soon)
ai-eng gate risk-check --strict    # Fail on expiring risks too
ai-eng gate all                    # Run all gates (pre-commit + pre-push + risk-check)
ai-eng gate all --strict           # Also fail on expiring risk acceptances
ai-eng gate run                    # Run the spec-104 single-pass gate orchestrator
ai-eng gate cache                  # Inspect or clear the gate cache (D-104-10)
```

## Skills management

```bash
ai-eng skill status                # Check which local skills meet their runtime requirements
ai-eng skill status --all          # Include all eligible skills in output
```

## Host capacity

```bash
ai-eng host probe                  # Print the HostProbe snapshot plus the recommended wave cap
```

## Maintenance

```bash
ai-eng maintenance report                      # Generate a framework maintenance report
ai-eng maintenance report --staleness-days 60  # Custom staleness threshold
ai-eng maintenance pr                          # Generate a report and create a PR
ai-eng maintenance risk-status                 # Show risk acceptance status (active/expiring/expired)
ai-eng maintenance repo-status                 # Show repository branch and PR status dashboard
ai-eng maintenance repo-status --no-prs        # Exclude open PR listing
ai-eng maintenance reset-events                # Archive framework-events.ndjson and seed a fresh chain
ai-eng maintenance all                         # Run all maintenance checks and produce a combined report
```

## Cleanup

Git branch, runtime, and spec cleanup (spec-133 D-133-03).

```bash
ai-eng cleanup branches            # Clean up local git branches across 7 canonical modes
ai-eng cleanup runtime             # Rotate `.ai-engineering/runtime/` per retention policy
ai-eng cleanup specs               # Reconcile merged specs, then consolidate shipped ledger rows
ai-eng cleanup all                 # Run branches --all + runtime + specs in sequence
```

## Platform setup

```bash
ai-eng setup platforms             # Detect and configure all platforms found in the repository
ai-eng setup github                # Verify GitHub CLI authentication and scopes
ai-eng setup sonar                 # Configure SonarCloud / SonarQube credentials
ai-eng setup azure-devops          # Configure Azure DevOps PAT credentials
ai-eng setup sonarlint             # Configure SonarLint Connected Mode in all detected IDEs
```

## Decision store

```bash
ai-eng decision list               # List all decisions from the canonical decision-store.json
ai-eng decision expire-check       # Flag decisions whose expires_at is past or within 7 days
ai-eng decision record             # Record a new decision into decision-store.json
ai-eng decision backfill           # Backfill the decisions table from markdown sources
```

## Ownership

```bash
ai-eng ownership import            # Import CODEOWNERS into state.db.ownership_map
```

## Audit and observability

The audit chain is the append-only ledger at
`.ai-engineering/state/framework-events.ndjson` (files-only per spec-148).
All commands are read-only.

```bash
ai-eng audit verify                # Verify the hash-chained audit trail (events and/or decisions)
ai-eng audit verify --decisions    # Decision ledger only
ai-eng audit tokens --by skill     # Aggregate token usage by skill
ai-eng audit tokens --by agent     # Aggregate token usage by agent
ai-eng audit tokens --by session   # Aggregate token usage by session
ai-eng audit replay --session <id> # Walk a session (or trace) as a span tree
```

## Risk acceptance

Manage risk-acceptance decisions in the canonical decision store (spec-105).

```bash
ai-eng risk accept                 # Accept a single gate finding as a tracked risk acceptance
ai-eng risk accept-all             # Bulk-accept all findings in a gate-findings.json document
ai-eng risk renew                  # Renew a risk acceptance (max 2 renewals)
ai-eng risk resolve                # Mark a risk acceptance as remediated (fix landed)
ai-eng risk revoke                 # Revoke a risk acceptance (mistaken / no longer valid)
ai-eng risk list                   # List risk-acceptance decisions filtered by status/severity/expiry
ai-eng risk show                   # Show full detail for a single risk acceptance decision
```

## Spec lifecycle

```bash
ai-eng spec start                  # Activate a work plane and ensure spec/plan buffer files exist
ai-eng spec verify                 # Verify spec task counters and status consistency
ai-eng spec list                   # Display current spec title and progress
ai-eng spec show                   # Print the active spec handoff surface (paths + progress)
```

## Plan helpers

```bash
ai-eng plan dag-build              # Build the sub-spec dependency DAG and emit a JSON wave plan
```

## Issue board sync

```bash
ai-eng issue sync                  # Sync specs to external issues (GitHub Issues / Azure DevOps Boards)
```

## Releases (framework-internal)

`ai-eng release` is a framework-internal command hidden from the help tree
(spec-183 D-183-03): it publishes the `ai-engineering` package itself, not the
consumer-facing surface. The release-authority rules follow, for maintainers.

Release rule: ai-eng release <VERSION> is the sole authority for framework releases.
It updates `pyproject.toml`, `src/ai_engineering/version/registry.json`, the source-repo
`framework_version` manifests, and promotes `CHANGELOG.md` out of `Unreleased`. Do not
edit those version surfaces by hand during a normal release.

Release path: use `--dry-run` first, then the real command creates the governed
`release/v<VERSION>` branch and release commit. After merge, the tag-triggered Release workflow
publishes the release: it validates on TestPyPI before PyPI Trusted Publishing, then attaches
the provenance packet (checksums, SBOM, attestations, release notes) to the GitHub Release.
`workflow_dispatch` is a protected recovery dispatch only, not the normal release path.
legacy automated release tooling and manual CI commit-back are hard-removed, so CI never invents a release commit.
Reserve `--skip-bump` for recovery or resume flows when the version bump commit exists.
