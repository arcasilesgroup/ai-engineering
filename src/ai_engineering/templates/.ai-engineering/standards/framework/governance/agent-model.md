# Agent Model Standard

## Update Metadata

- Rationale: formalize the 10-agent architecture with dispatch protocol, guard integration, and self-improvement mechanism.
- Expected gain: clear agent boundaries, formal dispatch, proactive governance during development.
- Potential impact: all agents must comply with dispatch schema and context handoff contract.

## Agents (10)

| Agent | Tier | Scope | Purpose |
|-------|------|-------|---------|
| plan | Orchestration | read-write (specs) | Plan, discover, design, create specs. STOPS before execution. |
| execute | Orchestration | read-write (tasks) | Dispatch agents via formal schema, checkpoint, gate verification. |
| guard | Orchestration | read-only + decision-store | Proactive governance advisory during development. Shift-left. |
| build | Domain | read-write | ONLY code-write agent. 20+ stacks. Runs guard.advise post-edit. |
| verify | Domain | read-only + work-items | 7-mode assessment: security, quality, governance, performance, accessibility, architecture, gap. |
| ship | Domain | read-write | ALM lifecycle: commit, PR, release, changelog, triage. |
| observe | Domain | read-only | 5-mode dashboards + evolve (self-improvement analysis). |
| guide | Advisory | read-only | Developer growth: teach, tour, onboard, decision archaeology. |
| write | Advisory | read-write (docs) | Documentation: generate, simplify. Divio system + Google style. |
| operate | Advisory | read-write (issues) | SRE: runbook execution, incident response, operational health. Owns all runbooks. |

## Dispatch Protocol

When execute dispatches work, each task follows this schema:

```yaml
dispatch:
  phase: <phase-id>
  agent: <agent-name>
  tasks: [<task-ids>]
  scope:
    files: [<file patterns>]
    boundaries: [<exclusions>]
  gate:
    pre: [guard.gate]
    post: [verify.quality]
  on_failure: escalate | retry | skip_and_log
```

## Guard Integration

Guard operates at two integration points:
1. **Build post-edit**: after every file modification, build invokes guard.advise on changed files. Fail-open advisory.
2. **Execute pre-dispatch**: before dispatching any agent, execute invokes guard.gate to validate governance compliance.

## Context Handoff Contract

Every dispatched agent MUST produce:
- `## Findings` — what was discovered or created
- `## Dependencies Discovered` — new dependencies identified
- `## Risks Identified` — new risks found
- `## Recommendations` — suggestions for next actions

## Self-Improvement Loop

The observe agent's evolve skill analyzes audit-log, decision-store, and health-history to identify improvement patterns. Proposals are presented to the human for approval, then flow through the standard plan→execute→build→verify→ship workflow.

## Session Contract

1. Every session reads: `_active.md` → `spec.md` → `tasks.md` → `decision-store.json`
2. Spec-first: if no active spec and work is non-trivial, create spec first
3. One phase = one commit: `spec-NNN: Phase X.Y — description`
4. Checkpoint after every task: update tasks.md + `ai-eng checkpoint save`
5. Post-change: if `.ai-engineering/` modified, run integrity-check
