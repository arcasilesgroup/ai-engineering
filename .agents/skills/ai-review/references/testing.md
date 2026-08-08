# Testing

- A check that fails without this change. If none exists, the change is untested whatever
  the coverage number says.
- Tests that assert behaviour, not implementation. Renaming a private function should not
  turn anything red.
- The failure the test was written for: does it still reproduce with the fix reverted.
- Mocks that assert the contract of the thing they replace, not the shape of the caller.
- Flakiness: time, ordering, network, randomness. Each one named and pinned.
- A test that cannot fail is worse than no test: it is a green nobody earned.
