# Documentation

A separate documentation skill was not kept: the work splits into judging a diff, which is
this pass, and the tasks that land with the change, which belong to `/ai-ship`.

- Something the diff changed that a person reads and that still says the old thing. Names,
  flags, defaults, error text, the README's first paragraph.
- A behaviour somebody upgrading would search for and not find. If the change moves, renames
  or removes anything they depend on, the changelog entry is part of the diff and not a
  follow-up.
- A comment explaining what the code says. Delete it. A comment saying *why* the code is
  surprising, or what breaks if it changes, is the one worth keeping.
- A docstring that promises what the function does not do — this repository has shipped two
  in one week, and both took an exception out through a gate the docstring said would
  return a verdict.
- An example that nothing runs. It is the first line to go stale, and it goes stale
  silently, so it either has a check behind it or it says it is illustrative.
- Instructions written for whoever already knows. Rule 9: somebody who does not code has to
  be able to follow what changed and why it matters to them.
- What the change does *not* do. The absence is the half a reader cannot infer, and it is
  where support tickets come from.
