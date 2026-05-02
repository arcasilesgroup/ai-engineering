# Plan: spec-117-hx-04 Harness Kernel Unification

## Pipeline: full
## Phases: 5
## Tasks: 15 (build: 11, verify: 2, guard: 2)

## Architecture

modular-monolith

`HX-04` changes one repository-wide local execution core spanning policy engine, gate CLI, hook adapters, findings envelopes, cache, residual output, and local failure semantics. It remains a modular-monolith change because all of this still belongs to one framework runtime and one governed repository, but it is a high-collision slice and should serialize across kernel, hook, and policy surfaces.

### Phase 1: Authority Inventory And Cut Line
**Gate**: One explicit authority map and cut line exist for the kernel, adapters, validators, verify, CI, and adjacent state-plane surfaces.
- [x] T-1.1: Consolidate the `HX-04` exploration evidence into one governed authority matrix covering local gate engines, adapter layers, result models, and serialized artifact families (agent: build).
- [x] T-1.2: Run a governance review on deterministic versus advisory kernel behavior, serialized output families, and the ownership boundary with `HX-05` and `HX-11` before implementation begins (agent: guard, blocked by T-1.1) -- PASS-WITH-NOTES
- [x] T-1.3: Define the compatibility boundary for legacy hook gate behavior, findings publication, CI-facing semantics, and residual outputs so migration can be parity-first (agent: build, blocked by T-1.2).

### Phase 2: Kernel Contract And Result Envelope
**Gate**: One authoritative kernel contract exists with stable findings envelope, registration model, mode/profile resolution, and publish semantics.
- [x] T-2.1: Write failing tests or invariant coverage for kernel registration, mode resolution, normalized findings envelope, residual output compatibility, and explicit publish responsibility (agent: build, blocked by T-1.3).
- [x] T-2.2: Implement the canonical kernel contract over the owned orchestrator/gate surfaces without yet cutting over all adapters (agent: build, blocked by T-2.1).
- [x] T-2.3: Add retry ceilings, loop-cap rules, and blocked disposition output to the kernel contract without moving durable state ownership into this feature (agent: build, blocked by T-2.2).
- [x] T-2.4: Run a governance review on the result envelope, risk-accept partitioning, and failure-output contract before adapter cutover begins (agent: guard, blocked by T-2.3) -- PASS-WITH-NOTES

### Phase 3: Adapter Convergence
**Gate**: Local callers run through the kernel rather than through separate gate authorities.
- [x] T-3.1: Write failing tests for gate CLI parity, hook adapter parity, workflow-helper parity, and legacy-engine deprecation behavior (agent: build, blocked by T-2.4).
- [x] T-3.2: Move gate CLI variants and workflow-helper entry points onto the kernel-backed execution path while preserving compatibility semantics (agent: build, blocked by T-3.1).
- [x] T-3.3: Move git-hook installation and hook entry points onto thin kernel adapters and retire duplicate local decision-making in the legacy gate engine (agent: build, blocked by T-3.2).
- [x] T-3.4: Keep validate and verify as downstream reporters over kernel or repo data rather than letting them become alternate local gate authorities (agent: build, blocked by T-3.3).

### Phase 4: Sequencing, Cache, And Audit Safety
**Gate**: Shared output families run with explicit sequencing and cache behavior that do not weaken audit or findings integrity.
- [x] T-4.1: Add explicit sequencing rules or enforcement for shared findings publication, mirror-sync-before-validation, and event-emitting validation order where the kernel or adapters own the call path (agent: build, blocked by T-3.4).
- [x] T-4.2: Tighten cache, residual-output, and publish-path behavior so kernel results cannot be silently constructed without the expected durable artifacts (agent: build, blocked by T-4.1).
- [x] T-4.3: Run targeted verification for kernel parity, adapter parity, sequencing behavior, and compatibility semantics before strict cutover (agent: verify, blocked by T-4.2).

### Phase 5: Cutover Proof And Deferred Ownership
**Gate**: One kernel is proven authoritative for local execution, and deferred state/eval ownership remains explicit.
- [x] T-5.1: Flip strict local callers and tests to the kernel-backed authority once compatibility coverage and parity proof are green (agent: build, blocked by T-4.3).
- [x] T-5.2: Document deferred work for `HX-05` and `HX-11`, especially event vocabulary, task traces, scorecards, check taxonomy, eval packs, and any remaining CI-only aggregation concerns (agent: build, blocked by T-5.1).
- [x] T-5.3: Run the focused end-to-end proof for this feature with the relevant unit/integration slices plus `uv run ai-eng validate -c cross-reference` and `uv run ai-eng validate -c file-existence` (agent: verify, blocked by T-5.2).

## Sequencing Notes

- Kernel, hook, and policy-engine changes serialize.
- Sync completes before mirror validation where kernel or adapters own the call order.
- Event-emitting validations remain sequential where they can touch the audit chain.
- Validate and verify stay outside kernel ownership even if they consume kernel outputs.
- CI job orchestration remains downstream of the first HX-04 cut.

## Exit Conditions

- One authoritative kernel exists for local check execution and local blocking disposition.
- Local adapters no longer act as separate gate authorities.
- Findings and residual output use one stable envelope family with explicit publish semantics.
- Retry ceilings, loop caps, and blocked disposition output are part of the kernel contract.
- Shared output families have explicit safe sequencing rules.
- Deferred state-plane and eval-plane ownership is explicit rather than accidental.