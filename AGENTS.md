# AGENTS.md — Multi-IDE entry point

This file is the canonical instruction file consumed by Codex CLI,
Cursor, Claude Code (alongside CLAUDE.md), Gemini CLI (alongside
GEMINI.md), and other agents that follow the AGENTS.md open standard.

> **Single source of truth**: all framework rules live in
> [`CONSTITUTION.md`](./CONSTITUTION.md). Skills documented in
> [`skills/catalog/`](./skills/catalog/). ADRs in
> [`docs/adr/`](./docs/adr/).

---

## Step 0 — Always

1. Read `CONSTITUTION.md`. Apply Articles I–X to every action.
2. Read the project-level `.ai-engineering/manifest.toml` (if it
   exists) to learn the active profile and overrides.
3. Run no implementation work without an approved spec
   (`.ai-engineering/specs/spec-NNN-*.md` with state = approved).

## Skills available

The following slash commands are first-class skills in this framework.
Each has a full spec at `skills/catalog/<name>/SKILL.md`.

### Workflow + code lifecycle

| Skill | Trigger | Notes |
|-------|---------|-------|
| `/ai-specify` | "design", "let's add", "how should we" | HARD GATE — produces spec |
| `/ai-plan` | "break this down", "create a plan" | HARD GATE — produces plan |
| `/ai-implement` | "go", "build it", "execute the plan" | requires approved plan |
| `/ai-test` | "add tests for", "TDD" | RED-GREEN-REFACTOR enforced |
| `/ai-debug` | "it's broken", "this doesn't work" | 4-phase root-cause |
| `/ai-review` | "review this", "feedback" | parallel specialist agents |
| `/ai-verify` | "is this ready", "prove it works" | evidence-first |
| `/ai-commit` | "commit my changes" | governed pipeline (< 1s hot path) |
| `/ai-pr` | "open a PR" | watch + fix CI to green |

### Governance + security (regulated profiles)

`/ai-security`, `/ai-governance`, `/ai-release-gate`, `/ai-eval`,
`/ai-data`, `/ai-audit-trail`, `/ai-incident-respond`,
`/ai-compliance-report`, `/ai-data-classification`.

### Onboarding + learning

`/ai-start`, `/ai-guide`, `/ai-explain`, `/ai-learn`, `/ai-note`,
`/ai-constitution`, `/ai-bootstrap`.

### SDLC ops

`/ai-resolve`, `/ai-postmortem`, `/ai-hotfix`, `/ai-docs`, `/ai-board`.

### Always-available CLI commands (no LLM)

`ai-eng bootstrap`, `ai-eng doctor`, `ai-eng sync-mirrors`,
`ai-eng cleanup`, `ai-eng plugin <verb>`, `ai-eng llm <verb>`,
`ai-eng skill <verb>`.

---

## Hard rules summary

- HARD GATE: no `/ai-implement` without approved plan.
- HARD GATE: no commit without ruff + gitleaks + injection-guard pass.
- NEVER `--no-verify` on git.
- NEVER bypass deterministic gates.
- NEVER suppress lint/test failures (`# noqa`, `// @ts-ignore`, etc.).
- NEVER push to protected branches (main/master).
- NEVER edit generated mirror files (`.claude/skills/`, `.cursor/`,
  `.codex/`, `.gemini/`).
- NEVER ask the developer for an API key — piggyback on the IDE host.

## Subscription piggyback

The framework deposits artifacts in directories your IDE already reads.
You handle inference using the developer's existing subscription. The
framework consumes **zero tokens** in Layer 1 commands, and only
delegates to your CLI when invoking workflow skills.

For BYOK CI flows, see `ai-eng llm add-provider <name>`.
