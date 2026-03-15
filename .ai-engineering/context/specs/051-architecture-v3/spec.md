---
id: "051"
slug: architecture-v3
title: "Architecture v3 — Clean-Sheet Redesign: 10 Agents, 40 Skills, Self-Improvement"
status: in-progress
created: "2026-03-15"
size: "XL"
tags: ["architecture", "agents", "skills", "standards", "governance", "self-improvement", "guard", "guide", "operate"]
branch: "spec/051-architecture-v3"
pipeline: "full"
decisions: []
---

# Spec 051 — Architecture v3

## Problem

ai-engineering's current architecture (7 agents, 35 skills, 37 standards) was grown organically over 50 specs. A comprehensive audit reveals structural issues that prevent market leadership:

1. **5 stub skills** — governance (48 lines), quality (45), security (58), build (45), perf (46) are hollow facades after over-consolidation. Users invoke them and get a CLI forwarder, not a procedure.
2. **No proactive governance** — all governance is reactive (hooks block at commit, scan reports post-hoc). No intelligent advisory during development.
3. **No developer growth** — every framework does work FOR the developer; none helps the developer learn and improve.
4. **14 orphaned runbooks** — prose templates with zero explicit agent ownership. When they fail, nobody escalates.
5. **Orphaned explain skill** — 253 lines of the highest-quality skill, owned by no agent.
6. **Aspirational dispatch** — execute agent is documented but has no programmatic orchestration code.
7. **Self-documenting names** — `a11y`, `db`, `cicd`, `perf`, `docs`, `feature-gap` are abbreviations/jargon that violate clean code naming.
8. **No self-improvement** — the framework collects telemetry (audit-log, signals) but no agent analyzes it to propose improvements.

Competitive analysis of 10+ frameworks (BMAD, GSD, SpecKit, Kiro, Tessl, Intent, Cursor, Windsurf) confirms: no competitor has proactive governance, developer growth, or data-driven self-improvement. This is ai-engineering's market opportunity.

## Solution

Clean-sheet architecture redesign applying SOLID, DRY, Anthropic skill-creator pattern, and AI 2027 readiness:

- **10 agents** in 3 tiers: orchestration (plan, execute, guard), domain (build, verify, ship, observe), advisory (guide, write, operate)
- **40 skills** with self-documenting names, expanded stubs, Anthropic pattern compliance (<500 lines, description triggers, explain WHY)
- **Self-improvement** via evolve skill: observe reads telemetry → proposes improvements → human reviews → plan creates spec
- **Guard integration** into build's post-edit validation (shift-left governance that works TODAY)
- **Feature gap reviewer** via verify.gap --framework mode (promise vs reality audit)

## Scope

### In Scope

- Expand 5 stub skills to full procedures (security, quality, governance, build, perf)
- Create 3 new agents (guard, guide, operate) with full behavioral contracts
- Create 6 new skills (guard, dispatch, guide, onboard, evolve, ops)
- Rename 2 agents (scan→verify, release→ship) + 12 skills to self-documenting names
- Merge create+delete skills into lifecycle
- Reassign explain skill to guide agent
- Reorganize standards (flatten standards/framework/ → standards/)
- Rewrite framework-contract.md and product-contract.md
- Create .ai-engineering/README.md
- Update all IDE adapters, templates, Python source, tests
- Sync template mirror to src/ai_engineering/templates/
- Update root README.md and CHANGELOG.md
- Add owner to all 5 runbooks (consolidated from 14)

### Out of Scope

- Programmatic agent dispatch (Python orchestrator) — tracked as gap spec-052
- Scheduled/headless execution modes — tracked as gap spec-055/058/059
- Multi-IDE verification (Copilot/Gemini/Codex testing) — tracked as gap spec-057
- ML-based prediction in observe — tracked as gap spec-056
- New CLI commands (unless required for new skills)

## Acceptance Criteria

| # | Criterion | Verification |
|---|----------|-------------|
| 1 | 10 agents with complete behavioral contracts (no stubs) | All agent files >100 lines with Identity, Modes, Behavior, Boundaries |
| 2 | 40 skills with full procedures (no facades) | All skills >50 lines, follow Anthropic pattern |
| 3 | 5 former stubs expanded to functional procedures | security >150, quality >120, governance >120, code >150, performance >100 lines |
| 4 | guard.advise integrated into build post-edit validation | build.md references guard.advise step |
| 5 | evolve skill produces self-improvement report from real data | Run evolve on audit-log → report with ≥3 patterns |
| 6 | verify.gap --framework mode checks promise vs reality | Run on product-contract → gap report |
| 7 | explain owned by guide, cleanup owned by plan+operate | Agent frontmatter references correct |
| 8 | All 5 runbooks have owner: operate in frontmatter | Grep confirms |
| 9 | All Python tests pass after rename updates | pytest → 0 failures |
| 10 | Template mirror byte-identical with canonical | ai-eng validate → 0 mirror findings |
| 11 | Fresh ai-eng install works | Install in temp dir → success |
| 12 | All aspirational gaps documented with future spec numbers | Gap register in done.md |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| ~50-60 cross-references per rename → missed reference | High | Medium | Migration validation script checks all locations |
| Template mirror drift during rename | Medium | High | Sync + validate after each phase |
| Tests break during rename phase | High | Low | Update tests in same commit as rename |
| guard.advise adds overhead to build | Low | Medium | Fail-open design, only checks changed files |
| Evolve produces low-quality proposals | Medium | Low | Human review gate, confidence scoring |
