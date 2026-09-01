# Gates: <branch name> (integration)

Scope: children <list child leaves/branches> merged into one working whole

- [ ] N1: every child leaf's gates file is fully checked (no unchecked boxes, no pending evidence)
  CHECK: node <skill-dir>/scripts/gate-check.mjs --status gates/leaf-<a>.md gates/leaf-<b>.md
  EXPECT: ALL MET
  EVIDENCE: pending

- [ ] N2: the whole project builds and its full suite passes
  CHECK: <repo-wide build / typecheck / full test suite: the checks that must NOT sit in a leaf gate>
  EXPECT: <success marker>
  EVIDENCE: pending

- [ ] N3: interfaces match the contract in PLAN.md
  CHECK: <import test, API shape assertion, or schema diff>
  EXPECT: <success marker>
  EVIDENCE: pending

- [ ] N4: cross-child behavior works end to end
  CHECK: <integration test, smoke script, or curl sequence>
  EXPECT: <success marker>
  EVIDENCE: pending

- [ ] N5: nothing regressed in siblings this merge touched
  CHECK: <targeted re-run of affected sibling checks>
  EXPECT: <success marker>
  EVIDENCE: pending

<!--
Branch gates exist because finished parts do not imply a finished whole.

N1 reads the children's ledger with --status rather than re-running it, because
the driver already re-ran each leaf's checks with --recheck when that leaf
returned. That per-leaf re-verification is what makes this roll-up worth
anything; without it N1 is just child self-certification with extra steps
(verification hierarchy, references/orchestration.md).

N2 is where whole-project checks live. A leaf gate that runs the full suite
costs the tree that suite once per leaf and again per verification; scope leaf
checks to the files that leaf owns and let this gate cover the whole
(references/gates.md).
-->
