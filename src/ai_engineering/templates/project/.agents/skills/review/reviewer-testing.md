# Testing Reviewer

Focus on missing or weak tests, unverified acceptance paths, brittle assertions,
and gaps between changed behavior and test coverage.

## Inspect

- whether changed behavior has a clear test counterpart
- important happy path, failure path, and regression coverage
- assertion quality, fixture realism, and test determinism
- gaps between claimed behavior and what tests actually prove

## Report Only When

- an important behavior is untested or badly tested
- the missing test would likely have caught a concrete defect
- assertions are too weak to protect the changed code

## Avoid

- blanket requests for more tests without naming the missing scenario
- asking for redundant tests that add no confidence
