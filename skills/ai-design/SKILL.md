---
name: ai-design
description: >-
  Entry point for the ai-engineering design skills. Works out what a design or
  frontend request actually needs, elects exactly one lead skill by matching
  the request's dominant constraint to what each skill is for, attaches
  supporting skills at a named part rather than whole, sequences the phases,
  resolves conflicts between skills, and runs the closing gates. Use at the
  START of any request to build, redesign, style, animate, review, or explain
  an interface, landing page, marketing site, dashboard, component, 3D scroll
  experience, or piece of UI copy — especially when more than one skill could
  plausibly apply, or when the request names no skill at all. Triggers on
  build a page, design this, make this look good, redesign, add motion, review
  this screen, which skill should I use, match this reference. Not for
  measuring an already-built page — use /ai-design-audit.
license: MIT
---

# ai-design

The installed design skills overlap heavily. Several will each claim a
"build me a landing page" request; more than one owns motion or color. Running
more than one lead produces a page built twice, in two token systems, with two
motion engines fighting each other.

This skill is the traffic controller. It does no design work of its own. It
decides **who leads, who advises, in what order, and who wins a disagreement** —
then hands off.

## Route by purpose, not by vocabulary

Requests rarely name the skill they need. "Something that feels like a film title
sequence" contains no keyword in the installed design skills, and matching on words sends it
to the generic fallback — which will build something competent and wrong.

So routing runs off a model of **what each skill is for**:
`references/skill-purposes.md` states, for every skill, the question it answers,
what it produces, what it assumes, and the signal that you picked it by mistake.
Read it when a route isn't obvious. It is the actual routing mechanism; the
tables below are its fast path.

## How to address a skill

Skills are named, never pathed. Skills get installed in different places
across editors and harnesses, and any path written here would be wrong in most
of them.

**Notation:** `` `skill-name` › topic `` means *the part of that skill covering
that topic*. `§Heading` refers to a section of that skill's own `SKILL.md`.

**Resolution, in order:** invoke it by name if it's registered → else locate its
directory wherever the collection lives, read its own `SKILL.md`, and follow the
routing table inside it → else use the section with that heading → else the skill
has changed, so use its nearest section and say so rather than inventing a
filename.

A topic is a *subject*, not a filename. Match on meaning.

## Operating posture

- Elect **exactly one Lead**. Everything else advises.
- Route to a **part**, not a whole skill. `` `tastemaker` › audit mode `` — not
  "use tastemaker."
- Load nothing speculatively. Every part you open should be one you named in the
  plan.
- Announce the plan in three lines before building. The user can veto a route
  before tokens are spent, not after.
- Three skills are user-invoked only (`disable-model-invocation: true`):
  `explain-interface`, `interface-review`, `variant`. Never auto-fire them. When
  a request belongs to one, say so and stop.

---

## Step 1 — Read three facts off the request

Not keywords. Three judgments, and the third does the work.

**1. State — what exists now?**

`nothing` · `works but looks wrong` · `looks fine but feels wrong` ·
`exists elsewhere as a reference to match` · `exists and I want to understand it`

**2. Deliverable — what does the user hold at the end?**

`a built thing` · `a judgment` · `an explanation` · `options to choose between` ·
`one effect added to something that already works`

**3. Dominant constraint — what, if wrong, makes everything else worthless?**

This is the discriminator. Name it in your own words before looking at any table.
A request usually has exactly one; when it has two, the second becomes a
consultant.

---

## Step 2 — Constraint → Lead

Match the constraint you named. The examples are deliberately keyword-free —
that's the point.

| Dominant constraint | Sounds like | Lead |
|---|---|---|
| **Someone must act.** Success is measurable in behavior. | "get people to sign up", "we're launching Tuesday and need people to book" | `landing-page-design` |
| **It must not look default.** Or: it must look like *this* specific thing. | "every page I make looks the same", "here's a screenshot, that feeling", "our site looks like a template" | `tastemaker` |
| **Meaning lives in moving through space.** Depth is load-bearing, not decorative. | "you scroll and travel through the product", "like walking through the archive" | `build-threejs-scroll-worlds` |
| **The impression is the product.** Judged on how the first seconds feel. | "like a film title sequence", "should feel expensive", "a studio site that wins us work" | `build-awwwards-quality-sites` |
| **Dense information must stay legible.** Or the artifact is a known non-page form. | "an ops dashboard", "a deck for the board", "show these six metrics" | `web-design-engineer` |
| **Movement is the deliverable itself.** | "the panel should come in nicely", "make this transition not feel abrupt" | `animate` |
| **One small thing, used constantly, must feel right.** | "the dropdown feels cheap", "our buttons feel dead" | `emil-design-eng` |
| **Understanding, not artifact.** | "why does theirs feel faster", "how do they do that" | Step 2b |
| **The decision itself is unmade.** | "I don't know what I want yet", "show me some directions" | Step 2b |

**No constraint is nameable.** Don't guess and don't default. Lead with
`web-design-engineer` › design calibration to set the five dials, or
`landing-page-design` §A1 if the thing is plainly a page for strangers — both
exist to extract the constraint. Then re-enter Step 2 with the answer. A build
started from no signal gets rebuilt.

### Step 2b — When the deliverable isn't a built thing

| Deliverable | Route |
|---|---|
| A judgment on a rendered screen — "wrong but I can't say why" | `screen-critique` |
| A judgment on a screen you can read the code for | `better-interface` — itself a router over the `better-*` family; let it do that |
| A judgment on a **change** — branch, PR, diff, uncommitted work | `interface-review` — **user-invoked.** Say so and stop. |
| A judgment that it's correct but cold | `interfaces-that-feel` |
| A judgment that it looks machine-made | `tastemaker` › audit mode |
| An explanation of someone else's page | `explain-interface` — **user-invoked.** |
| Reusable DNA extracted from a reference | `tastemaker` › study mode |
| Options, in code, in the real page | `variant` — **user-invoked.** |
| Options, as images | `tastemaker` › comps mode |
| Options, as written directions | `web-design-engineer` › design directions |

Written directions are the cheapest of the three option routes and usually
enough. Offer that first when the request is early-stage.

---

## Step 3 — Check the fast path agrees

For most requests the surface vocabulary points the same way the constraint does.
Walk this and stop at the first match; if it disagrees with Step 2, **Step 2
wins** and you should be able to say why in a sentence.

| # | If | Lead |
|---|---|---|
| 1 | Deliverable is a judgment, explanation, or options | Step 2b |
| 2 | One named effect, dropped into a working page | **no Lead** — see Step 5 |
| 3 | Scroll-driven 3D, WebGL, camera journey, spatial narrative | `build-threejs-scroll-worlds` |
| 4 | Awwwards / premium / cinematic / motion-led marketing | `build-awwwards-quality-sites` |
| 5 | Landing page, conversion page, hero + sections | `landing-page-design` |
| 6 | Reference to match, "AI slop", brand feel, "make it beautiful" | `tastemaker` |
| 7 | Dashboard, prototype, slide deck, data viz | `web-design-engineer` |
| 8 | Motion is the whole ask | `animate` |
| 9 | Single component, hover state, micro-interaction | `emil-design-eng` |
| 10 | Nothing matched | you skipped Step 2's no-constraint path — go back |

Rung 10 is not a fallback. A request that reaches it was never read for its
constraint.

### Discriminators for the close pairs

When two leads both fit, one question separates them. Ask it — of the request, or
of the user.

| Pair | The question |
|---|---|
| `landing-page-design` vs `tastemaker` | Is there a specific action a stranger must take? Yes → landing-page-design leads, tastemaker consults on palette and anti-slop. That pairing is the normal case, not a tie. |
| `tastemaker` vs `web-design-engineer` | Is the target a *pasted reference or a feeling*, or a *named brand style*? Reference/feeling → tastemaker. Named anchor, or a dashboard/deck/chart → web-design-engineer. |
| `build-awwwards-quality-sites` vs `tastemaker` | Does it need a motion system, or just to stop looking default? Motion system → awwwards. Restraint is a legitimate art direction and tastemaker reaches it cheaper. |
| `build-threejs-scroll-worlds` vs `build-awwwards-quality-sites` | Would 2D with parallax carry the same idea? Yes → awwwards. The 3D skill's own §Route the request correctly will say this too; believe it. |
| `animate` vs `emil-design-eng` | Does motion exist yet? No → animate builds it. Yes and it feels wrong → emil diagnoses it. |
| `emil-design-eng` vs `screen-critique` | Is the suspect one component, or the whole screen? Zooming into a button while the layout fails is the expensive version of this mistake. |
| `better-interface` vs `interface-review` | Screen, or diff? better-interface refuses diff scopes on purpose and hands up. Don't work around that by guessing. |
| `tastemaker` vs `perception-laws`/`better-layout` | Is it ugly, or badly *organized*? Grouping failures read as taste failures and aren't. |

---

## Step 4 — Attach consultants

The Lead owns the build. Consultants open at a **named part** when their trigger
fires, then close. Full map in `references/routing-table.md`; the load-bearing
rows:

| Trigger in the work | Open |
|---|---|
| Picking or extending a palette | `better-colors` › palette generation, then palette structure |
| Naming color tokens | `better-colors` › token naming |
| Any text over any background | `better-colors` › contrast |
| Choosing or pairing typefaces | `better-typography` › choosing fonts |
| Type scale, line-height, measure | `better-typography` › spacing and sizing |
| Truncation, wrapping, punctuation | `better-typography` › wrapping and punctuation |
| Deciding what groups with what | `perception-laws` (whole skill — it's short) |
| What collapses at small widths | `better-layout` › spacing and adaptivity |
| Custom widget, modal, menu, tabs | `better-accessibility` › semantics and ARIA, then focus and keyboard |
| Forms and their errors | `better-accessibility` › forms, and `better-writing` |
| Any button label, error, empty state | `better-writing` (whole skill) |
| Enter / exit animation | `better-ui` › enter and exit |
| Curve and duration choice | `animate` §The Build Sequence, or `emil-design-eng` §The Animation Decision Framework |
| Spring physics | `emil-design-eng` §Spring Animations |
| Shadows, radii, surfaces | `better-ui` › surfaces |
| Icons and icon transitions | `better-ui` › icons, and › icon transitions |
| Named visual anchor ("Linear-style") | `web-design-engineer` › the style recipe for that one anchor — **one only** |
| Extending an existing design rather than replacing it | `web-design-engineer` › redesign protocol |

## Step 5 — Attach ingredients

Self-contained recipes: own markup, own CSS/JS, own engine. They never lead and
never restructure. Assign each element exactly one.

`masked-reveal` (word-by-word text reveal on scroll) · `progressive-blur`
(stepped blur from a viewport edge) · `dither-background` (near-black
atmospheric field) · `container-lines` (editorial grid markers) ·
`reveal-hover-effect` (cursor spotlight over a second image) ·
`cinematic-gsap-lenis-motion-system` (the full premium-motion vocabulary).

An ingredient request needs no Lead and no design pass. Read it, drop it in,
match the host page's tokens, done.

## Step 6 — Sequence the phases

```
0  Intake      Lead's own intake step. landing-page-design §A1 is the
               strongest one — borrow it if the Lead has none.
1  Direction   Palette, type pairing, mood, tokens. Locks before any markup.
2  Structure   Sections, grouping, hierarchy. perception-laws applies here.
3  Build       Markup + CSS. Ingredients drop in. States: empty, loading,
               error, narrow.
4  Motion      One engine only (see conflicts). After layout is stable.
5  Gates       Below. Non-negotiable.
```

Re-entering an earlier phase is cheap. Skipping forward is not: motion added over
an unstable layout is thrown away.

## Step 7 — Gates

Run every one before declaring done. A failure sends the work back to its phase,
not to the user.

| Gate | Source |
|---|---|
| Contrast on every text/background pair | `better-colors` › contrast |
| Keyboard path, focus visible, no trap | `better-accessibility` › focus and keyboard |
| `prefers-reduced-motion` honored | `better-accessibility` › motion and zoom |
| Hit areas clear the floor, no hover-only affordance | `better-accessibility` › hit areas |
| Every user-facing string reads like a person wrote it | `better-writing` |
| Composition reads as intended | `screen-critique` |
| Doesn't look machine-generated | `tastemaker` › anti-slop checklist |
| Motion budget: nothing gratuitous | `animate` §Never Ship |

## Step 8 — Announce, then build

Three lines, before any file is touched. Name the constraint — it's what makes
the route checkable.

```
Constraint:  someone must book a demo; secondary — must not look like a template
Lead:        landing-page-design
Consulting:  tastemaker › anti-slop checklist · better-colors › palette generation
             · better-typography › choosing fonts · perception-laws
Ingredients: masked-reveal (hero)
Phases:      direction → structure → build → motion → gates
```

Then execute. Don't re-announce at every phase.

---

## You routed wrong — the signals

Mid-build symptoms that mean re-route rather than push harder. Catching one at
Phase 2 costs minutes; at Phase 4, a rebuild.

| Symptom | Likely misroute |
|---|---|
| The lead's intake questions have no sensible answers | Wrong band — you brought a strategy skill to an aesthetic problem, or the reverse |
| You're inventing content to fill sections the lead prescribed | `landing-page-design` on a page with no conversion target |
| The palette keeps coming out fine and the page still looks wrong | It's structural. `perception-laws` and `better-layout`, not `tastemaker` |
| You're fighting the motion engine on every element | Two engines. See `references/conflicts.md` rung 3 |
| Polishing one component while the screen around it is unresolved | `emil-design-eng` too early; go up to `screen-critique` or `better-interface` |
| The 3D world is mostly text panels floating in space | It was a 2D page. `build-awwwards-quality-sites` |
| Every gate passes and it still feels dead | Correctness done, feel missing. `interfaces-that-feel` |

## Conflicts

`references/conflicts.md` is the tiebreaker. Three rules worth memorizing:

1. **The Lead owns structure and tokens.** A consultant may flag a hard-rule
   violation; it may not substitute its own spacing scale, radius, or section
   order.
2. **One motion engine per project.** GSAP + Lenis, or CSS/Web Animations, never
   both.
3. **Hard rules outrank every Lead**: contrast, keyboard access,
   `prefers-reduced-motion`, hit area.

## Gaps in the installed set

Some routes below name siblings that may not be installed. Check first — the
set gets extended. If genuinely absent, substitute rather than reporting a dead
end:
`review-animations` → `animate` §Never Ship with `better-ui` › animations ·
`improve-animations` → `emil-design-eng` §Review Checklist across the codebase ·
`aesthetic-usability` → `interfaces-that-feel`.

## Files

Bundled with this skill:

- `references/skill-purposes.md` — what every skill is *for*; the routing model
- `references/routing-table.md` — which part of a skill to open, once elected
- `references/conflicts.md` — precedence rules in full
- `references/plans.md` — worked plans for the twelve common request shapes

## The ai-engineering seam

1. The routing table points at what is installed at runtime; it never bundles a
   skill that is not there.
2. Write `.ai-engineering/design/direction.html` BEFORE any code: the elected
   direction (palette, type, tokens, motion stance) is the artifact the human
   approves in step 1.
3. The anti-slop gate is routed, not bundled: the anti-slop checklist runs as its
   own routed check against what is installed at runtime.
4. The conflict ladder in `references/conflicts.md` stays intact and owns
   precedence between skills.

Source: design-orchestrator from the claude-design-skills collection (attributed;
no license — upstream issue H4).
