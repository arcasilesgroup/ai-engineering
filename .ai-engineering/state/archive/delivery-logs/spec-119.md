## spec-119 — Evaluation Layer (Generator/Evaluator Split, CI Eval Gates, pass@k Telemetry, Lint-as-Prompt)

**Branch**: `feat/knowledge-placement-governance-cleanup`. **Status**: runtime-landed; `.claude/` documentation surface deferred behind harness auto-mode safety policy. Commit `a1ae2d2d`.

**Scope**: closed the Evaluation Layer with four coordinated additions — Generator/Evaluator agent split, CI eval gates blocking on threshold/regression failure, pass@k telemetry through a single new `eval_run` audit kind, and structured lint-as-prompt envelopes replacing prose violation labels.

**Key landings (runtime, all green at commit time)**:
- One new audit kind `eval_run` with eight discriminated sub-operations (D-119-01) registered across canonical hook, Python validator, and both install-template mirrors.
- Eight `emit_eval_*` helpers with verdict-aware outcome mapping (`NO_GO → failure`, `SKIPPED → degraded`, else `success`).
- Brand-new module `src/ai_engineering/eval/` with `replay`, `pass_at_k` (HumanEval formula), `scorecard` (verdict mapping), `regression`, `runner`, and `gate` (modes `check` / `report` / `enforce`).
- New top-level `evaluation:` section in `manifest.yml` per D-119-04; manifest schema declaration with required fields; side-effect: `gates` block added to manifest schema (parity repair).
- New `.ai-engineering/schemas/lint-violation.schema.json` per D-119-05; canonical renderer at `src/ai_engineering/lint_violation_render.py`.
- New optional dependency extra `eval = ["deepeval"]` in `pyproject.toml`; pytest markers `eval` and `eval_slow`.
- Evals scaffolding under `.ai-engineering/evals/` with seed `baseline.json` covering three reference scenarios (`/ai-build`, `/ai-plan`, `/ai-review`) using deterministic graders.
- 81 new tests under `tests/unit/eval/`; canonical smoke proves the gate engine runs end-to-end against the real repo.

**Side-effect repairs**:
- `memory_event` added to `ALLOWED_EVENT_KINDS` in `src/ai_engineering/state/event_schema.py` and to both install-template copies (closes a spec-118 mirror gap).
- `gates` block declared in `manifest.schema.json` (the schema lacked the section that the manifest already used).

**Deferred (auto-mode harness denied autonomous writes into `.claude/`)**:
- `.claude/agents/ai-evaluator.md` — final body in `spec-119-progress/proposed-ai-evaluator-agent.md`.
- `.claude/skills/ai-eval-gate/SKILL.md` — final body in `spec-119-progress/proposed-ai-eval-gate-skill.md`.
- `.claude/skills/_shared/execution-kernel.md` Stage 0 insertion — diff in `spec-119-progress/kernel-stage-0-diff.md`.
- `.claude/skills/ai-code/handlers/compliance-trace.md` prose update — diff in `spec-119-progress/proposed-compliance-trace-update.md`.
- `/ai-pr` and `/ai-release-gate` skill wiring — diff embedded in the proposed eval-gate skill body.

The runtime engine is independently dispatchable; the deferred files are documentation surface that pin the dispatch contract. `ai-eng sync --check` should be run after the maintainer applies the proposals.

**Lessons learned**:
1. **Auto-mode protects the harness's own dispatch surface**. The harness denies autonomous writes to `.claude/agents/`, `.claude/skills/`, and the install-template mirrors of those paths even with explicit user permission given mid-session — a deliberate safety net that prevented the run from rewriting how Claude itself dispatches subagents. The right path is to keep the runtime engine outside `.claude/` and treat the dispatch surface as the maintainer's review target.
2. **One audit kind sub-typed via `detail.operation` is now the third precedent** (`framework_operation`, `memory_event`, `eval_run`). Future audit-kind additions should default to this pattern.
3. **Spike before assuming spec lineage**. spec-119 D-119-07 originally claimed three named functions from spec-117 hx-11 existed; the spike found they did not. Catching this in Phase 1 (T-1.1) prevented Phase 2 from importing ghost names; the SSOT landed under spec-119 instead with a transparent reconciliation note.
4. **Schema gaps surface during foundation waves**. The manifest schema did not declare the `gates:` block that the manifest already used; the side-effect repair lands cheaply alongside the new `evaluation:` block. Establishing the rule "if the foundation phase touches a schema, sweep adjacent gaps in the same phase" is worth documenting.
5. **Test bar can be stricter than schema**: `test_skill_has_valid_effort` allowlist `{max, high, medium}` was tighter than the skill-frontmatter schema enum `{max, high, medium, low}`. spec-118's `ai-remember` set `effort: low` per the schema and surfaced the divergence; spec-119 cleanup aligned the test to the schema.
