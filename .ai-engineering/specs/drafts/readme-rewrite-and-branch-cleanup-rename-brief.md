---
title: README rewrite and branch cleanup rename
status: draft
audience: ai-engineering implementation agents; secondary audience is operators and external newcomers
branch: feat/readme-rewrite-and-branch-cleanup-rename
length_estimate: multi-wave refactor; four README surfaces plus skill rename touch surface
authoring_style: staff-principal architecture brief; terminal-native prose; no emoji; no marketing fluff
principles_required:
  - §10.1 KISS
  - §10.2 YAGNI
  - §10.3 SOLID
  - §10.4 DRY
  - §10.5 TDD
  - §10.6 SDD
  - §10.7 Clean Code
  - §10.8 Hexagonal Architecture
delivery_mode: ai-brainstorm consume brief, then ai-plan, then ai-build, then ai-pr
mantra: One governed front door, one honest skill name, zero stale onboarding paths.
---

# README Rewrite & `/ai-branch-cleanup` Rename — Brief for Spec / Plan

> **Brand source of truth:** `docs/design.pen` (Penpot v2.11, five canonical boards) and `docs/untitled.pen` (workshop posters carrying the most distilled voice).
> **North Star:** A first-time visitor lands on the root `README.md`, reads the 30-second pitch, runs one install command, and reaches `/ai-start` without opening a second tab. Every README echoes the same brand voice; no dead links, no stale counts, no marketing fluff, no shims.

---

## 1. Vision

The four README files form the **first-contact surface** of `{ai} engineering`. Today they leak surfaces that are no longer enabled (Antigravity), omit surfaces that are (OpenCode, Cursor), link to files that have been hard-deleted (`GETTING_STARTED.md`), and miss the brand voice that the design system defines (terminal-native, code-comment headers, mid-dot stat lines, bracket-tag status grammar, `{ai} engineering` brace wordmark). The visual brand exists in `docs/design.pen`; the README copy still reads like the 2024 marketing draft.

After this brief is executed:

1. The **root `README.md`** opens with the canonical tagline (`docs/design.pen:3291`), gives an install one-liner, lists the canonical chain (`/ai-brainstorm → /ai-plan → /ai-build → /ai-pr`), and exits under 120 lines (the hard cap enforced at `tests/docs/test_links.py:228`).
2. The **`.ai-engineering/README.md`** (operator-facing governance root) describes the four-tier persistence doctrine, the audited skill chain, and the runbook system in the same brand voice — no marketing speak, no dead links.
3. The **`src/ai_engineering/templates/.ai-engineering/README.md`** (the file that ships to every new project via the installer) stays byte-identical to the live governance README via a documented sync mechanism — so consumers see exactly what dogfood sees.
4. The **`.ai-engineering/team/README.md`** stays as the minimal four-line placeholder it already is (`.ai-engineering/team/README.md:1-4`).
5. The skill `/ai-repo-tidy` is **hard-renamed** to `/ai-branch-cleanup` per `CONSTITUTION.md:71-73` ("No backwards-compat shims"). The new name reveals intent — the skill cleans branches, not "tidies the repo". Every non-historical reference found by `rg --hidden -n 'ai-repo-tidy'` updates in the rename wave; `CHANGELOG.md` carries the `BREAKING CHANGE:` note; mirror sync regenerates root `.codex/`, `.gemini/`, and `.github/` surfaces plus installer-template provider surfaces from `.claude/`.

The deliverable reads like a single intentional product launch, not an accreted set of patches.

---

## 2. Scope Boundary

**In scope:**

- Rewrite from scratch of four README files: `README.md`, `.ai-engineering/README.md`, `.ai-engineering/team/README.md`, `src/ai_engineering/templates/.ai-engineering/README.md`. (Team README will be reviewed; default outcome is preserving the existing 4-line placeholder unless a concrete defect is found.)
- Application of brand voice and lexicon extracted from `docs/design.pen` and `docs/untitled.pen` to all rewritten prose.
- Hard rename `/ai-repo-tidy → /ai-branch-cleanup` across the full surface: canonical `.claude/`, root generated mirrors (`.codex/`, `.gemini/`, `.github/`), installer-template provider surfaces under `src/ai_engineering/templates/project/` (`.claude/`, `.codex/`, `.gemini/`, `.github/`, `.cursor/`, `.opencode/`, `.agent/`), Python source (`src/ai_engineering/config/framework_defaults.py`, `src/ai_engineering/validator/categories/file_existence.py`), reference docs (`.ai-engineering/reference/model-dispatch-policy.md`, `.ai-engineering/reference/surface-axioms.md`), session-bootstrap scripts, and all affected tests.
- `CHANGELOG.md` `[Unreleased]` block updated with a `### BREAKING` entry documenting the skill rename.
- Sanity-review pass on `CONSTITUTION.md`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md` — operator has confirmed they are already current; this brief only checks them, it does not rewrite them.
- Brand-voice **rules document** at `.ai-engineering/reference/brand-voice.md` so future doc edits inherit the lexicon without re-reading the .pen files.

**Out of scope:**

- Updating `docs/design.pen` (the stat line at `docs/design.pen:15131` says "53 skills · 11 agentes · 4 IDEs" — outdated; the design asset team owns this update; this brief notes the drift but does not touch the .pen files).
- Updating `docs/untitled.pen` (the workshop poster says "// 48 skills" at `docs/untitled.pen:482`; same ownership rule).
- Logo SVG generation or rendering. Per operator decision, branding is applied **textually** (voice, tone, lexicon, code-block accents) — no images or SVG inline in README files.
- Refactoring the `/ai-repo-tidy` skill behaviour. This is a pure rename, not a redesign. Behaviour is preserved exactly; only the slug changes.
- Updating the docs portal under `docs/` (other than the new `brand-voice.md` reference). The portal is governed by `prune-contexts-docs-research-evals-brief.md` and overlaps must be coordinated with that work.

---

## 3. Diagnostic Snapshot — Current State Evidence

### 3.1 Root `README.md` (102 lines)

`README.md:23` opens with: *"Turn any repository into a governed AI workspace … One canonical chain across Claude Code, GitHub Copilot, OpenAI Codex, Gemini CLI, and Antigravity."*

Two factual breakages in one sentence:

- **Antigravity is not in the enabled surfaces list.** `.ai-engineering/manifest.yml:28` declares `surfaces.enabled: [claude-code, github-copilot, gemini-cli, codex, opencode, cursor]`. Antigravity is absent.
- **OpenCode and Cursor are missing from the README mention.** Both ship as first-class IDE surfaces (`.ai-engineering/manifest.yml:28`) and have installer-template skill surfaces under `src/ai_engineering/templates/project/.cursor/` and `src/ai_engineering/templates/project/.opencode/` generated by `scripts/sync_mirrors/core.py:81-94` and `scripts/sync_mirrors/core.py:1761-1805`.

`README.md:67-91` ("How AI Works Here" + attribution table) — content is accurate; voice is generic, not branded. The "Standing on the shoulders of …" attribution table is distinctive and should be preserved verbatim.

`README.md:5-21` (banner + badge block) — badges reference `arcasilesgroup/ai-engineering`; live and correct. The dual `<picture>` source pair (`banner-dark.svg` / `banner-light.svg`) loads correctly.

`tests/docs/test_links.py:203-228` (`test_readme_minimal`) enforces a **120-line cap** and forbids skill-list tables; the rewrite has 18 lines of headroom under the cap.

### 3.2 `.ai-engineering/README.md` (294 lines) and the templates twin

`.ai-engineering/README.md:5` contains a dead link: `[Getting Started](../GETTING_STARTED.md)`. The file was hard-deleted by spec-136 D-136-13; `tests/docs/test_links.py:229-231` asserts the file is absent at the repo root. The `EXCLUDED_PATH_FRAGMENTS` at `tests/docs/test_links.py:42-60` excludes `.ai-engineering/` from the broken-link walker, so the dead link does not break CI — but it is the **first link a new operator clicks** after install.

`src/ai_engineering/templates/.ai-engineering/README.md:5` carries the same dead link and is byte-identical to the live `.ai-engineering/README.md`. Because the templates README ships via the installer to every new project, the dead link greets every new operator on every install.

`.ai-engineering/README.md:257-292` lists 12 "Slash Commands" — accurate for the day-to-day flow but no longer reflects the canonical chain shape declared at `CLAUDE.md:47-64` (`/ai-brainstorm → /ai-plan → /ai-build → /ai-pr`).

### 3.3 `/ai-repo-tidy` naming reveals nothing

The current slug suggests the skill "tidies the repo" — vague, untargeted, and a misnomer once you read the body. The skill's actual job is **branch cleanup after merge**: it switches to the default branch, prunes merged and squash-merged branches, syncs to remote, sweeps stale specs, and rotates `.ai-engineering/runtime/`. The verb that survives intent inspection is "branch cleanup", not "tidy". `CLAUDE.md` already uses the verb in the skill description: *"prunes merged and squash-merged branches"*. The rename aligns the slug with intent — a textbook case of `§10.1 KISS` ("naming reveals intent") and `§10.4 DRY` (one verb per concept, no synonyms competing for the same job).

### 3.4 Brand voice is documented in design files but absent from prose

`docs/design.pen` declares the full visual identity system across five canonical boards (`docs/design.pen:9, 647, 1719, 2260, 3160`). The brand uses JetBrains Mono as the primary face (`docs/design.pen:1796`), `$accent` (#00D4AA) as the energy color (`docs/design.pen:850`), `$primary-dark` (#0B1120) as the base background (`docs/design.pen:722`), `{ai} engineering` as the wordmark (`docs/design.pen:40, 3291`), and bracket-tag status grammar `[PASS] / [WARN] / [FAIL]` (`docs/design.pen:3862-3911`).

The workshop posters in `docs/untitled.pen` distil the voice further: every section label prefixes `//` like a code comment (`// workshop`, `// what's inside`, `// stack` — `docs/untitled.pen:1517`); feature counts compress to mid-dot lines (*"48 skills · 10 agents · 4 IDEs · 1 governed flow"* — `docs/untitled.pen:1944`); CTAs render as shell prompts (`$ ai-eng install` — `docs/untitled.pen:522`).

**None of this voice is present in the current README files.** They read as conventional OSS marketing prose — adjectives where commands belong, no terminal-native framing, no mid-dot stat lines, no bracket-tag status references.

### 3.5 Stale counts in design assets

`docs/design.pen:15131` reads *"53 skills · 11 agentes · 4 IDEs"*. The 53-skills number is current; the **11 agentes** and **4 IDEs** are stale (current state: 9 first-class agents per `CLAUDE.md:76-80`, 6 enabled surfaces per `.ai-engineering/manifest.yml:28`).

`docs/untitled.pen:482` and `docs/untitled.pen:830` carry *"// 48 skills"* and *"// 48 skills · 10 agents"* — both stale.

These are design source files outside any automated test perimeter; this brief flags them for the asset-team handoff but does not modify them.

### 3.6 Rename touch surface

The exploratory `rg --hidden -n 'ai-repo-tidy'` snapshot found a broad rename surface (raw count depends on whether draft/state/generated caches are included). The spec phase must re-run the grep and update every non-historical hit. The categories:

- **Canonical `.claude/` source** (10 files including the skill directory itself): `.claude/skills/ai-repo-tidy/SKILL.md`, `.claude/skills/ai-commit/SKILL.md:3,116`, `.claude/skills/ai-resolve-conflicts/SKILL.md:3,106`, `.claude/skills/ai-autopilot/SKILL.md:88`, `.claude/skills/ai-pr/SKILL.md:99,144`, `.claude/skills/ai-pr/handlers/watch.md:22`, `.claude/skills/ai-simplify-sweep/SKILL.md:108`, `.claude/skills/ai-start/SKILL.md:124`, `.claude/skills/_shared/consolidate-spec.md:5,13,39`.
- **Root generated mirrors** (`.codex/`, `.gemini/`, `.github/`): each replicates the canonical pattern byte-equivalent. `scripts/sync_mirrors/core.py:60-67` regenerates these from `.claude/` — so the operator edits canonical, runs `ai-eng sync`, and root mirrors flow.
- **Installer-template provider surfaces** under `src/ai_engineering/templates/project/`: `.claude/`, `.codex/`, `.gemini/`, `.github/`, `.cursor/`, `.opencode/`, and `.agent/` outputs are generated by `scripts/sync_mirrors/core.py:1555-1817`. They ship to consumer projects and must be updated/verified in the same rename wave.
- **Python source** (4 files): `src/ai_engineering/config/framework_defaults.py:262` (the registry key `"ai-repo-tidy"`), `src/ai_engineering/validator/categories/file_existence.py:282,312,324` (user-facing messages).
- **Reference docs**: `.ai-engineering/reference/model-dispatch-policy.md:44`, `.ai-engineering/reference/surface-axioms.md:39`.
- **Session bootstrap scripts** (2 files × 2 instances): `.ai-engineering/scripts/session_bootstrap.py:1024,1040` and `src/ai_engineering/templates/.ai-engineering/scripts/session_bootstrap.py:1024,1040`.
- **Tests that pin the slug**: 10 unique files including `tests/unit/test_cleanup_history_rotation.py:19-22` (4 hardcoded path literals), `tests/unit/test_consolidate_spec_action.py:21,43`, `tests/architecture/test_naming_clarity.py:59` (the `_RENAMED_SKILLS` tuple).
- **State files** (NOT edited): `.ai-engineering/state/framework-events.ndjson` and `.ai-engineering/state/state.db` may contain historical occurrences; both are append-only/history-bearing and must not be rewritten for this rename.

### 3.7 Manifest count divergence in code comment

`src/ai_engineering/config/framework_defaults.py:249` has a comment claiming "48 entries"; the actual registry has 53 entries. Stale comment, not catching CI gates.

---

## 4. Architecture

### 4.1 Documentation surface hierarchy

```
                 ┌───────────────────────────────────────────┐
                 │  README.md (root, 120-line cap)            │
                 │  Hero · Install · Canonical chain · Links  │
                 └───────────────┬───────────────────────────┘
                                 │ next step
                                 ▼
                 ┌───────────────────────────────────────────┐
                 │  .ai-engineering/README.md (operator depth)│
                 │  Persistence · Skills · Agents · Runbooks  │
                 └───────────────┬───────────────────────────┘
                                 │ ships to consumer via installer
                                 ▼
                 ┌───────────────────────────────────────────┐
                 │  templates/.ai-engineering/README.md       │
                 │  Byte-identical mirror (sync-enforced)     │
                 └───────────────────────────────────────────┘

                 ┌───────────────────────────────────────────┐
                 │  team/README.md  (4-line placeholder)       │
                 └───────────────────────────────────────────┘

                 (CONSTITUTION.md, CLAUDE.md, AGENTS.md, GEMINI.md, copilot-instructions.md — already current; sanity-reviewed only)
```

### 4.2 Brand voice layer (textual only)

```
docs/design.pen ──┐
                  ├── extract ──► .ai-engineering/reference/brand-voice.md
docs/untitled.pen ┘                          │
                                             │ cited as voice authority
                                             ▼
                                    All README rewrites
                                    (and future doc edits)
```

The `brand-voice.md` reference becomes the authority. `/ai-docs`, `/ai-prose`, `/ai-marketing`, and `/ai-explain` all read it. The .pen files remain the design SoT (visual); `brand-voice.md` becomes the prose SoT (textual extraction). No image generation, no SVG inline.

### 4.3 Skill rename surface (hexagonal — the slug is a port label)

```
.claude/skills/ai-repo-tidy/        ──►  .claude/skills/ai-branch-cleanup/
.codex/skills/ai-repo-tidy/         ──►  .codex/skills/ai-branch-cleanup/
.gemini/skills/ai-repo-tidy/        ──►  .gemini/skills/ai-branch-cleanup/
.github/skills/ai-repo-tidy/        ──►  .github/skills/ai-branch-cleanup/
src/ai_engineering/templates/project/.cursor/skills/ai-repo-tidy/      ──►  .../ai-branch-cleanup/
src/ai_engineering/templates/project/.opencode/skills/ai-repo-tidy/    ──►  .../ai-branch-cleanup/
src/ai_engineering/templates/project/.agent/skills/ai-repo-tidy/       ──►  .../ai-branch-cleanup/
src/ai_engineering/templates/...                                        ──►  same rename
src/ai_engineering/config/...       ──►  registry key + comment fix
tests/...                           ──►  4 hardcoded literals + naming tuple
CHANGELOG.md                        ──►  [Unreleased] BREAKING entry
```

The skill code/body **does not change** — only the slug, the directory name, and string references. This is a textbook hexagonal-architecture move: rename a port label, leave the adapter and domain untouched.

Important distinction: `.cursor/`, `.opencode/`, and `.agent/` are not root dogfood directories in this repository today; they are install-template provider surfaces under `src/ai_engineering/templates/project/` (`scripts/sync_mirrors/core.py:81-94`, `scripts/sync_mirrors/core.py:1761-1817`).

### 4.4 Skill dispatch plan for the rewrite

Per operator decision, the rewrite uses four doc-authoring skills in their proper niches (per their actual capabilities, surfaced by ai-explore):

| Concern | Skill | Why |
|---------|-------|-----|
| Diff-aware structural README sync | `/ai-docs readme` | Handler `readme.md` is explicitly "Diff-aware README updates" (`.claude/skills/ai-docs/handlers/readme.md:5`); accepts `readme` argument; gate flag `documentation.auto_update.readme` in manifest. |
| Voice rules (active voice, no filler, audience-targeted) | `/ai-prose` (rules only) | `/ai-prose` is **NOT for READMEs** per its own SKILL.md, but its writing principles ("active voice, present tense, no filler") are the right ones to apply inside `/ai-docs readme`. |
| External-facing hook sentence framing | `/ai-marketing` (one targeted pass) | Public-tone hook sentence, SEO/social hooks. Not the executing skill — informs the framing of the hero. |
| ASCII diagrams + architectural explanation paragraphs | `/ai-explain` | Produces `file:line`-cited diagrams; the rewriter incorporates the diagrams into the README prose. |

`/ai-docs readme` is the executor. `/ai-prose`, `/ai-marketing`, `/ai-explain` contribute rules, framing, and diagrams respectively.

---

## 5. Evidence Catalog

| # | File:line | Evidence |
|---|-----------|----------|
| E1 | `README.md:23` | "Antigravity" listed in IDE list; not in `.ai-engineering/manifest.yml:28` |
| E2 | `.ai-engineering/manifest.yml:28` | `surfaces.enabled: [claude-code, github-copilot, gemini-cli, codex, opencode, cursor]` (no Antigravity) |
| E3 | `README.md:67-91` | "How AI Works Here" + attribution table — preserve voice |
| E4 | `tests/docs/test_links.py:203-228` | 120-line cap and structural invariants enforced |
| E5 | `tests/docs/test_links.py:229-231` | `GETTING_STARTED.md` must NOT exist at repo root |
| E6 | `.ai-engineering/README.md:5` | Dead link to `../GETTING_STARTED.md` |
| E7 | `src/ai_engineering/templates/.ai-engineering/README.md:5` | Same dead link in installer template |
| E8 | `.ai-engineering/README.md:257-292` | 12 "Slash Commands" listed; chain not framed canonically |
| E9 | `CLAUDE.md:47-64` | Canonical chain: `/ai-brainstorm → /ai-plan → /ai-build → /ai-pr` |
| E10 | `docs/design.pen:9` | Frame 01 "Logo & Wordmark" — design system root |
| E11 | `docs/design.pen:1796, 1853` | Typography: JetBrains Mono (primary) + Inter (secondary) |
| E12 | `docs/design.pen:722, 850` | Palette: `$primary-dark` (#0B1120), `$accent` (#00D4AA) |
| E13 | `docs/design.pen:3291, 3593, 3605` | Approved taglines |
| E14 | `docs/design.pen:3862-3911` | `[PASS]/[WARN]/[FAIL]` bracket-tag status grammar |
| E15 | `docs/untitled.pen:1517, 1944` | Code-comment headers + mid-dot stat line |
| E16 | `docs/untitled.pen:522` | Shell-prompt CTA pattern: `$ ai-eng install` |
| E17 | `docs/design.pen:15131` | Stale stat line "53 skills · 11 agentes · 4 IDEs" — handoff to asset team |
| E18 | `docs/untitled.pen:482` | Stale "// 48 skills" in poster |
| E19 | `.claude/skills/ai-repo-tidy/SKILL.md` | Canonical source to rename (16 internal self-refs) |
| E20 | `src/ai_engineering/config/framework_defaults.py:262` | Registry key `"ai-repo-tidy"` requires rename |
| E21 | `src/ai_engineering/config/framework_defaults.py:249` | Stale "48 entries" comment (registry has 53) |
| E22 | `src/ai_engineering/validator/categories/file_existence.py:282,312,324` | User-facing messages mentioning old slug |
| E23 | `tests/unit/test_cleanup_history_rotation.py:19-22` | 4 hardcoded path literals to update |
| E24 | `tests/architecture/test_naming_clarity.py:59` | `_RENAMED_SKILLS` tuple must change `"ai-repo-tidy"` to `"ai-branch-cleanup"` |
| E25 | `tests/unit/test_consolidate_spec_action.py:21,43` | Caller-list string + path literal |
| E26 | `.ai-engineering/reference/model-dispatch-policy.md:44` | Skill slug in reference doc |
| E27 | `.ai-engineering/reference/surface-axioms.md:39` | Skill slug in reference doc |
| E28 | `.ai-engineering/scripts/session_bootstrap.py:1024, 1040` | Two slug references in narrative output |
| E29 | `scripts/sync_mirrors/core.py` | Mirror regeneration mechanism; canonical-first edit pattern |
| E30 | `CHANGELOG.md:8-18` | `[Unreleased]` block — `### BREAKING` entry goes here |
| E31 | `CONSTITUTION.md:71-73` | "No backwards-compat shims" — justification for hard rename |
| E32 | `.claude/skills/ai-docs/SKILL.md:18-20` + `.claude/skills/ai-docs/handlers/readme.md:5` | `/ai-docs readme` is the right executor for diff-aware README sync |
| E33 | `.claude/skills/ai-prose/SKILL.md:32` | `/ai-prose` is explicitly NOT for READMEs — rules-only contribution |
| E34 | `docs/persistence-doctrine.md:97-116` | Tier 4 Markdown SoT; READMEs are Tier 4 |

---

## 6. Roadmap

The brief decomposes into **four waves** that can be executed in sequence by `/ai-build` (or wrapped by `/ai-autopilot` since the change is multi-concern).

### Wave 1 — Brand voice reference

1. Create `.ai-engineering/reference/brand-voice.md` extracting the voice rules from `docs/design.pen` and `docs/untitled.pen`. Source the lexicon, tagline templates, voice posture, lexicon prohibitions, code-comment header pattern, mid-dot stat line pattern, bracket-tag status grammar, em-dash subhead separator, and the `{ai} engineering` wordmark rule.
2. `/ai-explain` produces the ASCII diagram of the four-README hierarchy + the canonical chain (for embedding in the rewritten roots).
3. Acceptance: the reference doc cites `docs/design.pen` / `docs/untitled.pen` line numbers for every rule; passes `tests/docs/test_links.py` PII patterns at `tests/docs/test_links.py:79-86`.

### Wave 2 — README rewrite (the four targets)

1. **`README.md` (root)** — rewritten under the 120-line cap, opens with the approved tagline (`docs/design.pen:3291`), gives a one-line install command, lists the canonical chain, preserves the attribution table verbatim (`README.md:77-91`).
2. **`.ai-engineering/README.md`** — rewritten to describe the four-tier persistence model, the audited skill chain, the runbook system, and the active manifest counts. Replaces the dead `GETTING_STARTED.md` link with the Open Decision 3 outcome. Recommendation: inline Quick Start rather than another outbound link.
3. **`src/ai_engineering/templates/.ai-engineering/README.md`** — kept byte-identical to the live governance README. A sync mechanism (either a script or a documented manual mirror step) prevents future drift.
4. **`.ai-engineering/team/README.md`** — reviewed; kept at the existing 4-line shape unless reviewer-correctness finds an issue.

Each README is generated by `/ai-docs readme`, which reads `brand-voice.md` as its style authority and applies `/ai-prose` rules. The hero sentence and external-facing framing borrow patterns from `/ai-marketing`.

Acceptance: `tests/docs/test_links.py::test_readme_minimal` passes; `tests/docs/test_links.py::test_no_broken_links` passes; line count ≤ 120 at the root; no PII patterns (`tests/docs/test_links.py:79-86`).

### Wave 3 — Skill rename `/ai-repo-tidy → /ai-branch-cleanup`

1. Rename the canonical directory `.claude/skills/ai-repo-tidy/` to `.claude/skills/ai-branch-cleanup/`. Update the 16 internal self-references inside `SKILL.md`.
2. Update sibling skill cross-references in `.claude/skills/{ai-commit, ai-resolve-conflicts, ai-autopilot, ai-pr, ai-simplify-sweep, ai-start}/SKILL.md` and `.claude/skills/_shared/consolidate-spec.md`.
3. Update Python source: registry key in `src/ai_engineering/config/framework_defaults.py:262`, stale comment at `src/ai_engineering/config/framework_defaults.py:249`, user-facing messages in `src/ai_engineering/validator/categories/file_existence.py:282,312,324`.
4. Update reference docs: `.ai-engineering/reference/model-dispatch-policy.md:44`, `.ai-engineering/reference/surface-axioms.md:39`.
5. Update session bootstrap scripts: `.ai-engineering/scripts/session_bootstrap.py:1024,1040` and the templates twin.
6. Update template trees under `src/ai_engineering/templates/project/` — these do NOT flow through `ai-eng sync`; direct edits required.
7. Update tests: `tests/unit/test_cleanup_history_rotation.py:19-22` (4 literals), `tests/unit/test_consolidate_spec_action.py:21,43`, `tests/architecture/test_naming_clarity.py:59` (`_RENAMED_SKILLS` tuple), plus the 5 docstring-only test files surfaced by ai-explore.
8. Run `ai-eng sync` to regenerate root `.codex/`, `.gemini/`, `.github/` mirrors and installer-template provider surfaces from `.claude/`.
9. Update `CHANGELOG.md` `[Unreleased]` block with a `### BREAKING` entry: *"`/ai-repo-tidy` renamed to `/ai-branch-cleanup`. Update any external automation that invokes the old slug. No alias preserved (CONSTITUTION.md §3)."*
10. Acceptance: full test suite green; `ai-eng sync --check` reports zero drift; `rg -n 'ai-repo-tidy'` returns zero non-historical hits (state.ndjson and state.db historical records excluded).

### Wave 4 — Sanity review on canonical docs

1. Read `CONSTITUTION.md`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md` end to end.
2. Cross-check against current `.ai-engineering/manifest.yml`, current skill count (53), current agent count (9 first-class), current surfaces enabled (6).
3. If any divergence is found, surface it for operator decision — do NOT rewrite without explicit approval, per operator scope confirmation.

Acceptance: review report committed alongside Waves 1-3, or zero divergences found.

---

## 7. Definition of Done

The brief is "done" when:

1. **`README.md` (root)** opens with an approved tagline from `docs/design.pen`, is ≤ 120 lines, lists the canonical chain `/ai-brainstorm → /ai-plan → /ai-build → /ai-pr` (`CLAUDE.md:47-64`), declares the six enabled surfaces (`.ai-engineering/manifest.yml:28`), preserves the attribution table (`README.md:77-91`), and passes `tests/docs/test_links.py::test_readme_minimal`.
2. **`.ai-engineering/README.md`** has zero dead links, describes the four-tier persistence model (`docs/persistence-doctrine.md`), surfaces the canonical chain in the brand voice, and reads as one cohesive document.
3. **`templates/.ai-engineering/README.md`** is byte-identical to the live governance README. A sync mechanism (script or documented checklist step) is in place. `tests/unit/validator/conftest.py:324-325` continues to pass (validator mirror-sync check).
4. **`team/README.md`** remains the minimal 4-line placeholder or is updated with explicit operator approval.
5. `.ai-engineering/reference/brand-voice.md` exists, extracts the brand lexicon and voice rules from the .pen files, and is cited as the style authority by future doc edits.
6. **Skill `/ai-branch-cleanup` exists** under `.claude/skills/ai-branch-cleanup/`. All 387 references to the old slug have been updated. `rg -n 'ai-repo-tidy'` returns only historical hits in `state/framework-events.ndjson` and `state.db` (append-only state).
7. **Tests pass**: `tests/architecture/test_naming_clarity.py::_RENAMED_SKILLS` references `ai-branch-cleanup`; `tests/unit/test_cleanup_history_rotation.py` references the new paths; `tests/unit/test_consolidate_spec_action.py` references the new slug.
8. **`CHANGELOG.md`** `[Unreleased]` block carries a `### BREAKING` entry documenting the rename, citing the rationale (intent clarity), and noting CONSTITUTION.md §3 as the policy basis for hard rename.
9. **Mirror sync**: `ai-eng sync --check` reports zero drift across root `.codex/`, `.gemini/`, `.github/` surfaces and installer-template provider surfaces under `src/ai_engineering/templates/project/`.
10. **Brand voice consistency**: every rewritten README echoes the same lexicon (`{ai} engineering` wordmark in prose, mid-dot stat lines for compressed counts, bracket-tag `[PASS] / [WARN] / [FAIL]` status grammar, code-comment `//` section markers where ASCII permits, no exclamation points, imperative second-person voice).
11. **Test bar**: full `pytest -q` green on the rewrite branch. `ai-eng verify --full` green. `ai-eng check` green. No `# noqa`, `# nosec`, or `// @ts-ignore` markers introduced.
12. **PR shape**: single commit per wave (4 commits), Conventional Commits format (`docs(readme):` for README work; `refactor(skills)!:` plus `BREAKING CHANGE:` footer for the rename), no `--no-verify` invocations, PR description references this brief and the spec generated from `/ai-brainstorm`.

---

## 8. Quality Stamps

Principles applied (citing `.ai-engineering/reference/principles.md` anchors):

- **§10.1 KISS** — README at 120-line cap. One install command. Single canonical chain. Skill name (`/ai-branch-cleanup`) reveals intent. No marketing fluff, no exclamation points.
- **§10.2 YAGNI** — No deprecation shim for the rename. No alias period. No backwards-compat detection. The breaking change is documented and shipped.
- **§10.3 SOLID** — `/ai-docs`, `/ai-prose`, `/ai-marketing`, `/ai-explain` have single responsibilities; the rewrite respects them. The skill rename is a hexagonal port relabel — domain untouched.
- **§10.4 DRY** — `brand-voice.md` is the single source for voice rules. The templates README mirrors the live README via documented sync, not duplicate edits. The four mirrored canonical surfaces (AGENTS / CLAUDE / GEMINI / copilot-instructions) keep their existing sha256-equivalent flow.
- **§10.5 TDD** — `tests/docs/test_links.py` and `tests/architecture/test_naming_clarity.py` are run first; they fail; the rewrite makes them green. No rewrite ships without test green.
- **§10.6 SDD** — This brief precedes the spec. `/ai-brainstorm` consumes this brief to produce `spec.md`. `/ai-plan` produces `plan.md`. `/ai-build` executes. The four waves above correspond to plan milestones.
- **§10.7 Clean Code** — Naming reveals intent (`ai-branch-cleanup` over `ai-repo-tidy`). One commit per wave. No drive-by refactors. CHANGELOG documents the breakage as policy requires.
- **§10.8 Hexagonal Architecture** — The skill rename is a port label change; the adapter and domain logic are unchanged. The brand voice layer is a port that flows from `.pen` design SoT through `brand-voice.md` to all README adapters.

Contracts honoured:

- `CONSTITUTION.md:71-73` — hard rename, no shims, CHANGELOG documents the breakage.
- `CONSTITUTION.md §1` — no secrets, no PII, no machine paths.
- `tests/docs/test_links.py::test_readme_minimal` — 120-line root README cap, no skill-list tables, required links to AGENTS/CONSTITUTION/CHANGELOG/CONTRIBUTING, no `GETTING_STARTED.md`.
- Conventional Commits — `docs(readme): rewrite README surfaces` for content; `refactor(skills)!: rename ai-repo-tidy to ai-branch-cleanup` for the rename commit, with a `BREAKING CHANGE:` footer.
- `docs/persistence-doctrine.md` Tier 4 (Markdown SoT for narrative) — READMEs are operator-authored truth, machine-synced only via the documented mirror flow.

---

## 9. Open Decisions

The spec phase must resolve these. Each is parked here, not pre-decided, because they have material trade-offs.

1. **Templates README sync mechanism.** Three options: (a) a `scripts/sync_governance_readme.py` script that copies `.ai-engineering/README.md → src/ai_engineering/templates/.ai-engineering/README.md` and is invoked by `pre-commit`; (b) a CI test that asserts byte-equivalence and fails the build on drift; (c) a manual checklist item in the PR template. Trade-off: automation vs ceremony. **Recommendation: (b) CI test** — least machinery, highest signal. Implementer to confirm in spec.
2. **Stale-comment fix sequencing.** `src/ai_engineering/config/framework_defaults.py:249` says "48 entries"; the count is 53. Fix as part of Wave 3 (rename wave) or as part of a separate hygiene commit? **Recommendation: bundle into Wave 3** — same file, same touch surface, atomic.
3. **Dead link replacement target.** `.ai-engineering/README.md:5` currently links to `../GETTING_STARTED.md` (deleted). What replaces it? Options: `CLAUDE.md`, `AGENTS.md`, a new `Quick Start` section inside the same README, or a pointer to `/ai-start`. **Recommendation: inline Quick Start section** (3-5 lines under a `## Quick Start` heading) — keeps the operator in one file instead of fanning them out.
4. **Brand-voice rule about emoji.** The user has stated a global "no emoji" preference. Should `brand-voice.md` codify it as a hard rule (rejecting any future PR that introduces one), or as a soft guideline? **Recommendation: hard rule** — the design system uses bracket-tags and code-comment markers as the equivalent of emoji; explicit prohibition aligns with the brand voice and the team convention surfaced by ai-explore.
5. **CHANGELOG `BREAKING` placement and granularity.** One combined entry or two (README rewrite + rename)? **Recommendation: two entries** under the same `[Unreleased]` block — one `### BREAKING` for the rename (the only breaking change), one `### Changed` for the README rewrite (not breaking).
6. **Asset-team handoff.** The stale stat lines in `docs/design.pen:15131` and `docs/untitled.pen:482` are outside this brief's scope. Should the spec emit a separate work item / ticket for the asset team, or just note the drift in the rewrite commit message? **Recommendation: file an `/ai-issue` for the asset-team handoff** so it does not get forgotten; cross-reference in the commit body.
7. **Sanity-review output for canonical docs (Wave 4).** If divergences are found in `CONSTITUTION.md` / `CLAUDE.md` / `AGENTS.md` / `GEMINI.md`, do they ship in this PR or get spun off? **Recommendation: spin off** — operator explicitly scoped this brief to "README rewrite + rename"; rewriting canonical docs is outside the scope they confirmed.
8. **Brand voice for code blocks.** Should `brand-voice.md` declare a syntax-highlight preference (e.g., explicitly request `bash` over `sh` in fences, JSON over YAML when both work)? Material because consistent fences read more deliberate. **Recommendation: yes, codify** — the four READMEs end up touching install commands, manifest snippets, and chain examples; consistency matters.

---

## 10. Migration

### 10.1 Hard rename — no shims

Per `CONSTITUTION.md:71-73`, the framework forbids backwards-compatibility shims for renamed/deleted/migrated content. **No `/ai-repo-tidy` alias is preserved.** Anyone who has externally automated against the old slug will receive a `command not found`-equivalent error from their IDE, see the `CHANGELOG.md` entry, and update their automation.

Justification:

- Internal policy is decisive: `CONSTITUTION.md:71-73` requires hard rename,
  hard delete, hard migration, and CHANGELOG documentation for renamed content.
- The old slug is misleading; the skill's documented behavior is branch
  cleanup plus spec/runtime hygiene, not general repository tidying.
- Conventional Commits §3 specifies that breaking changes get the `!` token
  (`refactor(skills)!:` in the commit subject) and an uppercase
  `BREAKING CHANGE:` footer. Both are used here.
- External deprecation/removal precedents are non-blocking context only;
  `/ai-research` may attach URLs in the promoted spec if reviewers want them.

### 10.2 Operator migration path

Operators see one CHANGELOG entry and one minute of work:

```
$ /ai-repo-tidy
→ command not found

$ cat CHANGELOG.md | head -30
→ [Unreleased]
  ### BREAKING
  - /ai-repo-tidy renamed to /ai-branch-cleanup. ...

$ /ai-branch-cleanup
→ (same behavior as before)
```

Any external workflow scripts that invoke `/ai-repo-tidy` get a one-line `sed` replacement.

### 10.3 Mirror flow

`scripts/sync_mirrors/core.py` regenerates root `.codex/`, `.gemini/`, and `.github/` mirrors plus install-template provider surfaces from `.claude/` on each `ai-eng sync` invocation. The rename PR runs `ai-eng sync` after canonical edits and commits the regenerated mirrors atomically.

### 10.4 Templates flow

Template provider surfaces under `src/ai_engineering/templates/project/` are generated by `ai-eng sync` (`scripts/sync_mirrors/core.py:1555-1817`); any non-generated template references outside that pipeline require direct edits. The PR verifies both generated and direct template hits in the same commit.

### 10.5 Audit

A `framework_operation` audit event chains into `.ai-engineering/state/framework-events.ndjson` for traceability. `skill_renamed` is **not** an allowed top-level event kind in `tools/skill_domain/event_schema.py:37-70`, so the operation lives in `detail.operation` unless a later spec explicitly extends the schema:

```json
{"kind": "framework_operation", "component": "ai-branch-cleanup-rename",
 "detail": {"operation": "skill_renamed", "from": "ai-repo-tidy",
 "to": "ai-branch-cleanup", "policy_source": "CONSTITUTION.md:71-73",
 "spec": "<spec-id>"}}
```

---

## 11. Risks

| Likelihood × Impact | Risk | Mitigation |
|--------------------|------|------------|
| High × Low | `tests/docs/test_links.py::test_readme_minimal` fails if the rewrite violates its structural invariants (120-line cap; required links; no skill table; no `GETTING_STARTED.md` link). | Run the test FIRST. Rewrite TDD-style. Wave 2 step 0 is "run `pytest tests/docs/test_links.py -q` and capture the failure modes". |
| High × Medium | `tests/architecture/test_naming_clarity.py` fails immediately after directory rename because `_RENAMED_SKILLS` tuple still pins `"ai-repo-tidy"` as a required-to-exist directory. | Update the tuple in the SAME commit as the directory rename. Atomicity matters here. |
| High × Medium | `tests/unit/test_cleanup_history_rotation.py` fails because of 4 hardcoded path literals. | Update all 4 in the rename commit. The grep is exhaustive; ai-explore already surfaced exact line numbers. |
| Medium × Medium | Some `framework-events.ndjson` historical records contain `"ai-repo-tidy"` — must NOT be modified (append-only audit chain). | Wave 3 explicit non-touch list; verify with `git status` before commit. |
| Medium × Medium | The templates README drifts from the live README over time. | CI test (open decision 1) asserts byte-equivalence; fails the build on drift. |
| Medium × Low | `src/ai_engineering/config/framework_defaults.py:262` registry-key rename may break effective-manifest skill registry projection if any consumer relies on the old key in `.ai-engineering/manifest.yml`. | `src/ai_engineering/config/framework_defaults.py:425-430` injects default skill registry values when missing; validator coherence checks live under `src/ai_engineering/validator/categories/manifest_coherence.py:398-417` and mirror checks under `src/ai_engineering/validator/categories/mirror_sync.py:1037-1087`. Spec phase confirms no consumer-facing manifest override depends on the old key. |
| Medium × Low | The `EXCLUDED_PATH_FRAGMENTS` in `tests/docs/test_links.py:42-60` currently shields `.ai-engineering/` and `templates/` from broken-link walking — the dead `GETTING_STARTED.md` link has been latent. Removing the exclusion would catch the bug but also catch legitimate excluded content. | Out of scope: do not modify the walker exclusions in this brief. The rewrite fixes the dead link directly. |
| Low × Medium | Brand-voice rules in `brand-voice.md` could be misinterpreted by `/ai-docs` and produce voice drift. | Acceptance criterion requires reviewer-correctness to score brand-voice fidelity ≥ 90% on the rewritten READMEs (subjective gate; reviewer judgement). |
| Low × Medium | `docs/design.pen:15131` stale stat line stays out of date forever because nobody owns design asset updates. | Open decision 6: file `/ai-issue` for asset-team handoff. |
| Low × High | A user runs `/ai-branch-cleanup` on a branch with uncommitted work and loses it. | Out of scope — skill behaviour is unchanged. The skill already has safety guards; this brief preserves them. |
| Low × Low | Mirror sync emits unexpected diffs after directory rename (e.g., trailing newline differences). | `ai-eng sync --check` is the gate. Run it before commit; resolve any noise in the same commit. |
| Low × Low | An external clone has the old slug cached in a shell autocompletion file. | Documented in CHANGELOG; operator rebuilds completions. Not a CI concern. |

---

## 12. References

### Internal (this repo)

- `CONSTITUTION.md:71-73` — project identity rule forbids backwards-compat shims, justifying hard rename.
- `CLAUDE.md` — canonical AI-behaviour mirror; §11 declares the canonical chain.
- `.ai-engineering/manifest.yml` — manifest of enabled surfaces, skill registry, agent registry.
- `.ai-engineering/reference/principles.md` — §10.1 KISS through §10.8 Hexagonal Architecture anchors.
- `docs/persistence-doctrine.md` — Tier 4 Markdown SoT rule.
- `docs/design.pen` — five-board design system (Penpot v2.11).
- `docs/untitled.pen` — workshop poster set; most distilled brand voice.
- `tests/docs/test_links.py` — README structural gates.
- `tests/architecture/test_naming_clarity.py` — naming invariants.
- `scripts/sync_mirrors/core.py` — IDE mirror regeneration mechanism.
- Prior briefs: `cli-ux-overhaul-brief.md`, `dx-excellence-refactor-brief.md` (M2 MD Canon — predecessor work), `skills-agents-excellence-v2-brief.md`.

### External (suggested research checks, not delivery blockers)

The implementation can proceed from repo-local evidence alone. If `/ai-brainstorm` wants external support, `/ai-research` should rehydrate URLs and attach only the sources that directly influence acceptance criteria:

- Conventional Commits v1.0.0 §3 — breaking-change marker and `BREAKING CHANGE:` footer.
- Keep a Changelog + Semantic Versioning — CHANGELOG placement for breaking changes.
- Diátaxis — README as overview plus navigation surface, not exhaustive reference.
- Public README exemplars (`astral-sh/uv`, `oven-sh/bun`, `denoland/deno`) — concise hero, install one-liner, first-success snippet.
- Documentation style guides (GitLab, Cloudflare, Mailchimp) — active voice, imperative mood, plain language.
- Design-system documentation references (GitHub Primer, Supernova) — translating visual tokens into prose rules.

Do not carry uncited external claims into `spec.md`. Any external claim promoted from this list must include its URL and retrieval note in the spec.

---

## 13. Glossary

- **`{ai} engineering`** — the brand wordmark in prose. Braces are literal; "engineering" is the qualifier; the "ai" is INSIDE the braces. Never write `ai-engineering` in body voice; that form is reserved for the package name, command (`ai-eng`), and URLs.
- **`ai-eng`** — the CLI executable name. Always lowercase, always hyphenated.
- **Bracket-tag status grammar** — the `[PASS] / [WARN] / [FAIL] / [PENDING]` form used in prose to mirror the design system's status convention (`docs/design.pen:3862-3911`).
- **Canonical chain** — `/ai-brainstorm → /ai-plan → /ai-build → /ai-pr`. The single authorised spec-driven flow (`CLAUDE.md:47-64`).
- **Canonical mirror** — one of four byte-equivalent surfaces (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`) carrying identical AI-behaviour payload. Each IDE reads its own native path.
- **Code-comment header** — section labels prefixed with `//` (`// what's inside`, `// stack`). The brand's signature header pattern, sourced from `docs/untitled.pen`.
- **Hard rename** — a rename with no alias, no shim, no compatibility wrapper. CHANGELOG documents the breakage. CONSTITUTION.md §3 mandates this for the framework.
- **Mid-dot stat line** — feature counts compressed onto one line separated by `·` (U+00B7): *"53 skills · 9 agents · 6 surfaces · 1 governed flow"*. NEVER comma-separated for this idiom.
- **Mirror surface** — an IDE-specific generated copy of canonical content. Root mirrors are `.codex/`, `.gemini/`, and `.github/`; install-template provider surfaces additionally include `.cursor/`, `.opencode/`, and `.agent/`. Generation flows from `.claude/` via `scripts/sync_mirrors/core.py`.
- **Penpot file (`.pen`)** — Penpot v2.11 JSON design document. SoT for visual identity; read-only from doc rewriter's perspective (extract voice; do not edit).
- **Skill port label** — the slug under `.claude/skills/<slug>/`. Renaming the port label is a hexagonal-architecture move; adapter and domain (the skill behaviour) are untouched.
- **Tier 4 markdown** — per `docs/persistence-doctrine.md`, the SoT layer for narrative prose. READMEs are Tier 4; machine-synced via documented mechanisms only.
- **`{ai} engineering` brace wordmark** — the literal mark with braces in `$accent` (#00D4AA), "ai" in white/dark depending on substrate, "engineering" in 600-weight letter-spacing 1.

---

## 14. Acceptance — Checklist

- [ ] `.ai-engineering/reference/brand-voice.md` exists, cites `docs/design.pen` and `docs/untitled.pen` line numbers, declares lexicon prohibitions, codifies mid-dot stat line, bracket-tag status grammar, code-comment headers, em-dash subhead separator, and `{ai} engineering` wordmark rule.
- [ ] `README.md` (root) rewritten under the 120-line cap; opens with an approved tagline; gives an install one-liner; lists the canonical chain; declares the six enabled surfaces; preserves the "Standing on the shoulders of …" attribution table.
- [ ] `.ai-engineering/README.md` rewritten; zero dead links; replaces `GETTING_STARTED.md` link with the resolution from open decision 3.
- [ ] `src/ai_engineering/templates/.ai-engineering/README.md` byte-identical to live governance README; sync mechanism in place (open decision 1).
- [ ] `.ai-engineering/team/README.md` reviewed; kept at 4-line shape unless operator approves a rewrite.
- [ ] Skill directory `.claude/skills/ai-repo-tidy/` renamed to `.claude/skills/ai-branch-cleanup/`.
- [ ] All non-historical `ai-repo-tidy` references from a fresh `rg --hidden -n 'ai-repo-tidy'` run updated: canonical, root mirrors (via `ai-eng sync`), installer templates, Python source, reference docs, session bootstrap, tests.
- [ ] `rg --hidden -n 'ai-repo-tidy'` returns only historical hits in `.ai-engineering/state/framework-events.ndjson` and `.ai-engineering/state/state.db`.
- [ ] `src/ai_engineering/config/framework_defaults.py:249` comment updated to "53 entries" (fixed alongside the rename).
- [ ] `CHANGELOG.md` `[Unreleased]` block: one `### BREAKING` entry (rename) + one `### Changed` entry (README rewrite).
- [ ] `tests/docs/test_links.py::test_readme_minimal` passes.
- [ ] `tests/docs/test_links.py::test_no_broken_links` passes.
- [ ] `tests/architecture/test_naming_clarity.py` passes (`_RENAMED_SKILLS` updated).
- [ ] `tests/unit/test_cleanup_history_rotation.py` passes (4 path literals updated).
- [ ] `tests/unit/test_consolidate_spec_action.py` passes (caller list updated).
- [ ] `tests/unit/validator/conftest.py:324-325` validator mirror-sync check passes.
- [ ] `pytest -q` green on the rewrite branch.
- [ ] `ai-eng verify --full` green.
- [ ] `ai-eng sync --check` reports zero drift.
- [ ] No `# noqa`, `# nosec`, `// @ts-ignore`, or other suppression markers introduced.
- [ ] Commit shape: one commit per wave (4 commits). Wave 2 uses `docs(readme):`; Wave 3 uses `refactor(skills)!:` plus a `BREAKING CHANGE:` footer.
- [ ] PR body cross-references this brief and the spec generated by `/ai-brainstorm`.
- [ ] A `framework_operation` audit row with `detail.operation=skill_renamed` is chained into `.ai-engineering/state/framework-events.ndjson`.
- [ ] Wave 4 sanity review on canonical docs committed (report or zero-divergences confirmation).
- [ ] Open decisions 1-8 explicitly resolved in `spec.md` before `/ai-plan` runs.

---

*End of brief. Promote to spec via `/ai-brainstorm --consume readme-rewrite-and-branch-cleanup-rename-brief.md`.*
