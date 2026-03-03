# Token Inventory

Detailed token counts and efficiency metrics for progressive disclosure.

## Measurement Formula

Token estimates use the approximation: **1 token ≈ 4 characters** (conservative for English text with markdown formatting).

```
skill_tokens = len(frontmatter_chars) / 4 + len(body_chars) / 4
agent_tokens = len(frontmatter_chars) / 4 + len(body_chars) / 4
```

## Budget by Loading Level

| Level | When Loaded | Budget Target |
|-------|-------------|---------------|
| **Metadata** (name + description) | Always in session | ≤ 50 tokens per skill |
| **Body** (SKILL.md content) | On-demand when invoked | ≤ 1,500 tokens per skill |
| **Resources** (scripts, references) | On-demand by AI decision | No hard limit (not in context window) |
| **Agent persona** | On-demand when activated | ≤ 500 tokens per agent |

## Session Token Budget

| Scenario | Metadata Load | On-Demand Load | Total Budget |
|----------|--------------|----------------|-------------|
| **Session start** (spec work) | ~500 tokens (CLAUDE.md compact + spec + decision-store) | 0 | ~500 |
| **Single skill invocation** | +50 (skill metadata) | +1,500 (skill body) | ~2,050 |
| **Agent activation + 2 skills** | +200 (agent + 2 skill metadata) | +2,500 (agent + skill bodies) | ~3,200 |
| **Platform audit (8 dimensions)** | +450 (9 skills metadata) | +12,000 (bodies loaded serially) | ~12,950 |

## Skills (47, flat organization)

Skills use `ai:` command prefix and flat directory layout (`skills/<name>/`).

| Skills (alphabetical) |
|-----------------------|
| a11y, agent-card, agent-lifecycle, api, arch-review, audit, changelog, cicd, cleanup, cli, code-review, commit, compliance, data-model, db, debug, deps, discover, docs, docs-audit, explain, improve, infra, install, integrity, migrate, multi-agent, ownership, perf-review, pr, prompt, refactor, release, risk, sbom, sec-deep, sec-review, simplify, skill-lifecycle, sonar, spec, standards, test-gap, test-plan, test-run, triage, work-item |

## Agents (6)

| Agent | Purpose | Scope |
|-------|---------|-------|
| plan | Orchestration, planning pipeline, dispatch, work-item sync | read-write |
| build | Implementation across all stacks (ONLY code write agent) | read-write |
| review | All reviews, security, quality, governance (individual modes) | read-write (work items only) |
| scan | Spec-vs-code gap analysis, architecture drift detection | read-write (work items only) |
| write | Documentation, changelogs, explanations | read-write (docs only) |
| triage | Auto-prioritize work items, backlog grooming | read-write (work items only) |

## Token Efficiency Score

```
efficiency = session_start_tokens / total_available_tokens
           = 500 / (48,561 + 12,825)
           = 500 / 61,386
           = 0.81% loaded at session start (99.19% deferred)
```

## Compared to Previous Model

| Metric | Before (flat loading) | After (progressive disclosure) |
|--------|----------------------|-------------------------------|
| Session start overhead | ~3,000-5,000 tokens | ~500 tokens |
| Multi-agent (3 parallel) start | ~9,000-15,000 tokens | ~1,500 tokens |
| Single skill invocation | ~3,000-5,000 + skill | ~500 + 1,550 = ~2,050 |
