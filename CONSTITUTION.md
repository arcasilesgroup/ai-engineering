# Constitution

The identity of this project. Read it once per session, before anything else.

## Mission

`ai-engineering` is an open framework for governed agentic engineering. Its mission
is to support companies, including regulated ones, startups and individual developers.

It is intended to support human-led work and bounded autonomous orchestrators from
Solution Intent onward: discover, specify, decide, plan, implement, verify, validate,
review and audit. Its controls are guardrails that fail closed, its checks are harnesses
that execute rather than assert, and what it claims is traceable to the evidence that
proves it.

Before work, the intended framework says what may happen. During work, it reports where
it is. Afterward, it says what happened, what proves it and what may happen next.

It must expose silent harm and false green results rather than hide either one.

## Who it is for

People and organisations whose repositories matter, including those accountable for an
agent's actions. The user may be an engineer, a team, a regulated company, a startup or
an individual developer. A stranger installing the open-source wheel should be able to
understand its boundaries without knowing its authors.

## Values

- Pragmatism — Prefer the smallest control that proves the required outcome.
- Candour — Say what is unknown, incomplete or unproven without softening it.
- Collaboration — Make ownership, authority and hand-offs visible.
- Learning — Turn repeated judgement and costly discoveries into checked knowledge.

## Vocabulary

- **Guard** — A guard fails closed: if it cannot decide, nothing passes.
- **Telemetry** — Telemetry observes and never decides; it fails open and says so.
- **Solution Intent** — The user's short record of constraints, facts and intended
  outcomes.
- **The pin** — `.ai/config.toml`, which names the version governing a repository.
- **The chain** — The hash-linked record, one per repository and machine, outside the
  clone.
- **The receipt** — `machine.json`: what was written, where and at which version.
- **T0 / T1 / T2 / T3** — Server protection, git hooks, process guards, instructions
  only.
- **Proven** — Proven means a denial has actually executed on that surface.

## Authority

Commands decide deterministic facts.

Models may investigate, propose and review; they never grant authority or accept risk.

A human or an already approved versioned policy supplies authority.

`FAIL`, `INCOMPLETE` and missing authority block; prose, metadata or a reviewer's
opinion cannot override them.

## Never

- Never let a guard pass without reaching a decision.
- Never create mirrors of guards, skills, templates or policy homes.
- Never write a tilde into a config value; git and the agent surfaces do not expand it.
- Never auto-update; a change of governance is never silent.
- Never record, publish or transmit secrets, personal data or private material.
- Never claim compliance, security, accessibility or certification without direct
  evidence.
- Never claim a gate result this code did not observe.
- Never touch a user's `AGENTS.md`, `CONSTITUTION.md` or `specs/` after writing them
  once.
- Never ship a suppression comment, in our code or in advice we give.

## Escalation

When a gate blocks, read the reason, fix it or ask. Do not skip it. Only an authorized
person may accept a dated, evidenced risk. A repeated bypass is a reason to repair or
delete the control, never evidence that the control works.

## Phase

The governing specification is the sole home of phase status.

No phase is considered complete until its required evidence exists.

A roadmap, passing prose review or intended release is not production evidence.
