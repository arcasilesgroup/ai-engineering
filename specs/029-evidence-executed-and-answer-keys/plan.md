# Plan: evidence executed and answer keys — 029 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and this
exact `plan.md`**, recorded at their digests in their own record. One repository writer, on a
branch carrying the whole 029 change. Each task is one atomic commit touching one primary
production, policy or skill file plus only the files that task names. Rollback for every task
is `git revert <commit>`.

**This plan is not edited while it is executed.** Every commit runs the whole gate in the same
chain as the commit itself. `ai-eng spec show 029 --task <n>` refuses any task whose digests
have moved.

## The order, and why

Measurement before the artefact it informs (the research's own ordering). The evals harness
(B-029-1) lands first — it is the instrument that will later score the answer-key consumer
and the recheck semantics, and a red control must exist before any of the new behaviours is
shipped. Then the recheck semantic (B-029-3) because *both* the answer key and the evals
consume "claimed is not passed". Then the answer key (B-029-2), which needs recheck to
execute. Then the cost calibration gate (B-029-4), which protects the now-expensive lanes
the first three tasks make runnable. The final task proves the whole gate with the four new
controls green along with their clean controls.

Each task starts with its **red fixture** (the test or control that fails before the
implementation exists), implemented in the same commit as the behaviour, exactly as
`tests/adversarial/run.py` and the mutation harness already arrange their controls.

## What this plan is not doing, and why

- **No change to `.ai/intent.md`, `CONSTITUTION.md`, or the one-writer rule.** The four
  behaviours extend the *target*, not the authority model. Touching them would be the change
  this plan exists not to make.
- **No acceptance of ADR 0025 / no history rewrite of spec 026.** The inherited
  `madr.validate` red is recorded, not fixed here; the final task asserts no new MADR
  failure, no fifth row.
- **No new CLI verb.** B-029-4 is a `--limit` flag on the existing `audit` and `report`
  verbs plus a `just cost` recipe; the ten verbs stay closed. No verb count changes.
- **No new skill.** B-029-2 modifies the `ai-verify` skill's corpus to consume answer keys;
  the fifteen-skill target is unchanged.
- **No CI/CD or observability box ticked.** Spec 029 adds no service, endpoint or URL; the
  boxes stay unticked.

## The boundary this plan may not cross

The evals harness writes its graded keys **outside the tree under test**. `.ai/.gitignore`
begins with `*`, so keys under `.ai/evals/` are never visible to a skill being scored —
matching graph-engineering's rule that a review finding bugs by reading the list of planted
bugs proves nothing. The *defect templates* under `tests/evals/packs/` are committed; the
graded position list is not. The `doctor` pre-run adds an assertion row and its reader
(`tests/test_doctor.py`) is updated in the same commit. The register's indicator count moves
18 → 19 in the same commit as the new row, because `tests/pilot_register.py` refuses a
register whose count drifted from its constant.

## Tasks

## Block A — measurement (B-029-1)

1. **Evals harness: plant + score over three tiers, answer key outside the tree** —
   **file** `tests/evals/` (new): `plant.py` (injects defect packs into a clean fixture copy),
   `score.py` (reports per-skill recall/precision), `packs/` (committed defect templates),
   plus `tests/test_evals_harness.py` owning the harness contract.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_evals_harness.py`
   **rollback**: `git revert <commit>`.
   **done when**: a planted Tier-2 defect in a fixture is counted in recall; a skill
   reporting nothing on a non-empty pack is `FAIL`; a clean tier-3 control that fires loses
   precision; and `plant.py` refuses to write the graded key inside the tree (refuses an
   in-tree key by construction).

2. **Packs for the review skills that own defect classes** —
   **file** `tests/evals/packs/{ai-review,ai-security,ai-verify}/` — committed templates: at
   least one Tier-1, one Tier-2 and one Tier-3 per skill, each with an `answer-key.template`
   whose graded positions are filled only at plant time (outside the tree).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_evals_harness.py -k packs`
   **rollback**: `git revert <commit>`.
   **done when**: each named skill has a defensible pack whose Tier-3 trap is verified to
   mask the defect from a regex-only scan (a fixture asserts the trap is not lexically
   greppable), or its row reports `no_instrument` with the reason rather than a number.

3. **Wire the evals lane into `just check`, register the indicator, move the count** —
   **file** `justfile` (add `evals:` recipe before `ran` and into `check`),
   `policy/pilot-register.toml` (new indicator row `skill_evals_recall`: bound "no review
   skill reports nothing on a non-empty pack and no clean control fires", command
   `uv run python tests/evals/score.py`, wave P2), `tests/pilot_register.py`
   (`INDICATORS = 18` → `19` in the same commit, with the reason in the commit message).
   **check**: `just evals`
   **rollback**: `git revert <commit>`.
   **done when**: `just evals` exits 0 and writes its check-evidence receipt; the register
   read by `tests/pilot_register.py` accepts the new row (count 19, every row instrumented
   or argued).

## Block B — re-execution (B-029-3)

4. **Red fixture: claimed-is-not-passed** —
   **file** `tests/test_recheck.py` (new): fixtures that stage a stale claim, a
   digest-mismatched claim and a mere assertion, and demand rejection.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_recheck.py`
   **rollback**: `git revert <commit>`.
   **done when**: the fixture is red before the behaviour ships (TDD: fails naming the
   missing semantic) and green after.

5. **Recheck behaviour in the verification path** —
   **file** `src/ai_engineering/evidencing.py` (new small module: `--recheck` semantics that
   re-execute a named command against fresh input/artifact digests and refuse claims),
   wired into `tests/ledger_run.py` (the existing "every command the ledger calls proof"
   runner) and into `src/ai_engineering/audit.py` (re-run the chain under recheck), plus the
   green half of `tests/test_recheck.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_recheck.py && uv run --with pytest==9.1.1 pytest -q tests/test_requirements_ledger.py`
   **rollback**: `git revert <commit>`.
   **done when**: a check whose evidence is stale, digest-mismatched or merely claimed is
   rejected `INCOMPLETE` (never `PASS`); a fresh `--recheck` yields the true verdict; the
   ledger rows still render with no new failure.

## Block C — the answer key (B-029-2)

6. **Answer key schema and `ai-eng spec` emission** —
   **file** `policy/answer-key-v1.schema.json` (new, closed JSON Schema 2020-12),
   `src/ai_engineering/spec.py` (the `spec` verb emits `answer-key.yaml` beside the approved
   `spec.md`, digest-bound to its bytes), `tests/test_answer_key.py` (new: schema validity,
   digest binding, `BLOCKED: U<n>` verdict).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_answer_key.py`
   **rollback**: `git revert <commit>`.
   **done when**: a spec written by `ai-eng spec new` carries an answer key whose checks are
   binary (`judged_by: run it | a/b pick`), the key's digest binds the spec bytes it judges,
   and the reader returns `BLOCKED: U<n>` for an unknown observable — never a fabricated
   score.

7. **Answer-key consumption in the `ai-verify` skill** —
   **file** `.agents/skills/ai-verify/corpus.md` (route: "apply the spec's answer key";
   refusal: "judge it by taste" — no, a decided standard exists), plus the consumer half of
   `tests/test_answer_key.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_answer_key.py -k consume && uv run python tests/skill_eval.py`
   **rollback**: `git revert <commit>`.
   **done when**: a deliverable against a key with all `run it` checks passes after
   re-execution; one touching `U<n>` is `BLOCKED`; one failing a decided check is `FAIL`;
   and the skill-routing evaluation proves the new corpus row collides with neither `ai-review`
   nor `ai-ship` (baseline moves only if the corpus size does, with the reason in the commit).

## Block D — the cost gate (B-029-4)

8. **Red fixture: cost calibration refuses an un-authorized unbounded run** —
   **file** `tests/test_cost_gate.py` (new): a large-tree simulation where `--limit <n>`
   samples, projects, and refuses without consent in non-interactive mode.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_cost_gate.py`
   **rollback**: `git revert <commit>`.
   **done when**: red before `src/ai_engineering/` ships the gate; green after.

9. **Cost gate and `doctor` pre-run** —
   **file** `src/ai_engineering/cost.py` (new small module: bounded sample, projection,
   fail-closed consent), `src/ai_engineering/cli.py` (`--limit` on the `audit` and `report`
   verbs), `src/ai_engineering/doctor.py` (pre-run assertion: config, credentials, git,
   pinned engine versions before an expensive lane), `policy/cost-thresholds.toml` (new
   data: the declared threshold the gate fails closed against),
   `tests/test_cost_gate.py` (green half), `tests/test_doctor.py` (the new assertion's
   reader).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_cost_gate.py tests/test_doctor.py`
   **rollback**: `git revert <commit>`.
   **done when**: `--limit 50` on `audit` samples 50 units, projects cost/wall-time, and
   refuses `INCOMPLETE` without consent above the `policy/` threshold in non-interactive
   mode; `ai-eng doctor` reports the pre-run prerequisites before any costly lane starts.

## Block E — prove the gate

10. **The full gate reads the four controls green with their clean controls** —
    **file** none (verification).
    **check**: `just check`
    **rollback**: `git revert <commit>`.
    **done when**: `just check` exits 0, `just evals` reports per-skill recall/precision with
    no skill reporting nothing on a non-empty pack and no clean control firing, the answer
    key consumer passes, the cost gate refuses an un-authorized unbounded run, and
    `tests/test_madr.py` reports exactly the same pre-existing failures as before this
    block (the ADR 0025 inherited red) — no fifth failure introduced.