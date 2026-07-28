---
spec: spec-201
title: Three-Layer Open-Model Harness
status: approved
effort: large
summary: "Harden ai-engineering as the harness and loop layer for open models: admit non-Claude engines into the audit plane, populate real cost, make OpenCode a guarded reference surface, and close the loop-layer gaps only Claude Code covers today."
---

## Summary

The framework is already being driven by open models — local transcripts record 22
sessions across `xiaomi/mimo-v2.5`, `tencent/hy3`, `moonshotai/kimi-k3` and
`cohere/north-mini-code`, 10 of them inside this repository, with zero recorded tool
errors. The framework does not know it, cannot bill it, and cannot guard it.

Direct measurement against the provider on 2026-07-27 inverted the expected diagnosis.
The prompts port fine: against the real assembled always-on context (`CLAUDE.md` plus
all 54 skill descriptions, measured 9,947-10,482 prompt tokens), skill routing scored
8/8 on three of four models, and all four made a correct first tool call when handed a
real `SKILL.md` body and a bash tool. Nine desk-research findings that would have shaped
this work were refuted by probe. spec-189's content portability holds under load.

What does not hold is everything below the prompt, and it decomposes into three verified
gaps.

**Gap A — no reachable harness with a guard plane.** The provider exposes only
`/v1/chat/completions`; both `/v1/messages` and `/anthropic/v1/messages` return 404, so
Claude Code — the one harness where all 11 canonical hook events are wired — cannot
reach these models at all. Open-model execution must run on an OpenAI-shaped host, and
that is exactly where enforcement is missing. Codex wires 4 of 11 events and is missing
both `no-verify-guard` (so a commit can bypass gitleaks, format and lint) and
`injection-read-guard` (so injected `tool_response` content is never scanned). OpenCode
wires 0 of 11: its bridge `dispatch()` returns `0` unconditionally, nothing loads it, and
the one hook that could veto was mapped to the passive `permission.asked` rather than the
blocking `permission.ask`. `cursor-hook-bridge.py` dispatches to a filename that does not
exist, yet is sha-pinned so it looks enrolled. And none of this is detectable after the
fact: the `engine` field is a closed 5-value enum duplicated across two byte-twins, so
any event from a foreign host is silently refused, while `ai-eng audit verify` always
exits 0 by design.

**Gap B — the loop layer is uneven.** Nine skills dispatch subagents; only four document
an inline fallback, and three of those four contradict it elsewhere in the same file. The
five carrying no fallback include the two heaviest dispatchers. The `cost_usd` slot
exists end to end and nothing populates it, even though the provider returns per-request
cost. Concurrency resolvers have zero production callers on the dispatch path. Three
files advertise an "isolated worktree" that no code performs.

**Gap C — mirror validation is blind where it matters.** `mirror_inventory` knows four
providers while the manifest enables six; `.opencode` and `.cursor` appear in neither
provider map, so `ai-eng dev sync --check` reports clean over a rotting surface. 52 root
`.opencode` skills still carry the retired `model_tier`, and its `/ai-review` preflight
cites the wrong surface entirely.

Two live defects were reproduced while scoping this spec and are fixed here as the
cheapest end-to-end proof: `/ai-spec-draft` emits `kind=brief_drafted`, which
`ALLOWED_EVENT_KINDS` refuses, so its audit step has silently failed on every run since
the skill shipped; and both audit hash chains are broken in the live stream (events index
28333, decisions index 1) at single-writer concurrency, with no surface able to report
it.

## Goals

- A session driven by an OpenAI-compatible host emits framework events attributed to the
  correct engine, verifiable via `ai-eng audit tokens --json`.
- `cost_usd` is populated from real per-request provider cost; `genai_system` reflects
  the actual driver rather than a hardcoded literal; `session_token_rollup` events carry
  the `sessionId` the rollup requires to see them.
- `/ai-spec-draft` emits an audit event that validates, proving the enum change works end
  to end; a refused emit surfaces loudly instead of returning an unchecked boolean.
- Both live audit chain breaks are repaired, and `ai-eng audit verify` gains a path to a
  non-zero exit so chain integrity can gate rather than only inform.
- `ai-eng dev sync --check` fails on a deliberately stale repo-root mirror file — the
  mirror blind spot is closed at its root cause, not by hand-copying the orphan.
- Skill trees collapse from seven to four: `.claude/skills` (Claude Code only) and
  `.agents/skills` (every other surface), at repo root and in the template tree.
  `.codex/skills`, `.github/skills`, `.opencode/skills` and `.cursor/skills` are gone,
  and no surface loses a skill.
- Zero `model_tier` occurrences remain anywhere under `.opencode/`.
- Every collapsed surface's `_SURFACE_TREE_MAPS` entry is re-pointed at the shared tree
  in the same change that deletes its old tree, proven by an install-smoke test per
  surface — a consumer install must never end up with zero skills.
- Codex loads each skill exactly once (it currently registers all 54 twice).
- On OpenCode, a staged secret is blocked, a `--no-verify` commit is blocked, and an
  injected `tool_response` is scanned — each proven by a behavioural test, not a
  string-presence assertion.
- On Codex, `no-verify-guard` and `injection-read-guard` are wired and behaviourally
  tested, closing two documented bypasses.
- Every dispatch-only skill carries an inline fallback, asserted by a test, with zero
  contradictions between a fallback paragraph and a Boundary or Common-Mistake in the
  same file.
- `skill_lint` scans every file under `.claude/skills/` including the 58 handler files,
  evaluates `Agent` and `Task` literals, and runs as a required pre-commit check.
- A spend cap is enforced by code on the dispatch path, with a real caller.
- A per-family capability table records measured runtime quirks, replacing the four-field
  `FamilyToolProfile`.
- Judge and verifier agents no longer share the generator's model.
- Surface support tiers are declared explicitly in the documentation, including a stated
  best-effort caveat for the OpenCode guard plane.
- A cross-model replay gate runs as an advisory CI job, green on at least two provider
  models, with a recorded Claude reference result.

## Non-Goals

- **Model management.** D-189-01 stands unamended: no runtime that detects, routes,
  selects, ranks or calls a model on the operator's behalf. The capability table is
  build-time data, not a dispatcher.
- **An `ai-eng skill run` verb.** Rejected — it duplicates the harness's own skill loader
  and puts the framework into prompt assembly and tool wiring it owns none of.
- **The graph layer and the governance-plane adapter.** Both ship as separate packages
  outside this repository, following the spec-178 precedent.
- **Semantic routing via the provider's embedding and rerank models.** Recorded as
  available; deliberately not wired. Measurement shows the retrieval problem they would
  solve does not exist, and any network call on the `UserPromptSubmit` path violates the
  under-one-second hot-path budget.
- **Worktree isolation as a mechanism.** The false claim is deleted, not implemented.
- **pi.dev harness work.** No hook substrate exists there; building one is out of scope.
- **Audit chain sharding for concurrent writers.** The two live breaks are repaired and
  verification is made capable of failing; the persistence-layer redesign is deferred.
- **Anything requiring Claude Code to reach the provider.** It cannot; only
  `/v1/chat/completions` exists.
- **Removing any currently-enabled surface.** All six stay enabled.
- **Collapsing the instruction payload.** `CLAUDE.md`, `AGENTS.md` and
  `copilot-instructions.md` remain three generated copies of the same canonical payload.
  Claude Code cannot read `AGENTS.md`, and reducing `CLAUDE.md` to an import would violate
  the repository's own byte-identical mirror contract, which must be amended first.
- **Collapsing agent trees, commands, or hook configurations.** See D-201-22.

## Decisions

### D-201-01 — Scope is the in-repo layers only: audit truth, reference harness, loop hardening

The spec delivers what the source brief scopes as M0, M1 and M2. The graph layer and the
governance-plane adapter are explicitly excluded and ship separately.

**Rationale**: The brief's own scope boundary already places those two layers outside this
repository, and adding a heavy graph dependency to a wheel of stdlib-only hooks is a
dependency-footprint decision with recent precedent for harm — consumer installs have
been bricked by smaller changes. Keeping the three in-repo layers together is what makes
the seams coherent: engine identity is a precondition for attributing anything, and the
harness work is a precondition for the loop work being observable.

### D-201-02 — OpenCode is the reference open-model harness, and Codex's two guard gaps close in the same spec

M1 invests in OpenCode as the surface where the guard plane is ported and behaviourally
proven. The two missing Codex guards are wired here rather than deferred.

**Rationale**: OpenCode has the only verified headless entry (`opencode run`, confirmed
installed at 1.18.5) and a genuinely blocking plugin API — `permission.ask` with a
mutable `output.status`, plus `tool.execute.before` — which is what a guard plane needs to
exist at all. pi.dev, despite being in daily use, binds skills to its interactive TUI and
silently drops them unless a specific tool is active. Closing the Codex gaps in the same
spec is not scope creep: building a new guard plane while knowingly leaving a documented
`--no-verify` bypass live on an adjacent surface is not defensible.

### D-201-03 — Surface support is declared in two explicit tiers, and the OpenCode guarantee is best-effort

Documentation declares GUARDED surfaces (content mirrors plus an enforced hook plane) and
CONTENT-ONLY surfaces (mirrors, no enforcement). The OpenCode guard plane is documented as
best-effort, explicitly not equivalent to Claude Code.

**Rationale**: Today the manifest enables six surfaces with no stated difference between
them, which invites an inference of parity that only Claude Code earns. Claude Code hook
bytes are sha-pinned and integrity-enforced with a hard failure on mismatch; OpenCode
plugins load unsigned. Claiming equivalence without an integrity story for the plugin
itself would be an overclaim on a security boundary, and a security posture left implicit
is the failure mode this work exists to correct. Best-effort stated plainly is worth more
than equivalence implied.

### D-201-04 — Skill trees collapse to two: `.claude/skills` for Claude Code, `.agents/skills` for every other surface

All four redundant skill trees are hard-deleted at repo root and in the template tree —
`.codex/skills`, `.github/skills`, `.opencode/skills`, `.cursor/skills` — approximately
710 files. `.claude/skills` remains canonical for Claude Code; `.agents/skills` becomes
the shared tree every other surface reads. Per-surface `commands/` and `hooks/` are
unaffected, and agent trees are handled separately by D-201-23.

**Rationale**: Each host was probed directly rather than inferred from documentation. The
OpenCode 1.18.5 binary contains both `.claude/skills/` and `.agents/skills/`; the Cursor
3.12.17 bundle's discovery allowlist contains `.agents/skills/`, `.claude/skills/` and
`.codex/skills/`; Codex CLI 0.145.0 was driven live with `codex debug prompt-input` inside
this repository and reads `.agents/skills` while returning zero hits for `.claude/skills`;
GitHub's own documentation names `.github/skills`, `.claude/skills` or `.agents/skills`;
Antigravity reads `.agents/skills` natively. Claude Code is the sole surface that cannot
participate — its search paths are compiled in, with no settings key to extend them — so
it keeps its own tree. That yields exactly two trees rather than seven. The duplication was
never buying anything: all 54 files differ from canonical on every surface, but the only
differences are four provenance frontmatter keys and a rewrite of the skill's own
self-references to its local tree — a self-consistency tax that has already produced a real
bug, where `.opencode`'s `/ai-review` was rewritten to cite `.codex/agents/internal/` and
hard-stops before its fallback is consulted. Collapsing also fixes two live defects: Codex
currently registers all 54 skills twice per session because it scans both roots and does
not dedupe across them, and the `.cursor/skills` template ships 56 files with no
`handlers/` directory at all, so `/ai-build` stops at preflight for every Cursor consumer.

### D-201-05 — Every collapse re-points the installer payload map in the same change that deletes the tree

`.opencode` and `.cursor` are registered in the mirror provider maps, and each collapsed
surface's `_SURFACE_TREE_MAPS` entry is re-pointed at the shared tree in the same commit
that removes its old one. An install-smoke test per surface asserts a freshly installed
consumer repository still resolves the full skill set.

**Rationale**: The per-surface trees are installer payloads, not merely repository
duplicates — a consumer installing with `--surfaces cursor` receives `.cursor/` and nothing
else. Deleting a tree without re-pointing its payload map therefore leaves that consumer
with zero skills, silently and with no error message, in their own repository. This is the
single largest risk in the collapse and it is entirely self-inflicted rather than
IDE-related, which is exactly why the two halves must be atomic. Registering the two
missing providers is the same root-cause fix as before: the validator knew four providers
while the manifest enabled six, which is why `dev sync --check` reported clean over a
rotting surface.

### D-201-06 — The engine enum admits `openai_compatible`, and the two twins' defaults are reconciled

Both byte-twins gain the new engine value, and the conflicting defaults — one twin
defaulting to `claude_code`, the other to `unknown` — are made to agree.

**Rationale**: The closed enum is what makes every other gap undetectable: a foreign host
emits nothing, so the live stream shows zero events for three enabled surfaces. The
default disagreement is worse than the enum itself, because under a foreign harness some
events are mislabelled as Claude and accepted while others are dropped — multi-harness
attribution is impossible until they agree. This is additive: existing events keep
validating.

### D-201-07 — `brief_drafted` is added to the allowed event kinds, and refused emits surface loudly

The missing event kind is added, and a refused emit stops returning a boolean nobody
checks.

**Rationale**: `/ai-spec-draft` has instructed emitting this kind since it shipped, and the
schema has refused it every time — reproduced during scoping. It is simultaneously a real
first-party bug and the cheapest possible end-to-end proof that the enum change works. The
silent-failure mechanism matters more than the single event: the same swallowed-boolean
path is what will hide a foreign harness's telemetry, so it must become loud in the same
change that starts relying on it.

### D-201-08 — Cost attribution is completed at the producer

`cost_usd` is populated from the provider's per-request cost, `genai_system` reflects the
real driver instead of a hardcoded literal, and `session_token_rollup` events carry a
top-level `sessionId`.

**Rationale**: The schema slot already exists end to end — shaped into the genai block,
summed by the rollup, printed by the CLI — and only the producer is missing. The provider
returns per-request cost on every response, so the input is free. The two adjacent defects
ship with it because they defeat the same goal: a hardcoded system label makes every event
look Anthropic-driven regardless of harness, and a rollup that skips events lacking
`sessionId` silently drops the token data it exists to aggregate.

### D-201-09 — The audit chain breaks are repaired and `audit verify` gains a failing exit path

Both live chain breaks are repaired, and `ai-eng audit verify` gains a way to exit
non-zero, superseding the always-advisory design.

**Rationale**: This spec makes the audit plane the source of truth for cost and engine
attribution, and that plane currently has two breaks it is structurally incapable of
reporting — which is exactly how the breaks went unnoticed. A source of truth that cannot
prove its own integrity is not one. The always-exit-0 design was defensible when the plane
was purely informational; it is not once a Definition of Done depends on it. Full
concurrent-writer sharding is deliberately excluded: the goal is a plane that can fail
honestly, not a persistence redesign.

### D-201-10 — The worktree isolation claim is hard-deleted, not implemented

The phrase is removed from all three files that carry it, and the documentation describes
the isolation that actually exists: a fresh context per task plus declarative
file-boundary frontmatter.

**Rationale**: Three user-facing descriptions assert a mechanism no code performs — there
is no worktree verb and no worktree step anywhere in the execution kernel. Mechanizing it
would add a create/route/merge-back/cleanup lifecycle to the busiest path in the
framework, and the only native primitive available is vendor-specific, which would
re-couple a description that every surface mirrors to a single harness. Deletion is
honest, minimal, and portable; an unbacked claim is also the class of instruction that
degrades first on a weaker model.

### D-201-11 — A read-only skill resolver verb ships; the rulebook gains a headless carve-out

`ai-eng` gains a verb mapping a skill name to its canonical `SKILL.md` path plus handler
set. The rulebook's prohibition on synthetic terminal invocation gains an explicit
carve-out for driving a real IDE agent surface headlessly.

**Rationale**: The resolver is metadata, not execution — it sits naturally alongside the
existing `skill status` and lets a subprocess hand a skill body to whatever harness it
drives without hardcoding surface paths. The carve-out closes an ambiguity rather than
changing policy: the rulebook forbids a synthetic terminal equivalent, and driving a real
agent surface headlessly is categorically different, but nothing says so, which leaves
legitimate use out-of-contract by silence.

### D-201-12 — The capability table replaces `FamilyToolProfile`

A frozen per-family record resolved exact-id, then regex pattern, then default, carrying
the runtime quirks the four-field profile has nowhere to store.

**Rationale**: The existing profile is provably stale in both directions — it records
quirks that did not reproduce under probe, and lacks every quirk that did. The
measurements produced exactly the fields it cannot express: one model returns HTTP 200 for
a strict schema contract and then violates it, which a boolean "supports schema" flag
cannot represent; and a small completion budget against a thinking model returns empty
content rather than truncated content, a distinct failure class. Per Hard Rule 3 it is
replaced, not wrapped.

### D-201-13 — Spend caps are enforced by code with a real caller

The cap is denominated in **tokens**, follows the existing clamp idiom, and is registered
on the **PreToolUse** path so it can deny a dispatch rather than merely record one.

**Rationale**: The existing concurrency resolvers have zero production callers — their only
caller is a diagnostic — so those bounds are honoured solely by a model reading handler
prose. That is not enforcement, and it is exactly the failure a spend cap must not repeat.
Two measured constraints fix the shape. Currency is unavailable as a unit: per-request cost
exists only on the OpenAI-compatible path, so a USD cap would be absent on the surface used
most, which is barely better than prose. Tokens are present on every path. And the existing
dispatch observer fires on PostToolUse — after the dispatch has already happened — so it can
account but can never block; blocking requires a PreToolUse registration. The check must
stay cheap because PreToolUse is the sub-one-second hot path.

### D-201-14 — Inline fallbacks land for all dispatch-only skills, and self-contradictions are resolved

The five skills lacking a fallback gain one; the three files that contradict their own
fallback are corrected; a test asserts every fallback exists.

**Rationale**: Coverage is currently inverted against risk — the skills with no fallback
include the two heaviest dispatchers. Probing settled that this is a harness-primitive
gap, not a model-capability one: all four models emit parallel tool calls correctly, so any
claim that open models cannot drive fan-out is unsupported and is dropped. The fallback is
what lets a host without a subagent primitive execute the skill at all. A fallback
paragraph contradicted elsewhere in the same file is worse than none, because it gives the
model two conflicting instructions.

### D-201-15 — `skill_lint` is widened and un-blinded before it is promoted to required

The order is **fix the corpus, then widen the linter, then promote to required** — three
separate commits, in that order.

**Rationale**: Sequence is load-bearing, and the original two-step framing was wrong in a
way that would have broken the build. `required=False` does not mean advisory: the gate
runner sets pass/fail purely on the process exit code and consults `required` only when a
binary is missing, so `skill_lint` **already blocks the pre-commit gate today**. The
blocking flip is therefore the corpus widening, not the promotion. Widening first would
make the very commit that fixes the corpus impossible to land, since the gate would reject
it. Measurement confirms the size: 70 word-boundary `Agent`/`Task` occurrences across the
skill tree, 37 of them in the 58 handler files the linter cannot currently see. The
promotion itself is close to cosmetic and lands last only so the declared contract matches
the real behaviour. Widening also reverses a documented decision — those literals were
deliberately excluded as core domain vocabulary — so the exclusion list needs an explicit
suppressor for the inline-fallback idiom, or D-201-14 and D-201-15 will fight each other.

### D-201-16 — Judge and verifier agents move off the generator's model

Agents that assess work no longer share the model of the agent that produced it. This
requires a **new model axis in the agent metadata**, independent of the effort tier.

**Rationale**: Independence is currently persona-only — 15 of 19 agents declare the same
model, generator and every judge alike, which makes corroboration and adversarial
validation structurally weaker than their contracts claim. The mechanism to fix it does not
exist today: the effort-to-model map is a closed three-value mapping and the canonical
validator hard-errors when an agent's declared model disagrees with the model implied by
its effort tier, so there is no way to express "different model, same capability". The only
alternative — downgrading judges to a lower effort tier — would buy independence by making
the reviewers weaker, which is a capability regression on exactly the agents whose job is
catching what the generator missed. Adding the axis costs generator and validator surgery
but is the only option that does not trade capability for independence.

### D-201-17 — The Cursor hook bridge is repaired, not deleted

`cursor-hook-bridge.py` is fixed: `.cursor/hooks.json` is generated so the bridge can load,
the dispatch is corrected to resolve real handler filenames, and the `subagentStart` to
`SubagentStop` mis-mapping is fixed.

**Rationale**: This reverses the spec's original decision on new evidence, and the reversal
matters because the original rationale was factually wrong. The bridge was called
structurally dead; probing Cursor 3.12.17 shows it maps twelve genuine Cursor hook events
against a real hooks API. It has never fired for a different reason — no `.cursor/hooks.json`
is generated anywhere, so nothing ever loads it. That is dead-by-bug, not dead-by-design,
and deleting working event mappings because a config file was never emitted would discard
the more valuable half of the fix. Repairing it also brings a third surface into the guarded
tier rather than shrinking guard coverage.

### D-201-18 — The cross-model replay gate ships as an advisory CI job

The replay runs in CI and reports without blocking a merge, and the spec records the
data-governance posture for provider egress.

**Rationale**: A blocking gate against a third-party provider makes every merge hostage to
that provider's uptime and quota — one connection drop was already observed during probing
— and would egress source, diffs and specs automatically on every pull request. Advisory
preserves the regression signal while keeping the failure modes off the critical path, and
it can be promoted once real cost and reliability data exist. Running it in CI rather than
by hand is what stops the signal decaying to nothing. The egress posture is written down
rather than assumed, because this repository operates under a constitution with compliance
gates.

### D-201-19 — `tiktoken` ships as an optional extra, and the counter stops presenting an estimate as a measurement

`tiktoken` is added as an optional extra rather than a core dependency. When it is absent
the counter still works, but labels its output explicitly as an approximation.

**Rationale**: Adding it to core dependencies would contradict this spec's own D-201-01
rationale about wheel footprint, and for a concrete reason rather than a stylistic one:
`tiktoken` is a compiled wheel whose encoding downloads its BPE file on first use unless the
cache directory is pre-seeded, which means a network call during offline installs and
install-smoke CI, plus a new audit subtree, in a package whose hooks are deliberately
stdlib-only. The actual defect was never the missing dependency — it was that the fallback
silently degrades to a character heuristic and reports the result as a token count, so
figures that are roughly 3.6% wrong look authoritative. Labelling the estimate fixes the
dishonesty for everyone; the extra fixes the accuracy for whoever wants it.

### D-201-20 — D-189-01 is upheld unamended; the model-management question is deferred with a named trigger

No runtime that detects, routes, selects, ranks or calls a model is built. Revisiting it is
deferred until the graph layer is specced.

**Rationale**: Nothing in this spec's scope crosses that line — the capability table is
build-time data consumed at generation time, not a dispatcher. The decision only becomes
live when a per-node effort router is designed, which belongs to the out-of-scope graph
layer. Deferring with an explicit trigger is better than pre-emptively amending a standing
decision for work this spec does not do.

### D-201-21 — The remaining open decisions are deferred with named triggers, not silently dropped

The repo-boundary question for the graph layer, the approval-gate delegation model, spec
slot addressing, agent-roster contract adoption, and audit chain sharding are each recorded
as deferred with the condition that reopens them.

**Rationale**: Each is genuinely out of this spec's scope, and each would otherwise
resurface as an undocumented assumption. Naming the trigger is what distinguishes a
deferral from an omission. Spec-slot addressing in particular only becomes urgent when
concurrent workstreams exist, which this spec does not create.

### D-201-22 — Agent trees, commands and hooks do NOT collapse; only skills do

The collapse is scoped to skill trees. Per-surface agent trees, OpenCode's `commands/`, and
every hook configuration stay as they are.

**Rationale**: Each was probed and each failed the standard the skills collapse met. Hook
event vocabularies are genuinely incompatible — Claude Code's own Codex-config importer
states verbatim that hook event names differ between the two, and Cursor, Copilot and Codex
each use a different event schema, so there is nothing to share. Copilot's agent tree
carries a real transformation, rewriting Claude's tool vocabulary into VS Code tool ids;
probing proved the untranslated variants *load*, but not that the resulting tool
restriction is *honoured*, and a silently widened tool grant is a security regression rather
than a cosmetic one. OpenCode's `commands/` supplies the `/ai-<name>` slash addressability
that the headless runner depends on, and nothing proves skills can replace it. The governing
rule is that failure to prove sharing means not deleting: a wrong collapse removes an IDE
capability silently, in a consumer's repository, with no error and no way for them to notice.

### D-201-23 — Codex's `.md` agent files are removed as a namespace squat

The 19 markdown files under `.codex/agents/` are deleted rather than migrated.

**Rationale**: Live probing showed Codex discovers none of them — its agent namespace
accepts TOML only, so these files are inert. They are worse than merely unused: they occupy
a real Codex configuration namespace with content Codex will never read. The deletion must
land together with the skills collapse, because sixteen skill files name `.codex/agents/` as
a preflight path and would otherwise stop at preflight; once those skills live in the shared
tree, the generator's self-reference rewrite already resolves correctly.

## Risks

| id | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| RK-1 | A provider returns HTTP 200 on a strict schema contract it does not honour, so a success response carries invalid content | High | High | Never trust the status code. Validate client-side, re-ask once with the violation echoed, fail over to a model measured as schema-valid. Record the behaviour in the capability table and pin it with a test. |
| RK-2 | A small completion budget against a thinking model returns empty content rather than truncated content, which parses as a failure rather than a retry | High | High | Enforce a minimum completion budget at the client edge. Treat a length-terminated response with empty content as a distinct retryable class, never a parse failure. |
| RK-3 | A model fabricates a working directory in an emitted command | Medium | High | Inject the working directory explicitly into the tool contract and reject model-emitted absolute paths outside an allowlist. Treat as a small-model class failure, not a single-model quirk. |
| RK-4 | Reasoning text leaks into the message body and is billed | High | Medium | Strip reasoning fields before parsing and before replaying history; account reasoning tokens in any budget model. |
| RK-5 | The guard plane is ported onto an unsigned plugin loader, and a weaker model is more susceptible to instructions injected into the very repo content the guard reads | Medium | High | D-201-03 declares the guarantee best-effort in writing rather than letting equivalence be inferred. The behavioural tests prove the guards fire; the docs state what is not guaranteed. |
| RK-6 | Widening the linter reds a large number of currently invisible findings and blocks every PR | High | Medium | D-201-15 makes the sequence explicit: fix the corpus first, promote the gate second. |
| RK-7 | Repairing the audit chain and enabling a failing exit surfaces breaks that were previously silent, creating immediate noise | Medium | Medium | Expected and intended. Repair precedes enabling the failing path, and the failing path is opt-in at first so it can be adopted deliberately rather than landing as a surprise block. |
| RK-8 | Deleting the `.opencode/skills/` tree breaks skill discovery if native `.claude/skills` discovery is version-dependent | Low | High | Discovery was verified directly in the installed 1.18.5 binary. Acceptance requires a live OpenCode session resolving a skill after deletion, so the assumption is tested rather than trusted. |
| RK-9 | Provider intermittency — a connection drop was observed during probing | Medium | Low | Retry with exponential backoff, handled distinctly from rate limiting. Cap concurrent fan-out. Advisory CI status keeps drops off the merge path. |
| RK-10 | Scope inflation across three layers and six surfaces | High | High | The precedence ordering is the control: audit truth is a precondition for everything, and each layer has a standalone gate. The graph and governance layers are excluded outright. |
| RK-11 | Provider egress of source, diffs and specs to a third party | Medium | High | D-201-18 requires the data-governance posture — retention, tenancy, jurisdiction, model licences — to be written into the spec before any CI matrix run, and keeps the job advisory. |
| RK-12 | The mirror-map registration changes generated output across six surfaces at once, producing a very large diff | Medium | Medium | The skill collapse removes files rather than regenerating them. Generated surfaces are verified by existing parity checks, and canonical files are edited before any sync. |
| RK-13 | **A collapsed tree is deleted without re-pointing its installer payload map, leaving consumers of that surface with zero skills — silently, with no error** | Medium | High | The highest-impact risk in the spec. D-201-05 makes deletion and re-pointing atomic, and requires a per-surface install-smoke test that installs into a fresh consumer repository and asserts the full skill set resolves. No collapse merges without its test. |
| RK-14 | Native shared-tree discovery is version-dependent, so a consumer on an older IDE build loses skills after the collapse | Medium | High | Discovery was proven against specific installed builds (OpenCode 1.18.5, Cursor 3.12.17, Codex 0.145.0, Copilot CLI 1.0.71), not assumed. Record the proven floor version per surface and surface a version check in `ai-eng doctor` rather than failing silently. |
| RK-15 | `skill_lint` widening blocks the very commit that fixes the corpus, because the linter already gates pre-commit | High | High | D-201-15 fixes the ordering: corpus, then widening, then promotion, in three commits, with the widened linter verified exit-zero before it is committed. |
| RK-16 | Regenerating mirrors resurrects a just-deleted tree, because the generator's write site is still live | High | Medium | Every tree deletion removes its generator write site in the same commit. A deletion that lags its write site by even one commit is silently undone by the next sync. |

## Data Governance

RK-11 requires the provider-egress posture to be written down before any CI matrix run.
This section is that record, and it binds the advisory replay job
(`.github/workflows/cross-model-replay.yml`, D-201-18) — the only surface in this spec
that talks to a third party.

**What is sent.** Only `.ai-engineering/evals/cross-model-replay/corpus.json`: eight
committed routing questions plus the model id and a completion budget. **Source, diffs,
specs, transcripts, audit events and any other working-tree content are NOT egressed.**
The corpus is a fixture precisely so the payload is reviewable in the diff rather than
assembled at run time. The runner posts to one endpoint shape,
`POST {base}/v1/chat/completions`, and constructs its request body from the corpus file
alone — it never reads the repository.

**Retention.** Nothing is retained by this project beyond the CI run: the replay report
is a build artifact with a 14-day expiry and is never committed. Provider-side retention
is the operator's to establish before provisioning `AIENG_REPLAY_API_KEY`; the probed
endpoint is an aggregator, so the retention window is the aggregator's AND the upstream
model host's, and both must be checked. This spec makes no claim about either.

**Tenancy.** The endpoint is a shared, multi-tenant aggregator reached with a bearer
token (brief E3: `gen-`-prefixed ids carrying `provider_specific_fields` and `is_byok`).
It is not a dedicated or single-tenant deployment, and must not be treated as one.

**Jurisdiction.** Undetermined, and deliberately not guessed. The aggregator does not
declare a processing region on the response, and the upstream host is selected per
request, so the data-residency jurisdiction cannot be derived from anything measured.
An operator with a residency obligation must resolve this with the provider BEFORE
provisioning the credential — the job stays skipped until they do, which is the point of
the unprovisioned SKIP path.

**Model licences.** The replayed models are open-weight releases served through the
aggregator (`deepseek-v4-flash`, `gemma4`). Their weights carry their own upstream
licences, which govern any redistribution or fine-tuning; this spec neither
redistributes weights nor fine-tunes, so it relies on inference-only access under the
provider's terms. No model output is committed to this repository.

**Consequence.** Because none of retention, jurisdiction or upstream licence terms is
established by measurement here, the job ships advisory and unprovisioned. Provisioning
the credential is a deliberate operator act that accepts the posture above.

## Open Questions

Deferred with explicit re-entry triggers, per D-201-20 and D-201-21:

- **Model management (D-189-01).** Reopens when a per-node effort router is designed for
  the graph layer.
- **Repo boundary for the graph layer.** Reopens when the graph layer is specced; the
  default answer is a separate package.
- **Approval-gate delegation.** Which chain gates are human-only, which are delegable, and
  which are machine-attestable. Reopens when unattended execution from an external work
  item is required — today a work item arriving with no spec cannot start unattended.
- **Spec-slot addressing.** Reopens when concurrent workstreams are introduced; the single
  live slot is destroyed by a second concurrent writer.
- **Agent-role contract adoption.** Whether to adopt a richer agent frontmatter contract
  and where it lands. Reopens during loop hardening if agent-boundary defects recur.
- **Audit chain sharding for concurrent writers.** Reopens if chain breaks recur after the
  repair, or when concurrent writers are introduced.

## References

- doc: `.ai-engineering/specs/drafts/three-layer-open-model-harness-brief.md`
- doc: `.ai-engineering/specs/archive/spec-189-open-model-portability/spec.md`
- doc: `.ai-engineering/specs/archive/spec-187-fleet-simplify-portability/`
- doc: `.ai-engineering/specs/archive/spec-181-ai-pr-small-model-robustness/`
- doc: `.ai-engineering/reference/gate-policy.md`
- doc: `docs/persistence-doctrine.md`
- pr: arcasilesgroup/ai-engineering#644
