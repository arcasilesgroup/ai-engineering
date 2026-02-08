# .ai-engineering Directory

## Overview

This directory contains the **complete governance and context structure** for the ai-engineering framework. It serves as both the product specification AND the example implementation that users will replicate in their own repositories.

**Purpose:**
- **Single source of truth** for all project decisions, architecture, and planning
- **Living documentation** that evolves with the project
- **Dogfooding example** demonstrating the framework's own governance model
- **Onboarding resource** for new contributors

---

## Directory Structure

```
.ai-engineering/
├── README.md                    # This file - structure overview
├── context/                     # Project context and governance
│   ├── product/                 # Product vision and roadmap
│   │   ├── vision.md            # Problem, goals, personas, principles
│   │   └── roadmap.md           # Phased delivery plan
│   ├── delivery/                # Delivery process and standards
│   │   ├── discovery.md         # Requirements, risks, constraints
│   │   ├── architecture.md      # System design and modules
│   │   ├── planning.md          # Phase 1 detailed plan
│   │   ├── implementation.md    # Living implementation log
│   │   ├── review.md            # Code review standards
│   │   ├── verification.md      # Testing and validation strategy
│   │   ├── testing.md           # Test types and coverage
│   │   └── iteration.md         # Feedback loops and improvement
│   ├── backlog/                 # Work breakdown and tracking
│   │   ├── epics.md             # High-level epics
│   │   ├── features.md          # Feature breakdown
│   │   ├── user-stories.md      # User story details
│   │   └── tasks.md             # Granular task tracking
│   └── learnings.md             # Retrospectives and insights
├── state/                       # Runtime state (created by framework)
│   ├── session.json             # Current session state
│   ├── history.json             # Session history
│   └── audit.log                # Append-only audit trail
├── standards/                   # Optional detailed standards
│   └── (future - Phase 1+)
├── local.yml                    # Local overrides (gitignored)
└── manifest.yml                 # Canonical configuration
```

---

## File Purposes

### Product Context

| File | Purpose | Update Frequency |
|------|---------|------------------|
| **vision.md** | Product vision, problem statement, goals, personas | Quarterly or when strategy shifts |
| **roadmap.md** | Phased delivery plan with milestones | Monthly or at phase boundaries |

### Delivery Context

| File | Purpose | Update Frequency |
|------|---------|------------------|
| **discovery.md** | Requirements, constraints, risks, decisions | Weekly during discovery; monthly after |
| **architecture.md** | System design, modules, ownership model | Weekly during Phase 1; as needed after |
| **planning.md** | Current phase detailed plan | Updated per sprint |
| **implementation.md** | Daily progress log, blockers, decisions | Daily during active development |
| **review.md** | Code review criteria, quality gates | Monthly or when process changes |
| **verification.md** | E2E test matrix, acceptance criteria | Updated per phase |
| **testing.md** | Test strategy, coverage requirements | Updated per phase |
| **iteration.md** | Retrospective process, feedback loops | Quarterly or when process evolves |

### Backlog

| File | Purpose | Update Frequency |
|------|---------|------------------|
| **epics.md** | High-level epic definitions | Monthly or at phase boundaries |
| **features.md** | Feature breakdown with acceptance criteria | Weekly during planning |
| **user-stories.md** | User story details for sprint planning | Updated per sprint |
| **tasks.md** | Granular task tracking (active sprint) | Daily during sprint execution |

### Living Documents

| File | Purpose | Update Frequency |
|------|---------|------------------|
| **learnings.md** | Retrospectives, insights, adaptations | Continuous (add immediately when learned) |

---

## How to Use This Structure

### For Contributors

1. **Onboarding:** Start with `context/product/vision.md` to understand the "why"
2. **Understanding Design:** Read `context/delivery/architecture.md` for system design
3. **Finding Work:** Check `context/backlog/` for epics, features, and tasks
4. **Daily Work:** Update `context/delivery/implementation.md` with progress
5. **Learning:** Add insights to `learnings.md` immediately

### For Product/Leadership

1. **Strategic Review:** Read `vision.md` and `roadmap.md`
2. **Progress Tracking:** Check `planning.md` for current phase status
3. **Risk Assessment:** Review `discovery.md` risks and `learnings.md` for surprises
4. **Decision Points:** All major decisions documented in `discovery.md` and `architecture.md`

### For AI Agents (Claude, Copilot, etc.)

1. **Context Loading:** Read priority files first (vision, architecture, planning)
2. **Understanding Requirements:** Check `backlog/` for current work
3. **Following Standards:** Respect all standards in `manifest.yml` and `context/delivery/`
4. **Logging Work:** Append to `state/audit.log` for all operations

---

## Context Maintenance

### Daily (During Active Development)
- Update `implementation.md` with progress
- Update task status in `tasks.md`
- Add learnings to `learnings.md` as discovered

### Weekly
- Review and triage new learnings
- Update sprint tasks in `tasks.md`
- Check for stale content (flag in team sync)

### Monthly
- Synthesize learnings (identify patterns)
- Update roadmap if needed
- Review and update risk register in `discovery.md`

### Quarterly
- Deep review of all context docs
- Archive completed phases
- Strategic roadmap adjustments

---

## Key Principles

### 1. Single Source of Truth
- Each concept documented in exactly one place
- Cross-reference instead of duplicating
- If contradictions exist, flag immediately

### 2. Token Efficiency
- Concise, high-signal content (no fluff)
- Use tables, lists, and structure (easier to scan)
- Progressive disclosure (priority files first)

### 3. Living Documentation
- Update context as decisions are made (don't wait)
- Archive old content (don't delete, just mark superseded)
- Learnings feed back into context (continuous improvement)

### 4. Actionable Content
- Every document should enable action
- Clear acceptance criteria and DoD
- No vague "nice to haves" - prioritize ruthlessly

---

## Phase 0 Status (Current)

**Objective:** Initialize complete context structure before implementation

**Status:** ✅ **COMPLETE**

**Deliverables:**
- [x] All context files created and populated
- [x] Product vision and roadmap defined
- [x] Architecture complete with ownership model
- [x] Phase 1 planning detailed with backlog
- [x] Verification strategy with E2E matrix
- [x] Learnings structure initialized

**Next Steps:**
1. Commit Phase 0 context as foundation
2. Begin Phase 1: MVP Core Framework implementation
3. Dogfood framework in this repo from day one

---

## Quick Links

### Start Here
- [Product Vision](context/product/vision.md) - Why this project exists
- [Roadmap](context/product/roadmap.md) - Phased delivery plan
- [Architecture](context/delivery/architecture.md) - How it works

### For Developers
- [Planning](context/delivery/planning.md) - What to build next
- [Epics](context/backlog/epics.md) - High-level features
- [Tasks](context/backlog/tasks.md) - Granular work items

### For Quality
- [Testing Strategy](context/delivery/testing.md) - How to test
- [Verification](context/delivery/verification.md) - Acceptance criteria
- [Review Standards](context/delivery/review.md) - Quality gates

### For Continuous Improvement
- [Learnings](context/learnings.md) - What we've learned
- [Iteration Process](context/delivery/iteration.md) - How we improve

---

## Contributing

When contributing to this project, please:

1. **Read context first:** Understand vision, architecture, and current plan
2. **Follow standards:** All standards in `context/delivery/` apply
3. **Update context:** If you change architecture or plans, update docs
4. **Add learnings:** Document surprises and insights immediately
5. **Get review:** All changes to context/ require review (like code)

---

## Questions?

- **About the project:** Read `context/product/vision.md`
- **About architecture:** Read `context/delivery/architecture.md`
- **About current work:** Read `context/delivery/planning.md`
- **About contributing:** Read `context/delivery/review.md`

If still unclear, open an issue or start a discussion.

---

**Last Updated:** 2026-02-08 (Phase 0 completion)
