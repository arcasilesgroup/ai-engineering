# Epic Backlog

## Purpose

This document defines **high-level epics** aligned with the product roadmap. Each epic represents a major deliverable or capability that spans multiple features and user stories.

**Last Updated:** 2026-02-08 (Phase 0)

---

## Epic Mapping to Roadmap Phases

| Epic | Phase | Status | Target Completion |
|------|-------|--------|-------------------|
| Epic 1: Core CLI and State Management | Phase 1 | Not Started | Week 2 |
| Epic 2: Mandatory Local Enforcement | Phase 1 | Not Started | Week 4 |
| Epic 3: Command Model and Branch Governance | Phase 1 | Not Started | Week 6 |
| Epic 4: Remote Skills with Integrity | Phase 2 | Not Started | TBD |
| Epic 5: Agent Orchestration with Bounded Capabilities | Phase 3 | Not Started | TBD |
| Epic 6: Context Optimization and Maintenance Agent | Phase 1-3 | Not Started | Progressive |
| Epic 7: Cross-OS and Multi-Provider Foundation | Phase 1-3 | Not Started | Progressive |

---

## Epic 1: Core CLI and State Management

### Objective
Establish foundational CLI structure and session state management to enable persistent context and change tracking.

### Scope
- CLI scaffolding with command routing
- Session lifecycle (start, end, pause, resume, status)
- State persistence (session.json, history.json)
- Change history logging
- Basic status queries

### Dependencies
- None (foundational epic)

### Acceptance Criteria
- [ ] CLI supports all core commands (install, session, status, help, version)
- [ ] Sessions can be started, paused, resumed, and ended
- [ ] Session state persisted to file system atomically
- [ ] History queryable with `ai history` command
- [ ] Test coverage >80%

### Key Deliverables
- `src/ai_engineering/cli.py` - Command dispatcher
- `src/ai_engineering/state_manager.py` - Session lifecycle management
- `tests/unit/test_state_manager.py` - State manager tests
- `tests/e2e/test_session_workflow.py` - E2E session tests

### Risks and Mitigation
| Risk | Mitigation |
|------|------------|
| State corruption from concurrent sessions | File locking, atomic writes, validation on load |
| Session state schema evolution | Schema versioning, migration scripts |

### Related Features
- Feature 1.1: CLI Scaffolding
- Feature 1.2: Session State Management
- Feature 1.3: History Tracking

**Owner:** TBD
**Status:** Not Started
**Target Completion:** Week 2 of Phase 1

---

## Epic 2: Mandatory Local Enforcement

### Objective
Implement local gates and hooks that agents cannot bypass, enforcing standards and security policies at commit time.

### Scope
- Installer with existing config detection and migration
- Manifest parser with schema validation
- Standards resolver with layered precedence
- Gate engine for pre-commit and pre-push checks
- Git hook installation and management
- Audit logging for all gate outcomes

### Dependencies
- Epic 1 (CLI and State Management)

### Acceptance Criteria
- [ ] `ai install` creates `.ai-engineering/` structure and installs hooks
- [ ] Existing configs (ADO, CLAUDE.md) detected and migrated
- [ ] Gates block destructive operations and sensitive files
- [ ] Gate overrides (`--no-verify`) logged in audit trail
- [ ] Standards resolved using correct layered precedence
- [ ] Test coverage >85%

### Key Deliverables
- `src/ai_engineering/installer.py` - Bootstrap logic
- `src/ai_engineering/manifest_parser.py` - YAML parsing and validation
- `src/ai_engineering/standards_resolver.py` - Layered precedence logic
- `src/ai_engineering/gate_engine.py` - Gate enforcement
- `.git/hooks/pre-commit` - Pre-commit hook template
- `tests/e2e/test_install_flow.py` - Installation E2E tests

### Risks and Mitigation
| Risk | Mitigation |
|------|------------|
| Git hook conflicts with existing tools | Detection, chaining, clear warnings |
| False positives blocking legitimate commits | Tunable sensitivity, override with justification |
| Migration errors from complex existing configs | Comprehensive detection, validation, dry-run mode |

### Related Features
- Feature 2.1: Installer and Migration
- Feature 2.2: Manifest Schema and Validation
- Feature 2.3: Standards Resolution
- Feature 2.4: Gate Enforcement

**Owner:** TBD
**Status:** Not Started
**Target Completion:** Week 4 of Phase 1

---

## Epic 3: Command Model and Branch Governance

### Objective
Deliver complete command surface area for Phase 1 MVP with basic branch governance support.

### Scope
- All Phase 1 commands functional and tested
- Context optimization (token budgets, ignore patterns)
- Audit logging for compliance
- Standards validation and diffing tools
- Diagnostics (`ai doctor`)

### Dependencies
- Epic 1 (CLI)
- Epic 2 (Enforcement)

### Acceptance Criteria
- [ ] All Phase 1 commands implemented (see command contract in architecture.md)
- [ ] Context loaded within token budget
- [ ] Audit log captures all operations
- [ ] `ai doctor` diagnoses common issues
- [ ] Test coverage >80%

### Key Deliverables
- `src/ai_engineering/context_optimizer.py` - Token-aware context loading
- `src/ai_engineering/audit_logger.py` - Append-only audit trail
- `src/ai_engineering/commands/` - Individual command implementations
- `tests/e2e/test_all_commands.py` - Command E2E tests

### Risks and Mitigation
| Risk | Mitigation |
|------|------------|
| Token estimation inaccurate | Start with conservative heuristic, validate with real repos |
| Context optimization too aggressive | Priority files always included, fail-safe |

### Related Features
- Feature 3.1: Core Commands
- Feature 3.2: Context Optimization
- Feature 3.3: Audit Logging
- Feature 3.4: Standards Validation
- Feature 3.5: Diagnostics

**Owner:** TBD
**Status:** Not Started
**Target Completion:** Week 6 of Phase 1

---

## Epic 4: Remote Skills with Integrity

### Objective
Enable org-wide skill sharing with integrity checking and local caching.

### Scope
- Skill registry design (centralized GitHub repo initially)
- Skill fetching and caching
- Integrity checking (checksums, signatures)
- Skill execution with parameter support
- `ai skill add/list/remove/run` commands

### Dependencies
- Epic 3 (Command Model)

### Acceptance Criteria
- [ ] Skills fetchable from remote URLs
- [ ] Integrity verified via checksums (Phase 2) or signatures (Phase 3)
- [ ] Local cache with TTL
- [ ] Skills executable with parameters
- [ ] Test coverage >80%

### Key Deliverables
- `src/ai_engineering/skill_manager.py` - Skill lifecycle
- `src/ai_engineering/skill_cache.py` - Local caching
- Remote skill registry (GitHub repo: `.ai-engineering-skills`)
- `tests/e2e/test_skill_workflow.py` - Skill E2E tests

### Risks and Mitigation
| Risk | Mitigation |
|------|------------|
| Skill integrity compromised | Checksum validation (Phase 2), signatures (Phase 3), allow-list |
| Network dependency | Graceful degradation, local cache fallback |

### Related Features
- Feature 4.1: Skill Registry Design
- Feature 4.2: Skill Fetching and Caching
- Feature 4.3: Integrity Checking
- Feature 4.4: Skill Execution

**Owner:** TBD
**Status:** Not Started
**Target Completion:** Phase 2

---

## Epic 5: Agent Orchestration with Bounded Capabilities

### Objective
Intelligent routing of tasks to appropriate agents with bounded capability enforcement.

### Scope
- Agent capability model definition
- Task-to-agent routing logic
- Agent handoff protocols
- Capability enforcement (read-only vs write access)
- `ai agent route/list` commands

### Dependencies
- Epic 4 (Remote Skills)

### Acceptance Criteria
- [ ] Agents defined with capability sets (read, write, execute, etc.)
- [ ] Tasks routed to appropriate agent based on type
- [ ] Agent capabilities enforced (e.g., read-only agent cannot write)
- [ ] Handoffs between agents tracked
- [ ] Test coverage >75%

### Key Deliverables
- `src/ai_engineering/agent_orchestrator.py` - Routing and handoff logic
- `src/ai_engineering/capability_model.py` - Capability definitions
- Agent capability manifest schema
- `tests/e2e/test_agent_orchestration.py` - Orchestration E2E tests

### Risks and Mitigation
| Risk | Mitigation |
|------|------------|
| Orchestration complexity | Start simple (manual routing hints), iterate to auto-routing |
| Capability model too rigid | Flexible capability sets, override mechanism |

### Related Features
- Feature 5.1: Capability Model
- Feature 5.2: Agent Routing
- Feature 5.3: Handoff Protocols
- Feature 5.4: Capability Enforcement

**Owner:** TBD
**Status:** Not Started
**Target Completion:** Phase 3

---

## Epic 6: Context Optimization and Maintenance Agent

### Objective
Autonomous context health management and token efficiency optimization.

### Scope
- Stale content detection
- Conflict detection and flagging
- Automated link checking and fixing
- Token budget optimization
- Maintenance agent scheduler

### Dependencies
- Epic 1 (State Management)
- Progressive enhancement across all phases

### Acceptance Criteria
- [ ] Maintenance agent detects stale content (>90 days old)
- [ ] Broken links detected and auto-fixed
- [ ] Conflicts flagged for human review
- [ ] Token efficiency optimized (<30% overhead)
- [ ] Agent runs on schedule (weekly, monthly)
- [ ] Test coverage >75%

### Key Deliverables
- `src/ai_engineering/maintenance_agent.py` - Agent logic
- `src/ai_engineering/context_health.py` - Health check algorithms
- Maintenance report template
- `tests/e2e/test_maintenance_agent.py` - Agent E2E tests

### Risks and Mitigation
| Risk | Mitigation |
|------|------------|
| False positives (flagging active content as stale) | Tunable thresholds, git activity tracking |
| Auto-fixes introduce errors | Conservative auto-fix scope, approval gates |

### Related Features
- Feature 6.1: Stale Detection (Phase 1)
- Feature 6.2: Conflict Detection (Phase 2)
- Feature 6.3: Maintenance Agent (Phase 3)
- Feature 6.4: Token Optimization (All Phases)

**Owner:** TBD
**Status:** Progressive (starts in Phase 1)
**Target Completion:** Fully delivered in Phase 3

---

## Epic 7: Cross-OS and Multi-Provider Foundation

### Objective
Ensure framework works consistently across operating systems and AI providers.

### Scope
- Cross-OS compatibility (macOS, Linux in Phase 1; Windows in Phase 3)
- Provider adapters (Claude, GitHub Copilot, OpenAI, local models)
- Provider-agnostic command model
- E2E testing on all platforms

### Dependencies
- All epics (cross-cutting concern)

### Acceptance Criteria
- [ ] Framework functional on macOS and Linux (Phase 1)
- [ ] Framework functional on Windows (Phase 3)
- [ ] Provider adapters for 3+ AI services (Phase 2+)
- [ ] E2E tests passing on all target platforms
- [ ] Test coverage >80% for adapters

### Key Deliverables
- `src/ai_engineering/adapters/` - Provider-specific adapters
- Cross-OS test suite (macOS, Linux, Windows)
- Provider adapter interface definition
- `tests/e2e/test_cross_os.py` - Cross-OS E2E tests

### Risks and Mitigation
| Risk | Mitigation |
|------|------------|
| Path separator issues (Unix vs Windows) | Use `pathlib.Path` everywhere |
| Provider API changes break adapters | Versioned adapters, graceful degradation |

### Related Features
- Feature 7.1: macOS/Linux Support (Phase 1)
- Feature 7.2: Provider Adapters (Phase 2)
- Feature 7.3: Windows Support (Phase 3)
- Feature 7.4: Multi-Provider Testing (Phase 2+)

**Owner:** TBD
**Status:** Progressive (starts in Phase 1)
**Target Completion:** Fully delivered in Phase 3

---

## Epic Tracking and Updates

### How to Update Epics

1. **Status Changes:** Update status as epics move through workflow (Not Started → In Progress → Complete)
2. **Scope Adjustments:** Document scope changes in epic description with rationale
3. **Risk Updates:** Add new risks as discovered, mark mitigations as implemented
4. **Feature Mapping:** Link to features.md as features are defined

### Epic Status Definitions

- **Not Started:** Epic defined but no work begun
- **In Progress:** At least one feature in active development
- **Blocked:** Waiting on dependency or external factor
- **Complete:** All acceptance criteria met, features delivered
- **Deferred:** Moved to later phase or out of scope

---

## References

- [Product Roadmap](../product/roadmap.md) - Phase planning
- [Architecture Document](../delivery/architecture.md) - System design
- [Planning Document](../delivery/planning.md) - Detailed implementation plan
- [Features Document](./features.md) - Feature breakdown per epic
