---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0007"
title: "Make the CLI outcome-first and exact"
date: "2026-08-13"
spec: "010"
status: "accepted"
authority_role: "repository owner"
approval_ref: "ae523990"
approved_at: "2026-08-15T03:54:12Z"
supersedes: ""
---

# 0007. Make the CLI outcome-first and exact

## Context and problem statement

The command line is the deterministic boundary between a requested operation and the
evidence that says what happened. Today its names and outputs reflect several older
contracts: decisions use an ADR spelling, exception work is called a plan, the local
digest is a top-level verb and each command explains completion differently. A person can
usually infer the result, but an orchestrator cannot safely infer authority, evidence or
the next permitted action from prose.

Adding aliases or translating outputs at each caller would preserve ambiguity. It would
also let source checkouts and installed wheels disagree while both appeared usable. The
contract needs one vocabulary, one terminal outcome and one closed machine representation.

## Considered options

1. **Keep every current spelling and add optional JSON.** Existing callers keep working,
   but aliases become a permanent second contract and optional fields still require
   consumers to guess what absence means.
2. **Create a second automation CLI beside the human CLI.** This separates presentation,
   but duplicates commands, mutations and error semantics; one path will eventually lag.
3. **Hard-rename the existing CLI and share one outcome across renderers.** Keep one set of
   deterministic verbs, reject obsolete spellings, and render the same result as human,
   plain or closed JSON output.

## Decision outcome

Recommend option 3.

The canonical verbs are `init`, `doctor`, `update`, `spec`, `decide`, `accept`, `audit`,
`report`, `exception` and `uninstall`. Rename `--adr` to `--madr`, `plan` to `exception`,
and `digest` to `report digest`. No old spelling remains as an alias. Invalid CLI use exits
2 without writing state; a missing alias is not recovered by abbreviation or hidden
dispatch.

Before mutation, human output names reads, writes and network use. The terminal result
names one canonical outcome, its evidence, remaining work and the next permitted action.
`--json` writes exactly one JSON object with the closed v1 fields required by Spec 010,
without prompts, ANSI or surrounding prose. Human, plain and JSON renderers carry the same
semantic result and exit status.

A hard rename is complete only when exact positive and negative checks execute from both
the source checkout and installed wheel: the new spelling performs the intended operation,
the old spelling and abbreviations return exit 2, and neither rejected invocation writes
state. Output-transition checks compare outcome, exit code and required JSON fields rather
than accepting a help label as proof. This evidence must be fresh for the candidate commit;
this record is not evidence that the transition ran.

## Consequences

Better, if accepted: people and orchestrators share one documented interface, every
terminal state has a stable meaning, and removal of an old name is mechanically visible.
The project maintains one command path instead of compatibility branches.

Worse: scripts using an old spelling break immediately and must be deliberately migrated.
The closed JSON envelope adds work to every verb before the CLI can claim parity, and the
installed-artifact checks make packaging defects block the transition.

Open risk: users may read `report digest` as permission to transmit a report, even though
P0 permits only a local privacy-safe digest. Another open risk is that JSON summaries may
accidentally expose repository paths or private material unless negative fixtures inspect
the actual bytes. No risk is accepted by this record: its approval fields approve the decision and nothing
else, and grant no authority to publish, preserve an alias or weaken a blocking outcome.
