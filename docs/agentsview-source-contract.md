# agentsview Source Contract

`ai-engineering` exposes one native source for viewers:

- `source`: `ai-engineering-framework-events`
- `version`: `1.0`
- `artifacts`:
  - `.ai-engineering/state/framework-events.ndjson`
  - `.ai-engineering/state/framework-capabilities.json`

## Contract

- `agentsview` is installed and launched independently by the user.
- Standard `ai-eng install` projects require no per-project viewer configuration.
- `ai-engineering` does not manage viewer lifecycle, sessions, or transcripts.
- The event stream is local-first and append-only.
- The capability catalog is replaceable and machine-readable.
- The source excludes prompts, responses, transcript bodies, and raw tool payloads.

## Intended Consumption

- Use `framework-events.ndjson` for skill, agent, context, hook, gate, governance, security, and quality activity.
- Use `framework-capabilities.json` to detect unused skills, agents, contexts, and hook kinds.
- Combine this source with `agentsview` session discovery for transcript and session-level browsing.
