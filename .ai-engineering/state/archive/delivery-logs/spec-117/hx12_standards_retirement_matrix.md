# HX-12 Standards And Retirement Matrix

## Standards Canon

| Surface | Role | Owner | Status |
| --- | --- | --- | --- |
| `.ai-engineering/contexts/engineering-standards.md` | Canonical standards matrix for review, verify, and retirement consumers | HX-12 | Added |
| `.ai-engineering/contexts/harness-engineering.md` | Canonical Harness Engineering rules | HX-12 | Added |
| `.ai-engineering/contexts/harness-adoption.md` | Framework-level adoption guidance for implemented runtime contracts | HX-12 | Added |
| `src/ai_engineering/standards.py` | Executable standards, review/verify bindings, and retirement manifest | HX-12 | Added |
| `src/ai_engineering/verify/taxonomy.py` | Verify check families now carry standards bindings | HX-11/HX-12 | Updated |

Template copies were added under `src/ai_engineering/templates/.ai-engineering/contexts/` so new installs receive the same standards contexts.

## Standards Coverage

| Standard | Primary canon | Review consumers | Verify consumers |
| --- | --- | --- | --- |
| `clean-code` | operational principles plus standards matrix | correctness, maintainability, frontend, design | quality, platform |
| `clean-architecture` | operational principles plus standards matrix | architecture, backend, compatibility | architecture, platform |
| `solid` | operational principles plus standards matrix | architecture, maintainability, backend | architecture, quality |
| `dry` | operational principles plus standards matrix | maintainability, architecture, performance | quality, architecture |
| `kiss` | operational principles plus standards matrix | architecture, maintainability, correctness | quality, feature |
| `yagni` | operational principles plus standards matrix | architecture, compatibility, maintainability | feature, architecture |
| `tdd` | Constitution plus standards matrix | testing, correctness, compatibility | quality, feature, platform |
| `sdd` | Constitution plus standards matrix | architecture, compatibility, testing | governance, feature, platform |
| `harness-engineering` | harness engineering context plus standards matrix | security, architecture, compatibility, testing, performance | governance, security, architecture, platform |

## Legacy Retirement Families

| Family | Replacement owner | Status | Deletion rule |
| --- | --- | --- | --- |
| Control-plane compatibility surfaces | HX-01 | preserved | No deletion without explicit compatibility reader retirement proof |
| Manual instruction families | HX-03/HX-12 | blocked | Decide manual, generated, or retired family-by-family |
| Legacy harness gate and eval affordances | HX-04/HX-11 | blocked | Retire only after verify taxonomy and kernel parity proof |
| State and report residue surfaces | HX-05 | blocked | Retire only after state-plane readers and report reducers prove parity |
| Template/runtime duplication | HX-08/HX-09/HX-10 | blocked | Preserve stdlib-only hook runtime until replacement proof exists |
| User-facing rollout docs | HX-12 | preserved | Root docs trail implemented runtime contracts |

The executable manifest currently sets `delete_allowed=False` for every family. Future retirement work must flip one family at a time only after parity proof and rollback criteria are present.

## Boundary Notes

- `HX-12` consumes earlier ownership decisions and does not reopen control-plane, mirror, kernel, state, capability, context-pack, eval, or CLI adapter architecture.
- Review and verify bindings are standards references, not new specialist ownership.
- README and GETTING_STARTED remain trailing user-facing docs; this slice adds framework-level guidance first.