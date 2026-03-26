---
total: 5
completed: 5
---

# Plan: sub-003 Context Loading Enforcement

## Plan

exports: [Step 0 context loading pattern for skills, dispatch context injection mechanism]
imports: [manifest.yml unified stacks (from sub-002)]

- [x] T-3.1: Add Step 0 to 6 code-touching skills (Claude Code primary)
  - **Files**: `.claude/skills/ai-test/SKILL.md`, `.claude/skills/ai-debug/SKILL.md`, `.claude/skills/ai-verify/SKILL.md`, `.claude/skills/ai-schema/SKILL.md`, `.claude/skills/ai-pipeline/SKILL.md`, `.claude/skills/ai-security/SKILL.md`
  - **Done**: Each of the 6 SKILL.md files contains a `### Step 0: Load Contexts` section before the first procedural step, following the ai-build.md Section 2 pattern (languages, frameworks, team). ai-review/SKILL.md is excluded because its handler already loads all three context types.

- [x] T-3.2: Add Step 0 to ai-review/SKILL.md with handler delegation note
  - **Files**: `.claude/skills/ai-review/SKILL.md`
  - **Done**: ai-review/SKILL.md contains `### Step 0: Load Contexts` in the Process section before Step 1, with a note that handler-based modes (review, find, learn) inherit context loading from the handler's Step 1 and should not duplicate it. Direct invocations of the skill without a handler use Step 0.

- [x] T-3.3: Add dispatch context injection to ai-dispatch
  - **Files**: `.claude/skills/ai-dispatch/SKILL.md`
  - **Done**: The `## Subagent Context` YAML template includes a `contexts:` field listing applicable context file paths (languages, frameworks, team). The dispatch process description (Step 4) includes detecting the stack from task file scope, resolving context file paths, and passing them to the subagent prompt. The subagent is instructed to read these context files before executing.

- [x] T-3.4: Add team context to autopilot handlers
  - **Files**: `.claude/skills/ai-autopilot/handlers/phase-implement.md`, `.claude/skills/ai-autopilot/handlers/phase-deep-plan.md`
  - **Done**: phase-implement.md Step 2b item 3 includes `contexts/team/*.md` alongside `contexts/languages/` and `contexts/frameworks/`. phase-deep-plan.md Step 2 bullet 4 includes `contexts/team/*.md` alongside `contexts/languages/` and `contexts/frameworks/`.

- [x] T-3.5: Replicate changes to Copilot and Codex mirrors
  - **Files**: `.github/skills/ai-test/SKILL.md`, `.github/skills/ai-debug/SKILL.md`, `.github/skills/ai-review/SKILL.md`, `.github/skills/ai-verify/SKILL.md`, `.github/skills/ai-schema/SKILL.md`, `.github/skills/ai-pipeline/SKILL.md`, `.github/skills/ai-security/SKILL.md`, `.github/skills/ai-dispatch/SKILL.md`, `.agents/skills/test/SKILL.md`, `.agents/skills/debug/SKILL.md`, `.agents/skills/review/SKILL.md`, `.agents/skills/verify/SKILL.md`, `.agents/skills/schema/SKILL.md`, `.agents/skills/pipeline/SKILL.md`, `.agents/skills/security/SKILL.md`, `.agents/skills/dispatch/SKILL.md`
  - **Done**: All 16 mirror files contain the same Step 0 / dispatch injection / autopilot handler changes as their `.claude/` counterparts. Content is identical except for platform-specific frontmatter (e.g., `mode: agent` in Copilot files, no `ai-` prefix in Codex skill directory names).

### Confidence
- **Level**: high
- **Assumptions**: (1) The ai-build.md Section 2 pattern is the canonical Step 0 format -- no alternative format is expected. (2) Mirror files are content-identical to `.claude/` counterparts except frontmatter. (3) ai-review handler context loading (lines 15-18 of review.md) is complete and does not need modification. (4) Dispatch injection uses file paths (not inline content) to avoid context window bloat.
- **Unknowns**: None. All files have been read and insertion points verified.

## Self-Report

| File/Function | Classification | Notes |
|---------------|----------------|-------|
| `.claude/skills/ai-test/SKILL.md` | real | Step 0 inserted before `### Mode: tdd`, follows ai-build.md Section 2 pattern |
| `.claude/skills/ai-debug/SKILL.md` | real | Step 0 inserted before `### Phase 1: Symptom Analysis` |
| `.claude/skills/ai-verify/SKILL.md` | real | Step 0 inserted before `### Verification Protocol` |
| `.claude/skills/ai-schema/SKILL.md` | real | Step 0 inserted as new `## Process` section before `## Modes` |
| `.claude/skills/ai-pipeline/SKILL.md` | real | Step 0 inserted as new `## Process` section before `## Routing` |
| `.claude/skills/ai-security/SKILL.md` | real | Step 0 inserted as new `## Process` section before `## Modes` |
| `.claude/skills/ai-review/SKILL.md` | real | Step 0 with handler delegation note; existing steps renumbered under `### Steps` |
| `.claude/skills/ai-dispatch/SKILL.md` | real | `contexts:` field added to YAML template; `### Context Injection` subsection added |
| `.claude/skills/ai-autopilot/handlers/phase-implement.md` | real | Item 3 expanded to include `contexts/team/*.md` |
| `.claude/skills/ai-autopilot/handlers/phase-deep-plan.md` | real | Bullet 4 expanded to include `contexts/team/*.md` |
| `.github/skills/ai-{test,debug,verify,schema,pipeline,security}/SKILL.md` (6) | real | Copilot mirrors synced via file-sync mechanism |
| `.github/skills/ai-review/SKILL.md` | real | Copilot mirror synced with handler delegation note |
| `.github/skills/ai-dispatch/SKILL.md` | real | Copilot mirror synced with context injection |
| `.agents/skills/{test,debug,verify,schema,pipeline,security}/SKILL.md` (6) | real | Codex mirrors synced via file-sync mechanism |
| `.agents/skills/review/SKILL.md` | real | Codex mirror synced with handler delegation note |
| `.agents/skills/dispatch/SKILL.md` | real | Codex mirror synced with context injection |
