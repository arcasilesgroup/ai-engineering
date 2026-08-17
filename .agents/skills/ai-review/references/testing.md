# Testing

- A check that fails without this change. If none exists, the change is untested whatever
  the coverage number says.
- Tests that assert behaviour, not implementation. Renaming a private function should not
  turn anything red.
- The failure the test was written for: does it still reproduce with the fix reverted.
- Mocks that assert the contract of the thing they replace, not the shape of the caller.
- Flakiness: time, ordering, network, randomness. Each one named and pinned.
- A test that cannot fail is worse than no test: it is a green nobody earned.

## What each test is for, and the four kinds

The matrix `ai-test` carried before it was absorbed. It is here rather than in a skill body
because it is a reading aid for a diff, and a diff is what this lens loads for.

- Start from the risk, not from the function. What breaks, who notices, and how late.
- Write the behaviour as an example first — given, when, then — and the test after it. An
  example somebody disagrees with is cheaper to argue about than an assertion.
- **Unit**: one decision, no I/O, and the assertion names the decision.
- **Integration**: the seam between two things this repository owns, exercised for real.
- **End to end**: one journey a person takes, on the thing that ships.
- **Negative**: the input that must be refused, and the refusal's exact code or message.
- A risk with no negative test is a risk nobody has decided about.

## What a test pass may not do

- It does not change production code. A test that needed the code changed to pass is a
  finding, and it goes to `/ai-build` with the failure that motivated it.
- It does not raise coverage over code nobody calls. Covering dead code moves a number and
  proves nothing; deleting it moves the same number honestly.
- It does not decide whether the change ships.

## The evidence manifest

What `ai-verify` carried. One row per criterion, and a row is complete only when every
column is filled: the specification it comes from, the criterion in one line, the command
that was run, the version of what ran it, the exit code it returned, and the digest of the
artefact it produced. A row missing a column is INCOMPLETE and never a pass.

Allowlists run without `--fix`: a formatter that repairs what it is measuring reports on a
file that no longer exists. On failure the answer is `/ai-debug` for a cause or `/ai-build`
for the change, and never a rerun with the repair switched on.
