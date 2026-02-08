# Iteration and Continuous Improvement

## Purpose

This document defines the **feedback loop and continuous improvement process** for the ai-engineering framework. It outlines how we learn from usage, maintain context health, and evolve the framework based on real-world feedback.

**Last Updated:** 2026-02-08 (Phase 0)

---

## Iteration Cadence and Triggers

### Regular Iteration Cycles

| Cycle Type | Frequency | Purpose | Participants |
|-----------|-----------|---------|--------------|
| **Sprint Retrospective** | Every 2 weeks | Review sprint, identify improvements | Core team |
| **Phase Retrospective** | End of each phase | Major learnings, architectural adjustments | Core team + stakeholders |
| **Release Retrospective** | After each release | Validate assumptions, gather user feedback | Core team + early adopters |
| **Quarterly Review** | Every 3 months | Strategic direction, roadmap adjustments | Leadership + product |

### Event-Driven Triggers

Iteration may be triggered by:
- **Critical Bug:** Severity 1 issues requiring immediate response
- **Security Incident:** Any security-related finding
- **Major User Feedback:** Consistent pain points from 3+ users
- **Performance Degradation:** >20% regression in key metrics
- **Breaking Change Needed:** Architectural limitations requiring redesign

---

## Feedback Collection Mechanisms

### 1. Dogfooding Feedback

**Process:**
- Framework maintainers use framework daily for ai-engineering repo development
- Document pain points immediately in `learnings.md`
- Weekly sync to review accumulated feedback
- Prioritize fixes based on frequency and severity

**Feedback Template:**
```markdown
## Dogfooding Feedback: [Issue Summary]
- **Date:** 2026-02-XX
- **User:** [Name]
- **Scenario:** [What were you trying to do?]
- **Pain Point:** [What didn't work well?]
- **Impact:** High | Medium | Low
- **Suggested Fix:** [If any]
- **Workaround:** [If any]
```

---

### 2. User Feedback (Post-MVP)

**Channels:**
- GitHub Issues (bug reports, feature requests)
- Discussions forum (questions, use cases)
- User surveys (quarterly NPS, satisfaction)
- Direct outreach (1:1 interviews with early adopters)

**Survey Template (Quarterly):**
```
1. How satisfied are you with the ai-engineering framework? (1-5)
2. What is the most valuable feature?
3. What is the biggest pain point?
4. How likely are you to recommend to a colleague? (NPS)
5. What feature would you add if you could only add one?
```

---

### 3. Telemetry and KPIs (Opt-In)

**Metrics Tracked:**
- Command usage frequency (which commands are most/least used)
- Gate pass/fail rates (identify false positives)
- Context load times (performance tracking)
- Error rates by command (stability tracking)
- Session duration and frequency (usage patterns)

**Privacy:**
- **Opt-in only:** Users must explicitly enable telemetry
- **No sensitive data:** No file names, code content, or credentials collected
- **Aggregated only:** Individual usage not tracked, only aggregate stats
- **Transparent:** Clear documentation of what's collected and why

**Opt-in Prompt:**
```
Would you like to help improve ai-engineering by sharing anonymous usage data?
We collect:
  - Command usage frequency (e.g., "ai session start" used 10 times/day)
  - Performance metrics (e.g., context load time: 8s)
  - Error rates (e.g., "ai install" failed 2% of the time)

We do NOT collect:
  - File names or code content
  - Credentials or secrets
  - Personally identifiable information

Enable telemetry? (y/n)
```

---

### 4. Maintenance Agent Integration (Phase 3)

**Automated Context Health Checks:**
- Stale content detection (unchanged for >90 days with active repo)
- Conflict detection (contradictions between context files)
- Completeness checks (missing required sections)
- Token efficiency analysis (context overhead >30%)

**Agent Actions:**
- Flag issues in `.ai-engineering/state/maintenance_report.md`
- Suggest fixes (e.g., "archive old learnings", "update stale architecture doc")
- Auto-fix low-risk issues (e.g., fix broken internal links)
- Prompt user for high-risk fixes (e.g., remove contradictory content)

**Example Maintenance Report:**
```markdown
# Maintenance Report: 2026-03-15

## Issues Detected

### High Priority
- **Stale Content:** `context/delivery/architecture.md` last updated 90 days ago, but 15 commits since then
  - **Suggestion:** Review and update to reflect recent changes
  - **Auto-fix:** No (requires human review)

### Medium Priority
- **Broken Link:** `context/product/roadmap.md` links to non-existent `../delivery/sprint-plan.md`
  - **Suggestion:** Update link to `planning.md`
  - **Auto-fix:** Yes (link updated)

### Low Priority
- **Token Efficiency:** Context load using 9500/8000 tokens (19% over budget)
  - **Suggestion:** Review `priority_files` list; remove rarely accessed files
  - **Auto-fix:** No (requires judgment)

## Actions Taken
- Fixed broken link in roadmap.md
- Flagged stale architecture.md for manual review
```

---

## Retrospective Format

### Sprint Retrospective (Every 2 Weeks)

**Agenda (30 minutes):**

1. **What Went Well (10 min)**
   - Celebrate wins
   - Identify successful patterns to repeat

2. **What Didn't Go Well (10 min)**
   - Identify pain points
   - No blame, focus on process improvement

3. **Action Items (10 min)**
   - Concrete, actionable improvements
   - Owner assigned for each
   - Due date set

**Output:** Action items added to next sprint backlog

**Template:**
```markdown
# Sprint Retrospective: Sprint X (2026-02-XX to 2026-02-XX)

## What Went Well
- ✅ All P0 modules completed on time
- ✅ Test coverage exceeded 85% target
- ✅ Dogfooding revealed only minor issues

## What Didn't Go Well
- ❌ Cross-OS testing blocked by Linux CI setup issues
- ❌ Gate false positive rate 15% (target: <5%)
- ❌ Context load time 18s (target: <15s)

## Action Items
- [ ] **Fix CI:** Set up Linux runner for cross-OS testing (Owner: Alice, Due: 2026-02-20)
- [ ] **Reduce False Positives:** Review gate detection logic for common false positives (Owner: Bob, Due: 2026-02-22)
- [ ] **Optimize Context:** Profile context loading to identify bottlenecks (Owner: Charlie, Due: 2026-02-25)

## Learnings to Document
- Gate logic needs more nuance (not just binary block/allow)
- Token estimation heuristic too conservative (overestimates by ~20%)
```

---

### Phase Retrospective (End of Phase 1, 2, 3)

**Agenda (90 minutes):**

1. **Phase Goals Review (15 min)**
   - Did we meet phase objectives?
   - What was in/out of scope?

2. **Metrics Review (15 min)**
   - Adoption, quality, performance, DevEx metrics
   - Compare actual vs targets

3. **Deep Dive: What We Learned (30 min)**
   - Architectural decisions that worked/didn't work
   - User feedback themes
   - Technical challenges and how we overcame them

4. **Roadmap Adjustments (20 min)**
   - Should next phase scope change?
   - New priorities based on learnings?

5. **Action Items (10 min)**
   - Updates to architecture, planning, or roadmap docs
   - Process improvements

**Output:** Updated learnings.md, roadmap adjustments, next phase kickoff plan

---

## How Learnings Feed Back into Context

### Learning → Context Update Flow

```
1. Identify learning (from retrospective, dogfooding, user feedback)
   ↓
2. Categorize learning:
   - Technical (code, architecture, performance)
   - Process (development workflow, testing, review)
   - Product (user needs, feature gaps)
   - Organizational (team dynamics, communication)
   ↓
3. Document in learnings.md with context:
   - What we learned
   - Why it matters
   - How we're adapting
   ↓
4. Update relevant context files:
   - Architecture decision? → Update architecture.md
   - Planning estimate wrong? → Update planning.md estimates
   - New risk identified? → Update discovery.md risks
   - Feature request? → Update backlog epics/features
   ↓
5. Communicate changes:
   - Announce in team sync
   - Update affected stakeholders
   - Document in CHANGELOG (if user-facing)
```

### Example Learning Flow

**Learning:**
> "Token estimation using `chars / 4` heuristic is too conservative, overestimates by ~20%. Users hitting token budget unnecessarily."

**Updates:**
1. **learnings.md:** Document finding with data
2. **architecture.md:** Update context optimization section with refined heuristic (use `chars / 3.5`)
3. **testing.md:** Add performance test to validate token estimation accuracy
4. **planning.md:** Adjust estimates for context optimizer module (less effort needed)

---

## Maintenance Agent Design (Phase 3)

### Agent Capabilities

**Autonomous Actions (No Approval Required):**
- Fix broken internal links
- Format markdown files
- Update timestamps in docs
- Regenerate table of contents

**Flagged Actions (Requires Approval):**
- Archive stale content (>90 days old, inactive)
- Resolve contradictions (conflicting statements in docs)
- Suggest content consolidation (duplicate info across files)
- Prune oversized context (token budget violations)

### Agent Schedule

| Task | Frequency | Trigger |
|------|-----------|---------|
| **Link Check** | Daily | Automated |
| **Stale Detection** | Weekly | Automated |
| **Conflict Detection** | Weekly | Automated |
| **Token Budget Check** | On commit | Git hook |
| **Comprehensive Audit** | Monthly | Scheduled |

### Agent Feedback Loop

```
1. Agent runs scheduled checks
   ↓
2. Generates maintenance report
   ↓
3. Auto-fixes low-risk issues
   ↓
4. Flags high-risk issues for human review
   ↓
5. Human reviews and approves/rejects
   ↓
6. Agent applies approved fixes
   ↓
7. Agent logs actions to audit trail
   ↓
8. Learnings from agent actions → learnings.md
```

---

## Continuous Improvement KPIs

### Framework Health Metrics

| Metric | Target | How Measured | Review Frequency |
|--------|--------|--------------|------------------|
| **Context Staleness** | <10% of files >90 days old | Git last-modified timestamps | Monthly |
| **Broken Links** | 0 broken internal links | Link checker | Weekly |
| **Token Efficiency** | <30% context overhead | Token usage tracking | Per-session |
| **Gate False Positive Rate** | <5% | Gate approval logs | Weekly |
| **Test Coverage** | >80% overall | pytest-cov | Per-commit |

### User Satisfaction Metrics (Post-MVP)

| Metric | Target | How Measured | Review Frequency |
|--------|--------|--------------|------------------|
| **NPS (Net Promoter Score)** | >30 | Quarterly survey | Quarterly |
| **Developer Satisfaction** | >4.0/5 | Quarterly survey | Quarterly |
| **Adoption Rate** | 80% of target repos within 6 months | Usage tracking | Monthly |
| **Time to First Commit** | <5 min from install | Onboarding telemetry (opt-in) | Monthly |

### Performance Metrics

| Metric | Target | How Measured | Review Frequency |
|--------|--------|--------------|------------------|
| **Context Load Time** | <10s (P50), <15s (P95) | Session start telemetry | Weekly |
| **Gate Check Time** | <2s (pre-commit) | Hook execution time | Weekly |
| **Install Time** | <30s | Install telemetry | Monthly |

---

## Periodic Review Schedule

### Weekly (Core Team)
- Review dogfooding feedback from learnings.md
- Triage new GitHub issues
- Review gate false positives
- Check performance metrics

### Bi-Weekly (Sprint Boundary)
- Sprint retrospective
- Update iteration.md with action items
- Adjust next sprint backlog based on learnings

### Monthly
- Review user satisfaction metrics (if available)
- Maintenance agent comprehensive audit
- Update roadmap if significant learnings

### Quarterly
- User survey and NPS measurement
- Phase retrospective (if phase boundary)
- Strategic roadmap review
- Stakeholder sync

---

## Learnings Synthesis Process

### From learnings.md to Actionable Insights

**Monthly Synthesis (30 minutes):**

1. **Review all learnings** added in past month
2. **Identify patterns:** Are there recurring themes?
3. **Prioritize top 3-5** highest-impact learnings
4. **Create action plan:**
   - Quick wins (can fix in current sprint)
   - Medium-term (add to next phase backlog)
   - Long-term (roadmap adjustment)
5. **Update context files** as needed
6. **Communicate** synthesis to team and stakeholders

**Output:** Synthesized learnings summary, action plan, context updates

---

## References

- [Learnings Document](../learnings.md) - Living retrospective log
- [Architecture Document](./architecture.md) - System design
- [Planning Document](./planning.md) - Implementation plan
- [Roadmap](../product/roadmap.md) - Strategic plan
