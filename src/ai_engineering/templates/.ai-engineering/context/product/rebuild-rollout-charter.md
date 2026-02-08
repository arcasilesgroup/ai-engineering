# Rebuild Rollout Charter (v1)

## Purpose

Define the execution plan to rebuild ai-engineering from scratch using a content-first architecture, with strict governance, local enforcement, and ownership-safe lifecycle operations.

## Scope

In scope:

- canonical contract and templates under `.ai-engineering/`,
- minimal Python runtime (`install`, `update`, `doctor`, `add/remove stack|ide`),
- mandatory local hooks and quality/security checks,
- command contract (`/commit`, `/pr`, `/acho`),
- readiness validation and update safety,
- dogfooding and full E2E validation.

Out of scope (for this charter):

- deep Azure DevOps runtime operations,
- heavy runtime compilers,
- local SonarQube server integration,
- non-essential feature expansion before MVP hardening.

## Success Criteria

1. Canonical `.ai-engineering/` contract is complete, concise, and auditable.
2. Install reproduces framework content in target repos without ambiguity.
3. Update preserves team/project ownership boundaries.
4. Hooks and mandatory local gates are non-bypassable and deterministic.
5. Command behavior matches the agreed contract.
6. Cross-OS validation passes (Windows, macOS, Linux).
7. Dogfooding succeeds in the ai-engineering repo itself.

## Workstreams

### W1 - Contract and Template Baseline

- finalize framework contract,
- finalize adoption map,
- finalize canonical template set,
- ensure no duplicated policy text.

### W2 - Minimal Runtime and State

- implement/install state manifests,
- ownership-map enforcement,
- decision and audit stores,
- update migration contract.

### W3 - Enforcement and Readiness

- hooks install + integrity checks,
- mandatory local checks (`gitleaks`, `semgrep`, dep-vuln, stack checks),
- readiness checks for `gh`, `az`, hooks, and stack toolchain.

### W4 - Command Contract

- `/commit`, `/commit --only`,
- `/pr`, `/pr --only` continuation policy,
- `/acho`, `/acho pr`,
- policy and decision-store integration.

### W5 - Validation and Release

- full local quality suite,
- cross-OS matrix execution,
- dogfooding cycle,
- release readiness and PR/merge to main.

## Milestones

| Milestone               | Target Outcome                            | Exit Criteria                                         |
| ----------------------- | ----------------------------------------- | ----------------------------------------------------- |
| M0 Contract Freeze      | Content-first contract finalized          | Contract docs accepted and linked from context        |
| M1 Installable Baseline | Minimal runtime installs canonical layout | install/doctor pass in empty + existing repo fixtures |
| M2 Update Safety        | Ownership-safe updater is deterministic   | no overwrite regression tests pass                    |
| M3 Enforced Workflows   | hooks and command contract fully governed | mandatory gates block correctly; command tests pass   |
| M4 Dogfood and E2E      | framework validates itself                | full E2E matrix passes and release checklist complete |

## Validation Plan

### Functional Validation

- install in empty repo,
- install in existing repo with stack detection,
- add/remove stack and IDE operations,
- update dry-run and apply,
- decision-store reuse behavior.

### Enforcement Validation

- verify hook integrity,
- verify gate failure blocking,
- verify no bypass messaging,
- verify protected branch restrictions.

### Cross-OS Validation

- run test and hook flows on Windows/macOS/Linux,
- verify path and shell compatibility,
- verify tool installation and readiness diagnostics.

### Product Validation

- measure context size and duplication trend,
- verify references remain canonical,
- ensure docs are readable by humans and AI.

## Risks and Mitigations

| Risk                                        | Impact | Mitigation                                         |
| ------------------------------------------- | ------ | -------------------------------------------------- |
| Runtime complexity drifts upward            | high   | enforce minimal Python scope and review gate       |
| Standards duplication increases token cost  | medium | canonical references + periodic compaction reviews |
| Hook friction slows adoption                | medium | clear remediation output and deterministic checks  |
| Ownership bugs overwrite project/team files | high   | strict ownership-map tests and dry-run previews    |
| Cross-OS script variance                    | high   | matrix validation and shell-safe templates         |

## Governance Rules

- No direct commits to `main`/`master`.
- No bypass guidance for mandatory checks.
- Non-negotiable controls cannot be silently weakened.
- Risk acceptances must be explicit and recorded.
- Every contract change includes rationale, expected gain, potential impact.

## Delivery Cadence

- Weekly execution checkpoint in `context/delivery/implementation.md`.
- Weekly backlog sync in `context/backlog/tasks.md`.
- Maintenance report first, PR after explicit acceptance.

## Release Readiness Checklist

- [ ] contract and templates frozen for release,
- [ ] runtime commands validated end-to-end,
- [ ] update safety proven with regression tests,
- [ ] mandatory local gates verified,
- [ ] cross-OS matrix green,
- [ ] dogfooding cycle complete,
- [ ] release notes and migration notes prepared.
