---
title: "Skill-Map (sm) Signal Recovery: config the validator down to real signal"
status: draft
audience: framework-dev
branch: chore/skillmap-signal-recovery
length_estimate: small-medium
authoring_style: diagnostic-decision
principles_required:
  - "§10.1 KISS"
  - "§10.2 YAGNI"
  - "§10.5 TDD"
  - "§10.6 SDD"
delivery_mode: "/ai-build (committed sm config + a small spec_lint parser hardening; brainstorm picks the scope tier)"
mantra: "Silence the tool's structural noise with committed config, fix the three real bugs it found, and harden our own gate so we catch them without it."
---

# Skill-Map (sm) Signal Recovery: config the validator down to real signal

> This brief reopens a decision spec-173 closed. spec-173 (PR#596, shipped) triaged an
> earlier ~150-finding `sm` run, fixed the one real defect, and ruled: `sm` is a one-off
> evaluation, add no config and no CI gate
> (`.ai-engineering/specs/archive/spec-173-skillmap-validator-triage/spec.md:19-20`). The
> operator is now looking at a full-repo run reporting **2659 findings** and asking whether
> we can make the tool useful. That is a genuine revision of decision D-173-03, not a
> re-triage. This brief is the contract handed to `/ai-brainstorm`.

## 1. Vision

`sm` (skill-map v0.88.0, npm `@skill-map/cli`, spec `@skill-map/spec@0.80.0`) is a
Markdown docs-graph linter. Run unconfigured against this repo it emits **2659 findings,
2456 of them `error`**, and is therefore unusable: the signal is drowned. Rigorous triage
(25 stratified samples read at source + a 662-finding systematic scan) shows
**zero real broken links in any live surface** and exactly **three genuine bugs**, all in
frozen archive specs. The end state: a committed `sm` configuration that scopes the scan to
source-of-truth surfaces and disables the two analyzers whose model structurally conflicts
with ai-engineering's design, leaving a small, mostly-real signal — plus the durable win of
hardening our own `spec_lint` so the one real bug-class `sm` surfaced (malformed YAML
frontmatter) is caught by our own gate, tool or no tool.

## 2. Scope Boundary

**In scope**
- Fix the three genuine bugs `sm` surfaced (all archive): two unquoted-colon YAML `title:`
  values in `spec-186`, one unbalanced inline backtick in `spec-177`.
- Add committed `sm` scope + analyzer configuration that collapses 2659 findings to a
  small, real residue (and makes `sm check` exit 0).
- Harden `tools/spec_lint/checks/frontmatter.py` to strict-parse spec/plan frontmatter as
  YAML so an unquoted-colon title fails our own gate — the root-cause fix independent of `sm`.
- File one upstream issue for the `reference-broken` false-positive class.

**Explicitly OUT of scope**
- Renaming the `effort: cheap|mid|high` taxonomy to satisfy `sm`'s enum (46 SKILL.md files +
  schema + tests + 4 mirror surfaces; standing false-positive verdict, spec-173 D-173-02).
- Restructuring the 9 intentional skill+agent name pairs (spec-173 D-173-02; CLAUDE.md §12).
- Wiring `sm` into CI as a blocking gate (see §9 OD5 — recommended still deferred).
- Any attempt to make `sm`'s `reference-broken` analyzer *correct* — it has four distinct
  extraction bugs we do not own the code to fix (§3, §4).

## 3. Diagnostic Snapshot

Evidence from the live repo (`$HOME/repos/ai-engineering`) and the captured
`sm check --json` dump (2659 findings). All counts are from the current dump.

**Finding census**

| analyzerId | count | severity | verdict |
|---|---|---|---|
| `reference-broken` | 2447 | error | **false positive** (four extraction bugs, §4) |
| `reference-redundant` | 121 | info | noise (duplicate-link advisory) |
| `frontmatter-invalid` (effort enum) | 46 | warn | **false positive** — our `cheap\|mid\|high` taxonomy ≠ `sm`'s enum; all 46 in live `.claude/skills` |
| `link-self-loop` | 31 | warn | noise — archive `spec.md`/`plan.md` naming themselves in prose |
| `name-collision` | 9 | error | **false positive by design** — intentional skill+agent pairs |
| `frontmatter-parse-error` | 4 | warn | 2 in `.venv/` (never in scope); **2 REAL** malformed YAML |
| `backtick-unbalanced` | 1 | warn | **1 REAL** (archive) |

**Where the 2447 phantom refs come from** — the scan is unscoped
(`.skill-map/settings.json` is tracked; `.skillmapignore` is the stock `sm init` default,
`.skillmapignore:1-28`, excluding only `.git/node_modules/dist`, not the trees below;
`scan.respectGitignore` is `false`):

```
891  src/ai_engineering/templates/    byte-mirror of .ai-engineering/ — double-counts canonical
537  .codex/ .agents/ .opencode/ .github/   byte-regenerated IDE mirrors of .claude/
365  .ai-engineering/specs/archive/   frozen historical specs
313  .ai-engineering/specs/drafts/    WIP briefs
126  CHANGELOG.md                     prose filename mentions
  2  .venv/                           vendored third-party (huggingface_hub templates)
```

**The one real signal, and why it matters** — `sm`'s `frontmatter-parse-error` caught two
genuinely-invalid YAML frontmatter blocks that our own gate cannot see:
`.ai-engineering/specs/archive/spec-186-client-value-comms-lens/spec.md:4` and
`plan.md:2` both carry `title: spec-186 — Client-Value Lens: stakeholder-legible …` — an
unquoted value whose mid-value `: ` breaks YAML (PyYAML: `mapping values are not allowed
here`, column 36). Our spec-frontmatter gate `tools/spec_lint/checks/frontmatter.py:92-121`
is a hand-rolled stdlib `partition(":")` parser (its own docstring: "not real YAML"), so it
captures the value on the first colon and never errors. Two scripts *do* use real
`yaml.safe_load` on spec frontmatter — `.ai-engineering/scripts/session_bootstrap.py:141`
and `branch_slug.py:62` — but both fail open (catch `YAMLError`, return `None`), silently
degrading rather than blocking. Net: a malformed spec title ships without any gate noticing.

## 4. Architecture

Two independent problems, two independent fixes.

**Problem A — `sm`'s `reference-broken` analyzer is miscalibrated for a path-heavy docs
corpus.** Its declared job is "flags arrows pointing at a node not part of the current
scan", and it manufactures those arrows four ways, none of which we can fix (closed-source
analyzer in the `core` plugin):

1. **Bare backtick prose, resolved directory-relative** (87%, ~2125 findings). A skill body
   that mentions `` `spec.md` `` or `` `docs/architecture/brand-tokens.md` `` in prose is
   read as a link and resolved against the *containing* file's directory, producing phantoms
   (`.claude/skills/_shared/_history.md`; the "reference/reference" doubling at
   `.ai-engineering/reference/brand-voice.md:9` → phantom
   `.ai-engineering/reference/docs/architecture/brand-tokens.md` while the real file sits at
   `docs/architecture/brand-tokens.md`, and `principles.md:251,253`).
2. **Slash-prose read as an invocation** (~66 findings, `kind:"invokes"`) — `/PR`, `/token`
   at `docs/ci-branch-protection.md:31,40`; `/release` at `docs/cache-cleanup-runbook.md:139`;
   the fictional example prompt `/ai-feedback` at `.claude/skills/ai-spec-draft/SKILL.md:55`.
3. **CSS `@`-rule read as an agent mention** — `@starting-style` inside a fenced code block
   at `.claude/skills/ai-animation/handlers/components.md:127,137`.
4. **Double-extraction of a valid link's own text** (new; not in spec-173's list) — a
   correct `[`CONSTITUTION.md`](../CONSTITUTION.md)` at `docs/persistence-doctrine.md:118-119`
   resolves the `href` fine, yet `sm` *also* extracts the inner backtick text and flags
   `docs/CONSTITUTION.md` as broken.

Structural proof it flags no real links: **0 of 662** live-surface findings contain the
literal `](target)` markdown-link substring for their flagged target, and **0 of 2447**
targets across the whole corpus are `../`-prefixed — `sm` never once resolved a genuine
relative link. The only lever we own is scope + disable + upstream report:

```
Scope:    edit .skillmapignore (gitignore syntax)  +  scan.respectGitignore=true
Disable:  sm plugins disable core/reference-broken core/name-collision
              → writes plugins.core.extensions.*.enabled=false to the tracked
                .skill-map/settings.json (team-shared) [--local for per-checkout]
Upstream: github.com/crystian/skill-map/issues  (the 4 extraction bugs)
```

**Problem B — our own spec-frontmatter gate cannot parse YAML.** Independent of `sm`. Fix at
the source: make `tools/spec_lint/checks/frontmatter.py` attempt a real `yaml.safe_load` of
the frontmatter block and emit a hard finding on `YAMLError`, with the `spec-186` colon-title
as the regression fixture. This is the durable win — it catches the bug-class whether or not
`sm` is ever adopted.

## 5. Evidence Catalog

| Claim | Location |
|---|---|
| spec-173 ruled sm one-off, no config/gate | `.ai-engineering/specs/archive/spec-173-skillmap-validator-triage/spec.md:19-20` |
| spec-173 standing FP verdicts (effort, name-pairs, refs) | same spec `:33-35`, D-173-02 `:66-76` |
| `.skillmapignore` is stock `sm init` default | `.skillmapignore:1-28` |
| `.skill-map/settings.json` is git-tracked (config lands here) | `git ls-files .skill-map` → `.skill-map/settings.json` |
| `.skill-map/` partial gitignore (db/serve/local/backups) | `.gitignore:194,195,213,214` |
| REAL: unquoted-colon YAML title (spec-186) | `.ai-engineering/specs/archive/spec-186-client-value-comms-lens/spec.md:4`; `plan.md:2` |
| our spec-frontmatter gate is a naive partition parser | `tools/spec_lint/checks/frontmatter.py:92-121` |
| fail-open YAML readers that degrade silently | `.ai-engineering/scripts/session_bootstrap.py:141`; `branch_slug.py:62` |
| reference-broken bug 1 (doubling) | `.ai-engineering/reference/brand-voice.md:9`; `principles.md:251,253` |
| reference-broken bug 2 (slash-prose) | `docs/ci-branch-protection.md:31,40`; `docs/cache-cleanup-runbook.md:139` |
| reference-broken bug 2 (fictional example prompt) | `.claude/skills/ai-spec-draft/SKILL.md:55` |
| reference-broken bug 3 (CSS @-rule) | `.claude/skills/ai-animation/handlers/components.md:127,137` |
| reference-broken bug 4 (link-text double-extract) | `docs/persistence-doctrine.md:118-119` |
| effort taxonomy is cheap/mid/high (FP) | `.claude/skills/ai-advise/SKILL.md:4` (`effort: cheap`); tally cheap 12 / mid 34 / high 7 |
| 9 name pairs are intentional (design) | CLAUDE.md §12; No-Twin Axiom is skill-vs-CLI `.ai-engineering/reference/surface-axioms.md:28-42` |
| CANONICAL.md true home (phantom target resolves) | `scripts/sync_mirrors/core.py:1028` |
| only error-sev left after reference-broken disable = 9 name-collision | `sm check --json` census |

## 6. Roadmap

- **M1 — Fix the three real bugs.** Quote the two `spec-186` titles; close the `spec-177`
  unbalanced backtick. **Gate:** PyYAML parses both `spec-186` frontmatter blocks;
  `sm check --analyzers core/frontmatter,core/backtick-unbalanced` reports 0 of these.
- **M2 — Scope the scan.** Set `scan.respectGitignore true` (folds `.venv/`) and add to
  `.skillmapignore`: `src/ai_engineering/templates/`, the mirror trees
  (`.codex/ .agents/ .github/ .opencode/`), and `.ai-engineering/specs/drafts/` (see OD2 on
  archive). **Gate:** node count drops from ~1900 to the canonical set; the 891 template +
  537 mirror + 313 draft phantom refs disappear.
- **M3 — Disable the structurally-FP analyzers.** `sm plugins disable core/reference-broken
  core/name-collision`, committed to `.skill-map/settings.json`. **Gate:** `sm check` exits
  0; every residual finding is real or info-only.
- **M4 — Harden our own gate (durable).** `tools/spec_lint/checks/frontmatter.py` strict-parses
  frontmatter YAML and fails on `YAMLError`; regression test uses the `spec-186` colon-title as
  a fixture (fails without the fix, passes with the value quoted). **Gate:** `spec_lint` red on
  an unquoted-colon title, green after quoting; existing live + template specs still pass.
- **M5 — File upstream.** One issue at `github.com/crystian/skill-map/issues` documenting the
  four `reference-broken` extraction bugs (§4) with minimal repros. **Gate:** issue URL recorded
  in the spec.

## 7. Definition of Done

1. `spec-186` spec.md/plan.md titles are valid YAML; `spec-177` backtick closed; `sm`'s two
   real-signal analyzers report those files clean.
2. Committed `sm` config (`.skillmapignore` + `.skill-map/settings.json` plugin-disable)
   makes `sm check` exit 0 on a fresh scan, with a documented residual (info/warn only).
3. `tools/spec_lint/checks/frontmatter.py` fails on frontmatter that is not valid YAML, with
   a regression test; all live + template specs pass the hardened check.
4. An upstream issue for the `reference-broken` false-positive class exists and is linked.
5. No effort-taxonomy rename, no name-pair restructure, no CI gate added.
6. spec-173's triage table stays valid; only its "invest nothing" posture (D-173-03) is
   explicitly revised, documented in the spec.

## 8. Quality Stamps

- **§10.1 KISS** — smallest correct moves: quote two titles, two config edits, one parser
  hardening. No taxonomy migration, no schema fight.
- **§10.2 YAGNI** — no CI gate, no per-node suppression machinery (`sm` offers none anyway),
  no attempt to reimplement `reference-broken` correctly.
- **§10.5 TDD** — M4 lands a regression test that fails on the `spec-186` fixture without the
  fix and passes with it.
- **§10.6 SDD** — this brief precedes and feeds the spec; the census + verdicts are the contract.
- Contracts honoured: committed team-shared config (no machine-local drift), mirror/template
  parity untouched, no `# noqa`-class suppression, no backwards-compat shim (CONSTITUTION.md §3).

## 9. Open Decisions

1. **OD1 — Adoption posture (revises D-173-03).** Adopt `sm` as a tuned *local* dev linter
   (M2+M3 committed config), reaffirm "one-off, no config", or drop `sm` entirely?
   *Recommend:* adopt as a local dev aid — the config is cheap, committed, and once tuned the
   tool genuinely catches malformed frontmatter (proven by the `spec-186` catch).
2. **OD2 — Archive/drafts in scope?** Keeping `.ai-engineering/specs/archive/` in scan means
   `sm` re-catches future malformed archive YAML; scoping it out is quieter. *Recommend:* scope
   `drafts/` out (WIP churn), keep `archive/` in (small once `reference-broken` is disabled, and
   it is where the two real bugs live).
3. **OD3 — Disable `core/frontmatter` (effort enum) too?** The 46 `effort` warnings are
   non-failing but persistent. *Recommend:* leave enabled as `warn` (harmless, and it still
   surfaces real color/schema issues like the one spec-173 fixed); revisit if noisy.
4. **OD4 — Bundle M4 (spec_lint hardening) here, or split to its own spec?** It is orthogonal
   to `sm` config but is the root-cause fix. *Recommend:* bundle — it is small and it is the
   reason the bug shipped.
5. **OD5 — CI gate on `sm check`?** *Recommend:* still no — the flagship `reference-broken`
   analyzer is off and the tool is immature; gate on our own hardened `spec_lint` (M4) instead.
   Reconsider only after the upstream fix lands.

## 10. Migration

Hard config change, no shim (CONSTITUTION.md §3). New committed entries in `.skillmapignore`
and `.skill-map/settings.json`; two quoted YAML titles; one hardened `spec_lint` check.
This brief **supersedes the posture** of the earlier triage brief
(`.ai-engineering/specs/drafts/skillmap-validator-triage-brief.md`) and spec-173 D-173-03
("no sm config / CI gate") — the false-positive *verdicts* from spec-173 remain valid and are
reused, only the "evaluate one-off, invest nothing" stance is revised now that the operator is
reconsidering the tool at full-repo scale. The stale triage brief is left as spec-173's frozen
`source_brief` and is not deleted. No CHANGELOG-breaking contract change (config + gate
hardening only); `/ai-docs` decides on a CHANGELOG note at PR time.

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Disabling `reference-broken` hides a future *real* broken link | Medium | Low | 0 real found across 662 + 2447 scanned; the analyzer cannot distinguish real from prose (0/2447 `../`), so it was never a reliable detector; real markdown-link hygiene stays covered by `skill_lint` md_mirror checks. |
| Committed `.skill-map/settings.json` confuses contributors | Low | Low | Short note in the spec + a comment header in `.skillmapignore`; config is team-shared by design. |
| Scoping `archive/` out would hide real malformed archive YAML | Low | Low | OD2 recommends keeping `archive/` in scan; M4 gate catches live/template cases regardless. |
| Hardened `spec_lint` YAML parse rejects a currently-passing live spec | Low | Medium | Agent confirmed 0 live/template occurrences; M4 gate runs against all live + template specs before merge. |
| Upstream never fixes `reference-broken` → analyzer stays off forever | Medium | Low | Acceptable — other analyzers (`frontmatter-parse-error`, `backtick-unbalanced`) still deliver value with it off. |
| Scope creep into "make sm fully green / rename taxonomy" | Medium | Medium | §2 boundary + spec-173 standing verdicts reject taxonomy/name-pair churn. |

## 12. References

- skill-map: repo `github.com/crystian/skill-map`, issues `github.com/crystian/skill-map/issues`,
  homepage `skill-map.ai`; npm `@skill-map/cli@0.88.0`, spec `@skill-map/spec@0.80.0`
  (from local `sm` introspection + npm registry).
- `sm` config surface — `.skillmapignore` (gitignore syntax), `config.ignore` (glob array),
  `config.roots` (allowlist), `scan.respectGitignore`, `scan.referencePaths`; analyzer disable via
  `sm plugins disable <qualified-id>`; **no** per-node finding suppression (sidecar `.sm` schema is
  provenance-only) — all confirmed from `sm help … --format md` and the bundled JSON schemas.
- PyYAML — confirmed the `spec-186` titles raise `ScannerError` (real invalid YAML).
- In-repo: spec-173 archive (`spec.md`, sidecar `.ai-engineering/state/specs/spec-173.json`,
  `_history.md:167`), CLAUDE.md §12/§13, `.ai-engineering/reference/surface-axioms.md`.

## 13. Glossary

- **sm / skill-map** — third-party CLI that scans a repo's Markdown into a node graph and runs
  analyzers over frontmatter + cross-references.
- **`reference-broken`** — the `core` analyzer that flags "arrows pointing at a node not part of
  the current scan"; miscalibrated here (§4), disabled by this brief's recommendation.
- **Backtick-prose extraction** — `sm` treating a backtick-wrapped path *mentioned* in prose as a
  live link and resolving it directory-relative → phantom target.
- **name-collision** — `sm` flagging two nodes that declare the same name; false-positive here
  because the 9 skill+agent pairs deliberately share a name (CLAUDE.md §12).
- **No-Twin Axiom** — ai-engineering rule governing when a verb may be both a `/ai-<name>` skill
  and an `ai-eng <verb>` CLI; does not govern skill-vs-agent, so it does not forbid the pairs.
- **Template twin** — the copy of a canonical file under `src/ai_engineering/templates/` shipped
  into fresh installs; a byte-mirror, hence excluded from scan (validated by parity gates instead).

## 14. Acceptance

- [ ] `spec-186` spec.md:4 and plan.md:2 titles quoted; PyYAML parses both frontmatter blocks.
- [ ] `spec-177` unbalanced inline backtick closed.
- [ ] `.skillmapignore` excludes `src/ai_engineering/templates/`, `.codex/ .agents/ .github/ .opencode/`, and `.ai-engineering/specs/drafts/`; `scan.respectGitignore=true`.
- [ ] `sm plugins disable core/reference-broken core/name-collision` committed to `.skill-map/settings.json`; `sm check` exits 0.
- [ ] `tools/spec_lint/checks/frontmatter.py` strict-parses frontmatter YAML and fails on `YAMLError`; regression test with the `spec-186` fixture; all live + template specs pass.
- [ ] Upstream issue for the four `reference-broken` extraction bugs filed and linked.
- [ ] No effort-taxonomy rename, no name-pair restructure, no `sm` CI gate.
- [ ] spec.md documents the D-173-03 revision and reuses spec-173's triage verdicts.
