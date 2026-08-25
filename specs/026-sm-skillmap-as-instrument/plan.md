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
before anything ships: the real-defect count must be accepted (or fixed) *before* the recipe
promises a 0, and `sm` must be pinned by version the way every other engine is. So the plan is
ordered so that the earliest possible failure is caught first, and the gate's promise is
honest. Task 1 pins `sm` and defines the `map` recipe; task 2 keeps the map reading the source
tree once by excluding the `.venv` copy; task 3 carries the `NNN-slug` template-hole exclusion
and the real-defect acceptance as data the gate reads; task 4 turns `just map` into the
single digest of real-vs-template; task 5 wires it into `just check`.
`ai-eng spec show 026 --task <n>` refuses any task whose digests have moved.

## What this plan is not doing, and why

- **No CI/CD task and no observability task.** Spec 026 adds no service, no endpoint, no URL:
  a data file, a script, a Justfile recipe. `/ai-plan` requires deployables only; inventing
  the boxes here would be ticked against nothing.
- **No repair of the ~47 real broken references in this block.** The challenge and the
  council both found the spec's numbers move (40 drafted, 47 live). The instrument's first
  honest finding is that the tree holds real broken links; that defect is a separate block
  with its own per-link evidence, named in `spec.md`'s unresolved risk, not bundled here.
- **No change to `.ai/intent.md` or `CONSTITUTION.md`.** This is a tool and a gate step, not a
  change of Solution Intent.

## The boundary this plan may not cross

`sm` is a third-party binary, not part of the wheel. The recipe must work on a machine with
no `sm` (stranger install): the recipe prints "map not exercised; sm missing" and the gate
stays green for the stranger — the check is bracketed so a machine without the tool does not
fail, and the source-tree scan is not a requirement. The map's DB is a sidecar, not a record:
it stays out of the receipt and the commit.

## Tasks

## Block A — the instrument and its honesty (Tasks 1–2)

1. [x] <!--t:0f5343b20a13--> **`sm` is pinned by version and a `map` recipe is defined in the Justfile** —
   **file** `justfile`.
   **check**: `uv run python -c "import sys;from pathlib import Path;s=Path('justfile').read_text();sys.exit(0 if ('sm := ' in s and 'map:' in s) else 1)"`
   **rollback**: `git revert <commit>`.
   **done when**: `justfile` carries a pinned `sm` version the way it pins gitleaks/trivy,
   and a `map`: recipe that runs `sm scan` then `sm check --json`, printing "map not
   exercised; sm missing" when the binary is absent instead of failing the stranger gate.

2. [ ] **The `.venv` copy of the wheel's skills is excluded from the map** —
   **file** the map's root/ignore config so the source tree scans once.
   **check**: `uv run python -c "import sys,subprocess;r=subprocess.run(['sm','list'],capture_output=True,text=True).stdout;sys.exit(0 if '.venv/' not in r else 1)"`
   **rollback**: `git revert <commit>`.
   **done when**: `sm list` names only source-tree nodes, and no `.venv/…/SKILL.md` appears
   as a scanned node.

## Block B — the honest inputs (Task 3)

3. [ ] **The template-hole exclusion and the real-defect acceptance become data the gate reads** —
   **file** `policy/skill-map-exclusions.toml` (new), a dated acceptance record for the ~47
   real broken references under `docs/adr/`, and `tests/test_skill_map.py` (new).
   **check**: `uv run --with pytest python -m pytest -q tests/test_skill_map.py`
   **rollback**: `git revert <commit>`.
   **done when**: the `NNN-slug` pattern is a loaded exclusion list (not a suppression comment
   anywhere), the real broken references are accepted with `--by`, `--expires` and
   `--justification` in a dated record, and the test asserts the template pattern is expected
   rather than failing.

## Block C — the gate step and its wiring (Tasks 4–5)

4. [ ] **The map renders a digest through a check that the template exclusion makes honest** —
   **file** the `map` recipe, calling a small script that runs `sm scan && sm check --json`,
   subtracts the exclusion list, and prints a digest.
   **check**: `just map`
   **rollback**: `git revert <commit>`.
   **done when**: `just map` is a machine-readable digest of the real-vs-template split, and
   a reintroduced real broken reference reddens it while a `NNN-slug` hole does not.

5. [ ] **The whole map is wired into `just check` and the output is shown** —
   **file** `justfile` `check:` recipe (the map step is already in it from the first task;
   today's gate is run and the map step's output shown).
   **check**: `just check`
   **rollback**: `git revert <commit>`.
   **done when**: `just check` includes the map step, the acceptance + exclusion drive its
   green, the output is shown, and `ai-eng spec show 026 --task 5` is green.