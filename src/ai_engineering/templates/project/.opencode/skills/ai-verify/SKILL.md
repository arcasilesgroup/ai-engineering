---
name: ai-verify
description: "Use when verification with evidence is needed — not assumptions. Trigger for 'check my code', 'is this ready to merge', 'run the tests', 'is coverage good enough', 'scan for security issues', 'does this meet our standards', 'prove it works', 'is this ready to ship', 'run the release checks', 'pre-release checklist', 'GO/NO-GO'. Runs 2 specialists post-W3 (deterministic, acceptance) with `normal` implicit and `--full` explicit; the `--release` mode flag aggregates 8-dimension release readiness (coverage, security, tests, lint, dependencies, types, docs, packaging) and emits GO/CONDITIONAL GO/NO-GO. For narrative code review with human judgment, use /ai-review instead."
effort: mid
argument-hint: "claim|governance|security|quality|feature|architecture|platform|--release [version] [--full]"
model_tier: sonnet
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-verify/SKILL.md
edit_policy: generated-do-not-edit
---


# Verify

## Quick start

```
/ai-verify                      # normal: deterministic + LLM judgment
/ai-verify --full               # one agent per specialist
/ai-verify quality              # deterministic quality scan only
/ai-verify platform             # 2-specialist aggregate verdict (post-W3)
/ai-verify --release            # 8-dimension release-readiness gate (GO|CONDITIONAL GO|NO-GO)
/ai-verify --release v2.0       # tag-specific release run
```

## Workflow

Evidence before claims. Two faces: (1) a verification protocol that proves claims with commands, and (2) a specialist verification surface that aggregates deterministic evidence into merge-readiness judgments. Same principle: run the command, read the output, check the exit code. No guessing. This SKILL.md owns the user-facing contract; verifier agent files provide specialist lenses and must not redefine mode semantics.

1. **Step 0** — load stack contexts: read `.ai-engineering/manifest.yml` `providers.stacks` and apply `.ai-engineering/overrides/<stack>/conventions.md` for each stack.
2. **Dependency preflight** — verify `.codex/skills/ai-verify/handlers/verify.md` plus required `.codex/agents/verifier-*.md` files exist for the selected mode (`normal` and `--full` both require deterministic + acceptance post-W3; individual modes require only the matching specialist). STOP and report exact missing path(s) — never improvise.
3. **Run protocol** — run the IRRV protocol: per claim, identify command → run → capture output + exit code → classify CONFIRMED (exit 0 + expected) or REFUTED.
4. **Dispatch specialists** via the Agent tool (never read them inline). Output is always reported by original specialist lens.

## Dispatch threshold

Dispatch the `ai-verify` agent for any merge-readiness check, scan, or evidence-backed claim. Hand off via `Agent` tool — each specialist runs in its own context window. The agent file (`.codex/agents/ai-verify.md`) is the orchestrator handle; the procedural contract — modes, profiles, output contract — lives here.

## When to Use

- Before claiming "it works" (run the test, show the output)
- Before claiming "it's secure" (run the scan, show the findings)
- Before claiming "Done!" (verify every acceptance criterion with evidence)
- When running quality/security/governance scans on a codebase

## Specialist Roster & Modes

Spec-140 W3 collapsed the verifier roster: `verifier-governance` + `verifier-feature` merged into `verifier-acceptance`; `verifier-architecture`'s heuristics moved to `/ai-advise` (advisory non-blocking) and the standalone verifier was deleted.

| Specialist | Agent File | Lens |
| --- | --- | --- |
| `deterministic` | `verifier-deterministic.md` | Security, quality, dependencies, tests (tool-driven) |
| `acceptance` | `verifier-acceptance.md` | Spec coverage, acceptance criteria, governance compliance, ownership boundaries, gate enforcement (LLM; merged from governance + feature) |

| Mode | What runs |
| --- | --- |
| `normal` (implicit) | 2 macro-agents: deterministic first, then acceptance (single LLM macro) |
| `--full` | Same 2 specialists, dispatched explicitly in parallel after deterministic |
| `quality` / `security` | Deterministic agent only (one scan slice) |
| `acceptance` / `governance` / `feature` | Acceptance specialist only (the `governance` / `feature` aliases preserved for operator muscle memory) |
| `platform` | Aggregate verdict over deterministic + acceptance |
| `--release [version]` | 8-dimension release-readiness gate (D-127-10, absorbs the legacy `/ai-verify --release` skill). Stack-detected (Python/JS/Rust/Go); aggregates **coverage** (≥ manifest threshold), **security** (gitleaks + semgrep + pip-audit, zero crit/high), **tests** (100% pass), **lint** (zero unfixable), **dependency vulns** (zero known CVEs unless risk-accepted in `decision-store.json`), **types** (zero errors), **documentation coherence** (CHANGELOG current), **packaging integrity** (build clean). Verdict is **GO** (all PASS) / **CONDITIONAL GO** (PASS with risk acceptances) / **NO-GO** (≥1 blocker). Closure path printed for NO-GO. |

Both profiles run the same two specialists — difference is grouping (single macro vs. parallel), not coverage. Deterministic always runs first and feeds the acceptance judgment. Architecture lens runs as advisory through `/ai-advise drift` rather than as a blocking verify lens. See `handlers/verify.md` for orchestration.

## Output Contract

Every scan mode produces score / verdict (PASS/WARN/FAIL) / profile / specialist table / findings table grouped by specialist / gate check (blocker + critical thresholds).

| Mode | Blocker if… | Critical if… |
| --- | --- | --- |
| deterministic | Any secret detected, any test failure | Coverage < 80%, critical lint |
| acceptance | Spec goal missing, integrity FAIL, suppression added | Acceptance criterion unmet, compliance FAIL, count drift |
| **platform** | Any blocker in ANY mode | Score < 60 |

## Verification Checklist (before claiming DONE)

- Every acceptance criterion verified with a command
- All tests pass (exact count reported)
- Lint/format clean (zero warnings)
- No secrets in staged files
- Coverage maintained or improved (exact % reported)
- No forbidden words used in the completion report

## Common Mistakes

- Claiming success without running the command
- Assuming `--full` adds specialist coverage instead of changing decomposition
- Pretending a specialist did not run instead of reporting `not applicable`
- Ignoring warnings when exit code is 0
- Using forbidden words ("should work") instead of evidence
- Reading specialist agent files inline instead of dispatching via Agent tool

## Examples

### Example 1 — pre-merge platform sweep

User: "is this branch ready to merge?"

```
/ai-verify platform
```

Dispatches deterministic + acceptance in parallel (post-W3 the roster is 2), aggregates findings, scores against the gate, returns PASS / WARN / FAIL with evidence per finding.

### Example 2 — quality-only sweep mid-implementation

User: "before I keep going, run the quality checks"

```
/ai-verify quality
```

Runs the deterministic specialist (lint, format, type-check, tests, coverage), reports findings inline so the build loop can fix in place.

### Example 3 — release readiness gate

User: "is the v2.0 branch ready to ship?"

```
/ai-verify --release v2.0
```

Aggregates 8 dimensions, scores against manifest thresholds, emits GO / CONDITIONAL GO / NO-GO with evidence per dimension and remediation hints (D-127-10; replaces `/ai-verify --release`).

## Integration

Called by: `/ai-build` (post-task), `/ai-autopilot` (Phase 5), user directly. Dispatches: `verifier-deterministic`, `verifier-acceptance` agents (post-W3 roster of 2). Read-only: never modifies code. See also: `/ai-review` (narrative review), `/ai-advise` (advisory architecture lens), `/ai-reliability-eval` (AI reliability over time), `/ai-security` (deep CVE/SBOM only), `/ai-governance` (compliance, risk acceptance).

$ARGUMENTS
