# CONSTITUTION

> Project-identity contract for this repository. AI-behaviour rules
> (engineering principles, plan-mode default, subagent strategy,
> commit conventions, etc.) live in
> [CANONICAL.md](src/ai_engineering/templates/project/CANONICAL.md)
> and its byte-equivalent mirrors (AGENTS.md, CLAUDE.md,
> .github/copilot-instructions.md). This file owns "what THIS project
> IS" — Mission, Stakeholders, Vocabulary, Prohibitions, Compliance
> gates, Anti-goals, Boundaries, Escalation, Language, Lifecycle phase.

Generated and maintained by the `/ai-constitution` skill (spec-131
D-131-04). Updates are ADR-required and rotate the prior body to
`.ai-engineering/specs/_history-constitution-<YYYY-MM-DD>.md`.

---

## Mission

ai-engineering is a governance framework for AI-assisted software
delivery in regulated environments. The framework ships a
deterministic preprocessor layer (planning, gating, audit) and a
probabilistic execution layer (LLM-driven skills + agents) with a
hard contract between the two: every probabilistic action passes
through a deterministic gate before it touches the filesystem or
the network. Adoption target is teams that ship under regulatory
constraints (banking, healthcare, public sector) where unattended
AI authoring is the cost-driver and auditability is the bar.

## Stakeholders

- **Operator engineers** consuming the framework through their IDE
  host (Claude Code, Codex, Antigravity, GitHub Copilot, OpenCode, Cursor).
- **Security + compliance reviewers** auditing the deterministic
  plane (policy engine, prompt-injection guard, append-only NDJSON
  audit chain).
- **Release engineers** wiring `ai-eng` into CI / CD pipelines.
- **Framework maintainers** — the canonical Spec-Driven Development
  flow (`/ai-brainstorm → /ai-plan → /ai-build → /ai-pr`) is the
  hand-off contract between operator + maintainer.

## Vocabulary

- **Skill** — a `.claude/skills/ai-<name>/SKILL.md` capability invoked
  via `/ai-<name>`. Skills carry frontmatter (`name`, `description`,
  `effort`, `model_tier`, `argument-hint`) plus a layout-conformant
  body (`## Quick start` / `## Workflow` / `## Examples` /
  `## Integration`).
- **Agent** — a `.claude/agents/ai-<name>.md` persona dispatched in a
  fresh context window. Build is the only agent with write
  permissions.
- **Canonical chain** — `/ai-brainstorm → /ai-plan → /ai-build →
  /ai-pr`. `/ai-commit` is an off-chain WIP-only skill.
- **Deterministic plane** — policy engine, audit chain,
  prompt-injection guard, gitleaks, semgrep. Never delegates to the
  LLM for go/no-go decisions.
- **Probabilistic plane** — LLM-driven skill execution. Every write
  passes through the deterministic plane first.

## Prohibitions

1. **No secrets in source.** `gitleaks protect --staged` blocks every
   commit; `gitleaks detect` blocks every push. Risk acceptance
   flows through the ledger (`ai-eng risk accept …`), never via
   inline allowlists.
2. **No suppression markers.** No `# noqa`, `# nosec`,
   `// @ts-ignore`, `// nolint`, `# pragma: no cover`, `// NOSONAR`.
   Refactor or risk-accept. spec-128 sub-d ships the repo-wide gate.
3. **No `--no-verify` ever.** Pre-commit and pre-push hooks are the
   on-disk evidence the deterministic plane fired.
4. **No backwards-compatibility shims** for renamed / deleted /
   migrated files. Hard rename, hard delete, hard migration.
   CHANGELOG documents the breakage.
5. **No PII, no operator names, no machine paths** in any committed
   file (specs, CHANGELOG, docs, telemetry, lessons, runbooks). Use
   placeholders (`$HOME/.local/bin`, `$(which …)`) where
   machine-relative references are needed.
6. **No multi-round retry inside the quality loop.** Fail-loud only;
   blockers STOP and escalate to the operator.
7. **No CONSTITUTION auto-amendment.** The 10 sections above are
   operator-authored. `/ai-constitution amend` rotates the prior
   body, applies the diff, bumps the minor version, and emits an
   audit event — but the operator types the new content.
8. **Single Source of Truth Per Datum.** Every datum has exactly
   one canonical writable store. Derived caches are explicitly
   labelled (named, with a rebuild command) and rebuildable on
   demand. See [docs/persistence-doctrine.md](docs/persistence-doctrine.md)
   for the three-tier files-only model and the rebuild semantics.

## Compliance gates

1. **Pre-commit gate** (sub-1s p95) — `ai-eng gate pre-commit` runs
   `gitleaks protect --staged`, `ruff format --check`, `ruff check`,
   and `ai-eng spec verify` on staged hunks only. Anything heavier
   belongs on pre-push or CI.
2. **Pre-push gate** (under 5s p95) — `ai-eng gate pre-push` runs
   `semgrep --config .semgrep.yml`, `pip-audit`, the unit-test
   suite, and `ty` static type-checking.
3. **CI** — re-runs every gate above plus the slower checks
   (integration tests, SonarCloud, Scorecard, SBOM diff). CI is the
   final authority; local gates are an early-warning layer.
4. **Allowlist hard rule.** `.gitleaks.toml [allowlist] paths` MUST
   list explicit individual files, never wildcards. Regex
   allowlists and stopwords are forbidden for suppressing
   real-secret findings. When remediation cannot land before the
   publish window closes, bypass goes through
   `ai-eng risk accept --finding-id <rule_id>` — time-bounded,
   owner-attributed, spec-referenced.
5. **Supply-chain bar.** The framework's own dependencies and CI
   ship with Sigstore keyless OIDC signature verification where
   available, SLSA v1.0 provenance metadata, a CycloneDX SBOM
   published per release, and an OpenSSF Scorecard run wired into
   CI. `--ignore-scripts` for npm/bun installs disables
   install-time script execution. GitHub Actions are pinned to
   immutable commit SHAs, never mutable tags.

## Anti-goals

- **No skill marketplace, no plugin store, no remote skill fetch.**
  Skills live in-tree; users fork or contribute upstream.
- **No multi-LLM orchestration layer.** Each session runs against
  one IDE-host LLM at a time. BYOK CI is opt-in, documented as
  not-yet-implemented at the current scale.
- **No managed-cloud component.** The framework runs entirely on
  the operator's machine plus their existing CI runner.
- **No telemetry collection by default.** `telemetry.consent:
  strict-opt-in` in `manifest.yml`; the audit chain stays local
  NDJSON unless the operator wires an exporter.
- **No regulated-tier provider lock-in.** Vendor selection for
  Layer 3 (BYOK CI) is a deployment-time decision captured by ADR,
  never by framework default.

## Boundaries

- **Framework-owned** — every file under
  `.ai-engineering/`, `.claude/`, `.codex/`, `.agents/`, `.opencode/`,
  `.cursor/`, `.github/skills/`, `.github/agents/`,
  `.github/copilot-instructions.md`, AGENTS.md, CLAUDE.md,
  CANONICAL.md, this CONSTITUTION.md, and
  `scripts/sync_mirrors/`. Operators MUST NOT hand-edit generated
  mirrors; `sync_command_mirrors.py` regenerates from canonical
  sources.
- **Team-owned** — every other file in the repository:
  application source, tests, configuration, CI workflows
  specific to the team's product surface.
- **Generated mirrors carry `DO NOT EDIT` headers** and
  `linguist-generated=true`.

## Escalation

- **Quality-gate failure** (pre-commit / pre-push / CI) → stop, fix,
  retry. `ai-eng doctor --fix` is the first-line tool.
- **Prompt-injection-guard fire** → exit 2 + framework_error event.
  Investigate the offending content; never bypass the guard.
- **Hook integrity violation** (`AIENG_HOOK_INTEGRITY_MODE=enforce`)
  → regenerate the manifest after intentional edits via
  `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py`.
- **Risk-acceptance request** → `ai-eng risk accept --finding-id
  <id> --justification <text> --spec <id> --follow-up <plan>`. The
  ledger is the single source of truth; CI consumes it.
- **CONSTITUTION change request** → `/ai-constitution amend`,
  diff-confirm, rotate to `_history-constitution-<date>.md`,
  minor-version bump, audit event.

## Language

English (project natural language for code identifiers, commits,
specs, CHANGELOG entries, and docs). Operator-facing prompts in the
interview surface (`/ai-constitution`) accept any language; the
written CONSTITUTION.md stays in English for cross-team review.

## Lifecycle phase

**Stabilising** — the framework has shipped its canonical chain
(spec-127 / spec-128 / spec-129) and is now hardening DX and reliability (spec-131 through spec-182, v0.12.3).
Breaking changes still land without backwards-compat shims (anti-goal
above), but the deterministic plane contract (audit chain shape,
risk-acceptance ledger, hooks manifest) is frozen modulo ADR.

---

<!--
ADAPTATION NOTE (spec-131 D-131-04)

Rescoped 2026-05-11 from a 13-Article AI-behaviour document into a
10-section project-identity contract. Pre-migration body rotated
verbatim to
`.ai-engineering/specs/archive/constitution-rotations/2026-05-11.md`
(traceability per R-131-03). AI-behaviour content migrated to
`src/ai_engineering/templates/project/CANONICAL.md` §§1-13, mirrored
byte-equivalent into AGENTS.md / CLAUDE.md / GEMINI.md /
.github/copilot-instructions.md by `scripts/sync_mirrors/core.py`.

Governance metadata:
- spec_ref: spec-131 (DX Excellence Refactor)
- decision_ref: D-131-04 (project-identity pivot)
- ratified: 2026-05-11
- last_amended: 2026-05-11
- amendments: [pre-2026-05-11 body preserved in archive/constitution-rotations/2026-05-11.md]
-->
