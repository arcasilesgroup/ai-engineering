---
total: 5
completed: 5
---

# Plan: sub-003 Instinct Skill Rewrite - Listening + Review

## Plan

exports: ["ai-instinct SKILL.md v2 (listening mode + --review)", "ai-onboard listening activation", "ai-commit --review pre-step", "ai-pr --review pre-step"]
imports: ["instincts.yml v2 schema (sub-002)", "confidence scoring API (sub-002)"]

- [x] T-3.1: Rewrite /ai-instinct SKILL.md with two commands
  - **Files**: `.claude/skills/ai-instinct/SKILL.md`
  - **Done**: Frontmatter updated (description CSO-optimized for listening/review triggers). Two commands: `/ai-instinct` (listening mode — single line output, silent) and `/ai-instinct --review` (5-step consolidation: extract, enrich, write, evaluate, create work items). References v2 families. Artifact set updated (no context.md). Boundaries section updated.

- [x] T-3.2: Update /ai-onboard to activate listening mode
  - **Files**: `.claude/skills/ai-onboard/SKILL.md`
  - **Done**: Lines 35-38 replaced: no longer reads context.md. Instead: "Activate `/ai-instinct` listening mode" as final onboard step. Reads LESSONS.md from new path (.ai-engineering/LESSONS.md per sub-001).

- [x] T-3.3: Add --review pre-step to /ai-commit
  - **Files**: `.claude/skills/ai-commit/SKILL.md`
  - **Done**: New step 0.6 after work item context: "Run `/ai-instinct --review` to consolidate session observations before committing." Conditional: only if listening mode was active (check instincts.yml exists).

- [x] T-3.4: Add --review pre-step to /ai-pr
  - **Files**: `.claude/skills/ai-pr/SKILL.md`
  - **Done**: New step 6.7 after docs: "Run `/ai-instinct --review` to consolidate session observations before creating PR." Same conditional as T-3.3.

- [x] T-3.5: Delete instinct consolidate.py script
  - **Files**: `.claude/skills/ai-instinct/scripts/consolidate.py`
  - **Done**: Script removed (v1 artifact). References in SKILL.md removed.

### Confidence
- **Level**: high
- **Assumptions**: Listening mode pattern works reliably across IDEs (behavioral, not hook-based). CSO-optimized description ensures correct triggering.
- **Unknowns**: None — all files read, patterns clear.

## Self-Report

**Status**: 5/5 tasks complete.

**Changes summary**:
- `.claude/skills/ai-instinct/SKILL.md`: Full rewrite. Two commands: `/ai-instinct` (listening mode -- single line output, then silent) and `/ai-instinct --review` (5-step consolidation: EXTRACT corrections/recoveries/workflows from conversation, ENRICH from ndjson streams with semantic trigger/action, WRITE to instincts.yml v2 schema with confidence scoring and merge rules, EVALUATE cross-referencing LESSONS.md for proposal generation at confidence >= 0.7 and evidenceCount >= 3, CREATE WORK ITEMS via gh/az if manifest work_items configured). Artifact set updated: instincts.yml, meta.json, proposals.md (no context.md). Description CSO-optimized for listening/review trigger phrases. Frontmatter preserved: name, description, effort, argument-hint, tags. Scripts section removed (consolidate.py deleted).
- `.claude/skills/ai-onboard/SKILL.md`: Step 3 replaced -- no longer reads meta.json/context.md; now activates `/ai-instinct` listening mode. LESSONS.md path updated from `contexts/team/lessons.md` to `.ai-engineering/LESSONS.md`. Quick status instinct line updated to "listening mode activated". Boundaries updated: onboard no longer writes instinct artifacts.
- `.claude/skills/ai-commit/SKILL.md`: New step 0.6 (Instinct consolidation) added after work item context (0.5), before staging (1). Conditional on instincts.yml existence.
- `.claude/skills/ai-pr/SKILL.md`: New step 6.7 (Instinct consolidation) added after docs finalization (6.5), before pre-push checks (7). Same conditional as commit.
- `.claude/skills/ai-instinct/scripts/consolidate.py`: Deleted (v1 artifact). Empty scripts/ directory removed.

**Validation**: All edits are markdown-only skill files -- no linter/compiler gates apply. Verified each file post-edit: frontmatter intact, step numbering consistent, no broken references to deleted artifacts (context.md, consolidate.py). No IDE mirror changes (deferred to sub-005 per spec).

**Risks**: None identified. All changes are behavioral instructions in skill markdown -- no runtime code affected.
