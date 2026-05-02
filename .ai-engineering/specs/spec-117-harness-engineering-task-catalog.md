# Spec 117 Task Catalog - Harness Engineering Root Refactor Program

This catalog decomposes spec-117 into features, tasks, dependencies, suggested agent ownership, and acceptance gates. It is designed for multi-session and multi-agent execution across the whole ai-engineering framework.

## Agent Ownership Model

Use the existing ai-engineering roles:

- `plan`: produces scoped specs and plans; does not implement.
- `explore`: read-only codebase research and inventories.
- `build`: only code-writing agent.
- `verify`: deterministic and evidence-first verification.
- `review`: code review and architecture/quality findings.
- `guard`: governance and ownership advisory.
- `simplify`: background cleanup only after explicit scope and gates.
- `run-orchestrator`: backlog-scale orchestrator that should eventually consume the same task packet model as `dispatch` and `autopilot`.

Every task that writes files must declare:

- write scope;
- blocked-by dependencies;
- acceptance evidence;
- handoff file path;
- rollback or cleanup expectations.

Recommended handoff convention:

- Exploration: `.ai-engineering/specs/spec-117-progress/explore_<topic>.md`
- Build task: `.ai-engineering/specs/spec-117-progress/build_<task-id>.md`
- Review task: `.ai-engineering/specs/spec-117-progress/review_<task-id>.md`
- Verify task: `.ai-engineering/specs/spec-117-progress/verify_<task-id>.md`
- Blocked state: `.ai-engineering/specs/spec-117-progress/blocked_<task-id>.md`
- Attachments: `.ai-engineering/specs/spec-117-progress/artifacts/<task-id>/...`

Subagents should return only:

`done -> .ai-engineering/specs/spec-117-progress/<file>.md`

or:

`blocked -> .ai-engineering/specs/spec-117-progress/blocked_<task-id>.md`

## Feature F0 - Program Baseline

Purpose: persist the root-refactor program context, future-spec portfolio, and task catalog so later sessions do not rediscover the same architecture facts.

### Tasks

- **T0.1 - Persist root-refactor context pack**
  - Agent: build.
  - Write scope: `.ai-engineering/specs/spec-117-harness-engineering-context-pack.md`.
  - Acceptance: research synthesis, reference lessons, fresh exploration findings, stable seams, rewrite candidates, and known/assumed/unknown map are present.

- **T0.2 - Persist canonical umbrella spec**
  - Agent: build.
  - Write scope: `.ai-engineering/specs/spec-117-harness-engineering-refactor-roadmap.md`, `.ai-engineering/specs/spec.md`.
  - Acceptance: draft spec reflects full-program root refactor, not only incremental harness hardening.

- **T0.3 - Persist task catalog**
  - Agent: build.
  - Write scope: `.ai-engineering/specs/spec-117-harness-engineering-task-catalog.md`.
  - Acceptance: feature tracks, dependencies, ownership, and wave plan are present.

- **T0.4 - Persist future-spec portfolio**
  - Agent: build.
  - Write scope: `.ai-engineering/specs/spec-117-harness-engineering-feature-portfolio.md`.
  - Acceptance: follow-on implementation specs are defined with scopes, dependencies, and exit gates.

## Feature F1 - Control Plane Normalization

Purpose: make canonical governance and artifact ownership explicit so the repo has one real control plane.

### Tasks

- **T1.1 - Inventory control surfaces**
  - Agent: explore.
  - Write scope: `.ai-engineering/specs/spec-117-progress/explore_control_plane.md`.
  - Reads: root governance docs, `.ai-engineering/manifest.yml`, templates, overlays, ownership metadata.
  - Acceptance: identifies constitutions, manifests, ownership maps, canonical overlays, derived surfaces, and active collisions.

- **T1.2 - Resolve dual-constitution model**
  - Agent: plan.
  - Write scope: spec/update only.
  - Blocked by: T1.1.
  - Acceptance: decides whether `.ai-engineering/CONSTITUTION.md` is deleted, renamed, reduced, or retained with a non-constitutional role.

- **T1.3 - Define artifact-plane taxonomy schema**
  - Agent: build.
  - Write scope: `.ai-engineering/schemas/`, `.ai-engineering/contexts/`, validators/tests.
  - Blocked by: T1.1.
  - Acceptance: schema classifies artifact plane, canonical source, generated/manual status, owner, lifecycle, and reason to exist.

- **T1.4 - Add artifact inventory and provenance validator**
  - Agent: build.
  - Write scope: validator category, tests.
  - Blocked by: T1.3.
  - Acceptance: missing provenance, missing artifact plane, and ambiguous ownership are reported deterministically.

- **T1.5 - Produce keep / rename / merge / delete report**
  - Agent: build.
  - Write scope: `.ai-engineering/specs/spec-117-progress/build_t1-5.md` or state/report artifact.
  - Blocked by: T1.4.
  - Acceptance: report lists candidate removals and explicitly marks that no deletion happens yet.

- **T1.6 - Split canonical vs derived manifest-adjacent surfaces**
  - Agent: build.
  - Write scope: manifest consumers, generated inventories, tests.
  - Blocked by: T1.2 and T1.4.
  - Acceptance: canonical config remains machine-readable while derived capability or ownership snapshots are clearly generated or on-demand.

Parallelization: T1.1 can run immediately. T1.3 and T1.2 can overlap once inventory exists. T1.4-T1.6 are sequential around schema ownership.

## Feature F2 - Work Plane Normalization

Purpose: replace the current mixed active-buffer model with a spec-scoped work plane that later agents can resume reliably.

### Tasks

- **T2.1 - Define spec-scoped work-plane contract**
  - Agent: plan.
  - Write scope: spec/update only.
  - Acceptance: contract defines active pointer, spec-local directory structure, task ledger, handoffs, evidence, current summary, and history summary.

- **T2.2 - Define task-ledger schema and fixtures**
  - Agent: build.
  - Write scope: `.ai-engineering/schemas/`, `tests/fixtures/`.
  - Blocked by: T2.1.
  - Acceptance: valid and invalid ledger fixtures exist.

- **T2.3 - Add active-pointer and work-plane CLI flows**
  - Agent: build.
  - Write scope: CLI modules/tests.
  - Blocked by: T2.1.
  - Acceptance: commands can initialize a spec work plane, point the active spec, and show current/history summaries.

- **T2.4 - Add task-ledger lifecycle commands**
  - Agent: build.
  - Write scope: CLI modules/tests.
  - Blocked by: T2.2 and T2.3.
  - Acceptance: commands can create, start, block, complete, and validate tasks with write scopes and dependencies.

- **T2.5 - Add handoff and evidence templates**
  - Agent: build.
  - Write scope: templates/docs.
  - Blocked by: T2.2.
  - Acceptance: build, review, verify, blocked, current, and history templates exist.

- **T2.6 - Add task-ledger validation**
  - Agent: build.
  - Write scope: validator category/tests.
  - Blocked by: T2.4 and T2.5.
  - Acceptance: duplicate overlapping writes, missing artifacts, invalid dependencies, and invalid terminal states are detected.

- **T2.7 - Wire work plane into dispatch / autopilot / run**
  - Agent: build.
  - Write scope: canonical skills/agents plus generated mirrors after sync.
  - Blocked by: T2.6.
  - Acceptance: all orchestrators can emit task packets and consume handoff refs rather than raw long-form chat output.

Parallelization: T2.2, T2.3, and T2.5 can partially overlap after T2.1. T2.4-T2.7 are sequential.

## Feature F3 - Instruction and Mirror Architecture Rewrite

Purpose: turn instruction surfaces into concise contracts and make mirrors provider-local, generated, and auditable.

### Tasks

- **T3.1 - Measure instruction surfaces and reference leaks**
  - Agent: explore.
  - Write scope: `.ai-engineering/specs/spec-117-progress/explore_instruction_surfaces.md`.
  - Acceptance: line counts, stale anchors, `.claude`-path leaks, top offenders, and provider-specific drift are documented.

- **T3.2 - Define public vs internal agent/skill surface**
  - Agent: plan.
  - Write scope: spec/update only.
  - Blocked by: T3.1.
  - Acceptance: first-class public agents are distinguished from internal review/verify specialists.

- **T3.3 - Rewrite mirror-local reference model**
  - Agent: build.
  - Write scope: generator, canonical skills/agents, templates, tests.
  - Blocked by: T3.2.
  - Acceptance: non-Claude mirrors no longer depend on `.claude`-specific references.

- **T3.4 - Enforce generated provenance**
  - Agent: build.
  - Write scope: generators, templates, validators/tests.
  - Blocked by: T3.3.
  - Acceptance: generated files declare origin, do-not-edit status, and generated classification consistently.

- **T3.5 - Render root overlays from manifest truth**
  - Agent: build.
  - Write scope: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, Copilot instructions, templates/generators, tests.
  - Blocked by: T3.2.
  - Acceptance: counts, anchors, and grouped views are manifest-driven or explicitly generated.

- **T3.6 - Evaluate install-time mirror generation**
  - Agent: explore then plan.
  - Write scope: progress/spec only.
  - Acceptance: recommends whether checked-in provider mirror trees can be replaced by install-time generation.

- **T3.7 - Collapse internal specialist agent sprawl**
  - Agent: build.
  - Write scope: canonical agent docs, skill references, generated mirrors/tests.
  - Blocked by: T3.2 and T3.4.
  - Acceptance: internal reviewer/verifier specialists move behind a registry or internal prompt system rather than a sprawling public surface.

Parallelization: T3.3 and T3.4 are tightly coupled. T3.5 can overlap once the public/internal surface is decided. T3.6 is read-only and can run in parallel.

## Feature F4 - Harness Kernel Unification

Purpose: make one deterministic kernel authoritative for checks, findings, failure output, retry policy, and loop handling.

### Tasks

- **T4.1 - Map verification authority**
  - Agent: explore.
  - Write scope: `.ai-engineering/specs/spec-117-progress/explore_harness_kernel.md`.
  - Acceptance: classifies legacy gates, newer orchestrator, validator categories, verify service, hooks, and CI by responsibility and overlap.

- **T4.2 - Define kernel boundary and artifact contracts**
  - Agent: plan.
  - Write scope: spec/update only.
  - Blocked by: T4.1.
  - Acceptance: defines authoritative engine, check registration, result envelope, and handoff to shell/CI layers.

- **T4.3 - Converge on one gate engine**
  - Agent: build.
  - Write scope: policy engine, adapters, tests.
  - Blocked by: T4.2.
  - Acceptance: legacy and new flows are unified or clearly adapted to one kernel.

- **T4.4 - Add `ai-eng harness check`**
  - Agent: build.
  - Write scope: CLI modules/tests.
  - Blocked by: T4.3.
  - Acceptance: composed readiness check exists with stable profiles and concise output.

- **T4.5 - Make failures LLM-readable and action-oriented**
  - Agent: build.
  - Write scope: kernel/report formatters/tests.
  - Blocked by: T4.4.
  - Acceptance: failures say what failed, why it matters, what to do next, and which files are affected.

- **T4.6 - Add retry / loop / blocked-state handling**
  - Agent: build.
  - Write scope: kernel/lifecycle/state/tests.
  - Blocked by: T4.4 and T2.
  - Acceptance: repeated failures can promote a task into blocked state with evidence.

- **T4.7 - Protect harness configuration surfaces**
  - Agent: build with guard review.
  - Write scope: policy engine, validators, hooks, tests.
  - Blocked by: T4.4.
  - Acceptance: accidental edits to hooks, mirrors, generated files, or protected config surfaces are caught deterministically.

Parallelization: T4.5-T4.7 can overlap after T4.4 if write scopes are separated.

## Feature F5 - State Plane and Observability Normalization

Purpose: separate durable truth from runtime residue and turn the event stream into a clean task-level observability surface.

### Tasks

- **T5.1 - Inventory state-plane surfaces**
  - Agent: explore.
  - Write scope: `.ai-engineering/specs/spec-117-progress/explore_state_plane.md`.
  - Acceptance: classifies decisions, event stream, install/runtime state, caches, last findings, spec-local evidence, and observation logs.

- **T5.2 - Normalize event vocabulary and schema**
  - Agent: build.
  - Write scope: event schema, emitters, tests.
  - Blocked by: T5.1.
  - Acceptance: provider names and event enums are canonical across validators, emitters, hooks, and tests.

- **T5.3 - Move spec-local evidence out of global state**
  - Agent: build.
  - Write scope: state paths, spec work plane, tests.
  - Blocked by: T2 and T5.1.
  - Acceptance: spec-local audit or classification artifacts live under their owning spec, not as global state peers.

- **T5.4 - Create runtime residue / cache model**
  - Agent: build.
  - Write scope: state layout, maintenance/GC policy, tests.
  - Blocked by: T5.1.
  - Acceptance: caches and ephemeral findings have a separate tree and retention policy.

- **T5.5 - Add task trace schema and emission**
  - Agent: build.
  - Write scope: state/observability, task ledger integrations, tests.
  - Blocked by: T2 and T5.2.
  - Acceptance: task start/block/complete/review/verify artifacts emit traceable lifecycle events.

- **T5.6 - Add harness scorecard and reports**
  - Agent: build.
  - Write scope: CLI/report modules/tests.
  - Blocked by: T5.5.
  - Acceptance: task resolution, retry, rework, verification tax, context-pack size, and drift counts are reported.

- **T5.7 - Encode safe validation sequencing**
  - Agent: build.
  - Write scope: docs, task flows, or locking logic/tests.
  - Blocked by: T4.4 and T5.5.
  - Acceptance: mirror sync ordering and event-chain-safe validation sequencing are enforced or made explicit in the kernel/shell.

Parallelization: T5.2 and T5.4 can overlap after inventory. T5.5-T5.7 are sequential around observability ownership.

## Feature F6 - Multi-Agent Execution Contracts

Purpose: make parallel execution safe through explicit agent capability cards, write scopes, tool scopes, and topology rules.

### Tasks

- **T6.1 - Define agent capability cards**
  - Agent: plan.
  - Write scope: specs/context.
  - Acceptance: each first-class agent has input contract, output contract, escalation rule, allowed write/read scope, and default tools.

- **T6.2 - Define task packet contract**
  - Agent: plan.
  - Write scope: specs/context.
  - Blocked by: T2 and T6.1.
  - Acceptance: task packets include owner, mode, dependency edges, read scope, write scope, checks, retry budget, and artifact refs.

- **T6.3 - Add write-scope taxonomy**
  - Agent: build.
  - Write scope: schemas/manifest metadata/tests.
  - Blocked by: T6.1.
  - Acceptance: shared control-plane, work-plane, state-plane, docs, and runtime write scopes are machine-readable.

- **T6.4 - Add topology classification**
  - Agent: build.
  - Write scope: orchestrators, task-ledger logic, tests.
  - Blocked by: T6.2 and T6.3.
  - Acceptance: tasks classify as sequential, parallel, hierarchical, blocked, or cascade-blocked.

- **T6.5 - Add tool-scope policy**
  - Agent: build.
  - Write scope: manifest/agent metadata, docs/tests.
  - Blocked by: T6.1.
  - Acceptance: default tool sets are small and task-scoped; expansions are explicit.

- **T6.6 - Add integration gate for overlapping writes and missing handoffs**
  - Agent: build.
  - Write scope: validators/policy/tests.
  - Blocked by: T6.4.
  - Acceptance: overlapping write scopes, skipped review/verify, and broken artifact refs are blocked.

- **T6.7 - Evaluate worktree isolation policy**
  - Agent: explore then plan.
  - Write scope: progress/spec only.
  - Acceptance: recommends always-on, conditional, or deferred worktree isolation for shared-runtime edits.

Parallelization: T6.3 and T6.5 can overlap after T6.1. T6.4 and T6.6 are sequential. T6.7 is independent.

## Feature F7 - Context and Memory Lifecycle

Purpose: make context compact, durable, and auditable without turning learning artifacts into an uncontrolled second source of truth.

### Tasks

- **T7.1 - Map memory surfaces**
  - Agent: explore.
  - Write scope: `.ai-engineering/specs/spec-117-progress/explore_memory.md`.
  - Acceptance: maps working memory, episodic memory, semantic memory, procedural memory, and the current learning funnel.

- **T7.2 - Define task context-pack contract**
  - Agent: plan.
  - Write scope: spec/update only.
  - Blocked by: T7.1 and T2.
  - Acceptance: context packs specify exactly which files and prior artifacts enter a task.

- **T7.3 - Implement context-pack generator**
  - Agent: build.
  - Write scope: CLI modules/templates/tests.
  - Blocked by: T7.2.
  - Acceptance: deterministic context packs can be generated from the work plane and control plane.

- **T7.4 - Define learning-funnel contract**
  - Agent: plan then build.
  - Write scope: contexts, notes/instincts flows, tests.
  - Blocked by: T7.1.
  - Acceptance: lessons, instincts, proposals, and notes have distinct lifecycle rules and promotion paths.

- **T7.5 - Add compaction and handoff validator**
  - Agent: build.
  - Write scope: validators/tests.
  - Blocked by: T7.3.
  - Acceptance: handoff files include sufficient evidence and reference large outputs instead of inlining them.

Parallelization: T7.3 and T7.4 can overlap after the contract work is stable.

## Feature F8 - Runtime Core Extraction and Selective Rewrites

Purpose: rewrite runtime subsystems only after the new control/work/kernel/state contracts exist.

### Candidate Rewrite Tracks

- **Track A - Manifest and state repository unification**: replace split loaders and broad state access with a clear repository/projection boundary.
- **Track B - Reconciler engine**: unify installer, doctor, and updater around one inspect/plan/apply/verify engine.
- **Track C - Thin CLI adapters**: move branching, prompting, and domain mutation out of large `cli_commands/*` files.
- **Track D - Asset/runtime split**: stop shipping duplicated executable logic inside templates when packaged runtime code should be authoritative.
- **Track E - Workflow automation layer**: unify release, work-item, and PR-like automation over reusable protocols.

### Tasks

- **T8.1 - Rank rewrite tracks by value, coupling, and blast radius**
  - Agent: explore.
  - Write scope: `.ai-engineering/specs/spec-117-progress/explore_runtime_tracks.md`.
  - Acceptance: each track is scored by line count, churn, coupling, test blast radius, and harness value.

- **T8.2 - Define stable contract for each rewrite track**
  - Agent: plan.
  - Write scope: future-spec updates only.
  - Blocked by: T8.1.
  - Acceptance: every rewrite track has stable public API targets, migration strategy, test plan, and rollback path.

- **T8.3+ - Implement one rewrite track per follow-on spec**
  - Agent: build.
  - Write scope: one runtime family at a time.
  - Blocked by: T8.2 and earlier waves.
  - Acceptance: no behavior regression, tests green, coverage maintained, docs updated, and legacy surface retirement plan exists.

Parallelization: runtime rewrites should be serialized unless write scopes and imports are provably disjoint.

## Feature F9 - Verification, Evals, and Test Architecture

Purpose: separate kernel checks from repo-governance checks and create a real harness eval plane.

### Tasks

- **T9.1 - Classify checks by plane**
  - Agent: explore then plan.
  - Write scope: progress/spec only.
  - Acceptance: checks are classified as kernel, repo-governance, eval, or shell/adapter.

- **T9.2 - Create eval scenario packs**
  - Agent: build with verify.
  - Write scope: tests/fixtures/evals or `.ai-engineering/evals/`, tests.
  - Blocked by: T5.5 and T9.1.
  - Acceptance: replayable scenario packs exist for mirrors, task ledger, kernel failures, context packs, and cross-IDE parity.

- **T9.3 - Add regression scorecards and budgets**
  - Agent: build.
  - Write scope: report modules/tests.
  - Blocked by: T9.2.
  - Acceptance: pass/fail, latency, retry, and cache-effect regressions are visible.

- **T9.4 - Split oversized test files by contract**
  - Agent: build.
  - Write scope: tests only.
  - Blocked by: T9.1.
  - Acceptance: multi-contract test files are decomposed so runtime refactors have clearer ownership.

- **T9.5 - Add perf and stability baselines where missing**
  - Agent: build.
  - Write scope: perf tests/reporting.
  - Blocked by: T9.2.
  - Acceptance: hot-path and scenario baselines exist for the new harness flows.

Parallelization: T9.2 and T9.4 can overlap after T9.1. T9.3 and T9.5 depend on stable eval packs.

## Feature F10 - Engineering Standards and Documentation

Purpose: make the new harness model explicit and keep the repo aligned with the engineering standards the user asked to formalize.

### Tasks

- **T10.1 - Write canonical engineering-principles docs**
  - Agent: build.
  - Write scope: `.ai-engineering/contexts/` or `docs/`.
  - Acceptance: Clean Code, Clean Architecture, SOLID, DRY, KISS, YAGNI, TDD, SDD, and Harness Engineering have canonical framework docs.

- **T10.2 - Bind standards to review and verify rubrics**
  - Agent: build.
  - Write scope: contexts, skills, internal review/verify contracts, tests.
  - Blocked by: T10.1.
  - Acceptance: later agents can apply the standards without relying on vague prose memory.

- **T10.3 - Update solution intent and harness architecture map**
  - Agent: build.
  - Write scope: `docs/solution-intent.md`, harness architecture docs.
  - Blocked by: earlier contract work.
  - Acceptance: docs match the implemented harness model and canonical sources.

- **T10.4 - Add migration and adoption guide**
  - Agent: build.
  - Write scope: docs/templates.
  - Blocked by: implemented runtime features.
  - Acceptance: projects can adopt task ledger, harness check, and new mirror/control-plane rules.

- **T10.5 - Document reference-repo lessons**
  - Agent: build.
  - Write scope: docs/spec references.
  - Acceptance: lessons from `/Users/soydachi/repos/ejemplo-harness-subagentes` are documented without copying project-specific content into runtime contracts.

- **T10.6 - Update README / GETTING_STARTED only after runtime is real**
  - Agent: build.
  - Write scope: root docs.
  - Blocked by: implementation completion.
  - Acceptance: user-facing docs only describe commands and artifacts that exist.

Parallelization: T10.1-T10.3 can partially overlap. T10.4-T10.6 wait for implemented features.

## Feature F11 - Legacy Surface Retirement

Purpose: remove accidental or replaced surfaces once parity is demonstrated.

### Tasks

- **T11.1 - Build legacy-deletion manifest**
  - Agent: build.
  - Write scope: spec-progress report or generated manifest.
  - Acceptance: delete candidates are enumerated with replacement owner, proof requirement, and rollback path.

- **T11.2 - Define parity proofs and rollback criteria**
  - Agent: plan.
  - Write scope: spec/update only.
  - Blocked by: T11.1.
  - Acceptance: deletions cannot happen without explicit parity evidence.

- **T11.3+ - Remove one legacy family per follow-on spec**
  - Agent: build.
  - Write scope: one family at a time.
  - Blocked by: T11.2 and relevant replacement work.
  - Acceptance: candidate families such as duplicate constitutions, dual gates, template runtime Python, stale mirror trees, and stale maintenance/reporting surfaces can be retired without regression.

Parallelization: retirements should be serialized by surface family.

## Suggested Wave Plan

### Wave 1 - Establish the Planes

Features: F1, F2.

Exit gate:

- control surfaces are inventoried;
- artifact-plane taxonomy exists;
- spec-scoped work plane exists;
- task ledger and handoff validation exist.

### Wave 2 - Fix the Interfaces

Features: F3, F6.

Exit gate:

- mirrors are provider-local and generated with provenance;
- public/internal agent surface is clear;
- task packets, write scopes, and topology rules exist.

### Wave 3 - Unify the Engine

Features: F4, F5.

Exit gate:

- one harness kernel is authoritative;
- `ai-eng harness check` exists;
- event vocabulary is normalized;
- state vs runtime residue is separated;
- task traces exist.

### Wave 4 - Make Context and Quality Operational

Features: F7, F9.

Exit gate:

- context packs generate deterministically;
- learning funnel is governed;
- eval scenario packs exist;
- oversized tests are being split by contract.

### Wave 5 - Rewrite the Runtime

Features: F8.

Exit gate:

- at least one rewrite track has landed cleanly behind the new contracts;
- runtime seams are improving for the right reasons, not just line counts.

### Wave 6 - Standardize and Delete

Features: F10, F11.

Exit gate:

- engineering-principles canon is published;
- docs match reality;
- one or more legacy surface families are retired with parity proof.

## Multi-Agent Parallelization Map

Safe parallel groups:

- **Plane discovery group**: one explorer for control plane, one for work/state plane, one for runtime seams.
- **Mirror group**: one build worker for reference-model rewrite, one for provenance enforcement, after generator ownership is explicit.
- **Context/eval group**: one worker on context packs, one on eval fixtures, one on test file splits, once task ledger contracts stabilize.
- **Docs/standards group**: one worker on engineering-principles canon, one on solution-intent/harness docs, after runtime names and artifacts are stable.

Unsafe parallel groups:

- Generated mirror sync must be coordinated by one worker at a time.
- Event-emitting validations should not run in parallel against the live audit chain.
- Manifest schema and state-model edits are serialized around ownership.
- Hook, policy-engine, and kernel changes are serialized with guard review.
- Runtime rewrite tracks touching shared imports should serialize unless proven disjoint.

## Future-Spec Portfolio

The follow-on implementation spec matrix lives in `.ai-engineering/specs/spec-117-harness-engineering-feature-portfolio.md`.

## Verification Commands to Use Later

Exact command set can evolve, but implementation specs normally include:

- `uv run ai-eng sync --check`
- `uv run ai-eng validate -c cross-reference`
- `uv run ai-eng validate -c file-existence`
- `uv run ai-eng validate -c manifest-coherence`
- targeted pytest for changed modules
- targeted tests for mirror sync and generated templates when canonical skills/agents change
- `ruff check`
- `ruff format --check`
- `gitleaks protect --staged` before commit

## First Implementation Recommendation

Start with Wave 1 as two tightly coupled slices:

1. **Control plane normalization minimum**: artifact taxonomy, constitution resolution decision, and provenance rules.
2. **Work plane normalization core**: spec-scoped task ledger, active pointer, handoffs, evidence folders, and current/history summaries.

Why:

- It gives the entire root refactor a real filesystem backbone.
- It fixes the current spec/plan mismatch before touching runtime packages.
- It creates the substrate later agents need for safe parallel work.
- It reduces the risk that runtime rewrites happen before the repo knows where durable evidence belongs.
