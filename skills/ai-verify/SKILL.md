---
name: ai-verify
description: >-
  Use when work has to be verified — "verify the feature", "did we build what
  was asked", "review this diff", "is it ready to commit" — by choosing the
  right verification tier (standalone, embedded, or chain) and producing
  verdicts with evidence, not impressions. Not for milestone-declared security
  audits — use /ai-security. Not for diagnosing a failure — use /ai-debug.
license: LicenseRef-Attributed
---

# ai-verify — verification in three tiers (Graph Engineering)

Three ways to verify, depending on who fires them: skills you run on purpose,
skills that fire themselves mid-workflow, and a chain of review lanes. The
chain's router decides which lanes run from the evidence in the diff, never
from its size.

### Tier 1 — standalone (you run it on purpose)

- Per-requirement verdict against what was actually asked, with a list of gaps → [tiers/1-standalone/verify-feature/SKILL.md](tiers/1-standalone/verify-feature/SKILL.md)
- Extract the requirements from the conversation into numbered, falsifiable claims → [tiers/1-standalone/spec-extract/SKILL.md](tiers/1-standalone/spec-extract/SKILL.md)

### Tier 2 — embedded (fires by itself, mid-workflow)

- Browser verification of the finished feature + blast radius of the routes that depend on the change → [tiers/2-embedded/feature-verify/SKILL.md](tiers/2-embedded/feature-verify/SKILL.md), with [blast_radius.py](tiers/2-embedded/feature-verify/scripts/blast_radius.py), [setup_harness.sh](tiers/2-embedded/feature-verify/scripts/setup_harness.sh) and [references/](tiers/2-embedded/feature-verify/references/)
- A second opinion from a fresh model instance with no visibility into your reasoning → [tiers/2-embedded/second-opinion/SKILL.md](tiers/2-embedded/second-opinion/SKILL.md)

### Tier 3 — chain (review lanes picked by evidence)

- Router that picks lanes, estimates cost, and executes → [tiers/3-chain/review-router/SKILL.md](tiers/3-chain/review-router/SKILL.md)
- Lanes: [code-audit](tiers/3-chain/code-audit/SKILL.md) · [security-audit](tiers/3-chain/security-audit/SKILL.md) · [a11y-audit](tiers/3-chain/a11y-audit/SKILL.md) · [perf-audit](tiers/3-chain/perf-audit/SKILL.md) · [design-check](tiers/3-chain/design-check/SKILL.md) · [build-check](tiers/3-chain/build-check/SKILL.md)
- Merge of all lanes into one deduplicated report → [full-review](tiers/3-chain/full-review/SKILL.md); scope and diff conventions → [CONVENTIONS.md](tiers/3-chain/_support/review/CONVENTIONS.md)

Setup guide and entry router → [VERIFICATION-SETUP-GUIDE.md](VERIFICATION-SETUP-GUIDE.md). Evals (plant real bugs and score the reviewer) → [evals/README.md](evals/README.md): [plant.py](evals/scripts/plant.py), [score.py](evals/scripts/score.py), [bug-catalog.md](evals/bug-catalog.md), example pack [answer-key.json](evals/packs/example-node-web/answer-key.json).

Source: Graph Engineering — Verification Skills (skills from the video, generalized to any stack; attributed, no license — issue H4; no public repo declared in the source).

## The ai-engineering seam

1. The router picks the tier using the source's taxonomy.
2. The judge runs at tier `decide`; the model comes from the ai-engineering `config.toml` pin. Binary checks run at tier `verify`.
3. The evals (`plant.py`/`score.py`) run in ai-engineering's own CI, not in the user's project.
4. Outputs: verdicts land in the EVIDENCE section of `.ai-engineering/spec.html`, plus a receipt.
