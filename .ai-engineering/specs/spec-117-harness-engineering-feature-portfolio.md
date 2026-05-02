# Spec 117 Feature Portfolio - Follow-on Implementation Specs

This file turns the umbrella spec into a concrete portfolio of follow-on implementation specs. The portfolio is now closed: `HX-01` through `HX-12` have reached terminal `done` status and the spec-117 task ledger has no remaining non-done tasks.

## Portfolio Closure

The implementation portfolio completed as the serialized harness-engineering refactor program. Final closure evidence is recorded in the task ledger, `current-summary.md`, and the `spec-117-progress` proof packets for each HX slice.

## Portfolio Matrix

| ID | Proposed Spec | Main Outcome | Primary Write Scope | Depends On | Parallelization | Exit Gate |
| --- | --- | --- | --- | --- | --- | --- |
| `HX-01` | Control Plane Normalization | One canonical governance/control model with explicit artifact planes and provenance. | `.ai-engineering/manifest.yml`, control docs, validators, templates | spec-117 only | Can overlap partially with `HX-02` after inventory | Artifact-plane taxonomy and provenance validator are real. |
| `HX-02` | Work Plane and Task Ledger | Spec-scoped task ledger, active pointer, handoffs, evidence, current/history summaries. | `.ai-engineering/specs/**`, CLI, validators, templates | `HX-01` minimal taxonomy | Foundational; should land early and mostly serial | Orchestrators can consume task packets and handoff refs. |
| `HX-03` | Mirror Local Reference Model | Provider-local mirror references, generated provenance, and slimmer public agent surface. | generators, canonical skills/agents, mirrors, templates, tests | `HX-01`, `HX-02` | Can run in parallel with `HX-04` design work | Non-Claude mirrors have no `.claude` leaks and provenance is enforced. |
| `HX-04` | Harness Kernel Unification | One authoritative gate/check engine and one `ai-eng harness check`. | policy engine, CLI, validators, hooks, tests | `HX-02` | Kernel core should serialize | One engine owns findings, mode resolution, failure output, and retry handling. |
| `HX-05` | State Plane and Observability Normalization | Durable truth vs residue split, normalized event vocabulary, task traces, scorecards. | state, observability, CLI reports, tests | `HX-02`, `HX-04` | Can overlap with `HX-06` if state ownership is clear | Task lifecycle events and scorecards exist on a clean schema. |
| `HX-06` | Multi-Agent Capability Contracts | Capability cards, write scopes, tool scopes, topology classification, integration gates. | manifest metadata, orchestrators, schemas, validators, docs/tests | `HX-02` | Parallel with portions of `HX-03` and `HX-05` | Parallel work is blocked unless write scopes and artifacts are valid. |
| `HX-07` | Context Packs and Learning Funnel | Deterministic task context packs and governed lessons/instincts/proposals lifecycle. | contexts, CLI, validators, notes/instincts flows | `HX-02`, `HX-05`, `HX-06` | Can overlap with `HX-08` planning | Context packs and handoff compaction rules are implemented. |
| `HX-08` | Runtime Core Extraction - Track A | Manifest/state repository unification. | `src/ai_engineering/config/**`, `state/**`, tests | `HX-04`, `HX-05` | Serialize with other runtime tracks unless proven disjoint | One repository/projection model replaces split loaders. |
| `HX-09` | Runtime Core Extraction - Track B | Reconciler engine for install/doctor/update. | installer/doctor/updater modules, tests | `HX-04`, `HX-06` | Serialize with `HX-08` and `HX-10` by default | Install, inspect, repair, and update share one engine. |
| `HX-10` | Runtime Core Extraction - Track C | Thin CLI adapters and asset/runtime split. | `cli_commands/**`, templates, hooks, tests | `HX-03`, `HX-04`, `HX-08` | Serialize with `HX-08` and `HX-09` | CLI commands stop owning broad domain mutation and template logic duplication is reduced. |
| `HX-11` | Verification and Eval Architecture | Check classification, eval scenario packs, large test splits, perf baselines. | tests, verify flows, report modules | `HX-04`, `HX-05`, `HX-07` | Can overlap with docs work | Kernel checks, repo-governance checks, evals, and shell checks are distinct and measurable. |
| `HX-12` | Engineering Standards and Legacy Retirement | Canonical clean-engineering docs, migration docs, and family-by-family legacy deletion. | docs, contexts, review/verify rubrics, legacy surface families | `HX-03` through `HX-11` depending on family | Mostly late-wave and serialized by deletion family | Standards are codified and at least one legacy family is retired with parity proof. |

## Recommended Sequence

1. `HX-01` then `HX-02`.
2. `HX-03` and `HX-06`.
3. `HX-04` then `HX-05`.
4. `HX-07` and `HX-11`.
5. `HX-08`, `HX-09`, `HX-10` one track at a time.
6. `HX-12` as the program closure layer.

## Safe Parallel Bundles

- Bundle A: `HX-01` discovery work and `HX-02` design work once artifact taxonomy is stabilizing.
- Bundle B: `HX-03` generator/provenance work and `HX-06` capability/tool-scope work.
- Bundle C: `HX-07` context-pack implementation and `HX-11` eval/test-shape work once task traces exist.
- Bundle D: parts of `HX-12` docs work can overlap with late runtime tracks once names and artifacts are stable.

## Serialization Rules

- Runtime core tracks `HX-08`, `HX-09`, and `HX-10` serialize unless import and write scopes are provably disjoint.
- Event-emitting validations and audit-chain writers run sequentially.
- Mirror sync and mirror validation remain serialized.
- Hook and kernel changes serialize with guard review.

## Suggested First Approval Package

If the user wants the first real implementation package after this brainstorm, approve these together or back-to-back:

- `HX-01` Control Plane Normalization.
- `HX-02` Work Plane and Task Ledger.

That pair gives the whole refactor a durable filesystem backbone before any risky runtime rewrites start.