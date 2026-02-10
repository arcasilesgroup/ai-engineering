---
spec: "003"
total: 30
completed: 0
last_session: "2026-02-10"
next_session: "Phase 0 — Scaffold"
---

# Tasks — Governance Enforcement

## Phase 0: Scaffold [S]

- [x] 0.1 Create `specs/003-governance-enforcement/` with spec.md, plan.md, tasks.md.
- [x] 0.2 Update `_active.md` → `003-governance-enforcement`.
- [x] 0.3 Create branch `feat/spec-003-governance-enforcement`.

## Phase 1: Skill create-spec [L]

- [ ] 1.1 Create canonical `skills/lifecycle/create-spec.md` — 8-phase procedure with branch-first step.
- [ ] 1.2 Create template mirror `src/.../skills/lifecycle/create-spec.md` (byte-identical).

## Phase 2: Skills delete-skill and delete-agent [L]

- [ ] 2.1 Create canonical `skills/lifecycle/delete-skill.md` — inverse procedure with dependency checks.
- [ ] 2.2 Create template mirror for delete-skill (byte-identical).
- [ ] 2.3 Create canonical `skills/lifecycle/delete-agent.md` — inverse procedure with dependency checks.
- [ ] 2.4 Create template mirror for delete-agent (byte-identical).

## Phase 3: Skill content-integrity [L]

- [ ] 3.1 Create canonical `skills/lifecycle/content-integrity.md` — 6-category validation skill.
- [ ] 3.2 Create template mirror for content-integrity (byte-identical).

## Phase 4: Expand verify-app [S]

- [ ] 4.1 Add content integrity capability to `agents/verify-app.md`.
- [ ] 4.2 Add behavior step 10: execute content-integrity skill.
- [ ] 4.3 Add `skills/lifecycle/content-integrity.md` to Referenced Skills.
- [ ] 4.4 Update verify-app template mirror (byte-identical).

## Phase 5: Enforcement rules [M]

- [ ] 5.1 Add "Spec-First Enforcement" section to `standards/framework/core.md`.
- [ ] 5.2 Add "Content Integrity Enforcement" section to `standards/framework/core.md`.
- [ ] 5.3 Update Session Contract in core.md: fallback + post-change validation rules.
- [ ] 5.4 Update framework-contract.md 9.5: add step 0 (create-spec) and step 7 (content-integrity).
- [ ] 5.5 Update manifest.yml: add `validate_content_integrity` to close_actions.
- [ ] 5.6 Update core.md template mirror (byte-identical).

## Phase 6: Update existing lifecycle skills [S]

- [ ] 6.1 Update `create-skill.md` References: add delete-skill, content-integrity.
- [ ] 6.2 Update `create-agent.md` References: add delete-agent, content-integrity.
- [ ] 6.3 Update mirrors for create-skill and create-agent (byte-identical).

## Phase 7: Integration [M]

- [ ] 7.1 Add 4 new lifecycle skills to all 6 instruction files under `### Lifecycle Skills`.
- [ ] 7.2 Update product-contract.md counters: 21→25 skills.
- [ ] 7.3 Update product-contract.md Active Spec → 003-governance-enforcement.
- [ ] 7.4 Add 4 new skill entries to CHANGELOG.md.
- [ ] 7.5 Add cross-references: create-spec ↔ create-skill, create-agent, prompt-engineer.
- [ ] 7.6 Add cross-references: delete-skill ↔ create-skill, content-integrity.
- [ ] 7.7 Add cross-references: delete-agent ↔ create-agent, content-integrity.
- [ ] 7.8 Add cross-references: content-integrity ↔ verify-app, create-skill, create-agent, delete-skill, delete-agent.

## Phase 8: Verify + Closure [S]

- [ ] 8.1 Verify all canonical/mirror pairs byte-identical.
- [ ] 8.2 Verify 6 instruction files list 6 lifecycle skills.
- [ ] 8.3 Verify product-contract counter = 25 skills, 8 agents.
- [ ] 8.4 Verify no broken cross-references.
- [ ] 8.5 Create `specs/003-governance-enforcement/done.md`.
- [ ] 8.6 Update tasks.md frontmatter to completed.
