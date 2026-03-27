# Plan: spec-082 Local-First Framework Events Reset with agentsview Integration

## Pipeline: full
## Phases: 5
## Tasks: 19 (build: 17, verify: 1, guard: 1)

### Phase 1: Lock Canonical Contract
**Gate**: The new state artifacts, schema boundaries, and capability catalog are defined by failing tests and concrete models before host emitters or legacy removal begin.
- [x] T-1.1: Write failing tests for `framework-events.ndjson` covering artifact path, schema versioning, append-only behavior, and the rule that new framework telemetry no longer targets `audit-log.ndjson`. (agent: build)
- [x] T-1.2: Implement the canonical framework event models, writer, and state-path plumbing for `.ai-engineering/state/framework-events.ndjson`. (agent: build)
- [x] T-1.3: Write failing tests for `framework-capabilities.json` generation from registered skills, agents, context classes, and hook kinds. (agent: build)
- [x] T-1.4: Implement capability catalog generation and persistence for `.ai-engineering/state/framework-capabilities.json` using existing registries as source of truth. (agent: build)

### Phase 2: Instrument Canonical Emitters
**Gate**: Supported host surfaces emit canonical framework events with data minimization, stable codes, and explicit degraded outcomes when host metadata is unavailable.
- [x] T-2.1: Write failing tests for canonical `skill_invoked` and `agent_dispatched` emission across Claude Code and GitHub Copilot surfaces, plus degraded behavior expectations for Codex and Gemini. (agent: build)
- [x] T-2.2: Implement shared canonical emitter helpers and migrate skill and agent hook writers from legacy audit output to `framework-events.ndjson`. (agent: build)
- [x] T-2.3: Write failing tests for context-load events covering context-class distinction and initiator attribution when skill, agent, or framework component metadata is available. (agent: build)
- [x] T-2.4: Implement context-load instrumentation for language, framework, team, project-identity, spec, plan, and decision-store events. (agent: build)
- [x] T-2.5: Write failing tests for framework-error, IDE-hook, and git hook or gate outcome events with stable component or error or check fields and no raw payload leakage. (agent: build)
- [x] T-2.6: Implement framework-error, IDE-hook, and git hook or gate canonical emitters with stable fields, minimization rules, and explicit degraded outcomes where hosts lack full fidelity. (agent: build)

### Phase 3: Reset The Legacy Surface
**Gate**: No supported surface exposes `observe` dashboards, `signals` telemetry, or new framework writes to `audit-log.ndjson`, and templates no longer promise the retired UX.
- [x] T-3.1: Write failing CLI, template, and installer-state tests asserting `observe` removal, `signals` retirement, and zero new framework writes to `audit-log.ndjson`. (agent: build)
- [x] T-3.2: Remove `observe` and `signals` CLI wiring and retire legacy aggregation modules, command routing, and next-actions tied only to dashboard UX. (agent: build)
- [x] T-3.3: Replace or remove legacy audit writers, hook wrappers, and installer, updater, state, and ownership references so framework telemetry flows only through `framework-events.ndjson` and `framework-capabilities.json`. (agent: build)
- [x] T-3.4: Update project templates, hook configs, instructions, and observability docs to remove `observe`, `signals emit`, and `audit-log.ndjson` as the supported framework observability surface. (agent: build)

### Phase 4: Define The agentsview Contract
**Gate**: `ai-engineering` produces a documented native-source contract and fixtures that `agentsview` can ingest without requiring per-project manual viewer configuration.
- [x] T-4.1: Write failing fixture and contract tests for native `agentsview` ingestion of `framework-events.ndjson` and `framework-capabilities.json`. (agent: build)
- [x] T-4.2: Implement the `agentsview` source contract artifacts, fixture or testdata generation, and upgrade notes documenting independent `agentsview` install and the no-per-project-manual-config expectation for standard `ai-eng install` projects. (agent: build)

### Phase 5: Verify And Reconcile Governance
**Gate**: Focused suites pass, spec-082 acceptance criteria are proven, and the decision and documentation surface no longer conflicts with the redesigned observability model.
- [x] T-5.1: Run the focused unit and integration suites for event models, host emitters, state and installer changes, and legacy-surface removal; fix regressions introduced by the redesign. (agent: build)
- [x] T-5.2: Verify spec-082 acceptance criteria for data minimization, cross-IDE degraded parity, capability catalog completeness, independent `agentsview` assumptions, and zero new writes to `audit-log.ndjson`. (agent: verify)
- [x] T-5.3: Review governance and decision drift, revise or supersede DEC-007 and DEC-013 as needed, and confirm docs and templates no longer describe `observe` dashboards or `audit-log.ndjson` as the supported surface. (agent: guard)

## Notes

- TDD applies to the canonical artifacts, emitter families, legacy-surface removal, and `agentsview` contract work: tests first, then implementation.
- Phase 2 depends on the artifacts and models locked in Phase 1.
- Phase 3 depends on Phase 1 for artifact paths and should not start removing legacy writers until canonical emitters exist from Phase 2.
- Phase 4 depends on the canonical artifact definitions from Phase 1 and should use the real v1 artifacts instead of an intermediate export format.
- Phase 5 runs only after build tasks are complete and includes the decision-store reconciliation required by spec-082.
