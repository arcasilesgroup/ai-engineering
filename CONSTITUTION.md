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
2. `/ai-dispatch` cannot run without `plan.md` marked ready and a user
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
2. The Deterministic Plane is enforced today by three concrete
   subsystems that MUST remain non-optional: an OPA-style policy
   engine that gates write actions, an immutable append-only audit
   log under `.ai-engineering/state/framework-events.ndjson`, and a
   regex-based prompt-injection guard hook
   (`prompt-injection-guard.py`) that scans LLM outputs before they
   reach a write tool.
3. ML-based input classifiers and OBO/identity-broker token exchange
   are explicitly OUT OF SCOPE at the current scale. The current
   framework relies on regex/heuristic detection and direct IDE-host
   credentials; any reintroduction requires a new spec + ADR.
4. The `build` agent is the **only** agent with code write
   permissions. Every other agent operates in read-only or
   advisory mode.

## Article IV — Subscription Piggyback

1. The framework **never** asks the developer for an API key in the
   default path.
2. Layer 1 (deterministic) requires no LLM.
3. Layer 2 (workflow) delegates inference to the developer's IDE host
   subscription (e.g. Claude Code, Copilot, Cursor) so no BYOK is
   needed for normal authoring flows.
4. Layer 3 (BYOK CI) is opt-in for CI flows. The current framework
   **documents the pattern but does not implement BYOK CI**; the CI
   gates run deterministic Layer 1 only. A future spec must land
   provider-agnostic BYOK CI before Layer 3 is considered active.
5. No specific regulated-tier provider is mandated. Any vendor
   selection for Layer 3 is a deployment-time decision and MUST be
   captured by ADR.

## Article V — Single Source of Truth

1. Skills live ONCE under `.claude/skills/ai-<name>/SKILL.md` (the
   canonical Claude Code path used today).
2. IDE mirrors for non-Claude hosts (GitHub Copilot, Codex, Gemini
   CLI, etc.) are **generated**, never edited by hand. Mirror files
   carry the `DO NOT EDIT` header and `linguist-generated=true`.
3. `ai-eng sync-mirrors` is the only authorized writer of those
   mirrors; manual edits are reverted on the next sync.

## Article VI — Supply Chain Integrity

1. The framework's **own** dependencies and CI MUST ship with
   Sigstore keyless OIDC signature verification where available,
   SLSA v1.0 provenance metadata, a CycloneDX SBOM published per
   release, and an OpenSSF Scorecard run wired into CI.
2. CI enforces `--ignore-scripts` for npm/bun installs to disable
   arbitrary install-time script execution.
3. GitHub Actions are pinned to **immutable commit SHAs**, not
   mutable tags.
4. Article VI applies to the framework itself. Third-party plugin /
   extension distribution is OUT OF SCOPE at the current scale and
   has no tier classifications associated with this Constitution.

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

## Article XI — Operating Behaviour (Cross-IDE)

The seven rules below are non-negotiable across **every** supported IDE
(Claude Code, Codex, Gemini, GitHub Copilot). They were previously stated
only in `GEMINI.md`; lifting them into the Constitution restores the
"AGENTS.md is the canonical cross-IDE rulebook" contract that
`manifest_coherence.py` validates.

1. **Plan Mode Default** — enter plan mode for any non-trivial task
   (3+ steps or architectural decisions). Stop and re-plan when something
   goes sideways instead of pushing through. Verification work uses plan
   mode too. Reduce ambiguity upfront via `/ai-brainstorm`.
2. **Subagent Strategy** — offload research, exploration, and parallel
   analysis to subagents. One task per subagent for focused execution.
   Never have one subagent do two unrelated things.
3. **Self-Improvement Loop** — after any user correction, update
   `.ai-engineering/LESSONS.md` with the pattern. Iterate on lessons until
   the mistake rate drops. Read lessons proactively at session start.
4. **Verification Before Done** (proof-before-done) — never mark a task
   complete without proving it works. Run tests, run the linter, check
   the output. Diff behaviour when relevant. Ask: "would a staff
   engineer approve this?"
5. **Demand Elegance (Balanced)** — pause and ask "is there a more
   elegant way?" for non-trivial changes. Skip for simple, obvious
   fixes. Clever is bad; simple and clear is elegant.
6. **Autonomous Bug Fixing** — when given a bug report, fix it. Don't
   ask for hand-holding. If you see a bug while working on something
   else, fix it and mention it in the commit.
7. **Parallel Execution** — batch independent operations into
   simultaneous tool calls. Never go sequential when you can go parallel.

## Article XII — Secrets-Gate Defense in Depth

The framework ships a two-stage secrets pipeline that fires on every
commit and every push. Findings BLOCK at `CRITICAL`, `HIGH`, and
`MEDIUM`; `LOW` warns. Suppression is forbidden (Article VII). Every
acceptance flows through the risk-acceptance ledger -- never via inline
allowlists or `# nosec` markers.

1. **Pre-commit gate** (sub-1s p95) -- `ai-eng gate pre-commit` runs
   `gitleaks protect --staged`, `ruff format --check`, `ruff check`,
   and `ai-eng spec verify` on staged hunks only. Anything heavier
   belongs on the pre-push or CI surface, not the local hot path.
2. **Pre-push gate** (under 5s p95) -- `ai-eng gate pre-push` runs
   `semgrep --config .semgrep.yml`, `pip-audit`, the unit-test suite,
   and `ty` static type-checking. Defense-in-depth catches what
   pre-commit cannot afford to scan.
3. **CI** -- re-runs every gate above, plus the slower checks
   (integration tests, SonarCloud, Scorecard, SBOM diff). CI is the
   final authority; local gates are an early-warning layer.
4. **Configuration** -- `.semgrep.yml` extends version-pinned
   community packs (`p/python`, `p/bash`, `p/owasp-top-ten`,
   `p/security-audit`). `.gitleaks.toml` + `.gitleaksignore` scope the
   secrets-detector. The semgrep update model is documented in
   `.ai-engineering/contexts/semgrep-update-model.md` -- pinned packs
   require quarterly manual review.
5. **Risk acceptance** -- when remediation cannot land before the
   publish window closes, run
   `ai-eng risk accept --finding <hash>` to log the bypass with a TTL,
   owner, and spec reference (see Article VII).
   `.ai-engineering/contexts/risk-acceptance-flow.md` documents the
   full lifecycle.
6. **Visibility** -- `ai-eng doctor` surfaces a `secrets_gate` runtime
   probe that verifies the binaries (`gitleaks`, `semgrep`),
   configurations, and the pre-commit / pre-push hook wiring. The
   probe is advisory: a missing tool warns, never fails the doctor
   summary.

## Article XIII — Active Spec Workflow Contract

The framework enforces a single canonical spec-workflow flow. Every
skill that touches `.ai-engineering/specs/` MUST follow the identical
sequence; depth scales with spec size, but process steps are invariant.

1. **Canonical flow** — the only authorized spec lifecycle is:
   `/ai-brainstorm → /ai-plan → /ai-dispatch | /ai-autopilot → /ai-pr`.
   No skill may bypass, reorder, or substitute these stages.
2. **Depth scaling** — `/ai-autopilot` is the execution surface for
   specs with ≥3 concerns or ≥10 file changes; `/ai-dispatch` handles
   smaller specs. Both share the upstream brainstorm + plan stages and
   the downstream PR stage; only the execution intensity varies.
3. **Three-file specs/ surface** — `.ai-engineering/specs/` contains
   exactly three files: `spec.md` (active spec), `plan.md` (active
   plan), `_history.md` (one-line ledger of completed lifecycles). No
   subdirectories, no numbered archives, no progress dirs, no
   work-plane artifacts. Numbered archive specs are recoverable via
   `git log -- .ai-engineering/specs/spec-NNN-*.md`. Decisions are
   authoritative in `state.db.decisions`. Autopilot transient state
   lives at `.ai-engineering/runtime/autopilot/` (gitignored) —
   never under `specs/`.
4. **Hard rule for skills** — any skill that reads or writes `specs/`
   MUST consume only the canonical 3 files. Reading numbered archives
   from disk is forbidden; query `state.db.decisions` or git history
   instead.
5. **Enforcement** — `tests/unit/specs/test_canonical_structure.py`
   asserts the 3-file invariant on every CI run.
   `tests/unit/specs/test_active_workflow_compliance.py` asserts that
   each lifecycle skill (`/ai-brainstorm`, `/ai-plan`,
   `/ai-dispatch`, `/ai-autopilot`, `/ai-pr`) exists and references
   the canonical surface. Any deviation fails CI.

---

<!--
ADAPTATION NOTE

This Constitution was harvested as a baseline from `ai-engineering-v3`
on 2026-04-29 (spec-110 task T-1.3) and then **adapted to current
scale** in task T-1.4 per decision D-110-01.

Adaptations applied (T-1.4) — we **deliberately do not include** the
following from the v3 baseline; see spec-110 D-110-01 for the
rationale:
- Article III: ML-based input classification and OBO/identity-broker
  token exchange are intentionally absent. The article now lists
  only the OPA-style policy engine, the immutable audit log, and the
  regex-based prompt-injection-guard hook that exists today.
- Article IV: no regulated-tier vendor is named; the article
  documents the BYOK CI pattern honestly as not-yet-implemented at
  the current scale.
- Article V: aligned skill path to the canonical
  `.claude/skills/ai-<name>/SKILL.md` (current repo) and noted that
  `ai-eng sync-mirrors` generates IDE mirrors.
- Article VI: scoped to the framework's own dependencies and CI;
  third-party plugin distribution and any associated tier
  classifications are explicitly out of scope at the current scale.
- Articles I, II, VII, VIII, IX, X: kept with minimum changes.

Governance metadata:
- baseline_version: 0.1.0-baseline
- adapted_version: 0.1.0-adapted
- ratified: pending user approval per spec-110 acceptance gate
- last_amended: 2026-04-29
- amendments: []
- spec_ref: spec-110 (governance v3 harvest)
- decision_ref: D-110-01 (content adaptation scope)
-->
