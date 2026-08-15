---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0006"
title: "Govern engineering work from intent to evidence"
date: "2026-08-13"
spec: "010"
status: "accepted"
authority_role: "repository owner"
approval_ref: "ae523990"
approved_at: "2026-08-15T03:54:12Z"
supersedes: ""
---

# 0006. Govern engineering work from intent to evidence

## Context and problem statement

The current product has a deliberately narrow and honest centre: help one person use an
agent across repositories without silent harm or false green results. Guards fail closed,
telemetry never decides and a denial must execute before a surface is called proven. Those
constraints remain the foundation.

Engineering work now also involves teams, regulated organisations, startups, individual
developers and bounded autonomous orchestrators. They need the same visible boundary from
the first statement of intent through decisions, change, review, evidence and production.
Without one mission for that journey, isolated skills and commands can expand without a
shared authority model, while an orchestrator's ability to act can be mistaken for
permission to decide.

The mission must become broader without restoring the previous control-plane sprawl or
claiming that proposed controls already prove security, compliance or production readiness.

## Considered options

1. **Keep the narrow one-person safety mission.** This is the smallest change and retains
   an honest product, but leaves teams and bounded autonomous workflows without an end-to-end
   contract for authority, outcomes and evidence.
2. **Restore the previous broad control plane.** This recovers many prompts and records
   quickly, but also restores duplicated homes, overlapping policy and unproven automation.
3. **Govern the whole engineering journey with bounded autonomy.** Preserve the proven v1
   boundaries, add only closed contracts with executable checks, and extend from Solution
   Intent through discovery, decisions, change, review, evidence and production in reviewed
   waves.

## Decision outcome

Recommend option 3.

The proposed mission is to make `ai-engineering` an open framework for governed agentic
engineering for companies, including regulated ones, startups and individual developers.
It supports human-led work and bounded autonomous orchestrators while keeping authority
separate from execution: commands decide deterministic facts; models investigate, propose
and review; a human or an already approved versioned policy authorizes decisions and risk.

Proposed decision owner: the project maintainer role. That role is accountable for keeping
the mission aligned with the Constitution and the governing specification. Naming the role
in this proposed record does not grant authority, approve this recommendation or accept
risk. A valid reviewed transition must provide separate authority evidence.

## Consequences

Better, if accepted: users get one understandable journey from intended outcome to proof,
and every new capability must state what it may read, write, execute, send and decide. The
narrow safeguards against silent harm and false green results become constraints on the
broader mission rather than features that autonomy can bypass.

Worse: a broader mission creates pressure to add abstractions, policy homes and enterprise
claims before there is a demonstrated consumer. Delivery must therefore remain wave-based,
closed-schema and evidence-led; unsupported scope is deferred rather than represented by
prompts or metadata.

Open risk: the word "governed" could be mistaken for a security or compliance guarantee.
This proposal does not claim regulatory compliance; each such claim still requires direct
evidence. A second open risk is that bounded orchestrators may be treated as authorities
because they can execute many steps. Capability checks and terminal outcomes reduce that
risk but do not accept it. While this MADR is `proposed`, it cannot be treated as acceptance
of those risks or as authority to implement beyond the separately approved plan.
