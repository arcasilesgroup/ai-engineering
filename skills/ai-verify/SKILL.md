---
name: ai-verify
description: >-
  Use when work has to be verified — "verify the feature", "did we build what
  was asked", "review this diff", "is it ready to commit", or when the user
  wants over-engineering findings or a debt ledger. Choose the right
  verification tier and produce verdicts with evidence, not impressions.
  Not for milestone-declared security audits — use /ai-security. Not for
  diagnosing a failure — use /ai-debug.
license: LicenseRef-Attributed
---

# ai-verify — verification in three tiers (Graph Engineering)

Three ways to verify, depending on who fires them: skills you run on purpose,
skills that fire themselves mid-workflow, and a chain of review lanes. The
chain's router decides which lanes run from the evidence in the diff, never
from its size.

### Tier 1 — standalone (you run it on purpose)

- Per-requirement verdict against what was actually asked, with a list of gaps → `verify-feature`
- Extract the requirements from the conversation into numbered, falsifiable claims → `spec-extract`

### Tier 2 — embedded (fires by itself, mid-workflow)

- Browser verification of the finished feature + blast radius of the routes that depend on the change → `feature-verify`, with its scripts and references
- A second opinion from a fresh model instance with no visibility into your reasoning → `second-opinion`

### Tier 3 — chain (review lanes picked by evidence)

- Router that picks lanes, estimates cost, and executes → `review-router`
- Lanes: `code-audit` · `security-audit` · `a11y-audit` · `perf-audit` · `design-check` · `build-check`
- Merge of all lanes into one deduplicated report → `full-review`; shared lane conventions are in `references/review/CONVENTIONS.md`

Setup guide and entry router → [VERIFICATION-SETUP-GUIDE.md](VERIFICATION-SETUP-GUIDE.md). The internal eval fixtures apply real bugs and score the reviewer in ai-engineering's own tests.

## Lifecycle

Lane: light, standard, full
Writes: the verdict, and the open checkpoint's review notes when one exists
Read by: CI, the human
Dies: with the milestone
Next: ai-security when the security trigger fired; ai-write when the public interface changed; ai-visual-recap otherwise

Source: Graph Engineering — Verification Skills (skills from the video, generalized to any stack; attributed, no license — issue H4; no public repo declared in the source).

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
