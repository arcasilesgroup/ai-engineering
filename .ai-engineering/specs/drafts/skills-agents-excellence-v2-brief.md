---
title: "Skills + Agents Excellence Refactor v2 — Cohesive UX, Self-Describing Surfaces, No-HITL Build, Auto-Spec Gate, Lean Mirrors"
status: draft
audience: /ai-brainstorm
predecessor_brief: skills-agents-excellence-refactor.md  # spec-129 (superseded — different scope)
branch: spec-128/context-overrides-refactor
pr: 509
pr_url: https://github.com/arcasilesgroup/ai-engineering/pull/509
length_estimate: "~850 lines"
authoring_style: "Staff Principal Architect IQ-200 — long-horizon, hexagonal, fail-loud, evidence-anchored"
principles_required: [KISS, YAGNI, DRY, SOLID, SDD, TDD, clean-code, hexagonal]
delivery_mode: "Single-branch continuation of PR 509 / hard-rename / no-shim / Conventional Commits"
skill_creator_reference: "claude-plugins-official/skill-creator (Anthropic) — frontmatter contract, eval workflow, grader+comparator+analyzer triumvirate"
mantra: "A first-time engineer types `/ai-` and the roster reads itself. Build never asks twice. Mirrors fit in one screen of tokens."
---

> **READ FIRST.** This brief is a structured intake for `/ai-brainstorm`. It captures owner feedback gathered in-session against the live HEAD of `spec-128/context-overrides-refactor` (PR 509). Every claim carries a `file:line` citation. Every milestone names the §10.x principle it advances. No implementation begins until this brief is promoted to `spec-NNN` and approved.
>
> **Scope discipline.** This is a refactor of **excellence**, not of survival. The repo is already healthy (governance + security + quality MEJORARON vs `v0.5.0` — see §3.4). Every change here exists because the experience is **opaque to a first-time user**, the **chain is interrupted by HITL friction**, or the **roster contains orphans** (agents without skills, skills without producers). KISS is the test: if a beginner cannot deduce the right skill from its name in 5 seconds, the name is wrong.

---

## 0. North Star

The picture that stays on the wall:

> **A first-time engineer opens Claude Code, types `/ai-`, and the surface explains itself. Every skill name says what it does. Every agent has a discoverable entry. The chain `/ai-spec-draft → /ai-brainstorm → /ai-plan → /ai-build → /ai-pr` is a single line of authoring. `/ai-build` runs unattended after approval — fast, governed, and fail-loud. Secrets never leak upstream because `ai-engineering-issue` redacts before submitting. Mirrors load in under 2k tokens at session start. The framework wears KISS, YAGNI, DRY, SOLID, SDD, TDD, clean code, and hexagonal architecture as visible craftsmanship — not as paperwork.**

This is the photo. Every milestone in §6 advances at least one pixel of it. Every Open Decision in §10 lives because the photo is not yet developed.

---

## 1. Executive Summary (one screen)

**Seven deltas land in PR 509:**

1. **Two new issue skills** close the work-item creation gap.
   - `/ai-issue` — create work-item on the user's board (GitHub Projects v2 / ADO) reusing `manifest.yml work_items` config that `/ai-board discover` already writes.
   - `/ai-engineering-issue` — sanitize + submit upstream bug report to `arcasilesgroup/ai-engineering/issues`. Mandatory PII/path/secret/state-redaction gate; human-confirmation before `gh issue create`.
2. **`/ai-build` no-HITL contract** mirrors `/ai-autopilot` for single-concern specs. Approved → unattended → fail-loud blockers → exit 78 governance halt. Velocity AND quality, governed by Constitution §13.5 single-round quality loop.
3. **`/ai-spec-draft` skill** as a canonical producer of `.ai-engineering/specs/drafts/<topic>-brief.md` artifacts. Today five drafts exist with no producer skill — research → structured brief → handoff to `/ai-brainstorm`.
4. **Mirror diet — 73% token reduction.** Move §1-9 prose, §10 Engineering Principles, §14 Mirror Authoring Contract, §15 IDE-Extras Escape Hatch, §16 Surface Axioms out of the four canonical mirrors and into `docs/`. Save ~3,900 tokens per Claude Code session bootstrap.
5. **Auto-spec gate in `/ai-brainstorm`.** Pre-check signals (file count, LOC, cross-module touch, public-API / state-schema / new-dep / security triggers) decide `requires_spec → bool` BEFORE interrogation. Trivial changes (typo, mechanical rename, single-line) → condensed-spec auto-approve. Regulated mode tightens thresholds.
6. **Naming refactor** — 11 rename candidates (`ai-gtm`, `ai-eval`, `ai-constitution`, `ai-guide`, `ai-observe`, `ai-create`, `ai-cleanup`, `ai-visual`, `ai-write`, `ai-prompt`, `ai-guard`) plus prefix consistency on the verifier-* family (`verify-deterministic` → `verifier-deterministic`) plus separation of lifecycle-misplaced reviewer-* nodes (`reviewer-context`, `reviewer-validator`).
7. **Skill-creator (Anthropic) adoption** as the governance standard for all new and modified skills: frontmatter contract, ≤500-line body with `references/` overflow, imperative voice, `evals/evals.json` with grader+comparator+analyzer subagents, blind A/B comparison, no `nosec`/`NOSONAR`, packaging artifact `.skill`.

**Scope:** single branch `spec-128/context-overrides-refactor`, continuation of PR 509. No new branches, no force-push, hard-rename per Constitution §13.3, Conventional Commits per §13.6.

**Quality stamp at delivery:** every milestone passes Constitution §10.x anchor + `tests/architecture/test_surface_parity.py` + `tests/architecture/test_layer_isolation.py` + new `tests/architecture/test_skill_agent_cohesion.py` + new `tests/unit/skills/test_brainstorm_auto_spec_gate.py`.

---

## 2. Scope Boundary

### In scope (this brief / this PR)

| Item | Reason |
|------|--------|
| Two new skills: `/ai-issue`, `/ai-engineering-issue` | Gap real (B12, B13 — see §5) |
| One new skill: `/ai-spec-draft` | Gap real (B14) |
| `/ai-build --no-hitl` mode contract + tests | Owner feedback (B15) |
| `/ai-brainstorm` auto-spec-gate handler + tests | Owner feedback (B16) |
| Mirror diet (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `copilot-instructions.md`) | Owner feedback (B17), DRY §10.4, KISS §10.1 |
| Naming refactor (11 renames + 2 prefix consistency fixes) | First-impression UX (B5, B20), Clean Code §10.7 |
| Surface orphan agents `ai-guard`, `ai-simplify` as `/ai-guard`, `/ai-simplify` skills | Cohesion (B1, B2), SOLID §10.3 ISP |
| Sanitizer hardening (`_shared/redactor.py`) — 7 vectors | Security (B19) |
| Skill-creator standard adoption (frontmatter, evals, ≤500 lines) | Owner explicit ask (M7) |
| `tests/architecture/test_skill_agent_cohesion.py` (new) | TDD §10.5 + enforce SOLID §10.3 |
| CHANGELOG row per rename + `BREAKING CHANGES` section | Constitution §13.3 + §13.6 |
| Auto-spec-gate knob in `.ai-engineering/manifest.yml` | YAGNI §10.2 — opt-out for regulated mode |
| Suppression-drift resolution (§13.2 amend OR F403 refactor) | Constitution drift cleanup (B18) |

### Out of scope (deferred to future briefs)

| Item | Why deferred |
|------|--------------|
| Fusing 5 creative skills (`ai-animation`, `ai-visual`, `ai-design`, `ai-media`, `ai-video-editing`, `ai-slides`) into a creative roster | Subjective UX call; needs separate creative-track brief |
| `ai-research` ↔ `ai-explore` rename | Both names already self-describing once disambiguated in description; rename adds risk without proportionate reward |
| Eval corpora for ALL 48 existing skills | Excessive scope; skill-creator standard applied prospectively to changed skills only |
| Replace `ai-create` with anthropic-skill-creator dispatch entirely | Open Decision D6 — depends on how skill-creator integrates with `/ai-create` UX |
| Rename `ai-research` → `ai-research-external` or similar | Hold for second-pass naming brief |
| Multi-language skill bodies (i18n) | Constitution explicitly English-only for committed files |

---

## 3. Diagnostic Snapshot — Current State

### 3.1 Inventory

- **48 skills** under `.claude/skills/ai-*/` (manifest.yml canonical count)
- **9 first-class agents** under `.claude/agents/ai-*.md` (manifest.yml `agents.registry`)
- **15 sub-agents** (10 `reviewer-*` + 4 `verifier-*` + 1 `verify-deterministic`) — internal dispatch only
- **5 drafts** under `.ai-engineering/specs/drafts/` (4 already promoted to spec-128/129/131/132/133; 1 deferred placeholder)
- **6 specs shipped** since v0.5.0 (spec-126 through spec-133)

### 3.2 Skill ↔ Agent Cohesion Gaps

| Surface | First-class agent? | Slash-command skill? | Status |
|---------|--------------------|----------------------|--------|
| autopilot | ✅ | ✅ | aligned |
| build | ✅ | ✅ | aligned |
| explore | ✅ | ✅ | aligned |
| plan | ✅ | ✅ | aligned |
| review | ✅ | ✅ | aligned |
| verify | ✅ | ✅ | aligned |
| guide | ✅ | ✅ | aligned |
| **guard** | ✅ (`.claude/agents/ai-guard.md`, ~4.4 KB) | ❌ **ORPHAN** | called by `/ai-build` + `/ai-autopilot` but undiscoverable from `/` menu |
| **simplify** | ✅ (`.claude/agents/ai-simplify.md`, ~4.1 KB) | ❌ **ORPHAN** (only `/ai-simplify-sweep` scheduler exists) | no direct invocation path |

### 3.3 IDE Mirror Weight

| File | Bytes | Lines | Tokens (est) | Notes |
|------|-------|-------|--------------|-------|
| `CLAUDE.md` | 21,512 | 496 | ~5,378 | Heaviest, +Hot-Path IDE-extras (~2.7 KB) |
| `GEMINI.md` | 19,825 | 457 | ~4,956 | +Hooks Wiring extras (~1.2 KB) |
| `.github/copilot-instructions.md` | 19,528 | 448 | ~4,882 | +Copilot Hooks extras (~0.9 KB) |
| `AGENTS.md` | 18,793 | 428 | ~4,698 | Base mirror, no extras |
| `CONSTITUTION.md` | 9,247 | 197 | ~2,312 | Project identity SSOT (load-bearing — do NOT touch) |
| **Canonical payload duplicated 4×** | 18,621 (×4 = ~74 KB) | — | — | sha256 `b188d03e119c4b25` — identical across mirrors |
| **Per-session bootstrap cost** (Claude Code) | — | — | **~7,690** | CLAUDE.md + CONSTITUTION |

**Trim opportunities** (target: ~62 KB disk reduction, ~3,905 tokens/session saved):
- §10 Engineering Principles (~5.8 KB × 4) → `docs/principles.md`
- §14 Strict Content Contracts (~4.2 KB × 4) → `docs/mirror-authoring.md`
- §16 Surface Axioms (~2.2 KB × 4) → `docs/surface-axioms.md`
- §15 IDE-Extras Escape Hatch (~0.6 KB × 4) → header comment in `tools/skill_lint/checks/md_mirror.py`
- §1-9 prose (~2.1 KB) → compressed 9-row table inline
- §13 Hard Rules — deduplicate against `CONSTITUTION.md §Prohibitions` (~0.7 KB)
- §12 Surface Index prose → tighten to Source-of-Truth table only

### 3.4 Governance + Security + Quality vs v0.5.0 — VERDICT: MEJORARON

| Dimension | v0.5.0 | HEAD | Δ |
|-----------|--------|------|----|
| Hook events wired | 5 | **11** | +6 (full canonical set) |
| Hook scripts | 41 | **74** | +80% |
| Hook integrity (sha256-pinned) | absent | **enforce mode** | new |
| Tests (`tests/**.py`) | 277 | **485** | +75% |
| Architecture tests | 0 | **4** | new (hexagonal, layer-isolation, surface-parity, template-tree) |
| Source files (`src/**.py`) | 187 | **288** | +54% |
| Decisions store | `decision-store.json` (41) | `state.db` STRICT + FTS5 (**116**) | +183% |
| Audit chain | absent | **99,502 events + 119,040 ndjson lines** | new |
| `risk_acceptances` + `gate_findings` + `hooks_integrity` tables | absent | present | new |
| First-class agents | 26 (overinflated registry) | **9** | −17 consolidation per D-133 |
| `nosec` / `NOSONAR` (real security suppressions) | 0 | **0** | unchanged — clean |

**Single asterisk:** code suppressions (`# noqa`, `pragma: no cover`) grew 43 → 143 in `src/`. **80** of those are in production code. Triage: all are hexagonal re-exports (F403, §10.8 architectural carve-out) or fail-open observability (`pragma: no cover -- defensive`). **Zero `nosec`/`NOSONAR`.** This is text-drift vs Constitution §13.2 ("No suppression"), NOT a regression. Open Decision D4 (§10) resolves: amend §13.2 with documented carve-out OR refactor F403 re-exports to explicit names.

**Bottom line:** the framework moved from "intent + JSON files" (v0.5.0) to "enforceable substrate + 11-event hook lifecycle + STRICT DB + audited ndjson + Surface Axioms" (HEAD). PR 509 has NOT regressed governance. It has hardened it. Refactor v2 inherits a healthy floor.

### 3.5 Naming Drift Inventory (current)

| Skill | Issue | Severity |
|-------|-------|----------|
| `ai-gtm` | Acronym; opaque to newcomers | MEDIUM |
| `ai-eval` | Jargon; reads as "AI evaluation" not "feature reliability eval" | MEDIUM |
| `ai-constitution` | Noun without verb; reads as "a document" not "an action" | LOW |
| `ai-guide` | Generic; collides conceptually with `ai-explore` for "explain code" | MEDIUM |
| `ai-observe` | Overlaps `ai-learn` and `ai-note` in name-space | MEDIUM |
| `ai-create` | "Create what?" — too generic | MEDIUM |
| `ai-cleanup` | Implies code cleanup; actually does git/repo hygiene | MEDIUM |
| `ai-visual` | Boundary vs `ai-design` non-obvious | LOW |
| `ai-write` | Overlaps `ai-docs` and `ai-gtm` for prose | MEDIUM |
| `ai-prompt` | Ambiguous: write a prompt or optimize a prompt? | LOW |
| `ai-guard` | **Name-behavior mismatch** — "guard" implies blocking, description says advisory | HIGH |
| `verify-deterministic` (sub-agent) | Breaks `verifier-*` prefix convention | MEDIUM |
| `reviewer-context` / `reviewer-validator` | Lifecycle-misplaced in `reviewer-*` family (pre/post processors, not specialists) | MEDIUM |

---

## 4. Final Architecture — Target State

### 4.1 Canonical Chain v2

```
/ai-spec-draft     →   /ai-brainstorm   →   /ai-plan   →   /ai-build   →   /ai-pr
  (research)         (gate + spec)        (plan)       (impl + verify)    (commit + review + ship)
       │                    │                  │              │                 │
       ▼                    ▼                  ▼              ▼                 ▼
  drafts/<topic>      spec.md +          plan.md         changes        PR + CHANGELOG
                      decisions          + tasks         + tests        + governance
                                                        + gates
                                              ┌──── --hitl (default current)
                                              │
                                              └──── --no-hitl (new — single-concern unattended)

       (≥3 concerns)      /ai-autopilot wraps the chain (current behavior unchanged)
```

### 4.2 Skill ↔ Agent Cohesion Map (target)

```
SKILL                          AGENT                       MODEL    NEW?
─────────────────────────      ─────────────────────       ──────   ────
/ai-spec-draft           ←→    ai-spec-draft (Sonnet)      sonnet   YES
/ai-brainstorm           ←→    (no agent — pure orchestrator with auto-spec gate)
/ai-plan                 ←→    ai-plan                     opus     existing
/ai-build (HITL + no-HITL) ←→  ai-build                    opus     existing — contract change
/ai-pr                   ←→    (orchestrator; calls ai-review, ai-docs, ai-board)
/ai-autopilot            ←→    ai-autopilot                opus     existing
/ai-verify               ←→    ai-verify (+ verifier-*)    opus     existing — sub-agent rename
/ai-review               ←→    ai-review (+ reviewer-*)    opus     existing — sub-agent reorg
/ai-explore              ←→    ai-explore                  sonnet   existing
/ai-guide                ←→    ai-guide                    sonnet   existing — rename candidate D2
/ai-guard                ←→    ai-guard                    sonnet   YES — surface orphan
/ai-simplify             ←→    ai-simplify                 sonnet   YES — surface orphan
/ai-issue                ←→    (no agent — direct CLI/MCP call to gh / az)              YES
/ai-engineering-issue    ←→    ai-engineering-issue (sanitize-and-submit)  sonnet  YES
```

### 4.3 Issue Surface Disambiguation

```
                      DESTINATION                      CONFIDENTIALITY
                      ───────────                      ───────────────
/ai-issue              user's board                    normal (private project context)
                       (GitHub Projects v2 / ADO,
                        reads manifest.yml work_items)

/ai-engineering-issue  arcasilesgroup/ai-engineering   HIGH — mandatory redactor gate
                       upstream OSS repo               (secrets, paths, emails,
                                                        usernames, hostnames,
                                                        state.db content)
```

The word `engineering` in the slug signals destination: **the framework**, not **my project**. A first-time user reading the description distinguishes by the noun.

### 4.4 Auto-Spec Gate (in `/ai-brainstorm`)

```python
def requires_spec(signals) -> tuple[bool, str]:
    # Hard triggers — any single one forces spec
    for trigger in [
        "touches_public_api",
        "touches_state_or_schema",   # DB migration, manifest, state.db
        "introduces_new_dep",
        "touches_security_surface",  # hooks, secrets, gates, redactor
    ]:
        if signals.get(trigger):
            return True, trigger

    # Cross-module — touching ≥2 top-level packages is implicit contract
    if signals["cross_module_count"] >= cfg.cross_module_threshold:  # default 2
        return True, "cross_module"

    # Cumulative volume — files OR loc
    if signals["files_changed"] >= cfg.files_threshold:  # default 3
        return True, "files_volume"
    if signals["loc_added"] >= cfg.loc_threshold:         # default 50
        return True, "loc_volume"

    # Type-based fast bypass
    if signals["commit_type"] in cfg.bypass_types:        # default {chore, docs, style}
        if not signals.get("touches_public_api"):
            return False, "trivial_type"
    if signals.get("is_pure_rename_or_format"):
        return False, "mechanical"

    return False, "condensed_ok"
```

Knob block in `.ai-engineering/manifest.yml`:

```yaml
brainstorm:
  auto_spec_gate:
    enabled: true
    thresholds:
      files: 3
      loc: 50
      cross_module: 2
    hard_triggers: [public_api, state_or_schema, new_dependency, security_surface]
    bypass_types: [chore, docs, style]
    condensed_auto_approve: true
    regulated_mode: false   # banking/healthcare: tighter thresholds
```

### 4.5 Build Mode Contract

```
/ai-build (default HITL)         /ai-build --no-hitl              /ai-autopilot
────────────────────────         ─────────────────────             ─────────────
Approved plan → impl             Approved plan → impl             ≥3 concerns
Stops + re-plans on snag         Fail-loud on blocker             Decomposes spec
Asks user on ambiguity           Exit 78 governance halt          Builds DAG
                                 No auto-retry                    Wave-based impl
Single concern                   Single concern                   Multi-concern
                                 Velocity AND quality             Quality convergence (3 rounds)
                                 governed by §13.5                governed by §13.5
```

`/ai-build --no-hitl` is NOT silent failure. Blockers escalate via exit code 78 + structured audit row in `state.db gate_findings`. Owner reads `ai-eng audit replay --session <id>` to triage.

### 4.6 Sanitizer (for `/ai-engineering-issue`)

Located at `src/ai_engineering/_shared/redactor.py` (new). Imports existing `_SECRET_RE` from `state/instincts.py` and `state/observability.py` (DRY §10.4 — no duplication). Adds 6 new regex patterns:

```python
PATH_USERHOME       = re.compile(r"/Users/[^/\s]+(?=/)")              → "$HOME"
PATH_REPO_PRIVATE   = re.compile(r"/private/[^\s]+")                  → "<private-path>"
EMAIL               = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")         → "<redacted@email>"
GH_TOKEN            = re.compile(r"\bgh[psouar]_[A-Za-z0-9_]{36,255}\b") → "<github-token>"
USERNAME_CLI        = re.compile(r"(?i)\b(whoami|hostname)=\S+")      → "<username/hostname>"
STATE_DB_BLOB       = re.compile(r"(?m)^.*state\.db.*sql.*$")         → "<state.db payload elided>"
```

Mandatory **human-confirmation gate** before `gh issue create` — preview body in screen-fit caveman summary; user types `confirm` to submit.

---

## 5. Evidence Catalog — Issues by ID

Format: `B<N> — <title> (SEVERITY) — <citation>`

- **B1 — Orphan agent `ai-guard` (no slash skill)** (HIGH) — `.claude/agents/ai-guard.md:1-20`; called by `/ai-build` and `/ai-autopilot` but no `/ai-guard` in `/` menu → undiscoverable.
- **B2 — Orphan agent `ai-simplify` (no slash skill)** (HIGH) — `.claude/agents/ai-simplify.md:1-20`; only `/ai-simplify-sweep` (scheduler) exists → direct invocation impossible without insider knowledge.
- **B3 — `verify-deterministic` breaks `verifier-*` family prefix** (MEDIUM) — `.claude/agents/verify-deterministic.md` vs `.claude/agents/verifier-{architecture,feature,governance}.md`; cognitive load on directory readers.
- **B4 — `reviewer-context` and `reviewer-validator` misplaced in `reviewer-*` family** (MEDIUM) — `.claude/agents/reviewer-context.md` (pre-processor), `.claude/agents/reviewer-validator.md` (post-processor adversary) sit in a specialist-named family but are lifecycle artefacts, not specialists.
- **B5 — `ai-guard` name-behavior mismatch** (HIGH) — `.claude/agents/ai-guard.md`: name implies blocking enforcement; description says "Always advisory, NEVER blocks." First-time user expectation broken.
- **B6 — Opaque skill names (`ai-gtm`, `ai-eval`, `ai-constitution`)** (MEDIUM) — `.claude/skills/ai-{gtm,eval,constitution}/SKILL.md` frontmatter `description`: requires reading body to understand domain.
- **B7 — `/ai-code` ↔ `/ai-build` entry-point confusion** (HIGH) — `.claude/skills/ai-code/SKILL.md:5` vs `.claude/skills/ai-build/SKILL.md:5`: both trigger on "implement this"; a beginner cannot infer which is canonical (answer: `/ai-build` is, per CLAUDE.md §11).
- **B8 — `/ai-explore` ↔ `/ai-guide` overlap** (MEDIUM) — both read code, both explain; boundary (structural research vs onboarding teaching) lives only in descriptions.
- **B9 — `/ai-research` ↔ `/ai-explore` confusion vector** (MEDIUM) — shared "research" mental model; correct off-ramp documented (external sources vs codebase-internal) but beginner invokes wrong one consistently.
- **B10 — `/ai-write` ↔ `/ai-docs` ↔ `/ai-gtm` prose overlap** (MEDIUM) — three skills carry "write a blog post" in trigger surface; correct routing requires reading "Not for" disclaimers.
- **B11 — `/ai-observe` ↔ `/ai-learn` ↔ `/ai-note` three-way persistence overlap** (MEDIUM) — all three persist session findings, with subtle boundaries (passive / post-PR / user-driven) not communicated by names.
- **B12 — `ai-board` exposes `sync` and `discover` but NO `create` subcommand** (HIGH) — `.claude/skills/ai-board/{sync,discover}.md`; work-item creation gap → forces ad-hoc `gh issue create` calls today.
- **B13 — No skill for upstream OSS bug report** (HIGH) — `arcasilesgroup/ai-engineering/issues` is the documented bug channel (`CODE_OF_CONDUCT.md`); no skill produces sanitized issue bodies → users either skip filing or risk PII leak.
- **B14 — No skill produces `specs/drafts/<topic>-brief.md` artifacts** (HIGH) — `.ai-engineering/specs/drafts/` has 5 files (4 already promoted to specs); the producer is undocumented chat or manual writing. No `/ai-spec-draft`.
- **B15 — `/ai-build` always HITL — no `--no-hitl` single-concern contract** (HIGH) — `.claude/skills/ai-build/SKILL.md`: stops + re-plans on snag; `/ai-autopilot` only kicks in for ≥3 concerns. Single-concern unattended path missing.
- **B16 — `/ai-brainstorm` forces spec on every change, no auto-gate** (MEDIUM) — `.claude/skills/ai-brainstorm/SKILL.md:48-51`: heuristic "< 3 file changes" runs AFTER interrogation, single-signal (file count), not configurable, no condensed-spec auto-approve path.
- **B17 — Mirror weight: ~5,378 tokens/session in `CLAUDE.md`** (HIGH) — 100 sessions/month ≈ 770k tokens preamble; §10 (5.8 KB), §14 (4.2 KB), §16 (2.2 KB) duplicated 4× in mirrors → ~62 KB redundant disk.
- **B18 — Suppression drift (43 → 143)** (LOW) — `src/ai_engineering/`: F403 hex-arch re-exports + fail-open observability `pragma: no cover`; zero `nosec`/`NOSONAR`. Text-drift vs Constitution §13.2 absolute prohibition.
- **B19 — Sanitizer covers only secrets** (HIGH for new `ai-engineering-issue` work) — `src/ai_engineering/state/instincts.py:28` `_SECRET_RE` + `state/observability.py:66`: cover api_key/token/secret/password/authorization/credentials/auth; missing paths/emails/usernames/hostnames/GH-tokens/state.db content.
- **B20 — 11 naming candidates (see §3.5)** (MEDIUM) — opaque, overlapping, ambiguous; collected for hard-rename pass per Constitution §13.3.
- **B21 — Inconsistent "auto-invoked by" annotations** (LOW) — `.claude/skills/ai-docs`, `ai-board`, `ai-review` are auto-invoked by `/ai-pr` but the annotation is inconsistent across descriptions; hampers traceability.

---

## 6. Roadmap — 9 Milestones

Each milestone names its principle anchor(s), the **Why**, **What**, **Done when**, and **Tests** that turn RED → GREEN.

### M1 · Surface the two issue skills [§10.1 KISS · §10.2 YAGNI · §10.4 DRY · §10.6 SDD]

**Why.** Two gaps real (B12, B13). Reusable primitives already exist (`_SECRET_RE`, `ISSUE_TEMPLATE/*.yml`, `manifest.yml work_items`). KISS says: bind them with thin skills.

**What.**
- Create `.claude/skills/ai-issue/SKILL.md`. Reads `manifest.yml work_items` (already populated by `/ai-board discover`). Routes by `provider`: `github` → `gh issue create` + `gh project item-add`; `azure_devops` → `az boards work-item create`.
- Create `.claude/skills/ai-engineering-issue/SKILL.md`. Captures context (stacktrace, command, output, version, IDE, recent ndjson events) → invokes `_shared/redactor.py` (M9) → renders body using `ISSUE_TEMPLATE/bug.yml` contract → human-confirms preview → `gh issue create --repo arcasilesgroup/ai-engineering`.
- Optional: add `create` subcommand to `/ai-board` (Open Decision D3).
- Save sanitized copy to `.ai-engineering/support/upstream-reports/{date}-{slug}.md`.

**Done when.**
- [ ] `/ai-issue` creates a work-item on a configured board (test backend: GitHub Projects v2 fixture).
- [ ] `/ai-engineering-issue` produces a sanitized body that passes assertion `body NOT MATCH /Users/` AND `body NOT MATCH _SECRET_RE` AND `body NOT MATCH gh[psouar]_`.
- [ ] Both skills follow skill-creator contract (frontmatter ≤100 words, body ≤500 lines, evals/evals.json).
- [ ] `tests/unit/skills/test_ai_issue.py` + `test_ai_engineering_issue.py` GREEN with 6 scenarios each.

### M2 · Build autonomy contract `/ai-build --no-hitl` [§10.3 SOLID-SRP · §13.5 single-round]

**Why.** Owner feedback (B15): "once spec and plan exist, build should not ask me anything until done — like autopilot, but for single-concern specs." Velocity AND quality, no degradation.

**What.**
- Add `--no-hitl` flag to `/ai-build` skill workflow.
- When set: build agent dispatches per plan task, runs TDD self-validation per task, never asks user. Blockers → exit 78 + `state.db gate_findings` row + audit row in `framework-events.ndjson`. No auto-retry.
- Reuse `/ai-autopilot` Phase 5 final-quality-loop machinery (single round, fail-loud) — DRY §10.4. Do not duplicate.
- Default behavior unchanged (HITL). Flag is opt-in (YAGNI §10.2 — no new default until adoption signal).

**Done when.**
- [ ] `/ai-build --no-hitl` runs end-to-end on `tests/fixtures/spec-noop/` without user prompts.
- [ ] On simulated blocker (`tests/fixtures/spec-fail/`): exits 78, writes `gate_findings` row, never retries.
- [ ] `tests/unit/skills/test_ai_build_no_hitl.py` GREEN with 4 scenarios (happy / blocker-on-test / blocker-on-lint / blocker-on-governance).
- [ ] Documentation in skill body cites §13.5 + escalation contract.

### M3 · `/ai-spec-draft` skill [§10.6 SDD · §10.5 TDD]

**Why.** Gap real (B14). Five existing drafts (cli-ux-cross-ide-rearch-brief, cli-ux-overhaul-brief, dx-excellence-refactor-brief, skills-agents-excellence-refactor, plus this v2 brief) demonstrate the artefact convention but no canonical producer.

**What.**
- New `.claude/skills/ai-spec-draft/SKILL.md`.
- Workflow: (1) interview owner on intent; (2) dispatch `ai-explore` + `ai-research` in parallel to gather evidence; (3) structure brief using the 14-section canonical layout (this brief is the reference template); (4) write to `.ai-engineering/specs/drafts/<topic>-brief.md`; (5) cite every claim with `file:line`; (6) emit handoff token for `/ai-brainstorm`.
- Body ≤500 lines per skill-creator contract.

**Done when.**
- [ ] Running `/ai-spec-draft "topic"` produces a brief with 14 sections, YAML frontmatter, ≥5 `file:line` citations, no emoji, no machine paths.
- [ ] `tests/unit/skills/test_ai_spec_draft.py` validates structure (header presence, frontmatter keys, citation count).
- [ ] `tests/integration/test_spec_draft_handoff.py` confirms output feeds `/ai-brainstorm` cleanly.

### M4 · Auto-spec gate in `/ai-brainstorm` [§10.2 YAGNI · §10.5 TDD · §10.6 SDD]

**Why.** Owner feedback (B16). Trivial changes waste an interrogation cycle today. Multi-signal pre-check (not just file count) + condensed-spec auto-approve.

**What.**
- New handler `.claude/skills/ai-brainstorm/handlers/auto-spec-gate.md` implementing the algorithm in §4.4.
- Pre-check runs BEFORE interrogation (step 0.5 in SKILL.md).
- Knob block in `.ai-engineering/manifest.yml brainstorm.auto_spec_gate`.
- New action `spec_lifecycle.py mark_condensed <slug> <reason>` writes a condensed-spec row (effort=trivial, status=approved, summary=user description) without `_history.md` entry until `mark_shipped`.
- Delete redundant step 5 ("Scope check") — already covered by step 0.5.

**Done when.**
- [ ] `tests/unit/skills/test_brainstorm_auto_spec_gate.py` passes T1-T6 from §6.6 in the original research (typo fix → no-spec; new CLI flag → spec; pure-rename → no-spec; 500-LOC refactor → spec; schema column → spec; regulated security fix → spec).
- [ ] `manifest.yml` block validated by `tests/integration/test_manifest_schema.py`.
- [ ] Regulated mode tested with `regulated_mode: true` fixture (files_threshold=2, loc_threshold=20, force_spec_on_security=true).

### M5 · Mirror diet — 73% token reduction [§10.1 KISS · §10.4 DRY]

**Why.** Owner feedback (B17). 5,378 tokens/session preamble is structural waste. ~3,900 tokens recoverable.

**What.**
- Create `docs/principles.md` with §10.1-§10.8 anchors preserved (skills still cite `§10.x`).
- Create `docs/mirror-authoring.md` with the §14 strict-content-contracts table.
- Create `docs/surface-axioms.md` with §16 A1/A2 content.
- Replace inline sections in the 4 canonical mirrors with one-line pointers ("Engineering principles — see [docs/principles.md](docs/principles.md). Skills cite anchors §10.x.").
- Compress §1-9 to a 9-row table inline (principle | one-liner | §10.x anchor).
- Deduplicate §13 Hard Rules against `CONSTITUTION.md §Prohibitions` (keep only Conventional Commits + single-round quality loop inline; rest become "see CONSTITUTION").
- Move §15 IDE-Extras Escape Hatch to header comment in `tools/skill_lint/checks/md_mirror.py` (only consumer).
- Update `tools/skill_lint/checks/md_mirror.py` to exclude `docs/` from sha256 mirror-equivalence check.
- Update `tests/architecture/test_mirror_equivalence.py` accordingly.

**Done when.**
- [ ] `CLAUDE.md` ≤ 200 lines / ≤ 1,500 tokens estimated.
- [ ] Mirror sha256 equivalence holds across `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `CLAUDE.md` (modulo IDE-extras fence).
- [ ] `tests/architecture/test_mirror_equivalence.py` GREEN.
- [ ] `docs/principles.md`, `docs/mirror-authoring.md`, `docs/surface-axioms.md` exist and are byte-identical to the moved content.
- [ ] No skill in `.claude/skills/` lost its `§10.x` citation (lint check).

### M6 · Naming refactor [§10.7 Clean Code · §13.3 hard-rename]

**Why.** 11 opaque/ambiguous names (§3.5). First-impression UX is the framework's biggest UX cost.

**What.** Hard-rename per Constitution §13.3 (no shims). Update `.claude/`, `.codex/`, `.gemini/`, `.cursor/`, `.opencode/`, `.github/`, `manifest.yml`, all references, CHANGELOG. Each rename is atomic single-commit per Constitution §3 (Surgical Changes).

| Current | Renamed to | Rationale |
|---------|------------|-----------|
| `ai-gtm` | `ai-marketing` | Domain-explicit, no acronym |
| `ai-eval` | `ai-reliability-eval` | Disambiguates from "AI evaluation" |
| `ai-constitution` | `ai-charter` | Verb-leaning; "set up the charter" reads as action |
| `ai-guide` | `ai-onboard` | Audience-explicit (onboarding humans) |
| `ai-observe` | `ai-session-watch` | Passive watch role explicit |
| `ai-create` | `ai-scaffold` | Cohesion with industry term (scaffolding) |
| `ai-cleanup` | `ai-repo-tidy` | Disambiguates from code cleanup |
| `ai-visual` | `ai-brand-art` | Scope explicit (branding visuals) |
| `ai-write` | `ai-prose` | Domain explicit |
| `ai-prompt` | `ai-prompt-tune` | Verb-leaning (optimize, not author) |
| `ai-guard` | `ai-advise` | Resolves name-behavior mismatch (B5) |
| `verify-deterministic` (sub-agent) | `verifier-deterministic` | Family prefix consistency |
| `reviewer-context` (sub-agent) | `review-context` (separate family) | Lifecycle role distinct from specialists |
| `reviewer-validator` (sub-agent) | `review-validator` (separate family) | Same as above |

**Done when.**
- [ ] All 14 renames committed; no `find . -name "ai-gtm*"` matches.
- [ ] CHANGELOG.md `## [Unreleased] BREAKING CHANGES` section lists every rename with old → new mapping.
- [ ] `tests/architecture/test_surface_parity.py` GREEN (Surface Axiom A2 — distinct verbs hold).
- [ ] `tests/architecture/test_naming_cohesion.py` (new) asserts no acronyms, no ambiguous overlap.

### M7 · Skill-creator standard adoption [§10.6 SDD · §10.5 TDD · external standard]

**Why.** Owner explicit ask. Anthropic's `skill-creator` is the industry baseline for skill quality.

**What.**
- Document the adopted contract in `docs/skill-authoring.md`:
  - Frontmatter: `name`, `description` (pushy, when-to-trigger biased), optional `compatibility`.
  - Body ≤500 lines. Overflow → `references/<topic>.md` with TOC if >300 lines.
  - Imperative voice. Explain WHY. Avoid ALL-CAPS rigidity.
  - `scripts/` for deterministic / repeated work; `references/` for context-loaded docs; `assets/` for output templates.
  - `evals/evals.json` mandatory for skills with objectively verifiable outputs.
- Adopt grader + comparator + analyzer subagent triumvirate for skill evals (mirror Anthropic's `agents/grader.md`, `comparator.md`, `analyzer.md` patterns).
- Packaging artifact: `.skill` file via `scripts/package_skill.py` (port from anthropic).
- Update `/ai-create` (renamed `/ai-scaffold` per M6) to dispatch anthropic skill-creator subagent on new skill (Open Decision D6 resolves form).
- Run `evals/evals.json` for any skill TOUCHED in this PR (M1-M6 skills); NOT for unchanged ones (YAGNI §10.2).

**Done when.**
- [ ] `docs/skill-authoring.md` exists and matches anthropic contract.
- [ ] All M1-M6 new/renamed skills carry `evals/evals.json` with ≥10 prompts (≥5 should-trigger + ≥5 should-not-trigger).
- [ ] `grader.md` + `comparator.md` + `analyzer.md` exist in `.claude/agents/` mirroring Anthropic's contract.
- [ ] CI workflow runs evals nightly (not on every PR — keeps hot path fast).
- [ ] `tests/architecture/test_skill_contract.py` GREEN (frontmatter validity, body ≤500 lines, references TOC presence).

### M8 · Skill ↔ Agent cohesion surfacing [§10.3 SOLID-ISP]

**Why.** Orphans (B1, B2) and prefix inconsistencies (B3, B4) hurt discoverability and cognitive coherence.

**What.**
- Create `.claude/skills/ai-advise/SKILL.md` (formerly `/ai-guard` — see M6). Thin wrapper that dispatches `ai-advise` agent (renamed from `ai-guard`). Description: "Advisory governance check — flags standards/decisions/quality concerns. NEVER blocks (fail-open). Use for second-opinion sanity check before commit."
- Create `.claude/skills/ai-simplify/SKILL.md`. Thin wrapper around `ai-simplify` agent for on-demand single-file/single-folder simplification. Keep `ai-simplify-sweep` as the scheduled wrapper.
- Rename sub-agent `verify-deterministic` → `verifier-deterministic` (M6 entry; mentioned again here for cohesion).
- Move `reviewer-context` → `review-context` (separate from specialist family).
- Move `reviewer-validator` → `review-validator` (separate from specialist family).
- Update `/ai-review` dispatch contract to call `review-context` (pre) and `review-validator` (post) explicitly.

**Done when.**
- [ ] `/ai-advise` discoverable in `/` menu; calls `ai-advise` agent; description ≤100 words.
- [ ] `/ai-simplify` discoverable in `/` menu; calls `ai-simplify` agent.
- [ ] No agent in `.claude/agents/` is orphan (every first-class `ai-*` agent has a slash-skill counterpart OR is documented as private dispatch-only).
- [ ] `tests/architecture/test_skill_agent_cohesion.py` (new) GREEN — asserts coverage.

### M9 · Sanitizer hardening [§10.4 DRY · §13.4 anonymous content · security]

**Why.** `/ai-engineering-issue` (M1) requires multi-vector redaction. Current `_SECRET_RE` covers ~14% of attack surface (secrets only).

**What.**
- New module `src/ai_engineering/_shared/redactor.py`.
- Imports existing `_SECRET_RE` from `state/instincts.py` (DRY §10.4 — no duplication, no copy).
- Adds 6 new regex patterns (see §4.6).
- Single public API: `redact(text: str, *, strictness: Literal["normal", "strict"] = "strict") -> str`.
- Strict mode (default for upstream reports): all 7 vectors active.
- Normal mode (for telemetry): secrets-only (backward-compat for `state/instincts.py` callers).
- Refactor `state/instincts.py` and `state/observability.py` to call `_shared/redactor.py:redact(text, strictness="normal")` — single source of truth.

**Done when.**
- [ ] `src/ai_engineering/_shared/redactor.py` exists with 7-vector coverage.
- [ ] `tests/unit/shared/test_redactor.py` GREEN with ≥21 test cases (3 per vector: hit / miss / boundary).
- [ ] `state/instincts.py` and `state/observability.py` import from `_shared/redactor` (no duplicated regex).
- [ ] `/ai-engineering-issue` flow integration test confirms sanitized body passes 7-vector assertions.

---

## 7. Definition of Done

Single PR (#509) lands with ALL of:

- [ ] **Surface** — 48 → 51 skills (`+ai-issue`, `+ai-engineering-issue`, `+ai-spec-draft`; orphans surfaced as `+ai-advise` + `+ai-simplify` = 53; renames keep count at 53 ± rename count). Final count confirmed in spec.
- [ ] **Renames** — 14 hard-renames per M6 list; `CHANGELOG.md ## [Unreleased] BREAKING CHANGES` section complete with old → new mapping per rename.
- [ ] **Tests** — every M passes:
  - `tests/architecture/test_skill_agent_cohesion.py` (new)
  - `tests/architecture/test_naming_cohesion.py` (new)
  - `tests/architecture/test_skill_contract.py` (new — frontmatter, ≤500 lines, references TOC)
  - `tests/architecture/test_surface_parity.py` (existing — Surface Axiom A1/A2)
  - `tests/architecture/test_layer_isolation.py` (existing — hexagonal §10.8)
  - `tests/architecture/test_mirror_equivalence.py` (updated — exclude `docs/`)
  - `tests/unit/skills/test_brainstorm_auto_spec_gate.py` (new — T1-T6)
  - `tests/unit/skills/test_ai_issue.py` + `test_ai_engineering_issue.py` + `test_ai_spec_draft.py` (new)
  - `tests/unit/skills/test_ai_build_no_hitl.py` (new — 4 scenarios)
  - `tests/unit/shared/test_redactor.py` (new — 21 cases)
  - `tests/integration/test_spec_draft_handoff.py` (new)
  - `tests/integration/test_manifest_schema.py` (extended for `brainstorm.auto_spec_gate`)
- [ ] **Mirror diet** — `CLAUDE.md` ≤ 200 lines / ≤ ~1,500 tokens; `docs/{principles,mirror-authoring,surface-axioms,skill-authoring}.md` exist; mirror sha256 equivalence holds.
- [ ] **Eval contract** — every new/touched skill has `evals/evals.json` with ≥10 prompts (≥5 should-trigger + ≥5 should-not-trigger).
- [ ] **Manifest** — `brainstorm.auto_spec_gate` block present; `agents.registry` updated with new agents.
- [ ] **Suppression drift** — Open Decision D4 resolved (§13.2 amended OR F403 re-exports refactored).
- [ ] **Sanitizer** — `_shared/redactor.py` exists; `state/instincts.py` + `state/observability.py` refactored to import from it.
- [ ] **CHANGELOG** — `## [Unreleased]` section: `### Added`, `### Changed`, `### Removed`, `### BREAKING CHANGES` populated.
- [ ] **PR 509** — single branch, no force-push, Conventional Commits per §13.6, all CI green.
- [ ] **Governance** — `ai-eng audit replay --session <impl-session-id>` shows zero blockers; `gate_findings` table clean for impl session.

---

## 8. Quality Stamps

| Principle | Anchor | Manifestation in this brief |
|-----------|--------|-----------------------------|
| **KISS** | §10.1 | M5 (mirror diet); M1 (thin skills bind existing primitives); rename `ai-gtm` → `ai-marketing` |
| **YAGNI** | §10.2 | M4 (no spec for trivial change); `--no-hitl` opt-in not opt-out; evals only on touched skills, not all 48 |
| **SOLID** | §10.3 | M2 (build mode = SRP; one concern); M8 (orphan agents get single-purpose surface); SRP per sub-agent in skill-creator triumvirate |
| **DRY** | §10.4 | M9 (`_SECRET_RE` reused, not duplicated); M5 (mirror payload moves to single `docs/`); M1 (`ai-engineering-issue` reuses `ISSUE_TEMPLATE/*.yml`) |
| **TDD** | §10.5 | Every M ships RED tests FIRST; T1-T6 for auto-spec gate; 21-case redactor; 4-scenario no-HITL |
| **SDD** | §10.6 | This brief → `/ai-brainstorm` → spec → plan → build; M3 (`/ai-spec-draft` formalizes pre-brainstorm research); auto-spec gate (M4) preserves SDD with condensed-spec for trivial |
| **Clean Code** | §10.7 | M6 (rename for clarity, no abbreviations, no acronyms); explain WHY per skill-creator (M7) |
| **Hexagonal** | §10.8 | M1 `ai-issue` provider port + adapter (GitHub / ADO); M9 `_shared/redactor` is domain service, callers are adapters |
| **Skill-creator** | external | M7 — frontmatter contract, body ≤500 lines, evals, grader/comparator/analyzer subagents, `.skill` packaging |

---

## 9. Risks + Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Renames break user muscle memory | MEDIUM | Hard-rename per §13.3; CHANGELOG `BREAKING CHANGES` row per rename; release notes prominently list old → new; no shims (accept abrupt break — KISS) |
| Mirror diet breaks `md_mirror.py` sha equivalence | HIGH | Update `md_mirror.py` to exclude `docs/`; update `tests/architecture/test_mirror_equivalence.py`; one commit lands both changes atomically |
| Auto-spec gate misjudges and ships unsafe change | HIGH | `regulated_mode: true` knob tightens thresholds; condensed-spec still routes through `spec_lifecycle.py mark_condensed` (audit chain row); hard triggers (public_api / state_or_schema / new_dep / security) never bypass |
| `/ai-build --no-hitl` hides blockers in silent failure | HIGH | Exit 78 + structured `gate_findings` row + audit row in `framework-events.ndjson`; never silent fail; documented in skill body cite §13.5 |
| `/ai-engineering-issue` leaks PII despite sanitizer | CRITICAL | 7-vector redactor (M9) + mandatory human-confirmation gate before `gh issue create`; preview body in screen-fit caveman summary; user types literal `confirm` token |
| Skill-creator eval workflow adds latency to every PR | MEDIUM | Run evals nightly in CI not per-PR; only TOUCHED skills require eval pass on PR |
| 14 renames in one PR overwhelms reviewers | MEDIUM | Each rename = atomic single commit per §3 (Surgical Changes); reviewer reads commit-by-commit; CHANGELOG is the single-document index |
| `docs/principles.md` becomes a stale shadow | LOW | Lint check: any `§10.x` citation in `.claude/skills/` must resolve to anchor in `docs/principles.md`; CI fails on broken anchor |
| Suppression drift cleanup churns hex-arch | MEDIUM | Open Decision D4: prefer amending §13.2 with documented carve-out (lower churn) over refactoring F403 re-exports (higher correctness but invasive) |
| New agents (e.g., `ai-spec-draft` agent) violate Surface Axiom A1 | LOW | All new agents/skills audited by `tests/architecture/test_surface_parity.py` pre-merge |
| PR 509 grows too large to review | MEDIUM | Milestone commits are atomic; reviewer can pause between Ms; the brief itself is the review map |

---

## 10. Open Decisions for `/ai-brainstorm`

These become `D-<spec>-NN` rows in the decisions table once spec is approved.

**D1 — Naming refactor scope.** Land all 14 renames in PR 509, OR split into two waves (rename in PR 509, rename-aware tooling in follow-up)?
> Recommendation: **single wave** — atomic per Constitution §13.3 hard-rename. Two waves leaves the world in an inconsistent state.

**D2 — Surface orphans.** Surface `ai-guard` and `ai-simplify` as `/ai-advise` and `/ai-simplify` thin-wrapper skills (M8), OR fold them as flags into `/ai-verify` and `/ai-simplify-sweep`?
> Recommendation: **thin wrappers** — preserves SOLID §10.3 single-responsibility; flags balloon parent skills.

**D3 — Board create primitive.** `/ai-issue` invokes `gh` / `az` directly (KISS), OR extend `/ai-board` with a third subcommand `create` (SOLID-SRP — board ops in one place)?
> Recommendation: **`/ai-board create` subcommand**. Cohesion wins over thinness — board operations belong in one skill.

**D4 — Suppression drift resolution.** Amend Constitution §13.2 with a documented carve-out for F403 hex-arch re-exports and `pragma: no cover -- defensive`, OR refactor F403 re-exports to explicit names?
> Recommendation: **amend with carve-out** — F403 is sanctioned by §10.8 hex-arch already; making it explicit in §13.2 closes the text-drift loop without code churn.

**D5 — Spec-draft output target.** `/ai-spec-draft` writes to `.ai-engineering/specs/drafts/<topic>-brief.md` (current convention, distinct from `spec.md`), OR straight to `specs/spec.md` with `status: draft`?
> Recommendation: **drafts/ folder** — distinguishes "research artefact" from "approved spec"; matches existing 5-draft convention.

**D6 — Replace `/ai-create` (renamed `/ai-scaffold`)** with anthropic skill-creator dispatch, OR keep `/ai-scaffold` as the canonical entry that dispatches anthropic skill-creator internally?
> Recommendation: **wrapper** — `/ai-scaffold` stays as the documented entry point; dispatches anthropic skill-creator under the hood. Preserves UX continuity through rename + standard adoption.

**D7 — `/ai-build` no-HITL default flip.** Make `--no-hitl` default (and `--hitl` opt-in), OR keep `--no-hitl` opt-in?
> Recommendation: **opt-in for now** — YAGNI §10.2. Promote to default in a follow-up brief after 30 days of adoption signal.

**D8 — Mirror diet aggressiveness.** Move `§10` Engineering Principles entirely to `docs/principles.md` (saves ~1,440 tokens/session), OR keep a compressed TL;DR table inline (saves ~1,000 tokens/session)?
> Recommendation: **move entirely** — every skill cites `§10.x` anchors which resolve to `docs/`. Inline TL;DR risks staleness; one source of truth.

**D9 — `/ai-explore` vs `/ai-research` rename.** Disambiguate via rename (`/ai-codebase-explore` vs `/ai-external-research`), OR rely on descriptions?
> Recommendation: **defer to second-pass naming brief** — out of scope here. Descriptions already disambiguate; rename adds risk.

**D10 — Skill-creator triumvirate location.** Place `grader.md` / `comparator.md` / `analyzer.md` in `.claude/agents/` (first-class) or in `.claude/skills/ai-scaffold/agents/` (skill-scoped)?
> Recommendation: **skill-scoped** — these agents serve `/ai-scaffold` exclusively; promoting to first-class inflates the 9-agent registry without need.

---

## 11. Hand-off Sequence

### What `/ai-plan` will consume

- This brief promoted to `.ai-engineering/specs/spec-NNN-skills-agents-excellence-v2.md` after `/ai-brainstorm` approval.
- 10 Decision rows `D-NNN-01` through `D-NNN-10` written into `.ai-engineering/state/state.db decisions` table with the recommended resolutions OR owner-overridden values.
- `plan.md` structured by Milestone M1-M9, each milestone broken into 3-6 atomic tasks per Constitution §3 (Surgical Changes), each task with TDD RED test first per §10.5.

### What `/ai-build` will execute (single-concern milestones may run `--no-hitl` once M2 lands)

- **Mechanical pass first**: hard-renames (M6), sub-agent moves (M8). Atomic single-commit per rename.
- **Library pass**: `_shared/redactor.py` (M9), `auto-spec-gate.md` handler (M4), no-HITL flag in `ai-build` (M2).
- **Skill scaffolding**: `/ai-issue`, `/ai-engineering-issue`, `/ai-spec-draft`, `/ai-advise`, `/ai-simplify` (M1, M3, M8). Each via anthropic skill-creator workspace (M7).
- **Mirror diet**: M5 — move §10/§14/§15/§16 to `docs/`, compress §1-9, deduplicate §13. Single commit lands the move + `md_mirror.py` exclusion + test update atomically.
- **Eval pass**: `evals/evals.json` for every touched skill (nightly CI, not blocking PR).
- **All tests RED → GREEN → REFACTOR** per §10.5. No test weakened.
- **Final quality loop** per Constitution §13.5: single round, fail-loud on blockers.

### What `/ai-pr` will surface

- PR 509 body updated with all 9 milestones complete + green check matrix.
- `CHANGELOG.md ## [Unreleased]` section populated: `### Added` (3 new skills + 2 surfaced + sanitizer + auto-spec gate + skill-creator standard), `### Changed` (14 renames + mirror diet), `### BREAKING CHANGES` (rename mapping table).
- `governance audit` report shows zero blockers.
- Commit history: ≤30 atomic commits, Conventional Commits prefix per §13.6, every commit on `spec-128/context-overrides-refactor`.
- No force-push. No hook bypass. No `--no-verify`.

---

## 12. Cross-Brief Coordination

| Predecessor | Relationship |
|-------------|--------------|
| `skills-agents-excellence-refactor.md` (spec-129) | This brief SUPERSEDES — different scope (cohesion + UX vs original consolidation focus). Old brief stays in `drafts/` for archaeology per Constitution §13.3 hard-delete-only-when-clearly-dead. |
| `cli-ux-cross-ide-rearch-brief.md` (spec-133 — shipped) | Source of Surface Axioms (§16) we move to `docs/surface-axioms.md`. No conflict. |
| `cli-ux-overhaul-brief.md` (spec-132 — shipped) | Source of `ai-eng` CLI primitives. `/ai-issue` and `/ai-engineering-issue` may emit CLI gemini per Surface Axiom A1 if they meet criteria. |
| `dx-excellence-refactor-brief.md` (spec-131 — shipped) | Source of hot-path discipline. Mirror diet (M5) reinforces this. |
| `skills-agents-excellence-phase-c.md` (deferred placeholder) | TBD — may absorb a creative-roster fusion task (out-of-scope here per §2). |

---

## 13. Appendix — Anthropic Skill-Creator Contract (adopted)

Single source for M7 reference. Full extract lives at `docs/skill-authoring.md` after M5.

**Frontmatter (mandatory):**
```yaml
---
name: <lowercase-kebab-case-slug>
description: <when-to-trigger biased pushy — both WHAT it does AND specific CONTEXTS for when to use>
---
```

**Anatomy:**
```
skill-name/
├── SKILL.md (required, ≤500 lines)
│   ├── YAML frontmatter (name, description)
│   └── Markdown body (imperative voice, explain WHY, no ALL-CAPS rigidity)
└── (optional)
    ├── scripts/       # deterministic / repeated code
    ├── references/    # context-loaded docs (≥300 lines requires TOC)
    ├── assets/        # output templates
    ├── evals/
    │   └── evals.json # ≥10 prompts: ≥5 should-trigger + ≥5 should-not-trigger
    └── agents/        # skill-scoped subagents (grader / comparator / analyzer)
```

**Quality bar:**
- Body imperative, explanations cite WHY not WHAT.
- Description "pushy" — counters Claude undertriggering tendency.
- Evals required for objectively verifiable skills; optional for subjective ones (art, writing style).
- Grader assessment: PASS only when evidence reflects "genuine substance, not surface compliance."
- Blind A/B comparison (comparator) — never let analyzer see which output came from which skill version.
- Iteration termination: user-happy OR empty-feedback OR no-meaningful-progress.

**Safety:**
- Principle of Lack of Surprise: skill behavior matches its description verbatim.
- No malware, no exfil, no misleading skills.
- Roleplay OK; deception OK ONLY as documented persona.

**Anti-patterns documented (lift wholesale):**
- Overfitting to test prompts.
- Heavy-handed `MUST` / `ALWAYS` / `NEVER` in caps — yellow flag; reframe with explained reasoning.
- Dead weight in prompt — keep lean.
- Lazy baselines — launch with-skill AND without-skill runs in same turn.
- Non-discriminating assertions (pass regardless of skill presence).
- Easy negative-trigger queries that test nothing.

---

**End of brief.** Promote with `/ai-brainstorm` for spec generation and decision-row writing.
