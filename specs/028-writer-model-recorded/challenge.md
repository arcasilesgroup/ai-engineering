# Challenge — 028 writer-model-recorded

Fork-only critic. Tested every checkable sentence of `specs/028-writer-model-recorded/spec.md`
against the tree at this repository's root on 2026-08-25.

Worst first: WRONG if the tree disagrees, UNPROVEN if nothing in the tree can decide it.

## Findings

### UNPROVEN — the post-implementation examples in "Examples somebody can check"

The three `Given … When … Then` examples describe a state that only exists after the proposed
change is implemented (a `proposed` ADR 0028, a raised `skill_eval` count). Nothing in the
current tree can decide them, and two of the three numbers the tree does show disagree with
the example.

**Sentence 1:** "Given the model is recorded as a proposed ADR and committed, When a reader
runs `ai-eng decide --list`, Then the output contains `0028` with status `proposed`."
Command: `uv run ai-eng decide --list 2>&1 | tail -12`
Output:
```
  0021-specification-023-is-approved-at-exact-digests accepted  ← superseded by 0023, which says so
  0022-a-council-may-conclude-and-ep-195-stays-open accepted
  0023-specification-023-is-re-approved-at-its-corrected-digests accepted
  0024-specification-026-and-its-plan-are-approved-at-exact-digests accepted
  0025-the-maps-real-broken-references-are-accepted-as-a-dated-record accepted
  0026-specification-027-and-its-plan-are-approved-at-exact-digests accepted
  RUNNING 3/4  report the outcome
✓ PASS … Exit code: 0
```
The listing ends at `0026`; there is no `0028`. Because the example is conditioned on the
recording being implemented (it is not), this is UNPROVEN, not WRONG.

**Sentence 2:** "Given `docs/adr/0028-*.md` exists with `status: "proposed"`…"
Command: `ls docs/adr/`
Output: 26 entries, `0001-…` … `0026-specification-027-and-its-plan-are-approved-at-exact-digests.md`.
No `0028-*.md` exists. UNPROVEN (post-implementation conditional; the file is absent because
the change is not implemented).

**Sentence 3:** "When `uv run python tests/skill_eval.py` runs, Then it exits 0, prints
`RAN skilleval=350`, and the baseline in `policy/pilot-register.toml` was moved to `350`…"
Command: `uv run python tests/skill_eval.py > /tmp/skilleval.out 2>&1; echo exit=$?; tail -3 /tmp/skilleval.out`
Output:
```
exit=0
  receipt: .ai/receipts/skill-evaluation.json
RAN skilleval=349
  baseline 349, delta +0, margin 0
```
It exits 0, but prints `RAN skilleval=349`, not `350`; `policy/pilot-register.toml` still
records `measured = 349`. The example's post-change value is not present in the tree, so it
is UNPROVEN (the +1 movement is the proposed effect, not a current fact).

### UNPROVEN — `ai-eng decide --madr`

**Sentence (Options 1 / Decision / D-028-02):** "`ai-eng decide --madr` writes a `proposed`
ADR that grants nothing."
Command: `uv run ai-eng decide --help`
Output:
```
usage: ai-eng decide [-h] [--supersede NNNN] [--list] [--accept NNNN] [--spec SPEC] [title]
options:
  -h, --help
  --supersede NNNN
  --list
  --accept NNNN     accept a proposed MADR
  --spec SPEC       which spec it belongs to; needed when more than one is open
```
The current CLI has no `--madr` flag (the proposed ADR-writing path is the positional
`title`). Since the flag is introduced by the not-yet-implemented change, nothing in the tree
can decide it, so this is UNPROVEN. Supporting fact: `policy/madr-v1.schema.json` line 20 sets
`"initial": "proposed"`, and proposed→accepted/rejected are the only transitions, so the
schema-side claim ("proposed grants no authority") holds — see the PASS below.

### PASS — the three current truth claims about the intent

**Sentence:** ".ai/intent.md, approved digest `ae523990` … fixes: 'Until a separately
approved P3 plan proves safe coordination, one writer owns repository changes.'"
Command: `read .ai/intent.md`
Output: `"approval_ref": "ae523990"` and under `fixed_constraints` exactly:
`"Until a separately approved P3 plan proves safe coordination, one writer owns repository
changes."` PASS.

### PASS — `policy/skill-sequence.toml` `[parallel]` and `[gate]`

**Sentence:** "its `[parallel] policy` is 'fork contexts only; task-level parallelism inside
ai-build per the approved plan', and its `[gate] approval` requires 'a human approval record
carrying the specification's exact digest'."
Command: `read policy/skill-sequence.toml`
Output: `policy = "fork contexts only; task-level parallelism inside ai-build per the approved
plan"` and `approval = "a human approval record carrying the specification's exact digest"`.
Both verbatim. PASS.

### PASS — `.agents/skills/ai-build/SKILL.md` step 1

**Sentence:** "`.agents/skills/ai-build/SKILL.md` step 1: 'Take the task, not the plan… It refuses when that
digest no longer matches the file on disk… If the task is not in a plan, or the plan is not
approved, stop here: nothing to execute.'"
Command: `read .agents/skills/ai-build/SKILL.md`
Output: step 1 reads "Take the task, not the plan: `ai-eng spec show <id> --task <n>` prints it
with the file, the check, the rollback and the digest of the plan it came from. It refuses
when that digest no longer matches the file on disk, which is the approval saying so. If the
task is not in a plan, or the plan is not approved, stop here: nothing to execute." PASS. Step 7
and "Done when" also confirm the agent "never … approved by the same hands that wrote it",
matching "stops before publishing or approving".

### PASS — spec 013 is a draft and records the P3 formula

**Sentence:** "`specs/013-origin-first-coordination/spec.md` (draft) records the future P3
target: 'One task, one work item… One remote branch, one worktree, one writer. Reviewers may
be many; writers may not.'"
Commands: `read specs/013-origin-first-coordination/spec.md` head + `grep -n "One task…"`.
Output: frontmatter `status: draft`; lines 137–138 verbatim:
```
- **One task, one work item.** The work-item ID is opaque and non-personal.
- **One remote branch, one worktree, one writer.** Reviewers may be many; writers may not.
```
PASS.

### PASS — `merge_group` trigger exists

**Sentence:** "The `merge_group` trigger already exists in `.github/workflows/check.yml`."
Command: `read .github/workflows/check.yml`
Output: under `on:` — `push:`, `pull_request:`, and `merge_group:` are present in the workflow
(yaml `on:` block). PASS.

### PASS — coordination-shape guards exist

**Sentence:** "The coordination shape is guarded: `tests/test_coordination_shape.py` refuses
bare force, background rebase, per-commit publish, an ownership store, a heartbeat and a TTL
takeover."
Command: `grep -n "" tests/test_coordination_shape.py`
Output: `test_no_bare_force_push_exists_anywhere_the_product_can_run_it` (bare force),
`test_nothing_rebases_in_the_background_or_publishes_every_commit` (background rebase +
per-commit publish), `test_no_ownership_store_no_heartbeat_and_no_ttl_takeover` (ownership
store/heartbeat/TTL takeover), plus `test_a_coordination_record_carries_only_the_fields_it_is_allowed`
and `test_the_claim_module_names_no_second_writer_of_ownership` (one-writer). All six shapes
are guarded by tests. PASS.

### PASS — the gate is red in four `test_madr.py` failures, documented in `.ai/reports/014`

**Sentence:** "the gate (`just check`) is currently red in four `tests/test_madr.py` failures
caused by ADR 0025 of spec 026, whose state lives in git history — a known, dated acceptance
documented in `.ai/reports/014`."
Command: `uv run --with "rich>=13,<16" --with "questionary>=2,<3" --with "pytest>=8,<9" python -m pytest tests/test_madr.py -q`
Output:
```
4 failed, 33 passed in 27.51s
FAILED tests/test_madr.py::test_intent_supersession_madr_is_complete - AssertionError: assert 'INCOMPLETE' == 'PASS'
FAILED tests/test_madr.py::test_mission_madr_has_options_risks_and_owner - AssertionError: assert 'INCOMPLETE' == 'PASS'
FAILED tests/test_madr.py::test_cli_madr_has_hard_rename_and_transition_evidence - AssertionError: assert 'INCOMPLETE' == 'PASS'
FAILED tests/test_madr.py::test_madr_final_repro_discovery_is_conservative - AssertionError: assert 'INCOMPLETE' == 'PASS'
```
Exactly four failures, all repository-wide `madr.validate(...) == PASS` assertions. Direct probe,
`uv run python -c "... madr.validate(Path('.'))"` prints `INCOMPLETE | MADR_SCHEMA_INVALID |
frontmatter does not match MADR v1`. The attribution to ADR 0025 is documented in
`.ai/reports/014-027-build-not-green.html`, which states "La puerta completa de `just check`
sigue roja en cuatro tests de madr, y ese rojo es el registro 0025 de 026" (verified by reading
the file). PASS for the four-failure count; the "ADR 0025" attribution rests on that report — I
could not independently name the offending history commit.

### PASS — AGENTS.md rule 12

**Sentence:** "The third time it resolves the same way it should be a script (`AGENTS.md` rule
12)."
Command: `grep -n "rule 12" AGENTS.md`
Output: line 26 — `12. A decision that always comes out the same is code, not a prompt. The
third time the …`. PASS.

### PASS — `skill_eval` current baseline is 349 (the "+1 → 350" cost is consistent)

**Sentence (Options 1, costs):** "the refusal count in `tests/skill_eval.py` rises by one,
with `policy/pilot-register.toml` baseline moved and argued."
Commands: `grep -n skilleval policy/pilot-register.toml` → `[[baseline]] id = "skill-routing",
measured = 349, margin = 0`; and `uv run python tests/skill_eval.py` → `RAN skilleval=349 /
baseline 349, delta +0, margin 0`. The current measured count is 349, so the stated "+1 → 350"
effect is consistent with the tree. PASS (as a statement about the unrecorded baseline; the +1
is the proposed effect).

### PASS — the `ai-goal` corpus has no route/refusal for recording the model

**Sentence:** "the one skill that routes by it (`ai-goal` corpus) gains a labelled refusal for
the case that currently has no route" and the conflict claim that `ai-goal` "runs the whole
cycle".
Command: `read .agents/skills/ai-goal/corpus.md`
Output: first line "Runs the whole governed cycle in one pass…"; `## Routes here` (5 routes) and
`## Refuses` (6 refusals) are listed; none covers recording the writer model as an ADR or
decision record. So the case "currently has no route" and the claimed conflict phrase exists.
PASS.

### PASS — `proposed` is the schema's non-authorizing state

**Sentence (D-028-02 / rationale):** "`proposed` is the schema's non-authorizing state".
Command: `grep -n proposed policy/madr-v1.schema.json`
Output: line 20 `"initial": "proposed"`; transitions allowed only `proposed→accepted` and
`proposed→rejected`; status enum includes `proposed`. A `proposed` ADR can only advance via an
explicit `--accept`, so it grants no authority. PASS.

### PASS — frontmatter of spec 028 itself

`id: "028"`, `slug: writer-model-recorded`, `status: draft`, `date: 2026-08-25` — matches the
tree's own "measured in this tree on 2026-08-25". PASS (by reading the spec).

## What I could not test

- `just check` itself. The spec's sentence names `tests/test_madr.py` failures, so I ran that
  file rather than the whole gate. The plain `uv run pytest tests/test_madr.py` in the default
  uv environment fails to even collect with `ModuleNotFoundError: No module named 'rich'`
  (37 errors) because `rich`/`questionary` are declared in `pyproject.toml` but not installed in
  the project's uv environment here; I reproduced the four failures by supplying them with
  `--with rich --with questionary --with pytest` and running `python -m pytest`. In CI the gate
  installs them, so the number "four failures" is the meaningful fact.
- The precise originating commit/ADR that makes `madr.validate` return
  `MADR_SCHEMA_INVALID / frontmatter does not match MADR v1`. My per-ADR `_parse` probe on every
  file in `docs/adr/` in the worktree raised no schema problem, so the failing snapshot comes
  from git history (as the spec says: "whose state lives in git history"). I could not name
  `0025` independently; I relied on `.ai/reports/014`, which does name it.
- The binary outcomes of the three `Given/When/Then` examples and the `--madr` flag: they
  describe the change this draft spec proposes but does not implement, so nothing in the tree
  decides them (2 of the tree's current numbers, `skilleval=349` and the `decide --list` tail at
  0026, disagree with the examples' `350` and `0028` — but that is expected pre-implementation,
  hence UNPROVEN rather than WRONG).
- The content of `.ai/reports/015` (only its existence was checked:
  `015-origin-first-multiagente-viabilidad.html` is present), so the assumption that its reader
  "accept[s] that one writer today, parallel P3 as the gated future is the true model" was not
  verified against the report body.
- Interpretive sentences with no observable referent in the tree: "the model is a single
  writer — the invoked agent", "the third identical verdict stays a prompt instead of a record",
  "nothing is authorized", the "ventory" of who reads `/ai-goal`, and the empty `## Accepted
  risks` block (no requirement either way).
