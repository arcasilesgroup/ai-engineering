# Conflict resolution

These skills were written independently. They contradict each other on real
decisions. Resolve with the ladder below rather than by averaging — averaging two
type scales produces a third one nobody designed.

`` `skill-name` › topic `` addresses a part of a skill; `§Heading` a section of
its `SKILL.md`. Resolve topics through the skill itself, never through a path.

## The ladder

Apply top-down. First rung that speaks to the disagreement decides it.

### 1. Hard rules beat everything

No lead, no aesthetic argument, no client preference outranks these:

| Rule | Source |
|---|---|
| Text meets contrast against its actual rendered background | `better-colors` › contrast |
| Every interactive element reachable and operable by keyboard | `better-accessibility` › focus and keyboard |
| Focus is visible wherever it lands | `better-accessibility` › focus and keyboard |
| `prefers-reduced-motion` is honored | `better-accessibility` › motion and zoom, and `animate` §Hard Rules |
| Hit areas clear the conformance floor; nothing is hover-only on touch | `better-accessibility` › hit areas |
| Meaning is never carried by color alone | `better-accessibility` §Don't rely on color alone |
| Inputs are 16px on mobile | `better-typography` › details and accessibility |

Read the source for the actual threshold rather than quoting a number from
memory — several of these carry a conformance floor and a separate, higher
usability target, and the two are not interchangeable.

If a lead's prescribed value violates one of these, the value changes and the
lead's intent is preserved by other means. A hero headline that fails contrast
gets a scrim or a different background, not a shrug.

### 2. The Lead owns structure and tokens

Within one project, exactly one skill decides: section order, spacing scale,
type scale, radius scale, palette, and motion vocabulary.

A consultant may say *"this violates a hard rule"* or *"this is inconsistent with
what you already set."* A consultant may **not** substitute its own scale.

The frequent collision: `landing-page-design` Part B states literal values
(specific sizes, radii, spacing steps) while `better-typography` and
`better-layout` state principles. When `landing-page-design` leads, its literals
stand and the `better-*` skills check consistency against them. When it does not
lead, its Part B is a reference, not a rule.

### 3. One motion engine, chosen by the Lead

Never ship GSAP and CSS transitions competing on the same elements, and never
two smooth-scroll libraries.

| Lead | Engine | Motion authority |
|---|---|---|
| `build-threejs-scroll-worlds` | GSAP, plus its own scroll conductor | its scroll conductor — don't stack Lenis on top without checking |
| `build-awwwards-quality-sites` | GSAP + Lenis | `cinematic-gsap-lenis-motion-system` §Init Order |
| `landing-page-design` | CSS by default; GSAP only if the page already loads it | §B7 Motion choreography |
| `tastemaker` | CSS / Web Animations | › animation guidelines; its GSAP starter if escalating |
| `web-design-engineer` | CSS / Web Animations | › advanced patterns |
| `emil-design-eng`, `animate` | CSS / Web Animations / springs | their own frameworks |

Ingredients declare an engine (see the routing table). Adding `masked-reveal`
(GSAP) to a CSS-only project means either adopting GSAP project-wide or
reimplementing the effect in CSS. Decide once, at Phase 4, out loud.

### 4. Specificity beats breadth

When two skills both legitimately cover a decision, the narrower one wins.

- Hero layout: `landing-page-design` §B5 over `tastemaker` › hero guidelines over `perception-laws`.
- Should this animate: `animate` §The Build Sequence over `better-ui` › animations over general taste.
- Spring physics: `emil-design-eng` §Spring Animations over anything else.
- A named anchor ("Linear-style"): that one `web-design-engineer` style recipe over the lead's default mood.

### 5. Build skills beat review skills during a build

`screen-critique`, `better-interface`, and `tastemaker`'s audit mode judge
finished work. Running them mid-build produces findings about a half-built page.
Hold them for Phase 5.

The inverse also holds: during a review, no build skill gets to start editing.
The `review` and `explain` verbs do not touch files.

### 6. Explicit user instruction beats every rung above except rung 1

If the user says "I want 24px radius everywhere" and the lead prescribes 12,
theirs wins. Say once that it diverges from the lead's system, then do it. Do not
re-raise it later.

Rung 1 is the exception: if a user's instruction would break keyboard access or
contrast, say so plainly, offer the nearest thing that works, and let them
decide.

---

## Named collisions

Situations that come up often enough to pre-decide.

**`landing-page-design` vs `tastemaker` on a landing page.**
Structure, copy, section order, and Part B literals → `landing-page-design`.
Palette derivation, reference matching, asset sourcing, and the anti-slop gate →
`tastemaker`. Neither runs its full workflow; the lead's phases absorb the
other's parts.

**`tastemaker` vs `web-design-engineer` on "make it look good".**
Reference image or URL in the request, or the complaint is that it looks
AI-generated → `tastemaker`. A named anchor style, a dashboard, slides, or data
viz → `web-design-engineer`. Both have a full workflow; running both is the
single most wasteful mistake available here.

**`animate` vs `emil-design-eng` vs `better-ui` on motion.**
Building from nothing → `animate`. Judging or fixing what exists →
`emil-design-eng`. Checking a specific property or pattern against a rule →
`better-ui` › animations or › enter and exit. All three agree on the
fundamentals; they differ in altitude, not opinion.

**`better-interface` vs `interface-review` on scope.**
A screen, flow, or feature → `better-interface`. A diff, branch, or PR →
`interface-review`, which is user-invoked. `better-interface` will refuse to
resolve a change scope and hand it up; don't work around that by guessing.

**`build-awwwards-quality-sites` vs `cinematic-gsap-lenis-motion-system`.**
Not a conflict — a layering. The former sets art direction and the quality bar;
the latter supplies the implementations. Lead with the former, open the latter at
Phase 4.

**Two ingredients on the same surface.**
`progressive-blur` over `dither-background` is fine. `masked-reveal` plus
`reveal-hover-effect` on the same element is not — one owns the element's
transform. Assign each element exactly one ingredient.
