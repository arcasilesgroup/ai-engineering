---
spec: spec-172
slug: ai-research-tavily-tier3-reliability
title: "ai-research: Tavily web provider + NotebookLM Tier-3 reliability"
status: in-progress
effort: medium
summary: Add Tavily as primary Tier-2 web provider in /ai-research (Tavily → Exa → built-in, one bounded fall-through), and fix NotebookLM Tier-3 so it completes reliably — real completion signal, correct login command, matching permissions, back-off/retry. Tier-3 stays fail-soft.
---

# spec-172 — ai-research: Tavily web provider + NotebookLM Tier-3 reliability

## Summary

`/ai-research` runs a 4-tier escalation (Tier 0 local → Tier 1 free MCPs →
Tier 2 web → Tier 3 NotebookLM autonomous deep research). Two problems, one
combined spec, two workstreams.

**Workstream A — Tavily.** Tier 2 (web) today is a *hard single-selection*:
Exa primary, built-in `WebSearch`/`WebFetch` fallback, with the selection
decided once up front and an explicit constraint that "the failure of one
provider's call never falls through to the other"
(`handlers/tier2-web.md:106`). The operator installed Tavily (`tavily-remote-mcp`,
HTTP `https://mcp.tavily.com/mcp/`) and wants it used by `/ai-research`. Tavily
is currently scoped only to a different repo (`arcamusic`); there are zero
Tavily references in `ai-engineering`. This workstream wires Tavily as the
**primary** Tier-2 web provider (Tavily → Exa → built-in) and upgrades the
hard-selection into a chain with one bounded fall-through.

**Workstream B — NotebookLM reliability.** Tier 3 "works sometimes" because of
concrete bugs, not bad luck. The root cause: `nlm_research(mode="deep")` is
**non-blocking** (returns an immediate async ack), but the harvest loop polls
`job_status(notebook_id)` — a callable that maps to **no real MCP tool**, so the
agent can never observe completion and times out at the 900s ceiling with 0
sources bound (ground truth: `runtime/research/local-llm-runtimes-ide-azure-2026-06-04.md:152-154`).
Compounding it: a 404 login command baked in and pinned in tests, an MCP
permissions allowlist that doesn't match the real tool names, a tight `while
True` poll with no back-off, no retry/terminal-status handling, and an
unverified background-subagent MCP context. The operator chose to **fix the
bugs and keep the fail-soft posture** (NLM problems degrade, never block the
run; Tiers 0-2 always return).

The repo stays the single source of truth; no provider-registry abstraction is
introduced — wiring follows the existing handler-prose + lockstep-Python-helper
pattern.

## Goals

- Tavily is the **default** Tier-2 web provider: `/ai-research` uses
  `mcp__tavily__*` when connected, falling back to Exa, then built-in
  `WebSearch`/`WebFetch`, by capability detection.
- The web tier survives a primary-provider **empty or error** result via
  exactly one bounded fall-through to the next available provider (recorded as
  degraded), instead of dead-ending.
- NotebookLM Tier-3 **completes deterministically** when the service is
  available and authenticated: a real MCP-backed completion signal replaces the
  phantom `job_status` poll — no more systematic 900s-timeout-with-0-sources.
- Every NotebookLM recovery hint points to the **working** login command
  (`uvx --from notebooklm-skill notebooklm login`).
- The NotebookLM permissions allowlist matches the **real** tool names
  (`mcp__notebooklm__*`) in both local and template configs.
- The harvest loop is back-off-bounded, retried, and exits early on a terminal
  failure status (no busy-loop, no poll-forever-on-dead-job).
- Fail-soft preserved: NLM degradation never blocks; the degrade warning is the
  user-visible signal and now carries the correct recovery command.
- All lockstep helpers, tests, and template mirrors are updated in lockstep; the
  full `tests/integration` ai-research suite plus `tests/unit/docs` are green.

## Non-Goals

- **Not** making Tier-3 blocking/mandatory — fail-soft posture is kept
  (operator choice). No top-of-output blocking banner.
- **Not** parallel-merging web providers — one active provider plus one bounded
  fall-through, not Exa+Tavily run together every call.
- **No** generic provider-registry or `manifest.yml` provider keys — keep the
  handler-prose + lockstep-helper pattern (YAGNI).
- **Not** installing/connecting the Tavily MCP on the operator's behalf — the
  operator connects it per-repo; this spec wires the skill + permissions only.
- **Not** changing the citation/synthesis contract
  (`handlers/synthesize-with-citations.md`).
- **Not** closing spec-150's lifecycle record (it stays `draft`) — noted as
  separate hygiene follow-up, out of scope here.

## Decisions

### D-172-01 — Tier-2 web provider order: Tavily → Exa → built-in

Tier 2 selects the first available of: Tavily (`mcp__tavily__*`), then Exa
(`mcp__exa__*`), then the Claude Code built-in `WebSearch`/`WebFetch`.
Selection is capability-detected via the existing shared `is_available` guard.

**Rationale**: The operator installed Tavily and explicitly chose it as the
default web provider with Exa as fallback; Exa is retained as a proven
secondary and the built-in remains the zero-config last resort. This reuses the
established capability-detection pattern rather than inventing config surface.

### D-172-02 — One bounded fall-through on empty/error

If the selected provider **raises** OR returns **zero results**, fall through to
the next available provider exactly once, recording the skipped provider in
`degraded_sources`. This supersedes the current hard-selection constraint
("failure of one provider's call never falls through", `tier2-web.md:106`).

**Rationale**: Directly targets the "a veces sí, a veces no" complaint — a
dead-end on a single provider's transient failure or empty result is a primary
flakiness source. Bounding it to one fall-through caps the added latency/cost.

### D-172-03 — Tavily wired via MCP search + extract tools, canonical server name

Tavily is wired through its MCP search + extract tools, capability-detected like
Exa. The canonical MCP server name is standardized to `tavily`, yielding tool
references `mcp__tavily__tavily_search` and `mcp__tavily__tavily_extract`. Exact
tool names and signatures are confirmed against the Tavily MCP docs during
`/ai-plan`.

**Rationale**: The skill cites exact `mcp__…` tool names, so a stable server
name is required. The operator's current install uses the key
`tavily-remote-mcp` in another repo; standardizing on `tavily` gives the skill
a stable reference and the operator a documented install convention.

### D-172-04 — Permissions allowlist + template wiring, no manifest registry

Add a `mcp__tavily__*` entry to the ai-engineering project allowlist and the
installer template (`src/ai_engineering/templates/project/.claude/settings.json`).
No `manifest.yml` provider keys are added.

**Rationale**: The permissions allowlist must cover the tool names the skill
calls — the NotebookLM permissions bug (D-172-07) proves an allowlist mismatch
silently blocks tools. A provider-registry abstraction is unjustified for three
web providers (YAGNI).

### D-172-05 — Replace the phantom `job_status` with a real completion signal

Remove the unbacked `job_status(notebook_id)` callable. Detect Tier-3
completion with a real MCP tool: poll `nlm_list_sources` / `nlm_list_artifacts`
(sources/artifacts bound ⇒ job complete) with back-off, or adopt
`nlm_research_pipeline` if it provides a blocking end-to-end result. The exact
tool is finalized in `/ai-plan` against the NotebookLM MCP docs.

**Rationale**: This is the single biggest reliability fix.
`nlm_research(mode="deep")` is non-blocking, and the harvest polled a callable
backed by no real tool, so the job's completion was never observable — every
run drained the full wait budget and bound 0 sources.

### D-172-06 — Correct the NotebookLM login command everywhere

Replace the 404 `uvx notebooklm login` with
`uvx --from notebooklm-skill notebooklm login` in the handler prose, the
lockstep helper warning, and the four test files that pin the wrong string.

**Rationale**: The fail-soft recovery hint currently sends users to a 404, so
re-authentication — the documented recovery path — cannot succeed. A working
command is required for fail-soft to actually recover.

### D-172-07 — Align NotebookLM permissions to the real tool names

Set the allowlist to the real `mcp__notebooklm__*` tools (`nlm_list`,
`nlm_create_notebook`, `nlm_research`, `nlm_ask`, `nlm_list_sources`,
`nlm_list_artifacts`) in both `.claude/settings.local.json` and the template
`settings.json`; drop the wrong `mcp__notebooklm-mcp__*` prefix and the
list-only local entry.

**Rationale**: The local allowlist permits only `nlm_list`; the template ships
the wrong `notebooklm-mcp` prefix. Either mismatch silently blocks
`create_notebook`/`research`, which is a top cause of "works on one machine,
not another."

### D-172-08 — Harvest-loop hardening: back-off, retry, terminal-status branch

Replace the tight `while True` with a back-off + max-poll cap; wrap
`nlm_create_notebook`/`nlm_research` in try/except with bounded retry; add a
non-`completed` terminal-status branch (`failed`/`error` ⇒ stop early and
degrade) instead of polling until timeout.

**Rationale**: The busy-loop risks MCP rate-limits and context blowup; the
missing retry leaves an empty `notebook_id` that breaks harvest; the missing
terminal branch wastes the entire wait budget polling a dead job.

### D-172-09 — Keep Tier-3 fail-soft (no blocking)

NotebookLM degradation never blocks the run; Tiers 0-2 always return their
result. The degrade warning remains the user-visible signal, now carrying the
correct recovery command.

**Rationale**: The operator explicitly chose "fix the bugs, keep fail-soft"
over loud-blocking. Partial research beats no research when a remote,
auth-gated Google service is unavailable.

### D-172-10 — Lockstep parity is mandatory

Every handler change mirrors into its `tests/integration/_ai_research_*_helper.py`
twin and the installer template mirror; tests are updated in lockstep —
especially the four files pinning the wrong login command.

**Rationale**: The tier2/tier3 handlers have lockstep Python mirrors (AC7); the
template is copied verbatim by the installer. Skipping a mirror ships features
that are absent or broken in consumer installs.

### D-172-11 — Verify NotebookLM MCP availability inside the background subagent

Before launch, the background subagent verifies the `notebooklm` MCP is loaded
in its own context; if not, it degrades at launch instead of producing an empty
`notebook_id` that breaks harvest.

**Rationale**: Subagent MCP-context propagation is not guaranteed (spec-150
Risk R2). An unguarded launch yields undefined harvest behavior.

## Risks

- **R1 (med) — Tavily MCP server-name variance across installs.** Different
  installs may register the server under a different key, breaking the
  `mcp__tavily__*` references. *Mitigation:* canonical name `tavily` +
  capability-detect + fail-soft degrade; document the install convention.
- **R2 (med) — NLM completion-signal assumption.** Sources/artifacts may bind
  late or under unexpected field keys, so polling could still miss completion.
  *Mitigation:* poll both `nlm_list_sources` and `nlm_list_artifacts`,
  alias-tolerant field reads, back-off + cap, degrade on timeout.
- **R3 (low) — Tier-2 fall-through latency/cost.** A failing primary adds a
  second provider round-trip. *Mitigation:* bounded to exactly one
  fall-through; record degraded.
- **R4 (low) — Test/parity drift.** Four test files pin the wrong login command;
  lockstep helper + template parity gates apply. *Mitigation:* D10 lockstep
  update; run the full tier2/tier3 + resilience suites and `tests/unit/docs`
  before PR.
- **R5 (med) — Subagent MCP propagation remains environment-dependent.**
  *Mitigation:* D11 pre-launch verify + degrade.
- **R6 (low) — Tavily not connected in ai-engineering, so it can't be
  dogfooded without an operator install.** *Mitigation:* document install; wire
  the repo + template config (D-172-04) so a one-time connect enables it.

## Open Questions (resolved in /ai-plan)

- **OQ1** — Exact NotebookLM completion-signal mechanism: poll
  `nlm_list_sources`/`nlm_list_artifacts` vs. adopt `nlm_research_pipeline`.
  Resolve against the NotebookLM MCP tool docs.
- **OQ2** — Exact Tavily MCP tool names/signatures (`tavily_search`,
  `tavily_extract`, and whether extract/crawl is needed for single-URL fetch)
  and the confirmed canonical server name. Resolve against the Tavily MCP docs.
