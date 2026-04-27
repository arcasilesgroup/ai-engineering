---
title: 5-minute on-ramp
description: Install, bootstrap, and ship your first feature with ai-engineering. Mirrors GETTING_STARTED.md.
sidebar:
  order: 1
---

This page mirrors `GETTING_STARTED.md` from the source repository so
the docs site is self-contained. For the canonical version, see
[`GETTING_STARTED.md`](https://github.com/soydachi/ai-engineering/blob/main/GETTING_STARTED.md).

## Prerequisites

- **macOS / Linux / WSL2** (native Windows is on the roadmap, not yet
  supported).
- **An AI coding subscription** — pick one (or more):
  - Claude Pro / Max / Team / Enterprise
  - GitHub Copilot Pro / Business / Enterprise
  - ChatGPT Plus / Pro / Enterprise (with Codex CLI)
  - Cursor Pro / Business
  - Gemini Code Assist / Advanced
  - Cline (BYOK to any provider)
- **No additional API key required** — the framework piggybacks on the
  subscription you already pay for. See
  [ADR-0005 — Subscription Piggyback](/adr/).

The framework will install Bun and `uv` automatically if missing.

## Install (alpha, build-from-source)

```bash
git clone https://github.com/soydachi/ai-engineering.git
cd ai-engineering

# TS side
bun install --ignore-scripts
bun run build

# Python side (optional during alpha — Phase 5+)
uv sync

# Local dev binary
bun packages/cli/src/main.ts --help
```

When the production installer ships:

```bash
curl -fsSL https://get.ai-engineering.dev | bash
ai-eng --version
```

User-scope install (no `sudo`). Detects Bun runtime and installs it if
missing. Honors `XDG_CONFIG_HOME`.

## First project

```bash
mkdir my-project && cd my-project
git init
ai-eng bootstrap
```

This creates `.ai-engineering/manifest.toml` and a folder layout under
`.ai-engineering/`. It auto-detects the IDE hosts you have installed and
prepares mirror targets.

## First feature (inside Claude Code, Cursor, Codex CLI, …)

```text
/ai-specify add magic-link auth with resend
```

Answer the planner's questions one at a time. The skill produces
`.ai-engineering/specs/spec-001-magic-link.md`. Review and approve.

```text
/ai-plan
```

The planner decomposes the spec into TDD-paired tasks at
`.ai-engineering/specs/spec-001/plan.md`. Review and approve.

```text
/ai-implement
```

The `builder` agent runs RED → GREEN → REFACTOR per task with quality
gates after each phase.

```text
/ai-pr
```

Pre-push gates run in three lanes (verify, docs, security). PR opens.
Watch loop monitors CI and dispatches the builder to fix failures up to
3 iterations.

## Day-2 commands you'll use

```bash
ai-eng doctor              # local install health check (no LLM)
ai-eng sync-mirrors        # regenerate IDE mirrors after editing skills/catalog
ai-eng plugin search soc2  # browse the marketplace
ai-eng plugin install @ai-engineering-verified/soc2-pack
```

## Regulated industry profile

```bash
ai-eng install --profile banking --tenant fintech-acme
```

Activates `audit-trail`, `incident-respond`, `compliance-report`,
`data-classification`. Pins LiteLLM to TrueFoundry (in-cluster, zero
external dependencies). Adds gitleaks banking allowlist + dependency
license check (rejects GPL/AGPL).

See [ADR-0008 — LiteLLM Isolation](/adr/) for the security boundary.

## Where to go next

- [Architecture overview](/architecture/overview/) — diagrams of the
  whole system.
- [Master plan](/architecture/master-plan/) — phase status and
  roadmap.
- [Skills catalog](/skills/) — every SKILL.md frontmatter at a glance.
- [Agents](/agents/) — 7 agent role definitions.
- [ADRs](/adr/) — the ten architecture decision records.
