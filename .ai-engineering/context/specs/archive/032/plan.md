---
spec: "032"
title: "Implementation Plan — ai-engineering v3"
status: "in-progress"
phases: 8
---

# Plan: ai-engineering v3

## Phase 0: Prerequisites + Setup
- Create spec scaffold and activate
- Fix AuditEntry model: `detail: str | dict[str, Any] | None`
- Instrument `run_gate()` to emit audit events
- Add signal emission utilities

## Phase 1: Core Agent Restructure
- Create `agents/scan.md` (7-mode unified scanner)
- Create `agents/release.md` (ALM + GitOps + work-items)
- Create `agents/observe.md` (observatory, 5 modes)
- Rewrite `agents/plan.md` (pipeline strategy + checkpoints + governance)
- Rewrite `agents/build.md` (20 stacks, code-simplifier)
- Rewrite `agents/write.md` (docs with modes)
- Remove `agents/review.md` (absorbed by scan)
- Remove `agents/triage.md` (absorbed by release)

## Phase 2: Skill Consolidation (47 → 33)
- New: code-simplifier, observe, feature-gap, create, delete
- Merge: test, security, quality, governance, docs, work-item, db, architecture, perf
- Keep: discover, spec, cleanup, explain, build, debug, refactor, api, cli, infra, cicd, a11y, commit, pr, release, changelog, risk, standards
- Eliminate: multi-agent, improve, prompt, agent-lifecycle, skill-lifecycle, agent-card, references

## Phase 3: Python CLI New Commands
- Extend existing typer CLI with: observe, integrity, compliance, ownership, gates, signals, checkpoint, stack-detect, version, changelog, decisions, triage, scan-report, metrics
- Add lib modules: signals.py, render.py, stacks.py

## Phase 4: State Layer
- Extend audit-log.ndjson schema for enriched events
- Add session-checkpoint.json support
- Operationalize decision-store.json

## Phase 5: Slash Commands + Instruction Files
- Update slash commands for 33 skills
- Update manifest.yml (33 skills, work-items enabled)
- Update CLAUDE.md, AGENTS.md

## Phase 6: Observability Bootstrap
- Wire scan agent to Python CLI for deterministic checks
- Implement observe skill (5 modes)
- Bootstrap DORA metrics

## Phase 7: Work-Item Integration
- Configure GitHub Projects sync
- Test bidirectional spec-to-issue sync

## Phase 8: Validation
- Integrity checks, scan platform, security scan
- Session checkpoint + recovery test
- Pipeline auto-classification test
- Backward compatibility verification
