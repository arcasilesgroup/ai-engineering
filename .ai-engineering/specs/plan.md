# Plan: Spec-055 — Radical Simplification

## Execution Order

### Fase 1: Spec + Branch ✅
- [x] Branch: `spec/055-radical-simplification`
- [x] Scaffold spec files

### Fase 2: Write 28 skills ✅
- [x] Core workflow (7): brainstorm, plan, dispatch, test, debug, verify, review
- [x] Delivery (4): commit, pr, release, cleanup
- [x] Enterprise (4): security, governance, pipeline, schema
- [x] Teaching+writing (3): explain, guide, write
- [x] SDLC (6): note, standup, sprint, postmortem, support, resolve-conflicts
- [x] Meta (4): create, learn, prompt, onboard

### Fase 3: Write 8 agents ✅
- [x] plan, build, verify, guard, review, explore, guide, simplify

### Fase 4: New CLAUDE.md + AGENTS.md ✅
- [x] CLAUDE.md rewritten (workflow orchestration + agent matrix + gates)
- [x] AGENTS.md rewritten (multi-IDE, no duplication)

### Fase 5: Delete old artifacts ✅
- [x] 19 old skills
- [x] standards/ (65 files)
- [x] contracts (product-contract.md, framework-contract.md)
- [x] 4 state files (ownership-map, install-manifest, health-history, session-checkpoint)

### Fase 6: Contexts ✅
- [x] Create contexts/ with hierarchical structure (languages/frameworks/orgs/team)
- [x] Merge Python context from review-code + dotfiles
- [x] Merge Rust context from review-code + dotfiles

### Fase 7: Simplified manifest ✅
- [x] Schema 2.0 manifest.yml

### Fase 8: Templates + installer ✅
- [x] Single source .claude/ → auto-generate mirrors
- [x] Installer templates updated

### Fase 9: Sync script ✅
- [x] Canonical = .claude/
- [x] Generate .agents/, .github/ from .claude/

### Fase 10: Eliminate tasks/ dead code ✅
- [x] Delete tasks/todo.md and tasks/lessons.md
- [x] Update layout.py, manifest ownership, ai-onboard, ai-learn

### Fase 11: Unify CLAUDE.md = AGENTS.md ✅
- [x] 4 files byte-identical (root + templates)

### Fase 12: Clean ghost skills from agents ✅
- [x] Remove 13 ghost skill references from ai-build, ai-verify, ai-plan, ai-guide

### Fase 13: Synchronize agent colors ✅
- [x] AGENT_METADATA updated
- [x] .agents/ + .github/ propagated

### Fase 14: Fix dead references in skills ✅
- [x] ai-pr, ai-commit, ai-security, ai-pipeline, +12 more skills cleaned
- [x] 51 /ai-code references migrated to ai-build agent

### Fase 15: Create /ai-solution-intent ✅
- [x] SKILL.md + 3 handlers (init/sync/validate)
- [x] Registered in manifest (29 skills)

### Fase 16: Create lessons.md + frontmatter + translate_refs ✅
- [x] contexts/team/lessons.md created
- [x] Frontmatter standardized (name, description, color, model, tools)
- [x] Directory path translation in mirrors

### Fase 17: Improve ai-create + analyze-permissions ✅
- [x] 3 handlers for ai-create (create-skill, create-agent, validate)
- [x] /ai-analyze-permissions ported from dotfiles (30 skills)

### Fase 18: Regenerate solution-intent.md ✅
- [x] 798 lines, 13 Mermaid diagrams, data from real audit
- [x] Handlers rewritten with 7-section depth

### Fase 19: Fix test suite ✅
- [x] uv sync (Python 3.12)
- [x] test_sync_mirrors.py rewritten
- [x] test_validator.py updated (paths, structure)
- [x] test_agent_schema_validation.py updated
- [x] test_skill_schema_validation.py updated
- [x] test_updater.py updated
- [x] defaults.py ownership bug fixed
- [x] validator categories updated (version optional, manifest coherence)

### Fase 20: Spec sync ✅
- [x] Update tasks.md and plan.md with all progress (Fases 1-19)
- [x] Add new Fases 21-22

### Fase 21: Restore Workflow Orchestration
- [ ] Restore 9 behavioral subsections in CLAUDE.md/AGENTS.md
- [ ] Restore Task Management section
- [ ] Restore Core Principles section
- [ ] Copy to 4 identical files (root CLAUDE.md, root AGENTS.md, template CLAUDE.md, template AGENTS.md)

### Fase 22: Fix Audit Log
- [ ] Direct NDJSON write (replace ai-eng signals emit)
- [ ] Name normalization (ai-<name> convention)
- [ ] Safety-net in Python aggregators
- [ ] Debug mode opt-in
- [ ] Tests for audit log write path
- [ ] Sync templates with new audit log behavior
