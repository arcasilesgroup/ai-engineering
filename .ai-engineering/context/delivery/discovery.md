# Discovery

## Update Metadata

- Rationale: capture finalized requirements and assumptions for execution.
- Expected gain: reduce decision churn during implementation.
- Potential impact: unresolved legacy options are removed from MVP scope.

## Problem Statement

Teams need enforceable AI governance that does not depend on cloud-only controls or manual discipline.

## Requirements (MVP)

- single source of truth at `.ai-engineering/`.
- strict ownership boundaries for framework/team/project/system content.
- mandatory local checks: `gitleaks`, `semgrep`, dependency vulnerability checks, stack checks.
- command contract for `/commit`, `/pr`, `/acho`.
- cross-OS support from day one: Windows, macOS, Linux.
- provider focus in MVP: GitHub runtime with Azure DevOps-ready schema.

## Constraints

- primary implementation language: Python.
- baseline toolchain: `uv`, `ruff`, `ty`.
- supporting formats: Markdown, YAML, JSON, Bash.
- telemetry is strict opt-in.

## Key Decisions Locked

- remote skills default ON with local cache and lock file.
- integrity includes checksums plus signature metadata scaffolding in MVP.
- direct commits to `main`/`master` are prohibited.
- `/pr --only` is warning-based when branch is not pushed and does not hard-fail.
- risk acceptance is explicit, audited, machine-readable, and reused until expired or materially changed.

## Main Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Hook bypass attempts | High | non-bypassable hooks + integrity checks + audited failures |
| Remote source compromise | High | allowlist + lock + checksum + signature metadata scaffold |
| Cross-OS behavior drift | High | Windows/macOS/Linux E2E matrix in MVP |
| Context bloat | Medium | compaction policy + maintenance agent weekly reports |

## Assumptions

- `gh` and `az` can be installed where framework is installed.
- authentication checks may be interactive on developer machines.
- branch protection can be discovered or configured locally.
