# Verification

## Update Metadata

- Rationale: align verification scope with finalized command and policy model.
- Expected gain: complete coverage of critical governance paths.
- Potential impact: larger E2E matrix, including continuation-path testing.

## MVP Validation Matrix

| Dimension | Required Values |
|---|---|
| OS | Windows, macOS, Linux |
| Repo state | empty repo, existing repo, already-installed repo |
| Connectivity | online, offline, partial source failure |
| Command flows | `/commit`, `/commit --only`, `/pr`, `/pr --only`, `/acho`, `/acho pr` |
| Security failures | leak hit, semgrep hit, vuln hit, lint/type/test failures |
| Ownership safety | framework update must not overwrite team/project paths |

## Critical E2E Cases

- install creates required state files and standards layering files.
- updater modifies only framework/system-managed paths.
- `/commit` blocks on protected branch and on failed mandatory checks.
- `/pr --only` on unpushed branch warns, proposes auto-push, then continues according to chosen mode.
- prior risk decision reuse suppresses duplicate prompts unless expired/materially changed.
- remote skills offline mode uses lock/cache without policy degradation.

## Acceptance Criteria

- all command contract cases pass on all three OSes.
- all mandatory checks are enforced locally.
- decision-store and audit log entries are generated and parseable.
- readiness checks report accurate status for `gh`, `az`, hooks, and stack tooling.
