# ADR-0005 — Subscription Piggyback (No API Keys From Devs)

- **Status**: Accepted
- **Date**: 2026-04-27

## Context

Most agentic frameworks require the developer to bring their own API key
and pay for tokens directly. This creates duplicate billing (the dev
already pays for Claude Pro, Cursor Pro, ChatGPT Plus, etc.) and a
huge friction point for adoption.

## Decision

`ai-engineering` **NEVER** asks the developer for an API key in the
default path. Instead, it deposits **artifacts** (skills, agents, hooks,
manifests) into directories the IDE host already reads. The IDE handles
inference using the user's existing subscription.

Three layers of operation:

1. **Layer 1 — Deterministic** (no LLM): install, cleanup, doctor,
   plugin install/verify, release-gate, board sync, governance, risk
   acceptance, migrate, sync-mirrors. ~70% of the framework's value.
2. **Layer 2 — IDE Host Delegation**: skills like `specify`, `implement`,
   `debug`, `review`, `verify` spawn the user's IDE CLI in headless
   mode (`claude -p`, `cursor-agent -p`, `codex exec`, `gemini -p`,
   `cline -y`). The IDE's subscription handles the inference.
3. **Layer 3 — BYOK opt-in** (CI only): when no IDE host is present,
   the user can configure LiteLLM with their own provider key.

## Consequences

- **Pro**: zero friction — install + use with zero new credentials.
- **Pro**: framework is licensable as **governance**, not as a SaaS
  LLM wrapper. Different commercial model entirely.
- **Pro**: regulated tier piggybacks on Claude Code+Bedrock or Copilot
  Enterprise — already BAA/DPA-signed.
- **Con**: subject to the IDE host's rate limits during heavy use.
  Mitigated by Layer 3 BYOK opt-in for CI batch flows.

## Implementation references

- `ai-engineering.toml` — `[framework.principles] subscription_piggyback = true`
- `packages/cli/src/main.ts` — CLI dispatches to layers based on command.
