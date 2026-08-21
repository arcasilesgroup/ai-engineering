---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0020"
title: "Four reporters that cannot fail are telemetry, not waste"
date: "2026-08-21"
spec: "022"
status: "proposed"
supersedes: ""
---

# 0020. Four reporters that cannot fail are telemetry, not waste

## Context and problem statement

The published subtraction plan's file audit graded seven files DELETE — 845 lines across
`tests/stats.py`, `tests/one_home.py`, `tests/unreviewed.py`, `tests/own_head_receipts.py`
and three of their tests. The criterion it used, in its own words: every exit is `return 0`
and none of them is in `just check`.

That criterion is the definition of the word this repository already uses for a legitimate
thing. `CONSTITUTION.md`: "Telemetry observes and never decides; it fails open and says so."
The whole `@guard` / `@telemetry` split exists so that a component which cannot fail is a
declared class rather than an oversight. Grading the four as waste for not blocking would
delete the category.

## Considered options

1. **Delete all seven, and regrade the ledger rows they are evidence for.** What the plan
   asks. It is 845 lines and it costs four measurements.
2. **Put them in `just check` so they run every gate.** Makes the word "measured" true
   everywhere, and adds gate minutes for output nobody is blocked by. The justfile already
   argues against it, per file, in prose that was written before this question was asked.
3. **Keep them, and repair the one claim that is actually false.** What this record decides.

## Decision outcome

Option 3. The four are kept, and each one was checked rather than defended as a class:

`tests/unreviewed.py` derives which commits no closed block review covers. The justfile
says why it must not block: "unreviewed is the ordinary state of work in flight, and a gate
that failed on it would demand a review before the block it belongs to has closed." A gate
here would amplify exactly what the block cadence exists to remove.

`tests/one_home.py` counts how many primary homes each commit touches. It cannot block
because `PO-16`'s single recorded exception cannot be recognised mechanically, and a gate
here "would assert a judgement it cannot make". Its reading is not decorative: 194 commits
measured, 26 touching one home and 168 touching more, the widest spanning seven.

`tests/own_head_receipts.py` is deliberately outside the pytest gate for a stated reason —
"a gate that needed the network would fail on a machine that has none" — and it answers a
question that is still open: whether a candidate commit carries the exact-HEAD workflow
proofs specification 010's Task 53 requires. Deleting it removes the only instrument for a
transition that has not happened yet.

`tests/stats.py` is the repository's own metrics report and `docs/tools.md` names it twice
as a report rather than a gate.

All four are cited as evidence in `docs/requirements.toml`: `EP-008` names
`test_own_head_receipts.py`, and the `one_home` and `unreviewed` rows name their scripts and
their tests. Deleting the instruments turns four rows that carry a measurement into four
rows that carry nothing, which is a trade this record refuses on the same grounds `0018`
refused the plan's other large deletion: the number was measured, and the measurement
disagreed with the audit.

One thing the audit was right to look at, and it is repaired here rather than argued away.
The `one_home` ledger note says the practice is "now measured every run instead of once",
and `homes` is not in `check` — the recipe list is `build sbom lint typecheck test cover
security register skilleval counts intent-page lenses ran`. It is measured when somebody
runs it, which is a different sentence, and the note now says that one.

## Consequences

The good one: the category survives. A repository that deletes its telemetry for not
blocking ends up with only guards, and then every observation has to justify itself as a
gate — which is how a gate that should not exist gets written.

The one that gets worse, and it is real. Four instruments stay in the tree that nothing runs
automatically, so their readings age. Nobody is told when `one_home`'s 168 becomes 200. The
honest repair is a schedule or a report that carries them, and neither exists; naming that
here is the least this can do, and it is less than the deletion would have cost.

A smaller one: the plan's file audit reached 27 DELETE verdicts over 6,476 lines, and two of
its groups have now been refused on measurement — `loop_guard` in `0018` and these four
here. The remaining verdicts are not thereby wrong, and they are also not evidence any more.
Each one that lands should be checked the way these two were, rather than counted.
