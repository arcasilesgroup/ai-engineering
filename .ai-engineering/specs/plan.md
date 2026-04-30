# Plan: spec-116 Framework Knowledge Consolidation, Canonical Placement, and Governance Cleanup

## Pipeline: full
## Phases: 5
## Tasks: 17 (build: 13, verify: 2, guard: 2)

## Architecture

modular-monolith

ai-engineering is a single deployable framework with bounded internal modules for manifest/config, sync and mirror generation, validator categories, governance state, and platform-specific skills and agents. Spec-116 changes the contracts between those modules without introducing separate deployables or runtime boundaries, which fits modular-monolith best: one operational unit, strong internal seams, and a need to preserve explicit ownership and integration points so future extractions stay possible.

### Phase 1: Canonical Placement Contract
**Gate**: One explicit placement matrix exists in a canonical framework surface, and downstream work no longer has to guess whether a rule belongs in a skill, agent, context, manifest, entry-point, or governance artifact.
- [x] T-1.1: Capture the canonical-placement matrix for framework knowledge classes in one governed source, using current spec-116 decisions and existing first-wave findings as the baseline (agent: build) -- DONE
- [x] T-1.2: Align the canonical ownership narrative across the root entry-point and framework-governance surfaces so the matrix has one unambiguous runtime contract (agent: build, blocked by T-1.1) -- DONE
- [x] T-1.3: Run a governance boundary review on the placement matrix before schema or cleanup work begins (agent: guard, blocked by T-1.2) -- DONE

### Phase 2: Manifest and Validator Metadata
**Gate**: `manifest.yml`, templates, sync logic, and validators share the same structured metadata contract for governed root surfaces and any new machine-readable placement data.
- [x] T-2.1: Write failing tests for the new manifest metadata and governed root-surface ownership contract, including template parity where applicable (agent: build) -- DONE
- [x] T-2.2: Implement the manifest model and template updates needed to satisfy the new metadata contract without adding freeform operational prose to the manifest (agent: build, blocked by T-2.1) -- DONE
- [x] T-2.3: Write failing tests for sync and validator consumption of the new metadata, including provider-aware root instruction surfaces (agent: build, blocked by T-2.2) -- DONE
- [x] T-2.4: Implement sync and validator support for the new metadata so mirror and coherence checks consume the same source of truth (agent: build, blocked by T-2.3) -- DONE
- [x] T-2.5: Verify the manifest/sync slice with targeted unit coverage plus `uv run ai-eng sync --check` and the relevant integrity categories (agent: verify, blocked by T-2.4) -- DONE

### Phase 3: Promotion from Learning Artifacts
**Gate**: Repeatable framework behavior has been promoted out of soft-memory artifacts into canonical runtime surfaces, while heuristic or discovery-only content remains explicitly in the learning funnel.
- [x] T-3.1: Audit `.ai-engineering/LESSONS.md`, `.ai-engineering/instincts/instincts.yml`, and `.ai-engineering/instincts/proposals.md` and mark each candidate as promote, retain, or drop with file-backed rationale (agent: build) -- DONE
- [x] T-3.2: Promote the approved repeatable rules into the correct canonical skills, agents, contexts, and entry-point surfaces using the placement matrix from Phase 1 (agent: build, blocked by T-3.1) -- DONE
- [x] T-3.3: Verify that promoted rules remain mirror-safe and cross-reference-safe across the platform surfaces they touch (agent: verify, blocked by T-3.2) -- DONE

### Phase 4: Decision-Store Normalization
**Gate**: `decision-store.json` contains only formal decisions and live governance risk, with explicit lifecycle state for superseded, completed, or archived material.
- [x] T-4.1: Audit the active decision store and classify entries as formal decision, live risk, superseded history, completed cleanup, or archive candidate using existing spec lineage and current code reality (agent: build) -- DONE
- [x] T-4.2: Write failing tests or invariant checks for the lifecycle rules that the normalized decision store must satisfy after cleanup (agent: build, blocked by T-4.1) -- DONE
- [x] T-4.3: Apply the decision-store lifecycle cleanup and any supporting schema or validator changes required to make those invariants pass (agent: build, blocked by T-4.2) -- DONE
- [x] T-4.4: Run a governance review on risk lifecycle, archival clarity, and audit-grade record boundaries before cleanup of redundant artifacts proceeds (agent: guard, blocked by T-4.3) -- DONE

### Phase 5: Cleanup and Determinism Proof
**Gate**: Stale or redundant knowledge has been removed only after promotion, and deterministic checks prove the framework is coherent across mirrors, references, manifests, validators, and templates.
- [x] T-5.1: Write failing validator or integration coverage for placement-matrix compliance, cleanup safety, and any newly governed root-surface invariants (agent: build, blocked by T-4.4) -- DONE
- [x] T-5.2: Implement the validator and integration coverage needed to protect the cleanup path and codify the new canonical-placement contract (agent: build, blocked by T-5.1) -- DONE
- [x] T-5.3: Remove or slim stale learning and governance content only where the promoted signal is now preserved in the correct canonical surface (agent: build, blocked by T-5.2) -- DONE
- [x] T-5.4: Run the focused end-to-end proof for this spec with targeted tests plus `uv run ai-eng sync --check`, `uv run ai-eng validate -c cross-reference`, and `uv run ai-eng validate -c file-existence` (agent: build, blocked by T-5.3) -- DONE
