# What each skill is for

The routing model. Not trigger words — the *job*. Route by matching a request's
shape to a skill's job, and keyword matching becomes a shortcut you can check
rather than the mechanism you depend on.

Each entry states four things:

- **Answers** — the question it exists to settle
- **Produces** — what you hold when it's done
- **Assumes** — what must already be true before it's useful
- **Wrong when** — the signal you picked it by mistake

`` `skill-name` › topic `` addresses a part of a skill. Resolve topics through
the skill itself, never through a path.

---

## Skills that can own a build

These bring a workflow, a token system, and usually a motion engine. Exactly one
runs.

### `landing-page-design`
- **Answers** — what sections, in what order, with what words, so a stranger acts?
- **Produces** — a page whose structure and copy are argued for, plus literal visual values (sizes, radii, spacing).
- **Assumes** — there is a specific action you want taken, and a specific person you want taking it.
- **Wrong when** — nobody needs to *do* anything. An about page, a portfolio, a docs home, an internal dashboard: no conversion, no reason for this skill's machinery.

The most opinionated skill here. Its Part B hands you numbers, not principles —
which is why it wins ties on pages it leads, and why it's a poor consultant
elsewhere.

### `tastemaker`
- **Answers** — why does this look machine-made, and what would make it look authored?
- **Produces** — a palette, a structure, and asset choices that don't collapse to the default; a memory of those decisions for next time.
- **Assumes** — the problem is aesthetic, not structural. Someone can tell good from bad but can't produce it.
- **Wrong when** — the page is ugly because it's badly *organized*. Grouping and hierarchy failures look like taste failures and aren't; that's `perception-laws` and `better-layout`.

The only skill that treats "generic" as a diagnosable defect with a gate list
rather than a vibe.

### `web-design-engineer`
- **Answers** — how do I build this browser-rendered thing well, in whatever style we pick?
- **Produces** — pages, dashboards, prototypes, slide decks, data viz, mockups; plus, when the request is vague, three named directions to choose between.
- **Assumes** — nothing. Widest scope in the collection, which is why it's the fallback.
- **Wrong when** — a narrower skill matched and you took this anyway. It will do a competent job where `landing-page-design` or `tastemaker` would have done a specific one.

Its style-recipe library is the collection's answer to "make it look like *that*"
when *that* is a known brand rather than a pasted image.

### `build-awwwards-quality-sites`
- **Answers** — how do I make a site feel authored, cinematic, deliberately art-directed?
- **Produces** — art direction, an honest asset system, a standout hero, GSAP choreography, one smooth-scroll engine, quality and perf safeguards.
- **Assumes** — the impression *is* the deliverable. Someone will judge this on how it feels in the first three seconds.
- **Wrong when** — there's a conversion target the motion is getting in the way of, or the budget can't carry a motion system. Restraint is a legitimate art direction; this skill is not the way to arrive at it.

### `build-threejs-scroll-worlds`
- **Answers** — how do I make scrolling feel like travelling through one continuous place?
- **Produces** — a persistent 3D world with authored chapters: camera, lighting, atmosphere, materials, a semantic DOM story, a perf budget.
- **Assumes** — the meaning genuinely lives in space and movement through it, not in text with decoration on top.
- **Wrong when** — a 2D page with parallax would carry the same idea. Its own §Route the request correctly will say so; believe it.

### `emil-design-eng`
- **Answers** — why does this component feel cheap, and what specifically makes software feel expensive?
- **Produces** — judgments and fixes at the level of a single component: radius, alignment, interruption, spring, gesture, stagger.
- **Assumes** — something exists and mostly works. This is a polish skill.
- **Wrong when** — the component is fine and the *page* is wrong. Zooming in on a button while the layout fails is a common and expensive mistake.

Deepest motion reasoning in the collection, which is why it consults far more
often than it leads.

### `animate`
- **Answers** — should this move, and if so, how — in the order that determines whether it feels right?
- **Produces** — an implemented animation, with the decisions made in sequence: purpose → tool → properties → curve → interruption → exit.
- **Assumes** — nothing moves yet.
- **Wrong when** — motion already exists and feels wrong. That's diagnosis, and it belongs to `emil-design-eng` §Debugging Animations.

Its first question is genuinely open. A real share of requests correctly end at
"it shouldn't animate."

---

## Skills that judge

No edits. Findings, ranked.

### `screen-critique`
- **Answers** — this looks wrong and I can't say why; what is it?
- **Produces** — seven rated dimensions (hierarchy, composition, typography, colour, density, affordance, brand) and a prioritized fix list.
- **Assumes** — you have something rendered to look at.
- **Wrong when** — you have code and a specific worry. Then a domain skill answers directly instead of scoring seven things.

### `better-interface`
- **Answers** — is this screen good, across every domain at once?
- **Produces** — one consolidated ranked verdict, having routed the screen through the `better-*` family itself.
- **Assumes** — a screen, flow, or feature you can inspect. Not a diff.
- **Wrong when** — the scope is a change. It refuses that on purpose and hands up to `interface-review`.

This is a router. Don't hand-run its members and reassemble their output.

### `interface-review` · user-invoked
- **Answers** — did this change make the interface worse?
- **Produces** — findings scoped to what the diff touched, classified as introduced or regression.
- **Assumes** — a branch, PR, commit range, or uncommitted work.
- **Wrong when** — never route around it. Guessing at a diff scope produces a report nobody can check.

### `explain-interface` · user-invoked
- **Answers** — how was this built?
- **Produces** — the layers that produce an effect, read off a live page; from a screenshot, a labelled reconstruction.
- **Assumes** — curiosity, not a build task.
- **Wrong when** — the user wants the effect, not the explanation. Then it's an ingredient or `animate`.

### `variant` · user-invoked
- **Answers** — which of these?
- **Produces** — several genuinely different versions behind a picker in the real page, then promotes one.
- **Assumes** — the axis of disagreement is real and nameable. Not tints of the same idea.
- **Wrong when** — one answer is clearly right and the ask is really "is this good?" That's a review.

---

## Skills that supply a domain

Consultants. Opened at a named part, then closed. None of them lead.

### `better-colors`
- **Answers** — what colors, named how, and does this pair actually pass?
- **Assumes** — you're building or auditing, and the palette is in play.
- **Wrong when** — the complaint is that the page is drab but the palette is fine. Drab is usually contrast *range* and hierarchy, not hue.

### `better-typography`
- **Answers** — which faces, at what scale, wrapping how?
- **Wrong when** — the type is fine and the *measure and rhythm* are the problem. Adjacent, and it does cover that — but check `better-layout` too.

### `better-layout`
- **Answers** — what goes where, what groups with what, what survives a narrow screen?
- **Wrong when** — the arrangement is right and the *reason* the eye misreads it is perceptual. Then `perception-laws` explains it and this skill implements the fix.

### `better-ui`
- **Answers** — what are the small things that read as polish?
- Concentric radius, optical alignment, elevation vs structure, interruptible motion, icon weight.
- **Wrong when** — you need to *decide* about motion rather than check it. Deciding is `animate` or `emil-design-eng`.

### `better-accessibility`
- **Answers** — can everyone actually use this?
- **Assumes** — nothing. It applies to every build, always, and its rules outrank every aesthetic argument.
- **Wrong when** — never. It is a gate on all work, not a choice.

### `better-writing`
- **Answers** — does this text sound like a person wrote it for another person?
- **Assumes** — there are user-facing strings, which there always are.
- **Wrong when** — never, for any build that renders words.

### `perception-laws`
- **Answers** — why does the eye group, skip, or misread this?
- **Produces** — the mechanism (proximity, similarity, common region, figure-ground, Hick, Miller, Fitts) behind a composition choice.
- **Assumes** — you're about to place things, or just did and it reads wrong.
- **Wrong when** — used as a post-hoc justification. Its value is at Phase 2, before the layout sets.

### `interfaces-that-feel`
- **Answers** — it passes every check and still lands cold; what now?
- **Produces** — prescriptions at the copy, motion, and interaction layer. Emotional timing, voice by state, motion as signal.
- **Assumes** — the interface is already correct. This is the last layer, not a rescue.
- **Wrong when** — it's cold because it's *broken*. Fix the breakage first; warmth won't paper over it.

---

## Skills that supply one effect

Ingredients. Each brings its own markup and CSS/JS, restructures nothing, and
declares an engine. Assign each element exactly one.

| Skill | The effect | Engine |
|---|---|---|
| `cinematic-gsap-lenis-motion-system` | The full premium-motion vocabulary: staggered text, scroll reveals, clip reveals, parallax, pinned sections, magnetic hover, custom cursor, mouse-reactive layers | GSAP + Lenis |
| `masked-reveal` | Text revealing word by word through an overflow mask on scroll | GSAP ScrollTrigger |
| `progressive-blur` | Stepped `backdrop-filter` fading from a viewport edge | CSS |
| `dither-background` | Near-black atmospheric field, enlarged pixels, ordered dithering | Canvas/shader |
| `container-lines` | Vertical container guides with corner squares — editorial grid markers | CSS |
| `reveal-hover-effect` | Cursor-following spotlight exposing a second aligned image | JS + CSS |

`cinematic-gsap-lenis-motion-system` is large enough to feel like a lead. It
isn't: no intake, no structure, no content strategy, no view on what the page
should say. It supplies motion to someone else's page.

---

## The shape of the collection

Reading the whole set at once, four bands:

1. **Strategy** — what should exist and why. `landing-page-design` §A,
   `web-design-engineer` › design directions, `tastemaker` › macrostructures.
2. **Aesthetic** — what it should look like. `tastemaker`,
   `web-design-engineer` style recipes, `build-awwwards-quality-sites`.
3. **Correctness** — the `better-*` family, `perception-laws`.
4. **Feel** — the last 5%. `emil-design-eng`, `animate`, `interfaces-that-feel`,
   the ingredients.

Most bad routes are band errors: answering an aesthetic question with a
correctness skill, or a strategy question with an aesthetic one. When a route
feels off, check the band before checking the skill.
