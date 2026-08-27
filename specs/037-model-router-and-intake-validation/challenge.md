# Challenge — spec 037 (model router and intake validation)

Challenger: independent critic, read-only on the tree except this file.
Date: 2026-08-26. Verdicts: WRONG / UNPROVEN / OK, each with the command and its output.
Findings are listed worst first.

Scope note: the spec is a draft whose deliverable half has already partially landed —
commit `30f8ec1e` ("pin gains [models]") added the `[models]` section to `.ai/config.toml`
and nothing else. So sentences about *today's tree* and sentences about *what the spec
adds* are checked against the same tree and reported separately.

---

## 1. WRONG — the quote "wayfinder W-01's 'the input is the contract'" is not in the research

Spec sentence: *"an intake that fails closed on a malformed opening request … the exact
gap both the research (wayfinder W-01's "the input is the contract") and the user's
"input validation of an API" phrasing mark as a real hole."*

Commands + output:

```
grep -rn "input is the contract" .ai/research   → No matches found
grep -rn "input.*contract" .ai/research         → No matches found
grep -n "W-01" .ai/research/reports/04-wayfinder/report.md
→ 58|| W-01 | **Check binario (run it / A/B pick)** — toda verificación es binaria, nunca score.
```

Wayfinder's W-01 is the binary-check verification pattern, not an input-contract claim.
The phrase exists nowhere in `.ai/research` (nor anywhere in the repo). The ID is real;
the quote attributed to it is unsourced.

## 2. WRONG — "spec 036 already rejected vendor lock-in" / "exactly what spec 036 rejected ('no vendor lock-in')"

Spec sentences: Option 2's cost line and D-037-01's rationale both rest on spec 036
having rejected vendor lock-in.

Commands + output:

```
grep -rn "vendor\|lock\|proveedor" specs/036-validate-adoption-and-close-boundary-delta/
→ (no match anywhere in the 036 dir, spec.md included; only "model" substring hits
   inside words like "module", none about vendors)
```

The vendor-lock-in rejection actually lives in spec 035 ("vendor lock-in (Vercel,
`claude -p`, SkillSpector/NVIDIA, Playwright-only, `model: opus`) … the research
explicitly rejects", `specs/035-adoption-of-reference-patterns/spec.md:88-90,175`) and
spec 001's "No vendor name appears in any SKILL.md" (`specs/001-…/spec.md:219`). The
cited authority is the wrong spec.

## 3. WRONG — "What is true today … `.ai/config.toml` … carries `[guards]` and `[observability]` but **no model section**"

Spec sentence (Context and problem, dated "measured in this tree on 2026-08-26").

Commands + output:

```
read .ai/config.toml
→ [framework] version = "1.0.0"
  [record] …
  [guards] loop_window = 6 …
  [models]
  # Per-repository model tiers (spec 037). …
  top = "deepseek-v4-flash"
  medium = "deepseek-v4-flash"
  low = "qwen3.6"
  [observability] …
git show --stat 30f8ec1e
→ .ai/config.toml | 6 +   (the [models] section, "pin gains [models]", 2026-08-26 15:38)
```

The tree has had a `[models]` section since the spec's own commit; the "no model
section" claim was false the moment the spec landed. Note also the realized section has
**no `default_tier` key**, which B-037-1 says the section gains ("`top`, `medium`, `low`
… all optional, plus `default_tier`") — the partial implementation already diverges from
B-037-1's section shape.

## 4. WRONG — "`tests/test_037_model_router.py` and `tests/test_037_intake.py` run in `just test` on every gate"

Spec sentence (Production-ready, Health and data age).

Commands + output:

```
justfile:99
→ test:
      uv run --with {{pytest}} --with {{xdist}} pytest -q -n auto -k "fast_enough"
justfile:122 and 125 (cover)
→ coverage run --parallel -m pytest -q -n auto -k "not fast_enough"
→ coverage report --fail-under=80
grep -rn "fast_enough" .   → only occurrence as a node id: tests/test_contracts.py::
  test_the_guards_start_fast_enough_to_be_guards (and the partition assertion in
  tests/test_p0_completeness.py:239-243)
```

`just test` selects exactly the tests whose node id contains `fast_enough` — today one
test, the guards' latency floor. Everything else runs in `just cover`. 036's own
fixtures were verified in the other half: "`pytest -q -k "not fast_enough and (036)"` →
`7 passed`" (`specs/036-…/verify.md:33-35`). So new test_037 fixtures would run in
`just cover`, not `just test`, unless named `*fast_enough*`; the claim names the wrong
recipe and no marking plan exists. (The files are also absent — see finding 7.)

## 5. WRONG — "the one JSON line `ai-eng digest` reads"

Spec sentence (Production-ready, Logs box).

Commands + output:

```
grep -n "digest" src/ai_engineering/cli.py
→ "report": "report digest | issue | surfaces | intent | blocked — what this install can show."
```

There is no `digest` verb; the ten verbs are `init doctor update … report exception
uninstall` (`cli.py:25-39`). The command that reads the event line is `ai-eng report
digest`. The event pipeline itself is real (hooks read one JSON payload per tool call
from stdin, `hooks/chain.py:236-244`), so this is a naming error, not a missing system.

## 6. WRONG — "the config schema by `tests/test_contracts.py` with no shared line"

Spec sentence (Production-ready, Second path).

Commands + output:

```
grep -rn "\[models\]\|default_tier\|model_router\|validate_intake\|new-goal-template" tests src hooks
→ No matches found
grep -n "config.toml" tests/test_contracts.py
→ 361| ".ai/config.toml … which are the pin."   (nondisposable-files list only)
```

`test_contracts.py` contains no reader or validator of the model configuration; nothing
in `tests/`, `src/` or `hooks/` reads the `[models]` section at all. Since
`policy/models.schema.json` also does not exist (finding 10), there is no config schema
and no second reader — the asserted independent path is absent on both sides.

## 7. UNPROVEN — all four "Examples somebody can check" cannot be executed

Spec sentences (Examples): the four commands with their `2 passed` / `1 passed` (×3) counts.

Commands + output:

```
glob tests/test_037_*            → (no matches; "Skipped missing paths: …")
ls tests/test_037_model_router.py tests/test_037_intake.py
→ No such files
```

The claimed pytest runs reference files that do not exist in this tree; the counts
cannot be reproduced. The commands themselves are well formed and the pinned versions
match the justfile (`pytest==9.1.1`), but there is nothing to run.

## 8. UNPROVEN — B-037-2's router does not exist, so every router claim is unexecutable

Spec sentences (B-037-2 and the Success example): `src/ai_engineering/model_router.py`
with `route(step, config) -> str`, `bail_out(request)`, the step→tier mapping
(research→low, security→top, rest→medium, per the example and prose), a pure function
over config, stdlib-only, never calling out to a model.

Commands + output:

```
glob src/ai_engineering/model_router.py   → Skipped missing paths: src/ai_engineering/model_router.py
grep -rn "route\|tier" src/ai_engineering/cost.py
→ (only "calibrate", "policy", "doctor_prereqs" definitions; no route, no tier)
```

The module is absent; the mapping table exists only as prose in the spec. The only
partially checkable half — that *today* nothing maps a step to a tier — is true
(`cost.py` has no route/tier; consistent with the spec's own "what is true today"
claim, which is the one current-state claim that checks out, see finding 15).

## 9. UNPROVEN — degraded mode has no source for `default_tier`

Spec sentences: B-037-1 "a repository that never configures models degrades to
`default_tier` for everything"; example "Given no `[models]` section … it returns the
`default_tier` value, never empty".

Commands + output:

```
grep -rn "default_tier" .ai/config.toml src specs/037-model-router-and-intake-validation/spec.md
→ appears only inside the spec text and the config *comment*;
  no key, constant or default anywhere in .ai/config.toml or src/ai_engineering/
```

`default_tier` is named by the config section comment ("`default_tier` is used when a
tier is not configured") but is not a key in the realized section, and no source
(`src/`) holds a fallback value. The degraded path has no implementable value today.

## 10. UNPROVEN — `policy/models.schema.json` does not exist

Spec sentence: B-037-1 "The schema lives in `policy/models.schema.json` (a small JSON
Schema, mirroring `capability-manifest.schema.json`)."

Commands + output:

```
glob policy/models.schema.json   → Skipped missing paths: policy/models.schema.json
glob policy/*.schema.json
→ answer-key-v1, capability-manifest, surface-adapter-v1, risk-acceptance-v1, issue-v1,
  madr-v1, outcome-v1, envelope-v1, intent-v1, check-evidence-v1 (no models schema)
```

The mirror target (`capability-manifest.schema.json`) exists; the schema itself does
not, so "mirroring" cannot be checked.

## 11. UNPROVEN — B-037-3's intake does not exist, and ai-spec has no step 0 today

Spec sentences: B-037-3 (`specs/new-goal-template.md` + `src/ai_engineering/intake.py`,
`validate_intake` PASS/INCOMPLETE) and "`ai-spec`'s procedure gains step 0".

Commands + output:

```
glob specs/new-goal-template.md; src/ai_engineering/intake.py
→ Skipped missing paths for both
grep -n "intake\|validate\|step 0\|step0" .agents/skills/ai-spec/SKILL.md
→ (no matches; the skill's numbered steps contain no intake step)
```

The current-state half of the claim is true (no template, no validator — see finding
14), but none of the deliverables B-037-3 describes exist.

## 12. UNPROVEN — "the router and intake are additionally asserted by their fixtures, the independent route"

Spec sentence (Production-ready, External check).

Commands + output:

```
glob tests/test_037_*   → (no matches)
```

No fixtures exist to assert anything; no independent route exists. The other half of
the box — `.github/workflows/check.yml` runs `just check` on every push — is verifiable
and true (`check.yml` jobs/check → "the gate, exactly as a developer runs it":
`just check | tee …`; push on `main`/`v1`, pull_request, merge_group).

## 13. UNPROVEN — the nan.builders endpoint is not in the tree

Spec sentence: "The user's concrete machine has `qwen3.6` (cheap), `deepseek-v4-flash`
(top/medium) and the nan.builders OpenAI-compatible endpoint `https://api.nan.builders/v1`".

Commands + output:

```
grep -rn "nan.builders" .ai/config.toml specs src
→ No matches found
```

The model names check out (finding 21); the endpoint URL is a machine-level claim that
no file in this tree carries, so it cannot be confirmed or refuted from here.

## 14. UNPROVEN — "a per-repo config must accept exactly this, and any other provider, without code change"

Spec sentence (Context). The config format is plain TOML string values (stdlib
`tomllib`), so any identifier string fits structurally; but nothing in `src/` reads the
section yet (finding 6), so "without code change" — the behaviour that matters — has no
consumer to accept anything.

## 15. OK — "cost.py (spec 029) provides the calibration ritual (bounded-sample `calibrate`) but has no tier→model table and no route-down/route-up function"

Commands + output:

```
grep -n "def \|class \|route\|tier\|calibrate" src/ai_engineering/cost.py
→ class _Policy(dict); def policy(); def calibrate(limit, samples, *, …); def doctor_prereqs()
```

`calibrate` exists with the bounded-sample signature (`limit`, `samples`); no route or
tier anywhere in the module. Spec 029 exists (`specs/029-evidence-executed-and-answer-keys/`).
TRUE as stated.

## 16. OK — "`policy/cost-thresholds.toml` gates *whether* a costly lane may run"

Commands + output:

```
glob policy/cost-thresholds.toml → exists
src/ai_engineering/cost.py:17-18 → THRESHOLDS = ROOT / "policy" / "cost-thresholds.toml"
```

The gate file exists and is the policy source for `cost.policy()` (schema
`urn:ai-engineering:cost-thresholds:1`, `threshold_usd > 0`, `limit > 0`). TRUE.

## 17. OK — MR-01/02/03 are present in `.ai/research/reports/02-model-router/report.md`

Commands + output:

```
grep -n "MR-0[123]" .ai/research/reports/02-model-router/report.md
→ MR-01 | Bail-out rápido: filtro antes de delegar …
  MR-02 | Matriz coste/capacidad: cada tipo de trabajo mapeado a un modelo …
  MR-03 | Fan-out con model-per-chunk …
```

All three IDs exist with the meanings the spec cites. The report also explicitly
rejects hardcoding Haiku/Sonnet/Opus/Fable ("son productos de Anthropic … no aplican a
ai-engineering", report.md:75), which supports the tiers-not-vendors direction — though
the spec attributes that rejection to the wrong spec (finding 2).

## 18. OK — deepsec D-01's calibration is present

Commands + output:

```
grep -n "D-01" .ai/research/reports/10-deepsec/report.md
→ D-01 | **Ritual de calibración**: `--limit N` + proyección de costo antes de ejecución libre
```

## 19. OK — "ai-spec (spec 019 era) requires asking only questions that change the decision"

Commands + output:

```
grep -n "change the decision" .agents/skills/ai-spec/SKILL.md
→ 40|7. Ask only questions whose answers change the decision, after presenting the evidence …
glob specs/019-*/spec.md → specs/019-the-four-days-two-specs-cost/spec.md exists
```

The requirement is in the skill verbatim; spec 019 exists. TRUE.

## 20. OK — no vendor model names in `src/`

Spec's "no vendor lock-in" claim, executed: model-router's vendor quartet absent from code.

Commands + output:

```
grep -rn -i "Haiku\|Sonnet\|Opus\|Fable\|anthropic\|openai" src
→ 15-16 src/ai_engineering/ui.py  (prose about TERM=dumb/CI; only hit is "di[fable]" in "diffable")
```

No vendor names in source. TRUE (the only match is the substring "fable" inside
"diffable").

## 21. OK — the user's model names match the spec's own example

Commands + output:

```
grep -n "top\|medium\|low" .ai/config.toml
→ top = "deepseek-v4-flash"; medium = "deepseek-v4-flash"; low = "qwen3.6"
```

Matches "The user's machine configures `deepseek-v4-flash` as `top`/`medium` and
`qwen3.6` as `low`" and the Success example's given config exactly. (Verdict covers the
names only — finding 13 covers the endpoint.)

## 22. OK — "The pin writes nothing on install" (about models)

Commands + output:

```
grep -n "CONFIG_TOML\|models\|guards" src/ai_engineering/skeletons.py
→ 181 CONFIG_TOML = """… [framework] version = "{version}" … [guards] loop_window = 6 …"""
```

The install skeleton written by `ai-eng init` ("Written when they are absent, and never
rewritten", `init.py:617-629`) contains no `[models]` section, so the installer writes
nothing about tiers. TRUE. (The `[models]` section in *this* repo's pin was added by
hand in commit 30f8ec1e, not by install — consistent with the claim.)

## 23. OK — CI and security claims that are about existing machinery

Commands + output:

```
read .github/workflows/check.yml → jobs/check step "the gate, exactly as a developer runs it":
  run: just check | tee "$RUNNER_TEMP/check.log"   (events: push main/v1, pull_request, merge_group)
justfile:101-110 → security: version-checks gitleaks ("gitleaks is …"), trivy
  (Version: 0.73.0), then runs semgrep through the lane contract (scan.baseline)
justfile:143 → check: build sbom lint typecheck test cover security register skilleval evals counts intent-page lenses council map ran
```

`.github/workflows/check.yml` exists and runs the whole gate on every push; `just
security` is gitleaks + trivy + semgrep, pinned, and is part of `just check`. TRUE for
the machinery; the "additionally asserted by their fixtures" half is finding 12.

## 24. OK — the research "grill" concept the spec leans on exists

Commands + output:

```
grep -rn "grill" .ai/research/reports/04-wayfinder/report.md
→ grill.md ← Motor de entrevista: design tree, rounds, checks; "agente termina 'grillándose' solo"; …
grep -rn "grill" .ai/research/reports/03-Loop-Engineering/report.md
→ grill-me → entrevista al usuario
```

The grill/wayfinder interview engine is real research content. ("Capped" is a loose
reading of W-04's frontier-only design-tree rounds, not a cited term.)

---

## What I could not test and why

- **The four example commands** (`pytest -q tests/test_037_model_router.py`, the
  `-k incomplete`, `-k default_tier`, `-k template` runs) — the fixture files do not
  exist; there is nothing to execute. The `2 passed` / `1 passed` counts are goals, not
  observations.
- **Router behaviour** (`route(step, config)`, `bail_out(request)`, the step→tier
  mapping, pure-function/no-network property, stdlib-only property) —
  `src/ai_engineering/model_router.py` does not exist.
- **Degraded mode** (`no [models] → default_tier`) — no router and no `default_tier`
  value anywhere in the tree to return.
- **Intake behaviour** (`validate_intake` PASS/INCOMPLETE, template copy-paste passes)
  — `src/ai_engineering/intake.py` and `specs/new-goal-template.md` do not exist.
- **The nan.builders endpoint** on the user's machine — a machine-level claim; the URL
  appears in no tree file.
- **"The config schema by `tests/test_contracts.py`"** — there is no config schema file
  and no reader; both halves are absent, which is a finding rather than a test gap.
- I deliberately did **not** run `just check`/`just security`/pytest at all: the
  targeted commands' targets do not exist, the suite has inherited `test_madr.py` reds
  (ADR 0025) that would contaminate any run, and sibling critics are editing the tree
  concurrently.

## Counts

- OK: 10 (findings 15–24)
- UNPROVEN: 8 (findings 7–14)
- WRONG: 6 (findings 1–6)
- Total checkable sentences executed: 24. Untested: named above.

Path: `specs/037-model-router-and-intake-validation/challenge.md` (not committed — the
challenge was scoped read-only except this file; the committing step is the main
agent's).