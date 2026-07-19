---
title: Rewrite human-facing docs with branded hybrid-diagram visual system
spec: spec-177
status: approved
pipeline: full
architecture: pipeline-and-filter (asset foundation → doc consumers → gates)
execution_route:
  version: 1
  spec: spec-177
  executor: build
  automation: operator-in-the-loop
  concern_count: 12
  estimated_files: 32
  reason: >-
    Large + multi-concern (branding, SVG infographics, Mermaid render, VHS demo,
    five doc rewrites, count-drift, dead-weight removal, CI pipeline). Routed to
    /ai-build rather than /ai-autopilot because the visual-asset phases are
    taste-driven and benefit from operator review at the Phase-1 gate; autopilot
    autonomous sub-spec decomposition is ill-suited to design-quality assets.
  safe_next_command: "/ai-build"
---

# Plan — spec-177 · Rewrite human-facing docs + branded hybrid-diagram visual system

## Architecture

Pipeline-and-filter. Phase 1 produces immutable **visual assets** (brand tokens, SVG
infographics, fal art, Mermaid sources + pre-rendered SVG, VHS demo). Phases 2–3
are **consumers** that embed those assets into rewritten docs and fix drift/dead-weight.
Phase 4 wires the **CI render filter**. Phase 5 is the **verification sink** against every
named test contract. Assets are upstream of every doc edit, so the order is dependency-forced.

## Design

Terminal-native editorial governance (authority: `.ai-engineering/reference/brand-voice.md`).
Palette navy `#0B1120`→`#162844`, accent teal `#00D4AA`, text `#F8FAFB`, 4% white grid,
30% teal corner brackets, JetBrains Mono. Wordmark `{ai} engineering`. NO emoji;
`[PASS]/[WARN]/[FAIL]/[PENDING]` grammar; mid-dot stat line; command-first imperative voice.
Diagram media routed by intent (D-177-01): fal art = branded illustration only (no
load-bearing text); SVG infographics = labelled "wow" visuals; Mermaid = technical diagrams.

## Operator review gates

- **G1 (after Phase 1)** — operator eyeballs every generated/authored visual (fal art +
  SVG infographics + rendered Mermaid SVGs + VHS GIF) for brand fidelity and "incite use"
  before any doc consumes them. Regenerate off-brand assets here, not after the rewrite.
- **G2 (after Phase 5)** — full green gate before `/ai-pr`.

---

## Phase 0 — Render toolchain + asset scaffold

- [ ] T-0.1 — Add dev render toolchain (mermaid-cli, VHS deps) as a documented dev/CI-only dependency
  - Agent: build
  - Files: `pyproject.toml`, `.ai-engineering/runbooks/` (new `docs-render-runbook.md`)
  - Principles applied: §10.2 YAGNI (CI/dev-only, never shipped to end users), §10.8 Hexagonal (render tooling is an outbound adapter, not core)
  - Patch (deterministic): omit — judgment on dependency placement; pin `ghcr.io/mermaid-js/mermaid-cli` digest + charmbracelet/vhs version in the runbook, do NOT add to the runtime wheel.
  - Gate: `twine check` still passes; no new runtime dep in built wheel (`uv build && unzip -l dist/*.whl | grep -c mermaid` == 0)

- [ ] T-0.2 — Create asset directory scaffold
  - Agent: build
  - Files: `.github/assets/architecture/` (new), `.github/assets/art/` (new), `docs/architecture/diagrams/` (new), `.github/assets/demo.tape` (new placeholder)
  - Principles applied: §10.7 Clean Code (one home per asset class)
  - Patch (deterministic): omit — `mkdir`-equivalent via committing `.gitkeep` placeholders.
  - Gate: directories exist; `git status` shows them tracked

---

## Phase 1 — Visual asset foundation  (→ Gate G1)

- [ ] T-1.1 — Author brand token reference (single source for every visual)
  - Agent: build
  - Files: `docs/architecture/brand-tokens.md` (new)
  - Principles applied: §10.4 DRY (one palette/type table consumed by all assets), §10.7 Clean Code
  - Patch (deterministic): omit — author the navy/teal/#F8FAFB hex table, JetBrains-Mono stack, grid/bracket specs, lifted verbatim from `banner-dark.svg` + `brand-voice.md`.
  - Gate: hex values byte-match `.github/assets/banner-dark.svg`; no emoji present

- [ ] T-1.2 — Author SVG infographic: deterministic-plane-gates-probabilistic thesis
  - Agent: build
  - Files: `.github/assets/architecture/thesis-light.svg`, `thesis-dark.svg`
  - Principles applied: §10.7 Clean Code (labels are real `<text>`, not raster), §10.3 SOLID (one concept per asset)
  - Patch (deterministic): omit — hand-author branded SVG (probabilistic skills above, deterministic gate plane below, audit chain beneath); palette from T-1.1; light+dark twins.
  - Gate: both SVGs render in a browser; `<text>` legible; palette matches T-1.1; opens in GitHub markdown `<img>`

- [ ] T-1.3 — Author SVG infographic: files-only three-tier persistence model
  - Agent: build
  - Files: `.github/assets/architecture/persistence-light.svg`, `persistence-dark.svg`
  - Principles applied: §10.7 Clean Code, §10.4 DRY (mirrors `docs/persistence-doctrine.md` tiers, no new claims)
  - Patch (deterministic): omit — Tier 1 NDJSON audit (hash-chained) / Tier 2 JSON+YAML records+config / Tier 3 Markdown, with derived-cache arrows; light+dark.
  - Gate: tiers match `docs/persistence-doctrine.md` exactly; no "four-tier"/"state.db" text

- [ ] T-1.4 — Author SVG infographic: 54-skill · 9-agent taxonomy map
  - Agent: build
  - Files: `.github/assets/architecture/taxonomy-light.svg`, `taxonomy-dark.svg`
  - Principles applied: §10.7 Clean Code, §10.4 DRY (counts sourced from filesystem ground-truth, not retyped)
  - Patch (deterministic): omit — group 54 skills by family + 9 agents; the count it renders is the canonical 54·9 that T-3.* enforces.
  - Gate: renders 54 skills / 9 agents; family grouping matches `.claude/skills/` reality

- [ ] T-1.5 — Generate fal.ai branded art (hero illustration + OG card + section divider)
  - Agent: build
  - Files: `.github/assets/art/hero-illustration.png`, `.github/assets/art/og-card.png`, `.github/assets/art/divider.png`
  - Principles applied: §10.2 YAGNI (art only where SVG/Mermaid can't carry it), §10.1 KISS
  - Patch (deterministic): omit — call fal queue API (`https://queue.fal.run/fal-ai/nano-banana-pro`, `Authorization: Key $FAL_KEY`); estimate cost first; prompt locks navy/teal/JetBrains-Mono terminal-governance aesthetic; ABSTRACT art with NO load-bearing text (labels live in SVG/Mermaid); iterate cheap (`nano-banana-2`) before the `nano-banana-pro` final; record `seed`.
  - Gate: images on-brand at G1; OG card is 1200×630; no garbled text in raster; cost logged

- [ ] T-1.6 — Author the 6 canonical Mermaid diagram sources (no theme)
  - Agent: build
  - Files: `docs/architecture/diagrams/canonical-chain.mmd`, `hooks-lifecycle.mmd`, `mirror-fanout.mmd` (+ extract/refresh the 3 reusable ones already in solution-intent: system-context, module-map, ide-sync)
  - Principles applied: §10.4 DRY (diagram source is SSOT; solution-intent embeds the same blocks), §10.5 TDD (lint before render)
  - Patch (deterministic): omit — author flowchart/sequence blocks; NO `%%{init}%%` theme (GitHub auto-adapts); guard the diagram-breakers (no bare `end`, no `{}` in `%%` comments, quote nested-shape labels).
  - Gate: `mmdc --parse` clean on every `.mmd`; zero `%%{init}.*theme` matches

- [ ] T-1.7 — Pre-render every Mermaid source to committed light/dark SVG
  - Agent: build
  - Files: `.github/assets/architecture/<name>-light.svg` + `-dark.svg` for all Mermaid diagrams (the 6 new/extracted + the 10 in solution-intent)
  - Principles applied: §10.8 Hexagonal (render adapter), §10.4 DRY
  - Patch (deterministic): omit — `mmdc -i x.mmd -o x.svg` via the pinned Docker image; produce light+dark variants for `<picture>`; this is the PyPI/off-GitHub fallback.
  - Gate: one SVG pair per Mermaid block; SVGs non-empty; render in browser

- [ ] T-1.8 — Author VHS demo tape + render GIF/MP4/WebM
  - Agent: build
  - Files: `.github/assets/demo.tape`, `.github/assets/demo.gif` (regenerated), `.github/assets/demo.mp4`, `.github/assets/demo.webp` (regenerated)
  - Principles applied: §10.5 TDD (deterministic re-render), §10.7 Clean Code
  - Patch (deterministic): omit — `.tape` with `Hide`/`Show` around setup, pinned `Set Theme`/`FontSize 18`/`Width`/`Height`, `TypingSpeed 75ms`, `LoopOffset`, seeded fixtures, NO machine paths / operator names (anonymity hard rule); shows `ai-eng install . → ai-eng doctor [PASS] → /ai-start → /ai-brainstorm`; target GIF ≤3 MB.
  - Gate: GIF ≤3 MB; plays inline; no PII/machine-path in frames; tape re-renders identically

---

## Phase 2 — Doc rewrites consuming the assets

- [ ] T-2.1 — RED: assert README brand-contract + count + asset embeds
  - Agent: verify
  - Files: `tests/unit/docs/test_readme_brand_contract.py`, `tests/docs/test_links.py`
  - Principles applied: §10.5 TDD (RED before rewrite)
  - Patch (deterministic): omit — run the existing contracts against the to-be-rewritten README; capture the failing baseline so the rewrite is driven to green. (Existing tests already encode ≤170, 6 surfaces, wordmark, chain literal, 4 doc links.)
  - Gate: tests run; failures captured as the target

- [ ] T-2.2 — GREEN: rewrite root README lean, proof-before-catalog
  - Agent: build
  - Files: `README.md`
  - Principles applied: §10.1 KISS, §10.7 Clean Code, §10.4 DRY
  - Patch (deterministic): omit — judgment-heavy. Order: SVG wordmark banner → mid-dot stat line (`54 skills · 9 agents · 6 surfaces · 1 governed flow`) → one-line value prop → VHS demo → thesis SVG (`<picture>`) → canonical-chain SVG replacing the plain text block → bounded observe-mode quickstart showing `[PASS]` → 54·9 taxonomy SVG → 6-surface table → "Why Governance Matters" → links to `docs/`, `AGENTS.md`, `CONSTITUTION.md`, `CHANGELOG.md`, `CONTRIBUTING.md`. All image URLs absolute `raw.githubusercontent .../main/...`. ≤170 lines. No emoji.
  - Gate: `pytest tests/unit/docs/test_readme_brand_contract.py tests/docs/test_links.py` green; `wc -l README.md` ≤170

- [ ] T-2.3 — Rewrite solution-intent.md: embed assets, modernize, fix counts
  - Agent: build
  - Files: `.ai-engineering/solution-intent.md`
  - Principles applied: §10.4 DRY (counts from ground-truth), §10.7 Clean Code
  - Patch (deterministic):
    ```diff
    @@ line 28 @@
    -Deterministic CLI tooling, 47 AI skills, 10 agents (+ 15 specialist sub-agents), and a governance surface
    +Deterministic CLI tooling, 54 AI skills, 9 agents (+ specialist review/verifier sub-agents), and a governance surface
    @@ line 430-431 @@
    -            47 skills
    -            10 agents
    +            54 skills
    +            9 agents
    @@ line 768 @@
    -| Skills (47) | `.claude/skills/ai-<name>/SKILL.md` |
    +| Skills (54) | `.claude/skills/ai-<name>/SKILL.md` |
    ```
  - Gate: `grep -E "47 |10 agents|Skills \(47\)" .ai-engineering/solution-intent.md` empty; `Last Review` bumped to 0.12.0

- [ ] T-2.4 — Rewrite .ai-engineering/README.md: fix stat line, keep client-manual contract
  - Agent: build
  - Files: `.ai-engineering/README.md`
  - Principles applied: §10.4 DRY, §10.7 Clean Code
  - Patch (deterministic):
    ```diff
    @@ line 12 @@
    -`53 skills · 9 agents · 6 surfaces · 1 governed flow`
    +`54 skills · 9 agents · 6 surfaces · 1 governed flow`
    ```
  - Gate: `pytest tests/unit/docs/test_readme_brand_contract.py::test_governance_readme_is_client_manual_with_quick_wins test_governance_readme_links_resolve` green; catalog markers intact; no "four-tier"/"state.db"/"GETTING_STARTED.md"/bare "ai-eng sync"

- [ ] T-2.5 — Build docs/ information architecture (index + architecture + guides)
  - Agent: build
  - Files: `docs/index.md` (new), `docs/architecture/index.md` (new), `docs/architecture/*.md` (diagram pages embedding the SVGs), `docs/guides/getting-started.md` (new)
  - Principles applied: §10.3 SOLID (shallow findable IA), §10.7 Clean Code
  - Patch (deterministic): omit — author the sitemap index, an architecture home embedding every SVG via `<picture>` light/dark with descriptive alt text, and a getting-started journey (install → doctor → /ai-start → canonical chain). Lifecycle-ordered, no deep nesting.
  - Gate: every relative link resolves; every embedded SVG path exists; no emoji

- [ ] T-2.6 — Generate llms.txt + llms-full.txt
  - Agent: build
  - Files: `llms.txt` (new), `llms-full.txt` (new), `.ai-engineering/scripts/gen_llms_txt.py` (new) + byte-identical twin under `src/ai_engineering/templates/.ai-engineering/scripts/gen_llms_txt.py`
  - Principles applied: §10.8 Hexagonal (generator is an adapter over the doc set), §10.4 DRY (derived artifact, rebuildable)
  - Patch (deterministic): omit — `llms.txt` = flat routing map (title, summary, primary doc links, `## Optional` for secondary); `llms-full.txt` = concatenated corpus. Label as a derived cache with the rebuild command.
  - Gate: both files non-empty; links resolve; regenerating is idempotent; twin byte-identical (`diff` clean)

---

## Phase 3 — Dead-weight removal (after assets exist)

- [ ] T-3.1 — Export the .pen visual sources to committed brand SVGs
  - Agent: build
  - Files: `.github/assets/brand/design-export.svg` (new), `.github/assets/brand/untitled-export.svg` (new)
  - Principles applied: §10.7 Clean Code (preserve the brand source-of-truth before deletion)
  - Patch (deterministic): omit — open `docs/design.pen` + `docs/untitled.pen` via pencil MCP (`open_document` → `export_nodes` to SVG). `.pen` are encrypted; ONLY the pencil MCP can read them. Confirm exports render before T-3.3.
  - Gate: both SVGs exist and render; visually match the .pen wordmark/status grammar

- [ ] T-3.2 — Repoint brand-voice.md from .pen sources to committed SVGs
  - Agent: build
  - Files: `.ai-engineering/reference/brand-voice.md`
  - Principles applied: §10.4 DRY (single live visual source-of-truth)
  - Patch (deterministic):
    ```diff
    @@ Evidence section @@
    -The visual sources remain `docs/design.pen` and `docs/untitled.pen`; this Markdown file is
    +The visual sources are `.github/assets/brand/design-export.svg` and `.github/assets/brand/untitled-export.svg` (exported from the retired .pen design files); this Markdown file is
    ```
    (and replace the three `docs/design.pen:NNNN` / `docs/untitled.pen:NNNN` evidence line references with the committed SVG paths)
  - Gate: no `\.pen` reference remains in `brand-voice.md`; new SVG links resolve

- [ ] T-3.3 — Hard-delete .pen files, empty presentations/, and .DS_Store
  - Agent: build
  - Files: `docs/design.pen`, `docs/untitled.pen`, `docs/presentations/`, `docs/.DS_Store`, `docs/presentations/.DS_Store`
  - Principles applied: §10.2 YAGNI, hard-delete (no shims, §13.3)
  - Patch (deterministic): omit — `git rm` the two `.pen` files + the `.DS_Store` files; remove the empty `presentations/` dir; ensure `.DS_Store` is gitignored.
  - Gate: `find docs -name '*.pen' -o -name '.DS_Store'` empty; `docs/presentations` gone; no inbound link to deleted paths anywhere (`grep -rn "\.pen\|presentations/" README.md docs/ .ai-engineering/` clean)

---

## Phase 4 — CI render pipeline + PyPI safety

- [ ] T-4.1 — Add diff-scoped diagram + demo render CI workflow
  - Agent: build
  - Files: `.github/workflows/docs-render.yml` (new)
  - Principles applied: §10.8 Hexagonal (render off the hot path), §10.2 YAGNI
  - Patch (deterministic): omit — trigger on `**/*.mmd` + `**/*.tape` changes only; render Mermaid→SVG (pinned mmdc Docker digest) and VHS GIF; commit regenerated assets via auto-commit; SHA-pin every action; concurrency + timeout per repo pipeline policy. Never runs on pre-commit/pre-push.
  - Gate: workflow lints (`actionlint`); references the CI Actions allowlist; pre-commit/pre-push budgets (<1s/<5s) unchanged

- [ ] T-4.2 — Verify PyPI long_description degradation safety
  - Agent: verify
  - Files: `README.md`, `pyproject.toml`
  - Principles applied: §10.5 TDD (verify the rendered artifact)
  - Patch (deterministic): omit — confirm Mermaid/`<picture>`/alerts degrade to safe fallbacks on PyPI; every image is an absolute `raw.githubusercontent .../main/...` URL.
  - Gate: `uv build && twine check dist/*` PASS; `grep -n "raw.githubusercontent" README.md` covers every `<img>`; zero relative image paths

---

## Phase 5 — Verification  (→ Gate G2)

- [ ] T-5.1 — Add count-consistency regression test
  - Agent: build
  - Files: `tests/unit/docs/test_inventory_count_consistency.py` (new)
  - Principles applied: §10.5 TDD (lock the drift fix so it can't regress)
  - Patch (deterministic): omit — assert README, `.ai-engineering/README.md`, and `solution-intent.md` all state `54 skills` / `9 agents` and that this equals `len(glob('.claude/skills/ai-*'))` / `len(glob('.claude/agents/ai-*.md'))`.
  - Gate: test passes; intentionally drifting a count makes it fail

- [ ] T-5.2 — Run the full doc + config gate suite
  - Agent: verify
  - Files: `tests/docs/`, `tests/unit/docs/`, `tests/unit/config/`
  - Principles applied: §10.6 SDD (verify against the spec contract), §10.4 Goal-Driven
  - Patch (deterministic): omit — `pytest tests/docs tests/unit/docs tests/unit/config -q` + `ai-eng check` (expect 7/7). Confirm no hardcoded count gate tripped by the new assets/docs.
  - Gate: all green; `ai-eng check` 7/7

- [ ] T-5.3 — No-emoji + brand-voice + link-resolution sweep
  - Agent: verify
  - Files: `README.md`, `.ai-engineering/README.md`, `.ai-engineering/solution-intent.md`, `docs/**`, `llms.txt`, `llms-full.txt`
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): omit — assert zero emoji in rewritten surfaces; `[PASS]/[WARN]/[FAIL]` grammar preserved; every relative link + embedded asset path resolves; SOUL.md still ≤80 lines.
  - Gate: emoji grep empty; all links resolve; `wc -l SOUL.md` ≤80

- [ ] T-5.4 — Secrets + mirror-parity + spec-lifecycle integrity
  - Agent: verify
  - Files: repo-wide
  - Principles applied: §13 Hard Rules, §10.6 SDD
  - Patch (deterministic): omit — `gitleaks protect --staged`; confirm no generated mirror (`CLAUDE.md`/`AGENTS.md`/copilot) was hand-edited (regenerate via `ai-eng dev sync` if canonical changed); any touched `.ai-engineering/scripts/*.py` has a byte-identical `src/ai_engineering/templates/` twin.
  - Gate: gitleaks clean; mirror diff clean; script twins byte-identical; spec_lint green (plan + spec)

---

## Dependency order

```
Phase 0 ─► Phase 1 ─► [G1 operator review] ─► Phase 2 ─► Phase 3 ─► Phase 4 ─► Phase 5 ─► [G2] ─► /ai-pr
                         (assets)                (docs)    (delete)   (CI)      (verify)
```

T-1.* assets are upstream of T-2.* doc embeds. T-3.1→T-3.2→T-3.3 is strictly ordered (export → repoint → delete). T-2.1 (RED) precedes T-2.2 (GREEN). Phase 5 is terminal.

## Gate criteria (plan-level)

- Every named test contract green: `test_readme_brand_contract.py`, `test_links.py`, `tests/unit/config`, `ai-eng check` 7/7.
- README ≤170 lines; SOUL.md ≤80 lines; counts unified at 54·9 everywhere.
- No emoji; no relative image URLs; PyPI `twine check` PASS.
- No `.pen` / `.DS_Store` / `presentations/` remnants; no inbound links to deleted paths.
- No generated-mirror hand-edits; script twins byte-identical; gitleaks clean.
- Website untouched (spec-178 boundary held).
