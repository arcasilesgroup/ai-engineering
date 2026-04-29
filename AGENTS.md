# AGENTS.md — Canonical Cross-IDE Entry Point

> Open standard adopted in 2026-04 by Codex CLI, Cursor, Claude Code, and Gemini CLI.
> This file is the single source of truth for cross-IDE agent rules.
> CLAUDE.md, GEMINI.md (root), .github/copilot-instructions.md and .codex/AGENTS.md
> are overlays that reference this file and add only IDE-specific specifics.

## Step 0 — Always

1. Read [CONSTITUTION.md](./CONSTITUTION.md). Apply Articles I–X to every action.
2. Read project manifest at `.ai-engineering/manifest.yml` for active providers/work_items config.
3. No implementation work without an approved spec at `.ai-engineering/specs/spec-NNN-*.md` with `status: approved`.

## Skills Available

Invoke as `/ai-<name>`. Each skill declares its own trigger phrases and effort level in frontmatter.
Source of truth: the canonical skill path declared in [Article V](./CONSTITUTION.md#article-v--single-source-of-truth). Mirrors for other IDEs are generated, never edited by hand.

| Skill | Trigger | Notes |
|---|---|---|
| `/ai-analyze-permissions` | "too many permission prompts", "consolidate allow rules" | Audit and consolidate IDE permission grants. Claude Code only. |
| `/ai-animation` | "animate this", "add transitions", "micro-interactions" | Motion, transitions, gestures. Not for design systems or visual art. |
| `/ai-autopilot` | "ship the whole thing", spec is large (3+ concerns / 10+ files) | Autonomous end-to-end delivery. Decompose, plan, DAG, waves, PR. |
| `/ai-board-discover` | "set up the board", "configure our ADO board" | Detects GitHub Projects v2 / Azure DevOps fields and writes manifest. |
| `/ai-board-sync` | "move this issue to in-review", "update the board" | Lifecycle state sync. Fail-open. Auto-invoked by brainstorm/dispatch/pr. |
| `/ai-brainstorm` | "let's add X", "how should we", any work without an approved spec | HARD GATE — produces a reviewed spec. No code until user approves. |
| `/ai-canvas` | "create a poster", "design a banner", "branding piece" | Static visual artifacts (PDF/PNG). Not for UI, animation, or AI media. |
| `/ai-cleanup` | "tidy up", "clean up branches", "sync to main" | Branch hygiene. Auto-invoked after PR merge. |
| `/ai-code` | "implement this", "write the code for", "build this function" | Production code with interface-first design. Not for tests or debugging. |
| `/ai-commit` | "commit my changes", "save my work", "ship it" | Governed pipeline: format, lint, secrets, conventional commit, push. |
| `/ai-constitution` | "draft the constitution", "amend Article X" | Generate / update `CONSTITUTION.md` via ADR. |
| `/ai-create` | "create a new skill", "add a slash command" | Extend the framework with a new skill, agent, or capability. |
| `/ai-debug` | "it's not working", "I'm getting an error", "CI is failing" | Systematic 4-phase root-cause diagnosis. Never patches symptoms. |
| `/ai-design` | "design this page", "create a design system", "color palette for" | UI design, design systems, aesthetic direction. |
| `/ai-dispatch` | "go", "execute the plan", "start building" | HARD GATE — produces plan. Orchestrates subagents per task with two-stage review. Requires an approved plan from `/ai-plan`. |
| `/ai-docs` | "update the changelog", "the README is stale", "document this feature" | Documentation lifecycle. Auto-invoked by `/ai-pr`. |
| `/ai-eval` | "how reliable is this", "did my changes break anything" | AI system reliability metrics — distinct from `/ai-test` and `/ai-verify`. |
| `/ai-explain` | "how does this work?", "trace through this", "explain this pattern" | Engineer-grade explanations with diagrams and execution traces. |
| `/ai-governance` | "are quality gates enforced?", "governance report for auditors" | Governance process validation. Complements `/ai-security`. |
| `/ai-guide` | "where does auth happen?", "I'm new to this project" | Architecture tours, decision archaeology, onboarding. Read-only. |
| `/ai-instinct` | "start observing", "consolidate instincts", "instinct review" | Observe corrections and consolidate workflow patterns. |
| `/ai-learn` | "the AI keeps doing X wrong", "learn from this PR" | Analyzes merged PR review feedback and writes lessons. |
| `/ai-market` | "write a blog post to publish", "investor deck", "post to X" | Marketing and go-to-market execution. Not for internal docs. |
| `/ai-mcp-sentinel` | "review this skill before install", "post-update audit" | Cold-path MCP/skill security audit via LLM coherence. |
| `/ai-media` | "generate an image", "create a thumbnail", "AI video" | AI-generated images/video/audio. Cost-aware. Requires fal-ai MCP. |
| `/ai-note` | "save this", "remember this finding", "what did we find about" | Cross-session knowledge. Save anything that took >30 minutes to figure out. |
| `/ai-pipeline` | "set up CI/CD", "is this workflow secure?" | GitHub Actions / Azure Pipelines workflows with policy validation. |
| `/ai-plan` | "break this down", "create a plan", "what tasks do we need" | HARD GATE — produces plan. Phased execution from approved spec. |
| `/ai-platform-audit` | "audit platform support", "are skill counts correct per platform?" | Verify IDE platform integration end-to-end. |
| `/ai-postmortem` | "we had an incident", "write up the outage", "near-miss analysis" | DERP format (Detection, Escalation, Recovery, Prevention). |
| `/ai-pr` | "open a PR", "submit this for review", "draft PR" | Pre-push gates, structured PR body, watches and fixes CI until merged. |
| `/ai-prompt` | "this prompt isn't working", "optimize this skill description" | Optimize prompts and skill descriptions. |
| `/ai-release-gate` | "is this ready to ship?", "GO/NO-GO" | Aggregated 8-dimension release readiness verdict. |
| `/ai-resolve-conflicts` | "I have conflicts", "rebase failed", "I see <<<<<<< in the file" | Type-aware conflict resolution by category. |
| `/ai-review` | "review this", "give me feedback", "is this merge-ready" | Specialist roster code review. Use `/ai-verify` for evidence-backed gates. |
| `/ai-run` | "run these backlog items", "execute these GitHub issues" | Autonomous backlog execution end-to-end. |
| `/ai-schema` | "add a column", "we need a migration", "the query is slow" | Schema design, safe migrations with rollback, query optimization. |
| `/ai-security` | "is this secure?", "audit dependencies", "check for secrets" | Pre-release security gate, SBOM, SAST with OWASP/CWE mapping. |
| `/ai-skill-evolve` | "evolve this skill", "improve /ai-plan", "make /ai-review better" | Improves an existing skill from real project pain — not theory. |
| `/ai-slides` | "create a talk deck", "pitch deck", "convert my PPTX" | Zero-dependency self-contained HTML decks. |
| `/ai-sprint` | "start sprint planning", "let's do the retro", "sprint goals check" | Sprint lifecycle: plan, retro, review deck. |
| `/ai-standup` | "write my standup", "what did I ship this week" | Status update from real git/PR history. |
| `/ai-start` | "hello", "let's start", "good morning", "what's the status" | Session bootstrap. Loads context, activates instinct, shows dashboard. |
| `/ai-support` | "a user is reporting that", "investigate this bug report" | Customer issue triage and knowledge base. |
| `/ai-test` | "add tests for", "I need 80% coverage", "test this" | TDD (RED-GREEN-REFACTOR), coverage gaps, test strategy. |
| `/ai-verify` | "check my code", "is this ready to merge", "prove it works" | Evidence-first verification by 4 specialists. |
| `/ai-video-editing` | "cut this video", "make a highlight reel", "reframe for TikTok" | Real footage editing with FFmpeg/Remotion. Not for generated video. |
| `/ai-write` | "write a blog post", "pitch deck", "solution intent doc" | Audience-aware content (developer/manager/executive). |

## Agents Available

Source of truth: `.claude/agents/ai-<name>.md`. Mirrors for other IDEs are generated.
The 10 first-class agents below are the dispatch surface; specialist sub-agents (reviewers, verifiers) are invoked indirectly through these.

- `ai-build` — Implementation coordinator. **The ONLY agent with code write permissions.** Test-first, dispatch-driven, quality-gated.
- `ai-explore` — Deep codebase research, architecture mapping, dependency tracing, pattern identification. **Read-only.**
- `ai-guard` — Proactive governance advisor. Checks standards, decisions, and quality trends during development. **Always advisory, NEVER blocks.**
- `ai-guide` — Project onboarding and teaching. Architecture tours, decision archaeology, knowledge transfer. **Reads everything, writes nothing.**
- `ai-plan` — Relentless interrogator. Extracts every detail, assumption, and blind spot before anything gets built.
- `ai-review` — Code review orchestrator. Dispatches specialist agents via Agent tool for real parallel review with context isolation.
- `ai-run-orchestrator` — Autonomous backlog orchestrator. Normalizes work items, plans a DAG, dispatches ai-build packets, coordinates local promotion, delivers through the PR workflow.
- `ai-simplify` — Code simplification and complexity reduction. Guard clauses, method extraction, nesting flattening, dead code removal. **Behavior preserved.**
- `ai-verify` — Evidence-first verification orchestrator. Dispatches 1 deterministic agent (tool execution) + 3 LLM judgment agents (governance, architecture, feature).
- `ai-autopilot` — Autonomous 6-phase orchestrator. Decomposes specs into sub-specs, deep-plans each with parallel agents, builds a DAG, implements in waves, runs quality convergence loops (verify+guard+review x3), and delivers via PR with full integrity report.

## Hard Rules

These are the non-negotiables. Each rule references the CONSTITUTION article that establishes it. Do NOT restate the rule prose here — that lives in CONSTITUTION.md.

- See [Article I](./CONSTITUTION.md#article-i--spec-driven-development-hard-gate) — Spec-Driven Development
- See [Article II](./CONSTITUTION.md#article-ii--test-driven-development-hard) — TDD
- See [Article III](./CONSTITUTION.md#article-iii--dual-plane-security) — Dual-Plane Security
- See [Article IV](./CONSTITUTION.md#article-iv--subscription-piggyback) — No API keys default path
- See [Article V](./CONSTITUTION.md#article-v--single-source-of-truth) — Single Source of Truth
- See [Article VI](./CONSTITUTION.md#article-vi--supply-chain-integrity) — Supply Chain
- See [Article VII](./CONSTITUTION.md#article-vii--no-suppression) — No Suppression
- See [Article VIII](./CONSTITUTION.md#article-viii--conventional-commits) — Conventional Commits
- See [Article IX](./CONSTITUTION.md#article-ix--cognitive-debt) — Telemetry
- See [Article X](./CONSTITUTION.md#article-x--right-to-evolve) — Amendment process

## Subscription Piggyback

The framework runs inside the developer's IDE host and avoids BYOK credentials in the default path
(see [Article IV](./CONSTITUTION.md#article-iv--subscription-piggyback) for the binding rules).
Three layers compose the model:

- **Layer 1 (deterministic)** — pure rules and tools, no LLM call.
- **Layer 2 (workflow)** — inference is delegated to the IDE host subscription (Claude Code, GitHub
  Copilot, Cursor, Gemini CLI), so authoring flows reuse the developer's existing entitlement.
- **Layer 3 (BYOK CI)** — opt-in for CI; the pattern is documented but not yet active at the current
  scale, and any vendor choice is a deployment-time decision captured by ADR.

## IDE-Specific Overlays

- [CLAUDE.md](./CLAUDE.md) — Claude Code specifics (hooks config, hot-path discipline)
- [GEMINI.md](./GEMINI.md) — Gemini CLI specifics (stdin/stdout JSON contract)
- [.github/copilot-instructions.md](./.github/copilot-instructions.md) — GitHub Copilot specifics
- `.codex/AGENTS.md` (if Codex requires its own — Codex auto-loads root AGENTS.md by default, see [Codex docs](https://developers.openai.com/codex/guides/agents-md))
