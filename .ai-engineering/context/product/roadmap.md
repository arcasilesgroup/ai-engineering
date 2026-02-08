# Product Roadmap

## Update Metadata

- Rationale: align phase boundaries with finalized MVP constraints.
- Expected gain: clearer sequencing and lower migration risk.
- Potential impact: roadmap milestones and validation scope become stricter.

## Phase 1 (MVP)

Scope is fixed by policy decisions:

- GitHub runtime integration first.
- Terminal + VS Code first.
- Cross-OS validation in MVP: Windows, macOS, Linux.
- Dogfooding in this repository from day one.
- Stack baseline in MVP: Python + Markdown/YAML/JSON/Bash with `uv`, `ruff`, `ty`, `pip-audit`.
- Mandatory system state files: install manifest, ownership map, sources lock, decision store, audit log.
- Remote skills default ON with cache, checksums, and signature metadata scaffolding.

Exit criteria:

- command contract is fully implemented (`/commit`, `/pr`, `/acho`).
- mandatory local enforcement is non-bypassable in governed flows.
- updater preserves team/project managed content.
- readiness checks validate `gh`, `az`, hooks, and stack tooling.

## Phase 2

- Azure DevOps runtime behavior on top of Phase 1 provider-agnostic schema.
- stronger signature verification enforcement modes.
- additional IDE and stack adapters.

## Phase 3

- governed parallel subagent orchestration at scale.
- maintenance agent maturity and policy packs.
- docs site integration and broader ecosystem work.

## Release Model

- SemVer with migration scripts for schema changes.
- channels: `stable` and `canary`.
- telemetry remains strict opt-in for OSS in all phases.

## Metrics

- governance compliance rate.
- local gate pass/fail trend and remediation time.
- context redundancy delta and compaction gain.
- command success rate for `/commit`, `/pr`, `/acho` workflows.
