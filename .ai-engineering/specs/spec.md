---
spec: spec-101
title: First-Run Experience Hardening
status: approved
effort: large
refs:
  - Anonymous first-run feedback audit (2026-04-03)
  - spec-064
  - spec-071
  - spec-096
  - spec-098
  - spec-099
  - spec-100
---

# Spec 101 - First-Run Experience Hardening

## Summary
The current first-run experience has multiple trust-breaking seams: install can surprise users with privilege-sensitive tooling work, provider identity is not consistently visible, top-level docs disagree on the first step after install, `doctor --fix` overstates what it can repair, and framework-managed helper hooks can fail against a project-local Python runtime that is older than the framework runtime. This work hardens the first-run path so a new user can install the framework, validate health, start the first governed session, and reach the first commit or first workflow action without framework-originated ambiguity or runtime mismatch.

## Goals
- A GitHub-backed first install does not auto-install or request Azure DevOps tooling unless Azure DevOps is explicitly configured or detected for that project.
- Install output, provider commands, and generated onboarding artifacts all report active AI providers from one canonical source, and the reported provider set is consistent across those surfaces.
- The documented first-run path converges on one default sequence: `ai-eng install` -> `ai-eng doctor` -> `/ai-start` -> user-selected workflow.
- Framework-managed helper scripts used by IDE hooks and first-run telemetry resolve and use the framework runtime explicitly on macOS, Linux, and Windows instead of inheriting whichever project `python` or `python3` binary appears first on `PATH`.
- `doctor` output and related docs distinguish fixable findings from manual follow-up steps and never advertise commands that do not exist.
- A fresh install can complete `/ai-start`, `/ai-brainstorm`, and the first git commit without a framework-originated syntax failure caused by the runtime boundary between the framework and the target project.

## Non-Goals
- Officially supporting Python versions below 3.11 as the framework runtime.
- Redesigning the full install, update, or doctor architecture beyond the first-run path.
- Reworking unrelated CLI surfaces that do not participate in install, doctor, provider visibility, `/ai-start`, or first governed action flows.
- Preserving or storing raw private feedback files, screenshots, or document metadata inside repository artifacts.
- Introducing notebook, Jupyter, or `.ipynb` management behavior into the framework.

## Decisions

### D-101-01: The first-run journey will use one canonical narrative
The framework will present one default first-run sequence across install output, README, getting started material, and generated instruction files: validate with `ai-eng doctor`, then begin the interactive session with `/ai-start`, then choose the appropriate governed workflow.

**Rationale**: First-run UX fails when the user sees competing “next step” narratives. A single sequence reduces hesitation, keeps the session bootstrap explicit, and aligns install-time guidance with the instruction contracts already enforced in generated provider files.

### D-101-02: Framework-managed helper hooks will run inside the framework runtime boundary
Framework-owned helper scripts triggered by IDE hooks and first-run telemetry will execute with the framework runtime boundary rather than inheriting an arbitrary project-local `python` or `python3` binary.

**Rationale**: The confirmed first-commit failure comes from mixing a framework that requires Python 3.11+ with helper scripts launched through whatever interpreter the project machine exposes first. Isolating the framework runtime addresses the root cause without forcing the target project to adopt the same runtime as the framework.

### D-101-03: Provider truth will come from `ai_providers.enabled`
Install summaries, provider commands, diagnostics, and onboarding artifacts will treat `ai_providers.enabled` as the canonical source for active AI providers. IDE lists and mirror files remain deployment artifacts, not semantic provider state.

**Rationale**: Provider confusion happens when the framework reports IDE configuration or shared instruction files as if they were provider truth. Using a single source of truth removes ambiguity about which assistants are active and prevents provider identity from drifting across surfaces.

### D-101-04: Tool installation and readiness guidance will be explicitly provider-scoped
Privilege-sensitive VCS tooling and first-run readiness checks will be scoped to the detected or configured provider path. The GitHub path must not behave as if Azure DevOps is required, and the Azure DevOps path must state its elevated prerequisites explicitly.

**Rationale**: Surprise installation or prompting for Azure CLI during a GitHub-first setup is a trust failure, especially in locked-down enterprise environments. Provider-scoped readiness preserves momentum and makes elevated requirements legible when they are genuinely needed.

### D-101-05: `doctor` remediation guidance will become capability-based
`doctor`, related docs, and follow-up suggestions will only advertise remediations that actually exist and will distinguish automatic repair from manual intervention in human-readable output.

**Rationale**: Users stop trusting diagnostics when “fix” messaging is broader than the command surface or when interactive repair language hides manual steps. Capability-based messaging makes the command honest and reduces false expectations during first-run recovery.

### D-101-06: First-run fixes will treat feedback artifacts as sensitive inputs
The spec and subsequent implementation may summarize patterns from user feedback, but repository artifacts will not embed raw private documents, screenshots, personal metadata, or local machine identifiers.

**Rationale**: The value of the feedback is diagnostic, not archival. Persisting raw source artifacts would create avoidable privacy risk and is unnecessary to fix the underlying first-run problems.

## Risks
- Runtime isolation for framework-managed helpers may behave differently across shell wrappers, PowerShell, and IDE host environments. Mitigation: define one shared launcher contract and cover it with cross-platform integration tests.
- Tightening provider-scoped tool handling may surface missing-tool states that were previously masked by over-broad checks. Mitigation: make manual steps explicit and validate the GitHub and Azure DevOps paths separately.
- Unifying first-run guidance across README, getting started material, and generated instruction files may drift again if only one source is updated. Mitigation: update canonical sources and add mirror or docs parity checks for first-run wording.
- Switching more UX and diagnostics surfaces to `ai_providers.enabled` may expose legacy assumptions in provider or installer commands. Mitigation: add regression tests for mixed-provider, single-provider, and shared-file cases.

## References
- README first-run flow and install tree
- GETTING_STARTED first-run sequence and multi-IDE guidance
- `src/ai_engineering/installer/service.py`
- `src/ai_engineering/installer/tools.py`
- `src/ai_engineering/cli_commands/provider.py`
- `src/ai_engineering/cli_commands/core.py`
- `src/ai_engineering/doctor/phases/tools.py`
- `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/instinct-extract.py`
- `src/ai_engineering/templates/project/github_templates/hooks/hooks.json`
