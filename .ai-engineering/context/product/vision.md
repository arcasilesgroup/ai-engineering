# Product Vision

## Problem Statement

AI-powered development teams need **consistent, enforceable governance** across repositories without sacrificing velocity or developer experience. Current solutions fail because they either:

- **Lack enforcement:** Documentation-only standards that agents ignore or misinterpret
- **Require manual oversight:** Context that must be manually assembled per session
- **Don't scale:** Project-specific tools that can't be shared or evolved
- **Bypass security:** AI agents with unrestricted access to sensitive operations

The result: **governance theater** where standards exist but aren't followed, leading to:
- Inconsistent code quality and architecture drift
- Security vulnerabilities from ungated operations
- Knowledge loss when context isn't captured
- Wasted tokens re-explaining policies every session

---

## Product Goals

**Primary Goals:**

1. **Single Source of Truth:** Canonical `.ai-engineering/` structure that defines standards, state, and context
2. **Mandatory Enforcement:** Local gates and hooks that agents cannot bypass
3. **Zero-Config Defaults:** Works out-of-box with progressive disclosure for customization
4. **Cross-Platform:** Consistent behavior on macOS, Linux, Windows
5. **Provider-Agnostic:** Works with Claude, GitHub Copilot, OpenAI, local models
6. **Secure by Default:** Explicit approval gates for destructive/sensitive operations
7. **Token-Efficient:** Optimized context delivery to minimize API costs
8. **Dogfooded:** Framework manages its own governance from day one

**Non-Goals:**

- ❌ Building yet another AI coding assistant (we orchestrate existing ones)
- ❌ Replacing CI/CD pipelines (we complement, not compete)
- ❌ Vendor lock-in to specific AI providers
- ❌ Complex configuration requiring deep expertise

---

## Core Personas

### Platform Engineer
**Needs:** Framework to enforce organization-wide standards without becoming bottleneck
**Pain Points:** Standards drift, inconsistent security posture, agent sprawl
**Success Metric:** 80%+ repos using framework within 6 months

### Team Lead / Engineering Manager
**Needs:** Visibility into AI-driven changes, quality gates, audit trail
**Pain Points:** Invisible AI commits, context loss between sessions, compliance risk
**Success Metric:** Zero security incidents from ungated AI operations

### Developer (AI User)
**Needs:** Fast, unobstructed workflow with AI assistance that "just works"
**Pain Points:** Re-explaining standards every session, manual gate approvals, context fatigue
**Success Metric:** <10s context loading, 90%+ automated gate pass rate

### Security / Compliance
**Needs:** Enforceable policies, audit logs, sensitive operation controls
**Pain Points:** AI agents bypassing approval flows, no trail for compliance review
**Success Metric:** 100% sensitive operations logged and approved

### DevEx / Developer Productivity Owner
**Needs:** Metrics on AI effectiveness, adoption tracking, friction points
**Pain Points:** Black box AI usage, unknown ROI, no telemetry
**Success Metric:** Measurable velocity improvement with framework adoption

---

## Product Principles

### 1. Simple Over Clever
- Prefer obvious YAML over DSLs
- Convention over configuration
- Clear error messages over magic

### 2. Efficient Over Exhaustive
- Token budgets matter
- Progressive context loading (need-to-know)
- Smart caching and deduplication

### 3. Practical Over Perfect
- Ship working MVP over theoretical completeness
- Pragmatic compromises documented in `learnings.md`
- Iterate based on real usage, not speculation

### 4. Robust Over Rigid
- Graceful degradation when tools unavailable
- Fallbacks for missing config
- Detection over assumption

### 5. Secure Over Permissive
- Default-deny for sensitive operations
- Explicit approval gates
- Audit trail for all state changes

---

## Key Differentiators

| Feature | ai-engineering | .github/CLAUDE.md | Cursor Rules | Copilot Workspace |
|---------|----------------|-------------------|--------------|-------------------|
| **Enforcement** | ✅ Mandatory local gates | ❌ Advisory only | ❌ Advisory only | ⚠️ Platform-dependent |
| **Cross-Provider** | ✅ Universal command model | ❌ Claude-specific | ❌ Cursor-specific | ❌ GitHub-specific |
| **State Management** | ✅ Session & history tracking | ❌ Stateless | ❌ Stateless | ⚠️ Cloud-only |
| **Remote Skills** | ✅ Org-wide skill library | ❌ Per-repo only | ❌ Per-repo only | ⚠️ Limited |
| **Security Gates** | ✅ Pre-commit hooks + gates | ❌ None | ❌ None | ⚠️ Platform gates only |
| **Context Optimization** | ✅ Token-aware caching | ❌ Manual | ❌ Manual | ⚠️ Proprietary |
| **Ownership Model** | ✅ Layered precedence | ❌ Flat file | ❌ Flat file | ❌ Not applicable |

---

## Success Metrics

### Adoption Metrics
- **Week 1:** Framework dogfooding this repo (ai-engineering)
- **Month 1:** 3+ internal repos using framework
- **Quarter 1:** 10+ repos, 5+ organizations adopting
- **Quarter 2:** Community contributions (skills, templates, adapters)

### Quality Metrics
- **Gate Pass Rate:** 90%+ operations auto-approved (low friction)
- **Security Incidents:** Zero ungated sensitive operations
- **Context Load Time:** <10s for typical repo
- **Token Efficiency:** <30% context overhead vs raw prompting

### Developer Experience Metrics
- **Time to First Commit:** <5 min from install to productive use
- **Session Setup Time:** <30s context load + gate config
- **Developer Satisfaction:** >4.0/5 "would recommend" rating

### Business Metrics
- **Standards Compliance:** 80%+ repos meet org standards within 3 months
- **Security Posture:** 100% sensitive operations logged and auditable
- **Velocity Impact:** 20%+ reduction in time spent on governance overhead

---

## Version and Evolution

**Current Phase:** Phase 0 - Context Initialization
**Target MVP:** Phase 1 - Core CLI, State Management, Local Enforcement
**Long-term Vision:** Industry-standard governance layer for AI-assisted development

See [`roadmap.md`](./roadmap.md) for detailed phasing and milestones.
