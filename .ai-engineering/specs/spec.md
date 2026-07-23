---
spec: spec-199
slug: cli-integration-portfolio-and-pilots
title: "CLI Integration Portfolio Research, Council, and Pilot Selection"
status: draft
effort: large
summary: "Per-CLI research, skills.sh assessment, LLM council, and selection of pilot integrations."
stack: python
---

# spec-199 — CLI Integration Portfolio Research, Council, and Pilot Selection

## Summary

The operator receives a trustworthy, low-context portfolio of CLI/MCP integration candidates rather than a speculative one-skill-per-executable catalog. Each candidate is researched from the installed binary and primary vendor documentation, compared with skills.sh only as discovery input, reviewed by an LLM council, and admitted to an individual implementation brief only when it can satisfy the governed pack contract and exact human invocation model.

Depends on spec-198 (pack contract) for admission criteria.

## Goals

- Every candidate has a values-free inventory record and official source/capability evidence.
- Every skills.sh candidate has immutable revision, license, checksum, source review and explicit adopt/adapt/reject decision.
- Council packet and dissent are retained with citations; no model vote is treated as evidence without source.
- Each selected pilot has an individual implementation brief with a defined dependency on the pack contract and MCP-removal outcome.
- Uninstalled, unpinned, unsafe-credential, MCP-only or unverifiable candidates are blocked rather than wrapped.
- No more than the approved pilot batch is selected: initially `gh`, local `engram`, conditional `railway`, research/docs, and identity-gated Pencil/Pen.

## Non-Goals

- Installing absent CLIs/wrappers.
- Copying a marketplace skill.
- Enabling a CLI.
- Retaining an MCP.
- Writing a pack (spec-198).
- Using a secret.
- Changing host surfaces (spec-197).

## Decisions

### D-199-01 — Discover broadly, approve narrowly

The portfolio pipeline has five deterministic stages: census, primary-source research, skills.sh comparison, council review, decision record. No candidate is installed or auto-discovered by this delivery.

**Rationale**: §10.2 YAGNI — reject `researchctl`/`docsctl` or any wrapper until a real installed capability and gap exist.

### D-199-02 — skills.sh is discovery only, never installation

skills.sh provides comparable patterns and discovery input. A candidate is fetched at immutable revision, licensed, reviewed and rewritten into canonical format. Never install directly from skills.sh.

**Rationale**: Catalog entries can drift from upstream; mutable installs are unsafe.

### D-199-03 — Council is advisory, not authoritative

The LLM council provides independent views and dissent. Primary source and immutable review outrank council prose. No model vote is treated as evidence without source citation.

**Rationale**: Council echoes can be stale; vendor docs are ground truth.

### D-199-04 — Batch limit prevents catalog bloat

No more than 5 pilots in the initial batch. One brief per coherent risk boundary. Additional pilots require measured gaps after initial evaluation.

**Rationale**: Too many pilots recreate the catalog bloat we're eliminating.

## Risks

- **Council echoes a stale marketplace recommendation**: medium likelihood, high impact. Mitigation: primary source and immutable review outrank council prose.
- **Too many pilots recreate catalog bloat**: high likelihood, medium impact. Mitigation: batch limit and one brief per coherent risk boundary.
- **Vendor docs omit destructive behavior**: medium likelihood, high impact. Mitigation: versioned local `--help`, sandbox/read-only probe and fail-closed classification.
- **Personal inventory leaks**: low likelihood, critical impact. Mitigation: values-free fields only; credentials and private aliases excluded.

## References

- brief: `.ai-engineering/specs/drafts/cli-integration-portfolio-and-pilots-brief.md`
- research: `.ai-engineering/runtime/research/personal-cli-skills-architecture-2026-07-23.md`
- research: `.ai-engineering/runtime/research/skills-sh-cli-candidates-2026-07-23.md`
- council: `.ai-engineering/runtime/research/llm-council-global-context-2026-07-23.md`

## Acceptance

- [ ] Redacted CLI/MCP candidate inventory is complete and bounded.
- [ ] Primary-source and skills.sh research records are cited and immutable where applicable.
- [ ] Council dossier includes independent views, dissent and a chaired verdict.
- [ ] Candidate decisions are adopt, adapt, reject or blocked, never implicit.
- [ ] Each selected pilot has a separate draft with pack-contract dependencies.
- [ ] No candidate is installed or auto-discovered by this research delivery.
