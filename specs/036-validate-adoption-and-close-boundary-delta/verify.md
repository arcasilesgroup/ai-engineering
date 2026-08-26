# Verify — spec 036 (validate adoption and close the boundary delta)

Verification by the ai-verify skill contract, run 2026-08-26 on commit `3a93e396`
(47ec9093..HEAD, the 036 build). Nothing here accepts anything; this reports and a person
or gate decides. `ai-eng spec checkpoint 036` returned **INCOMPLETE** (no claim receipt for
this code) — read alongside the runs below.

## The gate, as CI runs it: `just check`

Pasted tail (full run in the check chain; `cover` is where the authorized red lands, and
`just check` stops there by design — every recipe before it passed):

```
uv run --with pytest==9.1.1 --with pytest-xdist[psutil]==3.8.0 pytest -q -n auto -k "not fast_enough"
…
=========================== FAILURES ===================================
__________________ test_intent_supersession_madr_is_complete ___________________
    def _repository_madrs_validate() -> None:
…
>       assert madr.validate(ROOT).outcome == "PASS"
E       AssertionError: assert 'INCOMPLETE' == 'PASS'
E         - PASS
E         + INCOMPLETE
FAILED tests/test_madr.py::test_intent_supersession_madr_is_complete - AssertionError: assert 'INCOMPLETE' == 'PASS'
FAILED tests/test_madr.py::test_mission_madr_has_options_risks_and_owner - AssertionError: assert 'INCOMPLETE' == 'PASS'
FAILED tests/test_madr.py::test_cli_madr_has_hard_rename_and_transition_evidence - AssertionError: assert 'INCOMPLETE' == 'PASS'
FAILED tests/test_madr.py::test_madr_final_repro_discovery_is_conservative - AssertionError: assert 'INCOMPLETE' == 'PASS'
4 failed, 2353 passed, 2 skipped in 55.43s
error: recipe `cover` failed with exit code 1
GATE_EXIT=1
```

The 036 fixtures ran inside `cover`'s pytest and are part of the 2353 passed (verified
separately: `pytest -q -k "not fast_enough and (036)"` → `7 passed`; the 6 036 tests collect
and pass in the `not fast_enough` half). The **only** failures are the four inherited
`tests/test_madr.py` ADR 0025 reds (`INCOMPLETE` vs `PASS`). Reproduced at the base commit
`47ec9093`: `pytest -q tests/test_madr.py` → `4 failed, 33 passed` — the identical 4, so the
036 build adds **no fifth failure**.

Because `cover` stops the chain, the recipes after it in `just check` (security register
skilleval evals counts intent-page lenses council map ran) never ran as part of the gate. I
ran each individually below and against the base commit to separate the 036 build's effect
from the inherited state.

## Production-ready boxes

| Box | Command that proves it | Output | Verdict |
|---|---|---|---|
| CI/CD | `just check` (workflow `.github/workflows/check.yml` runs it on every push) | Gate ran to `cover`; 6 036 fixtures pass inside `cover`'s pytest; no deployment, nothing served | **PASS** (fixtures run in the gate; the inherited madr red stops the chain, not added by 036) |
| Logs | `not applicable` — 036 adds a pure stdlib module (`decision_boundary.py`) and two fixtures; adds no verb, no service, no log-writing path; every verb still emits the one JSON line `ai-eng digest` reads | — | not applicable |
| Traces | `not applicable` — 036 adds one process, no second hop, no network, no trace surface | — | not applicable |
| Errors | Fail-closed proof only: `uv run --with pytest==9.1.1 pytest -q tests/test_036_boundary.py -k undecidable` | `1 passed, 4 deselected` — out-of-declaration returns `None`, `U1`, `blocks=True`; never coerced into a guessed class (`test_never_coerces_an_undecided_class` in the same file) | **PASS** (spec marks the box not applicable; the fail-closed behaviour is proven green by the fixture) |
| Health and data age | `uv run --with pytest==9.1.1 pytest -q tests/test_036_boundary.py tests/test_036_validation.py` and `uv run python tests/skill_eval.py` | `5 passed` `0.04s`; `1 passed` `0.04s`; `RAN skilleval=368 / baseline 368, delta +0, margin 0`; both fixture files run in `just test`/`cover` on every gate | **PASS** |
| External check | `.github/workflows/check.yml` runs `just check` on every push (read: the gate step `just check \| tee …` is present, not conditioned on event); corpus cases ride the generic `skill_eval.py` routing lane | skill_eval → `RAN skilleval=368` (baseline 363→368, reason written into `policy/pilot-register.toml` in the same commit); workflow verified unchanged by the 036 diff (only 8 files, no workflow file) | **PASS** (independent reader counted the new corpus cases) |
| Second path | `uv run --with pytest==9.1.1 pytest -q tests/test_036_boundary.py tests/test_036_validation.py` and `uv run python tests/skill_eval.py` | `decision_boundary` read by its fixture (5 passed); corpus rows read by `skill_eval.py` (368) with no shared line; `test_036_validation.py` is the independent reader over the validated modules (1 passed) | **PASS** |
| Security | `just security` | **FAIL locally** — gitleaks flags `.skill-map/serve.json` (a locally generated scan artifact, gitignored, untracked); semgrep reports on `answer_key.py`, `cost.py`, `evidencing.py`, `verify_cold.py`, `.skill-map/serve.json`. None of these files is in the 036 diff (verified: 0 commits in 47ec9093..HEAD touch any of them) and all fail identically at the base commit `47ec9093`. The change adds no dependency and no network call | **INCOMPLETE** — the security lane is not green in this tree; the reds are provably pre-existing/environmental (identical at base, files untouched by 036). The box is not ticked by this run |

Security detail for the record — the following were found identically at base and HEAD, so
they are inherited, not introduced by 036:

- `just security` → exit 1: `FAIL secrets` gitleaks `generic-api-key` on `.skill-map/serve.json:9` (untracked local scan DB, gitignored; `git check-ignore` confirms); `INCOMPLETE semantic` semgrep on `answer_key.py:152`, `cost.py:40/93`, `evidencing.py:40/67`, `verify_cold.py:28`. `--with semgrep==1.172.0` is the pinned version.
- `just security` at base `47ec9093` → exit 1, same findings.
- `tests/adversarial/run.py` (the CI `suite` job) → `21 of 21 — green, RAN suite=21` (this is the part of `cover` after pytest which the gate never reached).

Other gate recipes run individually (after `cover`), with the same run at base for the
reds:

| Recipe | HEAD | Base | Verdict |
|---|---|---|---|
| `just security` | exit 1 (above) | exit 1 (same) | pre-existing red |
| `just register` | exit 0, `RAN register=33` | exit 0, `RAN register=33` | PASS |
| `just skilleval` | exit 0, `RAN skilleval=368`, baseline 368 delta +0 | exit 0, `RAN skilleval=363`, baseline 363 delta +0 | PASS (baseline moved 363→368 with reason) |
| `just evals` | exit 1 — `tests/evals/plant.py:49 ValueError: defect t3-secret-mask: 'find' not present in src/helper.py` (`src/helper.py` does not exist in the tree) | exit 1 (identical traceback) | pre-existing red |
| `just counts` | exit 0, `RAN lint=350`, `RAN tests=2360` | — | PASS |
| `just intent-page` | exit 1 — `docs/solution-intent.html` built from `263f22d68d48`; tree hashes to `e97fcf2e95a6` (needs regeneration) | exit 1 (same, older hash) | pre-existing red |
| `just lenses` | exit 0, nothing routed | — | PASS |
| `just council` | exit 0, `RAN council=25/22` | — | PASS |
| `just map` | exit 1, `REAL_AND_UNACCEPTED=158` | exit 1, `REAL_AND_UNACCEPTED=26` | pre-existing red (count delta is a local `.skill-map` scan-DB artifact over untracked `.ai/research` files; 18 real-and-unaccepted pairs are common to both runs, none names a 036 file) |
| `just guards` (mutation lane, its own CI job) | refuses to score — `mutation.py:387` "X is red before any mutant… Fix that first" because the suite half includes the inherited madr red | identical (same inherited red at base) | authorized-inherited red |

## Examples somebody can check

Counts from `ai-eng spec show 036`: **5 given, 5 when, 5 then, 1 naming a command and its
output** (the skill says an example names a command, and 1 of the Below annexes a `→
<count>`; the columns an example needs are in `ai-review/references/testing.md`, which
exists).

| Example | Command (as the example names it) | Output | Verdict |
|---|---|---|---|
| **Success, classified** — "returns `Always`, `Ask-first` or `Never` deterministically" (`→ 2 passed`) | `uv run --with pytest==9.1.1 pytest -q tests/test_036_boundary.py` | `5 passed in 0.04s` | **PASS** — the Then's behavioural claim (deterministic Always/Ask-first/Never) holds exactly; the example's `→ 2 passed` count is stale (the shipped fixture carries 5 tests); the spec itself says the counts are "the goal, not a claim". Count difference is a finding for `/ai-spec`, not a failure. |
| **Denial, out-of-declaration** — "returns `None`, reports `CANNOT DECIDE`, and blocks — it never guesses" (`→ 1 passed`) | `uv run --with pytest==9.1.1 pytest -q tests/test_036_boundary.py -k undecidable` | `1 passed, 4 deselected in 0.03s` | **PASS** (matches) |
| **Corpus, parseable shape** — "the routing lane counts the new cases and the baseline moves with its reason in the same commit; a refusal written only in `corpus.md` is not counted — the fixture proves the red half" | `uv run python tests/skill_eval.py` | `RAN skilleval=368 baseline 368 delta +0 margin 0`; the boundary hand-off `deciding a request that falls outside a declared boundary — report CANNOT DECIDE and block …` is counted in the routing output; baseline 363→368 moved in commit `7109fc96` with the reason recorded in `policy/pilot-register.toml`; the red half is proved by `test_a_corpus_row_that_is_not_a_quoted_case_is_skipped_and_not_guessed_at` (a `Not for` refusal written into `corpus.md` — an unquoted row — is skipped and never counted; the empty-target send is also skipped by `problems()`'s `if not target: continue`) | **PASS** |
| **Validation stays true** — "every module exists with its contract symbol and responsibility, and deleting one fails the check with the reason" (`→ 1 passed`) | `uv run --with pytest==9.1.1 pytest -q tests/test_036_validation.py` | `1 passed in 0.04s` (asserts all 7 rows' modules + symbols + provenance markers) | **PASS** (matches) |
| **Tree stays green** — "the gate proves it clean with the same inherited `madr.validate` red and no fifth failure" ("When `just check` passes") | `just check` | exit 1: exactly the 4 inherited `test_madr.py` reds (ADR 0025), `4 failed, 2353 passed, 2 skipped`, no fifth failure | **INCOMPLETE** — the precondition "When `just check` passes" is not observed (the gate exits 1 on the authorized inherited red, as it does at the base commit). The Then's substance is confirmed two ways: the red set is byte-identical to base (same 4, no fifth), and every other recipe passes or is a provably pre-existing environmental red. The gate is not green in this tree, so this example is not a pass and not a failure — it is the undecided case, reported separately. |

### Undecided, counted separately

1. **Tree stays green** (example 5 above) — the gate does not exit 0, so "When `just check`
   passes" is never observed; the no-fifth-failure claim holds but the example cannot be
   marked PASS or FAIL as written.

## What this verification did not accept

- Nothing here is accepted. Five boxes ticked by commands (CI/CD, Errors-fail-closed,
  Health/data age, External check, Second path); Logs and Traces are
  `not applicable` per the spec's own rule (no service, one process, one JSON line);
  **Security is INCOMPLETE** because `just security` is not green in this tree (reds are
  provably pre-existing and none touches a 036 file).
- One example is undecided (**Tree stays green**) because `just check` does not pass here —
  the inherited ADR 0025 red blocks it, identically at the base commit.
- The count deltas in the Success example (`→ 2 passed` vs actual `5 passed`) and the
  `map` REAL line count (26 vs 158, a local-scan artifact) are recorded as findings, not
  repaired. The `evals` red (`src/helper.py` missing) and `intent-page` red (stale HTML)
  predate 036 and are reported, not fixed.

## Findings recorded for `/ai-spec`, not repaired (per the skill: a Then that turned out
wrong is a finding, and rewriting it here is marking your own paper)

1. **Success example's `→ 2 passed` is stale.** The shipped fixture carries five tests
   (`5 passed`); the example was written for the two-test red shape. Behavioural Then
   holds; only the count annotation differs.
2. **Commit 7109fc96's message says "baseline 363 to 369"; the landing value is 368.**
   The intermediate commit wrote `measured = 369`; the next commit (8ccae280, "baseline
   368 with stated three-surface routing") corrected it. The final tree is consistent:
   register `measured = 368`, live run `RAN skilleval=368`, `baseline 368, delta +0`.
3. **The register note's decomposition is inconsistent with the live run.** The note in
   `policy/pilot-register.toml` says "Situations routed 81 to 81, hand-offs 42 to 42,
   labelled cases 240 to 245 — … 81+42+245 is 368" while the live `skill_eval.py` run
   prints "81 situations and hand off 44 more, measured against 243 labelled cases —
   118 a skill must take, 125 it must refuse" (81+44+243 = 368). Both totals agree at
   the enforced number 368; the parts disagree on how the total is decomposed.

## Done-when

- Every box carries a command and its output, or `not applicable`, or `INCOMPLETE` — yes.
- Every example carries a verdict, and the undecidable one is counted separately — yes
  (Tree stays green).
- Nothing was accepted — yes.