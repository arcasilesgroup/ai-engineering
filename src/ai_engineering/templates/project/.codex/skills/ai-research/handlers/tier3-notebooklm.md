# Handler: Tier 3 -- NotebookLM Autonomous Deep Research

## Purpose

Run an **autonomous deep-research job** on NotebookLM that discovers its own
sources, **launched first** (at T0, in a background subagent) and **harvested
last** with a bounded wait, overlapping Tiers 0-2. NotebookLM no longer ingests
Tier 1+2 URLs -- it researches the verbatim query autonomously and returns a
deep-research report plus the sources it found. The notebook ID is captured and
embedded in the artifact so a later `--reuse-notebook=<id>` can harvest a report
that did not finish within the wait window.

Backend: `claude-world/notebooklm-skill` (`uvx --from notebooklm-skill
notebooklm-mcp`, the 13 `nlm_*` MCP tools).

## Algorithm

This handler documents the algorithm that the agent (and the lockstep helper at
`tests/integration/_ai_research_tier3_helper.py`) implements. The two stay in
sync by design (AC7).

### Inputs

- `query` (string): the user's verbatim research question.
- `timestamp_iso` (string): ISO 8601 invocation timestamp -- used in the notebook
  title hash.
- `reuse_notebook` (string|None): if provided, skip `nlm_create_notebook` and
  research/harvest against the existing notebook.
- `nlm_list`, `nlm_create_notebook`, `nlm_research`, `nlm_ask` (callables):
  tool-shaped invocation handles for the `mcp__notebooklm__nlm_*` tools. The
  helper accepts these as injected dependencies so tests can substitute mocks.
- `poll_status` (callable) + `sleep` (callable) + `clock` (zero-arg
  monotonically-increasing float) + `wait_budget_sec` (float): drive the
  bounded-wait status-poll harvest deterministically. `poll_status(notebook_id)`
  returns the research task's current status payload (there is NO real
  status-job MCP tool -- it re-polls the research status itself, D-172-05);
  `sleep(seconds)` spaces the polls with a capped back-off (D-172-08). Both are
  injected so tests can substitute deterministic recorders.

### Outputs

A `Tier3Result` containing:

- `synthesized_response` (string): optional final `nlm_ask` answer (cited).
- `report_markdown` (string): the deep-research report from `nlm_research`.
- `notebook_id` (string): preserved on timeout for a later `--reuse-notebook`.
- `sources_discovered` (list[str]): URLs NotebookLM found autonomously.
- `timed_out` (bool): True when the bounded wait was exceeded.
- `degraded` (bool): True when Tier 3 produced no usable report.
- `warnings` (list[str]): visible operator-facing notes.

### Trigger (default-on)

Implemented by `should_launch_tier3(*, notebooklm_available)`:

- NotebookLM autonomous deep research is the **DEFAULT** path: it launches
  whenever the backend is available. There is no `--depth=deep` / comparative /
  `>=10-sources` heuristic any more (the source count is unknowable at T0, when
  the background launch happens). Returns `True` whenever `notebooklm_available`.

### Notebook Naming

`ai-research/<topic-slug>-<YYYY-MM-DD>-<hash6>` where:

- `topic-slug` = `re.sub(r'[^a-z0-9]+', '-', query.lower())[:40].strip('-')`.
- `<YYYY-MM-DD>` is the first 10 chars of `timestamp_iso`.
- `hash6` = `hashlib.sha256(f"{query}|{timestamp_iso}".encode()).hexdigest()[:6]`.

Helpers `topic_slug`, `hash6`, and `notebook_title` are exported from the
lockstep module (the persist helper imports `topic_slug`).

### Launch (T0, background subagent)

Implemented by `tier3_launch(query, *, timestamp_iso, nlm_list,
nlm_create_notebook, nlm_research, reuse_notebook=None)`:

1. **Capability/auth probe (the in-subagent D-172-11 availability gate)**:
   invoke `mcp__notebooklm__nlm_list()` first (replaces the legacy `server_info`
   probe). This probe runs **INSIDE the background subagent** and is the
   availability gate -- it executes BEFORE any `nlm_create_notebook` /
   `nlm_research`, because subagent MCP-context propagation is not guaranteed
   (spec-150 Risk R2). NotebookLM is treated as **unavailable** when the probe
   raises, returns a falsy payload, or reports `{"authenticated": False}`. When
   unavailable (the `notebooklm` MCP is not loaded in the subagent's own
   context, or the session expired), the subagent **degrades at T0**:
   short-circuit the launch with `{"degraded": True, "notebook_id": "",
   "warnings": [...]}` and call NOTHING else (no `nlm_create_notebook`, no
   `nlm_research`). There is **no blocking banner** -- the degrade is a
   warning, the main agent simply proceeds on Tiers 0-2 (fail-soft D-172-09).
   The warning references the operator recovery path --
   `uvx --from notebooklm-skill notebooklm login` and
   `~/.notebooklm/storage_state.json` (D-172-06, D-172-09 fail-soft).
2. **Resolve notebook id**:
   - If `reuse_notebook` was provided -> use that string directly.
   - Else call `mcp__notebooklm__nlm_create_notebook(title=notebook_title(...))`
     and read `notebook_id` from the response.
3. **Start deep research**: call `mcp__notebooklm__nlm_research(notebook=...,
   query=..., mode="deep")` -- the autonomous deep-research job. Resolved fact
   (D-172-05): `nlm_research(mode="deep")` is **NON-blocking** -- it returns an
   immediate `status="in_progress"` ack rather than the finished report. The
   launch simply fires the job (steps 2-3 each wrapped in a bounded retry,
   D-172-08), and the harvest observes completion by **re-polling the research
   status** via the injected `poll_status` callable (there is no real status-job
   MCP tool -- the old `job_status` callable was backed by nothing). On a bounded
   retry exhaustion the launch degrades fail-soft rather than raising (D-172-09).

`tier3_launch` returns a launch dict `{"notebook_id", "degraded", "warnings"}`
handed to the harvest step.

### Harvest (bounded wait, after Tiers 0-2)

Implemented by `tier3_harvest(launch, *, poll_status, clock, wait_budget_sec,
nlm_ask=None, sleep=time.sleep)`:

1. **Degraded passthrough**: if `launch` is already degraded (NotebookLM was
   unavailable at launch), return it straight through with no polling.
2. **Bounded status poll** (D4, D-172-05): anchor the start time from `clock()`
   (a zero-arg, monotonically-increasing wall-clock reading). Repeatedly call
   `poll_status(notebook_id)` and read the **status field** (case-insensitive,
   attribute-or-`.get` alias-tolerant), branching on a terminal `ResearchStatus`:
   - `completed` -> read the deep report (alias-tolerant:
     `report_markdown` / `report` / `summary`, normalised onto
     `report_markdown`) plus the autonomously-discovered `sources` (tuple|list,
     same alias tolerance), then break.
   - `failed` / `error` -> **stop early and degrade** (`degraded=True`,
     `timed_out=False`) with a failure warning -- do NOT keep polling a dead job.
   - `[AUTH_REQUIRED]` (the sentinel in a status string OR a caught exception)
     -> **stop and degrade** with the CORRECT login warning
     (`uvx --from notebooklm-skill notebooklm login`); this is an expired Google
     session, not "still running."
   - anything else (`in_progress` / `not_found` / ...) -> keep polling.

   Between polls the loop `sleep(min(interval, cap))` with a **capped back-off**
   (default 5s, cap 60s -- see `AIENG_RESEARCH_NLM_POLL_INTERVAL_SEC`) so it
   never spins without sleeping (D-172-08; replaces the former tight
   `while True`). If `clock() - start` exceeds `wait_budget_sec` the harvest
   **times out**: return `timed_out=True`, `degraded=True`, the `notebook_id`
   **preserved**, and a warning telling the user to harvest later with
   `--reuse-notebook=<id>`. Note: NotebookLM streams sources *while* the job
   runs, so the source/artifact count is only a **WEAK secondary heuristic** --
   ONLY the status field terminates the loop, never a non-empty source list.
3. **Completion read**: covered by the `completed` branch above
   (`report_markdown` + `sources`, alias-tolerant).
4. **Optional follow-up**: if `nlm_ask` is provided, run one cited
   `mcp__notebooklm__nlm_ask(notebook=..., query=...)` after completion and put
   its `answer` in `synthesized_response`.

The default wait budget is env-tunable via `AIENG_RESEARCH_NLM_WAIT_SEC`
(default 300s, ceiling 900s); the per-poll back-off interval is env-tunable via
`AIENG_RESEARCH_NLM_POLL_INTERVAL_SEC` (default 5s, ceiling 60s). Because a
remote, auth-gated Google deep-research job is frequently slower than the
bounded wait, **timeout-then-degrade is the common outcome** -- the run
synthesizes from Tiers 0-2 and preserves `notebook_id`, and
`--reuse-notebook=<id>` is the **primary recovery UX** for retrieving the
finished report on a later invocation.

## Resilience

NotebookLM auth expiry / backend absence is the most common failure mode. The
`nlm_list` capability/auth probe in the launch step short-circuits Tier 3 with
`degraded=True` and surfaces a warning suggesting
`uvx --from notebooklm-skill notebooklm login` (auth state at
`~/.notebooklm/storage_state.json`). The synthesizer then falls back to
the Tier 0-2 corpus.

On harvest timeout (the deep job is slower than the bounded wait), the run
synthesizes without the deep report but **persists `notebook_id`** so a follow-up
`--reuse-notebook=<id>` retrieves the finished report later (D4, AC6).

## Implementation Reference

The Python lockstep implementation lives at
`tests/integration/_ai_research_tier3_helper.py`. The public API is
`Tier3Result`, `topic_slug`, `hash6`, `notebook_title`, `should_launch_tier3`,
`tier3_launch`, and `tier3_harvest`. The helper and this handler stay in sync by
design -- if either changes, the other must follow. Deterministic tests inject
the `nlm_*` callables, the `poll_status` poll, a recording `sleep`, and a fake
monotonic `clock`.

## Status

Backend swapped to `claude-world/notebooklm-skill` (13 `nlm_*` tools) with the
async launch-first / harvest-last model: background launch at T0, capability/auth
probe via `nlm_list`, bounded-wait harvest, timeout -> degrade + persist
`notebook_id`, default-on trigger (spec `notebooklm-async-tier3`, D1/D3/D4/D5/D7).
