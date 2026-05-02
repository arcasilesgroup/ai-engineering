# Build: HX-11 Verification and Eval Architecture

## Scope

Implemented the canonical verification taxonomy and replayable eval reporting helpers for `spec-117-hx-11`.

## Changes

- Added `src/ai_engineering/verify/taxonomy.py` with stable verification check IDs, primary planes, reporting surfaces, test-shape metadata, eval scenario packs, replay outcomes, and reliability scorecards.
- Mapped existing kernel checkers, validator categories, verify specialists, CI workflows, perf suites, and the seed eval pack into one registry.
- Added registry validation for unique stable IDs, unique current names, and provenance on derived metrics.
- Added `build_seed_eval_pack()` over existing pytest-based scenario material without introducing a second execution engine.
- Added `build_replay_outcome()`, pass@k, pass^k, replay summaries, and `build_reliability_scorecard()` for derived reliability/perf reporting with provenance.
- Extended verify findings with optional `stable_id` and `primary_plane` metadata.
- Routed gate-finding and validator-category verify findings through the canonical taxonomy so verify remains explanatory while carrying stable IDs.

## Boundary

`HX-11` classifies and reports over existing execution outputs. It does not own kernel execution, state-plane truth, context-pack lifecycle, or CI runner semantics.
