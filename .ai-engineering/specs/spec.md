---
spec: spec-195
slug: third-party-mcp-removal
title: "Third-Party MCP Removal and Credential Safety"
status: draft
effort: large
summary: "Direct operational-owner removal of all third-party MCPs from hosts and generated templates, with verified Pencil/Pen exception and credential safety decisions."
stack: python
---

# spec-195 — Third-Party MCP Removal and Credential Safety

## Summary

Every third-party MCP is directly removed from every operator host and project configuration, then from ai-engineering-generated surfaces. The only survivors are the requested Codex vendor/system capabilities and the verified Pencil.dev/Pen.dev component. Credentials are never copied into Git or audit output: a credential may remain usable only when an approved governed CLI pack needs it and an OS credential manager, an official CLI store with private ACLs, or a governed process-local environment supports it.

Depends on spec-194 (harness) for baseline evidence and clean-host verification.

## Goals

- Produce a values-free inventory across user, project and plugin owners classifying each as: remove, exact retained vendor/system, exact Pencil/Pen candidate, or blocker.
- Rotate/revoke exposed credentials; move required values to an accepted store; correct modes/ACLs; verify no value enters a report.
- Apply direct removal host by host, including generated templates and source instructions.
- Replace no MCP capability in this delivery; report the missing workflow explicitly for later CLI-pack work.
- Start fresh host processes and run structural, permission and attempted-invocation checks; hard-delete stale framework-generated artifacts only where provenance matches.
- No reachable third-party MCP registration, plugin/package owner, permission, hook, skill or operational instruction remains on target hosts or generated templates.
- Codex retains only `node_repl`, Sites design picker and GitHub after exact vendor provenance verification.
- Pencil/Pen survives only with all five identity fields proven; otherwise it is removed and reported as blocked.
- All affected credentials are rotated, explicitly retired, or bound to an approved CLI pack.
- Fresh-process verification shows zero third-party MCP reachability and no fallback path.

## Non-Goals

- Creating CLI skill packs (spec-198/199).
- Changing root context budgets (spec-196).
- Adding a new policy service.
- Silently deleting legitimate Keychain entries.
- Broad dependency remediation.

## Decisions

### D-195-01 — Hard removal, no disabled state

This is a hard removal: no disabled registration, compatibility alias, MCP fallback or documentation that instructs activation remains. Historical references are retained only when plainly archival and non-operational.

**Rationale**: §10.1 KISS — hard deletion instead of a disabled but complex control plane.

### D-195-02 — Preview → confirm → apply → verify

Removal uses a deterministic process: preview (show what will be removed), confirm (operator approves), apply (execute removal), verify (fresh-process check). No permanent control plane.

**Rationale**: §10.6 SDD — every mutation has an approved removal plan.

### D-195-03 — Pencil/Pen requires all five identity fields

Pencil/Pen survives only when vendor/editor, component ID, channel, version/digest and installation owner all match recorded evidence. A future mismatch removes the exception.

**Rationale**: Name-based allowlists can preserve unintended servers.

### D-195-04 — Credential quarantine, not silent retention

A credential with no approved CLI pack reference is quarantined in the plan until the operator confirms revoke, delete or a future governed use. Never silently retained or deleted.

**Rationale**: Security: silent retention is a liability; silent deletion may break needed workflows.

## Risks

- **Unparseable config hides an MCP owner**: medium likelihood, high impact. Mitigation: block that host, record structure-only evidence, require manual classification.
- **Secret rotation disrupts a still-needed CLI**: medium likelihood, high impact. Mitigation: verify approved CLI reference before revocation; use staged rotation.
- **Pencil/Pen name match is a lookalike**: medium likelihood, high impact. Mitigation: require all identity fields, not a name allowlist.
- **Generated update overwrites user content**: low likelihood, high impact. Mitigation: update only digest-matched framework assets.

## References

- brief: `.ai-engineering/specs/drafts/third-party-mcp-removal-brief.md`
- audit: `.ai-engineering/runtime/audits/cli-first-context-audit-2026-07-23.md`
- research: `.ai-engineering/runtime/research/mcp-retirement-and-credential-audit-2026-07-23.md`
- gate policy: `.ai-engineering/reference/gate-policy.md`

## Acceptance

- [ ] Redacted preflight and confirmed change plan exist for each target host.
- [ ] Rotation/ACL and retention-decision receipts contain no secret value.
- [ ] All third-party MCP operational owners are removed.
- [ ] Codex exceptions and Pencil/Pen are evidence-verified.
- [ ] Fresh host verification proves no third-party MCP reachability.
- [ ] No framework-generated or user-owned file is removed outside approved provenance rules.
