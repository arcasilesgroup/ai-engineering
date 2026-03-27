# ai-engineering v0.4.0

This directory governs your AI workspace.

## Quick Start

```
/ai-brainstorm   -- design interrogation, spec approval
/ai-plan         -- task decomposition, agent assignments
/ai-dispatch     -- execute with subagents
/ai-commit       -- governed commit (lint + secrets + push)
```

## Skills (41)

Invoke as `/ai-<name>`. Grouped by workflow stage.

| | Skill | Purpose |
|-|-------|---------|
| **Design** | /ai-brainstorm | Design interrogation before implementation |
| | /ai-plan | Task decomposition and agent assignments |
| | /ai-project-identity | Define project essence and boundaries |
| **Build** | /ai-dispatch | Execute plan with subagents |
| | /ai-test | TDD enforcement (RED-GREEN-REFACTOR) |
| | /ai-debug | Systematic 4-phase debugging |
| | /ai-schema | Database schema design and migrations |
| **Deliver** | /ai-commit | Governed commit (lint + secrets + push) |
| | /ai-pr | Pull request with auto-generated summary |
| | /ai-release | GO/NO-GO release gate |
| | /ai-cleanup | Branch cleanup and repo hygiene |
| **Verify** | /ai-verify | Evidence-based quality scanning |
| | /ai-review | Parallel multi-agent code review |
| | /ai-security | SAST, dependency audit, SBOM |
| | /ai-governance | Compliance and policy validation |
| **Document** | /ai-write | Docs, changelogs, articles |
| | /ai-explain | Technical explanations |
| | /ai-guide | Project onboarding walkthroughs |
| | /ai-docs | Project documentation lifecycle (changelog, readme, solution-intent, external portal) |
| | /ai-slides | Presentation generation (HTML/CSS) |
| | /ai-media | Media asset generation |
| | /ai-video-editing | Video editing and post-production |
| **Sprint** | /ai-note | Technical discovery notes |
| | /ai-standup | Standup notes from PR activity |
| | /ai-sprint | Sprint planning and retrospectives |
| | /ai-sprint-review | Sprint review presentations |
| | /ai-postmortem | Incident postmortems (DERP format) |
| | /ai-support | Customer support investigation |
| | /ai-resolve-conflicts | Git conflict resolution |
| **Meta** | /ai-create | Create new skills and agents (TDD) |
| | /ai-learn | Continuous improvement from outcomes |
| | /ai-prompt | Prompt optimization and tuning |
| | /ai-onboard | Session bootstrap, bounded context refresh, and enforcement |
| | /ai-analyze-permissions | Permission pattern consolidation |
| | /ai-instinct | Project-local instinct review and consolidation |
| | /ai-autopilot | Multi-spec autonomous orchestration |
| | /ai-eval | Skill and agent evaluation |
| | /ai-pipeline | CI/CD pipeline generation |
| **Board** | /ai-board-discover | Auto-discover board configuration |
| | /ai-board-sync | Work item lifecycle state updates |

## Agents (9)

| Agent | Role | Activated by |
|-------|------|-------------|
| plan | Design interrogation | /ai-brainstorm, /ai-plan |
| build | Implementation | /ai-dispatch |
| verify | Quality scanning | /ai-verify |
| guard | Governance advisory | /ai-governance |
| review | Parallel code review | /ai-review |
| explore | Codebase research | subagent dispatch |
| guide | Teaching and onboarding | /ai-guide |
| simplify | Code simplification | direct dispatch |
| autopilot | Multi-spec orchestration | /ai-autopilot |

## Your project, your control

**YOURS** -- team-managed, never overwritten by updates:
- `contexts/team/` -- team conventions, lessons learned
- `contexts/project-identity.md` -- project essence and boundaries
- `manifest.yml` user configuration section (above the line)

**FRAMEWORK** -- managed by ai-engineering, updated automatically:
- `.claude/skills/` and `.claude/agents/`
- `.github/skills/`, `.github/agents/`, `.github/hooks/`
- `.agents/skills/` and `.agents/agents/`
- `manifest.yml` framework section (below the line)

**AUTOMATIC** -- system-generated, do not edit:
- `state/decision-store.json` -- settled architectural decisions
- `state/framework-events.ndjson` -- canonical framework events
- `state/framework-capabilities.json` -- registered skills, agents, contexts, hooks
- `state/instinct-observations.ndjson` -- sanitized recent tool observations retained for 30 days
- `instincts/instincts.yml` -- canonical project-local instinct store
- `instincts/context.md` -- bounded instinct context loaded at session start
- `instincts/meta.json` -- instinct consolidation checkpoints and refresh metadata
- `state/ownership-map.json` -- materialized ownership rules

## Configuration

Edit `manifest.yml` to customize your installation.

| Field | Description | Example |
|-------|-------------|---------|
| `providers.vcs` | Version control provider | `github`, `azure_devops` |
| `providers.stacks` | Language list for context loading | `[python, typescript]` |
| `ai_providers.enabled` | Active IDE integrations | `[claude_code, github_copilot, codex]` |
| `work_items.provider` | Issue tracker | `github`, `azure_devops` |
| `quality.coverage` | Minimum test coverage % | `80` |
| `quality.duplication` | Maximum code duplication % | `3` |
| `quality.cyclomatic` | Max cyclomatic complexity | `10` |
| `quality.cognitive` | Max cognitive complexity | `15` |
| `documentation.auto_update.*` | Auto-update readme, changelog, solution_intent | `true` / `false` |
| `cicd.standards_url` | Team CI/CD documentation URL | `https://...` |

## Contexts

Contexts are loaded by AI agents before writing or reviewing code. Language and framework contexts match your stack. Team contexts capture your conventions.

```
contexts/
  languages/       14 languages
  frameworks/      15 frameworks
  team/            your team conventions
  project-identity.md
```

- **Languages** (14): bash, cpp, csharp, dart, go, java, javascript, kotlin, php, python, rust, sql, swift, typescript
- **Frameworks** (15): android, api-design, aspnetcore, backend-patterns, bun, claude-api, deployment-patterns, django, flutter, ios, mcp-sdk, nextjs, nodejs, react, react-native
- **Team** (2 seed files): README.md, lessons.md
- **Project identity**: what the project is, services, boundaries

## Common workflows

**New feature:**
`/ai-brainstorm` -> `/ai-plan` -> `/ai-dispatch` -> `/ai-verify` -> `/ai-commit` -> `/ai-pr`

**Bug fix:**
`/ai-debug` -> `/ai-dispatch` -> `/ai-commit`

**Security audit:**
`/ai-security` -> `/ai-governance`

**Sprint review:**
`/ai-sprint-review`

## Multi-IDE

| IDE | Skills | Agents |
|-----|--------|--------|
| Claude Code | `.claude/skills/ai-*/SKILL.md` | `.claude/agents/ai-*.md` |
| GitHub Copilot | `.github/skills/ai-*/SKILL.md` | `.github/agents/*.agent.md` |
| Codex / Gemini | `.agents/skills/*/SKILL.md` | `.agents/agents/ai-*.md` |

For unsupported IDEs (Cursor, Windsurf, Aider): copy `AGENTS.md` into your IDE's instruction file.

## CLI quick reference

```
ai-eng install     -- install framework into current project
ai-eng update      -- update framework-managed files
ai-eng doctor      -- diagnose and fix framework health
ai-eng validate    -- verify content integrity
ai-eng sync        -- regenerate IDE mirrors
ai-eng gate        -- run quality gate checks
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Doctor reports missing files | `ai-eng doctor --fix` |
| Skill counts don't match | `ai-eng validate` then fix the source |
| IDE mirrors out of sync | `ai-eng sync` |
| Pre-commit hook blocks commit | Check `gitleaks protect --staged --verbose` output |
| Contexts not loaded by agent | Verify stack in `manifest.yml` matches your project |
