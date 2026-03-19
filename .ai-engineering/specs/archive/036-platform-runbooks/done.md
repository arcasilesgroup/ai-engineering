---
spec: "036"
slug: "platform-runbooks"
completed: "2026-03-04"
---

# Done — Platform Adaptors, Automation Runbooks & GitHub Infrastructure

## Summary

Implemented cross-platform AI adaptor system, 13 automation runbooks, GitHub issue/PR templates, VCS-aware installer wiring, clickeable spec URLs in PRs, issue definition standard, and rich PR description format (What/Why/How/Checklist/Stats).

Delivered:

1. **41 Codex/Gemini adaptors** — `.agents/skills/*/SKILL.md` pointing to canonical definitions. 7 agent adaptors use `-agent` suffix.
2. **Installer wiring** — `copy_project_templates()` accepts `vcs_provider`, `_VCS_TEMPLATE_TREES` maps VCS platforms to templates, `_PROVIDER_TREE_MAPS` populated for codex/gemini.
3. **GitHub templates** — 3 issue forms (bug, feature, task) + config + PR template, with installer mirrors.
4. **PR description builder** — `_get_repo_url()` detects GitHub/Azure DevOps from SSH/HTTPS remotes. `_build_spec_url()` constructs archive-aware web links. `build_pr_description()` generates What/Why/How/Checklist/Stats format from spec context and git data.
5. **Issue definition standard** — `work-item` SKILL.md extended with structured issue fields contract.
6. **Manifest updates** — `.agents/**` in `external_framework_managed`, issue standard in governance surface.
7. **13 automation runbooks** — Scanner (6), Triage (2), Executor (2), Reporting (3). Platform-agnostic prompts for Codex, Devin, cron, GitHub Actions.
8. **AGENTS.md** — Platform Adaptors and Runbooks sections documented.
9. **Spec lifecycle closure** — `done.md` files for specs 035 and 036, archive-aware spec URLs.

## Verification

- 1044 unit tests pass (43 PR description tests, 17 new)
- `ruff check` and `ruff format` clean
- `ty check` clean
- `gitleaks` — no leaks
- CHANGELOG.md updated

## New Files

| File | Purpose |
|------|---------|
| `.agents/skills/*/SKILL.md` (×41) | Codex/Gemini adaptors |
| `.ai-engineering/runbooks/*.md` (×13) | Automation runbooks |
| `.github/ISSUE_TEMPLATE/*.yml` (×3) | Issue forms |
| `.github/ISSUE_TEMPLATE/config.yml` | Issue config |
| `.github/pull_request_template.md` | PR template |
| `src/.../templates/project/.agents/skills/*/SKILL.md` (×41) | Installer mirrors |
| `src/.../templates/project/.github/**` (×5) | Installer GitHub mirrors |

## Modified Files

| File | Change |
|------|--------|
| `src/.../vcs/pr_description.py` | What/Why/How/Checklist/Stats format, archive-aware spec URL, spec context reader |
| `src/.../installer/templates.py` | `_VCS_TEMPLATE_TREES`, `copy_project_templates(vcs_provider=)` |
| `src/.../templates/.../skills/work-item/SKILL.md` | Issue definition standard |
| `src/.../templates/.../manifest.yml` | `.agents/**` ownership |
| `AGENTS.md` | Platform adaptors + runbooks documentation |
| `tests/unit/test_pr_description.py` | 43 tests (was 26) |

## Deferred

- **Issue backfill** (#79-86) — requires live GitHub API, excluded from spec scope.
- **Runbook execution** — runbooks are documentation; actual scheduled execution is a separate concern.
