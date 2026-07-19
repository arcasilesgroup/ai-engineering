# Model Dispatch Policy (spec-131 S3 / M5; spec-189 D-189-04)

> SSOT for `effort:` per skill. Consumed by
> `tools/skill_lint/checks/effort.py` (frontmatter enforcement).

## Vocabulary (D-131-08)

| `effort:` | Intent |
|---|---|
| `cheap` | Deterministic execution. Patch-ready plan; no judgment. |
| `mid` | Synthesis with judgment. Review, brainstorm, debug, narrative. |
| `high` | Deep architecture. Decompose, gate, audit, multi-round. |

Investing more in `/ai-plan` (high effort, exhaustive patch-ready output) is
what unlocks cheap-effort execution everywhere downstream. The policy below
codifies the cheap/mid/high decision per skill so the dispatch logic in
`/ai-build` can route mechanically.

## Posture

`effort:` enforcement is **blocking** (lint MAJOR on missing / invalid /
policy-mismatch). Per spec-189 (D-189-04) `effort` is the sole skill dispatch
axis — the former per-model tier field is retired fleet-wide, so agents own
their `model:` declaration independently.

## Mapping (47 skills)

The vocabulary migration is NOT a 1-to-1 rename of the legacy
`medium|high|max` axis. It re-tiers every skill against the dispatch
economics rubric: deterministic execution → cheap, synthesis with judgment
→ mid, deep architecture / multi-round dispatch → high.

| Skill | effort | Rationale |
|---|---|---|
| ai-animation | high | Multi-frame design synthesis with motion judgment. |
| ai-autopilot | high | Decomposition into N sub-spec waves; architecture. |
| ai-board | cheap | Deterministic board sync against work-item refs. |
| ai-brainstorm | mid | Synthesis + interrogation; multi-turn judgment. |
| ai-build | cheap | Executes patch-ready plan; mechanical when patches present. |
| ai-branch-cleanup | cheap | Mechanical hygiene (rotate `_history.md`, delete shipped). |
| ai-code | mid | Targeted code writes with stack-overrides judgment. |
| ai-commit | cheap | Deterministic stage + compose commit. |
| ai-constitution | mid | Interview-driven; project-identity judgment. |
| ai-scaffold | mid | Scaffold with framework + convention judgment. |
| ai-debug | mid | Reproduce + isolate + fix; targeted judgment. |
| ai-design | high | Deep design space exploration. |
| ai-docs | mid | Narrative authoring with placement judgment. |
| ai-reliability-eval | mid | Scenario synthesis + scoring. |
| ai-explain | mid | Pedagogical narrative; audience-aware. |
| ai-governance | high | Compliance posture; risk acceptance. |
| ai-marketing | mid | Go-to-market narrative + positioning. |
| ai-fundraising | mid | Investor narrative + market-sizing + financial-model judgment. |
| ai-onboard | mid | Step-by-step authoring with audience judgment. |
| ai-ide-audit | high | Cross-IDE matrix audit; architectural posture. |
| ai-learn | mid | Retro synthesis + lesson extraction. |
| ai-mcp-audit | high | Security skill: coherence analysis + rug-pull detection vs trusted baseline (spec-107 D-107-08). Elevated to `high` per spec-131 closure (C2) so judgment quality matches the security-impact ceiling. |
| ai-media | mid | Media synthesis with style judgment. |
| ai-note | cheap | Deterministic capture into note store. |
| ai-session-watch | mid | Telemetry surface review + reporting. |
| ai-pipeline | mid | CI/CD workflow design with stack judgment. |
| ai-plan | high | Deep architecture; exhaustive patch-ready output unlocks cheap downstream. |
| ai-postmortem | mid | Incident retro synthesis. |
| ai-pr | mid | PR composition + body synthesis. |
| ai-prompt-tune | mid | Prompt engineering technique synthesis. |
| ai-research | mid | External evidence synthesis (Tier 0-2). |
| ai-resolve-conflicts | cheap | Deterministic conflict resolution against rules. |
| ai-review | mid | 8-agent parallel review + corroboration judgment. |
| ai-schema | mid | Schema design + migration synthesis. |
| ai-security | mid | Security posture review with threat-model judgment. |
| ai-simplify-sweep | cheap | Mechanical guard-clause / early-return rewrites. |
| ai-skill-improve | mid | Skill refinement; rubric-driven judgment. |
| ai-slides | mid | Deck synthesis with narrative judgment. |
| ai-sprint | mid | Sprint planning narrative. |
| ai-standup | cheap | Deterministic per-spec digest from telemetry. |
| ai-start | mid | Session bootstrap with context loading. |
| ai-support | mid | Support narrative; audience-aware. |
| ai-test | mid | Test plan + write + run; judgment on coverage. |
| ai-verify | mid | 7-scan IRRV with severity mapping; judgment. |
| ai-video-editing | mid | Video assembly with edit-decision judgment. |
| ai-visual | mid | Visual synthesis with composition judgment. |
| ai-prose | mid | Long-form narrative authoring. |

## Lint contract

`tools/skill_lint/checks/effort.py` parses this table on every run and
cross-checks each skill's declared frontmatter against its row. Mismatch is
MAJOR.

## Mirror gap

`.github/skills/` omits any Claude-Code-only skill (those marked
`copilot_compatible: false`). The lint treats such an absence as an
allow-listed gap, not a violation. No skill currently uses this scoping.
