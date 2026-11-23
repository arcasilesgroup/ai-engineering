---
"ai-engineering": patch
---

One design system for every HTML artifact, with the gates that keep it honest.

`brand/components.css` and `brand/components.js` now carry the component layer —
diagrams, tabs, copy blocks, filters, steps, checklists, callouts, category chips,
verdict and terminal cards — beside `brand/tokens.json`. `bun scripts/brand.ts gen`
inlines them between markers into all eight templates and into `brand/gallery.html`,
the gallery that shows every part live with the markup that makes it, and `parity`
fails on a hand edit. Every colour pair a component uses is declared in
`tokens.json` and measured by `brand.ts contrast`; prose is left-aligned, and code
wells moved onto `--surface` where a comment clears 4.5:1.

Two gates protect the result. `tests/artifact-a11y.spec.ts` runs a static
accessibility gate inside `bun test` — language, one rendered `h1`, heading order,
table captions and header scope, SVG names, resolvable and unique ids, no external
request, no inline handler, zoom, and the forced-colours, reduced-motion and print
layers — with one failing fixture per rule. `bun run a11y` opens all nine pages in
the system Chrome at 320, 390, 768 and 1440px and under forced colours, runs
axe-core's WCAG 2.0, 2.1 and 2.2 A and AA rules, walks every tab set with the
keyboard, and proves 320px reflow and the no-script reading. It runs as its own CI
job so the unit suite still passes without Chrome.

The templates also ship ready slots — a diagram with a text version, decisions with
expand all, a stats row and options in tabs — and the page templates now install
beside the skills.
