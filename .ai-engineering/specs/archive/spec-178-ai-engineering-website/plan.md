---
title: Public landing site for {ai} engineering on Cloudflare Pages
spec: spec-178
status: approved
pipeline: full
architecture: jamstack-static-site (Astro islands → static dist → Cloudflare Pages CDN)
execution_route:
  version: 1
  spec: spec-178
  executor: build
  automation: operator-in-the-loop
  concern_count: 7
  estimated_files: 22
  reason: >-
    Multi-concern (external-repo bootstrap, credential preflight, brand/asset
    port, section composition, build + a11y/perf verification, *.pages.dev
    deploy, public DNS wiring) and ≥10 files — but routed to /ai-build rather
    than /ai-autopilot for the same reasons spec-177 was: the work is
    taste-driven (brand-fidelity composition) and gated on a human visual
    review (G1) before anything goes public, plus an outward, hard-to-reverse
    deploy + DNS step. Autopilot's autonomous sub-spec decomposition and
    in-repo worktree model do not fit an EXTERNAL-repo, deploy-gated landing.
  safe_next_command: "/ai-build"
---

# Plan — spec-178 · Public landing site for {ai} engineering on Cloudflare Pages

## Architecture

Jamstack / static-site. Astro produces static HTML to `dist/` (zero client JS by default;
one tiny inline copy-to-clipboard script is the only JS), deployed by direct upload
(`wrangler pages deploy dist`) to Cloudflare Pages' CDN, fronted by a proxied CNAME on the
existing `arcasiles.com` zone. No backend, no adapter, no SSR. The dependency order is forced:
credential preflight → repo + scaffold → brand/asset foundation → section composition →
local build/a11y/perf verification → preview deploy (Gate G1) → public DNS (post-approval).

## Execution context (read before /ai-build)

**The build does NOT happen in this Python governance repo.** Per D-178-02 the site lives in a
NEW, separate repo `arcasilesgroup/ai-engineering-web`, checked out to a sibling working
directory (`$HOME/repos/ai-engineering-web` — adjust to taste). This repo's Python gates
(gitleaks/ruff/pip-audit/pytest) do NOT apply to the JS site; the site repo carries its own
build/lint as its gate. When `/ai-build` runs, its build agent operates against the sibling
site directory, not a worktree of this repo. Asset SOURCES are read from this repo's
`.github/assets/` and COPIED into the site's `public/` (D-178-04). Credentials
(`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`) are already present in the shell env and are
NEVER printed or committed.

## Design

Design intent captured at `.ai-engineering/specs/spec-178/design-intent.md` (auto-routed from
`/ai-plan` because matched keywords: page, layout, typography, responsive, accessibility). It is
a **composition** of spec-177's approved brand + assets (D-178-06), not a new brand. Palette navy
`#0B1120`→`#162844`, accent teal `#00D4AA`, text `#F8FAFB`, border `#2EB39A`, JetBrains Mono
(self-hosted), `{ai} engineering` wordmark, `[PASS]` grammar, no emoji. Eight-section single-scroll
landing; ~0 KB JS; WCAG AA; dark by default. Social proof reuses the README's LIVE badges/widgets
(no hardcoded version/star/contributor numbers — the README ships none).

## Operator review gates

- **G1 (after Phase 4 — HARD STOP, outward action)** — the site is deployed to its private
  `*.pages.dev` preview URL ONLY. Operator eyeballs brand fidelity + copy on the live preview
  before any public DNS is wired. Off-brand → fix in Phase 1–2, redeploy, re-review here.
  Mirrors spec-177's G1 and spec-178's explicit visual-review gate.
- **G2 (after Phase 6)** — final green: static build clean, JS budget under the ceiling,
  WCAG-AA checks pass, and the public URL returns 200 over HTTPS.

## Risks carried into tasks

- CF token may lack `Pages:Edit` and/or `DNS:Edit` → **T-0.1 fails loud** before any build work.
- Custom-domain + CNAME propagation is async → Phase 5 polls `status==active`; the `*.pages.dev`
  deploy (Phase 4) is the real milestone, the subdomain is a follow-on, never a blocker.
- Demo gif weight (2.6 MB) → webp-primary `<picture>` + lazy-load + explicit dimensions (Phase 2).
- The site is public the instant DNS resolves → Phase 5 runs ONLY after G1 approval.

---

## Phase 0 — Credential preflight + external-repo bootstrap

- [x] T-0.1 — Verify Cloudflare token scope + resolve account/zone IDs (FAIL LOUD) — PASS: zone `arcasiles.com` active + zone_id resolved; `#dns_records:edit` confirmed; Pages read 200 + precedent `si.arcasiles.com` (Pages:Edit confirmed at first deploy). Token never printed.
  - Agent: verify
  - Files: (read-only API probe; no repo files) — `$HOME/repos/ai-engineering-web` not yet created
  - Principles applied: §10.4 Goal-Driven (green preflight before any build), §10.7 Clean Code
  - Patch (deterministic): omit — `npx wrangler whoami` (or `GET /client/v4/user/tokens/verify`) to confirm auth; confirm the token carries `Account > Cloudflare Pages: Edit` AND `Zone > DNS: Edit`; resolve `account_id` from env and `zone_id` for `arcasiles.com` via `GET /client/v4/zones?name=arcasiles.com` → `result[0].id`; confirm the zone is on this Cloudflare account. If Pages or DNS edit is missing, STOP and surface the exact missing scope to the operator (no silent partial deploy). NEVER print token values.
  - Gate: token verified; Pages:Edit + DNS:Edit confirmed; `zone_id` for arcasiles.com captured; else hard stop with the named missing scope

- [x] T-0.2 — Create the dedicated repo + sibling checkout
  - Agent: build
  - Files: `$HOME/repos/ai-engineering-web/` (new working tree), `.gitignore`, `LICENSE` (MIT)
  - Principles applied: §10.2 YAGNI (separate repo keeps JS out of the Python gates — D-178-02), §10.7 Clean Code
  - Patch (deterministic): omit — `gh repo create arcasilesgroup/ai-engineering-web --public --clone` into the sibling dir (operator may choose `--private`; default public matches the OSS posture); seed MIT `LICENSE` and a Node `.gitignore` (`node_modules`, `dist`, `.astro`, `.wrangler`).
  - Gate: repo exists on `arcasilesgroup`; cloned locally; `git remote -v` resolves

- [x] T-0.3 — Scaffold minimal static Astro (TS strict)
  - Agent: build
  - Files: `package.json`, `astro.config.mjs`, `tsconfig.json`, `src/pages/index.astro` (placeholder)
  - Principles applied: §10.1 KISS (minimal template, no UI framework), §10.8 Hexagonal (deploy is an outbound adapter, not core)
  - Patch (deterministic): omit — `npm create astro@latest . -- --template minimal --typescript strict --no-git`; set `astro.config.mjs` to `output: 'static'`, `build.format: 'directory'`; add `@fontsource/jetbrains-mono`; pin Node engine ≥20.3. No `@astrojs/cloudflare` adapter (static only).
  - Gate: `npm run build` emits `dist/index.html`; `dist` carries 0 framework JS chunks

---

## Phase 1 — Brand foundation + self-contained asset port

- [x] T-1.1 — Copy the 9 spec-177 assets into the site `public/` (self-contained — D-178-04)
  - Agent: build
  - Files: `public/banner-dark.svg`, `public/banner-light.svg`, `public/demo.webp`, `public/demo.gif`, `public/diagrams/workflow.png`, `public/diagrams/toolkit.png`, `public/art/hero-illustration.png`, `public/art/og-background.png` (+ `public/diagrams/install.png` if an install section is added)
  - Principles applied: §10.4 DRY (one rendered copy owned by the site), §10.7 Clean Code
  - Patch (deterministic): omit — copy verbatim from this repo's `.github/assets/{banner-*,demo.*,diagrams/*,art/*}`; do NOT hot-link `raw.githubusercontent`. Byte-identical copies; no re-encode.
  - Gate: 8 (or 9) files present in `public/`; sha256 matches the source assets; total media weight logged

- [x] T-1.2 — Author the brand-token CSS (single source for the site)
  - Agent: build
  - Files: `src/styles/tokens.css`
  - Principles applied: §10.4 DRY (one palette/type block the whole site consumes), §10.7 Clean Code
  - Patch (deterministic): omit — `:root` custom properties for `--bg-deep #0B1120`, `--bg-mid #162844`, `--accent #00D4AA`, `--border #2EB39A`, `--text #F8FAFB`, `--muted #9DB2C9`, grid/bracket/glow alphas, lifted verbatim from `docs/architecture/brand-tokens.md` / `banner-dark.svg`; JetBrains Mono stack; `[PASS]/[WARN]/[FAIL]` utility classes; `font-display: swap`. No emoji.
  - Gate: hex values byte-match `docs/architecture/brand-tokens.md`; no emoji; teal used only on non-text/large elements

- [x] T-1.3 — Base layout: head, OG/Twitter meta, fonts, global CSS, a11y scaffolding
  - Agent: build
  - Files: `src/layouts/Base.astro`, `src/styles/global.css`
  - Principles applied: §10.3 SOLID (one layout owns the document shell), §10.7 Clean Code
  - Patch (deterministic): omit — `<html lang="en">`, dark-by-default navy-gradient `body`, JetBrains Mono import, skip-to-content link, semantic landmarks, `:focus-visible` ring in `--accent`, `prefers-reduced-motion` guard; OG/Twitter card tags using `og-background.png`, canonical URL `https://ai-engineering.arcasiles.com`, title + description from the hero copy.
  - Gate: `<html lang>` set; skip-link present; OG image + canonical resolve; axe finds no critical landmark/contrast issues on the empty layout

---

## Phase 2 — Landing section composition (one task per section)

- [x] T-2.1 — Hero (wordmark · tagline · uv-first install · primary CTA · copy button)
  - Agent: build
  - Files: `src/components/Hero.astro`, `src/components/CopyButton.astro` (the only JS)
  - Principles applied: §10.1 KISS (vanilla inline copy script, no island), §10.7 Clean Code
  - Patch (deterministic): omit — banner-dark.svg wordmark; tagline "Turn AI-assisted delivery into a governed local workflow — in any repo, any IDE."; labelled `bash` block `uv tool install ai-engineering` → `ai-eng install .` → `ai-eng doctor` (`[PASS]`); tiny inline vanilla `navigator.clipboard` copy button as a real `<button>` with `aria-label="Copy install command"` + an `aria-live="polite"` status region announcing "Copied" (WCAG 4.1.2 name/role + 4.1.3 status messages); `hero-illustration.png` as background-bleed art with explicit dims.
  - Gate: renders; install commands copy to clipboard; copy button has accessible name + `aria-live` status confirmation (4.1.2/4.1.3); JS for the whole page stays well under 50 KB; alt text present

- [x] T-2.2 — Demo reel (`<picture>` webp-primary, gif fallback, lazy, dimensioned)
  - Agent: build
  - Files: `src/components/Demo.astro`
  - Principles applied: §10.1 KISS, §10.7 Clean Code
  - Patch (deterministic): omit — `<picture>` with `<source type="image/webp" srcset="/demo.webp">` + `<img src="/demo.gif" loading="lazy" width=.. height=.. alt="...">`; mitigates the 2.6 MB weight risk (webp served first, gif lazy below the fold). **WCAG 2.2.2 (Pause/Stop/Hide):** the looping reel auto-plays >5s, so default to a STATIC poster frame with a click-to-play control (load the gif/webp only on activation), and serve the static poster under `prefers-reduced-motion: reduce`. No always-on auto-loop.
  - Gate: webp is the served source on supporting browsers; no layout shift (explicit dims); gif lazy-loads; **2.2.2** — demo is click-to-play (no auto-loop), static poster under reduced-motion

- [x] T-2.3 — The governed workflow (workflow.png + chain copy)
  - Agent: build
  - Files: `src/components/Workflow.astro`
  - Principles applied: §10.4 DRY (reuse the committed diagram + canonical chain string), §10.7 Clean Code
  - Patch (deterministic): omit — `diagrams/workflow.png` (responsive, explicit dims) + the chain `/ai-brainstorm → /ai-plan → /ai-build` or `/ai-autopilot → /ai-pr` + "you approve each step; the gates catch the rest".
  - Gate: diagram scales to container; chain string matches CANONICAL §11

- [x] T-2.4 — The six Highlights (verbatim cards)
  - Agent: build
  - Files: `src/components/Highlights.astro`
  - Principles applied: §10.4 DRY (copy lifted verbatim from README `## Highlights`), §10.3 SOLID
  - Patch (deterministic): omit — six `--border` cards on navy, titles + one-line each, copied verbatim (autopilot one-run, approved=shipped SDD, owned audit trail, every-bypass-has-owner, deterministic tool guard, pass@k quality gate). No emoji; teal accents only on rules/brackets.
  - Gate: exactly six cards; text byte-matches README Highlights; AA contrast

- [x] T-2.5 — The toolkit (toolkit.png + mid-dot stat line + 6 surfaces)
  - Agent: build
  - Files: `src/components/Toolkit.astro`
  - Principles applied: §10.4 DRY (reuse diagram + canonical counts), §10.7 Clean Code
  - Patch (deterministic): omit — `diagrams/toolkit.png` + stat line `54 skills · 9 agents · 6 surfaces · 1 governed flow` + the 6 surfaces (Claude Code, GitHub Copilot, Codex, Antigravity, OpenCode, Cursor).
  - Gate: stat line matches CANONICAL counts (54/9/6); diagram responsive

- [x] T-2.6 — Why governance / social proof (thesis + LIVE badges/widgets)
  - Agent: build
  - Files: `src/components/Proof.astro`
  - Principles applied: §10.4 DRY (reuse the README's live badge URLs), §10.7 Clean Code
  - Patch (deterministic): omit — one deterministic-plane thesis paragraph + the README's live shields.io badges (PyPI version, CI, SonarCloud gate + coverage, Snyk, MIT, Python 3.11+), `star-history.com` chart, `contrib.rocks` contributors. Do NOT hardcode version/star/contributor numbers — the README ships none.
  - Gate: badges are live `img` URLs (not pinned numbers); links resolve; no invented figures

- [x] T-2.7 — Final CTA + footer (and assemble `index.astro`)
  - Agent: build
  - Files: `src/components/FinalCta.astro`, `src/components/Footer.astro`, `src/pages/index.astro`
  - Principles applied: §10.3 SOLID (index composes sections in spec order), §10.7 Clean Code
  - Patch (deterministic): omit — final CTA `uv tool install ai-engineering` → "open your editor and type `/ai-start`" → observe-mode line → `ai-eng update`; footer repo/PyPI/MIT links + wordmark; `index.astro` mounts Hero→Demo→Workflow→Highlights→Toolkit→Proof→FinalCta→Footer inside `Base.astro` in the exact spec-178 order.
  - Gate: full page renders top-to-bottom in spec order; all internal anchors resolve

---

## Phase 3 — Local build, accessibility + performance verification

- [x] T-3.1 — Assert static build + JS budget + a11y + responsive (the green contract)
  - Agent: verify
  - Files: `dist/**` (build output, read-only), site `README.md` checks
  - Principles applied: §10.5 TDD (assert the acceptance contract), §10.4 Goal-Driven
  - Patch (deterministic): omit — `npm run build`; assert `dist/` is static HTML; measure total JS (target ~0 KB, hard ceiling <50 KB); run axe/pa11y for WCAG-AA (contrast 1.4.3/1.4.11, landmarks 1.3.1, alt 1.1.1, focus 2.4.7, skip-link 2.4.1, lang 3.1.1); assert the demo honours **2.2.2** (click-to-play, no auto-loop; static under reduced-motion) and the copy button satisfies **4.1.2/4.1.3** (accessible name + `aria-live` status); check every `<img>`/`<picture>` has explicit `width`/`height` (no CLS); verify webp-primary + gif-lazy; smoke responsive at 360/768/1280px.
  - Gate: build static + clean; JS < 50 KB; zero axe critical/serious; 2.2.2 + 4.1.2/4.1.3 satisfied; all media dimensioned; webp served first

---

## Phase 4 — Deploy to *.pages.dev preview  (→ Gate G1, HARD STOP)

- [x] T-4.1 — Create the Pages project + direct-upload deploy to the private preview URL — DONE: project `ai-engineering-web` created (Pages:Edit confirmed); deployed → https://ai-engineering-web.pages.dev (200). **G1 HARD STOP — awaiting operator visual review before Phase 5 public DNS.**
  - Agent: build
  - Files: site `README.md` (record the `*.pages.dev` URL + one-command redeploy)
  - Principles applied: §10.8 Hexagonal (wrangler is the deploy adapter), §10.4 Goal-Driven
  - Patch (deterministic): omit — `npx wrangler pages project create ai-engineering-web --production-branch=main` (name is lowercase/hyphen, immutable → becomes `ai-engineering-web.pages.dev`); then `npx wrangler pages deploy dist --project-name=ai-engineering-web --branch=main`, authed via the `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` env vars (no `wrangler login`). Capture the live `*.pages.dev` URL. Do NOT wire the public subdomain yet.
  - Gate: `*.pages.dev` URL returns 200 over HTTPS; page renders; **STOP for G1 operator visual review before Phase 5**

---

## Phase 5 — Wire public subdomain (ONLY after G1 approval)

- [x] T-5.1 — Attach the custom domain to the Pages project + create the proxied CNAME — DEFERRED (operator: close on preview; public subdomain ai-engineering.arcasiles.com is a follow-up)
  - Agent: build
  - Files: (Cloudflare API calls; site `README.md` deploy notes)
  - Principles applied: §10.8 Hexagonal (DNS/Pages API as outbound adapters), §10.4 Goal-Driven
  - Patch (deterministic): omit — order matters: (1) `POST /accounts/{acct}/pages/projects/ai-engineering-web/domains` with `{"name":"ai-engineering.arcasiles.com"}`; (2) `POST /zones/{zone_id}/dns_records` with `{"type":"CNAME","name":"ai-engineering","content":"ai-engineering-web.pages.dev","proxied":true,"ttl":1}` (proxied is REQUIRED for the cert; ttl 1 = automatic). Use the `zone_id` from T-0.1.
  - Gate: both API calls return success envelopes; custom-domain record created; CNAME present and proxied

- [x] T-5.2 — Poll custom-domain status to active + verify the public URL — DEFERRED (follow-up with T-5.1)
  - Agent: verify
  - Files: (read-only API poll + HTTPS fetch)
  - Principles applied: §10.4 Goal-Driven (don't assume instant), §10.7 Clean Code
  - Patch (deterministic): omit — poll `GET /accounts/{acct}/pages/projects/ai-engineering-web/domains/ai-engineering.arcasiles.com` until `status==active` (cert issuance can take minutes; tolerate transient 522/525); then `curl -I https://ai-engineering.arcasiles.com` expects 200 + valid TLS.
  - Gate: domain `status==active`; `https://ai-engineering.arcasiles.com` returns 200 with a valid Cloudflare-issued cert

---

## Phase 6 — Document redeploy + commit site source (→ Gate G2)

- [ ] T-6.1 — Write the site README (one-command redeploy) + commit & push the source
  - Agent: build
  - Files: site `README.md`, full `arcasilesgroup/ai-engineering-web` tree
  - Principles applied: §10.7 Clean Code (a redeploy is one documented command), §10.6 SDD
  - Patch (deterministic): omit — README documents `npm run build && npx wrangler pages deploy dist --project-name=ai-engineering-web --branch=main` (D-178-03 repeatable deploy), the env vars needed, and the asset-reuse note; conventional-commit the whole tree; push to `main`.
  - Gate: README documents the one-command redeploy; source committed + pushed; **G2** — build green, JS under ceiling, a11y AA, public URL 200

---

## Verification matrix (G2)

| Acceptance (spec-178 Goals) | Gate task |
|---|---|
| Custom Astro static landing, brand-consistent, self-contained assets | T-1.1, T-3.1 |
| All spec-required sections in order, user-facing copy reused | T-2.1–T-2.7 |
| Deployed live on Cloudflare Pages | T-4.1 |
| Reachable at ai-engineering.arcasiles.com | T-5.2 |
| Fast + accessible (static, <50 KB JS, WCAG AA, responsive) | T-3.1 |
| Source versioned in arcasilesgroup/ai-engineering-web | T-0.2, T-6.1 |
| Repeatable one-command redeploy documented | T-6.1 |
| Operator visual-review gate before public | G1 (Phase 4 → 5 boundary) |
