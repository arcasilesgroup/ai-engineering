# Plan: Spec-055 — Radical Simplification

## Execution Order

### Fase 1: Spec + Branch ✅
- [x] Branch: `spec/055-radical-simplification`
- [x] Scaffold spec files

### Fase 2: Write 28 skills
- [ ] Core workflow (7): brainstorm, plan, dispatch, test, debug, verify, review
- [ ] Delivery (4): commit, pr, release, cleanup
- [ ] Enterprise (4): security, governance, pipeline, schema
- [ ] Teaching+writing (3): explain, guide, write
- [ ] SDLC (6): note, standup, sprint, postmortem, support, resolve-conflicts
- [ ] Meta (4): create, learn, prompt, onboard

### Fase 3: Write 8 agents
- [ ] plan, build, verify, guard, review, explore, guide, simplify

### Fase 4: New CLAUDE.md + AGENTS.md
- [ ] CLAUDE.md ~120 lines (workflow orchestration + agent matrix + gates)
- [ ] AGENTS.md ~80 lines (multi-IDE, no duplication)

### Fase 5: Delete old artifacts
- [ ] 19 old skills
- [ ] standards/ (65 files)
- [ ] contracts (product-contract.md, framework-contract.md)
- [ ] 4 state files (ownership-map, install-manifest, health-history, session-checkpoint)

### Fase 6: Contexts
- [ ] Create contexts/ with hierarchical structure (languages/frameworks/orgs/team)
- [ ] Merge Python context from review-code + dotfiles
- [ ] Merge Rust context from review-code + dotfiles

### Fase 7: Simplified manifest
- [ ] ~80 lines manifest.yml

### Fase 8: Templates + installer
- [ ] Single source .claude/ → auto-generate mirrors
- [ ] Interactive install with smart prompts
- [ ] Feature-based installation

### Fase 9: Sync script
- [ ] Canonical = .claude/
- [ ] Generate .agents/, .github/ from .claude/

### Fase 10: Tasks + lessons system
- [ ] .ai-engineering/tasks/todo.md + lessons.md

### Fase 11: E2E verification
- [ ] pytest green
- [ ] ruff green
- [ ] ai-eng gate all green
- [ ] Sync 0 errors
- [ ] Install in clean repo works
- [ ] Full workflow: brainstorm → plan → dispatch → review → commit → pr
