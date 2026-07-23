---
spec: spec-195
slug: third-party-mcp-removal
status: draft
executor: build
safe_next_command: "/ai-build"
automation: semi
concern_count: 3
estimated_files: 8
reason: "Security-critical removal; depends on spec-194 harness for baseline evidence"
execution_route:
  version: "1.0"
  executor: build
  automation: semi
---

# Plan — Third-Party MCP Removal (spec-195)

## Phase 1: Inventory + Classification (TDD)

- [ ] T-1 — Build MCP inventory scanner that classifies all MCP registrations
  - Agent: build
  - Files: `src/ai_engineering/mcp/inventory.py`
  - Principles applied: §10.6 SDD (evidence before action), §10.1 KISS
  - Gate: `pytest tests/unit/test_mcp_inventory.py -v`

- [ ] T-2 — Build credential assessor (reads store type/ACL only, never secret values)
  - Agent: build
  - Files: `src/ai_engineering/mcp/credential_assessor.py`
  - Principles applied: §10.5 TDD (test secret-shaped fixtures)
  - Gate: `pytest tests/unit/test_mcp_credentials.py -v`

## Phase 2: Removal Executor

- [ ] T-3 — Build removal executor with preview → confirm → apply → verify
  - Agent: build
  - Files: `src/ai_engineering/mcp/removal.py`
  - Principles applied: §10.8 Hexagonal Architecture (adapter per host)
  - Gate: `pytest tests/unit/test_mcp_removal.py -v`

- [ ] T-4 — Build Pencil/Pen identity verifier (5-field check)
  - Agent: build
  - Files: `src/ai_engineering/mcp/pencil_verifier.py`
  - Principles applied: §10.1 KISS (exact match, no fuzzy)
  - Gate: `pytest tests/unit/test_mcp_pencil.py -v`

## Phase 3: Host-Specific Adapters

- [ ] T-5 — Implement Claude Code MCP removal adapter
  - Agent: build
  - Files: `src/ai_engineering/mcp/adapters/claude.py`
  - Gate: `pytest tests/unit/test_mcp_claude.py -v`

- [ ] T-6 — Implement Codex MCP removal adapter (保留 vendor/system exceptions)
  - Agent: build
  - Files: `src/ai_engineering/mcp/adapters/codex.py`
  - Gate: `pytest tests/unit/test_mcp_codex.py -v`

- [ ] T-7 — Implement OpenCode MCP removal adapter
  - Agent: build
  - Files: `src/ai_engineering/mcp/adapters/opencode.py`
  - Gate: `pytest tests/unit/test_mcp_opencode.py -v`

## Phase 4: Integration + Verification

- [ ] T-8 — Write integration tests: full removal cycle with fixtures
  - Agent: build
  - Files: `tests/integration/test_mcp_removal_integration.py`
  - Principles applied: §10.5 TDD (fixture-based regression)
  - Gate: `pytest tests/integration/test_mcp_removal_integration.py -v`

- [ ] T-9 — Verify harness baseline shows zero MCP residue after removal
  - Agent: verify
  - Files: (uses spec-194 harness)
  - Gate: `uv run python -c "from ai_engineering.harness.adapters.claude import ClaudeAdapter; print(ClaudeAdapter().collect().mcp_residue)"`

- [ ] T-10 — Documentation and CHANGELOG
  - Agent: build
  - Files: `docs/mcp-removal.md`, `CHANGELOG.md`
