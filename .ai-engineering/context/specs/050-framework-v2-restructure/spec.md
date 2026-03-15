---
id: "050"
slug: framework-v2-restructure
title: "Framework v2 Restructure — Complete Platform Audit Remediation"
status: in-progress
pipeline: full
created: "2026-03-12"
tags: ["governance", "architecture", "restructure", "audit", "multi-ide", "quality"]
owner: plan
---

# Spec 050 — Framework v2 Restructure

## Problem

A comprehensive 8-dimension audit (2026-03-12) scored the ai-engineering framework **6.9/10**. While the governance model and CLI are strong, critical structural problems undermine reliability, multi-IDE portability, and developer trust:

1. **Empty decision-store** — 49 specs delivered with zero recorded decisions. The governance backbone is hollow.
2. **3 truncated skills** — `debug`, `architecture`, `api` are under 30 lines each; unusable stubs shipping as "complete".
3. **26% test confidence** — 243 tests exist but cover only CLI paths; agents, skills, and governance logic are untested.
4. **Unimplemented phase branching** — `framework-contract.md` promises `phase/2.x` branching; code uses flat `main`.
5. **50% multi-IDE reality** — Claude Code works; Copilot/Gemini/Codex support is aspirational documentation.
6. **PR skill scope creep** — `pr/SKILL.md` at 400+ lines does branch creation, commit, push, PR, and review — 5 responsibilities in 1 skill.
7. **Execute/Release checkpoint conflict** — Both agents write `session-checkpoint.json` with incompatible schemas.
8. **10 missing stack standards** — Rust, Java/Kotlin, Swift, Ruby, PHP, C/C++, Terraform, Helm, Ansible, Pulumi listed in manifest but have no standard files.
9. **Governance doc proliferation** — CLAUDE.md, AGENTS.md, GEMINI.md, COPILOT.md, .cursorrules overlap ~60%.
10. **Ghost skill references** — manifest.yml lists skills that don't exist on disk.
11. **No mirror sync validation** — Multi-provider instruction files diverge silently.
12. **4 dead-weight runbooks** — `codex-runbook.md`, `gemini-runbook.md`, `installer-runbook.md`, `github-templates-runbook.md` contain placeholder content.
13. **metrics_collect bug** — `observe` agent's `metrics_collect` function has unreachable code path.
14. **12 missing cross-cutting standards** — No standards for error-handling, logging, config, i18n, observability, etc.
15. **4 severely incomplete skills** — `work-item`, `feature-gap`, `product-contract`, `migrate` lack actionable procedures.

## Solution

Six-phase remediation plan executing all 15 findings, prioritized by blast radius and dependency order:

- **Phase 1 (Foundation)**: Fix governance backbone — decision-store, bugs, checkpoint conflict
- **Phase 2 (Skills)**: Remediate truncated and incomplete skills, decompose PR skill
- **Phase 3 (Agents)**: Resolve agent conflicts, add missing agent capabilities
- **Phase 4 (Standards)**: Fill 10 missing stacks + 12 cross-cutting standards
- **Phase 5 (Multi-IDE & CI)**: Consolidate governance docs, add mirror sync validation, harden CI
- **Phase 6 (Validation)**: End-to-end audit re-run, cleanup dead artifacts, update contracts

## Scope

### In Scope

- All 15 audit findings remediation
- Governance model consolidation (single-source → generated per-IDE)
- Skill decomposition and completion
- Agent checkpoint schema unification
- Test coverage expansion to 60%+ meaningful coverage
- Stack standards for all 10 missing platforms
- Cross-cutting standards framework
- Multi-IDE validation tooling
- Decision-store bootstrapping with retroactive decisions

### Out of Scope

- New CLI commands (unless required for validation tooling)
- New agent creation (optimize existing 7)
- Python version upgrade
- External integrations (SonarCloud, Snyk already covered by specs 038, 049)
- Phase branching implementation (descoped — flat main is correct for current scale)

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Audit score | 6.9/10 | ≥8.5/10 |
| Decision-store entries | 0 | ≥15 (retroactive + new) |
| Truncated skills | 7 | 0 |
| Test confidence | 26% | 60%+ meaningful |
| Multi-IDE validated | 1/4 | 3/4 (Claude, Copilot, Gemini) |
| Missing stack standards | 10 | 0 |
| Cross-cutting standards | 0 | ≥8 |
| Ghost references | >5 | 0 |
| Governance doc overlap | ~60% | <10% (generated) |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Scope creep across 6 phases | High | High | Strict phase gates; each phase is independently shippable |
| Breaking existing workflows | Medium | High | Each phase has rollback checkpoint; tests before merge |
| Multi-IDE testing requires manual validation | High | Medium | Document manual test matrix; automate what's possible |
| Retroactive decision-store may miss context | Medium | Low | Best-effort from git log; mark as RECONSTRUCTED |
| Standards fatigue (too many new docs) | Medium | Medium | Lean standards — max 1 page each; template-driven |

## Dependencies

- Spec 049 (SonarCloud Quality Gate) should complete first or in parallel
- No external service dependencies
- Requires `uv`, `ruff`, `ty`, `pytest` toolchain (already installed)
