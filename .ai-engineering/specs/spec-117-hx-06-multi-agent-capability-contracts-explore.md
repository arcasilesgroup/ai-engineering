# HX-06 Explore - Multi-Agent Capability Contracts

This artifact captures the evidence gathered before writing the feature spec for `HX-06`.

## Scope

Feature: `HX-06` Multi-Agent Capability Contracts.

Question: what must change so long-running multi-agent execution is governed by explicit capability cards, tool scopes, write scopes, topology classes, and deterministic integration gates instead of prose-only role descriptions and optimistic parallelism?

## Evidence Summary

### There Is No Single Capability Authority Today

- `.ai-engineering/manifest.yml` is the strongest machine-readable source for roster membership, counts, skill kind/tags, providers, and some root ownership metadata.
- Canonical behavior semantics still live mainly in `.claude/skills/**` and `.claude/agents/**`.
- Copilot-specific delegation, tool allowlists, handoffs, hooks, and topology are effectively authored in `scripts/sync_command_mirrors.py`.
- `framework-capabilities.json` is a shallow projection and is already known to drift.

The current capability model is therefore split across registry metadata, prompt prose, provider-specific generation logic, and stale projections.

### Capability Signals Exist, But They Are Fragmented And Too Shallow

- Skills already have frontmatter such as effort, tags, `requires`, and provider-related compatibility fields.
- Agents already describe mutability, delegation, escalation, and allowed behavior in prose.
- Provider signals and topology hints exist in manifest data, installer logic, sync metadata, and docs.
- Validation currently checks frontmatter shape, counts, and selected mirror behavior more than it checks runtime-safe capability semantics.

The repo has useful inputs, but not one executable capability contract that downstream runtime and validators can trust.

### Topology Is Real, But Mostly Enforced By Convention

- Public first-class topology is a 10-agent registry.
- Actual execution graphs are larger because `review` and `verify` dispatch internal specialist agents, and orchestrators such as `autopilot` and `run` use staged multi-agent flows.
- Leaf/read-only, advisory, spec-writing, code-writing, state-writing, and git-writing roles are not declared once in machine-readable form.

The result is that the real system topology is broader than the public registry and only partially enforced.

### Write Permissions And Tool Permissions Are Not Modeled Precisely Enough

- `build` is documented as the only code writer, but `plan` also has real write capability for specs and plans.
- `autopilot` and `run` do not edit source code directly, but they still mutate state, manifests, branches, commits, and delivery artifacts.
- `guard` is described as having some influence on decision state or telemetry, but in practice hooks and runtime emit most telemetry writes.
- Tool access differs across canonical prompt files and provider-generated metadata.

The current system therefore confuses code-write authority, spec-write authority, state-write authority, and system-side telemetry or hook writes.

### Unsafe Parallelism Is Known, But Not Deterministically Blocked

- `autopilot` and `run` both describe wave and DAG logic.
- The collision model depends on declared file sets, imports/exports, generated files, lockfiles, workflows, migrations, and serialize-on-uncertainty language.
- Shared global surfaces still exist, including shared work-plane files, run manifests, hooks, validators, and generated outputs.
- Hooks and telemetry observe dispatches, but they do not enforce capability parity, delegation parity, or write-scope overlap.

The repo already knows where collisions come from, but it lacks one deterministic gate that blocks invalid agent/tool/write combinations.

### `HX-06` Must Be A Thin Enforcement Layer Over `HX-02` And `HX-03`

- `HX-02` owns the work plane, task ledger, handoffs, evidence, and active pointer.
- `HX-03` owns the mirror-family inventory and public/internal mirrored boundary.
- `HX-06` should extend those contracts with capability cards, task-packet validation, tool scopes, write-scope taxonomy, topology role, and integration gates.

If `HX-06` duplicates task-ledger design or mirror-family governance, it will recreate the same split-authority problem it is supposed to solve.

## High-Signal Findings

1. The core defect is not missing prose. It is missing machine-readable capability authority.
2. `HX-06` must model mutation plane explicitly: read, advise, spec-write, code-write, state-write, git-write, board-write, telemetry-emit.
3. Tool scope, provider compatibility, and topology class need one cross-provider schema.
4. Deterministic gates should block invalid combinations; optimization heuristics should remain advisory until modeled explicitly.
5. `HX-06` should consume `HX-02` task packets and `HX-03` public/internal boundaries instead of redefining them.

## Recommended Decision Direction

### Preferred Capability-Layer Direction

- Add one capability card per first-class agent or skill.
- Capability cards should declare write eligibility, allowed artifact classes, default read scope, default write scope, tool allowlist, provider compatibility, handoff inputs/outputs, escalation path, and public/internal status.
- Make `framework-capabilities.json` a projection of this contract rather than a competing source.

### Preferred Task-Packet Direction

- Keep the task ledger and work-plane state in `HX-02`.
- Add task packets that bind one ledger task to one capability card and declare owner, dependencies, read scope, write scope, tool subset, provider binding, retry budget, required checks, produced artifacts, and handoff target.
- Use the capability contract to answer whether a capability may accept a packet, not to redefine the packet schema itself.

### Preferred Enforcement Direction

- Block invalid delegate/tool/write combinations deterministically.
- Block overlapping write scopes and missing dependency or handoff edges where the work plane already has enough information.
- Keep warnings for broad-but-legal scopes, semantic coupling risk, degraded hosts, and token inefficiency until those become modelable contracts.

## Migration Hazards

- Generalizing capability metadata without preserving Copilot-specific enrichments can break current subagent behavior.
- Reusing current prompt prose as if it were already authoritative will just rename drift instead of removing it.
- Pulling mirror-family governance or work-plane schema into `HX-06` would duplicate `HX-03` or `HX-02`.
- Existing tests mostly validate counts, frontmatter shape, or selected mirror behavior; richer capability enforcement will need compatibility shims.
- Worktree isolation, token budgets, and deep semantic overlap are important, but they may not all be ready as hard gates in this slice.

## Scope Boundaries For HX-06

In scope:

- capability-card contract for first-class agents and skills
- write-scope taxonomy
- tool-scope policy
- provider compatibility model
- topology role classification
- integration gates for invalid delegate/tool/write combinations
- advisory checks for broader risk patterns that are not yet deterministic

Out of scope:

- work-plane schema ownership from `HX-02`
- mirror-family inventory and public/internal mirror governance from `HX-03`
- kernel-wide retry/loop/failure engine from `HX-04`
- full context compaction and token-budget contract from `HX-07`
- state-plane normalization from `HX-05`

## Open Questions

- Should worktree isolation be mandatory for all concurrent write tasks or only for high-collision runtime families?
- How fine-grained should the write-scope taxonomy be before it becomes harder to maintain than the collisions it prevents?
- Which provider features are minimum required for compatible execution versus only degraded execution?
- Should token budgets remain advisory until `HX-07`, or should some minimum budget rules become part of `HX-06`?
- Should artifact ownership live only in capability cards and task packets, or also in a shared registry reused by mirror and state families?

## Source Artifacts Consulted

- `.ai-engineering/manifest.yml`
- `.claude/skills/**`
- `.claude/agents/**`
- `scripts/sync_command_mirrors.py`
- `docs/copilot-subagents.md`
- `src/ai_engineering/skills/service.py`
- `src/ai_engineering/cli_commands/skills.py`
- `src/ai_engineering/validator/categories/skill_frontmatter.py`
- `src/ai_engineering/state/defaults.py`
- `src/ai_engineering/updater/service.py`
- `src/ai_engineering/state/observability.py`
- `.ai-engineering/state/framework-capabilities.json`
- `.github/skills/_shared/execution-kernel.md`
- `.github/agents/autopilot.agent.md`
- `.github/agents/run-orchestrator.agent.md`
- `.github/agents/review.agent.md`
- `.github/agents/verify.agent.md`
- `.github/hooks/hooks.json`
- `.ai-engineering/specs/spec-117-hx-02-work-plane-and-task-ledger.md`
- `.ai-engineering/specs/spec-117-hx-03-mirror-local-reference-model.md`
- `.ai-engineering/specs/spec-117-harness-engineering-task-catalog.md`