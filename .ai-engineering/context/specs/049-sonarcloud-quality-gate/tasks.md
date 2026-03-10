---
spec: "049"
total: 12
completed: 11
last_session: "2026-03-10"
next_session: "3.2 — Create PR"
---

# Tasks — Fix SonarCloud Quality Gate + No-Suppression Rule

## Phase 0: Scaffold [S]
- [x] 0.1 Create spec.md, plan.md, tasks.md
- [x] 0.2 Activate spec in _active.md
- [x] 0.3 Create feature branch `fix/049-sonarcloud-quality-gate`

## Phase 1: No-Suppression Governance Rule [S]
- [x] 1.1 Add rule 9 to CLAUDE.md Absolute Prohibitions
- [x] 1.2 Add no-suppression rule to AGENTS.md behavioral rules
- [x] 1.3 Add no-suppression to `standards/framework/core.md` Non-Negotiables
- [x] 1.4 Sync template mirrors (CLAUDE.md, AGENTS.md, core.md)

## Phase 2: Fix SonarCloud Vulnerabilities [M]
- [x] 2.1 Fix S2083 in `spec_cmd.py:123` — path containment validation
- [x] 2.2 Fix S2083 in `commit_msg.py:54` — .git parent validation
- [x] 2.3 Fix S2083 in `changelog.py:75` — filename + containment validation
- [x] 2.4 Fix S2083 in `sonarlint.py:493` — suffix + containment validation
- [x] 2.5 Fix S6350 in `azure_devops.py:419` — argument type validation

## Phase 3: Validation [S]
- [x] 3.1 Run tests, lint, type check, content integrity
- [ ] 3.2 Create PR targeting main
