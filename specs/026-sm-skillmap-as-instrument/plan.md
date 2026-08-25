# Plan: skill-map as the reference-integrity instrument — 026 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and this
exact `plan.md`**, recorded at their digests in their own record. One repository writer, on a
branch carrying the whole 026 change. Each task is one atomic commit touching one primary
production, policy or skill file plus only the files that task names. Rollback for every task
is `git revert <commit>`.

**This plan is not edited while it is executed.** Every commit runs the whole gate in the same
chain as the commit itself. A receipt is keyed to the bytes being committed, so `just map`'s
digest is computed and recorded at commit time, and the map is read back by its own recipe.

## The order, and why

The instrument's honesty is decided by the two things the challenge proved the draft got wrong
before anything ships: the real-defect count must be fixed *before* the recipe promises a
0, and `sm` must be pinned by version the way every other engine is. So the plan is ordered so
that the earliest possible failure is caught first, and the gate's promise is honest:

1. Pin `sm` and define the `join` recipe in the Justfile — task 1 is the first failing check,
   because a tool whose version we did not test is a tool whose answer we cannot read.
2. Exclude the `.venv` copy from the map (task 2) — the wheel's own skills scan as a second,
   phantom tree and inflate the real count; the instrument must read the source tree once.
3. Record the real defects as accepted risk (task 3) — the challenge proved the 0-promise is
   unreachable until each real finding is fixed **or** accepted with a dated record, prose
   cannot accept. The fix block is deferred by acceptance, not hidden.
4. Add the check that holds the bits together (task 4): a script that runs `sm scan && sm
   check --json`, applies the `NNN-slug` template-hole exclusion list, and renders a digest,
   so the recipe's green is a machine re-read of the whole tree rather than a prose promise.
5. Wire `join` into `just check` (task 5) and make the acceptance + exclusion the two live
   inputs the check reads every run.

**What this plan is not doing, and why**

- **No CI/CD task and no observability task.** Spec 026 adds no service, no endpoint, no URL:
  a data file, a script, a Justfile recipe. `/ai-plan` requires deployables only, and
  inventing them here would be ticked boxes against nothing.
- **No repair of the ~47 real broken references in this block.** The challenge and the
  council both found the spec's numbers move (40 drafted, 47 live). The instrument's first
  honest finding is that the tree holds real broken links; that defect is a separate block
  with its own per-link evidence, named in `spec.md`'s unresolved risk, not bundled in here
  where it would mix one decision (adopt the instrument) with dozens of resolutions.
- **No change to `.ai/intent.md` or `CONSTITUTION.md`.**

## The boundary this plan may not cross

`sm` is a third-party binary, not part of the wheel. The recipe and script must work on a
machine with no `sm` (stranger install): the recipe prints "map not exercised; sm missing"
and the gate stays green for the wrong reason guarded — the check is bracketed so a machine
without the tool does not fail, and the source-tree scan is not a requirement. The directory
the scan writes (`~/.skill-map/` or local) must stay out of the receipt and the commit,
because a DB is a sidecar, not a record.

## Tasks

1. [ ] **Pin `sm` and add the `map` recipe to the Justfile** —
   - **file:** `Justfile`
   - **check:** `just map` (before: undefined; after: runs or prints "map not exercised; sm
     missing" on a machine without `sm`, and `just --list` shows `map`)
   - **rollback:** `git revert <commit>`
   - **done when:** the recipe exists, `sm` version pinned (or the pattern made to find a
     pinned engine), and `just map` runs without error on this machine.
2. [ ] **Exclude the `.venv` copy from the scan roots** —
   - **file**: the map's root/ignore settings (`.skill-map/settings.json` or the config
     that declares scan roots)
   - **check:** the `.venv` copy of the wheel's skills is no longer a node (`sm list` shows
     no `.venv/…/SKILL.md`)
   - **rollback:** revert the settings file.
   - **done when:** `sm list` names only source-tree nodes.
3. [ ] **Record the real broken references as accepted risk in a dated record** —
   - **file**: `docs/adr/0024-skill-map-finds-47-real-broken-references.md` (or the
     `ai-eng accept` output for the 47 findings, whichever the harness writes natively)
   - **check**: `ai-eng accept --list` (or `git show HEAD:…adr`) shows 47 accepted real
     broken references, each with `--by`, `--expires`, and `--justification`
   - **rollback:** revert the acceptance record
   - **done when:** the acceptance is a record a later repair reads, not a claim.
4. [ ] **Carry the `NNN-slug` template exclusion list + tallise the map** —
   - **file**: `policy/skill-map-exclusions.toml` (list of template prefixes that are holes,
     not targets)
   - **check:** `uv run --with pytest pytest -q tests/test_skill_map.py` reads the
     exclusions and asserts the template pattern is expected, not failing
   - **rollback:** revert the policy file and the test
   - **done when:** the map distinguishes the 15+ template holes from the 47 real without a
     suppression comment anywhere.
5. [ ] **Wire the whole map into `just check`** —
   - **file**: the Justfile `check` recipe (append `map`)
   - **check:** `just check` runs `map` last and prints its digest; the gate does not fail
     when engine missing, fails when a real broken reference is unaccepted
   - **rollback:** revert the Justfile.
   - **done when:** `just check` includes the map step, the acceptance + exclusion drive its
     green, and the output is shown.

## The order this plan is not doing, and why

The list is not fully parallelled: tasks 1-2 and 4 are independent files, but 5 depends on 4,
and 3 depends on 2 (the count is honest only after `.venv` is excluded). The one-writer rule
in `AGENTS.md` means no block is split between parallel writers; each commit lands in order.