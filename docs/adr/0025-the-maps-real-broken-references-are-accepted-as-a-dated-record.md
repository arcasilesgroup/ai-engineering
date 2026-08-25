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
accepted: "2026-08-25"
expires: "2026-09-30"
renewals: 0
follow_up: "a separate spec repairs the accepted references, guided by this record"
---

# 0025. The map's real broken references are accepted as a dated block

## Context

Spec 026 adopts `sm` (skill-map.ai) as the reference-integrity instrument. Its first
honest run reported real broken references in this tree (with `.venv` excluded and the
template holes declared): links in `CHANGELOG.md`, `docs/audit-2026-08-16.md`, the
`docs/adr/` records, and two dozen `specs/NNN-*/` records pointing at `SKILL.md`,
`DESIGN.md`, `docs/thesis.md`, `corpus.md` or a nested `specs/` path that does not exist on
disk. The instrument's whole point is that these are visible; this record accepts them as
known debt so the gate's green is honest, and pins the exact class that must be repaired.

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