# ai-engineering

Governed AI-assisted software development framework for regulated industries.

## What Gets Installed

- `.claude/skills/` -- 30 AI skills (slash commands)
- `.claude/agents/` -- 8 specialized AI agents
- `.ai-engineering/` -- governance, contexts, state
- `CLAUDE.md` -- Claude Code instructions
- `AGENTS.md` -- multi-IDE instructions (Copilot, Codex, Gemini)

## Skills by Category

### Core Workflow

| Skill | Purpose |
|-------|---------|
| /ai-brainstorm | Design interrogation before implementation |
| /ai-plan | Implementation planning with task decomposition |
| /ai-dispatch | Execute plan with subagents |
| /ai-test | TDD enforcement (RED-GREEN-REFACTOR) |
| /ai-debug | Systematic 4-phase debugging |
| /ai-verify | Evidence-based verification |
| /ai-review | Parallel 8-agent code review |

### Delivery

| Skill | Purpose |
|-------|---------|
| /ai-commit | Governed commit (lint + secrets + push) |
| /ai-pr | Pull request with auto-generated summary |
| /ai-release | GO/NO-GO release gate |
| /ai-cleanup | Branch cleanup and repo hygiene |

### Enterprise

| Skill | Purpose |
|-------|---------|
| /ai-security | SAST, dependency audit, SBOM |
| /ai-governance | Compliance validation |
| /ai-pipeline | CI/CD generation |
| /ai-schema | Database engineering |
| /ai-solution-intent | Architecture document lifecycle |

### Teaching and Writing

| Skill | Purpose |
|-------|---------|
| /ai-explain | Technical explanations |
| /ai-guide | Project onboarding |
| /ai-write | Docs, changelogs, articles |

### SDLC

| Skill | Purpose |
|-------|---------|
| /ai-note | Technical discovery notes |
| /ai-standup | Standup notes from PR activity |
| /ai-sprint | Sprint planning and retros |
| /ai-postmortem | Incident postmortems (DERP) |
| /ai-support | Customer support investigation |
| /ai-resolve-conflicts | Git conflict resolution |

### Meta

| Skill | Purpose |
|-------|---------|
| /ai-create | Create new skills/agents (TDD) |
| /ai-learn | Continuous improvement from outcomes |
| /ai-prompt | Prompt optimization |
| /ai-onboard | Session bootstrap and enforcement |
| /ai-analyze-permissions | Permission pattern consolidation |

## Agents

| Agent | Role | Model |
|-------|------|-------|
| plan | Design interrogation | opus |
| build | Implementation | opus |
| verify | Quality scanning | opus |
| guard | Governance advisory | sonnet |
| review | Parallel code review | opus |
| explore | Codebase research | sonnet |
| guide | Teaching/onboarding | sonnet |
| simplify | Code simplification | sonnet |

## Directory Structure

```
.ai-engineering/
  manifest.yml          # Framework configuration (editable)
  README.md             # This file
  contexts/             # Language, framework, org, team conventions
    languages/
    frameworks/
    orgs/
    team/               # Your team's custom conventions
  specs/                # Architecture specs and decisions
    _active.md
    archive/
  state/                # Compliance state
    decision-store.json
    audit-log.ndjson
```

## Workflow

1. **Brainstorm** -- Design interrogation, spec approval
2. **Plan** -- Task decomposition, agent assignments
3. **Execute** -- Subagent per task, TDD, verification
4. **Review** -- 8 parallel agents, self-challenge
5. **Ship** -- Commit, PR, release gate
6. **Learn** -- Analyze outcomes, update lessons

## Configuration

Edit `manifest.yml` to customize:
- VCS provider (GitHub/Azure DevOps)
- IDE support (Claude Code, Copilot, Codex, Gemini)
- Quality gates (coverage, complexity thresholds)
- Documentation auto-update settings
- Stack contexts

## Using with Other IDEs

ai-engineering supports three IDE surfaces out of the box:

| Surface | IDE | Skills | Agents |
|---------|-----|--------|--------|
| `.claude/` | Claude Code | `skills/ai-*/SKILL.md` | `agents/ai-*.md` |
| `.github/` | GitHub Copilot | `skills/ai-*/SKILL.md` | `agents/*.agent.md` |
| `.agents/` | Codex / Gemini CLI | `skills/*/SKILL.md` | `agents/ai-*.md` |

For unsupported IDEs (Windsurf, Aider, Cursor, etc.):

1. Copy `AGENTS.md` into your IDE's instruction file (e.g., `.cursorrules`, `.windsurfrules`)
2. Point your IDE to `.agents/skills/` and `.agents/agents/` for skill and agent definitions
3. These use a generic markdown format compatible with any AI coding assistant

To generate a custom IDE surface, ask your AI assistant:
```
Read AGENTS.md and .agents/ directory structure, then create equivalent
files for [your IDE] following its native format conventions.
```

## CLI

```
ai-eng install     # Install framework
ai-eng update      # Update to latest
ai-eng doctor      # Diagnose issues
ai-eng validate    # Verify manifest
ai-eng sync        # Regenerate IDE mirrors
ai-eng gate        # Run quality gates
ai-eng observe     # Observability dashboards
```
