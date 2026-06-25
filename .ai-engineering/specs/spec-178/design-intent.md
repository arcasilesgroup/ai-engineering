# Design Intent — spec-178 · Public landing site for {ai} engineering

> Auto-routed from `/ai-plan` (design-routing matched: page, layout, typography,
> responsive, accessibility). This is a **composition** of spec-177's already-approved
> brand and assets (D-178-06) — NOT a new brand system. No token is invented here; every
> value is lifted verbatim from `docs/architecture/brand-tokens.md`,
> `.ai-engineering/reference/brand-voice.md`, and `.github/assets/banner-dark.svg`.

## Brand tokens (verbatim — reuse, do not redesign)

| Role | Value | Use |
|------|-------|-----|
| `--bg-deep` | `#0B1120` | page background outer / radial stop 100% |
| `--bg-mid` | `#162844` | background inner / radial stop 0% (navy gradient pairs with `--bg-deep`) |
| `--accent` | `#00D4AA` | brackets, separators, glow, wordmark braces, `[PASS]` tag, focal — **non-text accent** (AA only for large/bold/graphical >3:1, never body teal-on-navy) |
| `--border` | `#2EB39A` | 1px node/figure/card borders (solid teal carries the WCAG-AA border role) |
| `--text` | `#F8FAFB` | primary text / nodes / wordmark `ai`+`engineering` (>15:1 on navy — AAA) |
| `--muted` | `#9DB2C9` | secondary/caption text |
| `--grid` | `#FFFFFF @ 4%` | decorative grid lines only |
| `--bracket` | `#00D4AA @ 30%` | decorative corner brackets |
| `--glow` | `#00D4AA @ 8%` | decorative radial glow behind focal elements |

> Correction carried from the planning probe: the canonical accent is teal **`#00D4AA`**,
> NOT `#2C7E6D` (that value exists only in an operator memory note, never a committed
> token). The "navy" is the two-stop gradient `#162844` → `#0B1120`, not a single hex.

**Font**: JetBrains Mono (weights 400/500/600/700), self-hosted via `@fontsource/jetbrains-mono`
(no external Google Fonts request — faster, no third-party call, consistent with the
"no telemetry" ethos and the self-contained-assets decision D-178-04). Stack fallback:
`'JetBrains Mono','Fira Code','Cascadia Code','SF Mono','Consolas',monospace`. Wordmark weight 700.

**Grammar (hard, from brand-voice)**: bracketed textual status `[PASS] · [WARN] · [FAIL] · [PENDING]`
(never color-only); **no emoji anywhere**; wordmark form `{ai} engineering` (braces in `--accent`,
`ai`/`engineering` in `--text`, 700) in prose, but technical identifier `ai-engineering` for
package/repo/URL/CLI; mid-dot stat line (`54 skills · 9 agents · 6 surfaces · 1 governed flow`);
imperative second-person voice (lead with the command, then why); labelled code fences only.

## Aesthetic direction

Terminal-native editorial governance, **dark by default** (the brand has no light mode requirement
for the landing; the navy gradient IS the canvas). Generous vertical rhythm, monospace throughout,
faint 4%-white grid + 30%-teal corner brackets as the only decoration. The page reads like a
governed terminal session: command-first, proof-before-pitch, zero decorative noise.

## Page composition (single scroll, top → bottom)

Section order is fixed by spec-178 Goals — sell *usage*, not internals:

1. **Hero** — `{ai} engineering` wordmark (banner-dark.svg) · tagline
   *"Turn AI-assisted delivery into a governed local workflow — in any repo, any IDE."* ·
   the uv-first install block (`uv tool install ai-engineering` → `ai-eng install .` → `ai-eng doctor`
   `[PASS]`) with a copy-to-clipboard button · primary CTA. `hero-illustration.png` as a subtle
   right-side / background-bleed branded illustration (no load-bearing text in it).
2. **Demo reel** — `<picture>`: `demo.webp` (866 KB) as the primary `<source type="image/webp">`,
   `demo.gif` (2.6 MB) as the `<img>` fallback. **Lazy-loaded** (`loading="lazy"`, below the fold)
   with explicit `width`/`height` to prevent layout shift (mitigates the asset-weight risk).
3. **The governed workflow** — `diagrams/workflow.png` (`/ai-brainstorm → /ai-plan → /ai-build`
   or `/ai-autopilot → /ai-pr`) + the one-line chain copy + "you approve each step; the gates
   catch the rest".
4. **The six Highlights** — the six verbatim Highlight cards (titles + one-line), 1px `--border`
   cards on the navy canvas. Source copy lifted from README `## Highlights`.
5. **The toolkit** — `diagrams/toolkit.png` + the mid-dot stat line
   `54 skills · 9 agents · 6 surfaces · 1 governed flow` and the 6 surfaces
   (Claude Code, GitHub Copilot, Codex, Antigravity, OpenCode, Cursor).
6. **Why governance / social proof** — the deterministic-plane thesis in one paragraph +
   the **live** proof badges/widgets exactly as the README renders them (dynamic, not hardcoded):
   shields.io PyPI version, CI, SonarCloud quality gate + coverage, Snyk, License MIT, Python 3.11+;
   `star-history.com` chart; `contrib.rocks` contributors. (README ships NO literal version/star/
   contributor numbers — embed the same live widgets, do not invent figures.)
7. **Final CTA** — `uv tool install ai-engineering` → *"open your editor and type `/ai-start`"* +
   "ease in with observe mode" + `ai-eng update`. Repeat copy-to-clipboard.
8. **Footer** — repo link, PyPI link, license, `{ai} engineering` wordmark; `og-background.png`
   wired as the OpenGraph/Twitter social-card image in `<head>`.

## Layout · responsive · accessibility · performance

- **Responsive**: single-column, max content width ~`72ch`/`960px`, fluid type with `clamp()`,
  mobile-first; diagrams scale to container width (the source PNGs are 1840px-wide, downscale clean).
- **A11y (WCAG AA)**: body text is `--text` on navy (AAA); teal is non-text only; every image has
  real `alt` (reuse README alt text); skip-to-content link; visible `:focus-visible` ring in
  `--accent`; semantic landmarks (`<header><main><section><footer>`); `prefers-reduced-motion`
  respected on any transition.
- **Performance / JS budget**: pure static, **target ~0 KB JS** (well under the <50 KB ceiling).
  The ONLY script is a tiny inline vanilla copy-to-clipboard for the install commands — no UI
  framework, no Astro island, no hydration. `output: 'static'`, no `@astrojs/cloudflare` adapter.
- **No layout shift**: explicit `width`/`height` on every `<img>`/`<picture>`; fonts `font-display: swap`.

## Out of scope (carried from spec-178 Non-Goals)

No docs site / Starlight / `llms.txt` (phase 2), no CMS/blog/i18n, no multi-page nav, no backend,
no analytics, no new brand, no redesigned diagrams or demo, no domain purchase.
