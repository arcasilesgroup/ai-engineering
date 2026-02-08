# Discovery Findings

## Overview

This document captures comprehensive discovery findings from requirements analysis, persona research, risk assessment, and constraint validation. It serves as the foundation for all architectural and planning decisions.

**Discovery Period:** Initial product conception
**Last Updated:** 2026-02-08 (Phase 0)
**Status:** Complete for MVP scope

---

## Requirements Matrix

### Functional Requirements

| ID | Requirement | Priority | Rationale | Acceptance Criteria |
|----|-------------|----------|-----------|---------------------|
| FR-1 | **Local Governance Enforcement** | P0 | Standards must be enforceable, not advisory | Pre-commit hooks block violations; 100% gate coverage for destructive ops |
| FR-2 | **Session State Management** | P0 | Context persistence across sessions | Session start/end/pause/resume tracked; history queryable |
| FR-3 | **Provider-Agnostic Command Model** | P0 | Must work with Claude, Copilot, OpenAI, local models | Unified command interface; adapters for 3+ providers |
| FR-4 | **Single Source of Truth (SSOT)** | P0 | One canonical `.ai-engineering/` structure | No duplication; layered ownership model with precedence |
| FR-5 | **Zero-Config Installation** | P1 | Frictionless onboarding | `ai install` works with sensible defaults; <5 min to first commit |
| FR-6 | **Context Optimization** | P1 | Token efficiency critical for cost and latency | <30% context overhead; <10s load time for typical repo |
| FR-7 | **Remote Skills Library** | P1 | Org-wide skill sharing | Skills addressable by URL; integrity checking; local cache |
| FR-8 | **Branch-Level Governance** | P1 | Different rules for main vs feature branches | Branch-specific standards; merge gates enforced |
| FR-9 | **Agent Orchestration** | P2 | Intelligent task routing | Bounded capabilities per agent; handoff protocols |
| FR-10 | **Maintenance Agent** | P2 | Autonomous context health | Stale detection; conflict flagging; learnings synthesis |

### Non-Functional Requirements

| ID | Requirement | Priority | Target Metric | Validation |
|----|-------------|----------|---------------|------------|
| NFR-1 | **Cross-OS Compatibility** | P0 | macOS, Linux (P0); Windows (P2) | E2E tests on all platforms |
| NFR-2 | **Performance** | P1 | <10s context load (P95) | Load testing with varied repo sizes |
| NFR-3 | **Security** | P0 | Zero ungated sensitive operations | Audit log validation; penetration testing |
| NFR-4 | **Reliability** | P1 | 99% uptime for local operations | Graceful degradation; offline mode |
| NFR-5 | **Token Efficiency** | P1 | <5000 tokens for typical context load | Token budget tracking; optimization validation |
| NFR-6 | **Backward Compatibility** | P1 | Post-1.0: no breaking changes in MINOR | Deprecation policy; migration guides |
| NFR-7 | **Extensibility** | P2 | Plugin architecture for custom gates/skills | Adapter pattern validation |
| NFR-8 | **Observability** | P2 | Opt-in telemetry for usage insights | Privacy-preserving metrics; clear opt-out |

---

## Core Personas (Detailed)

### 1. Platform Engineer (Governance Owner)

**Profile:**
- **Role:** Sets and enforces organization-wide standards
- **Experience:** 5-10 years; deep infrastructure and tooling expertise
- **Goals:** Consistency, security, scalability, developer productivity
- **Frustrations:** Standards ignored by AI agents; manual enforcement; config sprawl

**Use Cases:**
- Define mandatory standards for all repos (linting, security gates, branching policies)
- Roll out framework to 50+ repos without individual repo changes
- Audit compliance across organization
- Evolve standards without breaking existing repos

**Success Metrics:**
- 80%+ repo adoption within 6 months
- <10% false positive gate rate
- Zero security incidents from ungated AI operations

**Key Requirements:**
- Layered ownership (org > team > repo > local)
- Remote standards distribution
- Audit trail and compliance reporting

---

### 2. Team Lead / Engineering Manager

**Profile:**
- **Role:** Manages team delivery; accountable for code quality and velocity
- **Experience:** 3-8 years individual contributor + 1-3 years management
- **Goals:** Predictable delivery, high code quality, team efficiency, risk mitigation
- **Frustrations:** Invisible AI changes; no review trail; context loss between sessions

**Use Cases:**
- Review AI-driven changes before merge
- Track which standards are frequently violated (learning opportunity)
- Ensure team members use consistent AI workflows
- Investigate incidents involving AI-generated code

**Success Metrics:**
- 100% AI changes visible in audit log
- <20% time spent on governance overhead
- Team velocity +20% with framework adoption

**Key Requirements:**
- Change history and audit trail
- Gate override approval workflow
- Reporting and dashboards (phase 2+)

---

### 3. Developer (AI User)

**Profile:**
- **Role:** Writes code with AI assistance; primary framework user
- **Experience:** 0-10 years (wide range)
- **Goals:** Fast iteration, minimal friction, clear guidance from AI
- **Frustrations:** Re-explaining context every session; manual approvals; unclear errors

**Use Cases:**
- Start new session and have AI immediately understand repo standards
- Request feature implementation that respects existing architecture
- Override gate for legitimate edge case (with justification)
- Resume paused session without losing context

**Success Metrics:**
- <10s context load time
- 90%+ gates auto-approved (low friction)
- <5 min from idea to first AI-assisted commit
- >4.0/5 developer satisfaction

**Key Requirements:**
- Fast context loading (token-optimized)
- Clear, actionable error messages
- Minimal configuration (zero-config ideal)
- Escape hatches for edge cases (documented overrides)

---

### 4. Security / Compliance Specialist

**Profile:**
- **Role:** Ensures secure development practices; manages compliance requirements
- **Experience:** 3-10 years; focus on AppSec, DevSecOps, audit
- **Goals:** Prevent vulnerabilities, ensure audit trail, meet compliance mandates
- **Frustrations:** AI agents bypass security controls; no visibility into AI actions

**Use Cases:**
- Block AI from committing secrets or sensitive data
- Require manual approval for infrastructure changes
- Audit all AI operations for compliance review (SOC2, PCI-DSS, etc.)
- Detect and alert on policy violations

**Success Metrics:**
- 100% sensitive operations gated and logged
- Zero compliance audit findings related to AI usage
- <1% false negative rate on sensitive data detection

**Key Requirements:**
- Mandatory gates for sensitive operations (cannot be disabled)
- Tamper-proof audit log
- Integration with secret scanning tools
- Configurable sensitivity thresholds

---

### 5. DevEx / Developer Productivity Owner

**Profile:**
- **Role:** Measures and improves developer experience; owns tooling strategy
- **Experience:** 3-8 years; focus on metrics, tooling, process improvement
- **Goals:** Quantify productivity gains, reduce friction, optimize tooling ROI
- **Frustrations:** Black box AI usage; no data on effectiveness; unknown costs

**Use Cases:**
- Measure AI adoption rate across organization
- Track token usage and costs per team/repo
- Identify friction points in AI workflows
- A/B test different standards or gate configurations

**Success Metrics:**
- Measurable velocity improvement (e.g., 20% faster feature delivery)
- Token cost optimization (30% reduction via context optimization)
- Developer NPS improvement

**Key Requirements:**
- Opt-in telemetry with privacy controls
- Usage analytics and reporting
- Cost tracking per repo/team
- Experimentation framework (A/B testing gates/standards)

---

## Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Cross-OS compatibility issues** | High | High | Start macOS/Linux; extensive E2E testing; defer Windows to Phase 3 |
| **Git hook conflicts with existing tools** | Medium | Medium | Detection and graceful warnings; priority-based hook chaining |
| **Performance degradation on large repos** | Medium | High | Context optimization as P0; caching; progressive loading |
| **Token budget overruns** | Medium | Medium | Hard limits; smart file prioritization; ignore patterns |
| **Remote skill integrity compromised** | Low | Critical | Signature verification; checksum validation; allow-list option |
| **State corruption from concurrent sessions** | Low | High | File locking; atomic writes; conflict detection |

### Product/Market Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Low adoption (too complex)** | Medium | High | Zero-config defaults; dogfooding; clear migration path |
| **Fragmentation (provider-specific forks)** | Medium | Medium | Provider-agnostic core; adapter pattern; open source governance |
| **Competitive threat (platform vendors)** | High | Medium | Focus on cross-platform value; open standards; community-driven |
| **Maintenance burden (agent accuracy)** | Medium | Low | Start manual; iterate to automation based on accuracy |

### Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Support burden for edge cases** | High | Medium | Comprehensive docs; clear error messages; escape hatches |
| **Breaking changes disrupting users** | Medium | High | Semantic versioning; deprecation policy; migration guides |
| **Security incident from framework bug** | Low | Critical | Security review gates; penetration testing; bug bounty (post-1.0) |

---

## Constraints and Assumptions

### Technical Constraints
- **Python 3.9+ required** (for widespread compatibility)
- **Git as VCS** (framework assumes git; no SVN/Mercurial support planned)
- **Local file system access** (required for state management and hooks)
- **Network access for remote skills** (graceful degradation if offline)

### Business Constraints
- **Open source first** (MIT or Apache 2.0 license)
- **No vendor lock-in** (provider-agnostic by design)
- **Dogfooding mandate** (must use framework in ai-engineering repo before external release)

### Assumptions
- ✅ **AI agents can parse and respect structured commands** (validated with Claude)
- ✅ **Developers willing to adopt new tooling if ROI clear** (assumed; validate in Phase 1)
- ✅ **Organizations have base git/shell literacy** (prerequisite, not framework concern)
- ⚠️ **Remote skill integrity model sufficient** (to be validated in Phase 2)
- ⚠️ **Token optimization yields 30%+ savings** (hypothesis; validate with real repos)

---

## Glossary

| Term | Definition |
|------|------------|
| **Gate** | Approval checkpoint for operations (pre-commit, merge, destructive commands) |
| **Skill** | Reusable AI instruction template (local or remote) addressable by identifier |
| **Session** | Bounded context for AI work (start, end, pause, resume) with state tracking |
| **Ownership Model** | Layered precedence (local > repo > team > org > defaults) for config resolution |
| **Manifest** | `.ai-engineering/manifest.yml` - canonical config for repo governance |
| **Context Optimization** | Token-efficient loading of only necessary project context |
| **Provider** | AI service (Claude, Copilot, OpenAI, local model) interfaced via adapter |
| **Maintenance Agent** | Autonomous agent for context health checks and stale content detection |
| **Bounded Capability** | Restricted permission set per agent type (e.g., readonly vs write access) |

---

## Key Decisions Log

| ID | Decision | Rationale | Alternatives Considered | Status |
|----|----------|-----------|-------------------------|--------|
| DEC-001 | **YAML for manifest format** | Human-readable; widely supported; good tooling | TOML (less familiar), JSON (verbose) | ✅ Approved |
| DEC-002 | **Local-first enforcement (hooks/gates)** | Security and reliability; no cloud dependency | Cloud-based gates (latency, dependency) | ✅ Approved |
| DEC-003 | **Provider-agnostic command model** | Future-proof; no vendor lock-in | Provider-specific optimizations (fragmentation risk) | ✅ Approved |
| DEC-004 | **Python as implementation language** | Rich ecosystem; AI/CLI tooling; cross-platform | Go (fewer deps), Rust (complexity), Shell (portability) | ✅ Approved |
| DEC-005 | **Layered ownership with precedence** | Balances flexibility and control | Flat (no org standards), Strict (no local override) | ✅ Approved |
| DEC-006 | **Context in `.ai-engineering/context/`** | Separation of concerns; git-friendly | In manifest (bloat), External DB (complexity) | ✅ Approved |
| DEC-007 | **Defer Windows to Phase 3** | Focus MVP; validate model before Windows complexity | Simultaneous (delays MVP) | ✅ Approved |
| DEC-008 | **Session state in local files** | Simple; auditable; no external deps | Database (overkill), Cloud (dependency) | ✅ Approved |

---

## Open Questions (Parking Lot)

### Pre-Phase 1:
- ❓ **Installer distribution:** PyPI vs brew vs curl script? (Lean: PyPI for simplicity)
- ❓ **Minimum Python version:** 3.9+ or 3.11+? (Lean: 3.9 for compatibility)
- ❓ **CLI framework:** Click vs Typer vs argparse? (Lean: Typer for modern typing)

### Pre-Phase 2:
- ❓ **Skill registry:** Centralized GitHub repo vs federated? (Start centralized, allow org overrides)
- ❓ **Signature scheme:** GPG vs ed25519 vs cosign? (Start SHA-256 checksums, evolve to signatures)
- ❓ **Context cache:** In-memory vs file-based? (File-based for persistence)

### Pre-Phase 3:
- ❓ **Agent runtime:** Local subprocess vs containers? (Local for simplicity)
- ❓ **Maintenance frequency:** Daily vs weekly vs on-demand? (On-demand initially)

---

## Next Steps

1. **Validate assumptions:** Phase 1 dogfooding will test core hypotheses (token savings, adoption friction)
2. **Iterate on personas:** Refine based on real user feedback post-MVP
3. **Update risk register:** Quarterly review as new risks emerge
4. **Decision backlog:** Revisit open questions at phase boundaries

---

## References

- [Product Vision](../product/vision.md)
- [Architecture Document](./architecture.md)
- [Planning Document](./planning.md)
