---
id: sub-003
parent: spec-080
title: "Context Loading Enforcement"
status: implemented
files: [".claude/skills/ai-test/SKILL.md", ".claude/skills/ai-debug/SKILL.md", ".claude/skills/ai-review/SKILL.md", ".claude/skills/ai-verify/SKILL.md", ".claude/skills/ai-schema/SKILL.md", ".claude/skills/ai-pipeline/SKILL.md", ".claude/skills/ai-security/SKILL.md", ".claude/skills/ai-dispatch/SKILL.md", ".claude/skills/ai-autopilot/handlers/phase-implement.md", ".claude/skills/ai-autopilot/handlers/phase-deep-plan.md", ".github/skills/ai-test/SKILL.md", ".github/skills/ai-debug/SKILL.md", ".github/skills/ai-review/SKILL.md", ".github/skills/ai-verify/SKILL.md", ".github/skills/ai-schema/SKILL.md", ".github/skills/ai-pipeline/SKILL.md", ".github/skills/ai-security/SKILL.md", ".github/skills/ai-dispatch/SKILL.md", ".agents/skills/test/SKILL.md", ".agents/skills/debug/SKILL.md", ".agents/skills/review/SKILL.md", ".agents/skills/verify/SKILL.md", ".agents/skills/schema/SKILL.md", ".agents/skills/pipeline/SKILL.md", ".agents/skills/security/SKILL.md", ".agents/skills/dispatch/SKILL.md"]
depends_on: [sub-002]
---

# Sub-Spec 003: Context Loading Enforcement

## Scope
Add explicit "Step 0: Load Contexts" to the 8 code-touching skills (ai-code, ai-test, ai-debug, ai-review, ai-verify, ai-schema, ai-pipeline, ai-security). Implement dispatch injection: ai-dispatch injects applicable context content into subagent prompts as safety net. Update autopilot phase-implement and phase-deep-plan handlers to include team context alongside language and framework contexts.

## Exploration

### Existing Files

**Skills requiring Step 0 insertion (no context loading today):**

| File | Lines | Current first step | Notes |
|------|-------|--------------------|-------|
| `.claude/skills/ai-test/SKILL.md` | 154 | `### Mode: tdd` (line 24) | No context loading. Jumps straight into mode procedures |
| `.claude/skills/ai-debug/SKILL.md` | 118 | `### Phase 1: Symptom Analysis` (line 24) | No context loading. Starts with symptom gathering |
| `.claude/skills/ai-verify/SKILL.md` | 126 | `### Verification Protocol` (line 24) | No context loading. Starts with IRRV protocol |
| `.claude/skills/ai-schema/SKILL.md` | 83 | `### design -- Schema Design` (line 24) | No context loading. Starts with mode procedures |
| `.claude/skills/ai-pipeline/SKILL.md` | 59 | `Routing` table (line 23) | No context loading. Starts with routing table |
| `.claude/skills/ai-security/SKILL.md` | 122 | `### static -- SAST` (line 26) | Has "Detect stacks" (line 28) but only for tool selection, not context file loading |

**Skills where context loading already exists (verify, no Step 0 needed in SKILL.md):**

| File | Lines | Context loading location | Notes |
|------|-------|--------------------------|-------|
| `.claude/skills/ai-review/SKILL.md` | 99 | Delegates to `handlers/review.md` Step 1 (lines 15-18) | Handler already loads languages, frameworks, AND team contexts. SKILL.md itself does not need Step 0 because the handler is the entry point for the procedure |
| `.claude/skills/ai-review/handlers/review.md` | 152 | Step 1 lines 15-18 | COMPLETE: loads languages, frameworks, team. Gold standard for handler-level loading |

**Dispatch (injection target):**

| File | Lines | Injection point | Notes |
|------|-------|-----------------|-------|
| `.claude/skills/ai-dispatch/SKILL.md` | 150 | `## Subagent Context` section (lines 77-93) | YAML template defines task/description/agent/scope/constraints/gate. Missing: no `contexts:` field to inject language/framework/team content into subagent prompts |

**Autopilot handlers (team context gap):**

| File | Lines | Current context loading | Gap |
|------|-------|------------------------|-----|
| `.claude/skills/ai-autopilot/handlers/phase-implement.md` | 195 | Step 2b item 3 (line 54): loads `contexts/languages/` and `contexts/frameworks/` | Missing: `contexts/team/` is NOT loaded. Team conventions are invisible during implementation |
| `.claude/skills/ai-autopilot/handlers/phase-deep-plan.md` | 215 | Step 2 bullet 4 (line 35): loads `contexts/languages/` and `contexts/frameworks/` | Missing: `contexts/team/` is NOT loaded. Team conventions are invisible during deep planning |

**Mirror files (must receive same changes):**

- `.github/skills/ai-{test,debug,review,verify,schema,pipeline,security,dispatch}/SKILL.md` -- 8 Copilot mirrors
- `.agents/skills/{test,debug,review,verify,schema,pipeline,security,dispatch}/SKILL.md` -- 8 Codex mirrors
- Note: `.agents/` skills use names without `ai-` prefix (e.g., `test/SKILL.md` not `ai-test/SKILL.md`)

### Patterns to Follow

**Gold standard: `ai-build.md` Section 2 "Load Contexts" (lines 30-39)**

```
### 2. Load Contexts

After detecting the stack, read the applicable context files:
1. **Languages** -- read `.ai-engineering/contexts/languages/{lang}.md` for each detected language.
   Available (14): bash, cpp, csharp, dart, go, java, javascript, kotlin, php, python, rust, sql, swift, typescript
2. **Frameworks** -- read `.ai-engineering/contexts/frameworks/{fw}.md` for each detected framework.
   Available (15): android, api-design, aspnetcore, backend-patterns, bun, claude-api, deployment-patterns, django, flutter, ios, mcp-sdk, nextjs, nodejs, react, react-native
3. **Team** -- read `.ai-engineering/contexts/team/*.md` for all team conventions.

Apply loaded standards to all subsequent code generation.
```

This exact block (adapted as "Step 0") should be inserted before the first procedural step in each skill. The step should be titled `### Step 0: Load Contexts` and placed inside `## Process` but before any mode-specific or phase-specific steps.

**Insertion points per skill:**

| Skill | Insert before | Exact anchor line |
|-------|---------------|-------------------|
| ai-test | `### Mode: tdd` | Line 24 |
| ai-debug | `### Phase 1: Symptom Analysis` | Line 24 |
| ai-verify | `### Verification Protocol` | Line 24 |
| ai-schema | `### design -- Schema Design` | Line 24 |
| ai-pipeline | `## Routing` section | Line 23 (insert a `## Process` section wrapping routing + new Step 0) |
| ai-security | `## Modes` section | Line 25 (insert Step 0 before `### static`) |

**ai-review exception**: The review handler (`handlers/review.md`) already loads all three context types in Step 1 (lines 15-18). Adding Step 0 to the parent SKILL.md would duplicate the handler's work. The correct action is to add Step 0 to `SKILL.md` with a note that handler-based modes inherit context from Step 1 of the handler, while direct invocations use Step 0.

**Dispatch injection pattern:**

The `## Subagent Context` YAML template (lines 81-93) needs a `contexts:` field added. The dispatch process should detect the stack from the task's file scope, read applicable context files, and embed their content (or file paths) into the subagent prompt. This acts as a safety net -- even if a skill does not have its own Step 0, contexts are injected by the dispatcher.

### Dependencies Map

- **Imports from sub-002**: The `stacks:` field in `manifest.yml` (populated by sub-002's unified stacks work) is used to determine which language/framework contexts to load. Step 0 reads `manifest.yml` providers.stacks to know what to load.
- **Consumed by**: All 6 skills consume context files from `.ai-engineering/contexts/{languages,frameworks,team}/`. These files already exist and are not modified by this sub-spec.
- **ai-dispatch**: The injection mechanism references the same context files but embeds their content into subagent prompts rather than expecting subagents to read them.
- **Mirror sync**: Changes to `.claude/skills/` must be replicated to `.github/skills/` and `.agents/skills/`.

### Risks

1. **Mirror drift**: If mirrors are updated inconsistently, Copilot and Codex users get different behavior than Claude Code users. Mitigation: one task per mirror set, mechanical copy.
2. **ai-review duplication**: Adding Step 0 to the parent SKILL.md while the handler already loads contexts creates redundant loading. Mitigation: Step 0 in SKILL.md says "if proceeding to a handler, the handler handles context loading; otherwise load here."
3. **ai-pipeline structure**: This skill uses a `## Routing` pattern instead of `## Process`. Step 0 needs to fit before routing without breaking the existing flow. The `## When to Use` section ends at line 21, and routing starts at line 23. Step 0 can be inserted between them.
4. **Dispatch injection size**: Injecting full context file contents into subagent prompts may consume significant context window. Mitigation: inject file paths with explicit read instructions, not full content. The subagent reads them in its own context.
