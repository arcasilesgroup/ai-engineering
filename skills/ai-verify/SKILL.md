---
name: ai-verify
description: >-
  Use when work has to be verified — "verify the feature", "did we build what
  was asked", "review this diff", "is it ready to commit", or when the user
  wants over-engineering findings or a debt ledger. Choose the right
  verification tier and produce verdicts with evidence, not impressions.
  Not for milestone-declared security audits — use /ai-security. Not for
  diagnosing a failure — use /ai-debug.
license: Apache-2.0
---

# ai-verify — verification in three tiers (Graph Engineering)

Three ways to verify, depending on who fires them: lanes you run on purpose,
lanes that run themselves mid-workflow, and a chain of review lanes. Every lane is a file in
`lanes/`: read it when its line below is the one you need. The
chain's router decides which lanes run from the evidence in the diff, never
from its size.

### Tier 1 — standalone (you run it on purpose)

- Per-requirement verdict against what was actually asked, with a list of gaps → [lanes/verify-feature.md](lanes/verify-feature.md)
- Extract the requirements from the conversation into numbered, falsifiable claims → [lanes/spec-extract.md](lanes/spec-extract.md)

### Tier 2 — embedded (fires by itself, mid-workflow)

- Browser verification of the finished feature + blast radius of the routes that depend on the change → [lanes/feature-verify.md](lanes/feature-verify.md), with `scripts/blast_radius.ts`, `scripts/setup_harness.sh` and `references/feature-verify/`
- A second opinion from a fresh model instance with no visibility into your reasoning → [lanes/second-opinion.md](lanes/second-opinion.md), with `scripts/second-opinion.sh`

### Tier 3 — chain (review lanes picked by evidence)

- Router that picks lanes, estimates cost, and executes → [lanes/review-router.md](lanes/review-router.md)
- Lanes: [code-audit](lanes/code-audit.md) · [security-audit](lanes/security-audit.md) · [a11y-audit](lanes/a11y-audit.md) · [perf-audit](lanes/perf-audit.md) · [design-check](lanes/design-check.md) · [build-check](lanes/build-check.md)
- Merge of all lanes into one deduplicated report → [lanes/full-review.md](lanes/full-review.md); shared lane conventions are in `references/review/CONVENTIONS.md`

Setup guide and entry router → [VERIFICATION-SETUP-GUIDE.md](VERIFICATION-SETUP-GUIDE.md). The internal eval fixtures apply real bugs and score the reviewer in ai-engineering's own tests.

## Lifecycle

Lane: light, standard, full
Writes: the verdict, and the open checkpoint's review notes when one exists
Read by: CI, the human
Dies: with the milestone
Next: ai-security when the security trigger fired; ai-write when the public interface changed; ai-visual-recap otherwise

Source: the Graph Engineering verification-skills lineage, generalized to any stack and supplied by the maintainer (rights attested 2026-11-06, see NOTICE.md).

## The ai-engineering seam

1. The router picks the tier using the source's taxonomy.
2. The judge runs at tier `decide`; the model comes from the ai-engineering `config.toml` pin. Binary checks run at tier `verify`.
3. The evals (`tests/fixtures/verify-tiers/evals/scripts/apply-pack.ts` and `score.ts`) run in ai-engineering's own CI, not in the user's project.
4. Outputs: the verdict is the report. When a checkpoint is open, the same verdict
   is written into that checkpoint's review notes. Style follows
   [ai-brainstorm › references/artifact-design.md](../ai-brainstorm/references/artifact-design.md).

## Over-engineering review and debt collection

Use this route for "review code", "code review", "find over-engineering", "check for bloat", or "what can we simplify". It is distinct from judging whether requirements were met: use the verification tiers above for correctness.

### Diff review (default)

Review the current PR, branch, or requested diff against the AGENTS.md code style rules. Return ranked findings, one line each: location, problem, fix.

```text
src/utils/parser.ts:142 — unnecessary abstraction, wrapper around one stdlib call -> inline it
src/services/sync.ts:87-94 — generic name hides purpose -> rename it to describe the value
```

### Debt collection

Use `/ai-verify --debt` or "collect debt", "list deferred shortcuts", or "what did we defer". Scan the codebase for `todo:` comments and return a structured ledger with file, line, comment, and category (`lock`, `perf`, `simplification`, `test`, `correctness`, or `other`).

For both modes, check findings against the AGENTS.md code style rules: KISS, YAGNI, DRY, early returns, one function/one job, purpose-named values, comments that explain why, and the shortest working solution. Cite the applicable rule in each finding. Do not refactor working code or report a style preference without a concrete improvement.
