---
spec: spec-084
title: Agentic Operations Program -- MAS+HITL Orchestration, Update UX, Shared Context Promotion, and Review/Verify Assessment Architecture
status: approved
approval: approved
effort: large
refs:
  - .ai-engineering/runbooks/
  - .github/workflows/
  - src/ai_engineering/updater/service.py
  - src/ai_engineering/cli_commands/core.py
  - src/ai_engineering/verify/service.py
  - src/ai_engineering/verify/scoring.py
  - src/ai_engineering/state/defaults.py
  - .agents/agents/ai-review.md
  - .agents/skills/review/SKILL.md
  - .agents/skills/review/handlers/review.md
  - .agents/agents/ai-verify.md
  - .agents/skills/verify/SKILL.md
  - .agents/skills/autopilot/SKILL.md
  - /Users/soydachi/repos/review-code/agents/code-review-context-explorer.md
  - /Users/soydachi/repos/review-code/agents/finding-validator.md
  - README.md
  - .ai-engineering/README.md
---

# Spec 084 - Agentic Operations Program

## Summary

`ai-engineering` already has strong building blocks for agentic delivery, but they are unevenly distributed across automation content, updater UX, ownership boundaries, and assessment flows. The current runbooks are still biased toward GitHub scheduled workflows instead of a portable MAS+HITL contract. `ai-eng update` respects ownership correctly but its preview output is still flat and low-signal for large updates. Framework-shared guidance currently leaks into `contexts/team/`. The two README files no longer explain the real generated topology, especially the extra directories introduced by skills and stateful workflows. Finally, `review` and `verify` both show the same architectural smell: a rich skill contract next to an overlapping agent wrapper, with `review` already embracing specialist fan-out and `verify` still mostly serialized and CLI-centric. This program defines an umbrella spec that decomposes the work into focused sub-specs so `ai-autopilot` can execute them as a dependency-aware multi-agent program while preserving the human approval gate at spec time.

## Goals

- Define a portable runbook layer of self-contained Markdown files that works across Codex App Automation, Claude scheduled tasks, GitHub agentic workflows, and manual operator execution without changing the MAS+HITL approval model.
- Keep human approval at the spec boundary: feature definition and spec approval remain HITL, while post-approval planning, execution, verification, and reporting become explicitly orchestrated agentic flows.
- Redesign `ai-eng update` preview output to render grouped tree-style results for created, updated, protected, unchanged, and skipped paths while preserving the current JSON contract and ownership guarantees.
- Extract framework-shared guidance out of team-owned paths so consumer projects can receive it via install/update without violating the promise that `contexts/team/**` stays user-owned.
- Refresh both `README.md` files so they accurately describe the generated `.ai-engineering/` tree, including skill-created directories, stateful artifacts, and ownership rules.
- Modernize `review` using explicit specialist subagents, adversarial finding validation, and clearer separation between the canonical skill contract and the thinner agent wrapper.
- Bring `verify` to parity with the multi-agent review philosophy by defining parallel specialist fan-out, aggregation, and evidence-backed scoring that can be reused by `dispatch` and `autopilot`.
- Produce a decomposition into independent child specs with clear dependencies so `ai-autopilot` can create child plans and execute them in parallel waves.

## Non-Goals

- Implementing the program in this spec. This document defines scope and decomposition only.
- Removing the existing spec approval gate or allowing autonomous work to begin before a human approves the umbrella spec and later the child plans.
- Allowing silent overwrite of team-managed files.
- Replacing the current ownership model with a permissive one. The boundary remains framework-managed vs team-managed vs system-managed.
- Changing the current `Notes` / `Learnings` / `Instincts` model in this initiative. That area stays as-is and is removed from this umbrella scope.
- Rewriting unrelated CLI output surfaces outside the update experience.
- Designing or implementing any `ai-eng update rebase` flow in this spec. That line is explicitly deferred.
- Creating a new agent, skill, or standalone promotion workflow just to move knowledge from team space into framework space.

## Decisions

### D-084-01: Treat this as an umbrella program with six child specs, not a monolithic change

This work spans automation contracts, updater semantics, ownership topology, documentation, review architecture, and verification orchestration. It is too broad for a single execution plan.

**Rationale**: `ai-autopilot` is explicitly designed for approved specs with 3+ independent concerns. A six-spec split keeps context bounded, allows specialist agents per stream, and reduces the risk of mixing policy, docs, and runtime changes in one branch of reasoning.

### D-084-02: The recommended operating model is MAS+HITL, with HITL only before autonomous execution

The human remains responsible for execution kickoff, but not necessarily for pre-implementation readiness marking inside the provider. Runbooks may gather context, triage work, refine or draft specs in the external work-item system, and mark an item as `ready` once their preparation checks pass. That provider-side `ready` state means the item is prepared for local intake; it does not trigger implementation automatically. The canonical local path remains manual intake into `/ai-brainstorm` -> `/ai-plan` -> `/ai-autopilot` or `/ai-dispatch`. Runbooks do not replace the local spec/plan pipeline.

**Rationale**: This preserves the local spec/plan pipeline while allowing provider-side automation to do more of the preparation work without waiting on a human to bless every refinement step. It matches the user's clarified model: runbooks can prepare and mark work as ready, but a human or local operator still decides when to pull it into the local ai-engineering execution flow.

### D-084-03: Runbooks remain the canonical portable orchestration layer

The canonical source will be self-contained Markdown runbooks, not GitHub-specific workflow wrappers. Each runbook must carry its own structured metadata, HITL rules, execution contract, and output expectations inside the same file so it can be copied as a single portable unit into multiple automation runtimes: GitHub agentic workflows, Codex App Automation, Claude scheduled tasks, and manual execution. The `runbooks/` directory itself will be reserved for this executable contract model; mixed manual-only files do not belong there.

**Rationale**: The user wants `.md` artifacts that can be copied and pasted and still carry the optimized ai-engineering behavior, while keeping the established `runbooks` name. Self-contained runbooks preserve one source of truth, minimize drift between human-readable procedure and machine-executable behavior, and make portability materially better than a split-content design.

### D-084-03a: The umbrella spec fixes the runbook contract at a high level; exact required sections belong to Child Spec A

At umbrella level, the runbook direction is already decided: self-contained Markdown, provider-native actions, portable metadata, and explicit guardrails. The exact mandatory section list and frontmatter schema should be finalized inside Child Spec A rather than expanded further here.

**Rationale**: The user explicitly indicated that the runbook contract has already been discussed enough for this umbrella spec. The remaining detail belongs in the dedicated child spec, not in more umbrella-level interrogation.

### D-084-04: Runbooks write provider-native work-item updates, not local spec artifacts

When a runbook leaves work "ready" before human approval, its output lives in the external provider, not in local `spec.md` or `plan.md`. The runbook may update the work item's title, description, comments, and provider fields. It should use the discovered board configuration from `ai-board-discover` to adapt to the client's Azure Boards or GitHub Issues setup. By default, it should populate all available ticket fields that are relevant and writable in that provider, and it should add comments describing what the runbook changed on the card. Runbooks may also create new provider-native work items when analysis surfaces reportable follow-up work, but they must obey the configured hierarchy rules from `manifest.yml`.

**Rationale**: The user wants runbooks to operate against Azure Boards or GitHub Issues as the remote preparation layer. This keeps the local ai-engineering pipeline clean: provider-native refinement first, local `/ai-brainstorm` -> `/ai-plan` -> execution only after approval.

### D-084-05: Features are read-only to runbooks; hierarchy creation is constrained by manifest policy

Runbooks may read features, but they may not create, modify, close, or otherwise mutate feature-level records. When they need to structure work beneath a feature, they may create user stories under that feature and tasks under those user stories, following the hierarchy policy configured in `manifest.yml`. The same rule applies when a runbook creates new reportable work from code analysis: it may create compatible user stories and tasks, but not mutate features directly.

**Rationale**: This preserves the top-level product planning boundary while still allowing runbooks to decompose work and capture technical findings in the provider. It also aligns the remote workflow with the explicit hierarchy model already present in `manifest.yml`.

### D-084-06: Runbooks may move provider state through the standard lifecycle using discovered board mappings

Runbooks may update the work-item state in the external provider, but only through the ai-engineering lifecycle phases and provider mappings discovered by `ai-board-discover` and executed through `ai-board-sync`. They should not hardcode board-specific state names or bypass the framework lifecycle model.

**Rationale**: The user wants runbooks to operate meaningfully in GitHub Issues or Azure Boards, not just write comments. Using the existing board discovery and sync model keeps provider-side automation adaptable to client-specific boards while preserving one canonical lifecycle vocabulary inside the framework.

### D-084-07: Provider-side `ready` must be filterable through a dedicated label/tag convention

When runbooks mark work as prepared for local intake, they should also apply a dedicated provider-native label or tag so teams can filter the backlog by agent-prepared items separately from ordinary board state. The default canonical marker is `handoff:ai-eng`.

**Rationale**: The user explicitly wants a filterable marker beyond state alone. This is especially important where board state is overloaded or where multiple teams share the same board but only some items have passed the ai-engineering preparation loop. `handoff:ai-eng` clearly signals that the item has been prepared remotely and is now ready for local ai-engineering intake.

### D-084-08: `ai-eng update rebase` is explicitly out of scope for this umbrella spec

The update UX work in this program covers preview and explainability only. Any future rebase semantics for team-managed or seed content must be handled in a separate initiative.

**Rationale**: The user explicitly descoped `ai-eng update rebase` as over-engineering for the current umbrella program. Keeping it inside this spec would add policy complexity and ownership risk without improving the immediate MAS + HITL and verify goals.

### D-084-08a: `ai-eng update` preview should use a tree view comparable to modern git apps, with ai-engineering CLI branding

The update preview should visually resemble the kind of nested file tree shown in modern git clients: grouped directories, indented hierarchy, and clear per-file status emphasis. The exact rendering should follow ai-engineering CLI brand conventions and colors rather than copying a third-party palette.

**Rationale**: The user provided a concrete reference image for the desired shape of the tree output. The requirement is not generic "better formatting"; it is a recognizable hierarchical tree with ai-engineering-specific CLI styling.

### D-084-09: Team knowledge is promoted into framework assets only when it clearly improves ai-engineering for downstream users

Knowledge currently living under `contexts/team/**` should only be promoted into framework-managed assets when, and only when, it materially improves `ai-engineering` for consumer projects. Team-owned paths remain the default home for repository-local conventions, temporary learnings, and anything that does not clearly generalize.

**Rationale**: The user does not want a bulk migration of team context into the framework. The goal is selective productization: extract only the subset that genuinely helps ai-engineering users elsewhere. This keeps the framework lean and prevents local conventions from being over-generalized into shared behavior.

### D-084-10: Promotion decisions stay human and case-by-case in this initiative

For this umbrella program, the framework should analyze the current repository state and identify candidate knowledge worth promoting, but it should not introduce a new agent, skill, or autonomous process to make those promotions. Any promotion out of team space is a human decision taken during or after this brainstorm.

**Rationale**: The user explicitly clarified that this is a one-time analytical exercise over what exists now, not a request to invent a new ongoing promotion mechanism. Keeping the decision human and case-specific avoids process bloat and keeps the work focused on the current audit.

### D-084-13: `verify` should adopt specialist fan-out with aggregation, not stay as a thin serial wrapper

`verify` will be designed as a parallel specialist orchestration surface, analogous to `review`, while still preserving evidence-first CLI-backed execution for concrete scans.

**Rationale**: The current `verify` skill promises seven modes, but the implementation is mostly four CLI-backed services with simple aggregation. Parallel specialist fan-out is the correct direction for deeper evidence gathering, especially when invoked from `dispatch` and `autopilot`.

### D-084-14: Documentation is part of the program, not cleanup after the fact

The root README and `.ai-engineering/README.md` must be updated as first-class deliverables, including the evolving `.ai-engineering/` directory topology and skill-created artifact families.

**Rationale**: The current READMEs are already stale on counts, folder names, and generated artifacts. Leaving documentation to the end would guarantee more drift while the topology changes underneath it.

### D-084-16: Provider-backed local intake must always start from the work-item reference

When work has been prepared remotely by runbooks in GitHub Issues or Azure Boards, the local intake path must start from the provider reference itself, such as `/ai-brainstorm #123` or `/ai-brainstorm AB#456`. The local flow should not detach from the originating work item.

**Rationale**: The user wants the remote preparation layer and the local ai-engineering execution layer to stay formally linked. Starting from the work-item reference preserves traceability, keeps board-sync meaningful, and avoids silent divergence between provider-native refinement and local spec materialization.

### D-084-17: `verify` should target conceptual parity with `review`, not a 1:1 clone

The goal for `verify` is not to copy `review` mechanically. It should adopt parallel specialist fan-out only where that increases signal, while preserving deterministic evidence collection as the base layer.

**Rationale**: The user chose a middle path: bring `verify` closer to the review philosophy, but avoid flattening the important distinction between evidence-driven verification and narrative multi-angle review.

### D-084-17a: `verify` should use the same profile model names as `review`, with a tighter default grouping

`verify` should expose the same profile model names as `review`: `normal` and `full`. `normal` should be implicit when no profile argument is provided, and the expensive path should be requested explicitly with `--full`. In `normal`, the full specialist surface still runs, but bundled into 2 broader fixed macro-agents with adaptive internal emphasis based on the diff and active stack. A recommended baseline split is: (1) governance + security + architecture and (2) quality + performance + a11y + feature. In `full`, `verify` dispatches one agent per specialist. Unlike `review`, `verify` must still preserve deterministic evidence collection as the foundation under both profiles.

**Rationale**: The user explicitly wants `verify` to follow the same normal-vs-full dispatch pattern as `review`, but with an even tighter default grouping to keep verification efficient while preserving evidence discipline.

### D-084-17b: `verify` should not add a separate adversarial validator stage

`verify` should stay evidence-first and aggregation-driven. It may self-challenge or de-duplicate internally, but it should not introduce a distinct `finding-validator`-style secondary agent stage the way `review` does.

**Rationale**: The user explicitly prefers to keep `verify` without a separate validator. This preserves the distinction between narrative review and deterministic verification instead of making both surfaces converge too far.

### D-084-17c: `verify normal` should still report findings by original specialist lens

Even though `verify normal` bundles execution into 2 macro-agents, the output contract should still attribute and present findings by the original specialist lenses rather than by macro-agent bucket.

**Rationale**: The user wants execution cost reduced without flattening the interpretability of the output. Specialist-level attribution keeps `verify normal` easier to reason about and closer to `verify --full`.

### D-084-17d: Specialist lenses should not be fully disabled by diff classification

For both `review` and `verify`, diff classification may reduce effort or push a lens onto a lightweight path, but it should not completely turn that lens off. Every original specialist lens should still emit either findings, a low-signal disposition, or an explicit `not applicable` outcome.

**Rationale**: This preserves the user's requirement that all specialists still run, while allowing the system to control cost when a lens clearly has little to contribute on a given diff.

### D-084-18: `review` and `verify` should keep both skill and agent, but the skill must become the canonical contract

For both assessment surfaces, the skill definition is the procedural source of truth and the agent is a thinner role wrapper used for orchestration and persona. The agent must not introduce independent modes, promises, or behavior that materially diverge from the skill and its handlers.

**Rationale**: The user explicitly hit the current confusion: `review` and `verify` each have both a skill and an agent, and the overlap makes it unclear whether they are duplicates. Keeping both artifacts preserves the existing framework shape, but making the skill canonical and the agent thinner removes ambiguity and reduces drift.

### D-084-19: `review` should adopt the structural pattern of `review-code`, not just borrow one validator idea

The target is not merely to copy the `finding-validator` concept. `review` should move toward the `review-code` shape: a canonical skill with handlers, context-loading assets, and a stable set of specialist Markdown prompts that are individually dispatchable and understandable. The current top-level review surface in ai-engineering should be refactored so each specialist has its own detailed Markdown contract, while the top-level skill remains the entrypoint and orchestration layer.

**Rationale**: The user explicitly wants the same kind of detail found in `/Users/soydachi/repos/review-code/agents` and `/Users/soydachi/repos/review-code/skills`, adapted to ai-engineering rather than reduced to one isolated pattern. The main value is the structure and clarity of the specialist prompts, not only the existence of one validator.

### D-084-20: Specialist prompts, handlers, and references are first-class architecture for `review` and `verify`

The quality of `review` and `verify` should not depend on one oversized top-level prompt. Specialist subagents, handler files, reference materials, and context-explorer patterns should be treated as first-class assets in the skill architecture wherever they improve determinism, clarity, and maintainability. For `review`, this likely means dedicated Markdown prompts per specialist comparable to `review-code/agents/**`; for `verify`, it means equivalent specialist surfaces where they add signal on top of deterministic evidence collection.

**Rationale**: The user explicitly wants strong subagents with good descriptions and a detailed Markdown structure per agent. The `review-code` inspiration repo shows the value of keeping the context-explorer and specialist prompts separate instead of hiding everything in one generic instruction blob.

### D-084-21: Adversarial validation remains part of the target `review` architecture

Within that richer `review-code`-style structure, ai-engineering should still adopt an explicit adversarial validation stage, modeled after `finding-validator`. That validation stage should run in both `review normal` and `review --full`, and it should evaluate all emitted findings rather than only a high-severity subset. The difference between profiles is the decomposition of the review agents, not whether findings are adversarially challenged at all.

**Rationale**: The user wants the validator to act as a universal anti-noise layer inside `review`, not as a selective escalation step. Once specialist reviewers become more explicit and powerful, validating every finding is the clearest way to keep trust high.

### D-084-22: `review` should have one primary orchestration handler, not a deep handler tree

The target `review` architecture should keep a single primary review handler responsible for context loading, scope classification, specialist dispatch, aggregation, and validation. The value from `review-code` to import is the specialist prompt detail and orchestration discipline, not a proliferation of top-level handlers for the main review path.

**Rationale**: The user explicitly rejected copying `handlers/review.md`, `handlers/find.md`, and `handlers/learn.md` as parallel top-level review flows. They want one core review handler that launches the right specialist Markdown prompts and synthesizes the result.

### D-084-23: `review` should gain an explicit backend specialist to mirror the existing frontend focus

Alongside `frontend`, the specialist roster should include a dedicated `backend` reviewer focused on API boundaries, service-layer behavior, persistence interactions, background processing, and server-side operational risks.

**Rationale**: The current eight-agent framing already singles out frontend concerns. The user explicitly called out the asymmetry and wants backend represented with the same clarity.

### D-084-24: `review` should support `normal` and `full` profiles

`review` should expose two operating profiles named `normal` and `full`. `normal` should be implicit when no profile argument is provided, and `--full` should be the only explicit opt-in modifier for the expensive path. Both profiles should cover the full specialist surface, but they differ in dispatch granularity. In `normal`, all specialist lenses should still run, but bundled into 3 broader fixed macro-agents to control token cost and orchestration overhead while keeping the UX predictable across mirrors. A recommended baseline split is: (1) correctness + testing + compatibility, (2) security + backend + performance, and (3) architecture + maintainability + frontend. Each macro-agent may adapt the emphasis of its internal specialist lenses based on the diff, but the top-level 3-agent shape stays stable. In `full`, each specialist gets its own dedicated agent and prompt, with richer context gathering and stronger adversarial validation. The expensive mode must be opt-in from the command surface.

**Rationale**: The user wants reviews "en condiciones" by default without silently dropping specialist coverage. A profile-based design makes the real tradeoff explicit: same review breadth, different agent decomposition and token spend.

### D-084-24a: Normal-mode macro-agent composition should be fixed in the framework, not configurable per project

The normal-mode macro-agent composition for `review` and `verify` should be framework-defined and stable across projects. `manifest.yml` should not be used to reconfigure which specialist lenses belong to which macro-agent.

**Rationale**: The user explicitly wants the grouping fixed. Making it configurable would increase drift, complicate mirrors and docs, and create another source of aspirational surface area without enough value.

### D-084-24b: `review normal` should still report findings by original specialist lens

Even though `review normal` bundles execution into 3 macro-agents, the output contract should still attribute and present findings by the original specialist lenses rather than by macro-agent bucket.

**Rationale**: The user wants execution cost reduced without collapsing the analytical clarity of the report. Specialist-level attribution keeps the output understandable and closer to `review --full`.

### D-084-25: Every approved architecture change in this program must land consistently across all platform mirrors and framework surfaces

Any work produced from this umbrella spec must update the equivalent Claude Code, GitHub Copilot, Codex, and Gemini CLI surfaces, along with any required sync/template/framework artifacts, so the framework does not drift by platform. Additions, removals, and renames should be mirrored deliberately rather than patched in one IDE flavor only.

**Rationale**: The repository explicitly treats these IDE surfaces as platform mirrors. The user does not want one platform modernized while the others keep stale instructions or outdated agent shapes.

### D-084-26: This program must remove stale, aspirational, or dead assessment surfaces instead of layering over them

When a child spec replaces a prompt, handler, mirror, template entry, or orchestration path, the old surface should be removed or rewritten across the framework rather than left behind as dead code, aspirational docs, stubs, or partially disconnected compatibility leftovers.

**Rationale**: The user explicitly does not want dead code, aspirational contracts, or stale sync/template/framework artifacts. Quality here means convergence, not accumulation.

### D-084-27: `review` should be narrowed to review only

The `review` surface should focus exclusively on producing review findings for code changes. Modes such as `find` and `learn` should not remain embedded inside the `review` skill contract once this architecture refresh lands, and they should not be preserved as separate replacement skills as part of this initiative.

**Rationale**: The user explicitly wants `review` to stay only for reviewing and chose elimination rather than splitting `find` and `learn` into standalone skills. Keeping or re-homing them would work against the simplification goal.

## Proposed Child Specs

### Child Spec A: Portable Runbook Automation Contract

- Scope: canonical self-contained runbook schema, migration of `runbooks/` to the executable contract model, provider-native pre-approval workflow behavior, runtime adapters, MAS+HITL lifecycle, approval boundary, automation host mappings.
- Primary files: `.ai-engineering/runbooks/**`, `.github/workflows/ai-eng-*.md`, automation docs, autopilot references.
- Dependency profile: independent foundation; docs depend on it.

### Child Spec B: Update Tree UX

- Scope: tree-style preview rendering inspired by modern git-app file trees, grouped change summaries, ownership-safe explainability, ai-engineering brand-consistent CLI styling, CLI/docs/tests.
- Primary files: `src/ai_engineering/updater/**`, `src/ai_engineering/cli_commands/core.py`, update tests, CLI docs.
- Dependency profile: mostly independent, but should stay aligned with ownership decisions from Child Spec C.

### Child Spec C: Shared Context Promotion and Ownership Migration

- Scope: identify framework-shared material currently trapped in `contexts/team/**`, define new framework-managed pathing, migrate loader references, update installer/update ownership maps.
- Primary files: `.ai-engineering/contexts/**`, `src/ai_engineering/state/defaults.py`, install/update logic, templates, instruction files.
- Dependency profile: foundational for Child Specs B and D.

### Child Spec D: README and Generated Topology Documentation

- Scope: refresh `README.md` and `.ai-engineering/README.md`, document skill-created folders and artifact purposes, correct counts and workflows.
- Primary files: `README.md`, `.ai-engineering/README.md`, supporting docs.
- Dependency profile: should land after Child Specs A-C-E-F stabilize the topology.

### Child Spec E: Verify Specialist Fan-Out

- Scope: redesign `verify` orchestration, parallel mode execution, `normal`/`full` profiles where default mode uses 2 fixed macro-agents with adaptive internal specialist emphasis and `full` uses one agent per specialist, evidence-first aggregation/scoring contract without a separate adversarial validator stage, output attribution by original specialist lens, integration with `dispatch` and `autopilot`, tests/docs.
- Primary files: `.agents/skills/verify/**`, `src/ai_engineering/verify/**`, CLI verify command, tests.
- Dependency profile: largely independent; docs depend on it.

### Child Spec F: Review Architecture Refresh and Adversarial Validation

- Scope: clarify `review` skill vs agent ownership, make the skill canonical, narrow the surface to review-only behavior, remove `find` and `learn` from the review area entirely, thin the agent wrapper, adapt the `review-code` structure into ai-engineering, keep one primary review handler, create or reorganize dedicated specialist Markdown prompts, add `backend` alongside `frontend`, introduce `normal`/`full` profiles where default mode uses 3 fixed macro-agents with adaptive internal specialist emphasis and `full` uses one agent per specialist, add explicit context-explorer and finding-validator stages where appropriate, and align handlers/references/tests/docs with the stronger architecture.
- Primary files: `.agents/skills/review/**`, `.agents/agents/ai-review.md`, mirrored review skill/agent surfaces under `.claude/**` and `.github/**`, supporting review docs/tests, and inspiration mapping from `/Users/soydachi/repos/review-code/agents/**`.
- Dependency profile: largely independent; can proceed in parallel with Child Spec E and should inform Child Spec D documentation.

## Dependency Plan for Autopilot

1. Child Spec C first, because ownership topology affects propagation, updater semantics, and docs.
2. Child Specs A, E, and F can proceed in parallel after C starts, because they are mostly orthogonal runtime surfaces.
3. Child Spec B can proceed in parallel with C, but its final UX wording should align with the ownership taxonomy from C and the ai-engineering CLI brand standard.
4. Child Spec D lands last, after A-B-C-E-F freeze the user-facing topology and workflows.

## Risks

- **Ownership regression**: promoting shared guidance out of team-owned paths could accidentally weaken the "never overwrite team content" contract.
  - **Mitigation**: keep ownership migration explicit, preserve deny semantics for true team-managed paths, and require migration-safe tests for allow/deny boundaries.
- **Documentation drift during execution**: if child specs land out of order, README content can become stale again mid-program.
  - Mitigation: keep docs as a dedicated closing child spec and require dependency completion before its plan is approved.
- **Noisy verify fan-out**: parallel specialist verification can create duplicate or speculative findings that reduce trust.
  - Mitigation: reuse review-style aggregation, corroboration, and evidence requirements instead of ad hoc fan-out.
- **Assessment contract drift**: if the skill and agent continue to evolve independently, users and orchestrators will not know which artifact is authoritative.
  - Mitigation: make the skill canonical, keep agents thin, and require child specs E and F to align mode names, outputs, and escalation rules.
- **Token-cost blowout**: importing the `review-code` specialist structure naively could make the default review path too expensive for routine use.
  - Mitigation: require explicit cost/depth profiles with a serious but efficient default and an opt-in full mode.
- **Mirror drift**: one IDE surface or template can remain on the old assessment model while another is modernized, causing inconsistent behavior by platform.
  - Mitigation: require every child spec to update platform mirrors, sync artifacts, and template surfaces as part of definition-of-done.
- **Weak update preview UX**: a tree view can still feel noisy or off-brand if it only dumps paths without clear hierarchy and status styling.
  - Mitigation: treat the provided reference image as the shape target, then map statuses into ai-engineering CLI brand colors and keep the hierarchy legible at a glance.
- **Automation host fragmentation**: different runtimes support different schedules, permissions, and output contracts.
  - Mitigation: define a canonical runbook contract first, then build thin adapters per host instead of letting each host become its own source of truth.
- **Migration complexity**: moving shared guidance out of `contexts/team/**` affects loaders, templates, docs, and updater behavior together.
  - Mitigation: treat ownership migration as its own child spec with phased rollout and explicit compatibility checks.

## References

- `README.md` and `.ai-engineering/README.md` currently disagree on counts, generated structure, and ownership details.
- `src/ai_engineering/updater/service.py` already enforces strong ownership boundaries and stable reason codes, making it the correct home for preview UX evolution.
- `.agents/skills/review/SKILL.md`, `.agents/skills/review/handlers/review.md`, and `.agents/agents/ai-review.md` currently overlap enough to make the canonical assessment contract unclear.
- `.agents/skills/verify/SKILL.md` is closer to the real procedural contract than `.agents/agents/ai-verify.md`, which reinforces the need for skill-canonical alignment across both assessment surfaces.
- `/Users/soydachi/repos/review-code/skills/review-code/SKILL.md` and `handlers/review.md` show the target structural pattern: entry skill, handler-driven orchestration, context assets, scripts, and specialist Markdown prompts.
- `/Users/soydachi/repos/review-code/agents/code-review-context-explorer.md` and `/Users/soydachi/repos/review-code/agents/finding-validator.md` demonstrate two especially valuable patterns worth adapting: explicit pre-review context gathering and adversarial validation of high-severity findings.
- `.agents/skills/note/SKILL.md`, `.agents/skills/learn/SKILL.md`, and `.agents/skills/instinct/SKILL.md` define three different learning systems whose storage/install story is not yet aligned.

## Open Questions
