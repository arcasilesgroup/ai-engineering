---
spec: spec-196
slug: lean-bootstrap-and-observation
status: draft
executor: build
safe_next_command: "/ai-build"
automation: semi
concern_count: 3
estimated_files: 10
reason: "Root budget and bootstrap reduction; depends on spec-194 for measurement"
execution_route:
  version: "1.0"
  executor: build
  automation: semi
---

# Plan — Lean Bootstrap and Observation (spec-196)

## Phase 1: Root Refactor (TDD)

- [ ] T-1 — Define minimum root payload schema (identity, gates, commands, ticket pointer)
  - Agent: build
  - Files: `src/ai_engineering/bootstrap/schema.py`
  - Gate: `pytest tests/unit/test_bootstrap_schema.py -v`

- [ ] T-2 — Refactor CANONICAL.md template to ≤2 KiB
  - Agent: build
  - Files: `src/ai_engineering/templates/project/CANONICAL.md`
  - Principles applied: §10.1 KISS (delete, don't add)
  - Gate: `wc -c src/ai_engineering/templates/project/CANONICAL.md` ≤ 2048

- [ ] T-3 — Remove all "read every session" directives from generated roots
  - Agent: build
  - Files: `src/ai_engineering/templates/project/CANONICAL.md`, `scripts/sync_mirrors/core.py`
  - Gate: `grep -r "read every session" src/ai_engineering/templates/` returns empty

## Phase 2: Session Ticket

- [ ] T-4 — Implement deterministic session ticket generator
  - Agent: build
  - Files: `src/ai_engineering/bootstrap/ticket.py`
  - Principles applied: §10.6 SDD (deterministic, not LLM-generated)
  - Gate: `pytest tests/unit/test_session_ticket.py -v`

- [ ] T-5 — Implement ticket schema with task/risk/path inputs
  - Agent: build
  - Files: `src/ai_engineering/bootstrap/ticket_schema.py`
  - Gate: `pytest tests/unit/test_ticket_schema.py -v`

## Phase 3: Hook Cleanup

- [ ] T-6 — Remove additionalContext emission from runtime hooks
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/runtime-progressive-disclosure.py`, `.ai-engineering/scripts/hooks/runtime-session-start.py`
  - Principles applied: §10.1 KISS (delete injection code)
  - Gate: `grep -r "additionalContext" .ai-engineering/scripts/hooks/` returns empty

- [ ] T-7 — Remove automatic tracked writes from observation hooks
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/instinct-observe.py`, `.ai-engineering/scripts/hooks/observe.py`
  - Gate: `pytest tests/unit/test_hook_no_writes.py -v`

## Phase 4: Observation + Output

- [ ] T-8 — Refactor session-watch to opt-in cold-path sweep
  - Agent: build
  - Files: `.claude/skills/ai-session-watch/SKILL.md`
  - Gate: SKILL.md no longer describes always-on observation

- [ ] T-9 — Implement output capping (8 KiB/200, 4 KiB/100, 2 KiB/50)
  - Agent: build
  - Files: `src/ai_engineering/core/output/renderer.py`
  - Gate: `pytest tests/unit/test_output_caps.py -v`

- [ ] T-10 — Verify harness shows reduced root bytes and zero injection
  - Agent: verify
  - Gate: `uv run python -c "from ai_engineering.harness.adapters.claude import ClaudeAdapter; r=ClaudeAdapter().collect(); assert r.root.bytes <= 2048; assert r.hooks.injection_count == 0"`
