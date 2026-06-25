---
spec: spec-178
title: Public landing site for {ai} engineering on Cloudflare Pages
status: in-progress
effort: large
summary: Build and deploy a custom Astro landing page that sells {ai} engineering and incites install, live at ai-engineering.arcasiles.com on Cloudflare Pages, reusing the spec-177 brand and assets; the docs site is a phase-2 fast-follow.
---

## Summary

spec-177 deliberately scoped the public website out (it was a fast-follow). The README is now excellent, but the only public surface is the GitHub repo — there is no branded marketing site that sells `{ai} engineering` to a developer or enterprise visitor and drives them to install. This spec builds and deploys a **custom landing page** — a single, polished, brand-consistent page — live on a real domain, reusing the spec-177 visual system (banner, the three diagrams, the demo reel, the six Highlights, the toolkit) and the README's user-facing copy. The full navigable docs site (Astro Starlight migrating `docs/` + `llms.txt`) is an explicit **phase 2**, not this spec. v1 is one landing page, deployed, on the subdomain, with no spend.

## Goals

- A custom **Astro** landing page, statically built, brand-consistent (navy/teal, JetBrains Mono, no emoji, `[PASS]` grammar), reusing the committed spec-177 assets self-contained in the site's `public/`.
- Sections, user-facing (sell usage, not internals): hero (wordmark + tagline + uv-first install + primary CTA) → demo reel → the governed workflow → the six Highlights → the toolkit (54 skills · 9 agents · 6 IDEs) → why-governance / social proof (PyPI, stars, contributors) → final CTA.
- **Deployed live** on Cloudflare Pages and reachable at **ai-engineering.arcasiles.com** (the `arcasiles.com` Cloudflare zone is active; the DNS record + Pages custom domain are wired via the Cloudflare API).
- Fast + accessible: static output, minimal JS (Astro islands; target <50 KB JS), WCAG AA contrast (reuse the spec-177 palette ratios), responsive, dark by default with the brand aesthetic.
- The site **source is versioned** in a dedicated repo (`arcasilesgroup/ai-engineering-web`), separate from the Python governance framework so its JS toolchain never touches the framework's gates or PyPI package.
- A repeatable deploy: `npm run build` → `npx wrangler pages deploy dist` (direct upload), documented so a redeploy is one command.
- An operator visual-review gate before the site goes public (brand fidelity + copy), mirroring spec-177's G1.

## Non-Goals

- **The docs site is OUT of scope** (phase 2): no Starlight, no migration of `docs/`, no `llms.txt` portal, no search. v1 is the landing only.
- **No domain purchase.** `ai-engineering.com` is deferred; v1 uses the free `ai-engineering.arcasiles.com` subdomain. No spend.
- No backend, database, server, auth, analytics pipeline, or Railway service — the site is fully static.
- The Astro site does NOT live in the `ai-engineering` Python repo (no `site/` subdir) — it is a separate repo so the governance gates, stack detection, and the PyPI build stay clean.
- No new brand system — reuse spec-177's brand-voice, palette, and committed assets verbatim; do not redesign the diagrams or the demo.
- No CMS, blog, i18n, or multi-page nav in v1.

## Decisions

### D-178-01 — Astro static landing on Cloudflare Pages

The landing is an Astro project producing static HTML, deployed to Cloudflare Pages.

**Rationale**: Research ranks Astro best-in-class for a fast, content-first OSS site (zero-JS by default, islands only where needed), and it is the same family as Starlight reserved for phase-2 docs, so the stack stays coherent. Cloudflare Pages hosts static output for $0, and the account token + account id are already provisioned — the lowest-friction path to a live, fast, brand-controllable page.

### D-178-02 — Separate repo `arcasilesgroup/ai-engineering-web`, not a subdir

The site lives in a new repo (operator has org admin), not in the Python governance repo.

**Rationale**: The website is a distinct product. Putting a JS/Astro toolchain in the Python governance repo would pollute stack detection and the gate suite, bloat the PyPI package, and couple two release cadences. A separate repo keeps each clean and lets Cloudflare Pages connect to it later for auto-deploy.

### D-178-03 — Direct `wrangler pages deploy` for v1; Git-connect deferred

v1 deploys via `npx wrangler pages deploy dist` (direct upload) rather than a Pages↔GitHub auto-deploy connection.

**Rationale**: Direct upload is the fastest path to a live URL with zero connection ceremony, ideal for the rapid landing iteration this will need. The source still lives in the repo for versioning; Git-connected auto-deploy can be added in phase 2 once the design settles.

### D-178-04 — Assets are copied self-contained into the site's `public/`

The committed spec-177 assets (the three diagram PNGs, demo gif/webp, banner SVGs, fal art) are copied into the Astro `public/`, not hot-linked from `raw.githubusercontent`.

**Rationale**: Self-contained assets load from the site's own CDN (faster, no cross-origin/main-branch coupling), survive independently of the framework repo, and let the site control sizing. It mirrors the SSOT principle — the site owns its rendered copies.

### D-178-05 — Subdomain wired via Cloudflare API on the active `arcasiles.com` zone

`ai-engineering.arcasiles.com` is created as a DNS record on the existing active `arcasiles.com` zone and attached to the Pages project as a custom domain, both via the Cloudflare API.

**Rationale**: The zone is confirmed active in the account, so a CNAME to the `*.pages.dev` target plus the Pages custom-domain binding is a free, instant, no-purchase path to a branded URL. `ai-engineering.com` purchase stays deferred (Non-Goals).

### D-178-06 — Reuse the spec-177 brand, assets, and user-facing copy verbatim

Brand, palette, diagrams, demo, and the six Highlights / toolkit / install copy are reused, not redesigned.

**Rationale**: spec-177 already converged the brand and the user-facing messaging through many operator review rounds. Reusing it guarantees consistency between the README and the site and avoids re-litigating settled design. The landing is a new *composition* of approved parts.

### D-178-07 — Landing-first; docs site is phase 2

v1 ships only the landing; the docs site is a separate later spec.

**Rationale**: Operator chose landing-first. A single deployed marketing page is the highest-impact, fastest-to-ship surface; bundling a full docs migration would delay the first live URL and balloon scope. Keeps v1 tight and shippable.

## Risks

- **Cloudflare token scope.** The API token may lack Pages-edit or DNS-edit permission. *Mitigation:* probe the token's permissions early; if Pages/DNS edits fail, surface the exact missing scope to the operator before building further (fail-loud, no silent partial deploy).
- **Pages custom-domain + DNS propagation.** The custom-domain binding and CNAME can take minutes to propagate / validate. *Mitigation:* verify the `*.pages.dev` URL works first, then wire the subdomain; treat the subdomain as a follow-on step, not a blocker for the deploy itself.
- **Brand fidelity drift on a fresh page.** A new composition risks diverging from the README's look. *Mitigation:* the G1 operator review gate before going public; reuse exact tokens/assets; render and screenshot before deploy.
- **Asset weight.** The demo gif (2.6 MB) + diagrams could slow the page. *Mitigation:* serve the 24-bit webp as the primary (`<picture>`), lazy-load below-the-fold media, set explicit dimensions to avoid layout shift.
- **Outward publication.** The site is public the moment it deploys. *Mitigation:* deploy to the `*.pages.dev` preview first for operator review (G1); only wire the public subdomain on approval.
- **Scope creep into the docs site.** *Mitigation:* D-178-07 fixes the v1 boundary; docs are a separate spec.

## References

- doc: spec-177 — the docs and visual-system rewrite this builds on
- doc: .ai-engineering/reference/brand-voice.md
- doc: README.md (the user-facing copy to reuse)
- research: .ai-engineering/runtime/research/docs-excellence-2026-06-25.md
