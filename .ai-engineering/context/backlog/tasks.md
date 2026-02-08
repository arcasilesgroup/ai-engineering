# Tasks

## Purpose

This document contains **granular task-level tracking** for the active sprint/phase. Tasks are the smallest unit of work, typically completed in hours rather than days.

**Last Updated:** 2026-02-08 (Phase 0)

---

## Task Template

```markdown
### TASK-XXX: [Task Title]

**User Story:** US-X.Y.Z - [User Story Title]
**Status:** Todo | In Progress | Blocked | Done
**Owner:** [Name]
**Estimated Hours:** [1-8 hours]
**Actual Hours:** [Fill when complete]
**Created:** YYYY-MM-DD
**Completed:** YYYY-MM-DD

**Description:**
[1-2 sentence description of the task]

**Subtasks:**
- [ ] Subtask 1
- [ ] Subtask 2

**Blockers:**
- [Any blockers preventing completion]

**Notes:**
- [Implementation notes, decisions made, etc.]
```

---

## Active Sprint Tasks

**Sprint:** TBD (Phase 1 Sprint 1)
**Sprint Goal:** [Will be defined when Phase 1 begins]
**Sprint Dates:** TBD

### Sprint Backlog

*(Tasks will be added here when sprints are planned)*

**Example:**

```markdown
### TASK-001: Set up Python project structure

**User Story:** US-1.1.1 - View Available Commands
**Status:** Todo
**Owner:** TBD
**Estimated Hours:** 2
**Actual Hours:** -
**Created:** 2026-02-08
**Completed:** -

**Description:**
Initialize Python project with pyproject.toml, src/ and tests/ directories, and configure development dependencies.

**Subtasks:**
- [ ] Create pyproject.toml with project metadata
- [ ] Set up src/ai_engineering/ package structure
- [ ] Create tests/ directory with conftest.py
- [ ] Configure poetry for dependency management
- [ ] Add dev dependencies: pytest, ruff, mypy
- [ ] Create README.md with basic project info

**Blockers:**
- None

**Notes:**
- Use Poetry for modern Python dependency management
- Python version: 3.9+ for broad compatibility
```

---

## Task Breakdown Approach

### From User Story to Tasks

1. **Read User Story:** Understand acceptance criteria and DoD
2. **Identify Work Items:** Break story into discrete, testable units
3. **Estimate Hours:** Each task should be 1-8 hours (if >8, split further)
4. **Assign Owner:** One owner per task for accountability
5. **Define Subtasks:** Concrete checklist for task completion

### Example Breakdown

**User Story:** US-1.2.1 - Start AI Session (5 story points)

**Tasks:**
- TASK-010: Define session state schema (2h)
- TASK-011: Implement session creation logic (3h)
- TASK-012: Add file system persistence (4h)
- TASK-013: Implement `ai session start` command (3h)
- TASK-014: Add unit tests for session manager (4h)
- TASK-015: Add E2E test for session start workflow (3h)

**Total:** 19 hours ≈ 2.5 days ≈ 5 story points ✓

---

## Task States

### State Definitions

- **Todo:** Task defined but not started
- **In Progress:** Actively being worked on
- **Blocked:** Cannot proceed due to dependency or issue
- **Done:** Complete, tested, and reviewed

### State Transitions

```
Todo → In Progress → Done
         ↓
      Blocked → In Progress
```

### Guidelines

- **Move to In Progress:** When you start working (only 1-2 tasks in progress per person)
- **Move to Blocked:** Immediately when you encounter a blocker (document blocker)
- **Move to Done:** When all subtasks complete, code reviewed, and tests passing

---

## Task Assignment and Ownership

### Assignment Rules

1. **One Owner:** Each task has exactly one owner (for accountability)
2. **Self-Assignment:** Team members pull tasks from Todo based on priority and skills
3. **Capacity Limit:** No more than 2 tasks In Progress per person at once
4. **Pairing Allowed:** Owner responsible even if pairing with others

### Tracking Ownership

| Task ID | Owner | Status | Est Hours | Actual Hours |
|---------|-------|--------|-----------|--------------|
| TASK-001 | TBD | Todo | 2 | - |
| TASK-002 | TBD | Todo | 3 | - |

*(This table will be populated during active sprints)*

---

## How to Record Task Completion

### When Marking Task as Done

1. **Update Status:** Change from "In Progress" to "Done"
2. **Record Actual Hours:** Fill in actual time spent
3. **Complete Notes:** Document any deviations, learnings, or decisions
4. **Link to PR:** Include PR number for traceability
5. **Update User Story:** If last task for story, update story status

### Completion Template

```markdown
### TASK-XXX: [Task Title]

**Status:** Done ✓
**Actual Hours:** 4 (estimated: 3)
**Completed:** 2026-02-10

**Notes:**
- Task took 1 hour longer than estimated due to unexpected issue with file locking
- Decided to use `fcntl.flock` instead of custom locking implementation
- Learning: File locking is tricky on macOS; added extra tests

**PR:** #42
**Commits:** abc123, def456
```

---

## Task Tracking Best Practices

### Daily Task Updates

- **Morning:** Review task list, pull new task if none In Progress
- **During Work:** Update task status as you progress through subtasks
- **End of Day:** Update notes with progress, blockers, or decisions

### Blocker Management

**When Blocked:**
1. Move task to Blocked state immediately
2. Document blocker in task notes
3. Notify team (standup or async)
4. Pull different task if blocker will take >1 day to resolve

**Example Blocker Note:**
```markdown
**Blockers:**
- Waiting on TASK-015 to complete (session state schema needed)
- ETA: 2 days (owner: Alice, due 2026-02-12)
```

### Task Dependencies

Use task notes to document dependencies:

```markdown
**Dependencies:**
- TASK-010 (session schema) must complete before this task can start
- Blocked until US-2.2.1 (manifest validation) is complete
```

---

## Sprint Planning with Tasks

### Sprint Planning Process

1. **Select User Stories:** Choose stories for sprint based on priority and capacity
2. **Break Down Stories:** Convert stories into tasks
3. **Estimate Tasks:** Estimate hours per task
4. **Validate Capacity:** Ensure total hours ≤ team capacity
5. **Assign Tasks:** Team members self-assign or assign during planning

### Capacity Planning

**Example:**
- Team size: 2 developers
- Sprint length: 2 weeks (10 working days)
- Availability: 80% (20% meetings, support, etc.)
- Capacity: 2 devs × 10 days × 6.4h/day = 128 hours

**Sprint Backlog:**
- User Stories: 5 stories × 5 story points avg = 25 points
- Estimated hours: ~100 hours (leaves 28h buffer)

---

## Task Archive (Completed Sprints)

### Sprint 1 (Planned: 2026-02-XX to 2026-02-XX)

**Status:** Not Started

**Tasks:**
*(Will be populated during sprint)*

---

## Task Metrics and Insights

### Metrics to Track

- **Velocity:** Actual hours per story point (helps refine estimates)
- **Estimation Accuracy:** Actual vs estimated hours (track over/under estimation)
- **Blocker Frequency:** How often tasks get blocked (identify process issues)
- **Completion Rate:** % of tasks completed in sprint (capacity planning accuracy)

### Example Metrics (Post-Sprint)

```markdown
## Sprint 1 Metrics

- **Planned Story Points:** 25
- **Completed Story Points:** 22 (88%)
- **Planned Hours:** 100
- **Actual Hours:** 110 (10% over)
- **Avg Hours per Story Point:** 5 (update future estimates)
- **Tasks Blocked:** 3 (15% of tasks)
- **Velocity:** 4.4 story points per dev per week
```

---

## How to Use This Document

### During Sprint Planning
- Break user stories into tasks
- Estimate and assign tasks
- Validate capacity

### During Sprint Execution
- Pull tasks from Todo backlog
- Update status daily
- Document blockers and notes

### During Sprint Retrospective
- Review completed tasks
- Calculate metrics (velocity, estimation accuracy)
- Archive sprint tasks
- Extract learnings to `learnings.md`

---

## References

- [User Stories](./user-stories.md) - Parent user stories
- [Features](./features.md) - Parent features
- [Planning Document](../delivery/planning.md) - Sprint planning details
- [Implementation Log](../delivery/implementation.md) - Daily progress logs
