# ai-engineering Framework Contract

Binding rules for all agents and tools operating under the ai-engineering governance framework. Every directive is enforceable and verifiable.

## 1. Non-Negotiable Directives

### 1.1 Core Mandates

- Deliver solutions that are simple, efficient, practical, robust, and secure.
- Enforce quality and security by default — never defer to optional steps.
- Apply strong governance to prevent AI drift and hallucination.
- Follow the mandatory lifecycle: Discovery → Architecture → Planning → Implementation → Review → Verification → Testing → Iteration.
- Support native workflows for GitHub Copilot, Claude Code, Codex, and Gemini.
- Support governed parallel execution across multiple agents.
- Support cross-OS operation: Windows, macOS, Linux.
- Support VCS provider detection: GitHub and Azure DevOps.

### 1.2 Single Source of Truth

- `.ai-engineering/` is the canonical source. All agents MUST read governance content from this directory.
- No duplication SHALL exist across standards, context, skills, and agent configuration.
- All managed artifacts MUST be concise, purpose-driven, and high-signal.

### 1.3 Local Enforcement

- Git hooks MUST be enabled and non-bypassable. `--no-verify` MUST NOT be used.
- Mandatory checks: `gitleaks` (secrets), `semgrep` (SAST), dependency vulnerability checks, formatter/linter/security per stack.
- Failures MUST be fixed locally. No skip guidance SHALL be provided.
- Missing tools: detect → install → configure/authenticate → re-run. If remediation fails, block and provide manual steps.

### 1.4 Install and Bootstrap

- Existing repos: detect stack, IDE, platform, then adapt.
- Empty repos: guided initialization wizard.
- The installer MUST ensure first-commit readiness. `add/remove stack` and `add/remove IDE` MUST perform safe cleanup.

### 1.5 Framework vs Instance

- **Framework**: OSS core product maintained by framework maintainers.
- **Installed instance**: per-repo `.ai-engineering/` directory.
- The updater MUST NOT modify team-managed or project-managed content. The installer MUST NOT overwrite existing customizations.

## 2. Agentic Model

### 2.1 Session Contract

- Agents MUST operate as session-scoped workers with explicit scope, dependencies, and deliverables.
- Each session MUST read context from governance content — no implicit knowledge assumed.
- Session recovery MUST be deterministic: `_active.md` → `spec.md` → `tasks.md` → `decision-store.json` → `session-checkpoint.json`.
- Spec-first check: if no active spec and work is non-trivial, invoke `create-spec` before proceeding.
- Commit: 1 phase = 1 commit with `spec-NNN: Pase X.Y — <description>`.
- Content integrity: if any `.ai-engineering/` file was created, deleted, renamed, or moved, execute `integrity-check`.
- Report summary: tasks done, files changed, decisions made, blockers found.

### 2.2 Parallel Execution and Branching

- Parallelism boundaries MUST be defined by phase dependencies in `plan.md`.
- A Session Map in `plan.md` MUST pre-assign sessions to agent slots with explicit scope and size.
- Integration branch: spec-scoped (e.g., `rewrite/v2`). Phase branches: `<integration>-phase-N`.
- Serial phases MUST work directly on the integration branch.
- Phase branches MUST rebase from integration branch before merge; integration agent reviews.
- Phase branch lifespan: created at phase start, deleted after merge.

### 2.3 Phase Gates

Every phase MUST pass before dependent phases start:

1. All tasks marked `[x]` in `tasks.md`.
2. Phase branch merged to integration branch (if parallel).
3. Quality checks pass for affected files.
4. No unresolved decisions — all recorded in `decision-store.json`.

### 2.4 Agent Coordination

- Claim: each agent works on its own phase branch — no shared-file contention.
- Isolate: no cross-phase file edits within a session.
- Checkpoint: on completion, agent opens PR from phase branch → integration branch.
- Merge + Gate: integration agent reviews, merges, runs gate checks before unblocking next phase.

### 2.5 Context Threading

- Context Output Contract: every dispatched agent MUST produce: `## Findings`, `## Dependencies Discovered`, `## Risks Identified`, `## Recommendations`.
- Context Aggregation: deduplicate findings, resolve conflicts (security > governance > quality > style), construct dependency graph.
- Context Handoff MUST include: phase ID, agent ID, findings summary, unresolved questions, phase dependencies.
- No Implicit Context: all shared context MUST flow through spec artifacts or explicit context summaries.

### 2.6 Capability-Task Matching

- The orchestrator MUST match task requirements to agent `capabilities` frontmatter before assignment.
- Security tasks → security capability tokens. Code modification → `scope: read-write`. Read-only analysis → prefer `scope: read-only`.
- No capability match → escalate to user. Multi-capability tasks SHOULD be split into sub-tasks for specialized agents.

### 2.7 Task Tracking and Decisions

- Specs define WHAT (`spec.md`), HOW (`plan.md`), DO (`tasks.md`), DONE (`done.md`).
- `tasks.md` frontmatter MUST track: `total`, `completed`, `last_session`, `next_session`.
- Parallel phases annotated with `║`; session/agent/branch in phase headers. Size estimates (S/M/L) required.
- Decisions MUST be persisted in `decision-store.json` with SHA-256 context hash.
- Reprompt only when: decision expired, scope changed, severity changed, policy changed, or context hash changed.

## 3. Ownership Model

### 3.1 Boundaries

- **framework-managed** (updatable): `standards/framework/**`, `skills/**`, `agents/**`, `runbooks/**`, `context/product/framework-contract.md`.
- **external framework-managed** (updatable, outside `.ai-engineering/`): `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`, `.github/copilot/**`, `.github/instructions/**`, `.github/prompts/**`, `.github/agents/**`, `.github/ISSUE_TEMPLATE/**`, `.github/pull_request_template.md`, `.agents/**`, `.claude/settings.json`, `.claude/commands/**`.
- **team-managed** (never overwritten): `standards/team/**`.
- **project-managed** (never overwritten): `context/**` (except `context/product/framework-contract.md`).
- **system-managed**: `state/install-manifest.json`, `state/ownership-map.json`, `state/decision-store.json`, `state/audit-log.ndjson`, `state/session-checkpoint.json`.

### 3.2 Update Rules

- The installer MUST create missing folders and files safely.
- The updater MUST modify only framework-managed and system-managed paths. Team and project content MUST always be preserved.
- Schema and version migrations MUST be explicit, idempotent, and auditable.

### 3.3 Standards Layering

1. `standards/framework/core.md`
2. `standards/framework/stacks/<stack>.md`
3. `standards/team/core.md`
4. `standards/team/stacks/<stack>.md`

Higher-numbered layers override lower-numbered layers for the same directive.

## 4. Security and Quality

### 4.1 Quality Model

- Quality gates MUST be defined in framework standards and enforced locally via hooks and stack tooling.
- Quality rules MUST be content-driven and versioned in `.ai-engineering/`.
- Optional Sonar integration: `ai-eng setup sonar` / `ai-eng setup sonarlint`. Sonar gate MUST silent-skip when unconfigured.

### 4.2 Decision and Audit

When weakening a directive is requested: warn user → generate remediation patch → never auto-apply → require explicit risk acceptance → persist in `decision-store.json` → append to `audit-log.ndjson`. Agents MUST check the decision store before prompting — no repeated decisions unless expired, scope/severity/policy changed, or context hash changed.

## 5. Distribution Model

### 5.1 Template Replication

- Canonical content authored in `.ai-engineering/`; mirrored in `src/ai_engineering/templates/.ai-engineering/`.
- Non-state files MUST be identical between canonical and template mirror (except spec execution logs).
- `state/*` files MUST be generated at install/update runtime from typed defaults.

### 5.2 Release Model

- SemVer with migration scripts. Channels: `stable` and `canary`.
- Telemetry MUST remain strict opt-in.
- Every managed update MUST include: rationale, expected gain, potential impact.
- Periodic simplification is mandatory, preserving functionality and governance.
