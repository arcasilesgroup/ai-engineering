# Gates: <leaf or task name>

Scope: <one line: what this unit of work delivers>

- [ ] G1: <observable outcome, stated so a stranger could judge it>
  CHECK: <shell command that proves it>
  EXPECT: <substring the command output must contain, or /regex/>
  EVIDENCE: pending

- [ ] G2: <another runnable outcome>
  CHECK: <command>
  EXPECT: <substring or /regex/>
  EVIDENCE: pending

- [ ] G3: <manual gate, when no command can prove it>
  EVIDENCE: pending

<!--
Rules (full spec in references/gates.md):
- One box per outcome. Boxes are flipped by gate-check.mjs when CHECK output
  matches EXPECT, or by hand for manual gates.
- A checked box with EVIDENCE still reading "pending" counts as UNMET.
- Evidence is the deciding lines only, never a full log.
- Scope each CHECK to the files this leaf owns: `vitest run tests/parse.test.ts`,
  not `npm test`. Whole-project checks (full suite, repo-wide typecheck, build)
  belong in the branch gates, where they run once instead of once per leaf.
- If the checks here are not parallel-safe (one port, one browser, one
  database), add a `Jobs: 1` line under Scope.
- If a gate becomes impossible, do not delete it. Add a line:
    ABANDON: G<n> <reason>
  and report it. Visible surrender is honest; silent scope-narrowing is not.
-->
