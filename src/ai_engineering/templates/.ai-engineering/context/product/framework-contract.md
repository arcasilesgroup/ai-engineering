# ai-engineering Framework Contract

## Update Metadata

- Rationale: restructure as enforcement document with MUST/MUST NOT directives; add context threading protocol and capability-task matching for multi-agent orchestration; move temporal content (roadmap, rollout plan) to product-contract.md.
- Expected gain: AI agents treat this as binding law, not documentation. Every statement is actionable and verifiable. Multi-agent coordination gaps (context threading, capability matching) are formally addressed.
- Potential impact: all agent behaviors governed by this contract. Existing skills/agents continue to comply. Template mirror must be synced.

## 1. Identity

ai-engineering is an open-source governance framework for AI-assisted software delivery.

### 1.1 Mission

AI agents and human engineers MUST use this framework to ensure consistent quality, security, and delivery discipline. The framework MUST:

- guide AI behavior through explicit standards and context,
- enforce local quality and security gates,
- preserve project and team ownership boundaries,
- remain easy for humans to understand and maintain.

### 1.2 Product Model

ai-engineering is a content-first framework:

- Markdown, YAML, JSON, and Bash define behavior and governance.
- `.ai-engineering/` is the canonical source of truth.

## 2. Non-Negotiable Directives

### 2.1 Core Philosophy

All agents and tools operating under this framework MUST adhere to these principles:

- Deliver solutions that are simple, efficient, practical, robust, and secure.
- Enforce quality and security by default — never defer enforcement to optional steps.
- Apply strong governance to prevent AI drift and hallucination.
- Follow the mandatory lifecycle for non-trivial work:
  Discovery → Architecture → Planning → Implementation → Review → Verification → Testing → Iteration.

### 2.2 Interoperability Requirements

The framework MUST support:

- Native workflows for GitHub Copilot, Claude Code, Codex, and Gemini.
- Governed parallel execution across multiple agents.
- Cross-OS operation from day one: Windows, macOS, Linux.
- VCS provider detection: GitHub and Azure DevOps.

Agents MUST NOT assume a single platform or OS. All governance operations MUST work identically across supported targets.

### 2.3 Single Source of Truth

- `.ai-engineering/` is the canonical source. All agents MUST read governance content from this directory.
- No duplication SHALL exist across standards, context, skills, and agent configuration.
- All managed artifacts MUST be concise, purpose-driven, and high-signal.

### 2.4 Mandatory Local Enforcement

- Git hooks MUST be enabled and non-bypassable. The `--no-verify` flag MUST NOT be used on any git command.
- Mandatory checks MUST include:
  - `gitleaks` — secret detection.
  - `semgrep` — OWASP-oriented SAST.
  - Dependency vulnerability checks per stack.
  - Formatter, linter, and security checks by detected stack.
- Failures MUST be fixed locally. No skip guidance SHALL be provided.
- If a mandatory tool is missing, agents MUST attempt remediation in order: detect → install → configure/authenticate → re-run.
- If remediation fails, the operation MUST remain blocked and explicit manual remediation steps MUST be provided.

### 2.5 Install and Bootstrap Behavior

- On existing repos: the installer MUST detect stack, IDE, and platform, then adapt.
- On empty repos: the installer MUST provide a guided initialization wizard.
- The installer MUST ensure first-commit readiness.
- `add/remove stack` and `add/remove IDE` MUST perform safe cleanup.
- Operational readiness means each required tool is: installed + configured + authenticated (when applicable) + operational.

### 2.6 Framework vs Installed Instance

All agents MUST distinguish between:

- **Framework**: the OSS core product maintained by framework maintainers.
- **Installed instance**: the per-repo `.ai-engineering/` directory.

The updater MUST NOT modify team-managed or project-managed content. The installer MUST NOT overwrite existing customizations.

## 3. Agentic Model

ai-engineering is an **agentic-first framework**. Multi-agent coordination is a core capability, not an implementation detail.

### 3.1 Execution Model

- AI agents MUST operate as **session-scoped workers** with explicit scope, dependencies, and deliverables.
- Each session MUST read context from governance content (specs, skills, agents, standards) — no implicit knowledge assumed.
- Session recovery MUST be deterministic: `_active.md` → `spec.md` → `tasks.md` → `decision-store.json`.
- Any agent MUST be able to resume any session by reading the spec hierarchy.

### 3.2 Parallel Execution

- Governed parallel execution across multiple agents is supported and encouraged.
- Parallelism boundaries MUST be defined by **phase dependencies** in the spec's `plan.md`.
- Phases with no cross-dependencies SHOULD execute simultaneously on separate branches.
- A **Session Map** in `plan.md` MUST pre-assign sessions to agent slots with explicit scope and size.

### 3.3 Branch Strategy for Multi-Agent

- **Integration branch**: spec-scoped branch (e.g., `rewrite/v2`) from default branch.
- **Phase branches**: parallel phases MUST use `<integration-branch>-phase-N` branches.
- **Serial phases**: MUST work directly on the integration branch.
- **Merge protocol**: phase branches MUST rebase from integration branch before merge; the integration agent reviews.
- **Phase branch lifespan**: created at phase start, deleted after merge.

### 3.4 Phase Gate Protocol

Every phase MUST pass a gate before dependent phases can start:

1. All tasks marked `[x]` in `tasks.md`.
2. Phase branch merged to integration branch (if parallel).
3. Quality checks pass for affected files (content lint or code quality per stack).
4. No unresolved decisions — all new decisions recorded in `decision-store.json`.

### 3.5 Agent Session Contract

Every agent session MUST:

1. **Start** by reading: `_active.md` → `spec.md` → `tasks.md` → `decision-store.json`.
2. **Spec-first check**: if no active spec or active spec is completed, and work is non-trivial, invoke `create-spec` before proceeding.
3. **Announce** scope: session ID, phase, task range.
4. **Work** only within assigned tasks. If blocked, record decision and stop.
5. **Commit** atomically: 1 task = 1 commit with message `spec-NNN: Task X.Y — <description>`.
6. **Close** by marking completed tasks as `[x]` and updating `tasks.md` frontmatter.
7. **Content integrity**: if any `.ai-engineering/` file was created, deleted, renamed, or moved, execute `integrity-check` skill.
8. **Report** summary: tasks done, files changed, decisions made, blockers found.

### 3.6 Agent Coordination Protocol

When multiple agents work in parallel:

1. **Claim**: each agent works on its own phase branch — no shared-file contention.
2. **Isolate**: no cross-phase file edits within a session.
3. **Checkpoint**: on completion, agent opens PR from phase branch → integration branch.
4. **Merge**: integration agent (the agent that owns serial phases) reviews and merges.
5. **Gate**: integration agent runs phase gate checks before unblocking next serial phase.

### 3.7 Context Threading Protocol

When an orchestrator dispatches multiple agents for context gathering or parallel work:

1. **Context Output Contract**: every dispatched agent MUST produce a structured context summary with these sections: `## Findings`, `## Dependencies Discovered`, `## Risks Identified`, `## Recommendations`.

2. **Context Aggregation**: the dispatching agent MUST consolidate all context summaries before proceeding to the next phase. Consolidation MUST include:
   - Deduplication of overlapping findings.
   - Conflict resolution: security findings take priority, then governance, then quality, then style.
   - Dependency graph construction from individually discovered dependencies.

3. **Context Handoff**: when passing context between phases, the handoff MUST include: phase ID, agent ID, summary of findings, unresolved questions, and dependencies on other phases.

4. **No Implicit Context**: agents MUST NOT assume knowledge from other agents' sessions. All shared context MUST flow through spec artifacts (`tasks.md`, `decision-store.json`) or explicit context summaries.

### 3.8 Capability-Task Matching

When the orchestrator assigns tasks to agents:

1. **Capability Registry**: the agent frontmatter `capabilities` field is the authoritative registry. The orchestrator MUST match task requirements to agent capabilities before assignment.

2. **Matching Rules**:
   - Tasks requiring security review MUST be assigned to agents with security capability tokens (`sast`, `secret-detection`, `dependency-audit`, `owasp-review`).
   - Tasks requiring code modification MUST be assigned to agents with `scope: read-write`.
   - Read-only analysis tasks SHOULD prefer agents with `scope: read-only`.

3. **Fallback**: if no agent has the exact capability match, the orchestrator MUST escalate to the user rather than assign to a mismatched agent.

4. **Multi-Capability Tasks**: tasks requiring multiple capability domains SHOULD be split into sub-tasks assigned to specialized agents, not assigned to a single generalist agent.

### 3.9 Spec-Driven Task Tracking

- Specs define WHAT (`spec.md`), HOW (`plan.md`), DO (`tasks.md`), DONE (`done.md`).
- `tasks.md` frontmatter MUST track: `total`, `completed`, `last_session`, `next_session`.
- Parallel phases MUST be annotated with `║` symbol; session/agent/branch in phase headers.
- Size estimates (S/M/L) MUST be provided to enable workload distribution across agents.

### 3.10 Decision Continuity

- Decisions made by any agent MUST be persisted in `decision-store.json` with SHA-256 context hash.
- All agents MUST check the decision store before prompting — no repeated decisions across sessions.
- Reprompt is allowed only when: decision expired, scope changed, severity changed, policy changed, or material context hash changed.

## 5. Ownership Model

### 5.1 Ownership Boundaries

Within `.ai-engineering/`:

- **framework-managed** (updatable by framework): `standards/framework/**`, `skills/**`, `agents/**`.
- **team-managed** (never overwritten by framework update): `standards/team/**`.
- **project-managed** (never overwritten by framework update): `context/**`.
- **system-managed**: `state/install-manifest.json`, `state/ownership-map.json`, `state/sources.lock.json`, `state/decision-store.json`, `state/audit-log.ndjson`.

Additional framework-managed project-root files: `CLAUDE.md`, `.github/copilot-instructions.md`.

### 5.2 Update Rules

- The installer MUST create missing folders and files safely.
- The updater MUST modify only framework-managed and system-managed paths.
- Team and project content MUST always be preserved.
- Schema and version migrations MUST be explicit, idempotent, and auditable.

### 5.3 Standards Layering Precedence

1. `standards/framework/core.md`
2. `standards/framework/stacks/<stack>.md`
3. `standards/team/core.md`
4. `standards/team/stacks/<stack>.md`

Higher-numbered layers override lower-numbered layers for the same directive.

### 5.4 Target Installed Structure

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
      framework-contract.md
      product-contract.md
    specs/
      _active.md
      NNN-<slug>/
        spec.md
        plan.md
        tasks.md
        done.md
    learnings.md
  skills/
    <category>/<name>/SKILL.md
  agents/
    <name>.md
  state/
    install-manifest.json
    ownership-map.json
    sources.lock.json
    decision-store.json
    audit-log.ndjson
  manifest.yml
```

## 6. Security and Quality Contract

### 6.1 Quality Model

Local-first enforcement is mandatory:

- Quality gates MUST be defined in framework standards (Sonar-like rules without requiring Sonar).
- Local coding profiles MUST be enforced via hooks and stack tooling.
- Quality rules MUST be content-driven and versioned in `.ai-engineering/`.

Optional Sonar Cloud/SonarQube integration:

- `ai-eng setup sonar` — guided onboarding with keyring-backed credential storage.
- `ai-eng setup sonarlint` — IDE Connected Mode configuration.
- `dev/sonar-gate` skill — quality gate check in governed workflows.
- Sonar gate MUST use silent-skip when token is not configured.

### 6.2 AI Permissions Policy

- **Default allow**: read, list, get, search, inspect operations.
- **Guardrailed**: write, execute, high-impact actions.
- **Restricted**: destructive and sensitive operations.

Permissions policies MUST NOT weaken local enforcement or governance controls.

### 6.3 Decision and Audit Contract

When weakening a non-negotiable directive is requested, agents MUST:

1. Warn the user.
2. Generate a remediation patch suggestion.
3. Never auto-apply the weakening.
4. Require explicit risk acceptance if remediation is declined.
5. Persist the decision in `decision-store.json`.
6. Append the event to `audit-log.ndjson`.

Agents MUST check the decision store before prompting and MUST NOT repeat decided questions unless: decision expired, severity changed, scope changed, policy changed, or material context changed.

## 7. Distribution Model

### 7.1 Template Packaging and Replication

- Canonical governance content MUST be authored in repository root `.ai-engineering/`.
- Distributable template content MUST be mirrored in `src/ai_engineering/templates/.ai-engineering/`.
- Non-state files MUST be identical between canonical and template mirror, except spec execution logs that remain canonical-only.
- `state/*` files MUST be generated at install/update runtime from typed defaults.
- The installer MUST create missing files only and MUST NOT overwrite existing team/project customizations.

### 7.2 Remote Skills and Cache Model

- Default mode: remote ON with local cache.
- Sources: `https://skills.sh/`, `https://www.aitmpl.com/skills`.

Required controls:

- Source allowlist — agents MUST NOT fetch from unlisted sources.
- Lock pinning and versioning — all remote skills MUST be version-locked.
- Checksum validation — all remote content MUST pass checksum verification.
- Signature metadata scaffolding — all remote skills MUST include signature metadata.
- Cache TTL — cached content MUST expire per configured TTL.
- Offline fallback — the system MUST work offline using cached content.
- No unsafe remote execution — remote skill content MUST NOT execute arbitrary code.

Bootstrap exception: null checksum values are allowed only before first successful sync and MUST be replaced by pinned checksums afterward.

### 7.3 Release Model

- SemVer with migration scripts for schema changes.
- Channels: `stable` and `canary`.
- Telemetry MUST remain strict opt-in in all phases.
- Every managed update MUST include: rationale, expected gain, potential impact.
- Periodic simplification is mandatory, preserving functionality and governance.
- Maintenance workflow: local report first; PR only after explicit acceptance.

## 8. Personas and Success Metrics

### 8.1 Target Personas

- **Platform engineer**: defines reusable governance and rollout at scale.
- **Team lead**: needs predictable quality and auditable decisions.
- **Developer**: wants fast workflows with guardrails that are clear and consistent.
- **Security/AppSec**: requires verifiable local controls and traceability.
- **DevEx owner**: tracks adoption, friction, and quality impact.

### 8.2 Success Metrics

- 100% mandatory gate execution on all governed operations.
- 0 ungated sensitive operations.
- Time to first governed commit under 5 minutes.
- Context compaction trend improving release-over-release.

## 9. Definition of Done

ai-engineering is considered ready only when:

- Installation replicates canonical `.ai-engineering/` correctly.
- Updates preserve team/project ownership boundaries.
- Mandatory local gates are enforceable and non-bypassable.
- Command contract behaves as specified in Section 3.
- Decision and audit files are operational.
- Cross-OS validation passes on Windows, macOS, and Linux.
- Documentation remains concise and understandable by humans and AI.
- All directives in this contract are verifiable through automated checks or governance skills.
