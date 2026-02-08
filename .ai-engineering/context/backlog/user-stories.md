# User Stories

## Purpose

This document contains **detailed user stories** for sprint planning. User stories break features into user-centric, testable units of work.

**Last Updated:** 2026-02-08 (Phase 0)

---

## User Story Template

```markdown
### US-X.Y.Z: [User Story Title]

**Feature:** Feature X.Y - [Feature Name]
**Priority:** P0 | P1 | P2
**Status:** Not Started | In Progress | Complete
**Owner:** [Name or TBD]
**Sprint:** [Sprint number or TBD]
**Story Points:** [1, 2, 3, 5, 8, 13]

**As a** [persona]
**I want** [capability]
**So that** [benefit]

**Acceptance Criteria:**
- [ ] Given [context], when [action], then [expected outcome]
- [ ] Given [context], when [action], then [expected outcome]

**Definition of Done:**
- [ ] Code complete and reviewed
- [ ] Unit tests written (>80% coverage)
- [ ] Integration/E2E tests if applicable
- [ ] Documentation updated
- [ ] Accepted by product owner

**Dependencies:**
- [Other user stories this depends on]

**Notes:**
- [Implementation notes, edge cases, etc.]
```

---

## Epic 1: Core CLI and State Management

### US-1.1.1: View Available Commands

**Feature:** Feature 1.1 - CLI Scaffolding
**Priority:** P0
**Status:** Not Started
**Owner:** TBD
**Sprint:** Sprint 1
**Story Points:** 2

**As a** developer
**I want** to run `ai help` and see all available commands
**So that** I can discover framework capabilities without reading docs

**Acceptance Criteria:**
- [ ] Given framework is installed, when I run `ai help`, then I see a list of all commands with brief descriptions
- [ ] Given I want command details, when I run `ai help <command>`, then I see command-specific help with examples
- [ ] Given I use an invalid command, when I run `ai invalid`, then I see "Unknown command: invalid. Run 'ai help' for available commands."

**Definition of Done:**
- [ ] Code complete and reviewed
- [ ] Unit tests for help text generation
- [ ] E2E test verifying help output
- [ ] Help text reviewed for clarity

**Dependencies:**
- None

**Notes:**
- Help text should be concise but informative
- Use examples for complex commands

---

### US-1.1.2: Check Framework Version

**Feature:** Feature 1.1 - CLI Scaffolding
**Priority:** P0
**Status:** Not Started
**Owner:** TBD
**Sprint:** Sprint 1
**Story Points:** 1

**As a** developer
**I want** to run `ai --version` to see the framework version
**So that** I can verify I'm using the correct version

**Acceptance Criteria:**
- [ ] Given framework is installed, when I run `ai --version`, then I see version string (e.g., "ai-engineering 0.1.0")
- [ ] Given framework is installed, when I run `ai version`, then I see the same version output

**Definition of Done:**
- [ ] Code complete and reviewed
- [ ] Version string sourced from `pyproject.toml`
- [ ] E2E test verifying version output

**Dependencies:**
- None

**Notes:**
- Version should be single source of truth from pyproject.toml

---

### US-1.2.1: Start AI Session

**Feature:** Feature 1.2 - Session State Management
**Priority:** P0
**Status:** Not Started
**Owner:** TBD
**Sprint:** Sprint 1
**Story Points:** 5

**As a** developer
**I want** to start a session with `ai session start`
**So that** the AI understands my project context

**Acceptance Criteria:**
- [ ] Given I'm in a git repo, when I run `ai session start`, then a new session is created with unique ID
- [ ] Given session is created, when I check `.ai-engineering/state/session.json`, then it contains session metadata (ID, start time, branch, user)
- [ ] Given session is created, when I run `ai session status`, then I see "Active session: <session-id>, started <time ago>"
- [ ] Given I'm not in a git repo, when I run `ai session start`, then I see error "Not a git repository"
- [ ] Given a session is already active, when I run `ai session start`, then I see error "Session already active. End or pause first."

**Definition of Done:**
- [ ] Code complete and reviewed
- [ ] Unit tests for session creation logic
- [ ] Integration tests for file system persistence
- [ ] E2E test for full workflow

**Dependencies:**
- US-1.1.1 (CLI scaffolding)

**Notes:**
- Session ID format: `sess_YYYYMMDD_HHMMSS`
- Store session in `.ai-engineering/state/session.json`

---

### US-1.2.2: End AI Session

**Feature:** Feature 1.2 - Session State Management
**Priority:** P0
**Status:** Not Started
**Owner:** TBD
**Sprint:** Sprint 1
**Story Points:** 3

**As a** developer
**I want** to end a session with `ai session end`
**So that** my work is logged and context is released

**Acceptance Criteria:**
- [ ] Given active session, when I run `ai session end`, then session is marked as ended
- [ ] Given session ended, when I check `.ai-engineering/state/history.json`, then session summary is appended
- [ ] Given session ended, when I run `ai session status`, then I see "No active session"
- [ ] Given no active session, when I run `ai session end`, then I see error "No active session to end"

**Definition of Done:**
- [ ] Code complete and reviewed
- [ ] Unit tests for session ending logic
- [ ] Integration tests for history append
- [ ] E2E test verifying session lifecycle

**Dependencies:**
- US-1.2.1 (Start session)

**Notes:**
- Session summary includes: ID, duration, commits, gates passed

---

### US-1.2.3: Pause and Resume Sessions

**Feature:** Feature 1.2 - Session State Management
**Priority:** P1
**Status:** Not Started
**Owner:** TBD
**Sprint:** Sprint 2
**Story Points:** 5

**As a** developer
**I want** to pause and resume sessions when switching tasks
**So that** I can maintain multiple session contexts

**Acceptance Criteria:**
- [ ] Given active session, when I run `ai session pause`, then session status changes to "paused"
- [ ] Given paused session, when I run `ai session resume`, then session becomes active again with same ID and context
- [ ] Given paused session, when I run `ai session start`, then I can start a new session (paused one remains paused)
- [ ] Given multiple paused sessions, when I run `ai session resume --id <session-id>`, then specific session is resumed

**Definition of Done:**
- [ ] Code complete and reviewed
- [ ] Unit tests for pause/resume logic
- [ ] E2E test for pause → new session → resume workflow

**Dependencies:**
- US-1.2.1 (Start session)

**Notes:**
- Support multiple paused sessions (stack-based or ID-based)

---

### US-1.3.1: View Session History

**Feature:** Feature 1.3 - History Tracking
**Priority:** P0
**Status:** Not Started
**Owner:** TBD
**Sprint:** Sprint 2
**Story Points:** 3

**As a** developer
**I want** to see my recent session history with `ai history`
**So that** I can track my AI-assisted work

**Acceptance Criteria:**
- [ ] Given completed sessions, when I run `ai history`, then I see last 10 sessions with summary (ID, start/end time, branch, commits)
- [ ] Given I want more history, when I run `ai history --limit 20`, then I see last 20 sessions
- [ ] Given no session history, when I run `ai history`, then I see "No session history found"

**Definition of Done:**
- [ ] Code complete and reviewed
- [ ] Unit tests for history query logic
- [ ] E2E test verifying history output

**Dependencies:**
- US-1.2.2 (End session, which creates history)

**Notes:**
- History read from `.ai-engineering/state/history.json`

---

## Epic 2: Mandatory Local Enforcement

### US-2.1.1: Quick Framework Installation

**Feature:** Feature 2.1 - Installer and Migration
**Priority:** P0
**Status:** Not Started
**Owner:** TBD
**Sprint:** Sprint 2
**Story Points:** 8

**As a** developer
**I want** to install the framework in <5 minutes
**So that** I can start using it without complex setup

**Acceptance Criteria:**
- [ ] Given fresh git repo, when I run `ai install`, then `.ai-engineering/` structure is created in <30 seconds
- [ ] Given installation complete, when I run `git commit`, then pre-commit hook executes
- [ ] Given installation complete, when I run `ai status`, then I see "Framework installed successfully"
- [ ] Given I re-run `ai install`, then I see "Framework already installed" and no data is lost (idempotent)

**Definition of Done:**
- [ ] Code complete and reviewed
- [ ] Unit tests for installer logic
- [ ] E2E test on fresh repo
- [ ] Installation time benchmarked (<30s target)

**Dependencies:**
- US-1.1.1 (CLI scaffolding)

**Notes:**
- Create: `.ai-engineering/manifest.yml`, `state/`, `context/`
- Install git hooks: `.git/hooks/pre-commit`, `pre-push`, `post-commit`

---

### US-2.1.2: Migrate Existing ADO Config

**Feature:** Feature 2.1 - Installer and Migration
**Priority:** P0
**Status:** Not Started
**Owner:** TBD
**Sprint:** Sprint 3
**Story Points:** 5

**As a** platform engineer
**I want** existing ADO config automatically migrated
**So that** I don't lose current governance setup

**Acceptance Criteria:**
- [ ] Given repo with `.azuredevops/ai-engineering.yml`, when I run `ai install`, then migration prompt is shown
- [ ] Given I approve migration, when installation completes, then ADO config is merged into `manifest.yml`
- [ ] Given migration complete, when I check `manifest.yml`, then all ADO standards are preserved
- [ ] Given I decline migration, when installation completes, then default manifest is created (ADO config ignored)

**Definition of Done:**
- [ ] Code complete and reviewed
- [ ] Unit tests for ADO config parsing
- [ ] E2E test with sample ADO config
- [ ] Migration tested with real-world ADO configs

**Dependencies:**
- US-2.1.1 (Installation)
- US-2.2.1 (Manifest schema)

**Notes:**
- Support common ADO config patterns
- Preserve original `.azuredevops/` files (don't delete)

---

### US-2.2.1: Validate Manifest Schema

**Feature:** Feature 2.2 - Manifest Schema and Validation
**Priority:** P0
**Status:** Not Started
**Owner:** TBD
**Sprint:** Sprint 2
**Story Points:** 5

**As a** developer
**I want** clear error messages when my manifest is invalid
**So that** I can fix configuration issues quickly

**Acceptance Criteria:**
- [ ] Given valid manifest, when I run `ai standards validate`, then I see "Manifest is valid ✓"
- [ ] Given invalid YAML, when I run `ai standards validate`, then I see error with line number and specific issue
- [ ] Given missing required field, when framework loads manifest, then I see error "Missing required field: standards"
- [ ] Given invalid field type, when framework loads manifest, then I see error with expected vs actual type

**Definition of Done:**
- [ ] Code complete and reviewed
- [ ] Unit tests for validation logic
- [ ] Test matrix: valid manifest, invalid YAML, missing fields, type mismatches
- [ ] Error messages reviewed for clarity

**Dependencies:**
- None (can be parallel)

**Notes:**
- Use pydantic or jsonschema for validation
- Error messages should suggest fixes

---

### US-2.3.1: Resolve Layered Standards

**Feature:** Feature 2.3 - Standards Resolution
**Priority:** P0
**Status:** Not Started
**Owner:** TBD
**Sprint:** Sprint 3
**Story Points:** 8

**As a** platform engineer
**I want** org-wide standards with repo-level overrides
**So that** I can enforce consistency while allowing flexibility

**Acceptance Criteria:**
- [ ] Given org standard `max_tokens: 8000` and repo override `max_tokens: 5000`, when I run `ai standards show`, then I see `max_tokens: 5000` (repo wins)
- [ ] Given org `ignore_patterns: ["*.log"]` and repo `ignore_patterns: ["*.pyc"]`, when I run `ai standards show`, then I see both patterns combined
- [ ] Given standard defined in multiple layers, when I run `ai standards show`, then layer attribution is shown (e.g., "max_tokens: 5000 (source: repo)")

**Definition of Done:**
- [ ] Code complete and reviewed
- [ ] Unit tests for all merge scenarios (scalars, lists, dicts)
- [ ] Integration tests with multi-layer manifests
- [ ] E2E test verifying precedence

**Dependencies:**
- US-2.2.1 (Manifest schema)

**Notes:**
- Precedence: local > repo > team > org > defaults
- See architecture.md for merge semantics

---

### US-2.4.1: Block Commits with Secrets

**Feature:** Feature 2.4 - Gate Enforcement
**Priority:** P0
**Status:** Not Started
**Owner:** TBD
**Sprint:** Sprint 3
**Story Points:** 8

**As a** security engineer
**I want** to block commits with secrets (.env, .pem, etc.)
**So that** credentials are never accidentally committed

**Acceptance Criteria:**
- [ ] Given staged `.env` file, when I run `git commit`, then commit is blocked with error "Sensitive file detected: .env"
- [ ] Given staged `credentials.json`, when I run `git commit`, then commit is blocked
- [ ] Given clean commit (no secrets), when I run `git commit`, then commit succeeds
- [ ] Given gate blocked commit, when I run `git commit --no-verify`, then commit succeeds but override is logged

**Definition of Done:**
- [ ] Code complete and reviewed
- [ ] Unit tests for sensitive file detection
- [ ] Integration tests with git hooks
- [ ] E2E test verifying gate enforcement

**Dependencies:**
- US-2.3.1 (Standards resolution for gate config)
- US-1.2.1 (Session for audit logging)

**Notes:**
- Sensitive patterns: `.env`, `.pem`, `credentials.*`, etc.
- Configurable in manifest

---

### US-2.4.2: Approve Destructive Operations

**Feature:** Feature 2.4 - Gate Enforcement
**Priority:** P0
**Status:** Not Started
**Owner:** TBD
**Sprint:** Sprint 4
**Story Points:** 5

**As a** developer
**I want** clear prompts when gates block my commits
**So that** I understand why and can approve if legitimate

**Acceptance Criteria:**
- [ ] Given destructive operation detected, when gate runs, then user is prompted: "Destructive operation detected: <operation>. Proceed? (y/n)"
- [ ] Given user approves (y), when gate completes, then operation proceeds and approval is logged
- [ ] Given user denies (n), when gate completes, then operation is blocked
- [ ] Given user provides justification, when approval is logged, then justification is included

**Definition of Done:**
- [ ] Code complete and reviewed
- [ ] Unit tests for approval prompt logic
- [ ] E2E test with interactive approval

**Dependencies:**
- US-2.4.1 (Gate enforcement basics)

**Notes:**
- Approval should include timestamp, user, justification

---

## User Story Tracking

### How to Add User Stories

1. Copy template above
2. Fill in all sections
3. Link to parent feature
4. Add story points (use Fibonacci: 1, 2, 3, 5, 8, 13)
5. Add to sprint backlog when ready

### Story Point Guidelines

- **1 point:** Trivial change (<2 hours)
- **2 points:** Simple feature (2-4 hours)
- **3 points:** Standard feature (4-8 hours, ~1 day)
- **5 points:** Complex feature (1-2 days)
- **8 points:** Very complex (2-3 days)
- **13 points:** Epic-sized (split into smaller stories)

### Story Status Definitions

- **Not Started:** Defined but not in active sprint
- **In Progress:** Currently being developed
- **Complete:** All acceptance criteria met, DoD satisfied
- **Blocked:** Waiting on dependency

---

## References

- [Feature Backlog](./features.md) - Feature-level planning
- [Epic Backlog](./epics.md) - High-level epic definitions
- [Planning Document](../delivery/planning.md) - Sprint planning details
