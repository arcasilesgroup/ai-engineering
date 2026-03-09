---
id: "039"
slug: "observe-enrichment-phase-1"
status: "in-progress"
created: "2026-03-09"
size: "L"
tags: ["observability", "audit", "dashboards", "governance"]
branch: "feat/039-observe-enrichment-phase-1"
pipeline: "full"
decisions:
  - id: "D039-01"
    decision: "Replace ai-eng spec save CLI with LLM-driven spec creation"
    rationale: "CLI templates destroy rich planning content (Risks, Verification, Architecture). LLM adapts format to each situation."
  - id: "D039-02"
    decision: "Keep spec verify/catalog/list/compact CLI commands"
    rationale: "Read/validation commands remain useful. Only creation (spec save) moves to LLM."
  - id: "D039-03"
    decision: "Move _next_spec_number() and _slugify() to lib/parsing.py"
    rationale: "Reusable helpers for spec verify, catalog, and LLM-driven creation."
---

# Spec 039 — Observe Enrichment Phase 1

## Problem

1. **Audit events lack VCS context**: No branch, commit SHA, repo, or provider recorded in events. Cannot trace events to code changes.
2. **Dead emitters**: 4/5 emitters (`emit_scan_event`, `emit_build_event`, `emit_deploy_event`, `emit_session_event`) defined but never called.
3. **Observe at ~20%**: 5 dashboards exist but show minimal data vs the observe agent spec (missing Code Quality, Decision Health, Adoption, Lead Time, Change Failure Rate, Session Recovery, multi-variable Health score).
4. **Orphaned workflow CLI**: `commands/workflows.py` has commit/PR logic but no CLI registration.
5. **Release orchestrator bypass**: Uses internal `_log_audit_event()` instead of standard `emit_deploy_event()`.
6. **audit-log.ndjson gitignored**: Data lost between sessions/devs.
7. **spec save CLI destroys content**: Templates lose Risks, Verification, Architecture, Execution Plan sections produced by the LLM.

## Solution

### Part A: Remove spec save CLI, adopt LLM-driven spec creation

Delete `ai-eng spec save` command. The LLM writes spec.md/plan.md/tasks.md directly via Write tool, preserving all planning content. Keep `spec verify/catalog/list/compact` as read/validation utilities. Move `_next_spec_number()` and `_slugify()` to `lib/parsing.py`.

### Part B: Enrich AuditEntry with VCS context

Create `vcs/repo_context.py` (URL parsing + cache) and `git/context.py` (branch + commit SHA). Add 7 optional fields to AuditEntry. Inject in `_emit()` so all 5 existing callers get context automatically. Update 6 write sites outside `_emit()`.

### Part C: Wire orphaned modules

Register `workflow commit/pr/pr-only` CLI commands. Standardize release orchestrator with `emit_deploy_event()`.

### Part D: Expand observe dashboards

Add 8 signal aggregators to `signals.py`. Expand 5 dashboards to show data computable from existing sources (audit-log, decision-store.json, install-manifest.json, git log, checkpoint files).

### Part E: Track audit-log in git

Simplify `.gitignore` to track all `state/`. Reset audit-log for fresh start with enriched format.

## Scope

### In Scope

- Remove `ai-eng spec save` CLI command and tests
- Move helpers to `lib/parsing.py`
- Update `agents/plan.md`, `skills/spec/SKILL.md`, `skills/plan/SKILL.md`
- VCS context enrichment (`vcs/repo_context.py`, `git/context.py`)
- AuditEntry extension (7 optional fields)
- Inject context in `_emit()` + 6 write sites
- Workflow CLI wiring (3 commands)
- Release orchestrator standardization with `emit_deploy_event`
- 8 new signal aggregators in `signals.py`
- 5 dashboard expansions in `observe.py`
- `.gitignore` simplification + audit-log reset
- 8 new test files

### Out of Scope (deferred to Phase 2+)

- Wire `emit_scan_event`/`emit_build_event`/`emit_session_event` to actual agents
- Skill/agent tracking (needs `skill_invoked` event type)
- MTTR (needs issue tracker integration)
- Standards drift, noise ratio, escalation rate
- 4-week trend analysis with direction indicators

## Acceptance Criteria

1. `ai-eng spec --help` shows verify/catalog/list/compact but NOT save
2. `agents/plan.md` Spec-as-Gate Pattern uses Write tool, not CLI
3. `skills/spec/SKILL.md` has no CLI-Driven Path section
4. AuditEntry events include `vcs_provider`, `branch`, `commit_sha` when in a git repo
5. `ai-eng workflow commit --help` works
6. `ai-eng observe engineer` shows Code Quality, Build Activity, Lead Time sections
7. `ai-eng observe team` shows Decision Store Health, Adoption sections
8. `ai-eng observe ai` shows Session Recovery section
9. `ai-eng observe dora` shows Lead Time and Change Failure Rate sections
10. `ai-eng observe health` computes multi-variable score (not just gate+velocity)
11. `git status` shows `state/audit-log.ndjson` tracked
12. `ruff check` + `ruff format` + `ty` + `pytest` all pass

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| LLM forgets mandatory spec sections | MEDIUM | MEDIUM | `spec verify` post-write validates structure |
| AuditEntry optional fields break serialization | LOW | HIGH | Pydantic optional with default None |
| Git subprocess timeout in `_emit()` | MEDIUM | LOW | Module-level cache, fail-open |
| Resetting audit-log loses data | LOW | MEDIUM | Current data is only local gate_result events |
| Removing spec save breaks existing workflows | LOW | LOW | spec skill procedure is the primary path; CLI was convenience |

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D039-01 | Replace `ai-eng spec save` CLI with LLM-driven spec creation | CLI templates destroy rich planning content |
| D039-02 | Keep `spec verify/catalog/list/compact` CLI commands | Read/validation commands remain useful |
| D039-03 | Move `_next_spec_number()` and `_slugify()` to `lib/parsing.py` | Reusable helpers for both CLI and LLM paths |
