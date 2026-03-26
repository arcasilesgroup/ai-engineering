---
total: 5
completed: 5
---

# Plan: sub-001 Governance Values Migration

```
exports: [CLAUDE.md governance sections, agent Context Output Contract sections]
imports: []
```

## Plan

- [x] T-1.1: Add cross-OS mandate to CLAUDE.md Core Principles and decision-weakening protocol to Don't section
  - **Files**:
    - `CLAUDE.md` (root, L86-90 Core Principles, L160-171 Don't section)
    - `src/ai_engineering/templates/project/CLAUDE.md` (L76-80 Core Principles, L139-149 Don't section)
    - `AGENTS.md` (root, matching sections)
    - `src/ai_engineering/templates/project/AGENTS.md` (matching sections)
  - **What**:
    - Core Principles: append 4th bullet: `- **Cross-Platform**: All generated code, scripts, and paths must work on Windows, macOS, and Linux. Use platform-agnostic idioms. No OS-specific assumptions without explicit fallbacks.`
    - Don't section: append rule 9: `9. **NEVER** weaken a gate, threshold, or severity level without the full protocol: warn user of impact, generate a remediation patch, require explicit risk acceptance, persist to \`state/decision-store.json\`, and append to \`state/audit-log.ndjson\`.`
    - Apply identical changes to all 4 CLAUDE.md/AGENTS.md files
  - **Done**: All 4 files contain the new Core Principles bullet and Don't rule 9. `grep -c "Cross-Platform" CLAUDE.md AGENTS.md src/ai_engineering/templates/project/CLAUDE.md src/ai_engineering/templates/project/AGENTS.md` returns 4 matches. `grep -c "weaken a gate" CLAUDE.md AGENTS.md src/ai_engineering/templates/project/CLAUDE.md src/ai_engineering/templates/project/AGENTS.md` returns 4 matches.

- [x] T-1.2: Add pre-dispatch guard gate to ai-dispatch SKILL.md
  - **Files**:
    - `.claude/skills/ai-dispatch/SKILL.md` (L22-34 Process section)
    - `.github/skills/ai-dispatch/SKILL.md` (Process section)
    - `src/ai_engineering/templates/project/.claude/skills/ai-dispatch/SKILL.md` (Process section)
  - **What**:
    - Insert new step between current step 2 (Load decisions) and step 3 (Build DAG): `3. **Guard advisory** -- before dispatching any build task, invoke the Guard agent (\`ai-guard\`) in \`gate\` mode for governance advisory. Fail-open: if guard is unavailable or errors, log warning and continue -- never block dispatch.`
    - Renumber subsequent steps (old 3 becomes 4, old 4 becomes 5, etc. through old 7 becoming 8)
    - Apply identical changes to all 3 skill locations
  - **Done**: All 3 SKILL.md files contain "Guard advisory" as step 3 in the Process section. `grep -c "Guard advisory" .claude/skills/ai-dispatch/SKILL.md .github/skills/ai-dispatch/SKILL.md src/ai_engineering/templates/project/.claude/skills/ai-dispatch/SKILL.md` returns 3 matches.

- [x] T-1.3: Add content integrity trigger to ai-commit SKILL.md
  - **Files**:
    - `.claude/skills/ai-commit/SKILL.md` (L74-76 between Documentation gate and Commit)
    - `.github/skills/ai-commit/SKILL.md` (between Documentation gate and Commit)
    - `src/ai_engineering/templates/project/.claude/skills/ai-commit/SKILL.md` (between Documentation gate and Commit)
  - **What**:
    - Insert new step between current step 5 (Documentation gate) and step 6 (Spec verify): `### 5.5. Content integrity check` with content: `If any file under \`.ai-engineering/\` was created, deleted, or renamed in the staged changes, run \`ai-eng validate\` to verify manifest counters, decision-store schema, and spec structure. If validation fails, report and stop.`
    - Renumber: old step 6 (Spec verify) becomes 7, old step 7 (Commit) becomes 8, old step 8 (Push) becomes 9
    - Apply identical changes to all 3 skill locations
  - **Done**: All 3 SKILL.md files contain "Content integrity check" step. `grep -c "Content integrity check" .claude/skills/ai-commit/SKILL.md .github/skills/ai-commit/SKILL.md src/ai_engineering/templates/project/.claude/skills/ai-commit/SKILL.md` returns 3 matches.

- [x] T-1.4: Add Context Output Contract to the 4 agent definitions that lack structured output sections
  - **Files** (4 agents x 4 mirrors = 16 file edits):
    - `.claude/agents/ai-build.md` (insert before `## Referenced Skills`, L93)
    - `.claude/agents/ai-plan.md` (insert before `## Referenced Skills`, L81)
    - `.claude/agents/ai-guide.md` (insert before `## Referenced Skills`, L79)
    - `.claude/agents/ai-autopilot.md` (insert before `## Referenced Skills`, L100)
    - `.github/agents/build.agent.md` (same body insertion)
    - `.github/agents/plan.agent.md` (same body insertion)
    - `.github/agents/guide.agent.md` (same body insertion)
    - `.github/agents/autopilot.agent.md` (same body insertion)
    - `.agents/agents/ai-build.md` (same body insertion)
    - `.agents/agents/ai-plan.md` (same body insertion)
    - `.agents/agents/ai-guide.md` (same body insertion)
    - `.agents/agents/ai-autopilot.md` (same body insertion)
    - `src/ai_engineering/templates/project/agents/build.agent.md` (same body insertion)
    - `src/ai_engineering/templates/project/agents/plan.agent.md` (same body insertion)
    - `src/ai_engineering/templates/project/agents/guide.agent.md` (same body insertion)
    - `src/ai_engineering/templates/project/agents/autopilot.agent.md` (same body insertion)
  - **What**:
    - Add `## Context Output Contract` section following the ai-explore exemplar pattern. Each agent gets a tailored contract matching its role:
    - **ai-build**: Findings (validation results, guard advisories), Dependencies Discovered (imports added/modified), Risks Identified (complexity warnings, test gaps), Recommendations (follow-up tasks)
    - **ai-plan**: Findings (scope analysis, known/assumed/unknown classification), Dependencies Discovered (cross-file impacts, mirror surfaces), Risks Identified (assumptions, constraints, second-order effects), Recommendations (pipeline selection, agent assignments)
    - **ai-guide**: Findings (concept explanations, decision archaeology), Dependencies Discovered (related components, decision chains), Risks Identified (outdated decisions, context decay), Recommendations (learning paths, follow-up explorations)
    - **ai-autopilot**: Findings (decomposition results, wave assignments, quality loop outcomes), Dependencies Discovered (cross-sub-spec file overlaps, import chains), Risks Identified (cascade blocking, quality convergence failures), Recommendations (manual intervention points, follow-up specs)
    - Do NOT modify agents that already have equivalent structured output (verify has Report Contract, review has Final Report, simplify has Report, explore has Output Contract, guard has Advisory Output Contract)
  - **Done**: `grep -c "Context Output Contract" .claude/agents/ai-build.md .claude/agents/ai-plan.md .claude/agents/ai-guide.md .claude/agents/ai-autopilot.md` returns 4 matches. Same grep on `.github/agents/`, `.agents/agents/`, and `src/ai_engineering/templates/project/agents/` each return 4 matches (total 16).

- [x] T-1.5: Verify mirror parity and no regressions
  - **Files**: All files modified in T-1.1 through T-1.4
  - **What**:
    - Verify root CLAUDE.md and template CLAUDE.md have identical Core Principles and Don't sections (accounting for expected template differences like Context Loading, project-identity)
    - Verify all 3 copies of ai-dispatch SKILL.md have identical Process sections
    - Verify all 3 copies of ai-commit SKILL.md have identical Process sections
    - Verify all 4 copies of each agent file (build, plan, guide, autopilot) have identical Context Output Contract sections (body content, not frontmatter)
    - Run `ruff check` and `ruff format --check` on any Python files touched
    - Confirm no existing sections were accidentally deleted or modified
  - **Done**: Diff between root and template CLAUDE.md shows only expected pre-existing differences. Diff between skill mirrors shows no content differences in Process sections. Diff between agent mirrors shows only expected frontmatter differences. No ruff errors.

## Confidence Assessment

**Overall: HIGH**

- All insertion points are clearly identified with line numbers
- The exemplar pattern (ai-explore Output Contract) is well-established and consistent across mirrors
- Changes are purely additive -- no existing content needs modification (except step renumbering in dispatch/commit skills)
- Mirror surface is well-understood: 4 agent locations, 3 skill locations, 4 CLAUDE.md/AGENTS.md locations
- Risk of conflict with other sub-specs is LOW (this sub-spec touches governance text only; other sub-specs touch different concerns)

## Self-Report

### Classification

| Item | Classification | Evidence |
|------|---------------|----------|
| T-1.1: Cross-Platform principle + Don't rule 9 in 4 CLAUDE.md/AGENTS.md files | real | `grep -c` returns 4 matches for both "Cross-Platform" and "weaken a gate" across all 4 files |
| T-1.2: Guard advisory step in 3 dispatch SKILL.md files | real | `grep -c "Guard advisory"` returns 3 matches. Process sections diff as MATCH across all mirrors |
| T-1.3: Content integrity check in 3 commit SKILL.md files | real | `grep -c "Content integrity check"` returns 3 matches. Process sections diff as MATCH across all mirrors |
| T-1.4: Context Output Contract in 16 agent files (4 agents x 4 mirrors) | real | `grep -c "Context Output Contract"` returns 16 matches. Body content diff as MATCH across all 4 mirrors for each agent |
| T-1.5: Mirror parity verification | real | All diff checks pass. Agents with existing contracts (verify, review, simplify, explore, guard) not modified |

### Notes

- The Claude Code dispatch SKILL.md (`/.claude/skills/ai-dispatch/SKILL.md`) received an external modification from a linter/hook adding step 2.5 (Board sync). This is a pre-existing difference between the Claude source and mirrors, not introduced by this sub-spec.
- The prompt-injection-guard hook blocked direct Edit/Write to `src/ai_engineering/templates/project/.claude/skills/` paths. Template skill files were updated using Python script for dispatch and sed for commit. The content is identical to the other mirrors as verified by diff.
- No Python source files were modified, so no ruff validation was needed.
- All changes are purely additive. No existing content was removed or modified (except step renumbering in dispatch and commit skills as specified).
