---
spec: spec-175
slug: tier3-notebooklm-cli-migration
title: "ai-research Tier-3 NotebookLM CLI migration"
status: in-progress
audience: framework-dev
summary: >-
  Hard-cut /ai-research Tier 3 from the NotebookLM MCP to the notebooklm-py
  CLI. Deep research now launches + natively waits + IMPORTS discovered
  sources in one command (`source add-research --mode deep --import-all
  --timeout 1800`) — the import step the MCP could not do. Detached-background
  launch + bounded harvest + --reuse-notebook fallback; capability/auth gated
  by `notebooklm doctor`. Supersedes the MCP re-poll (D-172-05). Tier 0/1/2,
  citation contract, and async-first overlap unchanged.
---

# ai-research Tier-3 NotebookLM CLI migration

## Summary

Today `/ai-research` Tier 3 binds NotebookLM through the MCP
(`mcp__notebooklm__nlm_list/create_notebook/research/ask`, backend
`notebooklm-skill`). The MCP `nlm_research(mode=deep)` does start+poll and
returns the report, but it has **no native status job** (the handler re-polls
the research status itself — D-172-05) and, critically, it **does not import**
the sources the deep-research job discovers (the NotebookLM "Importar" step). It
also caps the wait too low for deep, which prevents the import from firing.

This spec **hard-cuts Tier 3 to the `notebooklm-py` CLI**. Deep research launches,
waits natively, AND imports the discovered sources in ONE command:

```
notebooklm source add-research "<query>" -n <notebook> --from web --mode deep --import-all --timeout 1800
```

`--import-all` automates the import the MCP could not do; `--mode deep` is Deep
Research; `--timeout 1800` is required for deep (the old ~300s cap left the
import unfired). The CLI's native wait removes the hand-rolled re-poll
(D-172-05). The long job runs **detached in the background** at T0; the
`/ai-research` run harvests within a bounded window and, on timeout, degrades and
persists `notebook_id` so `--reuse-notebook=<id>` recovers the finished,
imported report later. Tier 0/1/2, the citation / 3-directions contract, and the
async-first overlap design are unchanged.

## Goals

- Tier 3 invokes the `notebooklm-py` CLI (no `mcp__notebooklm__nlm_*` tools).
- Deep research uses `source add-research --from web --mode deep --import-all
  --timeout <N>`: launch + native wait + **import discovered sources**.
- The deep+import job runs detached in the background at T0; the run harvests
  within `AIENG_RESEARCH_NLM_WAIT_SEC`, fusing the report when ready and
  otherwise degrading + persisting `notebook_id` for `--reuse-notebook`.
- Capability + auth gate via `notebooklm doctor` (exit 0 = available; non-zero →
  Tier 3 degraded/skipped, fail-soft, never raises).
- The deep job's own deadline is a tunable (`AIENG_RESEARCH_NLM_DEEP_TIMEOUT_SEC`,
  default 1800) mapped to the CLI `--timeout`.
- `--reuse-notebook=<id>` preserved (mapped to the CLI `-n <id>`).
- Handler, lockstep helper, tests, SKILL.md, manifest tunables, and mirrors kept
  in sync.

## Non-Goals

- No change to Tier 0 (local), Tier 1 (free MCPs), or Tier 2 (the parked
  spec-174 Tavily+Exa fan-out).
- No new NotebookLM artifact types (audio / video / slides / quiz / mind-map) —
  only the deep-research report + source import.
- No MCP fallback retained — hard-cut, no shim (CONSTITUTION §3).
- No change to the citation contract, the `## Recommended Directions` 3-direction
  output, or the async-first launch-first/harvest-last overlap design.
- No change to whether the operator keeps the NotebookLM MCP server registered
  globally — this spec only stops ai-research from binding it.

## Decisions

### D-175-01 — Hard-cut Tier 3 to the notebooklm-py CLI

Remove every `mcp__notebooklm__nlm_*` binding from the Tier 3 handler and helper;
Tier 3 drives the `notebooklm-py` CLI via subprocess. Invocation resolves a
`notebooklm` on PATH (operator `uv tool install "notebooklm-py[browser]"`) and
falls back to `uvx --from "notebooklm-py[browser]" notebooklm`.

**Rationale:** the CLI is a strict superset of the MCP (everything the MCP does +
import + timeout control + detached runs); a single path is simpler and removes
the fragile MCP re-poll. No shim (§3). The `[browser]` extra is needed for the
one-time browser login.

### D-175-02 — Deep research = one CLI command (launch + native wait + import-all)

Tier 3 deep research runs `notebooklm source add-research "<query>" -n
<notebook> --from web --mode deep --import-all --timeout <N>`, which launches the
job, waits via the CLI's native loop, and imports the discovered sources.

**Rationale:** `--import-all` is the capability the MCP lacked (its
`nlm_research` only start+poll'd, never imported). Native wait removes the
hand-rolled status re-poll (supersedes D-172-05). Deep requires a real
`--timeout` (~1800s) or the import never fires.

### D-175-03 — Detached background launch + bounded harvest + reuse fallback

The deep+import command is launched **detached** at T0 with its own
`--timeout = AIENG_RESEARCH_NLM_DEEP_TIMEOUT_SEC` (default 1800) so the import
completes regardless of the run's lifetime. `/ai-research` harvests within
`AIENG_RESEARCH_NLM_WAIT_SEC`: if the job finished, fuse the report + imported
sources into synthesis; if not, degrade gracefully and persist `notebook_id` so a
later `--reuse-notebook=<id>` harvests the now-finished, imported report.

**Rationale:** deep takes ~30 min; blocking a research run that long is
unacceptable. Detached + bounded harvest + reuse keeps `/ai-research` responsive
while guaranteeing the import always completes — matching the existing
async-first overlap and the timeout/degrade pattern.

### D-175-04 — Capability + auth gate via `notebooklm doctor`

Tier 3 availability is probed with `notebooklm doctor` (purpose-built: checks
profile setup, auth status, migration). Exit 0 → available; any non-zero or
missing binary → Tier 3 is recorded degraded and skipped, never raising.

**Rationale:** `doctor` is the most accurate single auth+setup gate, catching an
expired browser session so Tier 3 degrades cleanly instead of failing mid-run.
Replaces the `nlm_list` MCP probe.

### D-175-05 — Lockstep rewrite + tunable changes

Rewrite `_ai_research_tier3_helper.py` (callable injection → a CLI
command-builder + subprocess-output parser), its tests, `tier3-notebooklm.md`,
the SKILL.md Tier-3 lines, and the manifest/`CLAUDE.md` tunables (add
`AIENG_RESEARCH_NLM_DEEP_TIMEOUT_SEC`; retire the MCP re-poll interval now that
wait is native), then propagate mirrors via `ai-eng dev sync`.

**Rationale:** the handler↔helper 1:1 parity and the mirror/template parity are
standing contracts; the invocation-model change touches all of them and they
must move together.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| CLI not installed / `uvx` offline on a consumer machine | Medium | Medium | `doctor` gate + PATH→uvx fallback; fail-soft degrade to skip (existing Tier-3 pattern). |
| Subprocess text-output parsing is more brittle than MCP structured returns | Medium | Medium | Prefer a `--json`/`--quiet` output mode if the CLI offers one (resolve exact flags at plan time via `--help`); pin parsing in the lockstep helper + tests. |
| ~30-min detached job lifecycle on consumer machines | Medium | Low | Detached bg + bounded harvest + `--reuse-notebook` recovery; never blocks the run. |
| Expired browser auth (`~/.notebooklm` session) | Medium | Low | `doctor` detects → degrade clean; operator re-runs `notebooklm login`. |
| Large helper (20.8K) + test (36.5K) rewrite drift | Medium | Medium | TDD RED→GREEN; handler↔helper parity; full Tier-3 suite green before merge. |
| Losing the parked spec-174 (Tier-2 fan-out) while reusing the single slot | Low | Medium | spec-174 parked at `.ai-engineering/specs/parked/spec-174-tier2-fanout/`; restore after this ships. |
