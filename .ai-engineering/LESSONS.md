## Rules & Patterns

Persistent learning context for AI agents. Records corrections, patterns, and rules discovered during development sessions. This file is loaded by `/ai-start` at session start and updated by `/ai-learn` after corrections.

Unlike `decision-store.json` (formal decisions with expiry and risk acceptance), this file captures informal but important patterns that should persist across sessions.

## How to Add Lessons

When the user corrects AI behavior:
1. Identify the pattern (not just the specific fix)
2. Add a new section below with: context, the learning, and an example if applicable
3. Keep entries concise (3-5 lines max per lesson)

## Patterns

### Plan tasks must have checkboxes for progress tracking

**Context**: `/ai-plan` generates `plan.md` as the contract for `/ai-dispatch`.
**Learning**: Every task line MUST use `- [ ] T-N.N:` format, not `- T-N.N:`. Without checkboxes, `/ai-dispatch` cannot track progress and the user cannot see completion state at a glance.
**Rule**: When writing plan.md, always prefix tasks with `- [ ]`.

### /ai-pr MUST clear spec.md and plan.md after PR creation

**Context**: PR #190 (spec-056) merged into main with spec.md and plan.md still containing full spec content. Steps 8.5-8.8 of `/ai-pr` SKILL.md were completely skipped. `_history.md` also missing the spec-056 entry.
**Learning**: The spec cleanup in step 8 is not optional — it's the mechanism that resets the spec lifecycle for the next feature. Stale spec files cause the next `/ai-brainstorm` to see outdated content and the next `/ai-pr` to generate PR descriptions from wrong data.
**Rule**: During `/ai-pr`, after generating the PR body from spec content, ALWAYS execute ALL of step 8:
1. Add entry to `_history.md`
2. Clear spec.md to `# No active spec\n\nRun /ai-brainstorm to start a new spec.\n`
3. Clear plan.md to `# No active plan\n\nRun /ai-plan after brainstorm approval.\n`
4. `git add` the cleared files before committing
Never skip these steps. Verify by reading the files after clearing.

### Existing PR updates must reconcile branch spec history

**Context**: On long-lived branches, updating the current PR body can hide the fact that `_history.md` is still missing entries for earlier completed specs on the same branch.
**Learning**: When a PR spans multiple specs, audit `git log origin/main..HEAD` and `_history.md` together. Do not assume the active `spec.md` is the only history entry that needs to be recorded.
**Rule**: Before closing a PR-update task, verify `_history.md` includes every completed spec represented in the branch commits, not just the latest one.

### During brainstorm, scope corrections must be reflected immediately in the draft spec

**Context**: The user refined scope mid-brainstorm: keep `ai-eng update` UX improvements, but remove `ai-eng update rebase` from the umbrella program.
**Learning**: Scope corrections can be partial, not all-or-nothing. Do not overreact by dropping the whole workstream when the user only descopes one sub-part.
**Rule**: When the user narrows a feature during brainstorm, update the draft spec immediately and preserve only the still-in-scope slice.

### During brainstorm, naming decisions stay provisional until the user reconfirms them

**Context**: The user first accepted a new name for the portable automation layer, then explicitly reverted to `runbooks`.
**Learning**: Naming exploration is part of design, not approval. Do not treat a tentative label chosen during interrogation as final if the user later reconsiders.
**Rule**: Keep the draft spec flexible on naming until the user clearly reconfirms the term they want to ship.

### Provider-side automation must respect hierarchy limits from manifest policy

**Context**: The user clarified that provider-side runbooks may create/update work items and report findings, but may not mutate features. They can only create user stories under features and tasks under user stories, following the configured hierarchy in `manifest.yml`.
**Learning**: Board automation is not "free-form CRUD". Hierarchy rules are part of the contract and must be treated as hard constraints, not suggestions.
**Rule**: When designing or implementing provider-side runbooks, read `manifest.yml` hierarchy rules first and enforce them explicitly. Features are read-only unless the user later changes that policy.

### Provider-side `ready` does not mean auto-execute locally

**Context**: The user clarified that runbooks may mark an item `ready` without human approval, but the local `/ai-brainstorm` -> `/ai-plan` -> execution flow should still start manually.
**Learning**: Remote preparation and local execution are separate control planes. Do not interpret provider-side readiness as permission to auto-run the local implementation pipeline.
**Rule**: Treat provider-side `ready` as a filterable intake signal only. Local execution still starts explicitly and manually.

### Promotion from team context into framework context must be selective and product-driven

**Context**: The user clarified that moving content out of `contexts/team/**` is only desirable when it genuinely helps downstream ai-engineering consumers.
**Learning**: Do not frame knowledge promotion as "extract reusable content by default." Most team-local context should stay local unless it clearly improves the shared framework.
**Rule**: Treat promotion from team space into framework space as an explicit value test: only promote guidance that materially helps ai-engineering users outside this repository.

### A one-time audit is not a justification to invent a new permanent workflow

**Context**: The user clarified that, for now, they only want this brainstorm to analyze the current state and decide what to do with existing artifacts. They do not want a new agent, skill, or separate process created for promotions.
**Learning**: Do not respond to a governance audit by automatically designing another governance mechanism. Sometimes the correct move is a case-by-case human decision, not a new subsystem.
**Rule**: When the user asks for analysis of the current state, keep the solution analytical unless they explicitly ask for an ongoing automation/process.

### When a new workstream appears mid-brainstorm, expand the child-spec decomposition explicitly

**Context**: The user added a new `review` modernization concern after the umbrella spec already had a `verify` workstream, including inspiration from `review-code` and a requirement to clarify skill-vs-agent responsibilities.
**Learning**: Do not silently squeeze a distinct architecture concern into an existing child spec just because it is adjacent. If the new concern has separate files, decisions, and risks, reflect that in the umbrella decomposition.
**Rule**: During umbrella brainstorms, increase the child-spec count when a newly added concern is meaningfully independent.

### Skill-vs-agent pairs need an explicit canonical source of truth

**Context**: The user saw both `review`/`ai-review` and `verify`/`ai-verify` and immediately read them as confusing duplicates.
**Learning**: A skill and its paired agent may coexist, but only if the procedural contract is clearly canonical and the agent stays a thin wrapper. Otherwise the architecture reads as duplicate product surfaces.
**Rule**: When auditing or redesigning paired skills and agents, state which artifact is canonical and capture drift risk explicitly in the spec.

### When a user cites an inspiration repo, copy the architecture pattern, not just a single feature

**Context**: The user clarified that `review-code` is the inspiration not only because of `finding-validator`, but because of its whole structure: skill, handlers, context, and detailed Markdown prompts per specialist.
**Learning**: Do not reduce an inspiration repo to its flashiest component. First identify whether the user values a local feature or the overall decomposition pattern.
**Rule**: If the user points to an external internal repo as inspiration, reflect the full structural pattern they want unless they explicitly narrow it down.

### Do not mirror an inspiration repo more literally than the user wants

**Context**: After asking for the `review-code` structure, the user explicitly rejected copying its multi-handler shape and instead wanted one primary `review` handler with specialist subagents beneath it.
**Learning**: "Use this repo as inspiration" does not mean "clone its directory tree verbatim." Preserve the pattern the user values and drop the parts they reject.
**Rule**: When adapting an inspiration architecture, confirm which parts are structural requirements and which are optional source material.

### Default agentic depth must be explicit, not hidden in vague "efficient mode" wording

**Context**: The user clarified that "cost-efficient by default" does not mean fewer specialist lenses. It means normal mode still covers all specialists, but bundles them into about 3 agents, while `full` launches one agent per specialist.
**Learning**: Cost strategy needs concrete dispatch expectations, not just abstract language about efficiency. Otherwise implementation drifts toward either under-review or expensive defaults.
**Rule**: When specifying tiered agentic modes, describe both coverage and grouping: whether the default profile reduces specialist count or only changes how specialists are bundled into agents.

### Framework changes must converge across all mirrors, templates, and sync surfaces

**Context**: The user explicitly asked that changes apply cleanly across Claude Code, GitHub Copilot, Codex, and Gemini CLI, with no stale sync/template/framework artifacts and no dead or aspirational leftovers.
**Learning**: Mirror consistency is part of the feature, not post-work cleanup. A partially updated framework is a broken deliverable.
**Rule**: For framework-level work, definition-of-done includes mirrored platform updates and removal of obsolete surfaces everywhere they appear.

### Narrow multi-mode skills when the user wants one sharp responsibility

**Context**: The user explicitly decided that `review` should remain only for reviewing and should not carry `find` or `learn` as embedded modes.
**Learning**: A broad utility surface may look flexible, but if it blurs the main job of the skill it becomes harder to reason about and harder to document.
**Rule**: When a user narrows a skill to one core responsibility, reflect that immediately in the spec and remove adjacent modes from that skill's target surface.

### Elimination can be the simplification, not migration

**Context**: After narrowing `review` to review-only behavior, the user chose to eliminate `find` and `learn` rather than preserve them as separate skills.
**Learning**: When simplifying a framework surface, do not assume every removed mode needs a new home. Sometimes the right design is outright deletion.
**Rule**: If the user chooses elimination over migration, encode that explicitly and avoid inventing replacement surfaces.

### When the user asks for parity across sibling surfaces, mirror the dispatch model explicitly

**Context**: After defining normal/full profiles for `review`, the user explicitly chose the same profile model for `verify`.
**Learning**: Similar orchestration surfaces should not drift on mode semantics once the user requests parity. If one gets `normal` vs `full`, the sibling should match unless there is a concrete reason not to.
**Rule**: When the user asks for parity between sibling skills like `review` and `verify`, copy the mode model explicitly into the spec rather than leaving it implied.

### Mode names and default grouping counts are part of the contract

**Context**: The user chose `normal` as the exact profile name, with `review` grouped into about 3 agents by default and `verify` grouped into about 2.
**Learning**: Naming and grouping are not cosmetic details in agentic architecture. They directly shape UX, cost, and implementation.
**Rule**: When the user fixes profile names or default grouping counts, encode them explicitly in the spec instead of leaving them as future implementation choices.

### Default modes should stay implicit when the user wants a clean command surface

**Context**: After choosing `normal`/`full`, the user clarified that `normal` should be implicit and only `full` should appear explicitly in the command when the expensive path is desired.
**Learning**: Even when a system has named profiles, the default one does not always belong in the user-facing syntax. Requiring the default name can make the interface noisier without adding value.
**Rule**: When the user wants a clean default UX, make the standard profile implicit and reserve explicit flags or arguments for non-default expensive modes only.

### Explicit expensive modes need a concrete CLI shape

**Context**: After deciding that only the expensive profile should be explicit, the user chose `--full` instead of a positional `full` argument.
**Learning**: Once a mode becomes opt-in, the exact CLI form matters for consistency and docs. Leaving it vague invites divergence between skills and platforms.
**Rule**: When a user picks a specific flag form like `--full`, encode that exact syntax in the spec instead of referring to a generic explicit mode.

### For cost-sensitive multi-agent defaults, prefer fixed macro-agents with adaptive internal lenses

**Context**: To balance predictability and efficiency, the user accepted a hybrid model: `review normal` uses 3 fixed macro-agents and `verify normal` uses 2 fixed macro-agents, while each macro-agent adjusts internal specialist emphasis based on the diff.
**Learning**: Fully dynamic grouping is hard to document and mirror consistently, while fully fixed specialists waste context. A stable outer shape with adaptive inner emphasis gives the best tradeoff.
**Rule**: When designing token-efficient multi-agent defaults, keep the top-level agent count and grouping stable, and move adaptivity inside those macro-agents unless the user asks otherwise.

### Stable framework orchestration should not become per-project config by default

**Context**: After accepting fixed macro-agents, the user chose to keep that composition fixed in the framework rather than configurable through `manifest.yml`.
**Learning**: Not every framework decision benefits from becoming project-level configuration. Extra configurability can create mirror drift and docs debt faster than it creates value.
**Rule**: When a user prefers a stable framework-level orchestration shape, do not reopen it as per-project config unless there is a strong concrete need.

### Ask nested architecture questions at the right boundary

**Context**: While discussing `finding-validator`, I asked as if it might be shared between `review` and `verify`, but the user expected it as an internal part of `review`.
**Learning**: When a component clearly belongs inside one surface, ask about its behavior within that surface before asking whether it crosses into a sibling surface.
**Rule**: Keep brainstorm questions aligned to the architecture boundary the user has already established.

### Do not blur coverage with decomposition when discussing agent profiles

**Context**: The user corrected that `review normal` and `review --full` both run all specialists; the only difference is grouping into 3 agents versus one agent per specialist.
**Learning**: In agentic profile design, "which specialists run" and "how they are grouped into agents" are separate axes. Mixing them creates confusion even if the underlying spec is already correct.
**Rule**: When asking follow-up questions about profile behavior, keep specialist coverage and agent decomposition explicitly separate.

### Validation stages can be shared across profiles even when agent grouping differs

**Context**: After clarifying that both `review normal` and `review --full` run all specialists, the user also chose to keep `finding-validator` active in normal mode.
**Learning**: Profile differences do not automatically imply different quality gates. Sometimes the same validation stage should run in both profiles, with only the upstream decomposition changing.
**Rule**: Treat validation-stage inclusion as a separate decision from agent grouping and specialist coverage.

### Universal validation is a valid choice even when it increases cost

**Context**: When asked whether `finding-validator` should cover only severe review findings or all findings, the user chose all findings.
**Learning**: Cost pressure alone is not a reason to narrow a validation stage if the user is explicitly optimizing for trust and rigor.
**Rule**: When the user chooses universal validation, encode it directly instead of silently narrowing scope back to severe-only findings.

### Similar orchestration surfaces do not need identical validation pipelines

**Context**: The user accepted a universal `finding-validator` stage inside `review` but explicitly rejected adding a separate validator stage to `verify`.
**Learning**: Parity in profiles and grouping does not imply parity in every internal stage. Preserve the conceptual difference between review and verification when the user calls it out.
**Rule**: When sibling skills share dispatch patterns but differ in validation philosophy, encode that difference explicitly instead of over-unifying them.

### Execution grouping and report attribution are separate design choices

**Context**: The user chose `review normal` to execute specialists through 3 macro-agents, but still wants the final report organized by original specialist lens.
**Learning**: Reducing execution cost does not require flattening analytical attribution. Grouping can happen at runtime while the report stays specialist-shaped.
**Rule**: When a user groups specialists for execution, ask separately how they want findings attributed in the output.

### Preserve specialist attribution across sibling orchestration surfaces

**Context**: After choosing specialist attribution for `review normal`, the user made the same choice for `verify normal`.
**Learning**: Once the user optimizes for specialist-shaped output on one assessment surface, the sibling surface often should match unless they explicitly want a more fused report.
**Rule**: When sibling skills like `review` and `verify` share grouped execution, keep output attribution by original specialist lens unless the user says otherwise.

### If the user removes a whole workstream from the umbrella spec, remove it cleanly and rebalance the decomposition

**Context**: The user decided that `Notes` / `Learnings` / `Instincts` should be left untouched and taken out of this umbrella spec entirely.
**Learning**: When a whole workstream is descoped, do not just mark it "later." Update the title, goals, child-spec count, dependencies, risks, and docs references so the umbrella spec reflects the true current program.
**Rule**: Treat removal of a workstream as a structural spec edit, not just a sentence-level tweak.

### Reference visuals should become explicit UX direction, not vague inspiration

**Context**: For `ai-eng update`, the user provided a concrete tree-view image and asked for the same shape with ai-engineering CLI branding.
**Learning**: When the user provides a visual reference, convert it into a precise UX requirement in the spec instead of leaving it as a loose aesthetic note.
**Rule**: Encode user-provided UI references as explicit rendering targets with project-specific branding constraints.

### Brainstorm parallel-explore workflow

**Context**: During `/ai-brainstorm`, the agent often needs to understand multiple parts of the codebase simultaneously to evaluate approaches.
**Learning**: Launch parallel `ai-explore` agents (via Agent tool with subagent_type=Explore) at the start of brainstorm to gather architectural context from different areas concurrently. This dramatically reduces brainstorm duration and produces better-informed specs. Each explore agent should focus on one concern (e.g., one explores the data layer, another the API layer, another the test patterns).
**Rule**: When brainstorming features that touch 3+ modules, dispatch 2-4 parallel explore agents before writing the spec. Synthesize findings before proposing approaches.

### manifest.yml es la fuente de verdad absoluta

**Context**: `_BASE_INSTRUCTION_FILES` en `validator/_shared.py` hardcodea `CLAUDE.md` sin consultar `ai_providers.enabled`, causando falsos positivos en proyectos que no usan Claude.
**Learning**: `manifest.yml` DEBE ser consultado por TODOS los componentes del framework (CLI commands, validators, verifiers, hooks, skills, agents, installers, updaters) para cualquier decisión de configuración. NUNCA hardcodear listas de ficheros, providers, stacks, o capabilities — siempre leer de `manifest.yml`.
**Rule**: Patrón correcto: `load_manifest_config(target)` → `cfg.ai_providers.enabled` → filtrar dinámicamente. Ningún componente debe asumir qué providers o ficheros existen sin consultar el manifiesto.
