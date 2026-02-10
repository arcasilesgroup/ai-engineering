# Framework Core Standards

## Update Metadata

- Rationale: define immutable governance baseline including agentic execution model.
- Expected gain: consistent enforcement across installations and multi-agent sessions.
- Potential impact: team overrides are constrained by non-negotiables.

## Purpose

Framework-owned baseline standards for every installed instance.

## Non-Negotiables

- Mandatory local enforcement through git hooks.
- Required security checks: `gitleaks`, `semgrep`, dependency vulnerability checks.
- No direct commits to `main` or `master`.
- Protected branches are blocked for direct push flows.
- Remote skills are content-only; no remote execution.

## Enforcement Rules

- All mandatory checks run locally before commit/push operations.
- Failing mandatory checks block the operation.
- Missing mandatory tools must be auto-remediated locally before retrying checks.
- Auto-remediation order: detect -> install -> configure/authenticate if applicable -> re-run check.
- Team or project layers may add stricter rules, but cannot weaken this file.

## Command Governance

- `/commit` and `/acho` push only current branch.
- `/pr` and `/acho pr` must enable PR auto-complete with squash merge and branch deletion.
- `/pr --only` warns if branch is not pushed, proposes auto-push, and continues with user-selected mode if declined.

## Agentic Execution Standards

### Session Contract

- Every agent session starts by reading the spec hierarchy: `_active.md` → `spec.md` → `tasks.md` → `decision-store.json`.
- Agents work only within their assigned task scope. Cross-scope work is prohibited.
- Each task produces exactly one atomic commit: `spec-NNN: Task X.Y — <description>`.
- Sessions close by updating `tasks.md` checkboxes and frontmatter.

### Multi-Agent Coordination

- Parallel phases use dedicated phase branches (`<integration-branch>-phase-N`).
- Serial phases work directly on the integration branch.
- Phase branches rebase from integration branch before merge.
- No cross-phase file edits within a single agent session.
- Integration agent reviews and merges phase PRs.

### Phase Gates

- A phase is complete only when: all tasks `[x]`, branch merged, quality checks pass, decisions recorded.
- Serial phases cannot start until predecessor gate passes.
- Parallel phases start as soon as their shared prerequisite gate passes.

### Decision Continuity

- All decisions persisted in `decision-store.json` with context hash.
- Agents check decision store before prompting — no repeated decisions across sessions.
- Reprompt only on: expiry, scope change, severity change, policy change, or material context hash change.

## Risk Acceptance

- Weakening attempts must produce warning + remediation suggestion.
- Auto-apply is never allowed.
- Explicit accepted risk must be recorded in machine-readable decision store and audit log.

## Update Contract

This file is framework-managed and can be updated by framework migrations.
