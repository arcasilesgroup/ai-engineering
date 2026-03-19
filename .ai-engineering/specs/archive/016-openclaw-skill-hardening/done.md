---
id: "016"
slug: "openclaw-skill-hardening"
status: "done"
created: "2026-02-23"
completed: "2026-02-23"
---

# Done — Spec-016: OpenClaw-Inspired Skill & Standards Hardening

## Summary

Six enhancements inspired by OpenClaw patterns were applied to ai-engineering governance content: YAML frontmatter on all skills, anti-pattern sections, test tier classification, two new skills (doctor, multi-agent), install gating metadata, and governance updates with full mirror sync.

## Deliverables

| Deliverable | Files | Status |
|-------------|-------|--------|
| YAML frontmatter on all 43 existing skills | 43 skill files | Done |
| Anti-pattern sections on 6 confusable skills | security, architecture, code-review, refactor, audit-code, integrity-check | Done |
| Test tier classification | python.md, quality/core.md, test-strategy.md | Done |
| Doctor skill + slash command | skills/utils/doctor.md, .claude/commands/utils/doctor.md | Done |
| Multi-agent skill + slash command | skills/dev/multi-agent.md, .claude/commands/dev/multi-agent.md | Done |
| Install gating (`requires.bins`) | 7 skills with external binary deps | Done |
| Governance updates | integrity-check.md (Category 7), create-skill.md (template) | Done |
| Cross-references and counters | product-contract.md, 7 instruction files (43→45 skills) | Done |
| Mirror sync | 61 files synced (skills, agents, standards, commands) | Done |
| Integrity-check description | 6-category → 7-category in all instruction files | Done |
| Integrity-check procedure | Step 11 subsection names updated to current taxonomy | Done |

## Acceptance Criteria Verification

1. All 45 skills have valid YAML frontmatter (name, version, category). PASS
2. 7 skills with external binary deps declare `requires.bins`. PASS
3. 6 skills have "When NOT to Use" anti-pattern sections. PASS
4. Python stack contract defines 4 test tiers with gate mapping. PASS
5. `utils:doctor` created, registered, with slash command. PASS
6. `dev:multi-agent` created, registered, with slash command. PASS
7. `integrity-check` validates frontmatter (Category 7). PASS
8. `create-skill` template includes frontmatter block. PASS
9. Instruction file counters updated to 45 skills. PASS
10. Integrity-check passes with 7/7 categories. PASS

## Decisions Log

| ID | Decision | Rationale |
|----|----------|-----------|
| S016-001 | Supersede spec-015 as active spec | Spec-015 work is stable; this spec addresses different scope |

## Metrics

- **Total tasks**: 35
- **Commits**: 11 (scaffold, frontmatter, anti-patterns, test tiers, doctor, multi-agent, install gating, governance, cross-refs, tasks update, integrity remediation)
- **Files changed**: 100+ (45 skills, 9 agents, 3 standards, 2 new skills, 2 new commands, 7 instruction files, product-contract, manifest)
- **Duration**: 1 session
