---
spec: spec-173
slug: skillmap-validator-triage
title: "Skill-Map (sm) validator triage: fix review-validator color"
status: in-progress
audience: framework-dev
source_brief: .ai-engineering/specs/drafts/skillmap-validator-triage-brief.md
---

# Skill-Map (sm) validator triage: fix review-validator color

## Summary

`sm check --json` (third-party "skill-map" validator) run against an
ai-engineering install at `$HOME/repos/test` emitted ~150 findings. Triage
shows **one genuine defect**; everything else is `sm` modeling ai-engineering's
deliberate design as an error.

Owner scope decision: **fix the real defect only**; sm is a **one-off
evaluation**, so no suppression-config or CI gate.

The one real defect: the `review-validator` agent declares `color: magenta`
(`.claude/agents/review-validator.md:5`), which is off the standard Claude Code
agent palette. This spec changes it to `pink` and propagates through the mirror
pipeline. No other file changes.

Triage (standing verdicts):

| sm finding class | verdict | basis |
|---|---|---|
| `frontmatter-invalid` color (review-validator) | REAL (minor) | `magenta` off-palette; lone outlier |
| `frontmatter-invalid` effort (~46 skills) | false positive | `cheap`/`mid`/`high` is ai-eng taxonomy; sm enum is its own |
| `reference-broken` cross-folder | false positive | targets exist on disk; sm only indexes some folders |
| `reference-broken` backtick prose paths | false positive | illustrative prose parsed as links |
| `name-collision` (9 pairs) | false positive | intentional skill+agent pairs; No-Twin Axiom is skill-vs-CLI (`surface-axioms.md:28-42`) |
| `link-self-loop` / `reference-redundant` | noise | cosmetic |

## Goals

- Change `review-validator` agent `color` from `magenta` to `pink` (standard
  palette, unused by any sibling agent — no clash).
- Propagate the change canonically: edit source-of-truth, run `ai-eng dev sync`,
  confirm the `src/ai_engineering/templates/` twin carries the new value.
- Capture the triage verdicts so sm's false positives are not re-investigated.

## Non-Goals

- Renaming the `effort: cheap|mid|high` taxonomy to satisfy sm's enum.
- Restructuring or renaming the 9 skill+agent name pairs.
- "Fixing" the ~80 `reference-broken` findings (graph-scope + prose artifacts).
- Adding an `sm` config file, ignore-list, or CI gate.
- Touching `link-self-loop` / `reference-redundant` advisories.

## Decisions

### D-173-01 — Change review-validator color magenta → pink

Edit `.claude/agents/review-validator.md` `color: magenta` → `color: pink`.

**Rationale:** `pink` is in the standard Claude Code agent palette
(red/blue/green/yellow/purple/orange/pink/cyan), is the palette member visually
closest to magenta, and is unused by every sibling reviewer/verifier agent
(family uses purple/cyan/orange/red/yellow/green), so it introduces no color
clash. Smallest correct fix (§10.1 KISS).

### D-173-02 — Classify the remaining sm findings as false positives; change nothing

The effort taxonomy, the 9 name pairs, all `reference-broken` cross-folder and
backtick findings, and the self-loop/redundant advisories are left intact.

**Rationale:** each flags deliberate ai-engineering design — custom effort
taxonomy, the intentional skill(chat-entry)+agent(subagent) pairing for the 9
user-facing surfaces (CLAUDE.md §12), cross-folder canonical-chain links whose
targets exist on disk, and illustrative prose paths. Conforming would mean a
large multi-surface refactor to satisfy a third-party validator's opinions, with
real risk of fighting ai-engineering's own axioms. Not justified.

### D-173-03 — No sm config / CI gate

**Rationale:** owner is evaluating sm one-off, not adopting it as a gate.
Building a suppression-config or CI integration is unjustified investment
(YAGNI, §10.2).

### D-173-04 — Propagate via canonical edit + dev sync + template-twin parity

After editing the canonical agent file, run `ai-eng dev sync` to regenerate the
`.codex` / `.agents` / `.github` mirrors, and verify the
`src/ai_engineering/templates/` twin carries `color: pink`.

**Rationale:** mirror and template parity is a standing contract
(`scripts/sync_mirrors/core.py`); a canonical-only edit would leave fresh
installs shipping the stale `magenta` value (per the template-mirror-parity
lesson). Hard change, no shim (CONSTITUTION.md §3).

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Color edit not propagated to the install template twin → stale fresh installs | Medium | Low | D-173-04 parity check after `ai-eng dev sync`. |
| Scope creep into "make sm fully green" | Medium | Medium | Non-Goals are explicit; reject taxonomy/name-pair churn. |
| Future reader re-treats sm false positives as real bugs | Medium | Low | Triage table preserved as standing verdicts. |
| `pink` clashes with a sibling agent's color | Low | Low | Verified unused across all `.claude/agents/*.md`. |
| sm external schema unverified (research agents hit session limit) | Low | Low | Verdicts rest on direct repo evidence + sm output; sufficient for this scope. Revisit only if sm is adopted. |
