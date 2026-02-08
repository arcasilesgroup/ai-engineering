# Features

## Update Metadata

- Rationale: map feature scope to finalized policy and command decisions.
- Expected gain: less implementation ambiguity.
- Potential impact: acceptance criteria become enforcement-first.

## F-1 Installer/Updater Ownership Safety (P0)

- create missing `.ai-engineering` structure.
- update only framework/system-managed files.
- preserve team/project files.

## F-2 Tooling Readiness Validation (P0)

- verify installed/configured/auth status for `gh`, `az`, hooks, and stack tools.
- machine-readable doctor output.

## F-3 Command Flow Engine (P0)

- implement `/commit`, `/pr`, `/acho` contracts.
- enforce current-branch push behavior.

## F-4 /pr --only Continuation Policy (P0)

- warn when branch is not pushed.
- propose auto-push.
- continue with engineer-selected mode when auto-push is declined.

## F-5 Mandatory Local Security and Quality Gates (P0)

- pre-commit, commit-msg, pre-push enforcement.
- integrate `gitleaks`, `semgrep`, `pip-audit`, `ruff`, `ty`, tests.

## F-6 Remote Skills Lock and Cache (P0)

- lock sources and integrity metadata.
- support cache TTL and offline fallback.

## F-7 Risk Decision Store and Audit Trail (P0)

- persist explicit risk acceptance.
- prevent repeated prompts when valid prior decision exists.

## F-8 Maintenance Agent Reporting (P1)

- weekly local report with simplification proposals.
- optional PR generation after human approval.
