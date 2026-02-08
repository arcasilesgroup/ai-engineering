# ai-engineering Framework Contract (v1)

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
- `/pr` -> stage + commit + push + create PR.
- `/pr --only` -> create PR.
- `/acho` -> stage + commit + push.
- `/acho pr` -> stage + commit + push + create PR.

`/pr --only` policy when branch is not pushed:

- Emit warning.
- Propose auto-push.
- If declined, do not hard-fail; continue with engineer-selected PR handling mode.

### 9) Agentic Model

- Governed parallel execution is required.
- Governance must define safe delegation, verification, and merge-back outcomes.
- Assistant-internal implementation details are not mandated by this contract.

### 10) Product Management and DevEx

- Treat ai-engineering as a product: roadmap, KPIs, release channels, UX quality.
- Continuous DevEx improvement is first-class.
- OSS telemetry must be strict opt-in.

### 11) Context and Token Efficiency

- Optimize token usage and context footprint.
- Managed files must be concise, purpose-driven, and high-signal.
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
- Keep non-state files identical between canonical and template mirror.
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
