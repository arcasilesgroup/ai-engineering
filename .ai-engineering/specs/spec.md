---
id: spec-080
title: "Standards Engine, Governance Parity, Delivery Intelligence"
status: draft
created: 2026-03-26
refs: []
---

# Spec 080: Standards Engine, Governance Parity, Delivery Intelligence

## Problem

The framework has 14 language contexts, 15 framework contexts, and 4 team contexts — but 87% of skills (33/38) never load them. The `code` classify mode in ai-build is 4 words ("Write code following stack standards") with no backing skill. Stack detection is fragmented across 3 independent systems with incompatible vocabularies. AGENTS.md has drifted from CLAUDE.md with 5 missing sections. PR documentation updates are superficial (presence-checked, not quality-checked). Work item boards show binary state (open → closed) with zero intermediate updates. 10 governance values from framework-contract.md were eliminated without migration.

## Solution

Eight sub-specs executed sequentially by `/ai-autopilot`:

### Sub-spec 1: `/ai-code` Skill

Create a dedicated `/ai-code` skill (SKILL.md + handlers) that replaces the 4-word `code` classify mode in ai-build. The skill defines the procedure for writing code: pre-coding checklist, context loading, file placement, interface-first protocol, backward-compatibility checks, and self-review against loaded contexts.

The skill loads contexts with **layer precedence**: `team/ > frameworks/ > languages/`. When team conventions conflict with framework defaults, team wins. Precedence is declared in manifest.yml as `contexts.precedence: [team, frameworks, languages]`.

Build-time validation is **lightweight**: after each write, self-check against the loaded context rules focusing on the most impactful categories — naming conventions, anti-patterns, and error handling patterns. The self-check uses the same category structure as ai-review's `lang-generic.md` handler (naming, idiomatic patterns, anti-patterns, error handling) but checks only the critical categories. Full exhaustive validation remains in `/ai-review` at review-time.

ai-build's classify table updates the `code` row to reference `/ai-code` SKILL.md, matching how `test` references `/ai-test` and `debug` references `/ai-debug`.

### Sub-spec 2: Unified Stack Detection

Manifest `providers.stacks` becomes the **single source of truth** for stack detection. All agents and skills read the manifest instead of reimplementing file-based heuristics. Auto-detection via file markers becomes the fallback only when the manifest field is empty or missing.

Changes:
- ai-build: replace "Detect Stack" section with "read `manifest.yml providers.stacks`"
- ai-security, ai-pipeline, ai-review: same change — read manifest, not project files
- manifest.yml schema: unify the stacks enum vocabulary — separate `languages` from `frameworks` to eliminate the current mix (e.g., `python` is a language, `react` is a framework)
- `autodetect.py`: remains as install-time detection, writes to manifest. Not used at runtime by agents
- `ai-eng doctor`: add check for drift between manifest stacks and actual project files

### Sub-spec 3: Context Loading Enforcement

Enforce context loading for skills that generate or analyze code: ai-code (new), ai-test, ai-debug, ai-review, ai-verify, ai-schema, ai-pipeline, ai-security. The remaining 30+ skills (SDLC, delivery, teaching, meta) are exempt.

Dual enforcement mechanism:
1. **Per-skill**: each affected SKILL.md gets an explicit "Step 0: Load Contexts" with the procedure from ai-build Section 2 (read languages/, frameworks/, team/ per detected stack)
2. **Dispatch injection**: ai-dispatch injects applicable context content into the subagent prompt as a safety net, so even if the skill's Step 0 is skipped, the contexts are present

Update ai-autopilot `phase-implement.md` and `phase-deep-plan.md` to include team context (currently they pass language + framework but omit team).

### Sub-spec 4: Build Standards Validation

Close the gap between "contexts are loaded as inputs" and "code is validated against those inputs."

At build-time (in `/ai-code`): after writing code, the agent performs a lightweight self-check against the critical categories from loaded contexts (naming conventions, anti-patterns, error handling). This produces a compliance trace (category → checked/deviation found) included in the task output.

At review-time (in `/ai-review`): the existing `lang-generic.md` and per-language handlers continue doing the full exhaustive check against all context rules. This remains the comprehensive validation layer.

The gap closed: currently review catches deviations that build could have prevented. With build-time lightweight checks, critical violations are caught at write-time, reducing fix-loop round-trips.

### Sub-spec 5: Governance Values Migration

Restore the 5 critical governance values lost when framework-contract.md was eliminated (DEC-027). The remaining 5 (pipeline auto-classification, reprompt conditions, session map, stakeholders/personas, NFRs) are either already covered elsewhere (reprompt conditions → ai-governance skill), intentionally descoped (session map → DEC-004 flat main), or non-blocking (stakeholders → optional in project-identity.md, NFRs/pipeline classification → future enhancement).

Critical values to restore:

| Value | Destination | Content |
|-------|------------|---------|
| Cross-OS mandate (Windows, macOS, Linux) | CLAUDE.md Core Principles | Add: "Cross-platform: all changes must work on Windows, macOS, and Linux" |
| Decision-weakening protocol | CLAUDE.md Don't section | Add: "NEVER weaken a gate without: warn user → generate remediation patch → require explicit risk acceptance → persist to decision-store → append to audit-log" |
| Pre-dispatch guard gate | ai-dispatch SKILL.md | Add mandatory step: "Before dispatching any build task, invoke the Guard agent (`ai-guard`) for governance advisory — fail-open: log warning if guard unavailable, never block dispatch" |
| Content integrity trigger | ai-commit SKILL.md | Add step: "If any `.ai-engineering/` file was created/deleted/renamed, run `ai-eng validate`" |
| Context Output Contract | Agent definitions (all 9) | Add: "Every agent produces structured output: Findings, Dependencies Discovered, Risks Identified, Recommendations" |

Update CLAUDE.md, ai-dispatch SKILL.md, ai-commit SKILL.md, and all 9 agent definitions. Mirror changes to templates and IDE surfaces.

### Sub-spec 6: AGENTS.md Single-Source Generation

CLAUDE.md becomes the canonical source. `sync_command_mirrors.py` is extended to generate AGENTS.md and copilot-instructions.md from CLAUDE.md with platform-appropriate adaptations.

Changes:
- `sync_command_mirrors.py`: add generation functions for AGENTS.md (strip Claude-specific references) and copilot-instructions.md (add Copilot-specific subagent orchestration, hooks)
- Fix template copilot-instructions.md agent path: `ai-<name>.agent.md` → `<name>.agent.md`
- Validator: add content parity check between CLAUDE.md source and generated AGENTS.md/copilot-instructions.md
- Remove AGENTS.md `# CLAUDE.md` title (confuses Gemini CLI parsing)
- Restore the 5 missing items in AGENTS.md: Context Loading section, project-identity load instruction, autopilot row in Agent Selection table, Effort Levels section, correct hook event name

### Sub-spec 7: Deep Documentation in `/ai-docs`

Create `/ai-docs` skill that absorbs `ai-solution-intent` and becomes the specialized project documentation skill. `ai-write` retains general writing (articles, pitches, content).

`/ai-docs` has 7 handlers:

| Handler | Purpose |
|---------|---------|
| `changelog.md` | Read full diff semantically, write user-facing CHANGELOG entries |
| `readme.md` | Read changed code + current READMEs, rewrite affected sections |
| `solution-intent-init.md` | Scaffold solution-intent from project state (from ai-solution-intent) |
| `solution-intent-sync.md` | Diff-aware rewrite — compare document against current project state, rewrite misaligned sections (removes "surgical only" restriction) |
| `solution-intent-validate.md` | Completeness/freshness scorecard (from ai-solution-intent) |
| `docs-portal.md` | External docs: detect default branch → git pull/clone → update → PR. If PR pending, reference in our PR body |
| `docs-quality-gate.md` | 5th subagent: verify all doc outputs reflect 100% of semantic changes from the diff |

ai-pr dispatches 5 subagents in parallel during documentation:
1. Subagent CHANGELOG → `ai-docs changelog`
2. Subagent README → `ai-docs readme`
3. Subagent solution-intent → `ai-docs solution-intent-sync`
4. Subagent docs-portal → `ai-docs docs-portal` (if `external_portal.enabled: true`)
5. Quality gate subagent → `ai-docs docs-quality-gate` (reviews output of 1-4)

External docs portal flow:
- If local directory: detect default branch (`git symbolic-ref refs/remotes/origin/HEAD`), `git pull`, update, commit, push/PR
- If remote URL: `git clone` to temp, update, create PR
- If PR cannot complete: add comment to our PR with link to docs PR noting it is pending

ai-solution-intent is eliminated as independent skill. Skill count: 38 - 1 (solution-intent) + 4 (ai-code, ai-docs, ai-board-discover, ai-board-sync) = **41 skills**.

### Sub-spec 8: Work Item Lifecycle — `/ai-board-discover` + `/ai-board-sync`

**`/ai-board-discover`** (new skill): LLM-assisted post-install discovery. Explores the team's board provider, discovers process template, valid states per work item type, custom fields, workflow transitions, GitHub Projects v2 columns, documentation URLs, and CI/CD standards URLs. Writes complete configuration to manifest.yml.

New manifest sections:

```yaml
work_items:
  # ... existing fields ...
  state_mapping:
    refinement: "Refinement"     # or ADO state name / GH label
    ready: "Ready"
    in_progress: "Active"
    in_review: "In Review"
    done: "Closed"
  process_template: "agile"      # agile|scrum|cmmi|basic (ADO) or "github"
  custom_fields: []              # discovered custom fields
  github_project:
    number: null                 # Projects v2 number if detected
    status_field_id: null        # Projects v2 status field
```

GitHub handling: Projects v2 is first option for state management (real board columns). If no Projects v2 configured, fallback to labels (`status:in-progress`, etc.).

**`/ai-board-sync`** (new skill): operational sync invoked by other skills at transition points. Reads state_mapping from manifest.yml, updates work items via provider CLI.

| Trigger Skill | Phase | State Update |
|--------------|-------|--------------|
| ai-brainstorm | Work item fetched | → `refinement` |
| ai-brainstorm | Spec written | → `ready` |
| ai-dispatch | Implementation starts | → `in_progress` |
| ai-pr | PR created | → `in_review` |
| Platform | PR merged | → `done` (via keyword autoclose) |

ai-board-sync updates ALL applicable fields per transition: state, custom fields (remaining work, acceptance criteria status), tags, comments with spec/PR references.

Remove "set during install or edit manually" comments from manifest.yml. These fields are populated by `/ai-board-discover`, not the install wizard.

## Scope

### In Scope

- Create 4 new skills: `/ai-code`, `/ai-docs` (absorbing ai-solution-intent, 7 handlers), `/ai-board-discover`, `/ai-board-sync`
- Remove 1 skill: ai-solution-intent (absorbed into ai-docs)
- Modify ai-build agent (stack detection, code classify reference)
- Modify ai-dispatch (context injection, pre-dispatch guard gate)
- Modify ai-pr (5 documentation subagents, board-sync integration)
- Modify ai-brainstorm, ai-commit (board-sync integration)
- Modify ai-onboard (ensure manifest work_items and board config are loaded at session start)
- Update CLAUDE.md Effort Levels table and skill group listings for new/removed skills
- Extend sync_command_mirrors.py (generate AGENTS.md, copilot-instructions.md)
- Extend manifest.yml schema (contexts.precedence, work_items.state_mapping, work_items.process_template, work_items.custom_fields, work_items.github_project)
- Update CLAUDE.md (governance values, context loading)
- Update all 9 agent definitions (Context Output Contract)
- Mirror all changes to templates and IDE surfaces (.github/, .agents/)

### Out of Scope

- Rewriting existing context files (languages/, frameworks/, team/) — their content is adequate
- Creating new language or framework context files
- Modifying the install wizard (stays lean: stacks, IDEs, VCS provider)
- CI/CD pipeline changes
- Jira or other non-ADO/non-GitHub board providers
- Wiki-specific APIs (Confluence, etc.) — docs portal uses git-based wikis only
- Runtime enforcement hooks for context loading (enforcement is instruction-based + dispatch injection)

## Acceptance Criteria

### Sub-spec 1: /ai-code
- [ ] `.claude/skills/ai-code/SKILL.md` exists with pre-coding checklist, context loading, self-review procedure
- [ ] ai-build classify table `code` row references `/ai-code` SKILL.md
- [ ] manifest.yml has `contexts.precedence: [team, frameworks, languages]`
- [ ] Self-review produces compliance trace per critical category (naming, anti-patterns, error handling)
- [ ] Mirrors exist in `.github/skills/` and `.agents/skills/`

### Sub-spec 2: Stack Detection
- [ ] ai-build, ai-security, ai-pipeline, ai-review read `manifest.yml providers.stacks` instead of file heuristics
- [ ] manifest.yml schema separates language enum from framework enum
- [ ] `ai-eng doctor` reports drift between manifest stacks and project files

### Sub-spec 3: Context Loading
- [ ] 8 skills (ai-code, ai-test, ai-debug, ai-review, ai-verify, ai-schema, ai-pipeline, ai-security) have explicit "Step 0: Load Contexts"
- [ ] ai-dispatch injects context content into subagent prompts
- [ ] ai-autopilot phase-implement and phase-deep-plan include team context

### Sub-spec 4: Build Validation
- [ ] `/ai-code` self-check validates critical categories (naming, anti-patterns, error handling) from loaded contexts
- [ ] Compliance trace is included in task output (category → checked/deviation)
- [ ] ai-review continues full exhaustive validation (no regression)

### Sub-spec 5: Governance Values
- [ ] CLAUDE.md contains cross-OS mandate in Core Principles
- [ ] CLAUDE.md Don't section contains decision-weakening protocol
- [ ] ai-dispatch has pre-dispatch guard advisory step (invokes ai-guard agent, fail-open)
- [ ] ai-commit triggers `ai-eng validate` when `.ai-engineering/` files change
- [ ] All 9 agent definitions include Context Output Contract (Findings, Dependencies, Risks, Recommendations)

### Sub-spec 6: AGENTS.md Generation
- [ ] sync_command_mirrors.py generates AGENTS.md from CLAUDE.md
- [ ] sync_command_mirrors.py generates copilot-instructions.md from CLAUDE.md
- [ ] AGENTS.md has no `# CLAUDE.md` title
- [ ] Template copilot-instructions.md has correct agent path (`<name>.agent.md`)
- [ ] Validator checks content parity between source and generated files
- [ ] All 5 previously missing items are present in generated AGENTS.md (Context Loading section, project-identity instruction, autopilot Agent Selection row, Effort Levels section, correct hook event name)

### Sub-spec 7: /ai-docs
- [ ] `/ai-docs` skill exists with 7 handlers (changelog, readme, solution-intent-init, solution-intent-sync, solution-intent-validate, docs-portal, docs-quality-gate)
- [ ] ai-solution-intent skill directory removed
- [ ] ai-pr dispatches 5 documentation subagents in parallel
- [ ] docs-quality-gate subagent produces a checklist mapping each changed function/class/module to its documentation update, with zero uncovered items
- [ ] solution-intent-sync rewrites prose sections when misaligned (not surgical-only)
- [ ] docs-portal detects default branch before pull/clone
- [ ] docs-portal references pending PR in our PR body when PR cannot complete
- [ ] manifest.yml skill registry updated (remove ai-solution-intent, add ai-code, ai-board-discover, ai-board-sync, ai-docs; total: 41)
- [ ] CLAUDE.md Effort Levels table updated with new skills and corrected counts
- [ ] CLAUDE.md skill group listings updated (Enterprise: replace solution-intent with ai-docs; add ai-code, ai-board-discover, ai-board-sync to appropriate groups)
- [ ] ai-onboard loads manifest `work_items` config and makes it available for the session

### Sub-spec 8: Work Item Lifecycle
- [ ] `/ai-board-discover` skill exists — discovers states, custom fields, process template, Projects v2
- [ ] `/ai-board-sync` skill exists — updates work items at each lifecycle phase
- [ ] manifest.yml schema supports `state_mapping`, `process_template`, `custom_fields`, `github_project`
- [ ] ai-brainstorm invokes board-sync at refinement and ready transitions
- [ ] ai-dispatch invokes board-sync at in_progress transition
- [ ] ai-pr invokes board-sync at in_review transition
- [ ] GitHub Projects v2 is first option; labels are fallback
- [ ] ai-board-discover also discovers documentation URLs and CI/CD standards URLs
- [ ] "set during install or edit manually" comments removed from manifest.yml
- [ ] All discovered custom fields are round-tripped (read and written back)
- [ ] ai-board-discover writes to manifest only after full discovery completes (no partial writes)
- [ ] ai-board-sync is fail-open (logs warning, never blocks main workflow)
- [ ] docs-portal cleans up local branches on PR creation failure (no orphaned branches)

## Assumptions

- ASSUMPTION: Azure DevOps `az boards` CLI and GitHub `gh` CLI are available in the user's environment when board discovery/sync runs
- ASSUMPTION: Context files in `contexts/languages/` and `contexts/frameworks/` have sufficient content for build-time self-review (no new context files needed)
- ASSUMPTION: GitHub Projects v2 GraphQL API is accessible via `gh api graphql` without additional authentication beyond standard `gh auth`
- ASSUMPTION: Teams using Azure DevOps have consistent process templates across their project (not mixed Agile+Scrum in same project)
- ASSUMPTION: External documentation repos are git-based and accessible via the user's current git credentials

## Risks

- **Context loading token overhead**: loading language + framework + team contexts adds tokens to every code-touching skill invocation. Mitigation: only 8 skills load contexts; content is ≤1 page per file (DEC-014)
- **Board sync failures**: provider CLI may fail (auth expired, network, permissions). Mitigation: board-sync is fail-open — log warning and continue, never block the main workflow
- **Board discover partial failure**: discovery may fail mid-way (auth, network, missing permissions). Mitigation: ai-board-discover writes to manifest only after full discovery completes; partial results are not written. If discovery fails, manifest retains its previous state and the user is informed of what failed and why
- **Docs-portal clone/PR failure**: external repo operations may fail (permissions, network, branch conflicts). Mitigation: if clone fails, skip external docs and log warning in PR body. If PR creation fails, clean up the local branch and reference the failure in our PR body. Never leave orphaned branches in external repos
- **AGENTS.md generation drift**: generated file may lose nuances of manually-maintained content. Mitigation: validator checks parity; human review on sync
- **Solution-intent rewrite aggressiveness**: diff-aware rewrite may inadvertently alter user-authored sections. Mitigation: docs-quality-gate subagent reviews all changes; git diff available for human review before commit
- **GitHub Projects v2 API instability**: GraphQL API for Projects v2 may change. Mitigation: discovery caches field IDs in manifest; re-run discover if API changes

## Dependencies

- DEC-027 (contracts eliminated) — this spec fills the governance gaps left by that decision
- DEC-005 (single-source generation) — sub-spec 6 implements the mechanism DEC-005 promised
- DEC-014 (lean stack standards ≤1 page) — enables lightweight context loading without token bloat
- spec-079 (install & contexts cleanup) — must be merged before this spec starts (currently on main)

## Execution Order

Sequential by criticality (for `/ai-autopilot`):

1. Sub-spec 5: Governance Values Migration
2. Sub-spec 2: Unified Stack Detection
3. Sub-spec 3: Context Loading Enforcement
4. Sub-spec 1: `/ai-code` Skill
5. Sub-spec 4: Build Standards Validation
6. Sub-spec 6: AGENTS.md Single-Source Generation
7. Sub-spec 7: `/ai-docs` Deep Documentation
8. Sub-spec 8: Work Item Lifecycle (`/ai-board-discover` + `/ai-board-sync`)
