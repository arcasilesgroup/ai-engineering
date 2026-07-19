---
name: ai-verify
description: "Verifies claims with evidence, not assumptions: runs deterministic + acceptance specialists post-W3 (`normal` implicit, `--full` explicit), plus a `--release` mode aggregating 8-dimension release readiness (coverage, security, tests, lint, dependencies, types, docs, packaging) into a GO/CONDITIONAL GO/NO-GO verdict. Trigger for 'check my code', 'is this ready to merge', 'run the tests', 'is coverage good enough', 'scan for security issues', 'prove it works', 'pre-release checklist', 'GO/NO-GO'. Not for narrative code review with human judgment; use /ai-review instead."
effort: mid
argument-hint: "claim|governance|security|quality|feature|architecture|platform|--release [version] [--full]"
---

# Verify

Verifies merge-readiness claims with evidence instead of assumptions, dispatching deterministic and acceptance specialists over changed files. Use it to check code, prove tests pass, scan for security issues, or run the 8-dimension `--release` GO/NO-GO gate.

## Quick start

```
/ai-verify                      # normal: deterministic + acceptance (LLM)
/ai-verify --full               # one agent per specialist
/ai-verify quality              # deterministic quality scan only
/ai-verify platform             # 2-specialist aggregate verdict (post-W3)
/ai-verify --release [version]  # 8-dimension release gate (GO|CONDITIONAL GO|NO-GO)
```

## Workflow

Principles applied: §10.5 TDD (tests and gates ARE the evidence — run the command, read the exit code, never assume). Evidence before claims. This SKILL.md owns the user-facing contract; verifier agent files provide specialist lenses and must not redefine mode semantics.

1. **Step 0 — load contexts** — read `.ai-engineering/manifest.yml` `providers.stacks`; apply `.ai-engineering/overrides/<stack>/conventions.md` per stack.
2. **Dependency preflight** — verify `handlers/verify.md` plus the `.claude/agents/verifier-*.md` files the selected mode needs exist (`normal`/`--full` need deterministic + acceptance; single modes need only their specialist). STOP and report the exact missing path — never improvise.
3. **Run IRRV protocol** — per claim: identify command -> run -> capture output + exit code -> classify CONFIRMED (exit 0 + expected) or REFUTED.
4. **Dispatch specialists** via the Agent tool (never read inline). Report every finding by its original specialist lens.

## Dispatch threshold

Dispatch the `ai-verify` agent for any merge-readiness check, scan, or evidence-backed claim over ≥ 1 changed file. Each specialist runs in its own context window via the Agent tool. `.claude/agents/ai-verify.md` is the orchestrator handle; the procedural contract lives here.

## Specialist Roster (post-W3: 2)

Spec-140 W3: `verifier-governance` + `verifier-feature` merged into `verifier-acceptance`; `verifier-architecture` heuristics moved to `/ai-advise` (advisory) and the standalone verifier deleted.

| Specialist | Agent File | Lens |
| --- | --- | --- |
| `deterministic` | `verifier-deterministic.md` | Security, quality, dependencies, tests (tool-driven; always runs first) |
| `acceptance` | `verifier-acceptance.md` | Spec coverage, acceptance criteria, governance compliance, ownership boundaries, gate enforcement (LLM) |

## Modes

| Mode | What runs |
| --- | --- |
| `normal` (implicit) | deterministic, then acceptance (single LLM macro) |
| `--full` | same 2 specialists, dispatched in parallel after deterministic |
| `quality` / `security` | deterministic agent only (one scan slice) |
| `acceptance` / `governance` / `feature` | acceptance specialist only (`governance`/`feature` aliases preserved for muscle memory) |
| `platform` | aggregate verdict over deterministic + acceptance |
| `--release [version]` | 8-dimension release-readiness gate (D-127-10). Stack-detected (Python/JS/Rust/Go); aggregates **coverage** (≥ manifest threshold), **security** (gitleaks + semgrep + pip-audit, zero crit/high), **tests** (100% pass), **lint** (zero unfixable), **dependency vulns** (zero CVEs unless risk-accepted in `decision-store.json`), **types** (zero errors), **documentation coherence** (CHANGELOG current), **packaging integrity** (build clean). Verdict **GO** (all PASS) / **CONDITIONAL GO** (PASS with risk acceptances) / **NO-GO** (>= 1 blocker). Closure path printed for NO-GO. |

Both profiles run the same two specialists — grouping differs (single macro vs. parallel), not coverage. Deterministic always runs first and feeds the acceptance judgment. See `handlers/verify.md` for orchestration.

## Output Contract

Every scan mode emits: score / verdict (PASS/WARN/FAIL) / profile / specialist table / findings grouped by specialist / gate check.

| Mode | Blocker if… | Critical if… |
| --- | --- | --- |
| deterministic | Any secret detected, any test failure | Coverage < 80%, critical lint |
| acceptance | Spec goal missing, integrity FAIL, suppression added | Acceptance criterion unmet, compliance FAIL, count drift |
| platform | Any blocker in ANY mode | Score < 60 |

## Verification Checklist (before claiming DONE)

- [ ] Every acceptance criterion verified with a command.
- [ ] All tests pass (exact count reported).
- [ ] Lint/format clean (zero warnings).
- [ ] No secrets in staged files.
- [ ] Coverage maintained or improved (exact % reported).
- [ ] No forbidden words ("should work") in the completion report.

## Common Mistakes

- Assuming `--full` adds specialist coverage instead of changing decomposition.
- Reporting a specialist as skipped instead of `not applicable`.
- Ignoring warnings when the exit code is 0.
- Reading specialist agent files inline instead of dispatching via the Agent tool.

## Examples

### Example — pre-merge platform sweep

User: "is this branch ready to merge?"

```
/ai-verify platform
```

Dispatches deterministic + acceptance in parallel (post-W3 roster of 2), aggregates findings, scores against the gate, returns PASS / WARN / FAIL with evidence per finding.

## Integration

Called by: `/ai-build` (post-task), `/ai-autopilot` (Phase 5), user directly. Dispatches: `verifier-deterministic`, `verifier-acceptance` agents. Read-only: never modifies code. See also: `/ai-review` (narrative review), `/ai-advise` (advisory architecture lens), `/ai-reliability-eval`, `/ai-security` (deep CVE/SBOM only), `/ai-governance` (compliance, risk acceptance).

Inline fallback: Agent-tool dispatch is the primary path. On a harness with no subagent/Agent-tool primitive, execute this skill by reading the needed `.claude/agents/verifier-*.md` specialist file(s) and running their steps inline, in-context, sequentially — inline-sequential is the floor, not the default.

$ARGUMENTS
