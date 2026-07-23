---
spec: spec-197
slug: native-command-skill-agent-surfaces
title: "Native Explicit Commands, Skills, Agents, and Hook Surface Contract"
status: draft
effort: large
summary: "Exact human invocation via host-native IDs, one discovery root per host, native agent/hook adapters, fixture-first verification."
stack: python
---

# spec-197 — Native Explicit Commands, Skills, Agents, and Hook Surface Contract

## Summary

Every ai-engineering workflow is invoked by the operator through its host-native exact ID: `/ai-*` where slash commands exist, `$ai-*` in Codex, and only a documented equivalent proven by fixture elsewhere. Commands are thin manual adapters, skills are on-demand workflow knowledge, agents are compact least-privilege specialists, and hooks are deterministic host wiring. No model semantically selects a workflow and no host discovers duplicate skill trees.

Depends on spec-194 (harness) and consumes spec-195 (MCP removal result) before changing affected hosts.

## Goals

- Every enabled host has official-path evidence and a passing clean-host fixture, or is `UNVERIFIED` and unchanged.
- All canonical user workflows remain directly addressable by exact `ai-*` ID in each proven host's native syntax.
- A semantically similar request cannot implicitly load a governed workflow where host support exists.
- No host discovers two generated roots containing the same ID/signature.
- Commands are thin, skills load only after explicit use, agents cannot escalate permissions or select unrelated capabilities, and successful hooks add no model context.
- OpenCode's command index is measured not to inject a 54-item prompt catalog.

## Non-Goals

- Third-party MCP removal (spec-195).
- Root-context reduction (spec-196).
- CLI pack behavior (spec-198/199).
- Consumer-specific custom agents.
- An `ai-eng` runtime gateway.

## Decisions

### D-197-01 — One root per host, adapter-only directories

Each host gets exactly one discoverable root per ID. Host adapters contain only minimal wiring and must not duplicate skill logic or long operational prose. No symlink, dual root or `ai-eng` invocation gateway.

**Rationale**: Duplicate discovery costs 54+ skills in prompt context.

### D-197-02 — Explicit invocation only

No ai-engineering workflow may be implicitly selected by an LLM. The operator invokes an exact native ID. Where the host supports it, use its native user-only policy.

**Rationale**: Exact native invocation gives the operator control.

### D-197-03 — Agents are host-native, not universal

`.agents/agents` is not a universal standard. Generate small host-native agent adapters only where the host officially supports them. Codex retains `.codex/` for native wiring only.

**Rationale**: Treating `.agents` as universal would silently break Claude Code and Copilot custom agents.

### D-197-04 — OpenCode commands are thin entry points

OpenCode retains `commands/` as its human slash-command surface. Generate one thin, exact `/ai-*` command per canonical workflow. Prove through measurement that the command index is not injected as a catalog.

**Rationale**: OpenCode commands are necessary for user invocation but must not become a 54-item prompt surface.

## Risks

- **Host discovery precedence differs from documentation**: medium likelihood, high impact. Mitigation: clean-host probe and rollback before apply.
- **Explicit-only flag is ignored**: high on some hosts, high impact. Mitigation: host-specific adapter or `UNVERIFIED`, never universal metadata.
- **Command list itself consumes prompt context**: medium likelihood, high impact. Mitigation: measure native prompt input; redesign only after evidence.
- **Agent format changes across host versions**: medium likelihood, medium impact. Mitigation: version-pinned fixture and adapter schema.

## References

- brief: `.ai-engineering/specs/drafts/native-command-skill-agent-surfaces-brief.md`
- generator: `scripts/sync_mirrors/core.py`
- audit: `.ai-engineering/runtime/audits/cli-first-context-audit-2026-07-23.md`

## Acceptance

- [ ] Capability records and clean-host fixtures exist for all enabled hosts.
- [ ] Each proven host has exactly one discoverable root per ID.
- [ ] Exact user invocation loads the matching workflow; implicit invocation fails where supported.
- [ ] Agent and hook adapters are host-native and least-privilege.
- [ ] OpenCode dependency removal is gated by import scan and clean-install test.
- [ ] Generator parity, rollback and update-diff tests pass.
