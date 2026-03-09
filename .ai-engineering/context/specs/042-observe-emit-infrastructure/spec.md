---
spec: "042"
title: "Observe Emit Infrastructure — Wire Dead Emitters, Enrich Session, Noise Ratio"
size: M-L
pipeline: standard
created: "2026-03-09"
branch: "feat/042-observe-emit-infrastructure"
---

# Spec 042 — Observe Emit Infrastructure

## Problem

Observability dashboards are data-starved: `emit_scan_event()` and `emit_build_event()` are dead code (defined in `audit.py` but never called from production). `emit_session_event()` only receives `checkpoint_saved=True` — no tokens, skills, or decisions. Gate pipeline has no auto-remediation tracking, preventing noise ratio computation. Team dashboard at 55% coverage, AI at 70%.

## Solution

Wire existing dead emitters via agent instruction updates, enrich session event with checkpoint context, add auto-remediation tracking to gate pipeline, create new aggregators, and expand Team + AI dashboards.

### Approach

Skills and agents are LLM-side (markdown instructions, no Python dispatcher). Emission bridge: agents call `ai-eng signals emit <type> --detail '{...}'` CLI. For Python-side wiring: enrich `emit_session_event()` call in `checkpoint.py` with data from checkpoint file, and add `auto_remediated` count to `emit_gate_event()`.

## Scope

### In Scope

1. **Wire dead emitters** — update build/scan agent instructions to emit via CLI after operations
2. **Enrich session event** — pass checkpoint context (task, progress, skills) at save time
3. **Auto-remediation tracking** — detect when ruff --fix modifies files, include count in gate event
4. **New aggregators** — `noise_ratio_from()` in `signals.py`
5. **Dashboard expansion** — Team: Token Economy, Noise Ratio sections. AI: enriched Context Efficiency
6. **Health score** — add noise ratio as optional component

### Out of Scope

- `emit_skill_event()` / `emit_agent_event()` — requires Python-side dispatcher (no skill loader exists)
- Escalation Rate — no escalation tracking mechanism exists
- Standards Drift — needs architecture scan event wiring (separate spec)
- MTTR — needs external issue tracker integration

## Acceptance Criteria

1. `emit_session_event()` in `checkpoint.py` passes real data: task name, progress, skills list
2. Gate pipeline tracks auto-remediated check count in `gate_result` detail
3. Build agent instructions include `ai-eng signals emit build_complete` step
4. Scan agent instructions include `ai-eng signals emit scan_complete` step
5. `observe team` shows Token Economy and Noise Ratio sections
6. `observe ai` shows enriched Context Efficiency with real session data
7. `observe health` includes noise ratio as optional component
8. All existing tests pass, new tests cover new functions
9. `ruff check` + `ruff format` + `ty` clean

## Risks

1. **Agent instruction compliance** — LLM agents may not always execute emission steps → mitigated by clear, minimal instructions
2. **Checkpoint data availability** — checkpoint file may not exist → fail-open with defaults
3. **Auto-remediation detection** — ruff --fix output parsing fragile → use exit code + file hash comparison

## Decisions

- D042-001: No new `emit_skill_event` or `emit_agent_event` — Python has no skill/agent dispatcher to hook into; wait for dispatcher (future spec)
- D042-002: Auto-remediation detected by comparing staged file hashes before/after ruff --fix
- D042-003: Session enrichment reads checkpoint file at save time (synchronous, fail-open)
- D042-004: Noise ratio = auto_remediated_checks / total_checks (0 if no gate data)
