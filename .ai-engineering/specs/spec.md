# Spec 082 - Skill Surface Refactor

Status: complete
Created: 2026-03-27

## Problem

The ai-engineering framework has 41 skills that have grown organically across 80+ specs. A comprehensive 6-agent audit reveals systemic issues:

- **Ghost references**: 2 skills (`/ai-quality`, `/ai-infra`) are referenced by 4+ skills but don't exist
- **Undefined delegation**: `ai-verify` absorbs `ai-security` and `ai-governance` as modes without declaring whether it delegates or reimplements
- **Functional duplication**: 6 major overlap pairs (verify↔security, learn↔instinct, test↔eval, docs↔write changelog, guide↔onboard, sprint↔sprint-review)
- **Misclassified effort**: 8 of 41 skills have wrong effort levels, degrading model selection and token budget
- **Scope drift**: `ai-write` bundles engineering docs with startup marketing (investor outreach, x-api); `ai-onboard` mixes bootstrap with governance policy; `ai-verify` conflates behavioral protocol (IRRV) with scanner tool
- **Orphaned skills**: `ai-resolve-conflicts` has rich category-aware logic but zero automated callers
- **Misleading names**: `ai-release` is a gate, not a release
- **Structural inconsistency**: section headings (Process vs Procedure vs Modes), missing Integration sections, non-standard frontmatter, no spec.md schema contract

The cumulative effect: agents mis-route invocations, users can't choose between overlapping skills, and the framework's stated purpose (precision engineering for regulated industries) is diluted by unrelated capabilities.

## Goals

- Sharpen the 41-skill surface: merge 1, split 1, net count stays at 41 but with cleaner boundaries
- Eliminate all ghost references and phantom integration links
- Establish clear delegation model for verify↔security↔governance
- Correct all 8 misclassified effort levels
- Split scope-drifted skills to restore single-responsibility
- Wire orphaned skills into the automated pipeline
- Standardize SKILL.md structure across all 41 skills
- Add missing cross-references and Integration sections
- Define spec.md schema contract for brainstorm→plan handoff
- Verify and fix IDE mirror completeness before any structural changes

## Non-Goals

- Adding entirely new skills beyond the ai-market split
- Changing the handler/router pattern itself
- Modifying agents (`.claude/agents/`)
- Changing the installer or CLI
- Rearchitecting the brainstorm→plan→dispatch pipeline (only fixing seams)

Note: this spec does modify some skill behavior where required to fix delegation models (D-082-06, D-082-18). These are targeted behavioral fixes, not general rewrites.

IMPORTANT: ai-engineering is a multi-IDE framework supporting Claude Code, GitHub Copilot, Codex, and Gemini. Every structural change must be reflected in all 3 mirrors (.claude, .github, .agents) via the sync pipeline. IDE-specific frontmatter fields (`copilot_compatible`, `disable-model-invocation`, `mode: agent`) are functional — do not remove them.

## Chosen Direction

Surgical refactor in 4 waves, ordered by dependency and risk. Each wave is independently shippable and testable. No wave breaks the pipeline for subsequent waves.

## Decisions

### D-082-01: Merge sprint-review into sprint

`ai-sprint-review` becomes the `review` mode of `ai-sprint`. Eliminates duplicate data collection (PRs, commits, spec tasks). The `requires` frontmatter (python3, gh/az) moves to `ai-sprint`. Skill count: 41→40.

### D-082-02: Unify correction capture authority

`ai-learn` lines 82-87 ("Post-Correction Learning") is removed. `ai-instinct` becomes the single authority for in-session correction capture (`skillAgentPreferences` pattern family). `ai-learn` retains only PR-analysis modes (single, batch, apply). Eliminates the dual-write to context files.

### D-082-03: Split ai-write into ai-write + ai-market, remove duplicate handlers

`ai-docs` is the authoritative skill for engineering documentation: changelog, readme, solution-intent, docs-portal, quality-gate. `ai-write` must not duplicate these.

**Remove from ai-write**: `docs` and `changelog` handlers (and their handler files). These are `ai-docs`'s responsibility.

**ai-write retains**: `content` only (blog, pitch, sprint-review, architecture-board, solution-intent). Pure content writing, not documentation artifacts.

**New skill ai-market** gets: `content-engine`, `crosspost`, `market-research`, `investor-materials`, `investor-outreach`, `x-api`. Business development and marketing.

Skill count: 40→41 (+1 from split, -1 from D-082-01 merge = net 41).

### D-082-04: Extract IRRV from ai-verify

The IRRV protocol (evidence-before-claims, lines 37-57 of verify) moves to `.ai-engineering/contexts/evidence-protocol.md`. All agents load it via Step 0 context loading. `ai-verify` becomes scanner-only with clearly defined modes.

### D-082-05: Extract governance tables from ai-onboard

Red Flags Table and Detection Rules (30 lines of enforcement policy) move to `.ai-engineering/contexts/session-governance.md`. `ai-onboard` loads the file in Step 2 instead of declaring rules inline. Onboard becomes pure bootstrap.

### D-082-06: Declare verify↔security↔governance delegation model

`ai-verify security` delegates to `ai-security` (full scan). `ai-verify governance` delegates to `ai-governance` (full scan). Verify's modes become orchestration entry points, not reimplementations. Both security and governance SKILL.md files gain "Called by: /ai-verify (delegation)" in their Integration sections.

### D-082-07: Wire ai-resolve-conflicts into watch.md

In `ai-pr/handlers/watch.md` Step 5, replace the inline conflict-resolution sub-step (the "If rebase conflicts: read conflicting files, resolve..." logic) with a READ delegation to `ai-resolve-conflicts`. Steps 1 (fetch), 2 (rebase), 4 (force-push), and 5 (interval reset) of Step 5 remain. This activates category-aware resolution logic (lock files, migrations, generated files) during automated CI repair.

### D-082-08: Rename ai-release to ai-release-gate

The skill executes only a GO/NO-GO readiness gate — it does not tag, publish, or create releases. Rename to `ai-release-gate` to accurately reflect its purpose. Actual release mechanics (tagging, publishing, GitHub Releases) are out of scope for this spec and may be addressed in a future spec if needed.

### D-082-09: Correct 8 effort levels

| Skill | From | To |
|-------|------|----|
| plan | max | high |
| instinct | max | medium |
| release | medium | high |
| sprint | medium | high |
| prompt | high | medium |
| media | high | medium |
| debug | max | high |
| sprint-review | medium | high (before merge into sprint) |

### D-082-10: Fix ghost references

- Replace `/ai-quality` → `/ai-verify quality` in: `ai-security` line 21, `ai-governance` line 17, `ai-release` lines 17+109
- Replace `/ai-infra` → "(no infra skill exists)" in: `ai-schema` line 20

### D-082-11: Add spec.md schema contract

Create `.ai-engineering/contexts/spec-schema.md` defining required frontmatter and sections for spec.md. Both `ai-brainstorm` (writer) and `ai-plan` (reader) validate against it.

### D-082-12: Standardize SKILL.md sections

All skills must have these sections in this order:
1. Frontmatter (name, description, effort, argument-hint, tags, requires)
2. `## Purpose` (1-2 sentences)
3. `## When to Use` / `## When NOT to Use`
4. `## Process` or `## Modes` (with numbered steps)
5. `## Quick Reference` (optional table)
6. `## Integration` (Called by / Calls / Transitions to)
7. `## Common Mistakes` (optional)

### D-082-13: Reclassify skills in CLAUDE.md and all IDE instruction files

The framework supports 4 IDEs: Claude Code, GitHub Copilot, Codex, and Gemini. The reclassification must be applied to ALL instruction files, not just CLAUDE.md:
- `CLAUDE.md` (Claude Code)
- `.github/copilot-instructions.md` or equivalent (GitHub Copilot)
- `.agents/README.md` or equivalent (Codex/Gemini)

| Skill | From Group | To Group |
|-------|------------|----------|
| prompt | Teaching | Meta |
| schema | Enterprise | Engineering (new group, or merge into Workflow) |
| autopilot | Meta (peer) | Orchestrators (new section) |
| code | (unlisted) | Workflow |

### D-082-14: Register ai-learn storage path

Add `.ai-engineering/learnings/` to manifest.yml under state paths. Add initialization step in `ai-learn` for first-time use.

### D-082-15: Add cross-references at natural handoff points

20+ missing references across all groups. Key additions:
- `debug` Phase 4 → delegates regression test to `/ai-test`
- `debug` resolution → forward reference to `/ai-postmortem generate`
- `postmortem` generate → reads `ai-debug` Phase 1-3 output
- `note` When NOT → add `/ai-learn` redirect
- `standup` When NOT → add `/ai-sprint goals`
- `review` Called by → add `/ai-dispatch (via quality.md)`
- `eval` Called by → remove phantom `/ai-verify` reference; add explicit disambiguation note: "eval is for AI-system reliability (probabilistic pass@k); test is for deterministic code correctness"
- `eval`/`test` → add mutual When NOT guards with the above distinction
- `verify` → add Transitions to section
- `resolve-conflicts` → add Integration section with "Called by: handlers/watch.md (Step 5), user directly"
- `docs`/`write` → disambiguate changelog handlers
- `guide`/`onboard` → add mutual NOT guards
- `slides`/`write content presentation` → add boundary note
- `board-discover`/`board-sync` → add pairing notes
- `pipeline validate`/`governance compliance` → document boundary

### D-082-16: Formalize multi-IDE frontmatter fields

**DO NOT remove** `disable-model-invocation` and `copilot_compatible` fields. These are functional fields consumed by `scripts/sync_command_mirrors.py`:

- `copilot_compatible: false` — gates the skill out of the `.github/skills/` mirror (Copilot surface). Used by `is_copilot_compatible()` in the sync script.
- `disable-model-invocation: true` — signals the skill runs as a pure script/tool, not an LLM-driven agent.

Both fields are already in the frontmatter serializer's key ordering (`_serialize_frontmatter` line 381), confirming they were designed as first-class fields.

Action: formalize them in `ai-create`'s Registration Checklist and frontmatter schema as **optional IDE-compatibility fields**. Document their behavior so future skill authors know when to use them. Add them to `.agents/skills/` sync logic if missing (currently `.agents/` passes them through without gating, which may be incorrect for Codex/Gemini).

### D-082-17: Extract Step 0 to shared protocol

The identical 8-line Step 0 block (read manifest, load contexts) copy-pasted across 5+ skills becomes a reference: "Step 0: Load contexts (see `contexts/step-zero-protocol.md`)". Each skill says "Step 0: Standard context loading" instead of repeating the block.

### D-082-18: Close governance gap in dispatch

Add governance as a fail-closed gate in `dispatch/handlers/quality.md` for specs tagged with governance-sensitive labels. Document explicitly when governance is advisory vs blocking.

### D-082-19: Rewrite all 41 description fields for triggering quality (skill-creator methodology)

A 6-agent audit using Anthropic's skill-creator methodology scored descriptions across all 41 skills. Average score: ~2.1/5. Systemic pattern: all descriptions follow passive "Use when [capability]" without listing trigger phrases users would actually type.

Worst performers (1/5): eval, slides, media, video-editing, board-sync, resolve-conflicts.
Best performers (4/5): autopilot, sprint-review.

Every description must be rewritten to:
1. Front-load natural-language trigger phrases ("I need to...", "is this ready to...", "something broke...")
2. List edge-case phrasings that should invoke the skill
3. Explicitly differentiate from the nearest competing skill
4. Drop implementation jargon from the trigger surface (no "CSO-optimized", "bounded instinct context", "canonical store")

Each agent produced improved description text for its group. Use those as starting points during implementation.

### D-082-20: Reframe ALWAYS/NEVER/MUST directives with co-located rationale

The skill-creator methodology flags all-caps directives as yellow flags. Audit found:
- `ai-slides`: 13 caps directives in 151 lines (worst ratio in the framework)
- `ai-sprint-review`: MUST without rationale for brand constants
- `ai-commit`: 2 NEVER without reasoning
- `ai-pr`: 2 NEVER without reasoning
- `ai-test`: NEVER in "Iron Law" without consequence explanation
- `ai-schema`: ALWAYS on rollback migration without explaining data loss risk

For each directive: add a one-sentence rationale explaining the consequence of violation. Example:
- Before: `NEVER uses --no-verify`
- After: `Never uses --no-verify — bypassing hooks lets secrets and lint failures through to the remote`

### D-082-21: Bundle repeated operations as skill-local scripts

The audit identified zero bundled scripts in 39 of 41 skills (only `ai-analyze-permissions` has one). High-value bundling targets:

| Skill | Script | Purpose |
|-------|--------|---------|
| video-editing | `scripts/video-cuts.sh` | Batch cut from edit decision list |
| video-editing | `scripts/video-reframe.sh` | Social platform aspect ratio reframing |
| board-sync | `scripts/board-sync-github.sh` | GitHub Projects v2 two-step item lookup + field update |
| board-discover | `scripts/discover-github.sh` | Multi-step project field discovery with jq |
| instinct | `scripts/consolidate.py` | YAML merge + context.md regeneration |
| create | `scripts/scaffold-skill.sh` | GREEN phase skill directory scaffold |
| project-identity | `scripts/detect-meta.sh` | Package file detection → structured JSON |
| slides | `scripts/convert-pptx.py` | PowerPoint conversion scaffold |

Implementation: create scripts during Wave 4 standardization. Scripts reduce hallucination risk on mechanical operations and make repeated workflows reliable.

### D-082-22: Extract shared data-gathering reference for standup/sprint/sprint-review

Three skills (standup, sprint, sprint-review) independently define near-identical git log + `gh pr list` + `az repos pr list` command sequences. Create `.ai-engineering/contexts/gather-activity-data.md` as the canonical reference. Each skill references it instead of re-defining the commands. Prevents drift when CLI flags change.

## Functional Requirements

### Wave 0: Mirror Audit (prerequisite, verify before touching any skill)

1. Verify mirror completeness: identify skills missing from each mirror (.claude, .github, .agents)
2. Known gap: `.github/skills/ai-analyze-permissions/` is absent — create it
3. Document `.agents/skills/` naming convention (no `ai-` prefix on directory names) for sync procedures
4. Wire resolve-conflicts into watch.md (D-082-07) — no wave dependencies, pure structural wiring

### Wave 1: Foundation Fixes (no structural changes, safe to ship first)

1. Fix ghost references (D-082-10)
2. Correct effort levels (D-082-09)
3. Rewrite all 41 description fields for triggering quality (D-082-19)
4. Add missing Integration sections and cross-references (D-082-15)
5. Normalize analyze-permissions frontmatter (D-082-16)
6. Register learnings path in manifest (D-082-14)
7. Sync mirrors for Wave 0+1 changes

### Wave 2: Extractions (move content, no skill count changes)

1. Extract IRRV from verify to shared protocol (D-082-04)
2. Extract governance tables from onboard to context file (D-082-05)
3. Extract Step 0 to shared protocol (D-082-17)
4. Extract shared data-gathering reference (D-082-22)
5. Create spec.md schema contract (D-082-11)

### Wave 3: Merges, Splits, and Wiring

1. Merge sprint-review into sprint (D-082-01)
2. Unify correction capture in instinct (D-082-02)
3. Split ai-write into ai-write + ai-market (D-082-03)
4. Declare verify↔security↔governance delegation (D-082-06)
5. Close governance gap in dispatch (D-082-18)
6. Sync mirrors for Wave 3 changes

### Wave 4: Standardization and Polish

1. Standardize all SKILL.md sections (D-082-12)
2. Reframe ALWAYS/NEVER/MUST directives with rationale (D-082-20)
3. Bundle repeated operations as skill-local scripts (D-082-21)
4. Reclassify skills in all IDE instruction files (D-082-13)
5. Rename ai-release to ai-release-gate (D-082-08)
6. Formalize multi-IDE frontmatter fields in ai-create schema (D-082-16)
7. Sync all 3 IDE mirrors (.claude, .github, .agents)
8. Update manifest.yml skill registry

## Data Artifacts

### New files
- `.ai-engineering/contexts/evidence-protocol.md` (extracted IRRV from verify)
- `.ai-engineering/contexts/session-governance.md` (extracted from onboard)
- `.ai-engineering/contexts/step-zero-protocol.md` (shared context loading)
- `.ai-engineering/contexts/gather-activity-data.md` (shared git/PR data collection)
- `.ai-engineering/contexts/spec-schema.md` (spec.md contract)
- `.claude/skills/ai-market/SKILL.md` (split from ai-write, + mirrors in .github/.agents)
- 8+ `scripts/` directories in individual skills (video-editing, board-sync, board-discover, instinct, create, project-identity, slides, analyze-permissions)

### Deleted
- `.claude/skills/ai-sprint-review/` (merged into ai-sprint, + mirrors)

### Modified (key files per wave)

**Wave 0**: `ai-pr/handlers/watch.md`, `.github/skills/ai-analyze-permissions/SKILL.md` (created)

**Wave 1**: `ai-security/SKILL.md`, `ai-governance/SKILL.md`, `ai-release/SKILL.md`, `ai-schema/SKILL.md` (ghost fixes); 8 SKILL.md files (effort); 15+ SKILL.md files (cross-refs); `manifest.yml` (learnings path)

**Wave 2**: `ai-verify/SKILL.md` (IRRV removal), `ai-onboard/SKILL.md` (governance extraction), 5+ SKILL.md files (Step 0 replacement)

**Wave 3**: `ai-sprint/SKILL.md` (gains review mode), `ai-learn/SKILL.md` (loses post-correction), `ai-write/SKILL.md` (loses 6 handlers), `ai-verify/SKILL.md` (delegation declarations), `ai-dispatch/handlers/quality.md` (governance gate)

**Wave 4**: All 41 SKILL.md files (section standardization), `CLAUDE.md` (effort table, group reclassification), `manifest.yml` (skill registry update)

## Success Criteria

- Zero ghost skill references in any SKILL.md
- All 41 skills have standardized sections (When to Use, Process/Modes, Integration)
- All effort levels match the framework's cognitive weight criteria
- `ai-verify security` explicitly delegates to `ai-security` (traceable in SKILL.md)
- `ai-resolve-conflicts` is called from `watch.md` during automated CI repair
- `ai-write` contains zero marketing/investor handlers
- `ai-onboard` contains zero inline governance policy tables
- `spec.md` has a defined schema that both brainstorm and plan validate
- All 3 IDE mirrors (.claude, .github, .agents) are in sync after Wave 4
- No skill has a "Called by" reference to a skill that doesn't actually call it
- All 41 descriptions include natural-language trigger phrases (not just capability summaries)
- Zero ALWAYS/NEVER/MUST in caps without a co-located rationale sentence
- 8+ skill-local scripts bundled for high-value repeated operations
- Shared data-gathering reference exists and is consumed by standup, sprint, sprint-review

## Implementation Notes for Planning

- Wave 0 is a prerequisite audit — must complete before structural work begins
- Wave 1 is pure text edits — no logic changes, minimal risk
- Wave 2 creates new context files and updates references — moderate risk
- Wave 3 moves handlers between skills and changes integration — highest risk, needs careful testing
- Wave 4 is standardization sweep — tedious but low risk
- Each wave should be a separate branch/PR for reviewability
- Mirror sync (.github, .agents) should happen per-wave, not deferred to the end
- `.agents/skills/` uses directory names without `ai-` prefix — sync procedure must account for this naming convention
- The ai-release rename (D-082-08) is a simple rename; actual release mechanics deferred to a future spec
- D-082-07 (resolve-conflicts wiring) moved to Wave 0 because it has zero wave dependencies
