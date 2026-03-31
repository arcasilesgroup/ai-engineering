---
spec: spec-099
title: "ai-autopilot Token Efficiency — Rewrite Orchestrator + Handlers"
status: draft
effort: large
refs: []
---

## Summary

A deep audit of `ai-autopilot` reveals systematic token waste across its 6-phase pipeline. The worst offenders: Phase 5 (Quality Loop) dispatches up to 45 sub-agents across 3 rounds, Phase 2+4 duplicate identical stack contexts N*W times across parallel agents, and Phase 4 hides per-file guard advisory calls inside each build agent. Phase 6 spawns 5 documentation subagents that each read the diff independently. Combined, these patterns multiply token consumption by 3-9x beyond what is necessary to achieve the same quality outcomes. This spec rewrites SKILL.md and 4 handlers to centralize optimization logic in the orchestrator, reducing dispatches ~65% and context duplication ~55% without degrading quality gates.

## Goals

- Reduce Phase 5 from 3 mandatory rounds to 1 default round with conditional escalation (escalate to round 2-3 only when blockers are found)
- Move guard advisory in Phase 4 from per-file-edit to per-wave (1 guard call at wave end instead of N calls per file)
- Eliminate redundant stack context loading: orchestrator loads contexts once, agents read on demand by path reference instead of receiving embedded content
- Consolidate Phase 6 documentation subagents from 5 to 2 (CHANGELOG+README agent, docs-portal+quality-gate agent)
- All existing tests in `tests/unit/` pass after changes
- Run `python scripts/sync_command_mirrors.py` after all SKILL.md edits
- No degradation of quality gate enforcement: blockers still halt PR, critical/high still flag

## Non-Goals

- Modifying `ai-review` agent internals (sub-agent structure stays as-is)
- Modifying `ai-verify` or `ai-guard` agent definitions
- Modifying `ai-build.md` agent definition (guard-per-wave is enforced in the autopilot handler, not in the shared agent)
- Adding `--fast` / `--full` / `--lean` flags — the optimized behavior becomes the default
- Changing Phase 1 (Decompose) or Phase 3 (Orchestrate) — their token cost is negligible
- Changing spec decomposition logic or DAG construction
- Touching `CLAUDE.md`, `manifest.yml`, or agent definitions in `.claude/agents/`

## Decisions

- **D-099-01**: Phase 5 currently runs up to 3 rounds, escalating on any blocker/critical/high finding. New behavior: default to 1 round. Escalation trigger narrowed to blocker-severity only — if round 1 finds any blocker findings, run round 2. If round 2 still has unresolved blockers, run round 3. Critical/high findings do NOT trigger escalation — they are flagged in the PR but do not add rounds. Pass condition updated accordingly: a round passes when zero blocker findings remain (critical/high are reported but non-blocking for escalation). Rationale: most clean specs pass in round 1. Rounds 2-3 exist only for blocker remediation, where the cost of extra rounds is justified by the severity. This reduces Phase 5 dispatches from up to 45 (3 rounds * 3 agents * up to 5 review sub-agents) to 3-15 in the common case.

- **D-099-02**: Guard advisory moves from per-file to per-wave in Phase 4. Implementation: `phase-implement.md` adds a wave-end guard step that dispatches a single guard advisory agent after each wave completes (reviewing the wave's cumulative `git diff`). Build agents dispatched by autopilot receive an explicit instruction to suppress their built-in per-file guard (ai-build.md lines 67-69) via a `skip_inline_guard: true` directive in the dispatch prompt. This creates an intentional override: autopilot's wave-end guard replaces ai-build's per-file guard within the autopilot context only. Outside autopilot (e.g., `/ai-dispatch`), ai-build retains its per-file guard behavior unchanged. Rationale: guard at wave granularity catches the same governance issues with 1 dispatch instead of N (where N = files touched per sub-spec per wave, typically 3-15).

- **D-099-03**: Stack contexts are loaded once by the orchestrator and passed as path references, not embedded content. Implementation: SKILL.md Phase 0 reads `stack-context.md`, detects languages/frameworks, and records the resolved context file paths in a `context_paths` list. Handlers pass these paths to subagents with the instruction "Read these files if you need stack guidance" instead of embedding 1,600+ lines of context content into every agent prompt. Rationale: agents that don't need stack context (e.g., verify, guard) skip the reads entirely. Agents that do need it (build, plan) read on demand. This eliminates N*W copies of identical content from agent prompts.

- **D-099-04**: Phase 6 documentation subagents consolidate from 5 to 2. The 5-agent pattern lives in `ai-pr/SKILL.md` (lines 33-47), not in `phase-deliver.md` which merely delegates to ai-pr. Therefore the change targets `ai-pr/SKILL.md` directly. Agent 1: CHANGELOG + README updates (single diff read). Agent 2: docs-portal sync + docs-quality-gate + solution-intent-sync (single diff read). Rationale: 5 agents each reading the diff independently means 5x diff transmission. 2 agents with broader scope achieve the same output with 2x diff reads — a 60% reduction in Phase 6 context overhead.

- **D-099-05**: Phase 5 skill files (ai-verify, ai-review, ai-governance SKILL.md) are read once at quality-loop entry, not re-read per round. If escalation triggers additional rounds, the already-loaded skill content is reused. Rationale: these files (344 lines total) are static during the quality loop. Re-reading 3x wastes 688 lines of I/O per escalation cycle.

- **D-099-06**: Phase 5 git diff and Self-Reports are computed/read once at quality-loop entry and passed by reference to assessment agents. Currently they are re-computed and re-read per round (up to 9x for diff, N*3 for self-reports). Rationale: neither the diff nor the self-reports change between quality rounds — only the fix agents' output changes. Assessment agents in round 2+ receive the original diff plus a delta of fixes applied since round 1.

## Files Changed

| File | Change type |
|------|------------|
| `.claude/skills/ai-autopilot/SKILL.md` | Rewrite Phase 0 (add context resolution), Phase 5 (conditional escalation), Phase 6 (2-agent docs) |
| `.claude/skills/ai-autopilot/handlers/phase-quality.md` | Rewrite: 1-round default, skill-file caching, diff/self-report single-read, escalation logic |
| `.claude/skills/ai-autopilot/handlers/phase-implement.md` | Rewrite: remove per-file guard instruction, add wave-end guard step, context-by-reference |
| `.claude/skills/ai-autopilot/handlers/phase-deep-plan.md` | Rewrite: context-by-reference instead of context-embedded for plan agents |
| `.claude/skills/ai-autopilot/handlers/phase-deliver.md` | Minor: update ai-pr delegation references |
| `.claude/skills/ai-pr/SKILL.md` | Rewrite: consolidate 5 doc subagents to 2 (D-099-04) |

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| 1-round default misses issues that round 2-3 would catch | High | Escalation is automatic on blockers. Critical/high still flag in PR. Monitor first 5 autopilot runs for quality regression |
| Guard per-wave misses governance issue introduced mid-wave | Medium | Wave-end guard sees cumulative diff, which includes all mid-wave changes. Only intra-file ordering issues could theoretically be missed, but guard operates on diff not sequence |
| Agents fail to read context paths on demand | Medium | Phase 0 validates that all resolved paths exist before proceeding. Agents receive explicit "Read X if needed" instruction, not a silent reference |
| 2-agent docs consolidation produces lower quality docs | Low | Same content, fewer agents. Each agent has broader scope but same diff input. Quality gate agent is still present |
| Skill-file caching in Phase 5 serves stale content if a quality fix modifies a skill | Low | Quality fixes target implementation code, not skill definitions. If a skill file is modified during quality loop (extremely rare), the cached version is still valid for assessment purposes |
| Build agent ignores `skip_inline_guard` directive and runs per-file guard anyway | Medium | The directive is an explicit prompt instruction, not a code flag. If ai-build's context window prioritizes its own SKILL.md over the dispatch prompt, guard runs twice (per-file + per-wave). Mitigation: test with 2 autopilot runs and verify guard dispatch count matches expected 1-per-wave |
| ai-pr/SKILL.md change affects non-autopilot PR workflows | Medium | ai-pr is shared by `/ai-pr` standalone. The 2-agent consolidation must preserve the same doc outputs. Validate by running `/ai-pr` standalone after the change |

## References

- Audit source: `ai-explore` agent deep analysis of autopilot pipeline (this session)
- Current handler files: `.claude/skills/ai-autopilot/handlers/phase-*.md`
- Agent definitions: `.claude/agents/ai-{build,review,verify,guard}.md`
- Context loading protocol: `.ai-engineering/contexts/stack-context.md`
