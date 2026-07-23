---
spec: spec-197
slug: native-command-skill-agent-surfaces
status: draft
executor: autopilot
safe_next_command: "/ai-autopilot"
automation: semi
concern_count: 5
estimated_files: 20
reason: "Multi-concern surface refactor across 6 hosts; ≥3 concerns triggers autopilot"
execution_route:
  version: "1.0"
  executor: autopilot
  automation: semi
---

# Plan — Native Command/Skill/Agent Surfaces (spec-197)

## Phase 1: Evidence Matrix + Fixtures

- [ ] T-1 — Build host capability matrix (documented paths, precedence, invocation)
  - Agent: build
  - Files: `src/ai_engineering/surfaces/capability_matrix.py`
  - Gate: `pytest tests/unit/test_capability_matrix.py -v`

- [ ] T-2 — Create clean-host fixtures for Claude Code, Codex, OpenCode
  - Agent: build
  - Files: `tests/fixtures/surfaces/claude/`, `tests/fixtures/surfaces/codex/`, `tests/fixtures/surfaces/opencode/`
  - Gate: `pytest tests/unit/test_surface_fixtures.py -v`

## Phase 2: Generator Refactor

- [ ] T-3 — Refactor sync_mirrors/core.py to emit one root per host
  - Agent: build
  - Files: `scripts/sync_mirrors/core.py`
  - Principles applied: §10.4 DRY (shared portable contracts)
  - Gate: `pytest tests/architecture/test_surface_parity.py -v`

- [ ] T-4 — Remove duplicate skill trees from .codex and .agents
  - Agent: build
  - Files: `scripts/sync_mirrors/core.py`, `scripts/sync_mirrors/codex_target.py`
  - Gate: no duplicate IDs across roots

## Phase 3: Host Adapters

- [ ] T-5 — Implement Claude Code adapter (user-only skills, /ai-* commands)
  - Agent: build
  - Files: `src/ai_engineering/surfaces/adapters/claude.py`
  - Gate: `pytest tests/unit/test_surface_claude.py -v`

- [ ] T-6 — Implement Codex adapter ($ai-* syntax, native hooks)
  - Agent: build
  - Files: `src/ai_engineering/surfaces/adapters/codex.py`
  - Gate: `pytest tests/unit/test_surface_codex.py -v`

- [ ] T-7 — Implement OpenCode adapter (thin commands, no skill catalog injection)
  - Agent: build
  - Files: `src/ai_engineering/surfaces/adapters/opencode.py`
  - Gate: command index not injected as prompt catalog

## Phase 4: Agent + Hook Adapters

- [ ] T-8 — Generate host-native agent adapters (Claude .claude/agents, Copilot .github/agents)
  - Agent: build
  - Files: `src/ai_engineering/surfaces/agent_adapter.py`
  - Gate: `pytest tests/unit/test_agent_adapters.py -v`

- [ ] T-9 — Refactor hook wiring to use native mechanisms per host
  - Agent: build
  - Files: `scripts/sync_mirrors/core.py` (hook generation section)
  - Gate: hooks are host-native, no universal `.agents` assumption

## Phase 5: Integration + Rollback

- [ ] T-10 — Write integration tests: single-root discovery, explicit invocation, rollback
  - Agent: build
  - Files: `tests/integration/test_surface_integration.py`
  - Gate: `pytest tests/integration/test_surface_integration.py -v`

- [ ] T-11 — Verify harness shows zero duplicate IDs and reduced catalog
  - Agent: verify
  - Gate: harness report shows catalog.duplicate_ids == 0

- [ ] T-12 — Documentation and CHANGELOG
  - Agent: build
  - Files: `docs/surfaces.md`, `CHANGELOG.md`
