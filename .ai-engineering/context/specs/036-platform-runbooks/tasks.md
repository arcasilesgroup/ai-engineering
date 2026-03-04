---
spec: "036"
total: 28
completed: 0
last_session: "2026-03-04"
next_session: "Phase 1 — Codex/Gemini Adaptors"
---

# Tasks — Platform Adaptors, Automation Runbooks & GitHub Infrastructure

## Phase 0: Scaffold [S]
- [ ] 0.1 Create spec.md, plan.md, tasks.md
- [ ] 0.2 Update _active.md
- [ ] 0.3 Commit scaffold

## Phase 1: Codex/Gemini Adaptors [L]
- [ ] 1.1 Create 34 skill adaptors in `.agents/skills/<name>/SKILL.md`
- [ ] 1.2 Create 7 agent adaptors in `.agents/skills/<name>/SKILL.md`
- [ ] 1.3 Create 34 skill template mirrors in `src/ai_engineering/templates/project/.agents/skills/<name>/SKILL.md`
- [ ] 1.4 Create 7 agent template mirrors

## Phase 2: Installer + GitHub Templates [M]
- [ ] 2.1 Update `_PROVIDER_TREE_MAPS` for codex and gemini
- [ ] 2.2 Add `_VCS_TEMPLATE_TREES` concept to templates.py
- [ ] 2.3 Update `copy_project_templates()` to accept vcs_provider
- [ ] 2.4 Create 5 installer GitHub template files
- [ ] 2.5 Create 5 GitHub templates for this repo

## Phase 3: PR Description + Work-Item + Manifest [M]
- [ ] 3.1 Add `_get_repo_url()` to pr_description.py
- [ ] 3.2 Update `build_pr_description()` to render clickeable spec URL
- [ ] 3.3 Add Issue Definition Standard to work-item SKILL.md
- [ ] 3.4 Update manifest.yml (ownership, issue_standard)

## Phase 4: Runbooks + AGENTS.md [L]
- [ ] 4.1 Create 6 scanner runbooks
- [ ] 4.2 Create 2 triage runbooks
- [ ] 4.3 Create 2 executor runbooks
- [ ] 4.4 Create 3 reporting runbooks
- [ ] 4.5 Update AGENTS.md with runbooks + .agents/ section
- [ ] 4.6 Update AGENTS.md template mirror

## Phase 5: Tests + Verification [M]
- [ ] 5.1 Write tests for installer VCS template changes
- [ ] 5.2 Write tests for PR description spec URL
- [ ] 5.3 Run full test suite
- [ ] 5.4 Run ruff + ty + gitleaks
- [ ] 5.5 Update CHANGELOG.md
