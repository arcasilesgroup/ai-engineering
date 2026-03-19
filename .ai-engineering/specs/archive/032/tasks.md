---
spec: "032"
title: "Tasks — ai-engineering v3"
status: "done"
total: 48
completed: 48
---

# Tasks: ai-engineering v3

## Phase 0: Prerequisites + Setup
- [x] 0.1 Create spec scaffold (spec.md, plan.md, tasks.md)
- [x] 0.2 Activate spec in _active.md
- [x] 0.3 Fix AuditEntry model: detail field supports str | dict | None
- [x] 0.4 Instrument run_gate() to emit audit events after execution
- [x] 0.5 Add signal emission utility (append NDJSON to audit-log)

## Phase 1: Core Agent Restructure
- [x] 1.1 Create agents/scan.md (7-mode unified scanner)
- [x] 1.2 Create agents/release.md (ALM + GitOps + work-items)
- [x] 1.3 Create agents/observe.md (observatory, 5 modes)
- [x] 1.4 Rewrite agents/plan.md (pipeline strategy + checkpoints + governance)
- [x] 1.5 Rewrite agents/build.md (20 stacks, code-simplifier)
- [x] 1.6 Rewrite agents/write.md (docs with modes)
- [x] 1.7 Remove agents/review.md (absorbed by scan)
- [x] 1.8 Remove agents/triage.md (absorbed by release)

## Phase 2: Skill Consolidation (47 → 33)
- [x] 2.1 Create skill: code-simplifier
- [x] 2.2 Create skill: observe
- [x] 2.3 Create skill: feature-gap
- [x] 2.4 Create skill: create (agent/skill lifecycle)
- [x] 2.5 Create skill: delete (agent/skill lifecycle)
- [x] 2.6 Merge skill: test (test-plan + test-run + test-gap → modes)
- [x] 2.7 Merge skill: security (sec-review + sec-deep + sbom + deps → modes)
- [x] 2.8 Merge skill: quality (audit + sonar + code-review + docs-audit → modes)
- [x] 2.9 Merge skill: governance (integrity + compliance + ownership + install → modes)
- [x] 2.10 Merge skill: docs (docs + simplify → modes)
- [x] 2.11 Merge skill: work-item (work-item + triage → modes)
- [x] 2.12 Merge skill: db (db + data-model)
- [x] 2.13 Rename skill: architecture (from arch-review)
- [x] 2.14 Rename skill: perf (from perf-review)
- [x] 2.15 Remove eliminated skills (multi-agent, improve, prompt, agent-lifecycle, skill-lifecycle, agent-card, references)
- [x] 2.16 Create skill: build (explicit build skill)

## Phase 3: Python CLI New Commands
- [x] 3.1 Add lib/signals.py (NDJSON read/write/query)
- [x] 3.2 Add lib/render.py (rich markdown output)
- [x] 3.3 Add cli_commands/observe.py (5 modes: engineer/team/ai/dora/health)
- [x] 3.4 Add cli_commands/signals_cmd.py (emit/query)
- [x] 3.5 Add cli_commands/checkpoint.py (save/load)
- [x] 3.6 Add cli_commands/decisions_cmd.py (list/expire-check)
- [x] 3.7 Add cli_commands/scan_report.py (format raw findings)
- [x] 3.8 Add cli_commands/metrics.py (collect signals → dashboard data)

## Phase 4: State Layer
- [x] 4.1 Add enriched event models (via state/audit.py emit functions)
- [x] 4.2 Session checkpoint via cli_commands/checkpoint.py
- [x] 4.3 Checkpoint save/load operational

## Phase 5: Slash Commands + Instruction Files
- [x] 5.1 Update/create slash commands for 33 skills
- [x] 5.2 Update manifest.yml (33 skills, 6 agents, work-items enabled)
- [x] 5.3 Update CLAUDE.md
- [x] 5.4 Update AGENTS.md

## Phase 6: Observability Bootstrap
- [x] 6.1 Wire observe skill to call ai-eng observe CLI
- [x] 6.2 Wire scan skill to call ai-eng gates CLI
- [x] 6.3 Bootstrap DORA metrics from git history

## Phase 7: Work-Item Integration
- [x] 7.1 Update manifest.yml work_items section
- [x] 7.2 Update work-item skill for GitHub Projects

## Phase 8: Validation
- [x] 8.1 Ruff lint + format pass on all new files
- [x] 8.2 Type checker (ty) passes on all new files
- [x] 8.3 Unit tests pass (786/786)
- [x] 8.4 Integration tests pass (417/417)
- [x] 8.5 Fix broken tests (sonar gate, validator skill/agent paths)
- [x] 8.6 CLI standalone: ai-eng observe health/dora/engineer/team/ai
- [x] 8.7 CLI standalone: ai-eng checkpoint load
- [x] 8.8 CLI standalone: ai-eng decision list/expire-check
- [x] 8.9 Backward compatibility: /ai:commit, /ai:pr slash commands work
- [x] 8.10 GitHub Projects configuration (manual step)
