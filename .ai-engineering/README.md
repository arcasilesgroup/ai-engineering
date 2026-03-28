# `.ai-engineering/`

This directory is the local governance root for an ai-engineering workspace. It is the project-facing part of the framework: specs, contexts, runbooks, hooks, state, and long-lived AI memory all live here.

If you only remember one rule, remember this:

- framework content is updated through `ai-eng update`
- provider mirrors are regenerated through `ai-eng sync`
- team and project memory stay in `.ai-engineering/`

## Installed shape

Some directories are seeded at install time. Others appear only when a workflow or skill needs them.

```text
.ai-engineering/
├── contexts/
├── runbooks/
├── scripts/
├── specs/
├── state/
├── instincts/      # created and refreshed by instinct/onboard flows
├── reviews/        # review artifacts when review workflows persist output
├── schemas/        # schema artifacts and generated database work
├── notes/          # lazy, created by /ai-note
├── learnings/      # lazy, created by /ai-learn
└── ...
```

## Directory guide

| Path | Lifecycle | Purpose |
|------|-----------|---------|
| `contexts/` | seeded | Shared framework contexts, language/framework guidance, and team-local conventions |
| `runbooks/` | seeded | Self-contained Markdown automation contracts |
| `scripts/` | seeded | Hook and helper scripts installed by the framework |
| `specs/` | seeded | Active `spec.md`, `plan.md`, and child-spec workspaces such as `specs/autopilot/` |
| `state/` | seeded | Decisions, ownership, framework events, capability catalog, install metadata |
| `instincts/` | generated | Project-local instinct store and bounded context regenerated over time |
| `reviews/` | generated | Saved review reports or review-side artifacts |
| `schemas/` | generated | Schema planning or generated migration artifacts |
| `notes/` | lazy | Notes written by `/ai-note`; not created until needed |
| `learnings/` | lazy | Learning records written by `/ai-learn`; not created until needed |

## Ownership model

### Framework-managed

These paths are refreshed by `ai-eng update` and mirrored by `ai-eng sync`:

- `contexts/languages/**`
- `contexts/frameworks/**`
- shared root contexts such as `contexts/cli-ux.md` and `contexts/mcp-integrations.md`
- `runbooks/**`
- `scripts/**`
- framework parts of `state/**`

### Team-managed

These paths belong to the project or team and are not overwritten by framework updates:

- `contexts/team/**`
- `contexts/project-identity.md`
- active product work inside `specs/**`

### System-generated

These paths are written by the framework itself:

- `state/decision-store.json`
- `state/framework-events.ndjson`
- `state/framework-capabilities.json`
- `state/ownership-map.json`
- `instincts/**`
- generated review or schema artifacts

## Context layout

`contexts/` now has two different kinds of guidance:

1. Shared framework contexts at the root.
   - `cli-ux.md`
   - `mcp-integrations.md`
   - `project-identity.md` when the project defines one
2. Structured context families.
   - `languages/`
   - `frameworks/`
   - `team/`

`contexts/team/` is now intentionally narrow. It is for local conventions, lessons, and project-specific norms. Reusable framework guidance that should benefit all consumers belongs at the root of `contexts/`, not under `contexts/team/`.

## Runbooks

`runbooks/*.md` are 12 self-contained portable runbooks. Each is a single Markdown file combining a YAML frontmatter contract, full procedure, and host notes. There are no separate adapter files.

### Contract schema

Every runbook frontmatter declares these fields:

| Field | Purpose |
|-------|---------|
| `runbook` | Identifier (e.g. `triage`, `code-quality`) |
| `version` | Semver of the contract |
| `purpose` | One-line description |
| `type` | `intake` or `operational` |
| `cadence` | `daily` or `weekly` |
| `hosts` | Target platforms |
| `provider_scope` | Work-item provider (GitHub Issues, Azure Boards) |
| `feature_policy` | Rules for feature-level items |
| `hierarchy_policy` | Parent/child work-item rules |
| `scan_targets` | Files, directories, or APIs the runbook reads |
| `tool_dependencies` | CLI tools or APIs required at runtime |
| `thresholds` | Numeric limits that trigger findings |
| `outputs` | Artifacts produced (labels, comments, issues) |
| `handoff` | What happens after the runbook completes |
| `guardrails` | Hard constraints the runbook must not violate |

### Design principles

- **All HITL**: runbooks prepare work items in the provider. They never touch code and never create PRs.
- **dry_run_default: true**: hosts must explicitly configure `--apply` to make changes.
- **Portable**: the same runbook runs on Codex App Automation, Claude scheduled tasks, GitHub Agents, and Azure Foundry.
- **No adapter layer**: the old thin-host-adapter pattern is eliminated. Each runbook is fully self-contained.

### Catalog

| Runbook | Type | Cadence | Purpose |
|---------|------|---------|---------|
| `triage` | intake | daily | Scan backlog, classify, prioritize |
| `refine` | intake | daily | Gather context, draft acceptance criteria, mark ready |
| `feature-scanner` | operational | daily | Spec-vs-code gaps |
| `stale-issues` | operational | daily | Label/close stale issues |
| `dependency-health` | operational | weekly | CVEs, outdated deps, licenses |
| `code-quality` | operational | weekly | Complexity, duplication, tech debt |
| `security-scan` | operational | weekly | Secrets, SAST, compliance |
| `docs-freshness` | operational | weekly | Stale docs, coverage gaps |
| `performance` | operational | weekly | Test/build regressions |
| `governance-drift` | operational | weekly | Framework alignment |
| `architecture-drift` | operational | weekly | Solution-intent deviations |
| `wiring-scanner` | operational | weekly | Disconnected code |

## Specs and autopilot

`specs/` always contains the active local working set:

- `spec.md`
- `plan.md`

When `/ai-autopilot` decomposes a large initiative, it also creates:

- `specs/autopilot/manifest.md`
- `specs/autopilot/sub-*/spec.md`
- `specs/autopilot/sub-*/plan.md`

That sub-tree is still project memory. It is not regenerated by `ai-eng sync`.

## Reviews, notes, learnings, instincts

These folders do not all exist from day one.

- `reviews/` appears when review workflows persist review artifacts
- `notes/` appears on first `/ai-note`
- `learnings/` appears on first `/ai-learn`
- `instincts/` is maintained by instinct consolidation and onboarding flows

That is expected. A project that only uses a subset of skills should not be forced to carry every possible directory up front.

## Review and verify surfaces

The durable contracts for `review` and `verify` live outside this folder in the provider mirrors, but they operate against the state stored here.

- `/ai-review`
  - default `normal` profile covers every specialist through 3 macro-agents
  - `--full` runs one agent per specialist
  - findings are still reported by original specialist
  - `finding-validator` is part of the review flow
- `/ai-verify`
  - default `normal` profile covers every specialist through 2 macro-agents
  - `--full` runs one agent per specialist
  - output stays attributed by specialist
  - no separate validator stage

## Mirrors outside this folder

The framework also writes provider surfaces next to `.ai-engineering/`:

| Path | Purpose |
|------|---------|
| `../.claude/skills/` and `../.claude/agents/` | Claude Code skills and agents |
| `../.agents/skills/` and `../.agents/agents/` | Codex/Gemini skills and agents |
| `../.github/skills/` and `../.github/agents/` | GitHub Copilot skills and agents |
| `../AGENTS.md` and `../CLAUDE.md` | Shared instruction files |

Use `ai-eng sync` after framework changes to regenerate those mirrors.

## Day-to-day commands

```text
/ai-brainstorm   define or refine the spec
/ai-plan         break the approved spec into execution work
/ai-dispatch     execute a single approved plan
/ai-autopilot    execute a multi-spec DAG
/ai-review       run narrative multi-agent review
/ai-verify       prove quality/security/completeness with evidence
```

Framework maintenance stays in the CLI:

```bash
ai-eng doctor
ai-eng update
ai-eng sync
ai-eng validate
```
