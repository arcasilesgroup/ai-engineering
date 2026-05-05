# Build Packet: HX-12 Engineering Standards And Legacy Retirement

## Summary

Implemented the HX-12 closure layer for standards and retirement governance:

- Added `src/ai_engineering/standards.py` with the canonical standards matrix, review/verify bindings, and parity-first legacy retirement manifest.
- Bound `src/ai_engineering/verify/taxonomy.py` check families to the standards matrix without changing verify execution behavior.
- Added live and template context docs for the standards matrix, Harness Engineering, and harness adoption guidance.
- Added executable unit coverage for required standards, context availability, review/verify lookup, and safe deletion rules.
- Recorded the standards and retirement matrix in `.ai-engineering/specs/spec-117-progress/hx12_standards_retirement_matrix.md`.

## Files Changed

| Path | Change |
| --- | --- |
| `src/ai_engineering/standards.py` | New executable standards registry and legacy retirement manifest. |
| `src/ai_engineering/verify/taxonomy.py` | Verification check specs now carry standards bindings. |
| `tests/unit/test_engineering_standards.py` | New HX-12 standards, context, and retirement manifest tests. |
| `tests/unit/test_verify_taxonomy.py` | Added verification registry standards-binding assertions. |
| `.ai-engineering/contexts/engineering-standards.md` | New canonical standards matrix context. |
| `.ai-engineering/contexts/harness-engineering.md` | New canonical Harness Engineering context. |
| `.ai-engineering/contexts/harness-adoption.md` | New framework adoption guide for implemented runtime contracts. |
| `src/ai_engineering/templates/.ai-engineering/contexts/engineering-standards.md` | Template copy for new installs. |
| `src/ai_engineering/templates/.ai-engineering/contexts/harness-engineering.md` | Template copy for new installs. |
| `src/ai_engineering/templates/.ai-engineering/contexts/harness-adoption.md` | Template copy for new installs. |

## Implementation Notes

`EngineeringStandard` covers `clean-code`, `clean-architecture`, `solid`, `dry`, `kiss`, `yagni`, `tdd`, `sdd`, and `harness-engineering`. `build_engineering_standards_matrix()` validates that each standard has canonical references and at least one review and verify consumer.

`LegacyRetirementFamily` records family id, sequence, status, replacement owner, current surfaces, replacement references, parity proofs, rollback text, and whether deletion is allowed. The current manifest deliberately keeps deletion disabled for every family.

Verify taxonomy entries now include standards bindings so checks like `validate`, `verify:quality`, and kernel check families can be traced to the standards they prove or support. This is metadata only; the verify service behavior and scoring contract remain unchanged.

## Deferred Work

- Formal governance and review tasks remain deferred to the final end-of-implementation review pass requested by the user.
- Actual deletion of legacy families remains future work and must proceed one family at a time after parity proof.
- Root README and GETTING_STARTED updates remain trailing user-facing documentation work.

## Local Evidence

- RED test run failed on missing `ai_engineering.standards`, as expected.
- Focused standards and taxonomy tests passed: `11 passed in 0.08s`.
- Ruff import/syntax checks passed for touched Python files.
- Adjacent verify tests passed after Sonar cleanup: `102 passed in 0.45s`.
- SonarQube for IDE touched-file analysis returned `findingsCount: 0`.