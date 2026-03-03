# Framework Core Standards

## Update Metadata

- Rationale: align with framework-contract.md v2; add skills and agents as first-class governance content.
- Expected gain: consistent enforcement across installations and multi-agent sessions with full content governance model.
- Potential impact: team overrides are constrained by non-negotiables; skills and agents are framework-managed.

## Purpose

Framework-owned baseline standards for every installed instance.

## Non-Negotiables

- Mandatory local enforcement through git hooks.
- Required security checks: `gitleaks`, `semgrep`, dependency vulnerability checks.
- No direct commits to `main` or `master`.
- Protected branches are blocked for direct push flows.
- Remote skills are content-only; no remote execution.
- Documentation updates for user-visible changes (`CHANGELOG.md` and `README.md` for OSS GitHub users).

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
- `/commit` and `/pr` include a documentation gate that classifies changes as user-visible vs internal-only and enforces CHANGELOG.md, README.md, and external documentation portal updates for user-visible changes targeting OSS GitHub users.

## Skills and Agents

- Skills (`skills/**`) define reusable procedures: workflows, dev practices, reviews, docs, governance, quality audits.
- Agents (`agents/**`) define personas with capabilities, behavior protocols, and output contracts.
- Both are framework-managed. Team layers cannot weaken them but may extend via team-owned skills.
- Precedence: `standards/framework/**` > `skills/**` > `agents/**`. Standards override skill behavior if conflict arises.
- Full schema details (directory layout, frontmatter fields, gating logic, capability tokens, token budgets): `standards/framework/skills-schema.md`.

### Progressive Disclosure

Three-level loading: **Metadata** (always, ~50 tok/skill) → **Body** (on-demand) → **Resources** (on-demand).

Session start loads ONLY: `_active.md` → `spec.md` → `tasks.md` → `decision-store.json`. Do NOT pre-load skills or agents.

## Context Structure

- `context/product/` — framework-contract.md (framework identity) and product-contract.md (project identity).
- `context/specs/` — spec-driven work: each spec has `spec.md` (WHAT), `plan.md` (HOW), `tasks.md` (DO), `done.md` (DONE).
- `context/specs/_active.md` — pointer to the currently active spec.
- `context/learnings.md` — retained knowledge, never overwritten.

## Agentic Execution Standards

### Session Contract

- Every agent session starts by reading the spec hierarchy: `_active.md` → `spec.md` → `tasks.md` → `decision-store.json`.
- **Spec-first fallback**: if `_active.md` points to a completed spec (has `done.md`) or no spec exists, and the requested work is non-trivial, the agent must invoke `create-spec` before proceeding.
- Agents work only within their assigned task scope. Cross-scope work is prohibited.
- Each task produces exactly one atomic commit: `spec-NNN: Task X.Y — <description>`.
- Sessions close by updating `tasks.md` checkboxes and frontmatter.
- **Post-change validation**: if any file in `.ai-engineering/` was created, deleted, renamed, or moved during the session, the agent must execute `integrity-check` before closing.

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

### Behavioral Baselines

All agents and skills must adopt these behavioral norms (defined in `standards/framework/skills-schema.md § Behavioral Patterns`):

1. **Escalation Ladder** — max 3 attempts to resolve the same issue before escalating to user. Each attempt must try a different approach. Never loop silently.
2. **Post-Change Validation** — after modifying files, run the applicable linter (code) or integrity-check (governance content) before proceeding to the next step.
3. **Confidence Signaling** — read-only audit/review agents include a confidence signal (HIGH/MEDIUM/LOW with justification) in their output contract.
4. **Headless Fallback** — interactive skills provide default options when user input is unavailable, noting assumptions made.
5. **Holistic Analysis Before Action** — before modifying any file, analyze its dependencies and downstream consumers. No isolated edits — treat every change as part of a system.
6. **Exhaustiveness Requirement** — when N issues are identified, all N must be addressed or explicitly deferred with rationale. No partial solutions, no early exits.
7. **Parallel-First Tool Execution** — when multiple independent operations are needed, execute in parallel by default. Sequential only when data dependencies require it.

### Team Standards

Team standards (`standards/team/`) extend framework defaults. Skills and agents SHOULD check for team-layer overrides when applicable.

### Decision Continuity

- All decisions persisted in `decision-store.json` with context hash.
- Agents check decision store before prompting — no repeated decisions across sessions.
- Reprompt only on: expiry, scope change, severity change, policy change, or material context hash change.
- At session start, scan `decision-store.json` for expired active decisions (`expiresAt` < current date and status is active). Surface expired decisions as warnings for user review.

## Spec-First Enforcement

Non-trivial changes require an active spec before implementation begins.

### Definition of Non-Trivial

A change is non-trivial when ANY of these apply:

- Touches more than 3 files.
- Introduces a new feature or capability.
- Refactors existing architecture or patterns.
- Changes governance content (standards, skills, agents).
- Modifies framework-contract or core standards.
- Requires multi-step implementation across sessions.

### Exempt Changes (Trivial)

- Typo or formatting fix.
- Single-line change.
- Dependency version bump without breaking changes.
- Comment or documentation minor correction.

### Enforcement Behavior

- If no active spec exists and non-trivial work is requested, guide the user to `create-spec`.
- If `_active.md` points to a completed spec, guide the user to create a new spec.
- Non-trivial changes without an active spec are governance violations.
- The `create-spec` skill always starts with a dedicated branch (feat/*, bug/*, hotfix/*).

## Content Integrity Enforcement

Governance content must remain internally consistent after every change.

### Rules

- After creating, deleting, or renaming any file in `.ai-engineering/`, the agent must execute `integrity-check`.
- Commits with broken cross-references in `.ai-engineering/` are governance violations.
- Mirror desync between canonical and template is a governance violation.
- Counter mismatches between instruction files and product-contract are governance violations.

### Validation Scope

The `integrity-check` skill validates 7 categories:

1. File existence — all referenced files exist.
2. Mirror sync — canonical and template mirrors are byte-identical.
3. Counter accuracy — instruction file counts match product-contract.
4. Cross-reference integrity — all refs are valid and bidirectional.
5. Instruction file consistency — all 6 files list identical skills/agents.
6. Manifest coherence — manifest paths match directory structure.
7. Skill frontmatter — YAML frontmatter fields are valid and consistent with directory structure.

## Finding Deduplication

Before reporting a finding, agents MUST check `state/decision-store.json` for existing decisions on the same issue. If a finding matches an active accepted risk (by scope, severity, and context hash), reference the existing decision instead of reporting a duplicate.

## Risk Acceptance

- Weakening attempts must produce warning + remediation suggestion.
- Auto-apply is never allowed.
- Explicit accepted risk must be recorded in machine-readable decision store and audit log.

## Update Contract

This file is framework-managed and can be updated by framework migrations.
