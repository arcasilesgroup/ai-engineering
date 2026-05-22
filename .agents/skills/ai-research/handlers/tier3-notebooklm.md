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
- `job_status` (callable) + `clock` (zero-arg monotonically-increasing float) +
  `wait_budget_sec` (float): drive the bounded-wait harvest deterministically.

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

1. **Capability/auth probe**: invoke `mcp__notebooklm__nlm_list()` first
   (replaces the legacy `server_info` probe). NotebookLM is treated as
   **unavailable** when the probe raises, returns a falsy payload, or reports
   `{"authenticated": False}`. When unavailable, short-circuit the launch with
   `{"degraded": True, "notebook_id": "", "warnings": [...]}` and call NOTHING
   else (no `nlm_create_notebook`, no `nlm_research`). The warning references the
   operator recovery path -- `uvx notebooklm login` and
   `~/.notebooklm/storage_state.json` (D7 fail-soft).
2. **Resolve notebook id**:
   - If `reuse_notebook` was provided -> use that string directly.
   - Else call `mcp__notebooklm__nlm_create_notebook(title=notebook_title(...))`
     and read `notebook_id` from the response.
3. **Start deep research**: call `mcp__notebooklm__nlm_research(notebook=...,
   query=..., mode="deep")` -- the autonomous deep-research job. Per D1/OQ2 this
   is assumed **BLOCKING** (the background subagent holds the call while the main
   agent runs Tiers 0-2); a future non-blocking job handle is supported because
   the harvest reads job state via the injected `job_status` callable rather than
   this return value.

`tier3_launch` returns a launch dict `{"notebook_id", "degraded", "warnings"}`
handed to the harvest step.

### Harvest (bounded wait, after Tiers 0-2)

Implemented by `tier3_harvest(launch, *, job_status, clock, wait_budget_sec,
nlm_ask=None)`:

1. **Degraded passthrough**: if `launch` is already degraded (NotebookLM was
   unavailable at launch), return it straight through with no polling.
2. **Bounded poll** (D4): take the start time from `clock()` (a zero-arg,
   monotonically-increasing wall-clock reading). Repeatedly call
   `job_status(notebook_id)`. On each iteration, if the elapsed time
   (`clock() - start`) exceeds `wait_budget_sec`, the harvest **times out**:
   return `timed_out=True`, `degraded=True`, the `notebook_id` **preserved**, and
   a warning telling the user to harvest later with `--reuse-notebook=<id>`. No
   report is produced in this branch.
3. **Completion**: when `job_status` reports `{"status": "completed"}`, read the
   deep report from `report_markdown` (or `report` -- backend field-name
   variance, normalised onto `report_markdown`) and the autonomously-discovered
   `sources`.
4. **Optional follow-up**: if `nlm_ask` is provided, run one cited
   `mcp__notebooklm__nlm_ask(notebook=..., query=...)` after completion and put
   its `answer` in `synthesized_response`.

The default wait budget is env-tunable via `AIENG_RESEARCH_NLM_WAIT_SEC`
(default 300s, ceiling 900s).

## Resilience

NotebookLM auth expiry / backend absence is the most common failure mode. The
`nlm_list` capability/auth probe in the launch step short-circuits Tier 3 with
`degraded=True` and surfaces a warning suggesting `uvx notebooklm login` (auth
state at `~/.notebooklm/storage_state.json`). The synthesizer then falls back to
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
the `nlm_*` callables, the `job_status` poll, and a fake monotonic `clock`.

## Status

Backend swapped to `claude-world/notebooklm-skill` (13 `nlm_*` tools) with the
async launch-first / harvest-last model: background launch at T0, capability/auth
probe via `nlm_list`, bounded-wait harvest, timeout -> degrade + persist
`notebook_id`, default-on trigger (spec `notebooklm-async-tier3`, D1/D3/D4/D5/D7).
