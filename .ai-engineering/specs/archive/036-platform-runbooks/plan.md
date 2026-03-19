---
spec: "036"
approach: "serial-phases"
---

# Plan — Platform Adaptors, Automation Runbooks & GitHub Infrastructure

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `.agents/skills/*/SKILL.md` (41) | Codex/Gemini adaptors for 34 skills + 7 agents |
| `src/ai_engineering/templates/project/.agents/skills/*/SKILL.md` (41) | Installer mirror copies |
| `src/ai_engineering/templates/project/github_templates/ISSUE_TEMPLATE/bug.yml` | Bug report issue form |
| `src/ai_engineering/templates/project/github_templates/ISSUE_TEMPLATE/feature.yml` | Feature request issue form |
| `src/ai_engineering/templates/project/github_templates/ISSUE_TEMPLATE/task.yml` | Task issue form |
| `src/ai_engineering/templates/project/github_templates/ISSUE_TEMPLATE/config.yml` | Issue template config |
| `src/ai_engineering/templates/project/github_templates/pull_request_template.md` | PR template |
| `.github/ISSUE_TEMPLATE/bug.yml` | Bug report form for this repo |
| `.github/ISSUE_TEMPLATE/feature.yml` | Feature request form for this repo |
| `.github/ISSUE_TEMPLATE/task.yml` | Task form for this repo |
| `.github/ISSUE_TEMPLATE/config.yml` | Issue template config for this repo |
| `.github/pull_request_template.md` | PR template for this repo |
| `.ai-engineering/runbooks/*.md` (13) | Automation runbooks |

### Modified Files

| File | Change |
|------|--------|
| `src/ai_engineering/installer/templates.py` | Add tree maps for codex/gemini + VCS templates |
| `src/ai_engineering/vcs/pr_description.py` | Spec URL as clickeable link |
| `.ai-engineering/skills/work-item/SKILL.md` | Issue Definition Standard section |
| `.ai-engineering/manifest.yml` | Ownership + issue_standard |
| `AGENTS.md` | Runbooks + .agents/ documentation |
| `src/ai_engineering/templates/project/AGENTS.md` | Mirror update |

### Mirror Copies

All `.agents/skills/` files are mirrored 1:1 between repo root and installer templates.

## Session Map

### Phase 1: Codex/Gemini Adaptors [L]
- Create 41 `.agents/skills/` adaptors.
- Create 41 template mirrors.
- Estimated: 82 files.

### Phase 2: Installer + GitHub Templates [M]
- Update `templates.py` with tree maps and VCS template concept.
- Create 5 installer GitHub template files.
- Create 5 GitHub templates for this repo.
- Estimated: 10 files + 1 modification.

### Phase 3: PR Description + Work-Item + Manifest [M]
- Update `pr_description.py` for clickeable spec URLs.
- Add Issue Definition Standard to work-item skill.
- Update manifest.yml.
- Estimated: 3 modifications.

### Phase 4: Runbooks + AGENTS.md [L]
- Create 13 runbooks.
- Update AGENTS.md.
- Estimated: 13 files + 2 modifications.

### Phase 5: Tests + Verification [M]
- Write tests for installer changes and PR description changes.
- Run full test suite.
- Run ruff, ty, gitleaks.

## Patterns

- Adaptors are single-purpose pointer files — never duplicate content.
- Runbooks follow a consistent frontmatter schema (name, schedule, environment, layer, requires).
- GitHub issue templates use YAML form syntax.
- All changes maintain backward compatibility.
