# Plan: spec-099 ai-autopilot Token Efficiency — Rewrite Orchestrator + Handlers

## Pipeline: standard
## Phases: 4
## Tasks: 12 (build: 9, verify: 3)

---

### Phase 1: Orchestrator (SKILL.md)
**Gate**: SKILL.md updated with context resolution, new Phase 5/6 summaries, and updated Thin Orchestrator Principle. No handler changes yet.

- [x] T-1.1: Update SKILL.md Step 0 (L33-39) — add context path resolution logic: detect languages/frameworks via stack-context.md, store resolved paths in `context_paths` list, replace "Include relevant language/framework context in subagent dispatch prompts" with "Pass context file paths to subagent prompts for on-demand reading" (agent: build)
- [x] T-1.2: Update SKILL.md Phase 5 summary (L76-84) — change "up to 3 rounds" to "1 round default, escalate to 2-3 on blocker findings only". Update Thin Orchestrator Principle (L113-122) to note skill files are read once per quality loop entry, not per round (agent: build)
- [x] T-1.3: Update SKILL.md Phase 6 summary (L86-93) — reference 2 consolidated doc subagents instead of 5. No flag changes (agent: build)

### Phase 2: Handler Rewrites
**Gate**: All 4 handlers rewritten. Each handler compiles (no broken references). phase-quality.md implements 1-round + escalation. phase-implement.md has wave-end guard. phase-deep-plan.md + phase-implement.md use context-by-reference.

- [x] T-2.1: Rewrite phase-quality.md — (1) Move skill file reads (L49-66) from per-round to loop entry: read ai-verify, ai-review, ai-governance SKILL.md once before Step 2 loop starts; (2) Compute diff once at Step 1 (L39), pass by reference to all agents; (3) Change escalation logic (L110-115): round passes when 0 blockers, critical/high flagged but non-blocking; (4) Default to 1 round, escalate only on blockers; (5) Self-Reports read once at loop entry, not per-round (agent: build)
- [x] T-2.2: Rewrite phase-implement.md — (1) Replace stack context embedding (L54-55) with path references: "Stack standards — agents read from these paths on demand: [context_paths from Phase 0]"; (2) Add Step 2e (new): wave-end guard dispatch — after Step 3 commit, dispatch single guard agent reviewing wave's cumulative `git diff`; (3) Add `skip_inline_guard: true` directive to build agent dispatch prompt (L47-65) (agent: build, blocked by T-1.1)
- [x] T-2.3: Rewrite phase-deep-plan.md — Replace stack context embedding (L36) with path references: "Stack contexts available at [context_paths] — read on demand if needed for planning decisions" (agent: build, blocked by T-1.1)
- [x] T-2.4: Update phase-deliver.md — Minor: update Step 2 (L61-78) references to reflect ai-pr now dispatches 2 doc subagents instead of 5 (agent: build)

### Phase 3: ai-pr Doc Agent Consolidation
**Gate**: ai-pr/SKILL.md Step 6.5 dispatches 2 agents instead of 5. Both agents are flag-gated. Diff computed once.

- [x] T-3.1: Rewrite ai-pr/SKILL.md Step 6.5 (L33-47) — consolidate 5 subagents to 2: Agent 1 (CHANGELOG + README, flag-gated), Agent 2 (solution-intent-sync + docs-portal + docs-quality-gate, flag-gated). Compute diff once before dispatch and pass to both agents (agent: build, blocked by T-2.4)

### Phase 4: Sync + Verify
**Gate**: All mirrors synced, unit tests pass, no regressions.

- [x] T-4.1: Run `python scripts/sync_command_mirrors.py` to sync IDE mirrors after all SKILL.md edits (agent: build, blocked by T-3.1)
- [x] T-4.2: Run `source .venv/bin/activate && python -m pytest tests/unit/ -q` -- 2434 passed — all existing tests must pass (agent: verify, blocked by T-4.1)
- [x] T-4.3: Verify cross-file consistency -- 1 stale ref fixed in phase-quality.md Purpose — grep for stale references: "3 rounds", "5 documentation subagents", "per-file guard" across all modified files. Zero stale references (agent: verify, blocked by T-4.1)
- [x] T-4.4: Verify handler-to-SKILL.md alignment -- all 4 optimizations reflected in SKILL.md summaries — each handler's optimization (context-by-reference, 1-round, wave-guard, 2-agent docs) must be reflected in SKILL.md summaries (agent: verify, blocked by T-4.1)
