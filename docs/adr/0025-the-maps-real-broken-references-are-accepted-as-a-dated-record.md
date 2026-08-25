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
expires: "2026-09-25"
renewals: 0
follow_up: "a separate spec repairs the accepted references, guided by this record"
---

# 0025. The map's real broken references are accepted as a dated block

## Context

 its first
 honest run reported **42 unique real broken targets** in this tree (with `.venv`
excluded and the template holes declared): links in `CHANGELOG.md`, `docs/audit-2026-08-16.md`,
the `docs/adr/` records, and two dozen `specs/NNN-*/` records pointing at `SKILL.md`,
`DESIGN.md`, `docs/thesis.md`, `corpus.md` or a nested `specs/` path that does not exist on
disk. The instrument's whole point is that these are visible; this record accepts them as
 known debt so the gate's green is honest, and pins the exact class that must be repaired.

and the `policy/skill-map-exclusions.toml` template holes excluded). The exact set is
`policy/skill-map-accepted.toml`, the machine-readable half of this record: a reference
that is neither fixed nor in that file reddens the gate. Not accepted: any `NNN-slug`
template hole (those are declared, never accepted), and any reference that a later scan
adds — the next green must not silently include new breakage.
and the `policy/skill-map-exclusions.toml` template holes excluded). Not accepted: any
`NNN-slug` template hole (those are declared, never accepted), and any reference that a
later scan adds — the next green must not silently include new breakage.

`error: the accepted class is the class the instrument measures, repaired by a plan the
owner reads; a reference added after today is outside it and reddens the gate.`

## Decision outcome

Accept the 42 unique targets as of today, valid to **2026-09-30**, owner: repository owner. The
acceptance is a dated record, not prose: `follow_up` names the separate repair block, and
expiry means the debt is visible until it is cured or re-accepted, never silently
permanent. The repair is explicitly **not** in spec 026's block — the challenge and the
council both found the numbers move, so mixing adoption (decide to use the map) with
forty-five per-link repairs (decide each reference's true target) would ship two decisions
in one commit. This record is the boundary that says so.