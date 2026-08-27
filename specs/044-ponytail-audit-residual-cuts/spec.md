---
id: "044"
slug: ponytail-audit-residual-cuts
status: draft
date: "2026-08-27"
ref: ""
supersedes: ""
---

# Ponytail audit residual cuts

## Who this is for, and what it is worth to them

The maintainer of ai-engineering and every stranger who installs the wheel. Spec 043
removed the mechanically-dead wrappers and consolidated the byte-identical primitives it
could name. What remains after 043 is a second tier of weight the first pass deliberately
or accidentally left: eleven modules shipped and tested that no production file imports,
one register whose whole job is recording that fact, duplicated helper families that
survived with different error arms, function signatures written against their test files
rather than their call sites, and a test suite that re-derives the same fixtures dozens
of times. Today every CI second pays for code no command runs; after this spec the wheel
carries only what a caller reaches, each shared primitive has one home, and the diff a
reviewer reviews is smaller.

## Context and problem

A whole-tree over-engineering audit ran on 2026-08-27 (four independent scans plus a
verification pass; net estimate -1,900 lines src-side). Spec 043 then landed its cut
family on this tree (deletion commits through `fa2fb510`, docs follow-ups after):
`ui.ask`, `skeletons.seed_intent`, the four `_canonical_json` copies, and the
wrappers its challenge withdrew as governance-enclosed. Re-verifying the audit's
remaining findings against today's HEAD leaves three honest classes:
1. **The orphan layer.** Eleven src modules have zero production importers (AST sweep
   over `src/`, `hooks/`, `surfaces/`, `git-hooks/`, `justfile`, `.github/`, re-run
   2026-08-27 on this branch): `constellation`, `decision_fw`, `decision_boundary`,
   `intake`, `trim`, `versions`, `lane_merge`, `loopgate`, `skillify`, `verify_cold`,
   `evidencing`. Each is imported only by its own test module (and small neighbours).
   `policy/module-status.toml` records each as `deferred` or `orchestrator-future` —
   the register exists to give that fact a checked home. A tomllib census on this
   branch reads 19 rows, of which 16 have status ≠ `consumer`: the eleven above plus
   `answer_key`, `coverage`, `skillmap`, `sbom`, and `scan` (the remaining three rows
   name `consumer` modules). Three of those five extra rows are stale, not deletions:
   `sbom`, `scan` and `skillmap` have gate-time callers (`just sbom` runs
   `python -m ai_engineering.sbom`, justfile:47; `just security` imports `scan`,
   justfile:107; `just map` runs `python -m ai_engineering.skillmap`, justfile:268) —
   the audit's own "no module imports it" definition misses `python -m` entry points,
   which is exactly the gap the register's AST definition exists to close. `coverage`
   is likewise alive: `tests/evals/score.py:131` imports it under the `just evals`
   lane. The register's thirteenth true caller-less row is `answer_key`, which dies
   with the eleven. The register's own reader (`wiring.module_status`) has no
   production caller either, and its refusal suite (`tests/test_orphan_register.py`)
   hardcodes three names.
   Research report 020 swept the dynamic-resolver sites for 043's seven targets only;
   its own text names the one loop that matters here, and this spec's build order
   adopts it: `tests/test_036_validation.py` importlib-imports a hardcoded ROWS list
   that includes `verify_cold`, `trim` and `decision_fw`, and
   `tests/test_decision_and_notes.py` statically imports `decision_fw`. Both test
   files die in family (a) with the modules they import — the deletion list is the
   eleven modules plus every test file that imports one of them, enumerated by the
   same AST sweep that proved the imports, not "their own test modules" only.
   The skills corpus names some orphans by module (`trim`, `skillify`, `intake`,
   `loopgate`) and names others only as concepts (`verify_cold` appears as "verify
   this cold"; `constellation` not at all) — a prompt route is not a production
   caller (spec 042's own definition), and the corpus text can keep naming the
   concept while the module that would implement it waits at `git revert` distance.
   The harm: ~650 lines of wheel (src-side total for the eleven) plus their test
   modules run on every gate for nothing a command exercises.
2. **Residual duplication, re-verified against 043's landings.** Still true on this
   branch: five digest-pinned policy loaders (`acceptance`, `capability`, `evidence`,
   `madr`, `outcome`); `acceptance._parse_legacy` re-deriving `text.flat_yaml`
   (text.py:21-39 vs acceptance.py:332-357 — the clone adds the container checks, the
   duplicate-key refusal and the finding/expires gate, so the merge into one home
   must absorb those, error type as parameter); four `git ls-files` readers and five
   `git -C` wrappers (`checkpoint`, `claim`, `madr`, `uninstall`, `doctor`);
   `doctor._run_cli` mirroring `wiring.cli_answers` (same argv, same
   `PYTHONSAFEPATH`, same timeout); the `functools.cache`-shaped `_consoles` memo in
   `ui.py`; the char-loop `_hex` in `uninstall.py` beside a length check that makes
   `re.fullmatch` the native form.
3. **Test-shaped flexibility, dead weight, and three one-caller relics.**
   Zero-caller dead: `verify_cold.verify` takes `allow_write`/`constructor_reasoning`
   only to raise on them; `cost.calibrate`'s single call site passes a hardcoded
   one-sample list and its samples' second field is never read;
   `spec_transaction.publish` returns a `Published` both production callers discard;
   `spec.self_contained`/`_LEAKS`, `model_router.bail_out`, `audit.replay` (the verb
   path calls `_replay` directly at audit.py:549), `answer_key.valid`/`apply` and
   root `answer-key.yaml`. One-caller relics, folded in family (c): `cli.UNEXPECTED`
   (read once inside `crash()`, which `main` calls once), `solution_intent.NOT_HASHED`
   (empty tuple, read once by its own filter), `spec._document_relations` (one-use
   alias re-export). In tests: six hand-rolled JSON-Schema-subset validators, the
   `sys.path.insert + # noqa: E402` idiom in twenty-five pytest modules (fifteen after
   family (a) deletes the ten orphan-importing suites; pyproject `pythonpath`
   replaced it; rule 3 forbids the noqa), a 15-gram-identical lifecycle dict (three
   exact, one with differing dates), near-identical `home`/`machine` fixtures (two
   byte-identical pairs), a GIT-identity env dict ×7, four byte-identical `def git()`
   wrappers plus a fifth that differs, and the `json.loads(json.dumps())` deep-copy
   idiom.
The harm of leaving it: reviewers re-review copies; the gate burns minutes on tests of
unreachable code; and every new module reaches for its own copy of a primitive because
the shared home does not exist.

## Options considered

1. **Apply the residual cuts as ordered, gate-green commit families on one branch
   (chosen).** Order: (a) the orphan layer — delete the eleven modules, every test
   file the same AST sweep shows importing one of them, the register reader
   `wiring.module_status`, `policy/module-status.toml`, and
   `tests/test_orphan_register.py` whose fixture hardcodes three of the deleted
   names; (b) dedup helpers into shared homes (`intent.canonical_json` stays the
   canonical JSON home; one digest-pinned loader; `text.flat_yaml` behind
   `acceptance._parse_legacy` absorbing the container/duplicate-key refusals; one
   ls-files reader; `wiring.cli_answers` behind `doctor._run_cli`); (c) delete
   test-shaped flexibility and the zero-caller constants, folding the three
   one-caller relics into their single callers; (d) migrate the test-suite
   duplication (shared schema reader, conftest fixtures, delete the `noqa: E402`
   idiom). Gives: the wheel shrinks by ~650 src lines plus orphan test mass; each
   primitive one home; rule 3's prohibition enforced in the same commits that shrink
   the suite. Costs: a large diff across ~50 files; risk if a caller was missed
   (mitigated by the AST sweep, report 020's dynamic-import sweep, and per-family
   commits so bisect stays useful).
2. **Cut only the orphan layer; leave duplication and flexibility.** Gives: the
   biggest single win (module-status register becomes empty and can be deleted with a
   clean conscience) at a third of the diff size. Costs: keeps the five digest-pinned
   loaders and the noqa idiom — the classes 043's council already measured as real
   (C-1 verified four byte-identical copies) — and leaves rule 3 violated in fifteen
   files for another cycle.
3. **Defer everything pending an owner decision on the register.** Gives: zero
   governance tension. Costs: preserves 100% of the weight; the audit's findings rot
   exactly as 043's own retraction section documents happening before.

Option 2 loses: the register decision is the same decision for both halves — once the
tree stops shipping caller-less modules, the register's readership drops to its own
test, and keeping the duplication costs what option 1 already pays to remove. Option 3
loses: it is the "keep everything on speculation" answer 043's challenge already
refused.

## Decision

**D-044-01**: Apply option 1. The orphan deletion is a product decision this spec
records and the approval gate authorises: spec 042's register gave every orphan a
checked status precisely so that a later record could reverse it with a command —
`test_a_consumer_must_be_imported_by_a_production_file` enforces the AST definition,
and deletion satisfies the register's own invariant by emptying it. The skill-corpus
module names (`trim`, `skillify`, `intake`, `loopgate`) stay in the corpus — they
describe instruments a future spec may build against the same skill text, and
`git revert` is the reinstatement path; names the corpus never carried
(`verify_cold`, `constellation`) are untouched by this. `loopgate` keeps its mention
in `tests/test_skill_bounds.py` (it asserts the *corpus text* names
the instrument, not the module) — if the corpus keeps the name the test stays green;
if the corpus drops it, that test changes in the same commit.

**D-044-02**: The spec_transaction Windows backend stays, per 043's recorded prudence:
it is a platform arm of spec-010's publication design decision, and its removal
deserves a superseding spec with an owner. Also stays: `imagery.findings` (EP-254's
named evidence), `surface.receipt_binds_version` (EP-016), `executor.Sandbox.connect`
(EP-176's gated path — owner flagged in 043 to wire or remove), everything 043
withdrew as governance-enclosed.

**D-044-03**: Every dedup preserves the public behaviour the gate already holds: same
exit codes, same refusal messages (the contract the suite actually asserts: codes in
one suite, message fragments in another — test_acceptance asserts the code,
test_mut_acceptance asserts fragments with `in str(...)`, nothing holds whole-string
text), same fail-closed arms. Where two error types differ, the shared home
takes the error as a parameter, not a union.

## Challenged once

Strongest realistic failure case: "the orphan modules are the product's roadmap
(specs 030/031/033/034/037/042 cite each as *the* instrument for a planned verb);
deleting them throws away paid-for design work and forces a rewrite when the orchestrator
lands." Answer: the design work lives in the specs and the git history, not in the
bytes — a spec is the record, and `git revert` restores a module's commit family
(module, tests, register row) as one operation.
Keeping ~1,000 lines plus their suites compiled, packaged, linted and tested on every
gate *is* the cost; the roadmap pays it every day until the verbs land, and rule 4
(hard delete, changelog names it) plus rule 5 (delete before you abstract) are the
tree's own answer. The case fails: proceed. One boundary respected: this spec does not
delete `docs/adr/` or any spec — the record layer is untouched.

Second case: "deleting `policy/module-status.toml` breaks `wiring.module_status`
callers you have not grepped." Verified: the reader's only consumer is
`tests/test_orphan_register.py` (five call sites; `tests/test_mut_wiring.py` never
mentions it). It dies with the register in the same commit family.

## Assumptions and unresolved risks

Assumptions:
- Every way this tree can reach a module is covered: the AST import sweep, report
  020's dynamic-resolution sweep (scoped to 043's targets, and itself naming the
  `test_036_validation` ROWS loop this spec now deletes with them), and the
  family-(a) enumeration of every test file importing an orphan. No `pkgutil`,
  `entry_points`, or directory-scan loader exists outside `cli.py`'s closed `VERBS`
  dict and `chain.py`'s closed `TABLE`.
- The gate's baseline is the current green on `main` (b4a525c9). A branch-side run
  today fails `tests/test_one_home.py` (a one-home commit is expected at block close,
  not mid-run); the branch gates at family close on `main` after merge, and any cut
  that turns a test red without deleting that test's subject in the same commit is an
  incorrect cut, not a tree defect.
- Skill corpus prose naming deleted modules stays valid as prose; no test asserts an
  import of a deleted module from skill text.

Unresolved risks:
- A future orchestrator spec (031/041 lineage) may want `lane_merge`/`loopgate` back;
  reinstatement is `git revert` plus re-registration, cost bounded by the specs that
  describe them.
- The corpus/skill tests that name instruments by word (`test_skill_bounds`) are
  text-coupled; a corpus edit in a later commit must move them together.

## Examples somebody can check

**The orphan path.** Given the branch after the orphan family lands, When
`uv run python -c "import ai_engineering.constellation"` runs, Then it prints a
traceback ending in `ModuleNotFoundError` and exits non-zero.

**The register path.** Given the same branch, When
`test ! -f policy/module-status.toml` runs, Then it exits `0` (the file is gone), and
`grep -rn "module_status" src/ --include="*.py"` prints no hits.

**The dedup criterion.** Given all families landed, When
`grep -rn "def _parse_legacy" src/ai_engineering/acceptance.py` runs, Then it prints
exactly one hit whose first line delegates to `text.flat_yaml`; and
`grep -rln "EXPECTED_SCHEMA_DIGEST\|_EXPECTED" src/ai_engineering/*.py | wc -l`
prints `1` or less (one shared pinned-loader home; 043 already reduced
`_canonical_json` to `intent.canonical_json`).

**The noqa criterion.** Given the test-migration family landed, When
`grep -rn "noqa: E402" tests/ --include="test_*.py" | wc -l` runs, Then it prints `0`.

**The gate path.** Given the branch merged and gated on `main` (a multi-home branch
fails `test_one_home` by design mid-run), When `just check` runs at the merge head,
Then the tail reads `0 failed` with the same `passed, skipped` shape the pre-cut
baseline printed (minus the deleted modules' own tests).

**The undecidable path.** Given any module whose reachability the sweeps cannot decide,
When the evidence is ambiguous, Then the module stays, its name appears in the
changelog entry's `### Removed` section as "kept, reason recorded here" — the record,
not a grep, separates "kept after looking" from "never considered".

## Decisions
- [X] **D-044-01 — Delete the twelve true caller-less modules (the eleven plus
      answer_key), every test file importing one of them, and the orphan register
      (reader + data + refusal suite) as one family; correct the stale register rows
      for sbom/scan/skillmap/coverage by deleting those rows, not the modules.**
      **Rationale:** the register exists to make orphan-status checkable; deleting the
      modules satisfies its own invariant; reinstatement is a commit-family revert.
      Promotion-worthy because it constrains any future orchestrator spec: new
      instruments get built *with* their production caller in the same commit, not
      shipped ahead of one.
- [X] **D-044-03 — Shared primitive homes: one digest-pinned loader, `text.flat_yaml`
      behind `acceptance`, one ls-files/git wrapper, `wiring.cli_answers` behind
      `doctor`, `functools.cache` console memo, `re.fullmatch` hex check.**
      **Rationale:** the variation between copies is only the error type, which is a
      parameter; the gate holds codes and message fragments, which the dedup keeps.

## Accepted risks

<!-- none; unresolved risks are recorded above and none is accepted by this record -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command.

- [ ] CI/CD — build, lint, test and security analysis on every push; deploy from the default branch
- [ ] Logs — structured JSON, one line per event, with level and service, to stdout
- [ ] Traces — only if this is our code and has more than one hop; no hop, no trace
- [ ] Errors — every uncaught exception leaves as a log with severity 17 and marks its span
- [ ] Health and data age — alive, age of the newest datum, and an independent recomputation
- [ ] External check — something outside the service verifies it and says what it could not check
- [ ] Second path — every published number recomputed by an independent route and compared
- [ ] Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI
