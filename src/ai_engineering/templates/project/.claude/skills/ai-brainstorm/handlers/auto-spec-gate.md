# Handler: Auto-spec gate

> Trivial-vs-spec classifier for `/ai-brainstorm` (spec-134 D-134-04).
> Runs at the FRONT of the workflow (Step 0b), BEFORE interrogation.
> Trivial diffs route to a condensed-spec path; everything else routes
> to full interrogation.

## Purpose

Classify the working-tree diff up-front so operators do not waste an
interrogation pass on changes the framework can already see are
trivial. The gate is heuristic — hard triggers are absolute (any one
fires → full interrogation), thresholds are upper bounds (any breach
→ full interrogation). The default for any ambiguous input is the
safe one: route to full interrogation.

The procedure is hexagonal (§10.8). This handler is the **adapter** —
it shells out to `git`. The pure domain logic lives in
`ai_engineering.brainstorm.auto_spec_gate.classify_diff` and never
touches a subprocess.

## Procedure

1. **Read the manifest knob.** Load
   `manifest.brainstorm.auto_spec_gate` via the existing
   `ai_engineering.config.loader.load_manifest_config` helper. The
   knob is framework-managed — slim user manifests still resolve to a
   complete `AutoSpecGateConfig` instance.
2. **Honor the opt-out.** If `config.enabled` is `false`, log
   "auto-spec gate disabled — routing to full interrogation" and
   continue to SKILL.md Step 1 (work-item context). No further gate
   work runs.
3. **Resolve regulated mode.** Read `manifest.gates.mode`. When the
   value is `"regulated"`, pass `regulated=True` to the helper so the
   tightened `regulated_overrides` are substituted over `thresholds`.
4. **Collect the diff inputs (adapter calls).** Run these three
   commands and concatenate their stdout into a single `diff_text`
   string (newline-separated):

   ```bash
   git diff --name-only HEAD
   git diff --shortstat HEAD
   git diff HEAD -- pyproject.toml package.json
   ```

   The first command produces the `files` list (one path per line,
   empty lines filtered). The other two contribute to `diff_text`.
5. **Call the helper.** Invoke
   `ai_engineering.brainstorm.auto_spec_gate.classify_diff(files=...,
   diff_text=..., config=config.brainstorm.auto_spec_gate,
   regulated=...)`. The return is a `GateDecision` dataclass with
   `route`, `reason`, and `triggers` fields.
6. **Branch on the decision.**
   - `decision.route == "condensed"` → execute the **Condensed-spec
     path** (see below). STOP at SKILL.md Step 7 once the condensed
     spec is approved.
   - `decision.route == "full"` → log `decision.reason` for operator
     transparency, then continue to SKILL.md Step 1 (work-item
     context) and run the standard interrogation flow.

## Hard triggers

Any one of these matches forces `route='full'` regardless of LoC or
file counts. Disabling a flag in `manifest.brainstorm.auto_spec_gate.
hard_triggers` is a deliberate risk acceptance — document the reason
in the spec decision row when you do.

| Vector | Signal source | Detection rule |
|--------|---------------|----------------|
| `public_api` | changed-file paths | `**/__init__.py`, `src/**/cli_factory.py`, `src/**/cli_commands/**`. Re-exports + new CLI verbs land here. |
| `state_or_schema` | changed-file paths | `.ai-engineering/state/**`, `.ai-engineering/schemas/*.json`, `**/*.sql`, `**/migrations/**`. |
| `new_dependency` | `git diff HEAD -- pyproject.toml package.json` | An added `+` line matching a Python or JSON dependency entry. Removals do NOT fire. |
| `security_surface` | changed-file paths | `**/_shared/redactor.py`, `**/security/**`, `.ai-engineering/scripts/hooks/**`, `.ai-engineering/state/hooks-manifest.json`, `.ai-engineering/security/**`. |

## Thresholds

When no hard trigger fires, the helper compares against the
configured `thresholds` map (or `regulated_overrides` when
`gates.mode == "regulated"`). A diff is trivial only when **every**
threshold is strictly satisfied.

| Knob | Prototyping default | Regulated default |
|------|---------------------|-------------------|
| `files` | 3 | 1 |
| `loc` | 50 | 20 |
| `cross_module` | 1 | 1 |

- `files` = `len(git diff --name-only HEAD)`.
- `loc` = sum of `+` and `-` lines from `git diff --shortstat HEAD`.
- `cross_module` = count of distinct first-segment directories under
  `src/` that the diff touches (e.g., `src/ai_engineering/governance/`
  + `src/ai_engineering/brainstorm/` = 2).

## Condensed-spec path

When `decision.route == "condensed"`:

1. Skip Steps 1-6 (work-item context, prompt-enhance, evidence sweep,
   interrogate, scope check, propose approaches) — the gate has
   already classified the work.
2. Draft a **minimum-viable spec** at `.ai-engineering/specs/spec.md`
   conforming to `.ai-engineering/reference/spec-schema.md`. The
   condensed shape is a **strict subset** of the full schema:
   - Frontmatter: required fields plus `effort: trivial`.
   - `## Summary` (1 paragraph).
   - `## Goals` (1 bullet — what the diff achieves).
   - `## Non-Goals` (1 bullet — what is explicitly out of scope).
   - `## Decisions` (1 row — the `D-<spec>-<NN>` that ratifies the
     condensed path).
   - `## Risks` (1 bullet — the residual risk, even if "none").
3. Present the spec to the operator with this exact framing:

   > "Auto-spec gate classified this as a trivial change
   > (`{reason}`). Here is the condensed spec. Approve to proceed to
   > `/ai-plan`, or say 'interrogate' to escalate to full
   > interrogation."

4. If the operator says "interrogate", discard the condensed spec
   and fall back to the full interrogation path starting at SKILL.md
   Step 1.
5. On approval, STOP at SKILL.md Step 7 (Draft spec) — the spec is
   already drafted; the review loop in Step 9 still runs.

## Opt-out

`manifest.brainstorm.auto_spec_gate.enabled: false` is the mandatory
opt-out. Operators who want the legacy "always interrogate" behaviour
flip this knob to `false`. The handler routes immediately to full
interrogation without consulting any other knob.

This is the correct lever for teams who do not trust the gate yet —
it is **not** equivalent to disabling individual hard triggers, which
narrows the gate's signal coverage rather than disabling it.

## Failure modes

- **`git` is unavailable.** The handler emits a one-line warning,
  records `route='full'`, and falls through to interrogation. The
  gate must never block brainstorming on missing tooling — fail-open
  is the contract (mirrors the lifecycle bootstrap in SKILL.md
  Step 0).
- **Empty diff (`git diff --name-only HEAD` returns nothing).** The
  helper returns `route='full'` with reason
  `"no staged or tracked changes detected"`. This is the right
  default — the operator has not staged anything, so the gate has no
  signal to classify on.
- **Manifest validation error.** The loader raises before the gate
  runs; bubble the error up and STOP. The skill cannot continue with
  an invalid manifest.

## Calls / called by

- **Called by**: `.claude/skills/ai-brainstorm/SKILL.md` Step 0b.
- **Calls**: `ai_engineering.brainstorm.auto_spec_gate.classify_diff`
  (pure helper), `git diff` (adapter). Falls back to
  `handlers/interrogate.md` on `route='full'`. Mirrors the no-op
  shape of `_shared/consolidate-spec.md` when the gate routes to
  condensed.
