---
id: "020"
slug: "multi-agent-model-evolution"
status: "closed"
created: "2026-02-23"
---

# Spec 020 — Multi-Agent Model Evolution

## Problem

ai-engineering's agent/skill model was designed as a content-first governance framework where AI reads markdown and follows procedures. As the multi-agent ecosystem matures (Claude Code subagents, OpenAI Codex, Google ADK, A2A/MCP protocols), the current model has critical gaps:

1. **Token overhead**: every agent session loads 3-5K+ tokens of governance context before any work begins. In multi-agent scenarios (3 agents parallel), this balloons to 15K+ tokens of governance overhead.

2. **No progressive disclosure**: all 46 skills and 9 agents are always visible regardless of project context (stack, OS, available tooling). A .NET project sees Python skills; a macOS session sees Windows-only patterns.

3. **Skills are flat files**: a skill is a single `.md` file. It cannot bundle deterministic scripts, reference documents loaded on-demand, or template assets. Every procedure must be re-interpreted by the AI each time.

4. **Agent definitions are human-only**: agent files define personas but lack machine-parseable metadata (capabilities, inputs/outputs, scope, tool restrictions). An orchestrator cannot programmatically select the right agent.

5. **No interoperability path**: skills and agents are not compatible with AgentSkills.io spec, A2A Agent Cards, or MCP tool interfaces. ai-engineering content is invisible to external frameworks.

6. **Naming friction**: `skills/utils/` is a grab-bag (patterns are not utilities); agent scope (read-only vs read-write) is not signaled in metadata.

## Solution

Evolve the agent/skill model toward a **dual-layer architecture** that preserves the content-first governance strengths while adding machine-readable interfaces for interoperability and efficiency:

1. **Progressive disclosure**: restructure CLAUDE.md and skill loading so only essential context loads at session start; skill bodies and standards load on-demand when invoked.

2. **Skill directories with resources**: evolve skills from single `.md` files to AgentSkills-compatible directories with `SKILL.md` + optional `scripts/`, `references/`, and `assets/`.

3. **Skill gating metadata**: add eligibility criteria (stacks, bins, env, OS) so irrelevant skills are filtered at load time.

4. **Agent structured metadata**: add machine-parseable YAML frontmatter to agent files (capabilities, scope, inputs/outputs, tool restrictions) — compatible with future A2A Agent Card generation.

5. **Rename `utils/` to `patterns/`**: better reflects that these are reference catalogs, not utility procedures.

6. **Token measurement**: document expected token cost per skill/agent for conscious context management.

## Scope

### In Scope

- Skill directory structure migration (flat `.md` → directory with `SKILL.md`).
- AgentSkills-compatible frontmatter for skills.
- Skill gating metadata schema (stacks, bins, env, OS).
- Agent structured frontmatter (capabilities, scope, inputs/outputs).
- Rename `skills/utils/` → `skills/patterns/`.
- Progressive disclosure guidelines in CLAUDE.md.
- Token budget documentation per skill category.
- Update all cross-references (CLAUDE.md, product-contract, manifest, instruction files, command wrappers).
- Content integrity validation after migration.

### Out of Scope

- MCP tool server implementation (Phase 3 roadmap).
- A2A Agent Card endpoint implementation (Phase 3 roadmap).
- ACP bridge implementation (Phase 3 roadmap).
- Runtime enforcement of skill gating (future Python runtime work).
- ClawHub-style registry (Phase 2 roadmap).
- Changing the governance model (decision-store, audit-log, spec workflow unchanged).
- Python module changes.

## Acceptance Criteria

1. All 46 skills exist as directories with `SKILL.md` instead of flat files.
2. All skills have AgentSkills-compatible YAML frontmatter (name, description, metadata).
3. All 9 agents have structured YAML frontmatter with capabilities, scope, inputs, outputs.
4. Skill gating metadata schema is documented in `standards/framework/core.md`.
5. `skills/utils/` renamed to `skills/patterns/` with all cross-references updated.
6. CLAUDE.md updated with progressive disclosure guidelines (on-demand skill loading).
7. Token budget table published (characters/tokens per skill category).
8. Content integrity check passes (all 6 categories).
9. All instruction files (CLAUDE.md, AGENTS.md, codex.md, copilot-instructions.md) reflect new structure.
10. All command wrappers (`.claude/commands/`, `.github/prompts/`, `.github/agents/`) updated.
11. Manifest.yml reflects new skill directory structure.
12. At least 3 skills demonstrate `scripts/` or `references/` resources (commit, debug, security as pilots).

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D020-001 | Skills migrate to directories with SKILL.md (AgentSkills-compatible) | Cross-framework interoperability; enables bundled resources; aligns with OpenClaw/Codex patterns |
| D020-002 | Agent metadata is additive (frontmatter on existing .md), not replacement | Preserves human-readable persona; avoids rewrite; machine-readable is generated layer |
| D020-003 | `utils/` renamed to `patterns/` | Content is reference patterns (python-patterns, dotnet-patterns), not executable utilities |
| D020-004 | Skill gating is metadata-only (no runtime enforcement yet) | Content-first philosophy; runtime enforcement deferred to Python module rewrite |
| D020-005 | Progressive disclosure is advisory (guidelines in CLAUDE.md), not enforced | AI agents load on-demand by instruction; no technical enforcement mechanism in content-first model |
