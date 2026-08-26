# Plan: model router and intake validation — 037 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and
this exact `plan.md`**, recorded at their digests in their own record. One repository
writer, on a branch carrying the whole 037 change. Each task is one atomic commit; rollback
for every task is `git revert <commit>`.

**This plan is not edited while it is executed.** Every commit runs the gate in the same
chain as the commit itself. `ai-eng spec show 037 --task <n>` refuses any task whose
digests have moved.

## The order, and why

Proof objects first: the fixtures (`tests/test_037_model_router.py`,
`tests/test_037_intake.py`) land red before their modules. Then the schema + router
(B-037-1/2), then the intake validator + template (B-037-3), then the ai-spec step-0 wiring
and the `skill_eval` baseline move, then the gate. The spec's example commands are the
acceptance tests; each `--tick` seals its box with the check that ran.

## What this plan is not doing, and why

- **No change to specs 028-036 modules** except adding new files; `cost.py`'s calibration
  stays the budget gate (the router is the *which-model* answer, not a second budget
  authority).
- **No vendor lock-in**: the router reads model *names* from `.ai/config.toml`; nothing in
  code names a provider.
- **No new skill.** The intake step-0 wires into the existing `ai-spec` procedure.
- **No acceptance of ADR 0025** — the inherited `madr.validate` red stays; the final gate
  asserts no new MADR failure.
- **No CI/CD box ticked.** Adds no service, endpoint or URL.
- **The P1/P2 rows of the roadmap are not this plan's scope.** Only B-037-1/2/3 (P0)
  are authorised; the rest are candidate specs recorded in spec 037's roadmap table.

## The boundary this plan may not cross

`route(step, config)` returns a configured model string or the `default_tier` value, never
empty and never a name not in the config. `bail_out(request)` returns a bool. The intake
validator refuses only malformed shape (missing goal/constraints/outcome), never demands a
form; the template is a fallback, and a well-formed free request passes. The step→tier
mapping (mechanical→low, hard reasoning→top, rest→medium) is config, not code, so a later
measured need tunes it without a spec.

## Tasks

1. [ ] **Red fixtures: router and intake** —
   **file** `tests/test_037_model_router.py` (new) + `tests/test_037_intake.py` (new).
   `test_037_model_router.py` covers route() on a config with all three tiers
   (low for mechanical steps, top for security/review, medium otherwise), `default_tier`
   when a tier is missing, and bail_out on a small request. `test_037_intake.py` covers
   validate_intake PASS on the template's example and INCOMPLETE with the missing field on
   a request that names no acceptance signal.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_037_model_router.py tests/test_037_intake.py`
   **rollback**: `git revert <commit>`.
   **done when**: both files run and fail for the right reason (no module yet) — the plan
   will turn real reds green.

2. [ ] **Models schema + router module (B-037-1/2)** —
   **file** `policy/models.schema.json` (new: JSON Schema for `[models]` — top/medium/low/
   default_tier, all optional strings) + `src/ai_engineering/model_router.py` (new,
   stdlib-only: `route(step, config) -> str` reading `.ai/config.toml` and mapping
   mechanical steps to `low`, hard reasoning to `top`, the rest to `medium`, falling back
   to `default_tier`; `bail_out(request) -> bool`), plus the green half of
   `tests/test_037_model_router.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_037_model_router.py`
   **rollback**: `git revert <commit>`.
   **done when**: `route("research")` returns `qwen3.6` and `route("security")` returns
   `deepseek-v4-flash` on the configured pin; a missing tier falls back to `default_tier`;
   bail_out returns True for a one-line request.

3. [ ] **Intake validator + template (B-037-3)** —
   **file** `src/ai_engineering/intake.py` (new, stdlib-only: `validate_intake(text)`
   returning `PASS` or `INCOMPLETE` with the missing of goal/constraints/outcome) +
   `specs/new-goal-template.md` (new: the copy-paste template whose own example passes the
   validator), plus the green half of `tests/test_037_intake.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_037_intake.py`
   **rollback**: `git revert <commit>`.
   **done when**: the template's example passes; a request naming no acceptance signal
   returns INCOMPLETE listing it; a well-formed free request passes without the template.

4. [ ] **ai-spec step 0 + corpus + baseline move** —
   **file** `.agents/skills/ai-spec/SKILL.md` (procedure gains step 0: when the opening
   request fails `validate_intake`, ask the intake questions first) + `.agents/skills/
   ai-spec/corpus.md` (a quoted intake case + a refusal) + `policy/pilot-register.toml`
   (baseline moves with its reason in this same commit) + `docs/requirements.toml` (EP-029
   baseline notes restate the new number).
   **check**: `uv run python tests/skill_eval.py && uv run --with pytest==9.1.1 pytest -q tests/test_037_model_router.py tests/test_037_intake.py`
   **rollback**: `git revert <commit>`.
   **done when**: the intake case routes in the harness, the baseline moves with a stated
   reason, and both new suites stay green.

5. [ ] **The gate** —
   **file** none (verification).
   **check**: `just check`
   **rollback**: `git revert <commit>`.
   **done when**: `just check` exits 0 with the 037 suites green, `tests/test_madr.py`
   reporting exactly the same pre-existing failures as before this block (the ADR 0025
   inherited red) — no new failure — and the spec, plan and approval of 037 are committed
   at their exact digests.