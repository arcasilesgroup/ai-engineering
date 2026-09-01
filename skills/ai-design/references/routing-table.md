# Routing table

**Which part to open, once a skill is elected.** This is the second half of
routing. The first half — *which skill*, decided by matching a request's dominant
constraint to what each skill is for — lives in `skill-purposes.md`. Come here
after that, not instead of it.

**Notation.** `` `skill-name` › topic `` is *the part of that skill covering that
topic*. `§Heading` is a section of that skill's own `SKILL.md`. Nothing here is a
file path — resolve a topic by reading the skill's own routing table, then its
headings. See "How to address a skill" in `SKILL.md`.

Topics name subjects, not filenames. A skill that renamed or merged its
references still answers the same question; match on meaning.

Role legend — **Lead** may own a build · **Consult** opens at a named part ·
**Ingredient** is a drop-in recipe · **Gate** runs at the end · **User-only**
cannot be auto-invoked.

---

## Leads

### `build-threejs-scroll-worlds` — Lead
Scroll-controlled real-time 3D as one persistent world with authored chapters.
Owns camera, lighting, atmosphere, materials, DOM story. **Brings GSAP.**

| Need | Open |
|---|---|
| Decide if the request is really a 3D world | §Route the request correctly |
| Before any code | §Write the world bible, then › the world bible reference |
| Scene sequencing | §Author a scene ledger, then › the scene anatomy reference |
| Scroll → state mapping | §Map native scroll to deterministic state, then › the scroll conductor it ships |
| Engine structure | › realtime architecture |
| Perf budget + QA | §Hold a measurable performance budget, then › quality and QA |

### `build-awwwards-quality-sites` — Lead
Motion-rich marketing, editorial, portfolio sites. Seven numbered stages, art
direction first. **Brings GSAP + Lenis.** Defers implementation detail to
`cinematic-gsap-lenis-motion-system`.

Stages: 1 art direction · 2 honest asset system · 3 hero · 4 motion system ·
5 Three.js only with purpose · 6 quality bar · 7 validate before handoff.

### `landing-page-design` — Lead
The most prescriptive skill here. Split in two halves, routable independently.

| Need | Open |
|---|---|
| Intake questions (best in the collection — borrow for other leads) | §A1 |
| Section order and page structure | §A2, §A3 |
| Conversion rules and CTA logic | §A4 |
| Headline / body copywriting | §A5 |
| Build order | §A6 |
| SEO and AEO | §A7 |
| Hard visual rules — type, spacing, radius, backgrounds, hero, icons, motion | §B1–B7 |
| Realistic content, states, ship requirements | §B8–B10 |

Part B states literal values (sizes, radii, spacing). When it conflicts with a
consultant, Part B wins on this page — see `conflicts.md`.

### `tastemaker` — Lead, and the most common consultant
Anti-slop UI generation with a project-local memory of past decisions. Four
modes; detect the mode **before** starting.

| Mode | Open |
|---|---|
| build *(default)* | §Workflow, Steps 0–5 |
| study a reference | › study mode |
| audit existing UI (no edits) | › audit mode |
| reference comps, no code | › comps mode |

Highest-value parts when consulting rather than leading:

| Need | Open |
|---|---|
| Ranked "does this look AI-generated" gate list | › anti-slop checklist |
| Page macrostructure choice | › macrostructures |
| Avoid every page looking the same | › diversification |
| Hero composition | › hero guidelines |
| Palette from scratch or from a reference | › its palette generation and palette extraction scripts |
| Contrast check | › its contrast-check script |
| Motion audit | › its motion-audit script |
| Anti-slop scan | › its anti-slop scan script |
| Icons / photos / logos, sourced honestly | › asset curation, logo sourcing, illustration sources |
| Original SVG illustration | › its bundled illustration system |
| Persist decisions across sessions | › taste memory and the style-lock format |

It ships an aesthetic-mode hook: an opt-in named style override (brutalist,
minimalist, …) layered over the same engine. Check whether the project already
has one active before picking a mood.

### `web-design-engineer` — Lead, widest scope
Pages, dashboards, prototypes, slide decks, animations, mockups, data viz. Use
when nothing more specific matched.

| Need | Open |
|---|---|
| Five dials + design read | › design calibration |
| Vague request → propose 3 directions | › design directions |
| Named anchor ("Linear-style") | › the style recipe for that anchor — one only |
| Browse anchors | › the style-recipe index |
| Redesign an existing project safely | › redesign protocol |
| Known-good component pattern | › block library, then the matching section of › advanced patterns |
| Slides, device frames, tweaks panel, dark mode, oklch, data viz | › advanced patterns |
| Recurring AI failure modes | › failure patterns |
| Critique rubric | › critique guide |
| Browser QA / responsive verification | › browser acceptance |

It carries roughly two dozen named style anchors — product (Linear, Raycast,
Vercel, Notion, Apple HIG), editorial and print (Monocle, Businessweek, NYT,
Tufte, Pentagram, Vignelli, Rams, Muji), retail and brand (Aesop, Stripe Press,
Balenciaga, Mailchimp, Headspace), and experimental (Active Theory, Field, Resn,
Are.na, Y2K, mid-century). Read the index to see what's actually installed
rather than assuming a given anchor exists.

### `emil-design-eng` — Lead for components, consultant for motion
Emil Kowalski's polish philosophy. Deepest motion reasoning in the collection.

| Need | Open |
|---|---|
| Should this animate at all | §The Animation Decision Framework |
| Spring vs duration | §Spring Animations |
| Component API and composition | §Component Building Principles |
| Transform correctness | §CSS Transform Mastery |
| clip-path animation | §clip-path for Animation |
| Drag and gesture | §Gesture and Drag Interactions |
| GPU / jank | §Performance Rules |
| What makes a component loved | §The Sonner Principles |
| Stagger | §Stagger Animations |
| Debug a janky animation | §Debugging Animations |
| Final pass | §Review Checklist |

### `animate` — Lead when motion is the whole deliverable
Decisions in the order that determines whether motion feels right.

§Operating Posture · §Hard Rules · §The Build Sequence (should it animate →
purpose → tool → properties → curve and duration → interruption → exit) ·
§Recipes, which points at its recipe collection · §Never Ship.

Use `animate` to build motion from nothing; use `emil-design-eng` to judge motion
that exists.

---

## Consultants — the `better-*` family

`better-interface` routes across all of these and consolidates one ranked
verdict. When the request is a holistic review, hand it the whole job rather than
opening the members individually. Its output shape lives at
`better-interface` › review format.

Each member splits into topic references. Ask for the topic; the skill knows
where it keeps it.

### `better-colors`
› palette generation · palette structure · token naming · contrast ·
color formats (oklch, p3, conversion) · color usage (one color one meaning;
exactly one filled action per view).

Governing ideas: a system is ramps not colors; every step has a job; name
primitives by hue and semantics by role; hold the hue across the ramp; measure
the rendered pair before reporting.

### `better-typography`
› choosing fonts · spacing and sizing (scale, line-height by role,
letter-spacing by size, measure cap) · wrapping and punctuation ·
variable fonts and OpenType · details and accessibility (16px inputs on mobile,
size and contrast floors) · CSS cheat sheet.

### `better-layout`
› grouping and alignment (group with space not lines; align to shared edges;
controls distinct from content) · spacing and adaptivity (hold structure until it
breaks; content bleeds, controls float; plan for growth and clipping).

### `better-ui`
› surfaces (concentric radius, shadows for elevation / borders for structure,
image outlines) · animations (interruptible, motion restraint, transition only
what changes, `will-change` sparingly) · enter and exit (split and stagger enter,
subtle exit, skip on page load) · icons (stroke matched to text weight, one SVG
recolored per state) · icon transitions · performance.

### `better-accessibility`
› semantics and ARIA (native first, accessible names, structure is navigation) ·
focus and keyboard (visible rings, full keyboard, trap and restore) · forms
(label and type every control, errors that announce) · hit areas ·
motion and zoom (`prefers-reduced-motion`, survive zoom) · screen readers.

On hit areas it separates the conformance floor from the usability target —
24×24px is the WCAG AA hard floor, 44px the touch recommendation. Read it rather
than quoting a single number.

### `better-writing`
Whole skill, it is short. Verb-first buttons · links describe their destination ·
one capitalization policy · settings describe the ON state · errors say how to
fix next to where it broke · empty states point forward · placeholders are
examples not labels. Start with §Recon the existing voice.

---

## Composition and diagnosis

### `perception-laws` — Consult at Phase 2, always
Why grouping works, not whether it looks nice. §Grouping (proximity, similarity,
common region, closure, continuity, figure-ground, isolation) · §Flow (reading
order, continuity, serial position) · §Cognition (Hick, Miller, Fitts).

Open this **before** placing sections, not after.

### `screen-critique` — Gate
Rates a rendered screen across seven dimensions and returns a prioritized fix
list: 1 visual hierarchy · 2 composition · 3 typography · 4 colour ·
5 information density · 6 affordance · 7 brand consistency.

Use when a layout is wrong and nobody can name why.

### `interfaces-that-feel` — Consult
For UI that passes every check and still lands cold. §The Translation Process ·
§Emotional Timing Principles · §Copy Voice by State · §Motion as Emotional
Signal. Prescribes at the copy, motion, and interaction layer — it does not
restructure.

---

## Ingredients

Self-contained. Each brings its own markup and CSS/JS; none restructure a page.

| Skill | Produces | Engine |
|---|---|---|
| `cinematic-gsap-lenis-motion-system` | Full motion vocabulary: staggered text, scroll reveals, clip image reveals, parallax, pinned sections, magnetic hover, custom cursor, mouse-reactive layers. §Init Order matters. | GSAP + Lenis |
| `masked-reveal` | Word-by-word reveal through an overflow mask on scroll | GSAP ScrollTrigger |
| `progressive-blur` | Stepped `backdrop-filter` masks fading from a viewport edge | CSS |
| `dither-background` | Near-black Bayer-dithered field with enlarged pixels | Canvas/shader |
| `container-lines` | Vertical container guides with corner squares | CSS |
| `reveal-hover-effect` | Cursor-following radial spotlight over a second aligned image | JS + CSS |

`cinematic-gsap-lenis-motion-system` is large enough to feel like a lead. It
isn't — it has no intake, no structure, no content strategy. Pair it with a lead.

---

## User-invoked only

Never auto-fire. Name them and stop.

| Skill | For | Why it's gated |
|---|---|---|
| `interface-review` | Reviewing a **change**: branch, PR, commit range, uncommitted work | Diff scope resolution must be deliberate. `better-interface` explicitly refuses to guess at it and hands up to here. |
| `explain-interface` | "How was this built?" against a URL | Reads a live page; from a screenshot it reconstructs and says so |
| `variant` | Several genuinely different versions behind a picker in the real page | Builds N times; expensive by design |

For image-only comps without code, `tastemaker` › comps mode is the non-gated
alternative to `variant`.
