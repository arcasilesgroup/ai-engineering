# Learnings and Retrospectives

## Purpose

This is a **living document** that captures key learnings, surprises, and adaptations throughout the ai-engineering framework development. It serves as institutional memory and feeds continuous improvement.

**How to Use:**
- Add learnings immediately when discovered (don't wait for retrospectives)
- Review monthly to identify patterns
- Extract high-impact learnings to update context docs
- Reference during planning to avoid repeating mistakes

---

## Learning Template

```markdown
## [Category] - [Short Title]

**Date:** YYYY-MM-DD
**Phase:** [Phase 0, 1, 2, 3]
**Severity:** Low | Medium | High
**Status:** Active | Resolved | Archived

**Context:**
[What were we doing? What was the situation?]

**What We Learned:**
[What did we discover? What surprised us?]

**Impact:**
[How did this affect the project? Cost, timeline, quality, team?]

**Adaptation:**
[What did we change? How did we respond?]

**Actionable Takeaways:**
- [Concrete lessons for future work]
- [Updates to context docs, if any]

**References:**
- [Links to related issues, PRs, docs]
```

---

## Learning Categories

- **Technical:** Code, architecture, performance, tooling
- **Process:** Development workflow, testing, review, planning
- **Product:** User feedback, requirements, feature design
- **Team:** Collaboration, communication, skills, dynamics
- **Tools:** CI/CD, dependencies, development environment

---

## Phase 0: Context Initialization (Current)

### Technical - Context-First Approach Works

**Date:** 2026-02-08
**Phase:** Phase 0
**Severity:** High
**Status:** Active

**Context:**
We debated whether to start with code (typical approach) or comprehensive context documentation. We chose context-first: complete discovery, architecture, and planning before any implementation.

**What We Learned:**
Context-first initialization provides massive clarity and reduces thrash. Having comprehensive context docs before code means:
- Zero ambiguity about requirements or design
- Immediate execution without re-explaining decisions
- Traceable decisions (all in docs, not lost in chat)
- Framework can dogfood itself from day one (context/ is the product)

**Impact:**
- **Positive:** Planning Phase 1 was straightforward with complete context
- **Positive:** Can onboard new contributors instantly (read context/)
- **Trade-off:** ~8 hours upfront to create context (worth it)

**Adaptation:**
- Document this approach in framework methodology
- Make context initialization a recommended practice for users
- Use this repo as reference example

**Actionable Takeaways:**
- Always create context/ before src/ for non-trivial projects
- Context is not "documentation overhead" - it IS the product foundation
- Invest in context quality; it compounds over time

**References:**
- Phase 0 plan execution (this context/ structure)

---

### Process - Plan Mode Effective for Non-Trivial Work

**Date:** 2026-02-08
**Phase:** Phase 0
**Severity:** Medium
**Status:** Active

**Context:**
User requested implementation of detailed context initialization plan. We used plan mode to explore, design, and finalize the structure before execution.

**What We Learned:**
Plan mode is highly effective for:
- Designing complex structures (prevents premature execution)
- Getting user sign-off before significant work
- Exploring trade-offs and alternatives
- Creating comprehensive, actionable plans

**Impact:**
- Plan received user approval before execution
- Execution is now straightforward (plan is detailed and unambiguous)
- Avoided rework from misaligned expectations

**Adaptation:**
- Use plan mode proactively for multi-file/multi-step tasks
- Encourage framework users to adopt similar planning discipline

**Actionable Takeaways:**
- Plan first, execute second (especially for foundational work)
- Plans should be detailed enough to execute without further clarification
- User sign-off on plans prevents wasted effort

**References:**
- Plan mode conversation prior to this execution

---

## Phase 1: MVP Core Framework (Planned)

*(Learnings will be added here during Phase 1 implementation)*

### Examples of Future Learnings:

```markdown
## Technical - Token Estimation Heuristic Too Conservative

**Date:** TBD
**Phase:** Phase 1
**Severity:** Medium
**Status:** TBD

**Context:**
Implemented context optimizer with `chars / 4` heuristic for token estimation.

**What We Learned:**
Heuristic overestimates tokens by ~20%, causing users to hit token budget unnecessarily. Actual ratio closer to `chars / 3.5` based on testing.

**Impact:**
- Users frustrated by artificial token limits
- Context unnecessarily truncated
- Performance target (10s load time) at risk

**Adaptation:**
- Updated heuristic to `chars / 3.5`
- Added performance test to validate token estimation accuracy
- Documented in architecture.md

**Actionable Takeaways:**
- Validate heuristics with real data early
- Token estimation accuracy is critical for UX
- Add performance tests for key assumptions

**References:**
- Issue #XX: Token estimation too conservative
- PR #YY: Update token heuristic
```

---

## Periodic Learning Synthesis

### Monthly Synthesis (Template)

**Month:** YYYY-MM
**Learnings Added:** X
**Top Patterns Identified:**
1. [Pattern 1]
2. [Pattern 2]
3. [Pattern 3]

**High-Impact Actions:**
- [Action 1 with owner and due date]
- [Action 2 with owner and due date]

**Context Updates:**
- Updated architecture.md: [summary of changes]
- Updated planning.md: [summary of changes]

---

## Learnings Archive

*(Learnings that are no longer active but worth preserving)*

### Archived: [Title]

**Original Date:** YYYY-MM-DD
**Archived Date:** YYYY-MM-DD
**Reason for Archive:** [Resolved, superseded, no longer relevant]

**Summary:** [Brief summary of the learning for historical reference]

---

## How to Add a Learning

1. **Capture Immediately:** Don't wait for retrospectives; document as soon as you learn
2. **Use Template:** Fill in all sections (context, learning, impact, adaptation)
3. **Categorize:** Tag with category and severity
4. **Link:** Reference related issues, PRs, commits
5. **Update Context Docs:** If learning changes architecture/planning, update those docs too

---

## How to Review Learnings

### Weekly Review (Quick Scan)
- Scan new learnings added this week
- Identify any that need immediate action
- Triage severity (High → discuss in team sync)

### Monthly Synthesis (30 min)
- Group learnings by category and pattern
- Identify top 3-5 highest-impact learnings
- Create action plan with owners and due dates
- Update relevant context docs

### Quarterly Review (Deep Dive)
- Review all active learnings
- Archive resolved learnings
- Extract themes for strategic planning
- Present synthesis to stakeholders

---

## Retrospective Prompts

Use these prompts during retrospectives to surface learnings:

### Technical Learnings
- What technical decisions worked well? What didn't?
- What surprised us about the technology/tools?
- What performance/quality issues did we encounter?

### Process Learnings
- What slowed us down? What accelerated us?
- What process changes made a difference?
- What would we do differently next sprint/phase?

### Product Learnings
- What did we learn about user needs?
- What assumptions were validated? Invalidated?
- What feature had unexpected impact (positive or negative)?

### Team Learnings
- What collaboration patterns worked well?
- Where did we struggle with communication?
- What skills do we need to develop?

---

## Learning Metrics

Track these metrics to measure learning effectiveness:

| Metric | Target | How Measured |
|--------|--------|--------------|
| **Learning Capture Rate** | 80%+ of retrospective insights documented | Count learnings vs retro action items |
| **Context Update Rate** | 50%+ of high-impact learnings → context updates | Track learnings with "Updated X.md" tag |
| **Repeat Issue Rate** | <10% issues are repeats of known problems | Track issues linked to existing learnings |
| **Learning Synthesis Frequency** | Monthly | Calendar review |

---

## References

- [Iteration Process](./delivery/iteration.md) - How learnings feed back into context
- [Architecture Document](./delivery/architecture.md) - Technical decisions
- [Planning Document](./delivery/planning.md) - Implementation plan
- [Product Roadmap](./product/roadmap.md) - Strategic direction
