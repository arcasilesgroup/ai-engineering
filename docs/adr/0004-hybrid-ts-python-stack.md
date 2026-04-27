# ADR-0004 — Hybrid TypeScript+Bun + Python Stack

- **Status**: Accepted
- **Date**: 2026-04-27

## Context

Choices considered: **Bun pure**, **Python pure**, **Rust/Go monolith**,
**TS+Python hybrid**.

Constraints:
- 5 of 6 target IDEs are TS-first (Cursor, Codex CLI, Gemini CLI,
  Copilot, Antigravity).
- LiteLLM and DeepEval — the most mature multi-LLM router and eval
  frameworks — exist only in Python.
- Hooks are battle-tested in Python (`prompt-injection-guard.py`,
  `gitleaks` wrappers).
- Bun cold start (6-15ms) vs Python (30-80ms) matters for a CLI invoked
  100+ times per session.

## Decision

**Hybrid** with explicit boundaries:

| Component | Lang | Reason |
|-----------|------|--------|
| `ai-eng` CLI binary | TS+Bun | cold start; single-binary cross-target |
| Slash command runtime | TS+Bun | in-process in TS-first IDEs |
| Mirror sync | TS+Bun | filesystem-heavy |
| MCP server | TS+Bun | low overhead, IDE-native |
| Hooks (PreToolUse, PostToolUse, injection-guard) | Python | battle-tested; idempotent; OS-portable |
| Evals (deepeval, ragas, promptfoo) | Python | dominant ecosystem |
| LiteLLM bridge | Python (HTTP localhost) | only mature multi-LLM router |
| Lint/format | ruff (Py) + Biome (TS) | both Rust-backed top-tier |
| Tests | bun test (TS) + pytest (Py) | each in its lane |

IPC over **JSON-RPC over Unix sockets** with parent-child heartbeats
(zombie process detection) and unified error serialization across
languages (JSON Schema in `shared/schemas/`).

## Consequences

- **Pro**: best-of-breed in each language.
- **Pro**: incremental migration path for legacy Python users.
- **Con**: two toolchains to maintain. Mitigated by a single root CI
  matrix that runs both.
- **Con**: IPC adds latency. Bench cap: p95 ≤ 50ms overhead.

## Alternatives considered

- **Rust/Go monolith** — single binary attractive but loses LiteLLM,
  DeepEval, and Python hook ecosystem. Revisit if both reach TS/Rust
  parity.
- **Bun pure** — would block until Bun has sandbox parity with Deno
  (open issue oven-sh/bun#26637) and a TS replacement for LiteLLM exists.
- **Python pure** — cold start unacceptable for CLI invoked at session
  start; loses IDE host alignment.
