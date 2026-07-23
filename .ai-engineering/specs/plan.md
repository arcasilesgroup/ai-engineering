---
spec: spec-199
slug: cli-integration-portfolio-and-pilots
status: draft
executor: build
safe_next_command: "/ai-build"
automation: semi
concern_count: 3
estimated_files: 8
reason: "Research and pilot selection; depends on spec-198 pack contract for admission"
execution_route:
  version: "1.0"
  executor: build
  automation: semi
---

# Plan — CLI Integration Portfolio and Pilots (spec-199)

## Phase 1: Census + Research (TDD)

- [ ] T-1 — Build CLI census scanner (binary, version, origin, auth state, cost surface)
  - Agent: build
  - Files: `src/ai_engineering/portfolio/census.py`
  - Gate: `pytest tests/unit/test_portfolio_census.py -v`

- [ ] T-2 — Build primary-source researcher (vendor docs, immutable snapshots)
  - Agent: build
  - Files: `src/ai_engineering/portfolio/researcher.py`
  - Gate: `pytest tests/unit/test_portfolio_researcher.py -v`

## Phase 2: Council + Decision

- [ ] T-3 — Build council packet normalizer (evidence, options, dissent)
  - Agent: build
  - Files: `src/ai_engineering/portfolio/council.py`
  - Gate: `pytest tests/unit/test_portfolio_council.py -v`

- [ ] T-4 — Build decision record emitter (adopt/adapt/reject/blocked)
  - Agent: build
  - Files: `src/ai_engineering/portfolio/decision.py`
  - Gate: `pytest tests/unit/test_portfolio_decision.py -v`

## Phase 3: Pilot Briefs

- [ ] T-5 — Generate individual implementation briefs for selected pilots
  - Agent: build
  - Files: `.ai-engineering/specs/drafts/pilot-gh-brief.md`, `.ai-engineering/specs/drafts/pilot-engram-brief.md`
  - Gate: each brief has pack-contract dependency declared

- [ ] T-6 — Verify no candidate is installed or auto-discovered
  - Agent: verify
  - Gate: `grep -r "install\|enable\|authorize" .ai-engineering/specs/drafts/pilot-*` returns only advisory content

- [ ] T-7 — Documentation and CHANGELOG
  - Agent: build
  - Files: `docs/portfolio.md`, `CHANGELOG.md`
