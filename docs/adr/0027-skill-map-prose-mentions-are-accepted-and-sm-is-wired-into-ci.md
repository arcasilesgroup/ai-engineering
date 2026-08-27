---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0027"
title: "The map's prose mentions are accepted, and skill-map is wired into CI"
date: "2026-08-25"
spec: "026"
status: "accepted"
authority_role: "repository owner"
approval_ref: "ae523990"
approved_at: "2026-08-26T01:43:47Z"
supersedes: ""
---

# 0027. The map's prose mentions are accepted, and skill-map is wired into CI

## Context and problem statement

ADR 0025 accepted the map's first real broken references and made `just map` the
reference-integrity instrument of the governed tree. Two things completed since then make
that instrument a gap rather than a habit:

1. **Specs 027 and 028 landed, carrying new mentions** the analyzer reads as broken
   references. They are prose: a dossier about `SKILL.md` and `corpus.md` necessarily names
   those files as the standard it is about, a challenge quotes a live ADR listing verbatim,
   and an ADR body says the standard's own file shape. None is a broken link to a file that
   does not exist; each is a mention of a concept or a verbatim transcript. Because specs 027
   and 028 are approved at exact digests (ADR 0026), rewriting their prose to satisfy the
   analyzer would falsify the record. The honest move is to accept the mentions, the same
   way ADR 0025 accepted the earlier class.
2. **The instrument was never wired into CI.** The runner is a stranger install, so the
   `map` recipe prints "map not exercised; sm missing" and stays green. The check ran only on
   the maintainer's machine. This record also installs `sm` on the runner so the gate is
   real everywhere, in the same spirit gitleaks and trivy are installed: a reference-integrity
   check that only the person who wrote the change ever runs is a check that does not gate.

## Considered options

1. **Wire the instrument and accept the residual prose class with a date.** `sm` installed
   and gating means every future mention is counted; the 19 existing ones are real, named
   and expire.
2. **Leave `sm` to local runs and prose mentions uncounted.** Rejected: the map then gates
   nothing in CI, and the class it found keeps growing invisibly.

## What is fixed

Three mentions pointed at a file that exists elsewhere, and were corrected rather than
accepted (they are not `policy/skill-map-accepted.toml` entries):

- `CHANGELOG.md`'s `blocked.md` now names `specs/028-writer-model-recorded/blocked.md`.
- Two `ai-build/SKILL.md` mentions in specs 028 (`spec.md`, `challenge.md`) now name the
  real `.agents/skills/ai-build/SKILL.md`.

## What is accepted

**26 (node, target) pairs**, all prose mentions or verbatim transcripts, added to
`policy/skill-map-accepted.toml` (measured by `sm check --json` at accept time, non-template,
`.venv`-excluded, `scan.respectGitignore=true`):

- **7 from this record itself** — `SKILL.md`, `corpus.md`, `ai-build/SKILL.md`, `blocked.md`,
  `challenge.md`, `spec.md` and `testing.md`, named here while describing the class this
  record accepts, exactly as ADR 0025 accepted the same pattern for its own body.
- **16 from `specs/027-standard-skills-contract/`** — `SKILL.md`, `corpus.md`, and sibling

- **16 from `specs/027-standard-skills-contract/`** — `SKILL.md`, `corpus.md`, and sibling
  `ai-*/corpus.md` / `testing.md` as the subject of the standard the spec is about. Approved
  at exact digests (ADR 0026); the prose is not rewritten.
- **2 from `docs/adr/0026-specification-027-and-its-plan-are-approved-at-exact-digests.md`** —
  `SKILL.md` and `corpus.md` named as the file shape the standard governs.
- **1 from `specs/028-writer-model-recorded/challenge.md`** — a verbatim ADR listing whose
  last line names `0026-specification-027-and-its-plan-are-approved-at-exact-digests.md`, a
  real file that lives elsewhere in the tree (`docs/adr/`), quoted as command output.

## What the instrument now does

- **The runner carries `sm`.** `check.yml` installs Node 24 (pinned via SHA256) and
  `@skill-map/cli@1.12.2` (pinned via its npm `dist.integrity`), so `just check` runs `map`
  on the runner instead of printing "sm missing". `sm` is added to `PINNED_ENGINES`, so the
  two sides of the gate can no longer drift: the version pin must match between the Justfile
  and the workflow, the same way it does for gitleaks, trivy, semgrep and mypy.
- **Machine-local drafts stay out of the map.** `sm` does not honour nested `.gitignore`
  files, so a local-only, gitignored `*.md` under `.ai/reports/` was scanned and reddened
  the local gate. `scan.ignore` in `.skill-map/settings.json` excludes `.ai/reports/*.md`;
  those files exist only on a developer's machine, never in a CI checkout, so the exclusion
  is inert on the runner and only stops a maintainer's local scratch from faking breakage.

## Decision outcome

Accept the 19 prose mentions as a dated class valid to **2026-09-30**, owner: repository
owner, and wire `sm` into CI so the reference-integrity check actually gates. The
acceptance is a dated record, not silence: `follow_up` names the real repair blocks (specs
027/028), and expiry makes this class visible until those blocks close or it is
re-accepted. A reference that is neither fixed nor in `policy/skill-map-accepted.toml`
still reddens the gate — the instrument's honesty rule from ADR 0025 is unchanged.

## Consequences

The 19 accepted prose mentions are dated and expire **2026-09-30**; after that the same
links redden the gate unless the follow-up blocks closed them. `sm` runs in `just check`
on the runner, so a new prose mention or a broken reference shows up in the commit that
introduced it, not in somebody else's audit months later.
