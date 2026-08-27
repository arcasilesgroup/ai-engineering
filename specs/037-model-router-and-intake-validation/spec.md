---
id: "037"
slug: model-router-and-intake-validation
status: draft
date: 2026-08-26
ref: ""
supersedes: ""
---

# Model router and intake validation

## Who this is for, and what it is worth to them

The repository owner and the stranger who installs the wheel and runs `/ai-goal` on their
own repository. Today the framework does one thing the research (`.ai/research`, spec
035-036) explicitly marked as missing: **it does not route work by model cost/capability**
(model-router MR-01/02/03, deepsec D-01's calibration, and the "context an agent pays for"
economy; the vendor-lock rejection's sharpest form is spec 035's "What is not adopted at
all" and spec 036's validation of it). A stranger on a tight budget runs every step of the governed cycle on the same
model, paying frontier prices for a rename. And the first prompt of a new goal is
unvalidated: ai-spec crawls into discovery with whatever shape the user happened to type,
so half-built intent lands as a half-built spec. This spec gives the framework a
per-repository model tiering (`top`/`medium`/`low`) with a router that picks the model for
each step of the cycle, and a validated intake template so a goal starts from a known,
minimal shape.

## Context and problem

**What is true today, measured in this tree on 2026-08-26:**

- Before this spec, `.ai/config.toml` (the pin) carried `[guards]` and `[observability]`
  with **no model section**; `policy/cost-thresholds.toml` gates *whether* a costly lane may
  run, but no
  code maps *a step of the cycle to a model tier*.
- `cost.py` (spec 029) provides the calibration ritual (bounded-sample `calibrate`) but has
  no tier→model table and no route-down/route-up function; the model-router reference
  (`.ai/research/reports/02-model-router/report.md`) names MR-01/02/03 and the deepsec
  pre-flight as the gap.
- `ai-spec` (spec 019 era) requires asking only questions that change the decision, but
  nothing *validates the intake*: there is no template, no required fields, no
  well-formedness check on the user's opening request. The discipline is wayfinder's — a
  check only means what its input defined it to mean — not a citation of its numbered items.
- The user's concrete machine has `qwen3.6` (cheap), `deepseek-v4-flash` (top/medium) and
  the nan.builders OpenAI-compatible endpoint `https://api.nan.builders/v1` — a per-repo
  config must accept exactly this, and any other provider, without code change.

**The problem, in words a non-technical reader can follow:**

Two small missing pieces make the framework spend more than it should and start badly. It
has no way to say "this step of the work should use the cheap model, that step the strong
one" — so every step uses the same, often most expensive, model. And when someone begins a
goal, their opening request is not checked against any shape, so a vague idea produces a
vague spec. This spec adds both: a per-repository model configuration with three tiers and
a router that assigns each step of the cycle to a tier, and a validated intake template that
a goal requires before the governed cycle starts.

## Options considered

1. **Three tiers (`top`/`medium`/`low`) in `.ai/config.toml` + a router module + an intake
   template with a validation check (chosen shape).** Gives: the smallest general model —
   tiers not vendors — so any provider fits (`qwen3.6`/`deepseek-v4-flash`/any name), a
   deterministic `route(step) -> model` read once per goal, and an intake that fails closed
   on a malformed opening request. Costs: one config section, one stdlib module, one
   template + validator.
2. **Per-vendor model lists in code (equivalent of model-router's Haiku/Sonnet/Opus/Fable
   table).** Gives: a ready table like the reference. Costs: locks the framework to model
   names and vendors, exactly what spec 036 rejected ("no vendor lock-in"); a stranger with
   one model cannot use it without editing code. Rejected on evidence.
3. **Prompt-only intake (no template validation).** Gives: zero code. Costs: intake stays
   unvalidated — the exact gap both the research (wayfinder W-01's "the input is the
   contract") and the user's "input validation of an API" phrasing mark as a real hole.

## Decision

**Option 1.** Spec 037 adds three behaviours to the framework:

### B-037-1 — Per-repository model tiers

`.ai/config.toml` gains a `[models]` section: `top`, `medium`, `low` each a model
identifier string (any name, any provider), all optional, plus `default_tier`. The pin
writes nothing on install; a repository that never configures models degrades to
`default_tier` for everything (graceful, no lock-in). The user's machine configures
`deepseek-v4-flash` as `top`/`medium` and `qwen3.6` as `low`; any project can do the same
with its own provider names. The schema lives in `policy/models.schema.json` (a small JSON
Schema, mirroring `capability-manifest.schema.json`).

### B-037-2 — Step router and cost honesty

A `src/ai_engineering/model_router.py` (stdlib-only): `route(step, config) -> str` maps each
step of the governed cycle (research, spec, plan, build, review, verify, security, audit,
ship) to a tier — cheap work (mechanical edits, spec generation) routes to `low`, hard
reasoning (architecture, security, review) to `top`, the rest to `medium` — and
`bail_out(request)` returns whether the work is small enough to handle inline (model-router
MR-01). The router is a pure function over config, so it is testable without a provider; it
never calls out to a model (the surface that calls it picks the model string). `cost.py`'s
calibration stays the budget gate; the router is the *which-model* answer.

### B-037-3 — Validated intake template

`specs/new-goal-template.md` (a copy-paste template) + `src/ai_engineering/intake.py`:
`validate_intake(text)` returns `PASS` when the opening request names the goal, the
constraints, the intended outcome and an acceptance signal, and `INCOMPLETE` with the
missing fields when it does not. `ai-spec`'s procedure gains step 0: when the opening
request fails `validate_intake`, ask the intake questions (capped, the way the research's
grill/wayfinder recommends) before discovery. The template is the "API contract" the user
asked for: a known shape a person copy-pastes, and the validator is the input check.

## Challenged once

**"Three tiers is model-router's four-model table with extra steps; why not adopt the
reference wholesale?"** Because the reference's table is vendor-locked (Haiku/Sonnet/Opus/
Fable): a stranger with one open model cannot fill four slots. Tiers, not vendors, is the
general form — any provider maps into top/medium/low, and the router reads the *names the
repository configured*, never a hardcoded vendor. The reference's real content (route down
for mechanical work, route up for hard reasoning, bail out early) is preserved as the tier
mapping per step.

**"A template with required fields is exactly the ceremony the framework refuses; the whole
point of a goal is freedom."** The template is a *fallback*: it refuses only a request that
fails the three-field minimal check (goal, constraints, outcome/acceptance), and a
well-formed free-form request passes without ever seeing the template — the validator
checks shape, it does not demand a form. It is the difference between "we need a standard
input" and "we need a form you must fill".

## Assumptions and unresolved risks

- Assumption: `default_tier` (no config) is a sane degraded mode — every step uses the
  session's own model, so nothing breaks for a stranger who never configures models.
- Assumption: the step→tier mapping (mechanical→low, hard reasoning→top, rest→medium) is a
  good first cut; a later measured need may tune it without a new spec (config, not code).
- Unresolved: the router tells a surface *which model string* to use; binding it into every
  cycle step (actually switching models mid-run) is a consumer change the plan sequences —
  this spec delivers the config + router + intake, the wiring into each skill corpus is
  task-scoped.
- Unresolved: whether `ai-spec`'s step 0 should also be applied to `/ai-goal` and
  `/ai-research`; this spec scopes step 0 to ai-spec, and a follow-up may extend it.

## Examples somebody can check

- **Success, router:** Given a `.ai/config.toml` with `[models] top="deepseek-v4-flash",
  medium="deepseek-v4-flash", low="qwen3.6"`, When `route("research")` reads it, Then it
  returns `qwen3.6` (low) and `route("security")` returns `deepseek-v4-flash` (top)
  (`uv run --with pytest==9.1.1 pytest -q tests/test_037_model_router.py` → `2 passed`).
- **Denial, intake:** Given an opening request that names no acceptance signal, When
  `validate_intake` reads it, Then it returns `INCOMPLETE` listing the missing field
  (`uv run --with pytest==9.1.1 pytest -q tests/test_037_intake.py -k incomplete` →
  `1 passed`).
- **Degraded:** Given no `[models]` section, When `route("build")` reads the config, Then
  it returns the `default_tier` value, never empty (`-k default_tier` → `1 passed`).
- **Copy-paste:** Given `specs/new-goal-template.md`, When a user pastes it, Then the
  template's own example passes `validate_intake`, proving the contract end to end
  (`-k template` → `1 passed`).

## Decisions

**D-037-01 — model tiers, not vendor lists; `.ai/config.toml` holds them, any provider
fits.**
Rationale: spec 036 already rejected vendor lock-in; tiers are the general form, and a
per-repo pin keeps the stranger's environment in their own file, not in framework code.

**D-037-02 — the router is a pure function over config, never a caller; cost calibration
stays the budget gate.**
Rationale: separating *which model* (router) from *whether we may spend* (cost.py) keeps
each testable alone and avoids a second budget authority (spec 036's "no second source of
truth").

**D-037-03 — intake validates shape, not form; the template is a fallback for malformed
requests.**
Rationale: the user's "input validation of an API" analogy is right: validate that the
three fields exist, refuse only when they do not, and let a well-formed free request pass
unencumbered.

**D-037-04 — the sixteen reviewed points are recorded here, so the approved roadmap is a
commit, not a conversation; only P0 is this spec's scope.**
Rationale: the owner approved the reviewed roadmap and asked that nothing already approved
be forgotten. This spec's "Roadmap registrado" table records every point's state — covered,
P0 (this spec), P1/P2 (next specs), or rejected with reason — so the decision survives the
session. Nothing outside P0 (B-037-1/2/3) is authorised by this record; the P1/P2 rows are
candidate specs, not scope.

## Roadmap registrado — los dieciséis puntos revisados

Esta especificación es además el registro de la revisión de los dieciséis puntos del
roadmap que el owner aprobó el 2026-08-26, para que ninguna decisión quede solo en una
conversación. Cada punto queda anotado con su estado; los que son trabajo pendiente se
convierten en las próximas especificaciones candidatas, y los rechazos quedan con su razón.

| # | Punto | Estado | Dónde vive |
|---|---|---|---|
| 1 | claude-agents (catálogo) | Rechazado (contenido inflado, tools decorativos, KISS ❌ — research hoja 12) | este registro |
| 2 | unlazy (gates/planes) | P1 — gate-check-runner CLI; plan boxes ya corregidos (`5783fcd0`) | spec candidata |
| 3 | model-router tiers | **P0 — esta spec (B-037-1/2)** | specs/037 |
| 4 | Loop-Engineering | Ya cubierto (ai-goal + ai-cycle + verify_cold adversary) | registro |
| 5 | wayfinder answer-key | Ya cubierto (answer-key.yaml + verify_cold) | registro |
| 6 | al-design-system | P2 — solo si producimos UI (spec 038) | spec candidata |
| 7 | headstart intake | P1 — intake ≤7 preguntas (con #14, B-037-3) | specs/037 |
| 8 | code-simplifier/refactor | P2 — skill de refactor KISS/DRY/YAGNI, no hook auto | spec candidata |
| 9 | okf | Rechazado (YAGNI: convertir a OKF no resuelve una falta de sistema) | este registro |
| 10 | large-codebases CLAUDE.md | P2 — template por-área si onboarding | spec candidata |
| 11 | deepsec | P1 — two-job CI gate (era R1 de 035) | spec candidata |
| 12-13 | skillify | Ya cubierto (skillify.py spec 033 + corpus lo rutea); exponer CLI = P2 | registro |
| 14 | spec-planner/grill/intake | P1 — B-037-3 (paso 0 de ai-spec) | specs/037 |
| 15 | template de prompt inicial | **P0 — esta spec (B-037-3)** | specs/037 |
| 16 | AL-Design / a11y | P2 — guard de a11y en diseño (spec 038) | spec candidata |

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command. This
specification adds one config section, one stdlib module, one validator and one template;
no service, no URL, no second hop — the service-shaped boxes are `not applicable`.

- [x] CI/CD — `just check` runs the new fixtures on every push (`.github/workflows/check.yml`); nothing deployed
- [x] Logs — not applicable: every verb still emits the one JSON line `ai-eng report digest` reads
- [x] Traces — not applicable: one process, no second hop
- [x] Errors — not applicable: the new paths fail closed (missing model → `default_tier`, malformed intake → `INCOMPLETE` with fields)
- [x] Health and data age — `tests/test_037_model_router.py` and `tests/test_037_intake.py` run in the gate's pytest half (`just cover`'s `not fast_enough` collection) on every push
- [x] External check — `.github/workflows/check.yml` runs the whole gate on every push; the router and intake are additionally asserted by their fixtures, the independent route
- [x] Second path — the router is read by its fixture and the config schema by the schema reader and fixture this spec's build adds, with no shared line
- [x] Security — `just security`: gitleaks, semgrep, trivy on every push, over a change that adds no dependency and no network call