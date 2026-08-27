---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0025"
title: "The map's real broken references are accepted as a dated block, not silently repaired"
date: "2026-08-25"
spec: "026"
status: "accepted"
authority_role: "repository owner"
approval_ref: "ae523990"
approved_at: "2026-08-25T09:15:20Z"
supersedes: ""
---

# 0025. The map's real broken references are accepted as a dated block

## Context and problem statement

Spec 026 adopts `sm` (skill-map.ai) as the reference-integrity instrument. Its first
honest run reported real broken references in this tree (with `.venv` excluded and the
template holes declared): links in `CHANGELOG.md`, `docs/audit-2026-08-16.md`, the
`docs/adr/` records, and two dozen `specs/NNN-*/` records pointing at `SKILL.md`,
`DESIGN.md`, `docs/thesis.md`, `corpus.md` or a nested `specs/` path that does not exist on
disk. The instrument's whole point is that these are visible; this record accepts them as
known debt so the gate's green is honest, and pins the exact class that must be repaired.

## Considered options

1. **Accept the broken references as a dated, expiring record.** The map's first honest
   scan found real breakage; hiding it or fixing forty-two links inside the adoption block
   would ship two decisions in one commit.
2. **Fix every link inside spec 026.** Rejected: the numbers move, the repair is a block of
   its own, and the adoption's gate green would silently include unmeasured work.

## What is accepted

The **42 unique real broken targets** `sm check --json` reports as `reference-broken`
with a non-template target, measured on this tree at 2026-08-25 (`sm scan` with
`scan.respectGitignore=true` and the `policy/skill-map-exclusions.toml` template holes
excluded). The exact set is `policy/skill-map-accepted.toml`, the machine-readable half of
this record: a reference that is neither fixed nor in that file reddens the gate.

Why 42, when the draft and the challenge said 40 then 47: the count is measured at accept
time, not taken from a document. The challenge's 47 included the `.venv` phantom copy and
duplicated citations of this very spec; the 42 are the de-duplicated, `.venv`-excluded
targets on disk. Later scans that add a target are **not** part of this acceptance and
redden the gate — the next green must not silently include new breakage. `NNN-slug`
template holes are excluded by declaration, never by acceptance.

A reference that is neither fixed nor in `policy/skill-map-accepted.toml` is real,
unaccepted breakage: the gate prints it and exits non-zero. That is the whole instrument.

## Decision outcome

Accept the 42 unique targets as of today, valid to **2026-09-30**, owner: repository
owner. The acceptance is a dated record, not prose: `follow_up` names the separate repair
block, and expiry means the debt is visible until it is cured or re-accepted, never
silently permanent. The repair is explicitly **not** in spec 026's block — the challenge
and the council both found the numbers move, so mixing adoption (decide to use the map)
with forty-two per-link repairs (decide each reference's true target) would ship two
decisions in one commit. This record is the boundary that says so.

## Consequences

The 42 accepted targets are dated and expire **2026-09-30**: until then a reference in
`policy/skill-map-accepted.toml` is honest debt, after that it reddens the gate like any
other breakage. A new broken reference outside the file was never accepted and reddens
the gate from the day it appears. The repair block this record points at (follow_up)
carries the decision on fixing each link, so the acceptance cannot outlive its record.
