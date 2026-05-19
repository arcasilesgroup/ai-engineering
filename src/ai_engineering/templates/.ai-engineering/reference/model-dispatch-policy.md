# Model Dispatch Policy (spec-131 S3 / M5)

> SSOT for `effort:` and `model_tier:` per skill. Consumed by
> `tools/skill_lint/checks/effort.py` (frontmatter enforcement) and
> `.ai-engineering/scripts/spec-131/apply_effort_model_tier.py` (migration).

## Vocabulary (D-131-08)

| `effort:` | `model_tier:` | Intent |
|---|---|---|
| `cheap` | `haiku` | Deterministic execution. Patch-ready plan; no judgment. |
| `mid` | `sonnet` | Synthesis with judgment. Review, brainstorm, debug, narrative. |
| `high` | `opus` | Deep architecture. Decompose, gate, audit, multi-round. |

Investing more in `/ai-plan` (high tier, exhaustive patch-ready output) is
what unlocks cheap-tier execution everywhere downstream. The policy below
codifies the cheap/mid/high decision per skill so the dispatch logic in
`/ai-build` can route mechanically.

## Posture (R-131-09 grace)

* `effort:` enforcement is **blocking** from day one (lint MAJOR on missing
  / invalid / policy-mismatch).
* `model_tier:` enforcement is **observation-only** for one release cycle
  (lint MINOR on missing). The `--enforce-tier` CLI flag on
  `tools/skill_lint` flips it to MAJOR once the dispatch logic has been
  live and audited.

## Mapping (47 skills)

The vocabulary migration is NOT a 1-to-1 rename of the legacy
`medium|high|max` axis. It re-tiers every skill against the dispatch
economics rubric: deterministic execution → cheap, synthesis with judgment
→ mid, deep architecture / multi-round dispatch → high.

| Skill | effort | model_tier | Rationale |
|---|---|---|---|
| ai-analyze-permissions | high | opus | Audit / governance posture — deep judgment. |
| ai-animation | high | opus | Multi-frame design synthesis with motion judgment. |
| ai-autopilot | high | opus | Decomposition into N sub-spec waves; architecture. |
| ai-board | cheap | haiku | Deterministic board sync against work-item refs. |
| ai-brainstorm | mid | sonnet | Synthesis + interrogation; multi-turn judgment. |
| ai-build | cheap | haiku | Executes patch-ready plan; mechanical when patches present. |
| ai-branch-cleanup | cheap | haiku | Mechanical hygiene (rotate `_history.md`, delete shipped). |
| ai-code | mid | sonnet | Targeted code writes with stack-overrides judgment. |
| ai-commit | cheap | haiku | Deterministic stage + compose commit. |
| ai-constitution | mid | sonnet | Interview-driven; project-identity judgment. |
| ai-scaffold | mid | sonnet | Scaffold with framework + convention judgment. |
| ai-debug | mid | sonnet | Reproduce + isolate + fix; targeted judgment. |
| ai-design | high | opus | Deep design space exploration. |
| ai-docs | mid | sonnet | Narrative authoring with placement judgment. |
| ai-reliability-eval | mid | sonnet | Scenario synthesis + scoring. |
| ai-explain | mid | sonnet | Pedagogical narrative; audience-aware. |
| ai-governance | high | opus | Compliance posture; risk acceptance. |
| ai-marketing | mid | sonnet | Go-to-market narrative + positioning. |
| ai-onboard | mid | sonnet | Step-by-step authoring with audience judgment. |
| ai-ide-audit | high | opus | Cross-IDE matrix audit; architectural posture. |
| ai-learn | mid | sonnet | Retro synthesis + lesson extraction. |
| ai-mcp-audit | high | opus | Security skill: coherence analysis + rug-pull detection vs trusted baseline (spec-107 D-107-08). Elevated to `opus` per spec-131 closure (C2) so judgment quality matches the security-impact ceiling. |
| ai-media | mid | sonnet | Media synthesis with style judgment. |
| ai-note | cheap | haiku | Deterministic capture into note store. |
| ai-session-watch | mid | sonnet | Telemetry surface review + reporting. |
| ai-pipeline | mid | sonnet | CI/CD workflow design with stack judgment. |
| ai-plan | high | opus | Deep architecture; exhaustive patch-ready output unlocks cheap downstream. |
| ai-postmortem | mid | sonnet | Incident retro synthesis. |
| ai-pr | mid | sonnet | PR composition + body synthesis. |
| ai-prompt-tune | mid | sonnet | Prompt engineering technique synthesis. |
| ai-research | mid | sonnet | External evidence synthesis (Tier 0-2). |
| ai-resolve-conflicts | cheap | haiku | Deterministic conflict resolution against rules. |
| ai-review | mid | sonnet | 8-agent parallel review + corroboration judgment. |
| ai-schema | mid | sonnet | Schema design + migration synthesis. |
| ai-security | mid | sonnet | Security posture review with threat-model judgment. |
| ai-simplify-sweep | cheap | haiku | Mechanical guard-clause / early-return rewrites. |
| ai-skill-improve | mid | sonnet | Skill refinement; rubric-driven judgment. |
| ai-slides | mid | sonnet | Deck synthesis with narrative judgment. |
| ai-sprint | mid | sonnet | Sprint planning narrative. |
| ai-standup | cheap | haiku | Deterministic per-spec digest from telemetry. |
| ai-start | mid | sonnet | Session bootstrap with context loading. |
| ai-support | mid | sonnet | Support narrative; audience-aware. |
| ai-test | mid | sonnet | Test plan + write + run; judgment on coverage. |
| ai-verify | mid | sonnet | 7-scan IRRV with severity mapping; judgment. |
| ai-video-editing | mid | sonnet | Video assembly with edit-decision judgment. |
| ai-visual | mid | sonnet | Visual synthesis with composition judgment. |
| ai-prose | mid | sonnet | Long-form narrative authoring. |

## Lint contract

`tools/skill_lint/checks/effort.py` parses this table on every run
(cached via `functools.lru_cache`) and cross-checks each skill's declared
frontmatter against its row. Mismatch is MAJOR (effort) or MINOR
(model_tier, during R-131-09 grace).

## Mirror gap

`.github/skills/` deliberately omits `ai-analyze-permissions` (Copilot
surface intentionally excludes it). The lint and the migration script
both treat this as an allow-listed gap, not a violation.
