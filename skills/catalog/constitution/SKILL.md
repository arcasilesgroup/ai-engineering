---
name: constitution
description: Use to maintain CONSTITUTION.md — the framework's non-negotiable rules document. Subcommands init (first-time generation), propose <article> (open ADR for amendment), audit (verify articles I-X are referenced by skills + agents). Trigger for "draft a constitution", "amend article VII", "audit constitutional coverage", "is the constitution still binding".
effort: high
tier: core
capabilities: [tool_use, structured_output]
governance:
  blocking: true
---

# /ai-constitution

Editor for `CONSTITUTION.md`. Three subcommands — `init` for first-time
generation, `propose <article>` to open an ADR for amendment, `audit`
to verify every article is actually referenced and enforced.

> **HARD GATE** — direct edits to `CONSTITUTION.md` outside this skill
> are blocked by governance. Articles I–VI require an ADR plus 14-day
> public comment period (see Article X).

## When to use

- New project — `init` to draft the constitution from a profile baseline
- Amendment proposal — `propose <article>` to open the ADR
- Quarterly audit — `audit` to verify articles aren't drifting into
  decoration
- Reorg of skills / agents — re-run `audit` to catch broken references

## Subcommands

### `init`

First-time generation. Process:

1. Detect profile (`default | regulated`) from manifest or wizard.
2. Ask 4 framing questions:
   - "Is spec-driven development non-negotiable?" (Article I)
   - "Is TDD enforced or recommended?" (Article II)
   - "Are you in a regulated industry?" (Articles III, VI)
   - "Subscription piggyback default or BYOK?" (Article IV)
3. Render `CONSTITUTION.md` from the 10-article template, parameterized
   by answers.
4. Open a PR titled `chore(constitution): initial constitution`.
5. Cross-link from `AGENTS.md` and `CLAUDE.md`.

### `propose <article>`

Amendment proposal. Process:

1. Read the current article text.
2. Interrogate the user: motivation, proposed change, who is affected,
   migration plan for existing specs.
3. Open an ADR under `docs/adr/NNNN-amend-article-<n>.md` with: status
   `Proposed`, the diff against the current article, justification,
   sunset / activation plan.
4. Articles I–VI: trigger 14-day public comment window (Article X).
   Articles VII–X: 7-day window with maintainer approval.
5. On acceptance, rewrite the article, bump minor version, emit
   `constitution.amended` telemetry.

### `audit`

Compliance check. Process:

1. Parse every article into atomic rules.
2. For each rule, search skills + agents + manifest for an explicit
   reference (file path + line).
3. Surface unreferenced rules — these are decoration, not constitution.
4. Surface skills / agents that reference an article that no longer
   exists.
5. Output: pass / partial / fail with actionable gaps.

## Process

1. **Resolve subcommand** — `init | propose | audit`.
2. **Lock writes** — direct edits to `CONSTITUTION.md` outside this
   flow trigger governance violation.
3. **Run subcommand** with idempotent semantics (audit can run repeatedly).
4. **Emit telemetry** — `constitution.initialized`, `constitution.amended`,
   `constitution.audited`.
5. **Persist outcome** to `decision-store.json` for audit trail.

## Hard rules

- NEVER edit `CONSTITUTION.md` outside `/ai-constitution propose` flow.
- Articles I–VI require ADR + 14-day public comment per Article X.
- Articles VII–X require ADR + 7-day window + maintainer approval.
- Audit must surface references with file path + line number; "I think
  it's referenced somewhere" is not an audit.
- Constitution amendments take effect at the next minor version, never
  retroactively.

## Common mistakes

- Treating `propose` as a chat — it must produce an ADR
- Skipping the 14-day comment window for Articles I–VI
- Audit that lists "compliant" without citing references
- Editing `CONSTITUTION.md` directly to "fix a typo" — even typos go
  through propose
- Forgetting to bump version on amendment merge
- Letting articles accumulate without audit — drift is invisible until
  it bites a release
