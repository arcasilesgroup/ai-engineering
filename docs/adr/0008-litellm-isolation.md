# ADR-0008 — LiteLLM Bridge Isolation

- **Status**: Accepted
- **Date**: 2026-04-27
- **Source**: LiteLLM PyPI compromise (versions 1.82.7/8, March 2026)

## Context

LiteLLM is the most capable multi-LLM router (100+ providers) but its
Python package was compromised on PyPI in March 2026, leaking cloud
credentials, SSH keys, and Kubernetes secrets from machines that auto-
updated.

## Decision

Run the LiteLLM bridge in **strict isolation**:

1. **Hard-pinned versions** with content-addressable hashes (no `latest`,
   no caret/tilde ranges).
2. **Docker container, unprivileged user**, no root access.
3. **No environment credentials** — uses an in-memory keyring fed from
   the user's IDE host token (subscription piggyback) or a one-time
   prompt for BYOK.
4. **Network egress allowlist** — only configured provider domains.
5. **Hot-path latency cap** — p95 ≤ 50ms overhead; modes drop to direct
   provider SDK if exceeded.
6. **For `--profile=regulated`**, replace LiteLLM with TrueFoundry
   (K8s-native, in-cluster gateway, zero external dependencies for PII
   redaction).

## Consequences

- **Pro**: a future LiteLLM compromise no longer escalates to host
  credentials.
- **Pro**: regulated tier is independent of upstream Python supply chain.
- **Con**: more deployment complexity. Mitigated by Docker Compose example
  shipped with the framework (`docs/deployment/litellm-isolated/`).

## Implementation references

- `packages/llm-bridge/` — TS thin wrapper that talks to localhost
- `python/ai_eng_litellm_bridge/` — Python HTTP server inside Docker
