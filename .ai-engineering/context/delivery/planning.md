# Phase 1 Planning: MVP Core Framework

## Overview

This document contains the detailed implementation plan for **Phase 1: MVP Core Framework**. It breaks down the prioritized backlog into executable modules with clear dependencies and Definition of Done (DoD).

**Phase Objective:** Ship minimal viable framework that can enforce standards and manage state locally

**Target Timeline:** 4-6 weeks from Phase 0 completion
**Last Updated:** 2026-02-08

---

## Phase 1 Scope Summary

### Must-Have (P0):
- CLI bootstrapping and command routing
- Installation with existing config detection
- Session state management (start/end/pause/resume/status)
- Local standards enforcement via git hooks
- Basic gate system (pre-commit, pre-push)
- Manifest schema and layered resolution
- Audit logging

### Should-Have (P1):
- Context optimization (ignore patterns, priority files)
- Basic diagnostics (`ai doctor`)
- Standards validation and diff tools

### Nice-to-Have (P2):
- Telemetry (opt-in)
- Advanced context caching

---

## Prioritized Backlog (Phase 1)

### Epic 1: Core CLI and State Management

#### Module 1.1: CLI Scaffolding (P0)
**Objective:** Basic command structure and routing

**Tasks:**
- Set up Python project (`pyproject.toml`, `src/`, `tests/`)
- Choose CLI framework (Typer recommended)
- Implement command dispatcher
- Add help system and version command
- Create `ai --version` and `ai help`

**Dependencies:** None

**Acceptance Criteria:**
- `ai --version` shows framework version
- `ai help` displays command list
- `ai help <command>` shows command-specific help
- Test coverage >80%

**Estimated Effort:** 3-5 days

---

#### Module 1.2: State Manager (P0)
**Objective:** Session lifecycle and history tracking

**Tasks:**
- Design state schema (session.json, history.json)
- Implement session creation, start, end, pause, resume
- Add session status query
- Add change history logging
- File-based atomic writes (avoid corruption)

**Dependencies:** CLI Scaffolding

**Acceptance Criteria:**
- `ai session start` creates session with unique ID
- `ai session end` logs session summary to history
- `ai session status` shows current session state
- `ai history --limit 10` shows last 10 operations
- State files are atomic (no partial writes)
- Test coverage >85%

**Estimated Effort:** 5-7 days

**State Schema (Draft):**
```json
// .ai-engineering/state/session.json
{
  "id": "sess_20260208_123456",
  "status": "active",  // active, paused, ended
  "started_at": "2026-02-08T12:34:56Z",
  "branch": "feature/xyz",
  "user": "soydachi",
  "context_loaded": ["README.md", "src/main.py"],
  "operations": [
    {
      "type": "commit",
      "timestamp": "2026-02-08T12:45:00Z",
      "files": ["src/main.py"],
      "message": "Add feature X",
      "gates_passed": ["lint", "format"]
    }
  ]
}

// .ai-engineering/state/history.json
{
  "sessions": [
    {
      "id": "sess_20260208_123456",
      "started_at": "2026-02-08T12:34:56Z",
      "ended_at": "2026-02-08T14:00:00Z",
      "duration_seconds": 5160,
      "branch": "feature/xyz",
      "commits": 3,
      "gates_passed": 8,
      "gates_overridden": 0
    }
  ]
}
```

---

### Epic 2: Mandatory Local Enforcement

#### Module 2.1: Installer (P0)
**Objective:** Bootstrap `.ai-engineering/` structure and detect existing config

**Tasks:**
- Implement `ai install` command
- Detect existing config (ADO, GitHub CLAUDE.md, Cursor, etc.)
- Prompt for migration and merge detected config
- Create directory structure (context/, state/, standards/)
- Generate default manifest.yml
- Install git hooks (pre-commit, pre-push, post-commit)

**Dependencies:** CLI Scaffolding

**Acceptance Criteria:**
- `ai install` creates `.ai-engineering/` with correct structure
- Existing ADO config detected and merged into manifest.yml
- Git hooks installed and functional
- Migration prompt shown when existing config detected
- Idempotent (re-running `ai install` doesn't break state)
- Test coverage >80% (mock file system)

**Estimated Effort:** 7-10 days

**Directory Structure Created:**
```
.ai-engineering/
  manifest.yml          # Generated with defaults + migrated config
  context/              # Empty (user-populated)
    product/
    delivery/
    backlog/
  state/                # Session and history
    session.json
    history.json
  standards/            # Optional (future)
  local.yml             # Empty, gitignored
```

---

#### Module 2.2: Manifest Parser (P0)
**Objective:** Load, validate, and merge manifest files

**Tasks:**
- Define manifest schema (YAML)
- Implement YAML parsing with validation
- Add schema versioning support
- Implement layered merge logic (local → repo → team → org → defaults)
- Add validation errors with clear messages

**Dependencies:** None (can be parallel)

**Acceptance Criteria:**
- Manifest loads and validates against schema
- Invalid manifest shows clear error messages with line numbers
- Layered merge works correctly (scalars replace, lists extend, dicts merge)
- Test coverage >90% (core functionality)

**Estimated Effort:** 5-7 days

---

#### Module 2.3: Standards Resolver (P0)
**Objective:** Resolve standards using layered precedence

**Tasks:**
- Implement precedence hierarchy (local > repo > team > org > defaults)
- Add `ai standards show` command
- Add `ai standards diff` command
- Cache resolved standards (invalidate on manifest change)

**Dependencies:** Manifest Parser

**Acceptance Criteria:**
- `ai standards show` displays resolved standards with layer attribution
- `ai standards diff repo org` shows differences between layers
- Precedence logic matches architecture spec
- Test coverage >85%

**Estimated Effort:** 4-6 days

---

#### Module 2.4: Gate Engine (P0)
**Objective:** Enforce gates via git hooks

**Tasks:**
- Implement gate detection logic (sensitive operations, destructive commands)
- Add gate approval prompt with justification
- Integrate with git hooks (pre-commit, pre-push)
- Log gate outcomes to audit trail
- Support gate override with `--no-verify` detection

**Dependencies:** Standards Resolver, State Manager

**Acceptance Criteria:**
- `ai gate pre-commit` blocks destructive operations by default
- User prompted for approval on sensitive operations
- Gate overrides logged in audit trail
- Git hooks call gate engine and respect exit codes
- Test coverage >85%

**Estimated Effort:** 7-10 days

**Gate Logic (Example):**
```python
def run_pre_commit_gate(staged_files: List[str]) -> bool:
    """Run pre-commit gate checks."""
    standards = resolve_standards("gates.pre_commit")

    # Check 1: Destructive operations
    if standards.get("destructive_ops") == "mandatory":
        if detect_destructive_ops(staged_files):
            approved = prompt_approval("Destructive operation detected")
            log_gate_outcome("destructive_ops", approved)
            if not approved:
                return False

    # Check 2: Secret scan
    if standards.get("secret_scan") == "mandatory":
        if detect_secrets(staged_files):
            print("ERROR: Secrets detected in staged files")
            return False

    # Check 3: Lint
    if standards.get("lint") == "mandatory":
        if not run_linter(staged_files):
            return False

    return True
```

---

### Epic 3: Command Model and Branch Governance

#### Module 3.1: Core Commands (P0)
**Objective:** Implement all Phase 1 commands

**Commands to Implement:**
- `ai install` (Module 2.1)
- `ai session start/end/pause/resume/status` (Module 1.2)
- `ai status` (overall framework status)
- `ai gate pre-commit/pre-push/list` (Module 2.4)
- `ai standards show/validate/diff` (Module 2.3)
- `ai history` (Module 1.2)
- `ai help` (Module 1.1)
- `ai version` (Module 1.1)
- `ai doctor` (P1)

**Dependencies:** All prior modules

**Acceptance Criteria:**
- All commands functional and tested
- Help text clear and accurate
- Error messages actionable
- Test coverage >80% per command

**Estimated Effort:** Distributed across modules above

---

#### Module 3.2: Context Optimizer (P1)
**Objective:** Token-aware file selection and caching

**Tasks:**
- Implement ignore patterns logic
- Implement priority files logic
- Add token estimation (rough heuristic: chars / 4)
- Implement progressive loading within token budget
- Add `ai context show` command
- Add basic caching (file-based, TTL)

**Dependencies:** Manifest Parser, Standards Resolver

**Acceptance Criteria:**
- Context loaded within configured token budget
- Priority files always included
- Ignore patterns respected
- `ai context show` displays files to be loaded with token estimate
- Test coverage >80%

**Estimated Effort:** 5-7 days

---

#### Module 3.3: Audit Logger (P0)
**Objective:** Immutable log of all operations

**Tasks:**
- Design audit log schema (append-only JSON lines)
- Log all gate approvals/denials
- Log session start/end
- Log gate overrides (--no-verify detection)
- Add `ai audit` command (P2, can defer)

**Dependencies:** State Manager

**Acceptance Criteria:**
- All gate outcomes logged with timestamp, user, justification
- Audit log is append-only (no deletes/edits)
- Session lifecycle events logged
- Test coverage >80%

**Estimated Effort:** 3-5 days

**Audit Log Schema:**
```json
// .ai-engineering/state/audit.log (JSON lines format)
{"timestamp":"2026-02-08T12:34:56Z","event":"session_start","session_id":"sess_123","user":"soydachi","branch":"feature/xyz"}
{"timestamp":"2026-02-08T12:45:00Z","event":"gate_approval","gate":"pre_commit","operation":"commit","files":["src/main.py"],"approved":true,"justification":"Standard commit"}
{"timestamp":"2026-02-08T12:46:00Z","event":"gate_override","gate":"pre_push","operation":"push","user":"soydachi","justification":"Emergency hotfix"}
{"timestamp":"2026-02-08T14:00:00Z","event":"session_end","session_id":"sess_123","duration_seconds":5160}
```

---

### Epic 4: Quality and Diagnostics

#### Module 4.1: Standards Validation (P1)
**Objective:** Validate manifest schema and standards

**Tasks:**
- Add `ai standards validate` command
- Implement schema validation (YAML structure, required fields)
- Add linting for common mistakes (e.g., invalid regex patterns)
- Clear error messages with suggestions

**Dependencies:** Manifest Parser

**Acceptance Criteria:**
- `ai standards validate` detects schema violations
- Error messages show line numbers and suggestions
- Validation runs automatically on manifest load
- Test coverage >85%

**Estimated Effort:** 3-4 days

---

#### Module 4.2: Doctor Command (P1)
**Objective:** Diagnose common issues

**Tasks:**
- Implement `ai doctor` command
- Check for:
  - Git repository detection
  - Manifest schema validity
  - Git hooks installed correctly
  - Writable state directory
  - Remote standards reachability (if configured)
- Provide fix suggestions

**Dependencies:** All prior modules

**Acceptance Criteria:**
- `ai doctor` runs all checks and reports status
- Clear pass/fail indicators
- Actionable fix suggestions
- Test coverage >75%

**Estimated Effort:** 4-6 days

---

## Module Dependencies (Gantt-style)

```
Week 1-2:
  [CLI Scaffolding] ────────────┐
  [Manifest Parser] ────────────┤ (parallel)
                                ↓
Week 2-3:
  [State Manager] ──────────────┐
  [Standards Resolver] ─────────┤
                                ↓
Week 3-4:
  [Installer] ──────────────────┐
  [Gate Engine] ────────────────┤
                                ↓
Week 4-5:
  [Context Optimizer] ──────────┐
  [Audit Logger] ───────────────┤
                                ↓
Week 5-6:
  [Standards Validation] ───────┐
  [Doctor Command] ─────────────┤
                                ↓
Week 6:
  [Integration Testing]
  [Documentation]
  [Dogfooding Validation]
```

---

## Risk Mitigation Strategies

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| **Git hook conflicts** | Medium | Detect existing hooks; chain with ai-engineering hooks; clear warnings |
| **Cross-OS issues (macOS vs Linux)** | Medium | E2E tests on both platforms; defer Windows to Phase 3 |
| **State corruption from concurrent sessions** | Low | Atomic file writes; file locking; validation on load |
| **Manifest schema evolution breaks repos** | Medium | Schema versioning; migration scripts; backward compatibility tests |
| **Token budget optimization inaccurate** | Medium | Start with conservative estimates; iterate based on real usage |

---

## Definition of Done (Phase 1)

### Feature-Level DoD:
- [ ] All P0 modules implemented and unit tested (>80% coverage)
- [ ] All P0 commands functional and integration tested
- [ ] Dogfooding: ai-engineering repo managed by framework
- [ ] Pre-commit hooks block ungated destructive operations
- [ ] Session state persisted and queryable
- [ ] Manifest schema validated and documented
- [ ] Cross-OS testing (macOS and Linux) passing

### Documentation DoD:
- [ ] Installation guide (README.md)
- [ ] Command reference (CLI help + docs/)
- [ ] Migration guide (from ADO, CLAUDE.md, etc.)
- [ ] Architecture decision records for key choices

### Quality DoD:
- [ ] Zero critical bugs blocking daily use
- [ ] Test coverage >80% overall
- [ ] All P0 E2E tests passing
- [ ] Linting and formatting enforced by framework itself

### Release DoD:
- [ ] Version 0.1.0 tagged and released
- [ ] PyPI package published (or alternate distribution)
- [ ] Changelog published
- [ ] Announcement and feedback collection plan

---

## Verification Checkpoints

### Checkpoint 1 (End of Week 2):
- [ ] CLI scaffolding complete
- [ ] Manifest parser functional
- [ ] Basic tests passing

### Checkpoint 2 (End of Week 4):
- [ ] State manager functional
- [ ] Standards resolver working with layered precedence
- [ ] Installer can bootstrap `.ai-engineering/`
- [ ] Git hooks installed

### Checkpoint 3 (End of Week 5):
- [ ] Gate engine blocking destructive operations
- [ ] Context optimizer respecting token budget
- [ ] Audit logger capturing all operations

### Checkpoint 4 (End of Week 6):
- [ ] All P0 features complete
- [ ] Dogfooding validation passed
- [ ] Documentation complete
- [ ] Ready for 0.1.0 release

---

## Success Metrics (Phase 1)

### Adoption Metrics:
- **Week 1 Post-Release:** ai-engineering repo fully dogfooded
- **Month 1:** 1-2 internal repos using framework
- **Month 2:** 3+ repos, feedback collected

### Quality Metrics:
- **Gate Pass Rate:** 85%+ operations auto-approved (target: 90%+)
- **Context Load Time:** <15s for typical repo (target: <10s in Phase 2)
- **Installation Success Rate:** 95%+ (minimal errors)

### Developer Experience:
- **Time to First Commit:** <10 min from install (target: <5 min)
- **Developer Satisfaction:** >3.5/5 (target: >4.0/5 in Phase 2)

---

## Open Questions (Parking Lot)

### Pre-Implementation:
- ❓ **CLI Framework:** Typer vs Click? (Lean: Typer for type safety)
- ❓ **Installer Distribution:** PyPI vs brew vs curl script? (Start: PyPI)
- ❓ **Minimum Python Version:** 3.9 or 3.11? (Lean: 3.9 for compatibility)

### During Implementation:
- ❓ **Token Estimation:** Use tiktoken library or simple heuristic? (Start: heuristic, iterate)
- ❓ **Cache Storage:** Files vs SQLite? (Start: files for simplicity)
- ❓ **Audit Log Format:** JSON lines vs SQLite? (Start: JSON lines for simplicity)

---

## Next Steps

1. **Finalize Phase 1 backlog** (this document review)
2. **Set up Python project structure**
3. **Create Phase 1 sprint plan** (2-week sprints)
4. **Begin Module 1.1: CLI Scaffolding**
5. **Daily standups during implementation**
6. **Weekly checkpoint reviews**

---

## References

- [Architecture Document](./architecture.md)
- [Discovery Findings](./discovery.md)
- [Verification Strategy](./verification.md)
- [Epic Backlog](../backlog/epics.md)
