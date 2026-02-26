---
spec: "024"
total: 12
completed: 12
last_session: "2026-02-26"
next_session: "Complete"
---

# Tasks — OSS Documentation Gate

## Phase 0: Revert model_tier [S]

- [x] 0.1 Remove `model_tier: fast` from 5 workflow skill frontmatters
- [x] 0.2 Remove Model Tier Standard section from `skills-schema.md`
- [x] 0.3 Remove `model_tier` from `manifest.yml` commands
- [x] 0.4 Remove model tier hints from 5 Claude Code command wrappers
- [x] 0.5 Remove model tier advisory from 5 Copilot prompt wrappers
- [x] 0.6 Sync all template mirrors

## Phase 1: Enhanced Documentation Gate [S]

- [x] 1.1 Update `/commit` doc gate: CHANGELOG + README + external portal
- [x] 1.2 Update `/pr` doc gate: CHANGELOG + README + external portal + PR checklist
- [x] 1.3 Update `/acho` doc gate references
- [x] 1.4 Sync workflow skill template mirrors

## Phase 2: Standards + Registration [S]

- [x] 2.1 Update `core.md` non-negotiables and command governance for OSS docs
- [x] 2.2 Update `decision-store.json`: remove D024-001 (model tier), update D024-002 → D024-001 (doc gate)
- [x] 2.3 Rewrite spec files (spec.md, plan.md, tasks.md)
- [x] 2.4 Update CHANGELOG.md
- [ ] 2.5 Run `integrity-check`
