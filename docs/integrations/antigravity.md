# Antigravity Integration

spec-133 D-133-06 documents Antigravity as a **mirror-only** Surface
in ai-engineering. This file explains why and how to use it.

## Status: mirror-only

Antigravity (Google) does NOT support hooks today. Google staff have
confirmed this explicitly on the Antigravity forum
([thread Feb 2026](https://discuss.ai.google.dev/t/hooks-in-antigravity/120458))
— quote: *"In Antigravity, you can achieve 'hook-like' behavior … using
existing features like workflows and rules directories"* — i.e., not
real hooks.

ai-engineering therefore ships:

- `GEMINI.md` (priority 1) + `AGENTS.md` (v1.20.3+) at the repo root,
  carrying the byte-equivalent canonical payload (CLAUDE.md mirror).
- `.agent/skills/` and `.agent/agents/` populated by `sync_mirrors`.

It does NOT ship:

- A hook adapter (no upstream contract to wire to).
- A CLI deterministic probe (no `antigravity-cli` published).
- `.agent/workflows/` automation (procedural recipes, not invocable).

## Re-evaluation

Re-evaluate Antigravity tier when Google ships hooks. Watch the
forum thread linked above for updates. The cost of upgrading
Antigravity to a full Surface is one new ``antigravity-hook-bridge.py``
adapter + lift to ``hook_engine="native"|"plugin"|"stdio"`` in
``ai_engineering.domain.surface``.

## Install

```bash
ai-eng install --surface antigravity
```

The installer treats this as mirror-only — no hooks, no
deterministic-probe wiring. All skill content is reachable through
the standard ``.agent/`` tree that Antigravity reads.
