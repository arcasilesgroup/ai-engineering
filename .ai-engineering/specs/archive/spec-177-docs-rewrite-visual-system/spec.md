---
spec: spec-177
title: Rewrite human-facing docs from scratch with branded hybrid-diagram visual system
status: in-progress
effort: large
summary: Rewrite every human-facing doc surface lean-first with a branded hybrid-diagram visual system — fal.ai art plus PPTX-grade SVG infographics plus theme-adaptive Mermaid — fixing the 47/53/54 count drift, removing dead weight, and shipping llms.txt; the public website is a fast-follow.
---

## Summary

The human-facing documentation is visually flat and structurally stale. The root `README.md` advertises "54 skills · 9 agents" but ships **zero** diagrams; the framework's single richest visual asset — the 10 Mermaid diagrams in `.ai-engineering/solution-intent.md` — is buried in a dot-directory and never linked from the README, so a first-time visitor sees a value prop and install steps but never how the system is shaped or why governance matters. Skill counts disagree across three docs (root README says 54, `.ai-engineering/README.md` says 53, `solution-intent.md` says 47/10). `docs/` is a flat drawer with an empty `presentations/` stub, two stray `.DS_Store` files, and two opaque encrypted `.pen` files with no rendered exports. There is no architecture visual, no canonical-chain flow graphic, no skills/agents taxonomy, no persistence-tier diagram, no hooks-lifecycle diagram, and nothing the framework's own audience (AI agents) can route via `llms.txt`. This spec rewrites the entire in-repo human-facing surface from scratch under a "menos es más" (less-is-more) discipline with a coherent, terminal-native branded visual system: lean README, modernized `solution-intent.md` and `.ai-engineering/README.md`, a new structured `docs/` set, a hybrid diagram system (fal.ai branded art + hand-authored PPTX-grade SVG infographics + theme-adaptive Mermaid pre-rendered to SVG), a VHS-as-code terminal demo, and agent-facing `llms.txt`/`llms-full.txt`. Grounded in 4-tier research over 6 inspiration repos, ~70 web citations, and a NotebookLM deep-research pass over 116 sources.

## Goals

- Root `README.md` rewritten lean (≤170 lines, brand-contract preserved): hero → one-line value prop → proof (demo + one architecture visual + canonical-chain flow graphic) → bounded observe-mode quickstart that shows expected `[PASS]` output → scannable 54-skills/9-agents map → supported surfaces → links to depth. Passes `tests/docs` and `tests/unit/docs`.
- A coherent **branded visual system**: fal.ai-generated branded art (hero illustration, OG/social card, optional section dividers) + a set of hand-authored **PPTX-grade SVG infographics** (crisp, labelled, on-brand, GitHub-rendered) for the load-bearing concepts + **theme-adaptive Mermaid** for precise technical diagrams, every Mermaid block pre-rendered to a committed SVG.
- A defined diagram inventory covering: the deterministic-plane-gates-probabilistic-plane thesis, the canonical chain flow, the 54-skill/9-agent taxonomy, the files-only three-tier persistence model, the 11-event hooks lifecycle, and the one-canonical-payload→6-surfaces mirror fan-out.
- `solution-intent.md` and `.ai-engineering/README.md` modernized; the **47/53/54 skill-count drift resolved to one canonical number (54 skills · 9 agents)** sourced consistently across every surface.
- Dead weight removed: empty `docs/presentations/`, stray `.DS_Store` files, and the opaque `docs/*.pen` files (exported to committed brand SVGs first, then hard-deleted); `brand-voice.md` repointed from `.pen` sources to the committed brand assets.
- `docs/` reorganized into a navigable, lifecycle-ordered information architecture with an index and an `architecture/` home for the diagrams.
- Terminal demo rebuilt as a checked-in **VHS `.tape`-as-code** asset, regenerated in CI, replacing the Remotion-rendered `demo.gif/webp`.
- Agent-facing `llms.txt` + `llms-full.txt` shipped so IDE agents can route and ingest the canonical docs.
- A CI job renders diagrams (Mermaid→SVG) and the VHS demo on diff-scoped changes, off the local hot path; all README/PyPI images use absolute `raw.githubusercontent` main URLs and the PyPI `long_description` degrades safely (validated by `twine check`).
- No regression: all count gates (`tests/unit/config`, `tests/unit/docs`, `ai-eng check`) stay green; no emoji introduced; brand voice (`[PASS]/[WARN]/[FAIL]`, mid-dot stat line, command-first) preserved.

## Non-Goals

- **The public website is OUT of scope.** The custom landing + docs site, domain purchase/DNS (`ai-engineering.com` / `ai-engineering.arcasiles.com`), and Cloudflare/Railway hosting are deferred to a fast-follow spec (spec-178). Operator chose web architecture = full custom (landing + docs) for that follow-on; this spec touches no external infra, spends nothing, and publishes nothing outward.
- No edits to the generated IDE mirrors (`CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`) — they regenerate from `CANONICAL.md` / `scripts/sync_mirrors`; if canonical-payload wording must change, edit the canonical source and run `ai-eng dev sync`, never the mirror.
- No change to skill/agent behavior, CLI commands, hooks, or governance gate logic — this is documentation + visual assets only.
- No MkDocs/Docusaurus/Starlight in-repo docs-site generator now (folded into the spec-178 full-custom website decision).
- No rewrite of `CONSTITUTION.md` or `SOUL.md` content (SOUL.md stays ≤80 lines); only their inbound links/diagram references may be added.
- No new third-party runtime dependency shipped to end users (diagram/demo render tooling lives in CI/dev only).

## Decisions

### D-177-01 — Hybrid diagram strategy: three media, routed by intent

fal.ai produces **branded raster ART ONLY** (hero illustration, OG/social card, section dividers). Hand-authored **SVG infographics** carry the PPTX-grade explanatory visuals with real labels. **Mermaid** produces the precise, maintainable technical diagrams. No single medium is used for everything.

**Rationale**: Research is unambiguous — AI raster models hallucinate text and cannot be diffed, so they fail for labelled technical diagrams, while they excel at branded illustration; Mermaid is ~24× more token-efficient than draw.io XML and renders natively on GitHub but its Dagre engine crowds dense graphs; designed SVG gives slide-grade clarity and renders crisply on GitHub. Matching each medium to what it is good at is the only way to get both "wow" and correctness.

### D-177-02 — Keep the hand-authored SVG wordmark banner; fal art is additive

The existing `banner-dark.svg`/`banner-light.svg` wordmark stays as the hero banner. fal.ai art is added as *separate* assets, never as a replacement wordmark.

**Rationale**: The SVG banner is brand-perfect, 2.4 KB, theme-adaptive, and carries load-bearing text (`{ai} engineering`) that a raster model would risk corrupting. Operator confirmed "conservar SVG + añadir arte fal." Additive art captures the visual upgrade without regressing a working, accessible asset.

### D-177-03 — PPTX-grade SVG infographics are hand/tool-authored, not AI-generated

The explanatory "como en PPTX" visuals (architecture thesis, persistence tiers, taxonomy) are authored as branded SVG (design tooling or code), checked in, and embedded via `<img>`/`<picture>`. GitHub renders SVG in Markdown.

**Rationale**: Operator wants "simple, claro, que se entienda, incite a usar" — that requires precise typography and layout AI raster cannot guarantee. SVG is crisp at any zoom, theme-controllable, small, and reviewable. It is the medium that satisfies both the visual-quality bar and the repo's anonymity/diff constraints.

### D-177-04 — Mermaid blocks set no theme and are pre-rendered to committed SVG

Every Mermaid block omits an explicit `%%{init}%%` `theme` (so GitHub auto-adapts light/dark) and is also pre-rendered to a committed SVG via `mermaid-cli` (`mmdc`), wired through `<picture>` for non-GitHub surfaces.

**Rationale**: Specifying a Mermaid theme "typically results in a diagram completely unreadable in dark mode"; omitting it is the single highest-impact accessibility rule. PyPI's renderer executes no Mermaid, so a committed SVG with an absolute `raw.githubusercontent` URL is the only way the architecture survives off GitHub (a known repo lesson).

### D-177-05 — README stays lean; depth lives in docs/ and solution-intent

The README keeps its ≤170-line cap and brand contract; the catalog, deep architecture, and per-concept detail move into `docs/` and `solution-intent.md`, linked from the README.

**Rationale**: 10k-star READMEs sit at 800–1,500 words with depth folded or linked; "menos es más" plus the enforced line cap both demand a lean entry doc. The README's job is the five-second test and the first successful action, not exhaustiveness.

### D-177-06 — New docs/ information architecture, lifecycle-ordered

`docs/` is restructured to: an `index` landing/sitemap, an `architecture/` home for the diagram set + their SVG sources, a `guides/` getting-started/journey set, and the existing runbook/reference files kept as durable reference. Flat-drawer layout is replaced with a shallow, findable tree.

**Rationale**: Research IA guidance favors shallow, lifecycle-ordered, findable structures (install → bootstrap → canonical chain → reference) over deep nesting; a governance framework of this size needs a navigable doc set, not a loose drawer.

### D-177-07 — One canonical inventory count: 54 skills · 9 agents

Filesystem ground-truth (54 `.claude/skills/ai-*` dirs, 9 `.claude/agents/ai-*.md`) is the source; `solution-intent.md` (47/10) and `.ai-engineering/README.md` (53/9) are corrected to 54/9, and the count is stated once per surface from the same number.

**Rationale**: Three disagreeing counts across three docs is an authority-drift smell that erodes trust on close reading; Single-Source-of-Truth-Per-Datum (hard rule §13.7) requires one canonical figure. The build resolves drift while it is already touching every surface.

### D-177-08 — Hard-delete dead weight after exporting the .pen sources

Remove `docs/presentations/` (empty), the `.DS_Store` files, and `docs/design.pen` + `docs/untitled.pen` — but first export the `.pen` visual sources to committed brand SVGs, then repoint `brand-voice.md` from the `.pen` references to those committed assets.

**Rationale**: Hard rule §13.3 forbids backwards-compat shims (hard delete, not deprecate). The `.pen` files are opaque (encrypted, no exports) dead weight from a reader's view, but `brand-voice.md` cites them as the visual source of truth — so exporting + repointing first preserves the brand authority before deletion, satisfying anonymity and SSOT.

### D-177-09 — Rebuild the terminal demo as VHS `.tape`-as-code

The Remotion-rendered `demo.gif/webp` is replaced by a checked-in VHS `.tape` script rendered to a GIF (plus MP4/WebM), regenerated in CI.

**Rationale**: Operator chose "rehacer como VHS ahora." VHS makes the demo deterministic, diff-able, and CI-regenerable so it never drifts from the CLI, and a native GIF plays inline on GitHub (which does not autoplay `<video>` or run the asciinema player). It also enforces anonymized output via its isolated virtual terminal.

### D-177-10 — Ship llms.txt + llms-full.txt for agent consumption

Add `/llms.txt` (a flat Markdown routing map of the docs) and `/llms-full.txt` (the concatenated corpus) at the repo root, generated from the doc set.

**Rationale**: IDE agents (Claude Code, Cursor, Cline, Aider) are now top doc consumers and routinely fetch these files; for a framework that is itself agent-facing and distributed to agent IDEs, it is a near-free, uniquely on-brand, high-leverage artifact.

### D-177-11 — Diagram + demo rendering runs in CI, diff-scoped, off the hot path

A CI job renders Mermaid→SVG and the VHS demo only when their source files change, then validates outputs; pre-commit/pre-push stay within the <1s/<5s budgets and never render.

**Rationale**: Heavy render work (mmdc/Chromium, ttyd+ffmpeg) would blow the hot-path budget; the repo's diff-scoped gate discipline already models exactly this. Treating diagrams and the demo as build artifacts keeps them from going stale silently.

### D-177-12 — The public website is deferred to fast-follow spec-178

This spec ships only in-repo files. The custom landing + docs website, domain, and Cloudflare/Railway hosting are scoped to a separate spec.

**Rationale**: Brainstorm discipline — "is this in scope for v1?" The website involves money (domain), outward publishing, and infra outside git governance that needs per-action operator confirmation; bundling it would balloon an irreversible run and violate "menos es más." Operator explicitly chose "Web = fast-follow."

## Risks

- **README brand-contract / line-cap test breakage.** The rewrite must keep all 6 surfaces, `{ai} engineering`, the literal chain string, the four doc links, and ≤170 lines. *Mitigation:* author against `tests/unit/docs/test_readme_brand_contract.py` + `tests/docs/test_links.py`; run both (CI-only) locally before push.
- **PyPI degradation.** GFM alerts, `<picture>`, and Mermaid do not render on PyPI. *Mitigation:* keep a degradation-safe `long_description`, embed pre-rendered SVGs via absolute `raw.githubusercontent` URLs, validate with `twine check`/`readme_renderer`.
- **Hidden count gates trip on new docs/assets.** Adding files can break hardcoded count/parity tests. *Mitigation:* run `tests/unit/config` + `tests/unit/docs` + `ai-eng check` (7/7) before push; update any count test deliberately.
- **fal.ai art off-brand or hallucinated text / cost.** *Mitigation:* fal for ART ONLY (no load-bearing text — labels live in SVG/Mermaid); `estimate_cost` before each generate; lock the navy/teal/JetBrains-Mono palette in the prompt; iterate on a cheap model before any production render.
- **Irreversible `.pen` deletion.** *Mitigation:* export to SVG and confirm the exports render before the hard-delete; repoint `brand-voice.md` in the same change.
- **Mermaid diagram-breakers** (bare `end`, `{}` in `%%` comments, unquoted nested-shape labels) ship blank diagrams. *Mitigation:* CI lint/dry-render every Mermaid block (`mmdc`).
- **VHS determinism + render deps.** *Mitigation:* CI-only render with pinned theme/fonts/dimensions, `Hide`/`Show` around setup, seeded fixtures, no volatile IDs/paths (also satisfies the anonymity hard rule).
- **Scope balloon back into the website.** *Mitigation:* D-177-12 fixes the v1 boundary; the website is its own spec.

## References

- research: .ai-engineering/runtime/research/docs-excellence-2026-06-25.md
- doc: .ai-engineering/reference/brand-voice.md
- doc: .ai-engineering/solution-intent.md
- doc: https://github.com/TauricResearch/TradingAgents
- doc: https://github.com/affaan-m/ecc
- doc: https://github.com/DietrichGebert/ponytail
