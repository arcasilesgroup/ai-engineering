# ai-engineering docs site

Astro Starlight site for the public documentation. The repository's
`docs/` directory remains the source of truth for ADRs and architecture
prose; this directory wraps that content with auto-generated indexes
and a navigable shell.

## Local development

```bash
cd docs-site

# 1. Install deps (Node 20+, pnpm 9 or bun 1.3 with the Astro CLI).
#    Astro currently requires the npm/pnpm/yarn toolchain because some
#    sub-deps assume Node module resolution; pin to a single PM.
pnpm install

# 2. Regenerate the auto-generated index pages from the source-of-truth
#    files in skills/, agents/, and docs/adr/.
bun scripts/generate.ts
#    (or `pnpm generate` once the npm script wraps it)

# 3. Dev server with hot reload.
pnpm dev
```

The site is then served at `http://localhost:4321/`.

## What's auto-generated

The following pages are produced by `bun scripts/generate.ts`. They are
**checked in** so the docs site builds in CI without running the
generator first; CI runs the generator and fails if the indexes are
stale (working tree dirty after regeneration):

| Generated page | Reads from |
|----------------|------------|
| `src/content/docs/skills/index.md` | `skills/catalog/*/SKILL.md` + `skills/regulated/*/SKILL.md` |
| `src/content/docs/agents/index.md` | `agents/*/AGENT.md` |
| `src/content/docs/adr/index.md`    | `docs/adr/*.md` |

Run `bun scripts/generate.ts` after editing any SKILL.md / AGENT.md /
ADR and commit the regenerated indexes alongside your change.

## Production build

```bash
pnpm build      # writes static HTML to dist/
pnpm preview    # serves dist/ locally
```

The site is intentionally **static** — no SSR, no API routes — so it
can be hosted anywhere (GitHub Pages, Cloudflare Pages, Netlify, S3 +
CloudFront, etc.). Hosting decisions land in a separate ADR before the
public launch.

## Editing the docs

- `src/content/docs/index.md` — landing page.
- `src/content/docs/quickstart.md` — 5-minute on-ramp (mirrors
  `GETTING_STARTED.md`).
- `src/content/docs/architecture/{overview,master-plan}.md` — wrappers
  around `docs/architecture/`.
- `src/content/docs/{skills,agents,adr}/index.md` — auto-generated, do
  not edit by hand.

For ADR-by-ADR pages, the public site links back to the GitHub source.
We deliberately do not duplicate ADR bodies into the site — ADRs are
versioned alongside the code they describe and changes should be
visible in the same diff.
