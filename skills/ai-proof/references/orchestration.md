# Orchestrated mode: leaves as fresh agents

For tree depth 4+ or any build clearly beyond one sitting. The core insight:
the stall-at-80-percent failure is an end-of-long-context disease. Attention,
not time, is the scarce resource, and a fresh subagent per leaf resets it.

## The driver loop

You (the main session) are the driver. You do not implement leaves; you
plan, dispatch, verify, and integrate.

1. **Plan.** Write PLAN.md (contract, tree, gates file per leaf and branch)
   from templates/PLAN.md. Every leaf gets three fields there: `Owns` (the
   files it may write), `Needs` (the leaf ids that must be verified before it
   starts), `Tier` (which model runs it). This is the only step where the
   whole task must fit in one head.

2. **Dispatch every ready leaf at once.** A leaf is ready when every id in
   its `Needs` is verified. At the start that is every leaf with an empty
   `Needs`, which on a well-split tree is most of them. Launch them
   concurrently, in one message, each with a brief of exactly:
   - the contract section of PLAN.md (not the whole file, not your history)
   - its own gates file, verbatim
   - the instruction: work the four passes until every gate is met with
     evidence, then stop; if a gate is impossible, ABANDON it with a reason.

   Do not serialize the fan-out. Leaves own disjoint files by contract, so
   dispatching one at a time buys nothing and costs the whole tree's
   wall-clock. If two leaves would touch the same file, fix the plan; do not
   coordinate through hope.

3. **Verify each leaf as it returns.** Do not wait for the rest of the batch.
   Re-run that leaf's checks, naming its file:

   ```
   node <skill-dir>/scripts/gate-check.mjs --recheck gates/leaf-x.md
   ```

   Two details carry the weight here. `--recheck` re-executes every CHECK
   even for boxes the leaf already ticked with evidence; without it a
   self-certified gate is taken on trust and its command never runs, which
   makes this whole step decorative. And naming the file matters: a bare
   `gate-check` globs the milestone gates file (`.ai-engineering/spec.html` in
   ai-engineering, historically `GATES.md`) plus all of `gates/*.md`, so verifying one
   leaf would re-run the entire tree's checks, once per leaf, for the whole
   build. A failed `--recheck` withdraws that gate's evidence back to
   `pending`, which makes it unmet by the format's second rule and blocks the
   stop-hook; the box stays as the leaf set it, because a checkbox is the
   leaf's claim and voiding the proof under it is enough. Send it back with
   the specific unmet gates named.

   Two limits to hold in mind. `--recheck` can only re-run commands, so a
   manual gate is re-verified by you reading its evidence and judging whether
   it proves anything; a fabricated manual evidence line survives the flag
   untouched, which is the strongest argument for the runnable-gate
   preference in references/gates.md. And a gate that fails while siblings
   are still in flight may be failing on their half-written files rather than
   on this leaf's work, so confirm a newly-failing check is really the leaf's
   before sending it back. If it was the sibling, the plan is missing a
   `Needs` entry; fix the plan, not the leaf.

4. **Dispatch what it unblocks, immediately.** A verified leaf may complete
   the `Needs` of others; launch those now rather than at the end of a round.
   The tree drains continuously, and the slowest leaf delays only its own
   dependents instead of everything. A leaf sent back for rework unblocks
   nothing until it passes.

5. **Log.** Append one line per event to PLAN.md's status log: dispatched,
   verified, sent back, abandoned. You own PLAN.md and the branch gates;
   leaves own their own files and their own gates file. That split is what
   keeps an append-only log safe while several leaves are in flight.

6. **Integrate at branches.** When all children of a branch are verified,
   work that branch's integration gates yourself, or dispatch an integration
   leaf for it. Whole-project checks (full test suite, typecheck, lint,
   build) belong here and run once, not once per leaf; see references/gates.md
   for the scoping rule that makes that true.

7. **Report.** Only when the root's gates are met. Paste the ledger, N of N,
   with every ABANDON line surfaced, and re-measure every number you state.

## Verification hierarchy

Three layers, weakest to strongest, each catching what the layer below
misses:

1. **Leaf self-check**: gate-check run by the leaf itself. Catches honest
   incompleteness, misses self-deception.
2. **Parent re-run**: the driver re-executes the checks with `--recheck`.
   Catches self-deception and environment differences. The flag is the whole
   layer; a plain re-run skips exactly the gates worth distrusting.
3. **Stop-hook** (optional, Pi/Zed surfaces in ai-engineering): structurally blocks a session from
   ending while gates are unmet. Catches the driver itself drifting into
   report mode. It hooks `Stop`, not `SubagentStop`, so it guards the driver
   and never blocks a dispatched leaf on its siblings' unmet gates.

Prose discipline is layer zero and it is the weakest; that is the lesson v2
is built on. Prefer moving any repeated judgment call up this hierarchy:
if you find yourself re-checking the same thing twice by reading, write a
CHECK command for it.

## Model and effort tiering

Decide the tier once, while planning, and record it per leaf in PLAN.md so
dispatch is a lookup instead of a fresh judgment call each time. The routing
policy itself is not this skill's business: consult the model-router skill
for which model fits which shape of work, and write its answer into the
`Tier` field.

Two constraints this skill adds on top of that policy:

- **The driver stays on the strong model, always.** A weak driver
  invalidates every verification above layer one.
- **Verification is never tiered down.** Cheap models are for producing
  mechanical work, not for judging whether work is done. The `--recheck`
  pass is the driver's, not a subagent's.

## When NOT to orchestrate

Below roughly half an hour of real work, subagent overhead (context
re-establishment per leaf) costs more than it buys. Stay solo: one gates
file, one session, same discipline. The gates still do their job; you just
skip the dispatch machinery.
