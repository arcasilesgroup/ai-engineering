# Contract Compliance

## Purpose

Clause-by-clause validation of framework contracts (`framework-contract.md`, `manifest.yml`) against actual implementation surfaces. Extracts contractual obligations, maps each to code/config/docs evidence, and produces a compliance matrix with PASS/PARTIAL/FAIL per clause.

## Trigger

- Command: agent invokes contract-compliance skill or user requests contract audit.
- Context: pre-release compliance review, post-refactoring contract alignment, governance audit.

## Procedure

### Phase 1: Extract Clauses

1. **Parse framework-contract** — read `context/product/framework-contract.md` and extract each contractual obligation.
   - Identify statements containing MUST, SHALL, REQUIRED, MANDATORY, or equivalent imperative forms.
   - Assign a clause ID (e.g., FC-001, FC-002) to each obligation.
   - Record the clause text, section, and any referenced artifacts.

2. **Parse manifest obligations** — read `manifest.yml` and extract configuration-level contracts.
   - Ownership model boundaries (framework/team/project/system).
   - Non-negotiables list.
   - Command contract definitions.
   - Enforcement hook requirements.
   - Tooling requirements.

### Phase 2: Map to Implementation

3. **Build evidence map** — for each clause, identify the implementation surfaces that satisfy it.
   - Code surfaces: Python modules, functions, classes that implement the obligation.
   - Config surfaces: YAML/JSON files, CI workflows, hook scripts.
   - Doc surfaces: instruction files, standards, skill/agent references.
   - Test surfaces: test files that validate the obligation.

4. **Classify evidence strength** — for each mapping, assess completeness.
   - **Direct**: code/config explicitly implements the clause.
   - **Indirect**: behavior is implied but not explicitly tested or documented.
   - **Missing**: no evidence found for the clause.

### Phase 3: Evaluate Compliance

5. **Assess each clause** — determine compliance status.
   - **PASS**: direct evidence exists, tested, and documented.
   - **PARTIAL**: some evidence exists but gaps remain (e.g., implemented but not tested).
   - **FAIL**: no evidence or contradictory implementation.

6. **Identify semantic gaps** — look for obligations that are structurally present but semantically wrong.
   - Contract says X, implementation does Y (behavioral mismatch).
   - Contract scope broader than implementation scope.
   - Implementation exceeds contract (undocumented behavior).

### Phase 4: Report

7. **Produce compliance matrix** — structured output with one row per clause.
   - Clause ID, text, section, status, evidence paths, gap description.
   - Summary statistics: total clauses, PASS count, PARTIAL count, FAIL count.
   - Blocking issues (FAIL clauses that prevent release).

## Output Contract

```
## Contract Compliance Report

### Summary
- Total clauses: N
- PASS: N | PARTIAL: N | FAIL: N
- Compliance score: N%

### Clause Matrix
| ID | Clause | Section | Status | Evidence | Gap |
|----|--------|---------|--------|----------|-----|
| FC-001 | ... | ... | PASS/PARTIAL/FAIL | path(s) | ... |

### Blocking Issues
- [List of FAIL clauses that block release]

### Recommendations
- [Prioritized list of actions to close gaps]
```

## Governance Notes

- This skill validates contract semantics — `integrity-check` validates structural correctness. Both are needed for full compliance.
- FAIL clauses are release blockers unless explicitly risk-accepted via `state/decision-store.json`.
- Contract compliance is a governance requirement for release readiness (pairs with `quality/release-gate.md`).
- Run after any change to `framework-contract.md`, `manifest.yml`, or major implementation changes.

## References

- `context/product/framework-contract.md` — primary contract source.
- `manifest.yml` — configuration-level contract.
- `skills/govern/integrity-check.md` — structural validation (complementary).
- `skills/quality/release-gate.md` — release readiness aggregation.
- `agents/platform-auditor.md` — orchestrator that invokes this skill.
- `standards/framework/core.md` — governance structure and ownership model.
