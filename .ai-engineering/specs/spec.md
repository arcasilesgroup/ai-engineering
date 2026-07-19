---
spec: spec-188
slug: skillmap-signal-recovery
title: "Skill-Map signal recovery: fix real bugs sm found, harden our own frontmatter gate"
status: in-progress
effort: medium
summary: "Fix the 3 real bugs skill-map (sm) found in archived specs; harden spec_lint to strict-parse frontmatter YAML (fail closed); reaffirm D-173-03 (sm one-off, no config)."
audience: framework-dev
source_brief: .ai-engineering/specs/drafts/skillmap-signal-recovery-brief.md
---

# Skill-Map signal recovery: fix real bugs sm found, harden our own frontmatter gate

## Summary

The third-party `skill-map` (`sm`) validator reports 2659 findings against this repo,
~99.9% false positive (rigorously proven: 0 real broken links across 25 stratified samples
+ a 662-finding systematic scan; see the source brief). spec-173 (PR#596, shipped) already
ruled `sm` a one-off evaluation and declined to add config or a CI gate (D-173-03). The
operator reaffirms that posture: **we do not invest in tuning a noisy third-party tool.**

But `sm` did surface one genuinely valuable class our own gate is blind to: malformed YAML
in spec frontmatter. Two archived `spec-186` files carry an unquoted `title:` whose mid-value
colon breaks YAML (PyYAML-confirmed invalid), and our spec-frontmatter check
`tools/spec_lint/checks/frontmatter.py:92-121` is a hand-rolled `partition(":")` parser
("not real YAML", per its own docstring) that cannot see it.

This spec does two things and nothing else: **(1) fix the three real bugs `sm` found** (both
`spec-186` colon-titles, one unbalanced backtick in `spec-177`), and **(2) harden our own
`spec_lint` frontmatter check to strict-parse YAML and fail closed on malformed frontmatter**,
with a TDD regression test — so the framework catches this bug-class itself, independent of
`sm` or any third-party tool. No `sm` configuration, no taxonomy churn, no CI gate.

## Goals

- `.ai-engineering/specs/archive/spec-186-client-value-comms-lens/spec.md` and `plan.md`
  frontmatter parse as valid YAML (`yaml.safe_load` succeeds).
- The unbalanced inline backtick in the `spec-177` archived plan is closed.
- `tools/spec_lint/checks/frontmatter.py` rejects frontmatter that is not valid YAML,
  emitting a clear finding (fails closed — this is an integrity gate).
- A regression test fails on the pre-fix `spec-186` colon-title fixture and passes once the
  value is quoted.
- The full existing spec/test suite stays green; no live or template spec regresses.
- The reaffirmed posture (D-173-03 stands; we add our own gate rather than tune `sm`) is
  recorded so this is not re-litigated.

## Non-Goals

- **No `sm` configuration.** No edits to `.skillmapignore`, no `sm plugins disable`, no
  changes to the tracked `.skill-map/settings.json`, no scan-scope tuning. (The scan-scope
  preference gathered at brainstorm is moot under the no-config posture.)
- **No CI gate on `sm check`.** `sm` is not wired into `manifest.yml` or any workflow.
- **No effort-taxonomy rename** (`cheap|mid|high`) and **no skill+agent name-pair restructure**
  — spec-173 D-173-02 false-positive verdicts stand unchanged.
- **No attempt to fix `sm`'s `reference-broken` false positives**, and **no upstream issue
  filing** — we are not adopting `sm`, so investing in its ecosystem is out of scope.
- **No change to the fail-open YAML readers** `.ai-engineering/scripts/session_bootstrap.py:141`
  and `branch_slug.py:62` — they are hot-path plumbing that correctly fails open.

## Decisions

### D-188-01 — Fix the three real bugs in the frozen archive

Quote the two `spec-186` `title:` values (`spec.md:4`, `plan.md:2`) so the mid-value colon no
longer breaks YAML; close the unbalanced inline backtick in the `spec-177` archived plan.

**Rationale**: these are genuinely-invalid YAML and unbalanced Markdown, confirmed at source
(PyYAML raises `ScannerError` at column 36 on the `spec-186` titles). Frozen does not mean
broken — malformed YAML in an archived spec can break any tool that parses it, and the
hardened gate (D-188-02) must find the archive clean. Two-character quote fixes; smallest
correct change (§10.1 KISS). Hard edit, no shim (CONSTITUTION.md §3).

### D-188-02 — Harden `spec_lint` frontmatter to strict-parse YAML, fail closed

Augment `tools/spec_lint/checks/frontmatter.py` so the frontmatter block is validated with a
real YAML parse (`yaml.safe_load`); a `YAMLError` emits a blocking finding. A regression test
uses the `spec-186` colon-title as a fixture: red without the fix, green after quoting.

**Rationale**: `spec_lint` is an integrity gate, and integrity boundaries fail closed per
`.ai-engineering/reference/gate-policy.md`. The current naive partition parser silently
accepts malformed frontmatter — that is how the `spec-186` bug shipped. `sm` was merely the
detector; the durable fix is our own gate, tool-independent (§10.5 TDD, §10.6 SDD). This is
the root-cause fix, not a symptom patch.

### D-188-03 — Reaffirm spec-173 D-173-03: `sm` stays a one-off, no committed config or gate

We add no `sm` scope config, no analyzer disable, no CI wiring. `sm` remains a tool the
operator may run ad hoc.

**Rationale**: `sm`'s flagship `reference-broken` analyzer has four distinct extraction bugs
(backtick-prose resolved directory-relative, slash-prose read as invocations, CSS `@`-rules
read as mentions, and double-extraction of a valid link's own backtick text) that we do not
own the code to fix. Tuning `sm` means committing config to appease a noisy external tool that
would still need upstream fixes to be correct. Better return on effort: harden our own gate
(D-188-02). Operator-confirmed at brainstorm. YAGNI (§10.2).

### D-188-04 — Leave the fail-open YAML readers unchanged

`session_bootstrap.py:141` and `branch_slug.py:62` continue to catch `YAMLError` and degrade
rather than raise.

**Rationale**: both are hot-path plumbing (session bootstrap, branch-slug derivation), and
`gate-policy.md` prescribes fail-open for plumbing and fail-closed only for integrity gates.
Making them raise would risk breaking session start on a transient malformed file. The gate
that *should* stop malformed specs is `spec_lint` (D-188-02); that is the only place the
posture changes.

### D-188-05 — Strict-parse scope = the surfaces `spec_lint` already governs

The new YAML-parse check applies to whatever spec/plan surfaces `spec_lint` already scans; the
two `spec-186` archive fixes (D-188-01) keep that suite green. We do not force a fresh
full-archive re-validation beyond what the existing check already covers.

**Rationale**: scoping the check to the gate's existing surface avoids a surprise wave of reds
from other latent archive-frontmatter quirks unrelated to this spec, while still closing the
gap for governed specs. Exact surface enumeration is a `/ai-plan` detail. §10.1 KISS.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Hardened `spec_lint` reddens a currently-passing live or template spec | Low | Medium | Research confirmed 0 live/template occurrences of the colon-title pattern; run the hardened check across all governed specs before merge (D-188-05). |
| Editing frozen archive files is seen as rewriting history | Low | Low | Two-char quote fixes to genuinely-invalid YAML; documented in CHANGELOG; frozen != permitted-to-be-broken (D-188-01). |
| Strict parse surfaces other latent archive-frontmatter issues | Medium | Low | D-188-05 scopes to the gate's existing surface; any extra finds are triaged, not auto-blocked, in `/ai-plan`. |
| Reader-fail-open left unchanged hides a real malformed live spec at runtime | Low | Low | `spec_lint` (D-188-02) blocks malformed specs at the gate before they reach the readers; plumbing fail-open is deliberate (D-188-04). |
| Future reader re-treats `sm`'s false positives as real bugs | Medium | Low | spec-173 triage table + this spec's D-188-03 stand as the durable verdict. |

## Acceptance

- [ ] `spec-186` archive `spec.md:4` and `plan.md:2` titles quoted; `yaml.safe_load` parses both frontmatter blocks.
- [ ] `spec-177` archived plan unbalanced inline backtick closed.
- [ ] `tools/spec_lint/checks/frontmatter.py` emits a blocking finding on non-YAML-parseable frontmatter.
- [ ] Regression test: red on the pre-fix `spec-186` colon-title fixture, green after quoting.
- [ ] Full spec/test suite green; no live or template spec regresses under the hardened check.
- [ ] No `sm` config change (`.skillmapignore`, `.skill-map/settings.json`), no CI gate, no taxonomy/name-pair change.
- [ ] Spec records the reaffirmation of D-173-03 (sm one-off; own-gate over tool-tuning).
