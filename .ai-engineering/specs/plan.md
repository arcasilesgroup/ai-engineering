---
spec: spec-198
slug: cli-integration-pack-contract
status: draft
executor: build
safe_next_command: "/ai-build"
automation: semi
concern_count: 4
estimated_files: 12
reason: "Pack schema and validator; depends on spec-194/195/197 for evidence and surfaces"
execution_route:
  version: "1.0"
  executor: build
  automation: semi
---

# Plan — CLI Integration Pack Contract (spec-198)

## Phase 1: Schema + Validator (TDD)

- [ ] T-1 — Define integration pack YAML schema (integration.yml)
  - Agent: build
  - Files: `src/ai_engineering/packs/schema.py`, `src/ai_engineering/packs/schema.yml`
  - Gate: `pytest tests/unit/test_pack_schema.py -v`

- [ ] T-2 — Implement provenance lock validator (version/source/license/digest)
  - Agent: build
  - Files: `src/ai_engineering/packs/validator.py`
  - Principles applied: §10.5 TDD (fixture corpus for dangerous branches)
  - Gate: `pytest tests/unit/test_pack_validator.py -v`

## Phase 2: Redactor + Credential Assessment

- [ ] T-3 — Implement pack output redactor (extends harness redactor)
  - Agent: build
  - Files: `src/ai_engineering/packs/redactor.py`
  - Gate: `pytest tests/unit/test_pack_redactor.py -v`

- [ ] T-4 — Implement credential source assessor (store type, ACL, mode)
  - Agent: build
  - Files: `src/ai_engineering/packs/credential_assessor.py`
  - Gate: `pytest tests/unit/test_pack_credentials.py -v`

## Phase 3: Command Classifier + Helpers

- [ ] T-5 — Implement command classifier (read-only, mutation, production, destructive)
  - Agent: build
  - Files: `src/ai_engineering/packs/command_classifier.py`
  - Gate: `pytest tests/unit/test_command_classifier.py -v`

- [ ] T-6 — Implement preview/apply/readback helpers
  - Agent: build
  - Files: `src/ai_engineering/packs/helpers.py`
  - Gate: `pytest tests/unit/test_pack_helpers.py -v`

## Phase 4: Integration + Census

- [ ] T-7 — Build authorization census (single source for allowed integrations)
  - Agent: build
  - Files: `src/ai_engineering/packs/census.py`
  - Gate: `pytest tests/unit/test_pack_census.py -v`

- [ ] T-8 — Write integration tests: full pack lifecycle (validate → authorize → invoke)
  - Agent: build
  - Files: `tests/integration/test_pack_integration.py`
  - Gate: `pytest tests/integration/test_pack_integration.py -v`

- [ ] T-9 — Verify no MCP fallback is possible through packs
  - Agent: verify
  - Gate: `pytest tests/unit/test_no_mcp_fallback.py -v`

- [ ] T-10 — Documentation and CHANGELOG
  - Agent: build
  - Files: `docs/packs.md`, `CHANGELOG.md`
