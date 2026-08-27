# Plan: design accessibility honesty floor — 038 atomic execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and
this exact `plan.md`**, recorded at their digests in their own record. One repository
writer, on a branch carrying the whole 038 change. Each task is one atomic commit; rollback
for every task is `git revert <commit>`.

**This plan is not edited while it is executed.** Every commit runs the gate in the same
chain as the commit itself. `ai-eng spec show 038 --task <n>` refuses any task whose
digests have moved.

## The order, and why

Proof objects first: the fixture (`tests/test_038_accessibility.py`) lands red before the
rule. Then the `_accessibility_problems` contract lane (B-038-1) turns it green, then the
reference (B-038-2), then the ai-design verify-step wiring, then the gate. The spec's
example commands are the acceptance tests.

## What this plan is not doing, and why

- **No new skill.** The floor lives inside ai-design's verify route and one contract lane.
- **No change to the existing contrast/motion steps.** The council proved ai-design already
  verifies contrast and reduced-motion; this plan adds keyboard/focus and the `not-covered`
  exit, it does not duplicate the floor.
- **No re-audit of the insumo design skills.** They are `~/.claude/skills` insumos, not
  framework skills; `contract.audit` stays over ai-*/SKILL.md only.
- **No acceptance of ADR 0025** — the inherited `madr.validate` red stays; the final gate
  asserts no new MADR failure.
- **No CI/CD box ticked.** Adds no service, endpoint or URL.

## The boundary this plan may not cross

The rule refuses exactly two shapes: a surface that neither names the a11y basics nor
exits `not-covered`, and one that claims the basics without the existing verify steps
confirming them. It imposes no style: a `not-covered: <reason>` exit for a deliberately
non-compliant surface is the honest, legal end, never a pass and never a stall. The
reference stays under ai-design, laden only on verify.

## Tasks

1. [ ] **Red fixture: the honesty floor** —
   **file** `tests/test_038_accessibility.py` (new): three cases — `floor` (a verify pass
   naming contrast/keyboard/focus/motion → no problems), `silent` (a pass omitting the
   basics and naming no not-covered → refused), `honest` (a surface saying
   `not-covered: <reason>` → accepted), plus `reference` (the reference file names the
   checks and the rule).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_038_accessibility.py`
   **rollback**: `git revert <commit>`.
   **done when**: the fixture runs and fails for the right reason (no lane yet).

2. [ ] **The `_accessibility_problems` contract lane (B-038-1)** —
   **file** `src/ai_engineering/contract.py` (new `_accessibility_problems` in the audit
   lanes, in the shape of the existing disciplines: refuses a surface that omits the a11y
   basics or names no `not-covered`), plus the green half of `tests/test_038_accessibility.py`.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_038_accessibility.py`
   **rollback**: `git revert <commit>`.
   **done when**: `floor` and `honest` pass, `silent` is refused, and the lane reads the
   same rule the fixture asserts.

3. [ ] **The accessibility reference (B-038-2)** —
   **file** `.agents/skills/ai-design/references/accessibility.md` (new: contrast ratios,
   keyboard reachability, visible focus, reduced-motion, landmarks, and the `not-covered`
   rule with the `NOT COVERED` same-spelling note), plus the `reference` case green.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_038_accessibility.py -k reference`
   **rollback**: `git revert <commit>`.
   **done when**: the reference names the checks and the rule, and the fixture reads it.

4. [ ] **ai-design verify-step wiring** —
   **file** `.agents/skills/ai-design/SKILL.md` (verify step names the a11y basics —
   contrast/keyboard/focus/reduced-motion — and the `not-covered` exit, following the
   closed `AI_SPEC_SECTIONS`-style pin if ai-design's body is pinned; check
   `tests/test_contracts.py` for an ai-design pin and update it in this same commit), plus
   the corpus route for the `not-covered` case.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_038_accessibility.py && uv run python tests/skill_eval.py`
   **rollback**: `git revert <commit>`.
   **done when**: the verify step carries the floor, the corpus routes the edge, and any
   pin that moved was updated in this commit (baseline moves with its reason if the corpus
   count changes).

5. [ ] **The gate** —
   **file** none (verification).
   **check**: `just check`
   **rollback**: `git revert <commit>`.
   **done when**: `just check` exits 0 with the 038 suite green, `tests/test_madr.py`
   reporting exactly the same pre-existing failures as before this block (the ADR 0025
   inherited red) — no new failure — and the spec, plan and approval of 038 are committed
   at their exact digests.