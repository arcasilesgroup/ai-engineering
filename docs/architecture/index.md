# Architecture

How `{ai} engineering` is built, for contributors. (Using the framework? Start with [getting started](../guides/getting-started.md).)

## The big picture

`{ai} engineering` is a deterministic governance layer materialized as versioned local files: specs, decisions, skills, agents, hooks, and a hash-chained audit trail. There is no hosted control plane — every IDE reads the same canonical payload.

The authoritative architecture document is [solution-intent.md](../../.ai-engineering/solution-intent.md) (§3.1 carries the layered module map). It embeds the architecture diagrams as Mermaid, so they version with the code.

## Core ideas

- **The deterministic plane gates the probabilistic plane.** Every AI write passes hooks (secrets, policy, mirror-parity, docs-freshness, injection) before it lands; passing writes are appended to `framework-events.ndjson`.
- **Files-only persistence, one source of truth per datum.** See the [persistence doctrine](../persistence-doctrine.md) — Tier 1 NDJSON audit, Tier 2 JSON/YAML records and config, Tier 3 Markdown narrative, with explicitly labelled, rebuildable derived caches.
- **One canonical payload, six surfaces.** `CANONICAL.md` plus `.claude/` skills and agents are mirrored byte-for-byte into Claude Code, GitHub Copilot, Codex, Antigravity, OpenCode, and Cursor; parity is gate-enforced.
- **The canonical chain.** `/ai-brainstorm → /ai-plan → /ai-build → /ai-pr` is the spec-driven delivery workflow.

## The visual system

The README diagrams are diagrams-as-code: HTML/CSS source in [diagrams/build_diagrams.py](diagrams/build_diagrams.py), rendered to PNG and committed under `.github/assets/diagrams/`. The palette, type, and status grammar live in [brand-tokens.md](brand-tokens.md). The terminal demo is a checked-in VHS tape (`.github/assets/demo.tape`). Rendering runs in CI, never on the pre-commit hot path.

## Reference

- [Brand tokens](brand-tokens.md)
- [Persistence doctrine](../persistence-doctrine.md)
- [Supply-chain control matrix](../supply-chain-control-matrix.md)
- [CI branch protection](../ci-branch-protection.md)
