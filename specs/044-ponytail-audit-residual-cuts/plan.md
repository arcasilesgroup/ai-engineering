# Plan: ponytail audit residual cuts — 044 ordered execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and
this exact `plan.md`**, recorded at their digests in their own record. One repository
writer, on one branch carrying the whole 044 change. Each task is one atomic commit;
rollback for every task is `git revert <commit>` — which, per the council's corrected
sentence, restores the whole commit family of a cut (module, its tests, its register
rows), not a single file.

**This plan is not edited while it is executed.** The spec digest at approval time is:

| file | SHA-256 |
|---|---|
| `specs/044-ponytail-audit-residual-cuts/spec.md` | `b213c1d7d7660b93df7c82960526e3ba447ad18ca4310cee4fc51ab476808d5d` |

## The order, and why

Families land smallest-blast-radius first. Family (a) deletes the twelve true
caller-less modules (the eleven orphans plus `answer_key`) with every test file the AST
sweep shows importing them, the register reader, the register data, and the refusal
suite — the council's corrections are baked in: `sbom`, `scan`, `skillmap` and
`coverage` keep their modules and lose only their stale register rows (they have
gate-time callers: justfile:47,107,268 and tests/evals/score.py:131). Family (b) dedups
the shared primitives, (c) removes the zero-caller constants and folds the three
one-caller relics, (d) migrates the test-suite duplication and kills the `noqa: E402`
idiom. The critique after build reads the whole branch as one diff.

## What this plan is not doing, and why

- **No cut of `sbom`, `scan`, `skillmap`, `coverage`.** The register rows saying
  `consumer = ""` are stale; the gate-time callers are named above. Only the rows and
  the census prose are corrected.
- **No cut of the spec_transaction Windows backend** (D-044-02: spec-010's platform
  arm; a superseding spec with an owner is the vehicle). No cut of `imagery.findings`
  (EP-254), `surface.receipt_binds_version` (EP-016), `executor.Sandbox.connect`
  (EP-176, owner flagged in 043).
- **No new dependencies, no new verbs, no justfile recipe changes** except where a
  family must re-point a recipe at a renamed helper (none is known today).
- **No behaviour change in any refusal path** (D-044-03): exit codes identical,
  messages preserved — the suite holds codes and fragments, and both survive.
- **No change to `.ai/intent.md`, `CONSTITUTION.md`, `docs/adr/`, or any spec file.**
- **No CI/CD box ticked.** The production-ready section stays unticked; this change
  adds no service.

## Tasks

1. [ ] **Family (a): delete the orphan layer** —
   **file** `src/ai_engineering/{constellation,decision_fw,decision_boundary,intake,
   trim,versions,lane_merge,loopgate,skillify,verify_cold,evidencing,answer_key}.py`
   (twelve modules) + test files importing any of them:
   `tests/test_{constellation,lane_merge,loopgate,trim,skillify,versions,cold_read,
   recheck,037_intake,036_boundary,036_validation,decision_and_notes,answer_key,
   orphan_register}.py` + `policy/module-status.toml` + `src/ai_engineering/wiring.py`'s
   `module_status()` (reader + its policy import if now unused) + the stale rows'
   absence handled by the file deletion itself (register file is deleted whole).
   `tests/test_skill_bounds.py` survives — it asserts corpus *text* naming `loopgate`,
   which stays. `tests/test_contracts.py` is checked for rows referencing the register
   or `wiring.module_status` and adjusted in this commit if it reads them.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_contracts.py tests/test_skill_bounds.py && grep -rn "module_status\|answer_key\|loopgate\"" src/ai_engineering/wiring.py | wc -l`
   **rollback**: `git revert <commit>`.
   **done when**: `python -c "import ai_engineering.constellation"` exits non-zero with
   `ModuleNotFoundError`; `test ! -f policy/module-status.toml` exits `0`; the named
   check suites are green.

2. [ ] **Family (b): one digest-pinned policy loader** —
   **file** `src/ai_engineering/` modules carrying `_EXPECTED*_DIGEST` readers
   (`acceptance.py`, `capability.py`, `evidence.py`, `madr.py`, `outcome.py`) + the
   shared home (new function beside `intent.canonical_json` in `intent.py` or a new
   `policy_reader` helper — the smaller diff wins) + affected test files.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_acceptance.py tests/test_capabilities.py tests/test_evidence.py tests/test_madr.py tests/test_outcomes.py`
   **rollback**: `git revert <commit>`.
   **done when**: `grep -rln "EXPECTED.*DIGEST" src/ai_engineering/*.py | wc -l` ≤ 1;
   all five suites green; refusal messages byte-identical on the fragments the
   mutation suite asserts.

3. [ ] **Family (b): acceptance._parse_legacy delegates to text.flat_yaml** —
   **file** `src/ai_engineering/acceptance.py` (the shared home absorbs the container
   checks, duplicate-key refusal and finding/expires gate; error type as parameter per
   D-044-03) + `src/ai_engineering/text.py` if the refusals need new optional
   arguments + `tests/test_acceptance.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_acceptance.py tests/test_text.py`
   **rollback**: `git revert <commit>`.
   **done when**: `_parse_legacy`'s body is a thin call into `text.flat_yaml`; the
   refusal tests stay green unchanged.

4. [ ] **Family (b): one ls-files reader, one git wrapper, cli_answers behind doctor** —
   **file** `src/ai_engineering/{doctor,contract,evidence,madr}.py` (ls-files),
   `src/ai_engineering/{doctor,checkpoint,claim,madr,uninstall}.py` (git -C argv
   builder where the return contracts allow; per 043's ruling, runners with differing
   return contracts stay separate — the shared piece is argv+env+timeout only),
   `src/ai_engineering/doctor.py` (`_run_cli` calls `wiring.cli_answers`) +
   affected tests.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_doctor.py tests/test_checkpoint.py tests/test_claim.py tests/test_madr.py tests/test_wave.py`
   **rollback**: `git revert <commit>`.
   **done when**: one ls-files helper exists; `doctor._run_cli` is a two-line wrapper;
   the five suites green.

5. [ ] **Family (c): delete zero-caller dead weight, fold the one-caller relics** —
   **file** `src/ai_engineering/spec.py` (`self_contained`+`_LEAKS` die with
   `tests/test_spec_containment.py`; `_document_relations` inlines at its one use),
   `src/ai_engineering/model_router.py` (`bail_out` + its test),
   `src/ai_engineering/audit.py` (`replay` wrapper; the verb path already calls
   `_replay`), `src/ai_engineering/cli.py` (`UNEXPECTED` alias inlined),
   `src/ai_engineering/solution_intent.py` (`NOT_HASHED` inlined into the filter),
   `src/ai_engineering/answer_key.py` already gone in task 1, `answer-key.yaml`
   (root sample, read by nothing), `src/ai_engineering/verify_cold.py` already gone,
   `src/ai_engineering/cost.py` (`calibrate` drops `threshold_usd`/`interactive` if
   the single call site confirms; `_Policy` collapses to a validated dict), and
   `spec_transaction.publish`'s `Published` return dropped if both call sites stay
   return-blind.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_spec_containment.py tests/test_record.py tests/test_cli_migration.py tests/test_solution_intent.py tests/test_cost_gate.py tests/test_spec_transaction.py -k "not windows"`
   **rollback**: `git revert <commit>`.
   **done when**: each named symbol greps zero in src/; the suites stay green; the
   Windows backend untouched.

6. [ ] **Family (d): kill the `noqa: E402` idiom in test modules** —
   **file** the 15 surviving test modules carrying `sys.path.insert(ROOT/"src")` +
   `# noqa: E402` (pyproject `pythonpath = ["src","hooks","tests"]` already covers
   them) + `tests/evals/score.py` and `tests/test_evals_harness.py` only if their
   inserts are also redundant (standalone scripts like `pilot_register.py` keep theirs
   — they run without pytest).
   **check**: `grep -rn "noqa: E402" tests/ --include="test_*.py" | wc -l` prints `0`,
   then `uv run --with pytest==9.1.1 pytest -q tests/ -x -k "contract or skill_bounds or evals_harness"`
   **rollback**: `git revert <commit>`.
   **done when**: the grep count is `0` and the spot suites are green.

7. [ ] **Family (d): shared test fixtures and the schema reader** —
   **file** `tests/conftest.py` (promote `home`/`machine`/`repo` fixtures),
   a shared `tests/schema_reader.py` for the six JSON-Schema-subset validators, the
   lifecycle-dict helper `activate_intent(root)`, `git_identity_env()` +
   `tests/test_{acceptance,madr,intent,evidence,capabilities,outcomes,cli_migration,
   mut_spec,record,install,mut_init,cli_modes,doctor,mut_wiring,mut_uninstall_owned,
   model_event,checkpoint,claim,merge_gate,wave,spec_marker,stranger_install,
   quality_gate,hooks}.py` (the import-site changes).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/`
   **rollback**: `git revert <commit>`.
   **done when**: the suite is green, the six validators import one reader, the
   four-site lifecycle literal is one helper, and `grep -rn "json.loads(json.dumps"
   tests/ --include="test_*.py" | wc -l` reads 0 in the files touched.

8. [ ] **Block close: the gate over the whole branch** —
   `just check` at the head commit on this branch, output shown in full; the
   `test_one_home` expectation satisfied because this is the block-close run where the
   branch's multi-home history is the point (if the recipe refuses the branch shape,
   merge to `main` and gate there, per the spec's gate-path example).
   **file**: none — this task runs the gate and reports; every tree change it needs
   already landed in tasks 1-7.
   **check**: `just check`
   **rollback**: n/a — reporting task.
   **done when**: the gate's tail reads `0 failed` (suite count reduced by the deleted
   suites) and every other recipe in `check` is green.
