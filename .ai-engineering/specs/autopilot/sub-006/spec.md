---
id: sub-006
parent: spec-079
title: "README.md Overhaul"
status: planning
files: [".ai-engineering/README.md", "src/ai_engineering/templates/.ai-engineering/README.md"]
depends_on: ["sub-003", "sub-004", "sub-005"]
---

# Sub-Spec 006: README.md Overhaul

## Scope

Rewrite `.ai-engineering/README.md` as a post-install getting-started guide in English. Structure: Quick Start, Skills (38) grouped by workflow, Agents (9), Ownership boundaries, manifest.yml config, Contexts hierarchy (13 languages, 15 frameworks), Common workflows, Multi-IDE support, CLI reference, Troubleshooting. Update both template and dogfood copies. Reflects final state after all other sub-specs.

## Exploration

### Current State

**Dogfood README** (`.ai-engineering/README.md`, 158 lines): Title says "ai-engineering", subtitle "Governed AI-assisted software development framework for regulated industries." Contains 7 sections: What Gets Installed, Skills by Category (6 tables), Agents (1 table), Directory Structure (code block), Workflow (numbered list), Configuration (bullet list), Using with Other IDEs (table + instructions), CLI (code block). Stale counts: "30 AI skills" and "8 specialized AI agents". Missing: getting started workflow, manifest.yml field reference, ownership boundaries, contexts hierarchy detail, common workflows, troubleshooting.

**Template README** (`src/ai_engineering/templates/.ai-engineering/README.md`, 158 lines): Byte-identical to dogfood copy. Same stale counts, same structure, same content.

### Post-Dependencies Final State

After sub-001 through sub-005 complete, the framework state changes to:

**Skills**: 38 total (37 current + ai-project-identity from sub-003). New skill registered in manifest as `ai-project-identity: { type: meta, tags: [governance] }`.

**Agents**: 9 total (unchanged). Names: plan, build, verify, guard, review, explore, guide, simplify, autopilot.

**Contexts directory** (after sub-002, sub-003, sub-004, sub-005):
- `contexts/orgs/` -- DELETED by sub-002
- `contexts/product/` -- DELETED by sub-003 (replaced by project-identity.md)
- `contexts/project-identity.md` -- CREATED by sub-003 (root of contexts/)
- `contexts/languages/` -- 13 files after sub-004: bash, cpp, csharp, dart, go, java, javascript, kotlin, php, python, rust, sql, swift, typescript (ruby, elixir, universal DELETED; cpp CREATED)
- `contexts/frameworks/` -- 15 files (unchanged): android, api-design, aspnetcore, backend-patterns, bun, claude-api, deployment-patterns, django, flutter, ios, mcp-sdk, nextjs, nodejs, react, react-native
- `contexts/team/` -- 2 seed files after sub-005: README.md, lessons.md (cli.md, mcp-integrations.md DELETED from template)
- `specs/` -- CREATED by sub-005 with spec.md and plan.md placeholders

**Ownership boundaries** (from manifest.yml):
- FRAMEWORK: `.claude/skills/**`, `.claude/agents/**`, `.ai-engineering/**`, `.github/agents/**`, `.github/skills/**`, `.github/hooks/**`, `.github/copilot-instructions.md`, `.agents/**`
- TEAM: `.ai-engineering/contexts/team/**`
- SYSTEM: `.ai-engineering/state/**`
- After sub-003: `contexts/project-identity.md` added as TEAM_MANAGED/DENY

**CLI commands** (from `ai-eng --help`): install, update, doctor, validate, verify, version, release, guide, observe, sync, stack, ide, gate, skill, maintenance, provider, vcs, setup, signals, decision, spec, work-item, workflow. Most used for README: install, update, doctor, validate, sync, gate, observe.

**Quality gates** (from manifest.yml): coverage >= 80%, duplication <= 3%, cyclomatic <= 10, cognitive <= 15. Tooling: ruff, ty, pytest, gitleaks, pip-audit.

**Multi-IDE surfaces** (from CLAUDE.md):
- Claude Code: `.claude/skills/ai-*/SKILL.md`, `.claude/agents/ai-*.md`
- GitHub Copilot: `.github/skills/ai-*/SKILL.md`, `.github/agents/*.agent.md`
- Codex / Gemini: `.agents/skills/*/SKILL.md`, `.agents/agents/ai-*.md`

### Skills Grouping for README

The approved structure groups skills by workflow stage (not by manifest type). Mapping from current manifest registry:

**Design (3)**: brainstorm, plan, project-identity
**Build (4)**: dispatch, test, debug, schema
**Deliver (4)**: commit, pr, release, cleanup
**Verify (4)**: verify, review, security, governance
**Document (7)**: write, explain, guide, solution-intent, slides, media, video-editing
**Sprint (7)**: note, standup, sprint, sprint-review, postmortem, support, resolve-conflicts
**Meta (9)**: create, learn, prompt, onboard, analyze-permissions, instinct, autopilot, eval, pipeline

Wait -- re-reading the approved structure: "Design, Build, Deliver, Verify, Document, Sprint, Meta". Let me recount to ensure 38 total:
- Design: brainstorm, plan, project-identity = 3
- Build: dispatch, test, debug, schema = 4
- Deliver: commit, pr, release, cleanup = 4
- Verify: verify, review, security, governance = 4
- Document: write, explain, guide, solution-intent, slides, media, video-editing = 7
- Sprint: note, standup, sprint, sprint-review, postmortem, support, resolve-conflicts = 7
- Meta: create, learn, prompt, onboard, analyze-permissions, instinct, autopilot, eval, pipeline = 9

Total: 3 + 4 + 4 + 4 + 7 + 7 + 9 = 38. Correct.

### Content Inventory for Each Section

1. **Header**: Name from manifest (`ai-engineering`), version from `framework_version` in manifest (`0.4.0`), tagline from spec-079 decision.
2. **Quick Start**: 4-step flow: /ai-brainstorm, /ai-plan, /ai-dispatch, /ai-commit.
3. **Skills (38)**: Table with Skill, Purpose columns. 7 groups as above.
4. **Agents (9)**: Table with Agent, Role, "Activated by" columns. Data from CLAUDE.md Agent Selection table.
5. **Ownership**: Three blocks -- YOURS (contexts/team/, contexts/project-identity.md, manifest.yml user section), FRAMEWORK (skills, agents, hooks, IDE mirrors), AUTOMATIC (state/, audit-log, ownership-map).
6. **Configuration**: manifest.yml user-editable fields: providers.vcs, providers.stacks, ai_providers, work_items, quality, documentation, cicd.
7. **Contexts**: Hierarchy description. languages/ (13), frameworks/ (15), team/ (user-owned), project-identity.md (project essence).
8. **Common workflows**: New feature (brainstorm -> plan -> dispatch -> verify -> commit -> pr), Bug fix (debug -> dispatch -> commit), Security audit (security -> governance), Sprint review (sprint-review).
9. **Multi-IDE**: Table of 3 surfaces with paths, plus instructions for unsupported IDEs.
10. **CLI quick reference**: install, update, doctor, validate, sync, gate, observe.
11. **Troubleshooting**: Common issues: doctor failures, stale counts, missing contexts, hook failures, IDE sync.

### Differences: Template vs Dogfood

Both copies must be identical. The template is what `ai-eng install` copies to new projects. The dogfood is the live installation in this repository. After this sub-spec, both files must contain the same content reflecting the post-cleanup state.

### Risks

- **Count drift**: If sub-003 does not complete its skill count update to 38, the README will be inconsistent. Mitigation: The README is written for the FINAL state (all sub-specs complete). If counts are wrong elsewhere, that is a sub-003 defect, not a sub-006 defect.
- **Language list drift**: If sub-004 does not complete cpp creation or ruby/elixir/universal deletion, the 13-language count will be wrong. Same mitigation as above.
- **Template parity**: Both copies must be identical. Single source of truth for content, write to both files.
