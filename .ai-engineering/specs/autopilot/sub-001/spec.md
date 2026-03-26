---
id: sub-001
parent: spec-080
title: "Governance Values Migration"
status: planning
files: [CLAUDE.md, AGENTS.md, ".claude/skills/ai-dispatch/SKILL.md", ".claude/skills/ai-commit/SKILL.md", ".claude/agents/ai-build.md", ".claude/agents/ai-plan.md", ".claude/agents/ai-verify.md", ".claude/agents/ai-guard.md", ".claude/agents/ai-review.md", ".claude/agents/ai-explore.md", ".claude/agents/ai-guide.md", ".claude/agents/ai-simplify.md", ".claude/agents/ai-autopilot.md"]
depends_on: []
---

# Sub-Spec 001: Governance Values Migration

## Scope
Restore the 5 critical governance values lost when framework-contract.md was eliminated (DEC-027): cross-OS mandate in CLAUDE.md Core Principles, decision-weakening protocol in CLAUDE.md Don't section, pre-dispatch guard gate in ai-dispatch SKILL.md, content integrity trigger in ai-commit SKILL.md, and Context Output Contract in all 9 agent definitions. Mirror all changes to templates and IDE surfaces.

## Exploration

### Existing Files

| File | Summary | Key Sections | Output Contract Status |
|------|---------|-------------|----------------------|
| `CLAUDE.md` (root) | Top-level instruction file. 185 lines. Sections: Workflow Orchestration (10 subsections), Task Management, Core Principles (3 bullets), Agent Selection table, Platform Mirrors, Skills listing, Effort Levels, Quality Gates, Observability, Don't (8 rules), Source of Truth. | Core Principles (L86-90): 3 bullets -- Simplicity First, No Laziness, Minimal Impact. Don't (L160-171): 8 NEVER rules. | N/A |
| `CLAUDE.md` (template) | Template equivalent at `src/ai_engineering/templates/project/CLAUDE.md`. 185 lines. Identical structure to root CLAUDE.md. Differences: template has `## 10. Context Loading` and `project-identity.md` load instruction; template AGENTS.md omits autopilot row; template Observability uses `PostToolUse(Skill)` hook name vs root's `UserPromptSubmit(/ai-*)`. | Same insertion points as root. | N/A |
| `AGENTS.md` (root) | Generated file at root. Title `# CLAUDE.md`. Mirrors CLAUDE.md but omits: Context Loading section, project-identity load, autopilot row, Effort Levels section. Uses `PostToolUse(Skill)` hook name. | Same Core Principles and Don't sections as CLAUDE.md. | N/A |
| `AGENTS.md` (template) | Template at `src/ai_engineering/templates/project/AGENTS.md`. Same content as template CLAUDE.md (title `# CLAUDE.md`). | Same. | N/A |
| `.claude/skills/ai-dispatch/SKILL.md` | 149 lines. Execution engine skill. Sections: Purpose, When to Use, Process (7 steps), Task Statuses, Two-Stage Review, DAG Construction, Subagent Context, Stuck Protocol, Progress Tracking, Resume Protocol, Handler Dispatch Table, Common Mistakes, Integration. | Process step 4 (L26-31): Execute phase by phase. No guard gate before dispatch. | N/A |
| `.claude/skills/ai-commit/SKILL.md` | 117 lines. Governed commit pipeline. Steps 0-8: Auto-branch, Work item context, Stage, Format, Lint, Secret scan, Documentation gate, Spec verify, Commit, Push. | No step for `.ai-engineering/` file integrity validation. Steps are numbered 0-8. | N/A |
| `.claude/agents/ai-build.md` | 112 lines. Implementation coordinator. Sections: Identity, Mandate, Supported Stacks, Behavior (6 subsections), Referenced Skills, Boundaries, Escalation. | No Output Contract section. Has Boundaries at L99-111. | MISSING |
| `.claude/agents/ai-plan.md` | 100 lines. Planning agent. Sections: Identity, Mandate, Behavior (Interrogation Protocol, Pipeline Classification, Spec-as-Gate, Strategic Analysis), Self-Challenge, Referenced Skills, Boundaries, Escalation. | No Output Contract section. Has Boundaries at L87-99. | MISSING |
| `.claude/agents/ai-verify.md` | 114 lines. Quality/security agent. Sections: Identity, Mandate, Modes, Behavior, Confidence Scoring, Self-Challenge, Report Contract, Referenced Skills, Boundaries, Escalation. | Has `## Report Contract` (L77-93) with structured markdown template. | PRESENT (as Report Contract) |
| `.claude/agents/ai-guard.md` | 103 lines. Governance advisor. Sections: Identity, Mandate, Differentiation, Modes, Behavior, Advisory Output Contract, Referenced Skills, Boundaries, Escalation. | Has `## Advisory Output Contract` (L67-83) with structured markdown template. | PRESENT |
| `.claude/agents/ai-review.md` | 109 lines. Code review agent. Sections: Identity, Mandate, Behavior (6 subsections incl. Final Report), Referenced Skills, Boundaries, Escalation. | Has `### 6. Final Report` (L74-90) with structured template. | PRESENT (as Final Report) |
| `.claude/agents/ai-explore.md` | 137 lines. Research agent. Sections: Identity, Mandate, Behavior (6 subsections + MCP + Parallel), Output Contract, Referenced Skills, Boundaries, Escalation. | Has `## Output Contract` (L94-116) with full structured template: Architecture Map, Dependencies Discovered, Patterns Identified, Risks Found, Files of Interest, Sources Consulted. | PRESENT (canonical exemplar) |
| `.claude/agents/ai-guide.md` | 96 lines. Teaching agent. Sections: Identity, Mandate, Modes, Behavior, Pedagogical Principles, Referenced Skills, Boundaries, Escalation. | No Output Contract section. Has Boundaries at L84-95. | MISSING |
| `.claude/agents/ai-simplify.md` | 110 lines. Complexity reducer. Sections: Identity, Mandate, Behavior (5 subsections incl. Report), Referenced Skills/Standards, Boundaries, Escalation. | Has `### 5. Report` (L73-86) with structured template. | PRESENT (as Report) |
| `.claude/agents/ai-autopilot.md` | 128 lines. Multi-phase orchestrator. Sections: Identity, Mandate, Capabilities, Subagent Orchestration, Behavior (6 phases + State Machine), Self-Challenge, Referenced Skills, Boundaries, Escalation. | No Output Contract section. Has Boundaries at L111-127. | MISSING |

### Mirror Surface

Each agent/skill change must be mirrored to 4 locations:

| Location | Agent Format | Skill Format | Notes |
|----------|-------------|--------------|-------|
| `.claude/agents/ai-*.md` | Claude Code native | N/A | Source of truth for agents |
| `.claude/skills/ai-*/SKILL.md` | N/A | Claude Code native | Source of truth for skills |
| `.github/agents/*.agent.md` | Copilot format (tools/hooks/handoffs in frontmatter) | N/A | Body identical to Claude agents |
| `.agents/agents/ai-*.md` | Codex/Gemini format (no tools in frontmatter) | N/A | Body identical to Claude agents |
| `src/ai_engineering/templates/project/agents/*.agent.md` | Template (Copilot format) | N/A | Template for `ai-eng install` |
| `src/ai_engineering/templates/project/.claude/skills/ai-*/SKILL.md` | N/A | Template | Template for `ai-eng install` |

CLAUDE.md changes mirror to: root `CLAUDE.md`, template `CLAUDE.md`, `AGENTS.md` (root), template `AGENTS.md`.

### Patterns to Follow

**Governance rule format** (CLAUDE.md Don't section): Each rule is a numbered list item starting with `**NEVER**` in bold, followed by the prohibited action, then explanation. Example from L162: `1. **NEVER** \`--no-verify\` on any git command.`

**Output Contract format** (ai-explore exemplar): Section heading `## Output Contract`, followed by a paragraph explaining the format, then a fenced markdown code block showing the template with `## ` subheadings for each output section. Located between the last Behavior subsection and `## Referenced Skills`.

**Skill process step format** (ai-dispatch): Steps numbered sequentially in the `## Process` section as `N. **Step name** -- description`. Sub-steps use lettered lists (a, b, c).

**Skill process step format** (ai-commit): Steps numbered with `### N. Step name` markdown headings.

### Dependencies Map

- CLAUDE.md (root) is manually maintained; AGENTS.md is generated from it by `sync_command_mirrors.py` (sub-spec 6 will handle this, but for now AGENTS.md is manually maintained)
- Agent files: `.claude/agents/` is source of truth; `.github/agents/` and `.agents/agents/` and template `agents/` are mirrors (same body, different frontmatter)
- Skill files: `.claude/skills/` is source of truth; `.github/skills/` and template `.claude/skills/` are mirrors
- Codex/Gemini has NO skill mirrors for dispatch and commit (only `.github/skills/` has them)

### Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| AGENTS.md drift from CLAUDE.md after manual edits | Medium | Sub-spec 6 will automate this; for now, manually update AGENTS.md in sync |
| Output Contract added to agents that already have structured output (verify Report Contract, review Final Report, simplify Report) may create redundancy | Medium | Do NOT add a separate Output Contract section to agents that already have equivalent structured output (verify, review, simplify, explore, guard). Only add to the 4 missing agents: build, plan, guide, autopilot. The spec says "all 9" but 5 already have equivalent contracts. |
| Template CLAUDE.md has minor differences from root CLAUDE.md (Context Loading section present in template but not in root AGENTS.md) | Low | Apply same changes to both; differences are in other sections |
| Mirror sync across 4 agent locations per agent | Medium | Process systematically: edit Claude source, then copy body to all 3 mirrors |
