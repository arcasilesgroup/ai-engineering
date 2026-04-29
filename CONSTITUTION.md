# CONSTITUTION

> Non-negotiable rules consumed by every skill and agent at Step 0.

This file is the framework's "first law". When skills disagree with
each other, this document wins. When the LLM proposes a path that
violates it, the deterministic plane refuses.

Generated and maintained by the `/ai-constitution` skill. Updates are
ADR-required.

---

## Article I — Spec-Driven Development (HARD GATE)

1. **Every implementation traces back to an approved spec** under
   `.ai-engineering/specs/spec-NNN-<slug>.md`.
2. `/ai-implement` cannot run without `plan.md` marked ready and a user
   approval signal.
3. Trivial pipeline (typo / comment-only / single-line) is permitted
   to skip discovery + architecture phases; the spec still exists,
   only condensed.

## Article II — Test-Driven Development (HARD)

1. Every domain change starts with a **failing test**.
2. The minimum code to make the test pass is the only code added.
3. Refactor with all tests still green is mandatory.
4. **Coverage gate**: domain ≥ 80%, application ≥ 70%, adapters require
   contract tests.

## Article III — Dual-Plane Security

1. Every action proposed by the **Probabilistic Plane** (LLM) passes
   through the **Deterministic Plane** before execution.
2. Input Guard, Identity Broker, Policy Engine (OPA), and Immutable
   Audit Log are non-optional.
3. The `builder` agent is the **only** agent with write permissions.

## Article IV — Subscription Piggyback

1. The framework **never** asks the developer for an API key in the
   default path.
2. Layer 1 (deterministic) requires no LLM.
3. Layer 2 (workflow) delegates inference to the developer's IDE host.
4. Layer 3 (BYOK) is opt-in for CI flows only.

## Article V — Single Source of Truth

1. Skills live ONCE in `skills/catalog/<name>/SKILL.md`.
2. IDE mirrors are **generated**, never edited by hand. Mirror files
   carry the `DO NOT EDIT` header and `linguist-generated=true`.
3. `ai-eng sync-mirrors` is the only authorized writer.

## Article VI — Supply Chain Integrity

1. Plugins **must** ship with Sigstore keyless OIDC signature, SLSA
   v1.0 provenance, CycloneDX SBOM, and OpenSSF Scorecard ≥ 7
   (VERIFIED + COMMUNITY tiers).
2. CI enforces `--ignore-scripts` for npm/bun installs.
3. GitHub Actions are pinned to **immutable commit SHAs**, not
   mutable tags.

## Article VII — No Suppression

1. No `# noqa`, `# nosec`, `// @ts-ignore`, `// nolint`,
   `# pragma: no cover`, `// NOSONAR` to bypass quality gates.
2. If a finding is a false positive, refactor the code to satisfy the
   analyzer or open a risk acceptance with TTL by severity.
3. Risk acceptance is **logged-acceptance**, not weakening. It must
   include: justification, finding-id, owner, spec-ref, severity,
   TTL.

## Article VIII — Conventional Commits

1. Subject in imperative mood: `<type>(<scope>): <subject>`.
2. Body explains **why**, not what (the diff already shows what).
3. No `--no-verify` ever.

## Article IX — Cognitive Debt

1. Every action emits a telemetry event (NDJSON local + OTel optional).
2. The framework treats the cost of opaque, non-deterministic systems
   as a tracked metric (CLEAR framework). Cost regressions are
   first-class.

## Article X — Right to evolve

1. Any article can be amended through an ADR + community review.
2. Amendments take effect at the next minor version.
3. Articles I–VI are subject to a **stricter** amendment process: an
   ADR + 14-day public comment period.

---

<!--
BASELINE PROVENANCE

This document is a BASELINE harvested from `ai-engineering-v3` on 2026-04-29
as part of spec-110 task T-1.3 (governance v3 harvest, GREEN phase for
T-1.1 + T-1.2).

Source: /Users/soydachi/repos/ai-engineering-v3/CONSTITUTION.md (verbatim
copy of the 10-article body; footer added).

Content adaptation per D-110-01 (drop marketplace references, drop
Identity Broker references, drop TrueFoundry references, align with the
current ai-engineering deterministic-plane reality) is scheduled for the
NEXT task (T-1.4). Until T-1.4 lands, this file represents the v3
governance contract verbatim and MAY contain references to subsystems
that the current repository does not implement.

Governance metadata:
- baseline_version: 0.1.0-baseline
- ratified: pending T-1.4 adaptation + user approval
- last_amended: 2026-04-29
- amendments: []
- spec_ref: spec-110 (governance v3 harvest)
- decision_ref: D-110-01 (content adaptation scope)
-->
