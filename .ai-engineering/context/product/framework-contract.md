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
- Pre-dispatch gate: `guard.gate` MUST run before any agent dispatch — validates scope, permissions, and governance compliance. Dispatch blocked on gate failure.
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

- Agents work on the current branch — flat main workflow for current scale (DEC-004).
- Serialize governance content modifications — no parallel edits to `.ai-engineering/`.
- Checkpoint: on task completion, update tasks.md checkbox → `ai-eng checkpoint save`.
- Gate: validate each phase gate before advancing to next phase.
- Guard-Build integration: `guard.advise` provides real-time governance feedback to `build` during implementation — advisory, non-blocking, surfaced as inline warnings.

### 2.5 Context Threading

- Context Output Contract: every dispatched agent MUST produce: `## Findings`, `## Dependencies Discovered`, `## Risks Identified`, `## Recommendations`.
- Context Aggregation: deduplicate findings, resolve conflicts (security > governance > quality > style), construct dependency graph.
- Context Handoff MUST include: phase ID, agent ID, findings summary, unresolved questions, phase dependencies.
- No Implicit Context: all shared context MUST flow through spec artifacts or explicit context summaries.
- Evolve feedback loop: the `dashboard` skill emits metrics and drift signals → `evolve` skill synthesizes improvement proposals → proposals reviewed by human → accepted proposals feed into `plan` as new specs. This loop is continuous and asynchronous.

### 2.6 Capability-Task Matching

- The orchestrator MUST match task requirements to agent `capabilities` frontmatter before assignment.
- No capability match → escalate to user. Multi-capability tasks SHOULD be split into sub-tasks for specialized agents.
- Capability tokens by agent:

| Agent | Capabilities | Scope |
|-------|-------------|-------|
| plan | discovery, risk-analysis, spec-authoring, architecture | read-write |
| guard | governance, compliance, gate-validation, policy-enforcement | read-only |
| build | code-generation, refactoring, implementation, testing | read-write |
| verify | quality-analysis, security-scanning, coverage, linting | read-only |
| guide | onboarding, documentation, explanation, context-summary | read-only |
| operate | infrastructure, tooling, installation, configuration | read-write |
| explorer | codebase-navigation, dependency-mapping, architecture-discovery, context-gathering | read-only |
| simplifier | complexity-reduction, dead-code-removal, guard-clauses, early-returns | read-write |

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

## 5. Command Contract

### 5.1 Agent Commands

- `/ai:plan` → planning pipeline (classify → discover → risk → spec → execution plan → STOP)
- `/ai:plan --plan-only` → advisory only (discover → risk → recommend, zero writes)
- `/ai:guard` → run governance gate (scope validation, policy check, compliance audit)
- `/ai:guard --advise` → advisory mode (non-blocking governance feedback)
- `/ai:verify` → quality and security pipeline (lint → type-check → test → coverage → SAST → dependency audit)
- `/ai:guide` → onboarding and context summary (explain architecture, summarize spec, generate walkthrough)
- `/ai:operate` → infrastructure and tooling (install → configure → migrate → health check)
- `/ai:explorer` → codebase navigation, dependency mapping, architecture discovery
- `/ai:simplifier` → background complexity reduction (guard clauses, early returns, dead code removal)
- `/ai:commit` → stage + commit + push
- `/ai:commit --only` → stage + commit
- `/ai:pr` → stage + commit + push + PR + auto-complete (`--auto --squash --delete-branch`)
- `/ai:pr --only` → create PR; warn if unpushed, propose auto-push

### 5.2 Pipeline Strategy

Auto-classified from `git diff --stat` + change type. User override: `/ai:plan --pipeline=<type>`.

| Pipeline | When | Steps |
|----------|------|-------|
| full | Features, refactors, >3 files | guard.gate → discover → architecture → risk → spec → dispatch |
| standard | Enhancements, 3-5 files | guard.gate → discover → risk → spec → dispatch |
| hotfix | Bug fixes, <3 files | guard.gate → discover → risk → dispatch |
| trivial | Typos, single-line | guard.gate → dispatch |

### 5.3 Progressive Disclosure

Three-level loading: **Metadata** (always, ~50 tok/skill) → **Body** (on-demand) → **Resources** (on-demand).

Session start loads ONLY: `_active.md` → `spec.md` → `tasks.md` → `decision-store.json` → `session-checkpoint.json`. Do NOT pre-load skills or agents.

| Level | Budget |
|-------|--------|
| Session start | ~500 tokens |
| Single skill | ~2,050 tokens |
| Agent + 2 skills | ~3,200 tokens |
| Platform audit (10 dim) | ~14,000 tokens |

## 6. Distribution Model

### 6.1 Template Replication

- Canonical content authored in `.ai-engineering/`; mirrored in `src/ai_engineering/templates/.ai-engineering/`.
- Non-state files MUST be identical between canonical and template mirror (except spec execution logs).
- `state/*` files MUST be generated at install/update runtime from typed defaults.

### 6.2 Release Model

- SemVer with migration scripts. Channels: `stable` and `canary`.
- Telemetry MUST remain strict opt-in.
- Every managed update MUST include: rationale, expected gain, potential impact.
- Periodic simplification is mandatory, preserving functionality and governance.
