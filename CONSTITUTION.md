# Constitution

The identity of this project. Read once per session, before anything else.

## Mission

To be the small set of barriers and written procedures that let one person run a dozen
projects with an agent, without the agent doing harm silently or doing nothing silently.
Both appearances of "silently" are the product. Doing harm silently is pushing to the
default branch, leaking a key, looping, obeying text injected into a file it just read.
Doing nothing silently is reporting green while blind. A control you cannot watch fire is
not a control.

## Who it is for

Engineers who let an agent write code in repositories that matter, and the person who has
to answer for what it did. It is open source: the reader is a stranger, not the author.
Whoever runs `uv tool install ai-engineering` is the user, and they get five minutes of
patience before they leave.

## Vocabulary

- **Guard** — a hook that can deny. Fails closed. If it cannot decide, nothing passes.
- **Telemetry** — a hook that observes and never opines. Fails open, and says so.
- **The pin** — `.ai/config.toml`, which names the version that governs a repository.
- **The chain** — the hash-linked record, one per (repository, machine), outside every clone.
- **The receipt** — `machine.json`: what we wrote, where, at which version.
- **T0 / T1 / T2 / T3** — server-side protection, git hooks, process guards, instructions only.
- **Proven** — a denial has actually executed on that surface. Documented is not proven.

## Never

- Never let a guard exit zero without having reached a decision.
- Never copy a guard, a skill or a template into somebody else's repository.
- Never write a tilde into a config value; git and the agent surfaces do not expand it.
- Never claim a gate result this code did not observe.
- Never auto-update. A change of governance is never silent.
- Never touch a user's `AGENTS.md`, `CONSTITUTION.md` or `specs/` after writing them once.
- Never ship a suppression comment, in our code or in advice we give.

## Compliance gates

None imposed on us. What we produce for others is: dated risk acceptances with a named
owner, an ADR trail, and a tamper-evident chain anchored into git history. A buyer whose
auditor requires cryptographically signed policy artifacts is told plainly that v1 does
not have that.

## Escalation

When a gate blocks: read the reason, fix it, or ask. Never skip it. A bypass is a person's
act at a keyboard, it is recorded by name, and a guard bypassed three times is a guard to
fix or to delete.

## Phase

Production. v1.0.0 is the first release a stranger installs, and the acceptance suite in
§11 is the bar it had to clear.
