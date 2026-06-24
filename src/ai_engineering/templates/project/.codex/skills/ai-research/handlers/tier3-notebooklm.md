# Handler: Tier 3 -- NotebookLM Autonomous Deep Research

## Purpose

Run an **autonomous deep-research job** on NotebookLM that discovers its own
sources **and imports them**, **launched first** (at T0, in a background
subagent) and **harvested last** with a single bounded wait, overlapping Tiers
0-2. NotebookLM no longer ingests Tier 1+2 URLs -- it researches the verbatim
query autonomously, imports the sources it finds (`--import-all`), and returns a
deep-research report. The notebook ID is captured and embedded in the artifact
so a later `--reuse-notebook=<id>` can harvest a report that did not finish
within the wait window.

Backend: the **`notebooklm-py` CLI** (operator `uv tool install
"notebooklm-py[browser]"`; resolves `notebooklm` on PATH, falling back to `uvx
--from "notebooklm-py[browser]" notebooklm`). The `[browser]` extra powers the
one-time `notebooklm login`. This supersedes the `notebooklm-skill` MCP model
(spec-175 D-175-01; supersedes D-172-05/08 -- there is no MCP `nlm_*` binding,
no re-poll, and no hand-rolled back-off any more).

## Algorithm

This handler documents the algorithm that the agent (and the lockstep helper at
`tests/integration/_ai_research_tier3_helper.py`) implements. The two stay in
sync by design (AC7).

### Inputs

- `query` (string): the user's verbatim research question.
- `timestamp_iso` (string): ISO 8601 invocation timestamp -- used in the notebook
  title hash.
- `reuse_notebook` (string|None): if provided, skip `create_notebook` and launch
  research against the existing notebook (mapped to the CLI `-n <id>`).
- `deep_timeout_sec` (int): the DETACHED deep job's own deadline, mapped to the
  CLI `--timeout` (default `AIENG_RESEARCH_NLM_DEEP_TIMEOUT_SEC`, 1800s, ceiling
  7200s). Deep research requires a real timeout (~1800s) or the `--import-all`
  step never fires.
- `doctor_probe`, `create_notebook`, `add_research`, `wait_for_job`,
  `read_result`, `ask` (callables): CLI-shaped invocation handles. The helper
  accepts these as injected dependencies so tests can substitute mocks.
- `wait_budget_sec` (float): the bounded harvest window (default
  `AIENG_RESEARCH_NLM_WAIT_SEC`, 300s, ceiling 900s) passed to `wait_for_job` as
  its `timeout`.

### Outputs

A `Tier3Result` containing:

- `synthesized_response` (string): optional final `ask` answer (cited).
- `report_markdown` (string): the deep-research report parsed from the CLI
  `--json` result.
- `notebook_id` (string): preserved on timeout for a later `--reuse-notebook`.
- `sources_discovered` (list[str]): URLs NotebookLM found + imported autonomously.
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

Implemented by `tier3_launch(query, *, timestamp_iso, doctor_probe,
create_notebook, add_research, reuse_notebook=None, deep_timeout_sec)`:

1. **Capability/auth gate (`notebooklm doctor`)**: call `doctor_probe()` first
   (runs `notebooklm doctor`; exit 0 = available -- `doctor` is purpose-built to
   check profile setup, auth status, and migration). This gate runs **INSIDE the
   background subagent** BEFORE any `create_notebook` / `add_research`, because
   subagent context propagation is not guaranteed. NotebookLM is treated as
   **unavailable** when `doctor` exits non-zero (binary absent, or the Google
   session expired). When unavailable, the subagent **degrades at T0**:
   short-circuit the launch with `{"degraded": True, "notebook_id": "", "job":
   None, "warnings": [...]}` and call NOTHING else. There is **no blocking
   banner** -- the degrade is a warning, the main agent simply proceeds on Tiers
   0-2 (fail-soft D-172-09). The warning references the operator recovery path:
   `notebooklm login`, then re-check with `notebooklm doctor` (NOT the legacy
   `notebooklm-skill` MCP login string).
2. **Resolve notebook id**:
   - If `reuse_notebook` was provided -> use that string directly (mapped to the
     CLI `-n <id>`).
   - Else call `create_notebook(title=notebook_title(...))` and read the
     `notebook_id`.
3. **Launch the detached deep+import job**: call `add_research(notebook_id,
   query, deep_timeout_sec)`, which runs the ONE CLI command

   ```
   notebooklm source add-research "<query>" -n <notebook_id> --from web \
       --mode deep --import-all --timeout <deep_timeout_sec> --json
   ```

   **DETACHED in the background** and returns an opaque job handle. This single
   command launches the job, lets the CLI wait via its own native loop, and --
   critically -- **imports the discovered sources** (`--import-all`, the step the
   MCP could not do). `--mode deep` is Deep Research; `--timeout` is the detached
   job's own deadline (deep needs ~1800s or the import never fires); `--json`
   makes the result structured (no text scraping). Because the job is detached,
   it keeps running regardless of the `/ai-research` run's lifetime.

   The canonical token list for this command is pinned by
   `build_add_research_cmd(notebook_id, query, deep_timeout_sec)` in the lockstep
   helper -- that is the authoritative command shape (`source add-research
   <query> -n <id> --from web --mode deep --import-all --timeout <N> --json`).

Steps 2-3 never raise out of `tier3_launch` (fail-soft D-175-03): a `create` or
`add_research` failure degrades and **preserves the created `notebook_id`** so a
later `--reuse-notebook` can recover.

`tier3_launch` returns a launch dict `{"notebook_id", "job", "degraded",
"warnings"}` handed to the harvest step.

### Harvest (single bounded wait, after Tiers 0-2)

Implemented by `tier3_harvest(launch, *, wait_for_job, read_result,
wait_budget_sec, ask=None)`:

1. **Degraded passthrough**: if `launch` is already degraded (NotebookLM was
   unavailable at launch), return it straight through with no wait.
2. **Single bounded wait** (D4, D-175-02): call `wait_for_job(job,
   timeout=wait_budget_sec)` ONCE -- a blocking, bounded wait on the detached
   job that **replaces the entire MCP poll loop and capped back-off**. It returns
   one terminal status:
   - `completed` -> `read_result(notebook_id)` parses the `--json` result for the
     deep report (alias-tolerant: `report_markdown` / `report` / `summary`,
     normalised onto `report_markdown`) plus the autonomously-discovered +
     imported `sources` (tuple|list, same alias tolerance).
   - `timeout` -> the detached `--import-all` job is **STILL RUNNING** (it keeps
     importing). **Do NOT kill it and do NOT read a result.** Return
     `timed_out=True`, `degraded=True`, the `notebook_id` **preserved**, and a
     warning telling the user to harvest later with `--reuse-notebook=<id>`.
   - `failed` -> **degrade** (`degraded=True`, `timed_out=False`) with a failure
     warning; the `notebook_id` is preserved.
   - `auth_required` -> **degrade** with the CORRECT login warning (`notebooklm
     login`); this is an expired Google session, not "still running."
   - any other / unrecognized / non-terminal status (`running`, `in_progress`,
     `""`, an unknown literal) -> **degrade fail-soft like `failed`**: never
     fall through to `read_result` (that would fuse a partial report); preserve
     the `notebook_id` for a later `--reuse-notebook`.
3. **Completion read**: covered by the `completed` branch above
   (`report_markdown` + `sources`, alias-tolerant via `read_result`).
4. **Optional follow-up**: if `ask` is provided, run one cited `ask(notebook_id,
   q)` after completion and put its answer in `synthesized_response`.

The bounded harvest window is env-tunable via `AIENG_RESEARCH_NLM_WAIT_SEC`
(default 300s, ceiling 900s); the DETACHED deep job's own deadline is env-tunable
via `AIENG_RESEARCH_NLM_DEEP_TIMEOUT_SEC` (default 1800s, ceiling 7200s) mapped to
the CLI `--timeout`. Because a remote, auth-gated Google deep-research job (~30 min) is
frequently slower than the bounded harvest window, **timeout-then-degrade is the
common outcome** -- the run synthesizes from Tiers 0-2 and preserves
`notebook_id`, and `--reuse-notebook=<id>` is the **primary recovery UX** for
retrieving the finished, imported report on a later invocation.

## Resilience

NotebookLM auth expiry / backend absence is the most common failure mode. The
`notebooklm doctor` capability/auth gate in the launch step short-circuits Tier 3
with `degraded=True` and surfaces a warning suggesting `notebooklm login` (then
re-check with `notebooklm doctor`). The synthesizer then falls back to the Tier
0-2 corpus.

On harvest timeout (the deep+import job is slower than the bounded wait), the run
synthesizes without the deep report but **persists `notebook_id`** and leaves the
detached `--import-all` job running, so a follow-up `--reuse-notebook=<id>`
retrieves the finished, imported report later (D4, AC6).

## Implementation Reference

The Python lockstep implementation lives at
`tests/integration/_ai_research_tier3_helper.py`. The public API is
`Tier3Result`, `topic_slug`, `hash6`, `notebook_title`, `should_launch_tier3`,
`tier3_launch`, and `tier3_harvest`. The helper and this handler stay in sync by
design -- if either changes, the other must follow. Deterministic tests inject
the `doctor_probe` gate, the `create_notebook` resolver, the `add_research`
detached launcher, the `wait_for_job` bounded wait, the `read_result` `--json`
parser, and the optional `ask` follow-up.

## Status

Backend hard-cut to the `notebooklm-py` CLI (spec-175 D-175-01) with the async
launch-first / harvest-last model: detached deep+import launch at T0 via
`source add-research --from web --mode deep --import-all --timeout <N> --json`,
capability/auth gate via `notebooklm doctor`, single bounded `wait_for_job`
harvest (no poll loop), timeout -> degrade + persist `notebook_id` (detached job
keeps importing), default-on trigger.
