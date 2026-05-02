# HX-05 Explore - State Plane and Observability Normalization

This artifact captures the evidence gathered before writing the feature spec for `HX-05`.

## Scope

Feature: `HX-05` State Plane and Observability Normalization.

Question: what must change so ai-engineering separates durable cross-spec truth from runtime residue, normalizes event vocabulary and task traces, and turns scorecards into derived views instead of peer state authorities?

## Evidence Summary

### The Global State Root Mixes Durable Truth, Derived Snapshots, Residue, And Spec-Local Evidence

- The documented global state core includes the decision store, framework events, framework capabilities, install state, and ownership map.
- The live state root also contains last-run findings, hashed gate-cache entries, instinct observations, strategic compacts, and spec-tagged audit artifacts.
- Some of those files are long-lived governance or audit surfaces, while others are ephemeral session or task outputs.

The current directory boundary therefore does not match lifecycle or authority boundaries.

### Several Files Are Quasi-Authoritative Even Though They Behave Like Residue

- `gate-findings.json` is a last-run findings artifact but also behaves as a public operator-facing result surface.
- `framework-capabilities.json` and some other projections are persisted and consulted even though they are derived.
- `strategic-compact.json` is a session-local compact but lives beside durable ledgers.

This creates ambiguity around what must survive, what can be regenerated, and what downstream systems may trust.

### Spec-Local Evidence Is Already Wrongly Global

- Spec-specific audit or classification artifacts already live as peers under `.ai-engineering/state/`.
- The spec-117 task catalog already intends spec-local evidence to live under the work plane, but the filesystem has not been normalized yet.

This is the clearest ownership bug for `HX-05`: task-local evidence should not survive as a cross-spec global state peer.

### Observability Has One Main Chain But Multiple Schema And Writer Variants

- The canonical durable audit plane is the hash-chained framework-events stream plus the decision ledger.
- Event writers exist in runtime code and in hook-side shims.
- Provider identifiers drift between `copilot` and `github_copilot` across different writers and validators.
- Event kinds also drift, with one-off or bridge-only variants appearing outside one normalized vocabulary.

The system therefore has one intended event plane but not yet one normalized event contract.

### Task Traces Are Missing As A First-Class Model

- Framework events already carry correlation, session, trace, and parent identifiers.
- Hook and runtime emitters use some of those fields today.
- What is missing is a first-class task trace model with stable task identity, lifecycle phase, and artifact references.
- Downstream consumers already fall back to session or correlation as a weak proxy because no stronger task key exists.

`HX-05` therefore needs to add task traces as an append-only derived audit view over authoritative mutations, not as a second state machine.

### Scorecards And Reports Already Exist, But They Are Fragmented

- Verify has one score model.
- Maintenance has another health score.
- Agentsview exports copied event and capability data.
- Shell or maintenance scripts write their own report files.

Without a normalized state and trace model, scorecards will continue to drift into peer-authority territory.

### Audit-Chain Safety Is Already Fragile

- Event appenders do read-last-hash then append with no shared lock or atomic replace.
- Findings and residual artifacts use safer tempfile-plus-replace publishing.
- Chain verification behavior is not perfectly aligned across streaming and batch verification modes.
- Event-emitting validations are already known to race if run in parallel.

`HX-05` must therefore preserve serialized families and strengthen the distinction between authoritative mutation and derived reporting.

## High-Signal Findings

1. The global state root currently hides four different lifecycles: durable truth, derived projections, runtime residue, and spec-local evidence.
2. The first normalization rule should be that nothing belongs in global state root unless it is cross-spec and still authoritative after the originating task or session is gone.
3. Framework events and decision store should remain the durable audit chain; task traces and scorecards should derive from them plus work-plane state.
4. Provider IDs, event kinds, and writer paths need one canonical contract before scorecards become trustworthy.
5. `HX-05` must normalize ownership without absorbing kernel execution truth from `HX-04` or learning-funnel lifecycle from `HX-07`.

## Recommended Decision Direction

### Preferred State-Plane Direction

- Split global durable truth, runtime residue, and spec-local evidence into distinct homes.
- Keep only cross-spec authoritative records in the global durable state root.
- Move spec-local evidence under the owning spec work plane.
- Place caches, last-run findings, and disposable diagnostics in a residue subtree with retention or GC rules.

### Preferred Observability Direction

- Keep one canonical framework-events chain and one canonical chain-pointer location.
- Normalize provider IDs and event kinds through one state-layer contract.
- Force hook, CLI, and manual writers through adapters into that contract rather than letting each writer define semantics.

### Preferred Trace And Scorecard Direction

- Add a first-class task trace envelope on framework events with stable task identifiers, lifecycle phase, parent/correlation fields, and artifact references.
- Treat task traces as append-only audit views over authoritative mutations, not as a second state machine.
- Make scorecards and reports reductions over authoritative inputs rather than peer truth files.

## Migration Hazards

- Moving files out of the global state root can break consumers that quietly depended on them as quasi-authoritative.
- Event normalization can break host integrations if provider naming or event kinds change without compatibility shims.
- Race conditions in audit appenders can worsen if more event writers are added before sequencing and adapters are tightened.
- Generated scorecards can become peer authorities if persisted without clear provenance or regeneration rules.
- `framework-capabilities.json` remains ambiguous until `HX-06` fully normalizes capability authority.

## Scope Boundaries For HX-05

In scope:

- durable truth versus residue split
- spec-local evidence relocation out of global state
- normalized event vocabulary and provider identifiers
- task trace schema and emission
- harness scorecards and report surfaces as derived views
- safe sequencing for event-emitting and shared-output flows

Out of scope:

- harness kernel execution authority from `HX-04`
- work-plane schema ownership from `HX-02`
- learning-funnel lifecycle and promotion rules from `HX-07`
- full eval taxonomy from `HX-11`
- mirror-family governance from `HX-03`

## Open Questions

- Should task traces live directly in the framework-events stream or as a generated projection over it plus ledger state?
- What is the compensating behavior when authoritative state mutation succeeds but audit append fails?
- Which scorecard snapshots, if any, need to persist for UX/performance rather than being regenerated on demand?
- When does `framework-capabilities.json` become clearly downstream of the `HX-06` capability contract?
- Does the first cut need an explicit single-writer lock for audit append, or is strict sequencing enough?

## Source Artifacts Consulted

- `.ai-engineering/state/**`
- `.ai-engineering/README.md`
- `src/ai_engineering/state/observability.py`
- `src/ai_engineering/state/audit_chain.py`
- `src/ai_engineering/state/audit.py`
- `src/ai_engineering/state/models.py`
- `src/ai_engineering/state/instincts.py`
- `src/ai_engineering/state/agentsview.py`
- `src/ai_engineering/policy/orchestrator.py`
- `src/ai_engineering/policy/watch_residuals.py`
- `src/ai_engineering/verify/scoring.py`
- `src/ai_engineering/maintenance/report.py`
- `src/ai_engineering/cli_commands/audit_cmd.py`
- `src/ai_engineering/cli_commands/maintenance.py`
- `src/ai_engineering/cli_commands/doctor_hot_path.py`
- `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/hook-common.py`
- `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/copilot-common.sh`
- `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/copilot-common.ps1`
- `.ai-engineering/specs/spec-117-hx-02-work-plane-and-task-ledger.md`
- `.ai-engineering/specs/spec-117-hx-04-harness-kernel-unification.md`