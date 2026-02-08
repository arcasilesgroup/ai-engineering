# Target Architecture

## Update Metadata

- Rationale: replace legacy architecture with current governance contract.
- Expected gain: deterministic module boundaries and safer updates.
- Potential impact: implementation tasks and validators must follow this model.

## System Boundary

- Framework product: CLI, policy engine, updater, orchestrator, templates, migrations.
- Installed instance: `.ai-engineering/` inside each repository.

## Modules

| Module | Responsibility |
|---|---|
| `ae-cli` | command entrypoints, UX, diagnostics |
| `ae-detector` | stack/IDE/OS/provider detection |
| `ae-policy-engine` | allowed/guardrailed/restricted decisions |
| `ae-hooks` | install and verify non-bypassable hooks |
| `ae-standards` | layered standards resolution |
| `ae-skills` | remote source trust, cache, lock, fallback |
| `ae-orchestrator` | bounded subagent/task delegation |
| `ae-updater` | framework/system updates with ownership safety |
| `ae-state` | install, ownership, sources, decisions, audit files |

## Ownership and Layering

Authoritative ownership:

- framework-managed: `standards/framework/**`.
- team-managed: `standards/team/**`.
- project-managed: `context/**`.
- system-managed: `state/*.json`, `state/*.ndjson`.

Standards precedence:

1. `standards/framework/core.md`
2. `standards/framework/stacks/<stack>.md`
3. `standards/team/core.md`
4. `standards/team/stacks/<stack>.md`

## Command Contract

| Command | Behavior |
|---|---|
| `/commit` | stage + commit + push current branch |
| `/commit --only` | stage + commit |
| `/pr` | stage + commit + push + create PR |
| `/pr --only` | create PR only; warn/propose auto-push if branch not pushed; continue on engineer-selected mode if declined |
| `/acho` | stage + commit + push current branch |
| `/acho pr` | stage + commit + push + create PR |

Hard blocks:

- direct commit to protected branches.
- direct commit to `main`/`master`.
- mandatory check failures.

## Enforcement Architecture

- Hook set: `pre-commit`, `commit-msg`, `pre-push`.
- Mandatory checks include `gitleaks`, `semgrep`, dependency vulnerability checks, stack checks.
- Commands must fail closed when hooks are missing/tampered.

## Remote Skills Model

- default remote ON with local cache.
- allowlist sources only.
- lock and integrity in `state/sources.lock.json`.
- checksums required now; signature metadata scaffold required now.
- no unsafe remote execution.

## Decision and Audit Model

- risk decisions persisted in `state/decision-store.json`.
- operational events in append-only `state/audit-log.ndjson`.
- re-prompt only on expiration or material context change.

## Installer and Updater

- installer creates missing paths safely and validates readiness for `gh`, `az`, hooks, and stack tooling.
- updater modifies only framework-managed and system-managed paths.
- team/project files are preserved.

## Context Efficiency

- strict compaction and deduplication policy.
- no fixed cap by category; optimize by usefulness and redundancy.
- maintenance agent produces weekly local reports and creates PRs only after approval.
