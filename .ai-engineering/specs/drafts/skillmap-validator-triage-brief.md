---
title: "Skill-Map (sm) Validator Triage and Real-Defect Fix"
status: draft
audience: framework-dev
branch: chore/skillmap-validator-triage
length_estimate: small
authoring_style: diagnostic-triage
principles_required:
  - "§10.1 KISS"
  - "§10.4 DRY"
  - "§10.6 SDD"
delivery_mode: "/ai-build (single-file fix; small)"
mantra: "Fix the one real defect; document the tool's false positives; do not refactor to satisfy a third-party validator's opinions."
---

# Skill-Map (sm) Validator Triage and Real-Defect Fix

> Scope chosen by owner: **Real defects only** + sm is **one-off / exploring**.
> Therefore: fix the single genuine deviation, classify the rest as
> `sm` false positives, and do NOT invest in an sm suppression-config or
> CI gate. This brief is the contract handed to `/ai-brainstorm`.

## 1. Vision

`sm check --json` (the third-party "skill-map" validator) was run against an
ai-engineering install at `$HOME/repos/test` and emitted ~150 findings. The
end state: a clear, evidence-backed triage that separates the **one real
defect** from the **structural false positives** `sm` produces because its
schema and link-graph model do not match ai-engineering's deliberate design.
Outcome is a one-file fix plus a durable triage note — not a refactor of the
framework to please a tool we are only evaluating.

## 2. Scope Boundary

**In scope**
- Fix the one genuine deviation: `color: magenta` on the `review-validator`
  agent (off the standard Claude Code agent palette).
- Produce the triage classification (this brief's §3/§5) so the noise is
  understood once and not re-litigated.

**Explicitly OUT of scope**
- Renaming the `effort: cheap|mid|high` taxonomy to satisfy sm's enum
  (would touch ~46 SKILL.md files + schema + tests + 3 mirror surfaces).
- Restructuring or renaming the 9 skill+agent name pairs.
- "Fixing" the ~80 `reference-broken` findings (they are graph-scope and
  prose-parsing artifacts, not real dangling links).
- Building an `sm` config file, ignore-list, or CI gate (owner is
  exploring sm, not adopting it).
- Link-self-loop / reference-redundant noise (info/warn only; ignore).

## 3. Diagnostic Snapshot

Evidence from the live repo (`/Users/soydachi/repos/ai-engineering`) and the
`sm check --json` output captured at `$HOME/repos/test`.

| # | sm finding class | sm severity | Verdict | Evidence |
|---|---|---|---|---|
| 1 | `frontmatter-invalid` — `/color must be ... allowed values` | warn | **REAL (minor)** | `.claude/agents/review-validator.md:5` = `color: magenta`. Every other agent uses a standard palette color (blue/cyan/green/orange/purple/red/yellow); `magenta` is the lone outlier. |
| 2 | `frontmatter-invalid` — `/effort must be ... allowed values` (~46 skills) | warn | **FALSE POSITIVE** | ai-engineering taxonomy is `cheap` (12), `mid` (34), `high` (8) — e.g. `.claude/skills/ai-advise/SKILL.md:4` = `effort: cheap`. sm accepts only `high`, so it flags `cheap`+`mid`. `effort` is an ai-engineering convention, not a native Claude Code field; sm's enum is its own. |
| 3 | `reference-broken` — cross-folder pointers (CLAUDE.md, .ai-engineering/README.md, reference/*, runbooks/*) | error | **FALSE POSITIVE** | Targets exist on disk. `CLAUDE.md:13` -> `docs/persistence-doctrine.md` and `CLAUDE.md:114` -> `.ai-engineering/solution-intent.md` both resolve (verified present). sm only resolves links to files inside its indexed folders; links to the repo root / `docs/` read as "not found in the graph". Its own fix hint says "add its folder under Folders for link validation." |
| 4 | `reference-broken` — backtick paths in prose (`core.md`, `.claude/skills/ai-advise/quality/core.md`, etc.) | error | **FALSE POSITIVE** | sm's `backtick-path` extractor treats backtick-wrapped filenames in SKILL.md prose as links and resolves them relative to the wrong base dir. These are illustrative prose, not pointers. ai-engineering's own `skill_lint` does not treat them as links. |
| 5 | `name-collision` — 9 pairs (ai-advise, ai-autopilot, ai-build, ai-explore, ai-onboard, ai-plan, ai-review, ai-simplify, ai-verify) | error | **FALSE POSITIVE (by design)** | Each is the intentional skill+agent pair: `.claude/skills/<name>/SKILL.md` (chat entry) and `.claude/agents/<name>.md` (dispatchable subagent). These are the 9 user-facing agents per CLAUDE.md §12. The No-Twin Axiom governs skill-vs-**CLI**, not skill-vs-**agent** (`.ai-engineering/reference/surface-axioms.md:28-42`), so nothing in ai-engineering's design forbids the shared name. sm conflates the skill and agent namespaces. |
| 6 | `link-self-loop` (2) / `reference-redundant` (2) | warn/info | **NOISE** | Self-reference + duplicate-link advisories on `mirror-authoring.md`, `ai-session-watch/SKILL.md`, etc. Cosmetic; ignore. |

Net: **1 real, minor defect**. Everything else is sm modeling ai-engineering's
deliberate structure (cross-folder canonical chain, illustrative prose paths,
skill+agent pairing, custom effort taxonomy) as an error.

## 4. Architecture

No architectural change. The single fix is a frontmatter value edit on one
canonical agent file, propagated through the established mirror pipeline:

```
.claude/agents/review-validator.md   (canonical: color value)
        │  ai-eng dev sync (scripts/sync_mirrors/core.py)
        ▼
.codex/ , .agents/ , .github/ mirrors  (regenerated, byte-equivalent)
src/ai_engineering/templates/...        (install template twin — verify parity)
```

Per the "scripts template mirror parity" lesson, a canonical-surface edit that
also lives under `src/ai_engineering/templates/` must be propagated there too,
or fresh installs ship the stale value.

## 5. Evidence Catalog

| Claim | Location |
|---|---|
| `review-validator` uses non-standard `color: magenta` | `.claude/agents/review-validator.md:5` |
| effort taxonomy is cheap/mid/high (not low/medium/high) | `.claude/skills/ai-advise/SKILL.md:4` (`effort: cheap`); tally: cheap 12 / mid 34 / high 8 across `.claude/skills/*/SKILL.md` |
| CLAUDE.md cross-folder links resolve on disk | `CLAUDE.md:13` -> `docs/persistence-doctrine.md` (present); `CLAUDE.md:114` -> `.ai-engineering/solution-intent.md` (present) |
| .ai-engineering/README.md links flagged but targets exist | `.ai-engineering/README.md:14` (README.md/AGENTS.md/docs/persistence-doctrine.md all present) |
| 9 user-facing agents == 9 same-named skills (by design) | `CLAUDE.md` §12 "Agents (9)" + `.claude/agents/<name>.md` ∩ `.claude/skills/<name>/SKILL.md` |
| No-Twin Axiom is skill-vs-CLI, not skill-vs-agent | `.ai-engineering/reference/surface-axioms.md:28-42` |

## 6. Roadmap

- **M1 — Fix the real defect.** Change `color: magenta` to a standard palette
  color on `review-validator`. Gate: value is in the Claude Code agent palette.
- **M2 — Propagate.** Run `ai-eng dev sync`; confirm the template twin under
  `src/ai_engineering/templates/` carries the new value. Gate: mirror/template
  parity (no drift).
- **M3 — Record the triage.** Land this triage (or a short note pointer) so the
  sm false-positive classes are not re-investigated. Gate: §3 table reachable.

No M4. sm-config / CI-gate is deferred (out of scope per owner).

## 7. Definition of Done

1. `review-validator` agent `color` is a valid Claude Code palette value
   (no longer `magenta`), canonical + all mirrors + install template aligned.
2. `ai-eng dev sync` is clean (no uncommitted mirror drift).
3. The triage (§3) is captured so each sm finding class has a standing verdict.
4. No other ai-engineering file changed — taxonomy, name pairs, and links are
   left intact by deliberate decision.

## 8. Quality Stamps

- **§10.1 KISS** — smallest correct change: one value, not a taxonomy migration.
- **§10.4 DRY** — fix the canonical agent once; let `sync_mirrors` propagate.
- **§10.6 SDD** — this brief precedes the spec; the triage is the contract.
- Contracts honoured: mirror byte-parity (`sync_mirrors/core.py`), template
  parity, no `# noqa`-style suppressions, no backwards-compat shim.

## 9. Open Decisions

1. **Replacement color for `review-validator`.** Recommend `purple` (closest to
   magenta and already in use) or `pink` (currently unused, keeps palette
   distinct). Spec phase picks one.
2. **Triage durability.** Keep this triage as the draft brief only, or promote
   the §3 table into a short `docs/` note (or `.ai-engineering/reference/`)? For
   a one-off sm look, the draft brief alone is likely sufficient.
3. **External sm schema unverified.** The two background research agents (sm
   repo/schema + in-repo schema map) hit the session limit before returning, so
   the exact sm `effort`/`color` enum source and whether sm offers a
   folder-scope/ignore config are **[unsourced]**. The verdicts in §3 rest on
   direct repo evidence + sm's own output, which is sufficient for the chosen
   scope; revisit only if sm is later adopted as a gate.

## 10. Migration

Hard value change, no shim (CONSTITUTION.md §3). `magenta` -> standard color is
not a breaking contract change (cosmetic agent metadata). CHANGELOG note
optional given the size; `/ai-docs` will decide at PR time.

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Color edit not propagated to template twin -> stale fresh installs | Medium | Low | M2 parity gate; check `src/ai_engineering/templates/` after `dev sync`. |
| Scope creep into "make sm green" | Medium | Medium | §2 boundary is explicit; reject taxonomy/name-pair churn. |
| Future reader re-treats sm false positives as real bugs | Medium | Low | §3 standing verdicts (M3). |
| Chosen replacement color clashes with a sibling reviewer agent | Low | Low | Spec phase checks the agent palette before picking. |

## 12. References

- `sm` / skill-map third-party validator — repo/schema **[unsourced]**
  (research agents interrupted by session limit; confirm if sm is adopted).
- Claude Code agent frontmatter `color` palette (standard set:
  red/blue/green/yellow/purple/orange/pink/cyan) — **[unsourced here]**,
  inferred from the repo's existing color usage + sm's rejection of `magenta`.
- In-repo: `.ai-engineering/reference/surface-axioms.md`, `CLAUDE.md` §12/§16.

## 13. Glossary

- **sm / skill-map** — third-party CLI that validates `.claude/skills` and
  `.claude/agents` frontmatter + cross-references.
- **False positive (here)** — an sm finding that flags deliberate
  ai-engineering design (custom effort taxonomy, skill+agent pairing,
  cross-folder canonical links, illustrative prose paths) as an error.
- **No-Twin Axiom** — ai-engineering rule on when one verb may appear as both a
  `/ai-<name>` skill and an `ai-eng <verb>` CLI; does NOT govern skill-vs-agent.
- **Template twin** — the copy of a canonical file under
  `src/ai_engineering/templates/` shipped into fresh installs.

## 14. Acceptance

- [ ] `review-validator` agent `color` changed off `magenta` to a valid palette value.
- [ ] Canonical + `.codex`/`.agents`/`.github` mirrors + `src/.../templates` twin all carry the new color.
- [ ] `ai-eng dev sync` clean; no mirror drift.
- [ ] §3 triage verdicts captured (real vs sm false positive).
- [ ] No effort-taxonomy, name-pair, or link changes made.
- [ ] No sm config / CI gate added (deferred by scope).
