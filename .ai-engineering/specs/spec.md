---
spec: spec-198
slug: cli-integration-pack-contract
title: "Governed CLI and Retained-MCP Integration Pack Contract"
status: draft
effort: large
summary: "Canonical pack schema, validator, redactor, deterministic helpers for every agent-authorized CLI and retained MCP."
stack: python
---

# spec-198 — Governed CLI and Retained-MCP Integration Pack Contract

## Summary

ai-engineering publicly owns one concise, canonical pack for every agent-authorized CLI and each retained MCP. A pack provides exact provenance, bounded expertise and deterministic scripts while the active IDE supplies the human command that invokes it. The public repository never contains a credential, personal alias or installed receipt; the operating system credential manager or governed process environment does.

Depends on spec-194 (harness), spec-195 (MCP removal result), and spec-197 (native surfaces).

## Goals

- Every approved pack declares platform-specific version, source, license, asset/launcher digest, scopes and exact credential mode.
- Read-only commands are JSON-first, time/output bounded and redacted.
- Mutations require deterministic preview or rendered plan, explicit confirmation for production/payment/destruction/publication, readback and rollback guidance.
- Missing pin, unexpected binary, unsafe credential store, unbounded output, secret leak or MCP fallback fails closed.
- Public artifacts contain no operator data; private selection/pins/receipts are explicitly excluded from source control.
- No CLI becomes agent-authorized without one passing pack, and no pack is automatically selected by model intent.

## Non-Goals

- Enabling a particular CLI (spec-199 pilots).
- Retaining/removing MCPs (spec-195).
- Resolving Pencil/Pen identity.
- Adding wrappers for uninstalled tools.
- Changing user command surfaces (spec-197).
- Adding a runtime `ai-eng` router.

## Decisions

### D-198-01 — One canonical pack per authorized integration

Each CLI/MCP has exactly one pack in a public canonical library. The pack is loaded only after the operator explicitly invokes its exact `ai-*` workflow.

**Rationale**: Single contract makes capability use predictable and reviewable.

### D-198-02 — Supply-chain-safe adoption

No direct vendoring from skills.sh. A candidate is fetched at immutable revision, licensed, reviewed and rewritten into the canonical format.

**Rationale**: skills.sh entries can drift from upstream; mutable installs are unsafe.

### D-198-03 — Provenance lock model

Each pack declares: vendor source, version, license, asset digest, launcher digest, supported platforms. Missing any field blocks authorization.

**Rationale**: §10.6 SDD — no remediation begins without evidence.

### D-198-04 — Credential store must be accepted

Credentials may only reside in: OS credential manager (Keychain), official CLI private store with ACLs, or governed process-local environment. Unsafe stores block activation.

**Rationale**: Credentials in Git or audit output are a security liability.

## Risks

- **Contract becomes an oversized platform**: medium likelihood, high impact. Mitigation: start with validation primitives demanded by pilots; reject registry/daemon scope.
- **Checksum cannot be stable across OS packages**: medium likelihood, medium impact. Mitigation: pin source and platform asset separately; version-aware adapter.
- **Redactor misses a new provider secret shape**: medium likelihood, high impact. Mitigation: default deny on secret-bearing command classes and fixture corpus.
- **Pack prose recreates context bloat**: medium likelihood, medium impact. Mitigation: entry budget, one-level lazy refs and native explicit invocation.

## References

- brief: `.ai-engineering/specs/drafts/cli-integration-pack-contract-brief.md`
- audit: `.ai-engineering/runtime/audits/cli-first-context-audit-2026-07-23.md`
- persistence: `docs/persistence-doctrine.md`

## Acceptance

- [ ] Schema, validator and redactor have offline fixture coverage.
- [ ] Provenance and credential preflight failures fail closed.
- [ ] Read-only, mutation, confirmation and rollback contracts are enforced.
- [ ] MCP fallback attempts are rejected deterministically.
- [ ] Public/private boundary and ignored receipt paths are documented and tested.
- [ ] No command surface exposes a pack before exact human invocation.
