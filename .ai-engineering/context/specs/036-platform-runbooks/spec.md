---
id: "036"
slug: "platform-runbooks"
status: "in-progress"
created: "2026-03-04"
size: "XL"
tags: ["automation", "runbooks", "codex", "gemini", "github-templates", "installer"]
branch: "spec-036/platform-runbooks"
pipeline: "full"
decisions: []
---

# Spec 036 — Platform Adaptors, Automation Runbooks & GitHub Infrastructure

## Problem

The framework v3 has 34 skills + 7 agents as source of truth in `.ai-engineering/`. Each LLM platform has "adaptors" that reference that source. Currently:

1. **Missing Codex/Gemini adaptors** — `_PROVIDER_TREE_MAPS["codex"]` and `["gemini"]` are empty lists. Running `ai-eng install --provider codex` installs only `AGENTS.md` with zero skill/agent access.
2. **No automation runbooks** — recurring tasks (scans, triage, executor, reporting) have no documented, platform-agnostic prompts.
3. **No GitHub issue/PR templates** — contributors (human and AI) have no structured input forms.
4. **PR spec URLs are plain text** — not clickeable across GitHub/Azure DevOps.
5. **No issue definition standard** — work-item skill lacks structural contract for issue fields.

## Solution

9-phase implementation adding platform parity, automation runbooks, and GitHub infrastructure:

1. Create 41 Codex/Gemini adaptors in `.agents/skills/`.
2. Wire installer: tree maps, VCS templates, template mirrors.
3. Create GitHub issue/PR templates for this repo.
4. Make PR spec URLs clickeable and cross-platform.
5. Add issue definition standard to work-item skill.
6. Update manifest with ownership and issue standard.
7. Create 13 automation runbooks (4 layers: scanner, triage, executor, reporting).
8. Update AGENTS.md with runbooks and `.agents/` documentation.
9. Tests and verification.

## Scope

### In Scope

- 41 `.agents/skills/` adaptors (34 skills + 7 agents).
- 41 template mirrors in `src/ai_engineering/templates/project/.agents/skills/`.
- Installer changes: `_PROVIDER_TREE_MAPS`, `_VCS_TEMPLATE_TREES`, `copy_project_templates()`.
- 5 GitHub template files (3 issue forms + config + PR template).
- 5 installer template mirrors for GitHub templates.
- PR description spec URL as clickeable link.
- Issue definition standard in work-item skill.
- Manifest updates (ownership, issue standard).
- 13 automation runbooks.
- AGENTS.md updates.
- Unit tests for installer and PR description changes.

### Out of Scope

- Backfill of issues #79-86 (Phase 9 from original plan — requires live GitHub API).
- Actual execution of runbooks on any platform.
- New skills or agents (skill count stays at 34, agent count at 7).

## Acceptance Criteria

1. `ls .agents/skills/*/SKILL.md | wc -l` → 41.
2. `ls .ai-engineering/runbooks/*.md | wc -l` → 13.
3. `_PROVIDER_TREE_MAPS["codex"]` contains `(".agents", ".agents")`.
4. `_PROVIDER_TREE_MAPS["gemini"]` contains `(".agents", ".agents")`.
5. `_VCS_TEMPLATE_TREES["github"]` contains GitHub template entry.
6. `.github/ISSUE_TEMPLATE/` has 3 forms + config.
7. `.github/pull_request_template.md` exists.
8. PR description renders spec as clickeable URL.
9. work-item SKILL.md has `## Issue Definition Standard`.
10. manifest.yml has `.agents/**` in `external_framework_managed`.
11. AGENTS.md documents runbooks and `.agents/skills/`.
12. All tests pass: `uv run pytest`.
13. `ruff check` and `ruff format --check` pass.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | Use `.agents/skills/` path for Codex/Gemini | Matches Codex convention; Gemini shares same tree |
| D2 | Runbooks are Markdown, not YAML/JSON | Copy-paste friendly for any agentic platform |
| D3 | VCS templates are a separate concept from provider templates | GitHub infrastructure (issues/PRs) is VCS-specific, not LLM-specific |
| D4 | Skip issue backfill (Phase 9) | Requires live GitHub API, better done as a separate task |
