# ai-engineering Framework Contract (v2)

## Update Metadata

- Rationale: absorb vision.md personas and success metrics; absorb roadmap.md phases and release model. Consolidate into single authoritative contract.
- Expected gain: single source of truth for product identity, eliminating 4 redundant files.
- Potential impact: vision.md, roadmap.md, rebuild-rollout-charter.md, framework-adoption-map.md become obsolete and are deleted.

## Purpose

ai-engineering is an open-source governance framework for AI-assisted software delivery.
It is designed to be simple, efficient, practical, robust, secure, and highly usable across teams and environments.

This contract defines non-negotiable product behavior, architecture boundaries, and rollout rules.

## Mission

Provide a context-first, governance-first framework that ensures consistent quality, security, and delivery discipline when working with AI coding assistants.

The framework must:

- guide AI behavior through explicit standards and context,
- enforce local quality/security gates,
- preserve project/team ownership boundaries,
- stay easy for humans to understand and maintain.

## Product Model (Content-First)

ai-engineering is primarily a content framework:

- Markdown, YAML, JSON, and Bash define behavior and governance.
- `.ai-engineering/` is the canonical source of truth.

Python is intentionally minimal and operational.

### Minimal Python Runtime Scope

Python is used only for:

1. `install` - copy templates, set up hooks, run readiness checks.
2. `update` - ownership-safe updates and migrations.
3. `doctor` - verify installed/configured/authenticated/ready state.
4. `add/remove stack|ide` - safe template operations and cleanup.

No heavy policy engine should be embedded in Python if behavior can be declared in governance content.

## Product Principles (Non-Negotiable)

### 1) Core Philosophy

- Simple, efficient, practical, robust, secure.
- Quality and security by default.
- Strong governance to prevent AI drift/hallucination.
- Lifecycle enforced:
  Discovery -> Architecture -> Planning -> Implementation -> Review -> Verification -> Testing -> Iteration.

### 2) Interoperability and Execution Targets

- Native workflows for Claude, Codex, and GitHub Copilot.
- Governed parallel execution support.
- Cross-OS from day one: Windows, macOS, Linux.
- VCS detection: GitHub first, Azure DevOps next phase.

### 3) Single Source of Truth

- No duplication across standards/context/skills/agent config.
- `.ai-engineering/` is canonical.
- Keep artifacts concise and high-signal.

### 4) Tech Stack Baseline

- Primary language: Python (minimal runtime only).
- Supporting formats: Markdown, YAML, JSON, Bash.
- Toolchain baseline: `uv`, `ruff`, `ty`.
- Dependency vulnerability baseline (Python): `uv` + `pip-audit`.
- Future documentation site: Nextra.

### 5) Mandatory Local Enforcement

- Git hooks always enabled and non-bypassable.
- Mandatory checks include:
  - `gitleaks`
  - `semgrep` (OWASP-oriented SAST)
  - dependency vulnerability checks
  - formatter/linter/security checks by detected stack
- No skip guidance. Failures must be fixed locally.
- If a mandatory tool is missing or not operational, agents must attempt local remediation in-order:
  detect -> install -> configure/authenticate when applicable -> re-run failing check.
- If remediation still fails due to environment constraints, operation remains blocked and explicit manual remediation steps are required.

### 6) Install and Bootstrap Behavior

- Existing repo: detect stack/IDE/platform and adapt.
- Empty repo: guided initialization wizard.
- Installer must ensure first-commit readiness.
- Support add/remove stack and add/remove IDE with safe cleanup.
- Operational readiness means each required tool is:
  installed + configured + authenticated (when applicable) + operational.

### 7) Framework vs Installed Instance

- Distinguish clearly:
  - Framework: OSS core product maintained by maintainers.
  - Installed instance: per-repo `.ai-engineering/`.
- Must be explicit in architecture and updates.

### 8) Command Contract (Skills Behavior)

- `/commit` -> stage + commit + push.
- `/commit --only` -> stage + commit.
- `/pr` -> stage + commit + push + create PR + enable auto-complete (`--auto --squash --delete-branch`).
- `/pr --only` -> create PR.
- `/acho` -> stage + commit + push.
- `/acho pr` -> stage + commit + push + create PR + enable auto-complete (`--auto --squash --delete-branch`).

Mandatory PR behavior is embedded in the command definitions above.

Stack and IDE management commands:

- `ai stack add <name>`
- `ai stack remove <name>`
- `ai ide add <name>`
- `ai ide remove <name>`

`/pr --only` policy when branch is not pushed:

- Emit warning.
- Propose auto-push.
- If declined, do not hard-fail; continue with engineer-selected PR handling mode.

### 9) Agentic Model

ai-engineering is an **agentic-first framework**. Multi-agent coordination is a core capability, not an implementation detail.

#### 9.1) Execution Model

- AI agents operate as **session-scoped workers** with explicit scope, dependencies, and deliverables.
- Each session reads context from governance content (specs, skills, agents, standards) — no implicit knowledge assumed.
- Session recovery is deterministic: `_active.md` → `spec.md` → `tasks.md` → `decision-store.json`.
- Any agent can resume any session by reading the spec hierarchy.

#### 9.2) Parallel Execution

- Governed parallel execution across multiple agents is supported and encouraged.
- Parallelism boundaries are defined by **phase dependencies** in the spec's `plan.md`.
- Phases with no cross-dependencies can execute simultaneously on separate branches.
- A **Session Map** in `plan.md` pre-assigns sessions to agent slots with explicit scope and size.

#### 9.3) Branch Strategy for Multi-Agent

- **Integration branch**: spec-scoped branch (e.g., `rewrite/v2`) from default branch.
- **Phase branches**: parallel phases use `<integration-branch>-phase-N` branches.
- **Serial phases**: work directly on the integration branch.
- **Merge protocol**: phase branches rebase from integration branch before merge; integration agent reviews.
- **Phase branch lifespan**: created at phase start, deleted after merge.

#### 9.4) Phase Gate Protocol

Every phase must pass a gate before dependent phases can start:
1. All tasks marked `[x]` in `tasks.md`.
2. Phase branch merged to integration branch (if parallel).
3. Quality checks pass for affected files (content lint or code quality per stack).
4. No unresolved decisions — all new decisions recorded in `decision-store.json`.

#### 9.5) Agent Session Contract

Every agent session MUST:
1. **Start** by reading: `_active.md` → `spec.md` → `tasks.md` → `decision-store.json`.
2. **Announce** scope: session ID, phase, task range.
3. **Work** only within assigned tasks. If blocked, record decision and stop.
4. **Commit** atomically: 1 task = 1 commit with message `spec-NNN: Task X.Y — <description>`.
5. **Close** by marking completed tasks as `[x]` and updating `tasks.md` frontmatter.
6. **Report** summary: tasks done, files changed, decisions made, blockers found.

#### 9.6) Agent Coordination Protocol

When multiple agents work in parallel:
1. **Claim**: agent works on its own phase branch — no shared-file contention.
2. **Isolate**: no cross-phase file edits within a session.
3. **Checkpoint**: on completion, agent opens PR from phase branch → integration branch.
4. **Merge**: integration agent (convention: the agent that owns serial phases) reviews and merges.
5. **Gate**: integration agent runs phase gate checks before unblocking next serial phase.

#### 9.7) Spec-Driven Task Tracking

- Specs define WHAT (`spec.md`), HOW (`plan.md`), DO (`tasks.md`), DONE (`done.md`).
- `tasks.md` frontmatter tracks: `total`, `completed`, `last_session`, `next_session`.
- Parallel phases annotated with `║` symbol; session/agent/branch in phase headers.
- Size estimates (S/M/L) enable workload distribution across agents.

#### 9.8) Decision Continuity

- Decisions made by any agent are persisted in `decision-store.json` with SHA-256 context hash.
- All agents check decision store before prompting — no repeated decisions across sessions.
- Reprompt only when: decision expired, scope changed, severity changed, policy changed, or material context hash changed.

### 10) Product Management and DevEx

- Treat ai-engineering as a product: roadmap, KPIs, release channels, UX quality.
- Continuous DevEx improvement is first-class.
- OSS telemetry must be strict opt-in.

### 11) Context and Token Efficiency

- Optimize token usage and context footprint.
- Managed files must be concise, purpose-driven, and high-signal.

## Personas

- **Platform engineer**: defines reusable governance and rollout at scale.
- **Team lead**: needs predictable quality and auditable decisions.
- **Developer**: wants fast workflows with guardrails that are clear and consistent.
- **Security/AppSec**: requires verifiable local controls and traceability.
- **DevEx owner**: tracks adoption, friction, and quality impact.

## Success Metrics

- 100% mandatory gate execution on governed operations.
- 0 ungated sensitive operations.
- Time to first governed commit under 5 minutes.
- Context compaction trend improving release-over-release.

## Roadmap Overview

### Phase 1 (MVP)

- GitHub runtime integration first.
- Terminal + VS Code first.
- Cross-OS validation: Windows, macOS, Linux.
- Dogfooding in this repository from day one.
- Stack baseline: Python + Markdown/YAML/JSON/Bash with `uv`, `ruff`, `ty`, `pip-audit`.
- Mandatory system state files: install manifest, ownership map, sources lock, decision store, audit log.
- Remote skills default ON with cache, checksums, and signature metadata scaffolding.
- Exit criteria: command contract implemented, local enforcement non-bypassable, updater ownership-safe, readiness checks operational.

### Phase 2

- Azure DevOps runtime on top of Phase 1 provider-agnostic schema.
- Stronger signature verification enforcement modes.
- Additional IDE and stack adapters.

### Phase 3

- Governed parallel subagent orchestration at scale.
- Maintenance agent maturity and policy packs.
- Docs site integration and broader ecosystem work.

## Release Model

- SemVer with migration scripts for schema changes.
- Channels: `stable` and `canary`.
- Telemetry remains strict opt-in for OSS in all phases.
- Every managed update includes: rationale, expected gain, potential impact.
- Periodic simplification is mandatory, preserving functionality and governance.
- Maintenance workflow: local report first; PR only after explicit acceptance.

## Canonical Ownership Model

### Ownership Boundaries in `.ai-engineering/`

- framework-managed (updatable):
  - `standards/framework/**`
- team-managed (never overwritten by framework update):
  - `standards/team/**`
- project-managed (never overwritten by framework update):
  - `context/**`
- system-managed:
  - `state/install-manifest.json`
  - `state/ownership-map.json`
  - `state/sources.lock.json`
  - `state/decision-store.json`
  - `state/audit-log.ndjson`

Additional framework-managed project-root files:

- `CLAUDE.md`
- `codex.md`
- `.github/copilot-instructions.md`

### Update Rules

- Installer creates missing folders/files safely.
- Updater modifies only framework-managed and system-managed paths.
- Team/project content is always preserved.
- Schema/version migrations are explicit, idempotent, and auditable.

### Standards Layering Precedence

1. `standards/framework/core.md`
2. `standards/framework/stacks/<stack>.md`
3. `standards/team/core.md`
4. `standards/team/stacks/<stack>.md`

## Target Installed Structure

```text
.ai-engineering/
  standards/
    framework/
      core.md
      stacks/
        python.md
    team/
      core.md
      stacks/
        python.md
  context/
    product/
      vision.md
      roadmap.md
    delivery/
      discovery.md
      architecture.md
      planning.md
      implementation.md
      review.md
      verification.md
      testing.md
      iteration.md
    backlog/
      epics.md
      features.md
      user-stories.md
      tasks.md
    learnings.md
  state/
    install-manifest.json
    ownership-map.json
    sources.lock.json
    decision-store.json
    audit-log.ndjson
```

## Template Packaging and Replication

- Author canonical governance content in repository root `.ai-engineering/`.
- Mirror distributable template content in `src/ai_engineering/templates/.ai-engineering/`.
- Keep non-state files identical between canonical and template mirror, except high-churn project execution logs (`context/backlog/tasks.md`, `context/delivery/implementation.md`, and `context/delivery/evidence/**`) that remain canonical-only runtime artifacts.
- Generate `state/*` at install/update runtime from typed defaults and migrations.
- Installer replication rule: create missing files only; never overwrite existing team/project customizations.

## Remote Skills and Cache Model

Default mode:

- Remote ON with local cache.

Initial sources:

- `https://skills.sh/`
- `https://www.aitmpl.com/skills`

Required controls:

- source allowlist,
- lock pinning/versioning,
- checksum validation,
- signature metadata scaffolding,
- cache TTL,
- offline fallback,
- no unsafe remote execution patterns.

Bootstrap exception:

- null checksum values are allowed only before first successful sync and must be replaced by pinned checksums afterward.

## AI Permissions Policy (DevEx + Security)

- Default allow: read/list/get/search/inspect operations.
- Guardrailed: write/execute/high-impact actions.
- Restricted: destructive and sensitive operations.
- Policies must never weaken local enforcement or governance controls.

## Quality Model (Sonar-like without Local Sonar Server)

Local SonarQube server is not required.
Instead:

- define Sonar-like quality gates in framework standards,
- define SonarLint-like local coding profile in standards/skills,
- enforce measurable local checks via hooks and stack tooling,
- keep quality rules content-driven and versioned in `.ai-engineering/`.

## Decision and Audit Contract

When weakening non-negotiables is requested:

1. warn,
2. generate remediation patch suggestion,
3. never auto-apply,
4. require explicit risk acceptance if declined,
5. persist decision in `decision-store.json`,
6. append event to `audit-log.ndjson`.

AI must check decision store first and avoid repeated prompts unless:

- decision expired,
- severity changed,
- scope changed,
- policy changed,
- material context changed.

## Rollout Plan (From Scratch)

### Phase 0 - Rebuild Baseline

- Create clean branch/worktree from `origin/main`.
- Rebuild contract-first repository structure.
- Keep runtime minimal.

### Phase 1 - Content Core + Installability

- Finalize canonical templates under `.ai-engineering/`.
- Implement minimal Python install/update/doctor/add-remove.
- Ensure non-bypass local hooks and readiness checks.

### Phase 2 - Dogfooding + Hard Validation

- Install framework into this framework repo itself.
- Run full E2E validation across:
  - empty/existing repos,
  - GitHub detection paths,
  - tool missing/present/authenticated states,
  - Windows/macOS/Linux.

### Phase 3 - Release Readiness

- Freeze contract.
- Validate migration behavior.
- Publish release with clear versioning and upgrade notes.

Merge to main only after full E2E success.

## Definition of Done (Product-Level)

ai-engineering is considered ready only when:

- installation replicates canonical `.ai-engineering/` correctly,
- updates preserve team/project ownership boundaries,
- mandatory local gates are enforceable and non-bypassable,
- command contract behaves as specified,
- decision and audit files are operational,
- cross-OS validation passes,
- docs remain concise and understandable by humans and AI.
