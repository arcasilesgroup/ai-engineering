# Product Roadmap

## Overview

This roadmap defines the phased delivery plan for the ai-engineering framework. Each phase builds on the previous one, with clear exit criteria and incremental value delivery.

**Guiding Principles:**
- Ship working software early and often
- Dogfood every phase before external release
- Validate with real usage before expanding scope
- Maintain backward compatibility after 1.0

---

## Phase 0: Context Initialization ✅ CURRENT

**Objective:** Establish governance foundation before writing any framework code

**Scope:**
- Create `.ai-engineering/context/` structure
- Document all discovery findings, architecture decisions, and planning
- Establish product vision, roadmap, and backlog
- Initialize learnings.md for retrospectives

**Exit Criteria:**
- [x] All context files created and populated
- [x] Architecture document complete with ownership model, command contract, manifest schema
- [x] Planning document contains Phase 1 backlog with priorities
- [x] Verification strategy documented with E2E test matrix
- [x] First commit pushed with complete context as foundation

**Key Deliverables:**
- `.ai-engineering/context/product/` (vision, roadmap)
- `.ai-engineering/context/delivery/` (discovery, architecture, planning, verification, etc.)
- `.ai-engineering/context/backlog/` (epics, features, user stories, tasks)
- `context/learnings.md`

**Status:** ✅ **IN PROGRESS** (this plan execution)

---

## Phase 1: MVP - Core Framework Foundation

**Objective:** Ship minimal viable framework that can enforce standards and manage state locally

**Scope:**

### Must-Have (P0):
1. **CLI Bootstrapping**
   - `ai install` command that creates `.ai-engineering/` structure
   - Detection of existing config (ADO, GitHub, Cursor, CLAUDE.md)
   - Interactive onboarding with sensible defaults

2. **State Management**
   - Session tracking (start, end, pause, resume)
   - Change history log (operations, approvals, outcomes)
   - Status command for current session context

3. **Local Standards Enforcement**
   - Pre-commit hook installation
   - Basic gate system (destructive ops, sensitive files)
   - Standards validation (linting, naming conventions)

4. **Command Model**
   - Core commands: `ai install`, `ai session`, `ai status`, `ai gate`, `ai help`
   - Provider-agnostic command routing
   - Error handling and help text

5. **Manifest Schema**
   - YAML-based `.ai-engineering/manifest.yml`
   - Support for standards, gates, ownership, context optimization
   - Validation on load

### Should-Have (P1):
- Basic context optimization (ignore patterns, file prioritization)
- Git hooks for session boundaries
- Simple audit log

### Nice-to-Have (P2):
- Cross-OS installer (macOS, Linux)
- Basic telemetry (opt-in)

**Exit Criteria:**
- [ ] Framework can install itself (`ai install` in this repo)
- [ ] All P0 commands functional and tested
- [ ] Dogfooding: ai-engineering repo managed by framework
- [ ] Pre-commit hooks block ungated destructive operations
- [ ] Session state persisted and queryable
- [ ] Documentation: installation guide, command reference, migration guide

**Target Timeline:** 4-6 weeks from Phase 0 completion

**Key Risks:**
- Cross-OS compatibility issues (mitigate: start macOS/Linux, defer Windows)
- Git hook conflicts with existing tools (mitigate: graceful detection and warning)

---

## Phase 2: Branch Governance & Remote Skills

**Objective:** Add collaboration features and shared skill library

**Scope:**

### Core Features:
1. **Branch-Level Governance**
   - Branch-specific standards (main vs feature branches)
   - Merge gate enforcement
   - Protected branch policies

2. **Remote Skills**
   - Skill registry with integrity checking (signatures, checksums)
   - `ai skill add <url>` command
   - Local cache with TTL
   - Org-wide skill library support

3. **Enhanced Context Optimization**
   - Token budget awareness
   - Progressive context loading
   - Smart file prioritization based on task type

4. **Multi-Provider Support**
   - Adapters for Claude, GitHub Copilot, Cursor, OpenAI
   - Provider detection and routing
   - Unified command interface

### Dependencies:
- Phase 1 complete and dogfooded
- Real-world usage data from 3+ repos

**Exit Criteria:**
- [ ] Branch-specific governance functional
- [ ] Remote skills can be added, validated, and executed
- [ ] Context loading <10s for typical repo
- [ ] Multi-provider adapter architecture proven with 2+ providers

**Target Timeline:** 6-8 weeks from Phase 1 completion

**Key Risks:**
- Remote skill security model complexity (mitigate: start with signature-only, iterate)
- Token budget optimization requires provider-specific tuning

---

## Phase 3: Agent Orchestration & Maintenance

**Objective:** Intelligent agent coordination and autonomous context maintenance

**Scope:**

### Core Features:
1. **Agent Orchestration**
   - Bounded capability model per agent type
   - Task-specific agent routing
   - Handoff protocols and state transfer

2. **Maintenance Agent**
   - Automated context health checks
   - Stale content detection and flagging
   - Conflict resolution suggestions
   - Periodic learnings synthesis

3. **Advanced Security**
   - Sensitive data detection
   - Credential scanning integration
   - Audit trail enrichment
   - Compliance reporting

4. **Windows Support**
   - Cross-OS parity
   - PowerShell integration
   - Windows-specific gate logic

### Dependencies:
- Phase 2 complete
- Maintenance agent design validated
- Security model battle-tested in production

**Exit Criteria:**
- [ ] Agent orchestration reduces manual routing overhead by 50%+
- [ ] Maintenance agent successfully flags stale context
- [ ] Framework functional on Windows with parity testing
- [ ] Security gates block 100% of known vulnerability patterns

**Target Timeline:** 8-12 weeks from Phase 2 completion

**Key Risks:**
- Agent orchestration complexity (mitigate: start simple, iterate based on usage)
- Maintenance agent accuracy (false positives/negatives)

---

## Phase 4: Ecosystem & Scale (Future)

**Objective:** Community-driven expansion and enterprise features

**Scope (Exploratory):**
- Template marketplace for common project types
- Organization-level policy management
- Advanced analytics and insights
- IDE integrations (VS Code, JetBrains)
- API for third-party extensions
- Multi-repo orchestration (monorepo support)

**Dependencies:**
- Community adoption and feedback
- Enterprise pilot programs
- Proven scalability to 100+ repos

**Timeline:** TBD based on adoption and demand

---

## Release Model

### Versioning Strategy
- **Semantic Versioning:** `MAJOR.MINOR.PATCH`
- **Pre-1.0:** Breaking changes allowed per phase
- **Post-1.0:** Strict backward compatibility in MINOR/PATCH
- **LTS Releases:** Every 6 months post-1.0

### Release Cadence
- **Phase 1 (MVP):** Weekly alpha releases for dogfooding
- **Phase 2-3:** Bi-weekly beta releases
- **Post-1.0:** Monthly stable releases, weekly patches as needed

### Deprecation Policy
- **Pre-1.0:** 2-week notice for breaking changes
- **Post-1.0:** One major version deprecation cycle (6-12 months)

---

## Dogfooding Plan

**Phase 0:** ✅ Context initialization (this repo, now)

**Phase 1:**
- Install framework in ai-engineering repo
- Use for all subsequent development
- Validate session tracking, gates, standards enforcement
- Document pain points in `learnings.md`

**Phase 2:**
- Migrate 2-3 internal repos to framework
- Test remote skills with shared org library
- Validate multi-repo consistency

**Phase 3:**
- Use agent orchestration for framework maintenance
- Enable maintenance agent to audit ai-engineering repo
- Full cross-OS validation with team members

**Success Criteria for Each Phase:**
- Zero critical bugs blocking daily use
- Developer satisfaction >4.0/5
- All planned features functional in dogfooding context

---

## Metrics and Monitoring

### Leading Indicators (tracked per phase):
- Installation success rate
- Time to first productive session
- Gate false positive rate
- Context load time (P50, P95)

### Lagging Indicators (quarterly):
- Active repos using framework
- Community contributions (PRs, skills)
- Security incidents prevented
- Developer NPS

### Telemetry (Opt-In):
- Command usage frequency
- Error rates by command
- Session duration and frequency
- Context size distribution

---

## Open Questions & Decisions Needed

### Pre-Phase 1:
- [ ] **Installer Distribution:** PyPI package vs curl script vs brew formula?
- [ ] **Config Format:** YAML vs TOML vs JSON? (YAML for readability)
- [ ] **Minimum Python Version:** 3.9+ or 3.11+? (3.9+ for broader compatibility)

### Pre-Phase 2:
- [ ] **Skill Registry:** Centralized vs federated? (Start centralized GitHub repo)
- [ ] **Signature Scheme:** GPG vs ed25519 vs cosign? (Start simple: SHA-256 checksums)

### Pre-Phase 3:
- [ ] **Agent Runtime:** Local processes vs cloud functions? (Local for security/privacy)
- [ ] **Maintenance Frequency:** Daily vs weekly vs on-demand? (Start on-demand, iterate)

---

## Next Steps

**Immediate (Phase 0 → Phase 1 Transition):**
1. ✅ Complete context initialization (this plan)
2. Commit Phase 0 deliverables as foundation
3. Set up Python project structure (`pyproject.toml`, `src/`, `tests/`)
4. Scaffold CLI with `click` or `typer`
5. Begin installer implementation

**Within 1 Week:**
- Phase 1 kickoff meeting
- Set up CI/CD for testing
- Create Phase 1 sprint plan from backlog

**Within 1 Month:**
- MVP dogfooding in this repo
- First external repo pilot (select low-risk candidate)

---

## Links and References

- [Product Vision](./vision.md)
- [Architecture Document](../delivery/architecture.md)
- [Phase 1 Planning](../delivery/planning.md)
- [Epic Backlog](../backlog/epics.md)
