# Gate file format

The machine-readable contract between "I say it is done" and "it is done".
Both bundled scripts (`gate-check.mjs`, `stop-hook.mjs`) parse exactly this
format, so any deviation weakens enforcement.

## Format

```markdown
# Gates: <scope name>

Scope: <one line>
Jobs: 1

- [ ] G1: <outcome>
  CHECK: <shell command>
  EXPECT: <substring or /regex/>
  EVIDENCE: pending

- [ ] G2: <manual outcome>
  EVIDENCE: pending

ABANDON: G2 <reason, only if a gate had to be surrendered>
```

## Parsing rules

- A gate starts at a line matching `- [ ]` or `- [x]` (case-insensitive x).
- Indented `CHECK:`, `EXPECT:`, `EVIDENCE:` lines up to the next gate belong
  to the gate above them.
- `EXPECT:` is a plain substring match against the command's combined
  stdout+stderr, unless wrapped in slashes, then it is a JavaScript regex
  (e.g. `/8\/8 passed/`).
- `ABANDON: G<n> <reason>` anywhere in the file marks that gate as
  honestly surrendered. Tools treat it as resolved but reports must list it.
- `Jobs: <n>` is optional and caps how many of *this file's* checks run at
  once. Omit it and the checks run concurrently under the global `--jobs`
  cap, sharing one execution of any command two gates both name. Include it
  when the checks are not parallel-safe (they bind a port, drive one browser,
  write one database): the file then runs at most n at a time and neither
  lends its results to other files nor borrows theirs, since a borrowed
  result is a concurrent one. `Jobs: 1` is the fully serial case.

## What counts as UNMET

A gate is unmet if any of these hold:

1. Its box is unchecked, and no ABANDON line names it.
2. Its box is checked but `EVIDENCE:` still reads `pending`. A checkbox is a
   claim; evidence is the proof. Checked-without-evidence is the exact
   failure mode this system exists to catch, so it counts as worse than
   unchecked, not better.

A checked box *with* evidence is trusted by default and its command is not
re-run. That trust is exactly what a driver must not extend to a returned
subagent, so `gate-check --recheck` re-executes every CHECK regardless of
what the boxes claim. Use it whenever you are checking someone else's work,
including your own from an earlier context.

When a re-check fails, the gate's evidence is reset to `pending` and its box
is left alone. Rule 2 then makes it unmet, which is the whole reason rule 2
is written the way it is: a claim without proof is worth nothing, so the
tooling never has to argue with a checkbox. gate-check only ever ticks boxes,
never unticks them.

## Scope a gate to whoever owns it

A gate's CHECK should exercise the thing its own scope is responsible for and
nothing more. In orchestrated mode this is a hard rule, because breaking it
is quadratic: put `npm test` in a leaf gate and every leaf re-runs the whole
suite, then the driver re-runs it again per leaf when verifying.

- **Leaf gates check the leaf.** Target the files that leaf owns:
  `vitest run tests/parse.test.ts`, not `npm test`. `tsc --noEmit -p
  tsconfig.leaf.json` or a targeted `eslint src/foo`, not a repo-wide sweep.
  If a leaf's only honest check is a whole-project command, the leaf is
  under-specified; find the observable that belongs to it alone.
- **Branch and root gates check the whole.** The full test suite, repo-wide
  typecheck and lint, the production build, end-to-end smoke tests: these are
  integration outcomes and belong to integration nodes, where they run once.
  That is also where they are meaningful, since a full suite passing is a
  statement about the merge, not about any one leaf.
- **Name files when you invoke the checker.** `gate-check gates/leaf-x.md`
  runs one leaf's checks. Bare `gate-check` globs `GATES.md` plus every
  `gates/*.md`, which is right at report time and wasteful anywhere else.
- **A leaf's CHECK may read only settled files**: the ones that leaf owns,
  plus the output of leaves already verified. Disjoint ownership stops leaves
  from overwriting each other, not from reading each other mid-edit, and when
  leaves run concurrently a check that imports a sibling's half-written file
  fails for reasons that have nothing to do with the leaf. If a check needs
  another leaf's files, even transitively, declare that leaf in `Needs`.

## Writing good gates

- **State outcomes, not activities.** "All 8 planets clickable" is checkable.
  "Work on planet interaction" is not.
- **Prefer runnable gates.** Every CHECK you write converts model-tokens of
  self-assessment into a free shell command. If you cannot think of a CHECK,
  ask whether the outcome is observable at all; if it is not, sharpen it.
- **Make EXPECT decisive.** Match the line that can only appear on success
  (`8/8 passed`), not one that appears either way (`done`).
- **Cap evidence.** gate-check records the deciding tail of output. When
  filling manual evidence by hand, quote the deciding lines or cite
  `file:line`, never paste a log.
- **Five to twelve gates per leaf** is the useful range. Two gates means the
  leaf is under-specified; twenty means the leaf should have been two leaves.

## Numbers rule

Any number that will appear in a final report deserves its own gate with a
CHECK that measures it. Measured runs of v1 showed reports whose only false
claims were numbers stated from memory. If a number matters enough to
report, it matters enough to measure at report time.
