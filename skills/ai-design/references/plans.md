# Worked plans

Twelve request shapes that cover most of what arrives. These are **pre-solved
routes, not the routing method** — each one already has its constraint named, so
matching a shape saves you the Step 1–2 read. If a request doesn't clearly match
one, don't stretch it to fit: go back to `SKILL.md` Step 1 and read the request
for its dominant constraint, with `skill-purposes.md` open.

Each plan states the constraint it assumes. If that constraint isn't the
request's real one, the plan is the wrong plan however well the surface matches.

`` `skill-name` › topic `` addresses a part of a skill; `§Heading` a section of
its `SKILL.md`. Resolve topics through the skill itself, never through a path.

---

## 1. "Build me a landing page for X"

```
Constraint:  a stranger must take a specific action
Lead:        landing-page-design
Consulting:  tastemaker › anti-slop checklist, macrostructures
             better-colors › palette generation, contrast
             better-typography › choosing fonts, spacing and sizing
             perception-laws · better-writing
Engine:      CSS
```

0. `landing-page-design` §A1 intake — ask the questions, don't invent answers.
1. §A2/§A3 structure and layout, cross-checked against `tastemaker` ›
   macrostructures so the section order isn't the default one.
2. Palette via `better-colors` › palette generation; type via
   `better-typography` › choosing fonts. Lock both before markup.
3. Copy from §A5. Every string also passes `better-writing`.
4. Build in §A6 order, applying §B1–B7 literals.
5. §B7 motion, CSS only.
6. Gates: contrast · keyboard · reduced-motion · anti-slop checklist ·
   `screen-critique`.

---

## 2. "Build me an Awwwards-quality site"

```
Constraint:  the impression is the product; judged on the first seconds
Lead:        build-awwwards-quality-sites
Consulting:  cinematic-gsap-lenis-motion-system (Phase 4)
             tastemaker › asset curation, logo sourcing
             better-accessibility › motion and zoom
Ingredients: as chosen at stage 3–4
Engine:      GSAP + Lenis
```

Stages 1–2 before any markup. Stage 5 — Three.js — only if stage 1's art
direction actually needs it; if it does, the lead changes to
`build-threejs-scroll-worlds` and this becomes the consultant.

Motion implementations come from `cinematic-gsap-lenis-motion-system`; respect
its §Init Order or the scroll and the reveals will fight.

---

## 3. "This looks like every other AI site — fix it"

```
Constraint:  it must stop looking default — aesthetic, not structural
Lead:        tastemaker (build mode, after an audit pass)
Consulting:  better-colors · better-typography · perception-laws
Engine:      keep whatever the project already uses
```

1. `tastemaker` › audit mode first — diagnose, ranked, no edits.
2. Show the punch list. Get a yes.
3. `tastemaker` §Workflow to fix, top-severity first.
4. `tastemaker` › diversification so the fix isn't a different generic.
5. Re-run its anti-slop scan.

Do not skip step 1. Rewriting before diagnosing produces a second generic page.

---

## 4. "Make this look like Linear / Aesop / Stripe Press"

```
Constraint:  match one named brand style, not a pasted reference
Lead:        web-design-engineer
Consulting:  › the style recipe for that one anchor  ← one only
             › redesign protocol, if the thing already exists
```

Read exactly one recipe. Reading three produces a blend that resembles none of
them. If the user names a vibe rather than a brand, open the style-recipe index,
propose two or three anchors that are actually installed, let them pick, then
read one.

---

## 5. "Build a scroll-driven 3D experience"

```
Constraint:  meaning lives in moving through space; depth is load-bearing
Lead:        build-threejs-scroll-worlds
Consulting:  › world bible → scene anatomy → realtime architecture
             › its scroll conductor
             better-accessibility › motion and zoom
Engine:      GSAP + the skill's own conductor
```

§Route the request correctly first — it will send genuinely 2D requests back.
World bible before code, always. The perf budget under §Hold a measurable
performance budget is a gate, not an aspiration.

---

## 6. "Add a progressive blur / dither / container lines / spotlight hover"

```
Constraint:  none at page scale — one element, one effect
Lead:        none
Ingredient:  the named skill
Gate:        better-accessibility › motion and zoom, if it moves
```

Read the ingredient, drop it in, match the host page's tokens. Do not restructure
around it, do not open the lead ladder, do not run a full design pass. One
element, one ingredient.

---

## 7. "Animate this" / "add motion"

```
Constraint:  movement is the deliverable, and none exists yet
Lead:        animate
Consulting:  better-ui › enter and exit, animations
             emil-design-eng §The Animation Decision Framework, §Spring Animations
             better-accessibility › motion and zoom
Engine:      whatever the project already uses
```

`animate` §The Build Sequence in order. Its first question — *should this animate
at all* — is a real question; a meaningful share of requests end there. §Never
Ship is the gate.

If motion already exists and the complaint is that it feels wrong, lead with
`emil-design-eng` §Debugging Animations instead.

---

## 8. "This component feels off"

```
Constraint:  one small thing, used constantly, must feel right
Lead:        emil-design-eng
Consulting:  better-ui › surfaces, icons
             better-layout › grouping and alignment
             better-typography › spacing and sizing
```

§Initial Response, then §Review Format. Concentric radius, optical alignment,
and interruptible motion account for most "feels off" reports — check those three
before reaching further.

---

## 9. "Review this screen"

```
Deliverable: a judgment, not a built thing
Lead:        none — this is a review
Route:       better-interface  (it routes across every better-* skill itself)
Or:          screen-critique   (rendered image, seven dimensions, rated)
```

`better-interface` for code you can read. `screen-critique` for a rendered
screen or artboard. Both when the screen is bad and the code is available.

No file edits during a review. Findings first; the user decides what to fix.

---

## 10. "Review my branch / PR / uncommitted work"

```
Deliverable: a judgment scoped to a diff
Route:       interface-review  — USER-INVOKED ONLY
```

Say that this is a change review, that `interface-review` owns it, and that the
user needs to run it. Do not resolve the diff scope yourself and do not run
`better-interface` on it as a substitute — `better-interface` explicitly refuses
this scope and hands it up here.

---

## 11. "Show me a few directions"

```
Deliverable: options to choose between — the decision is unmade

In code, in the real page:    variant  — USER-INVOKED ONLY
As images, no code:           tastemaker › comps mode
As written directions:        web-design-engineer › design directions
```

Ask which of the three they want if it isn't obvious. Written directions are the
cheapest and often enough — offer that first when the request is early-stage.

---

## 12. "Build the frontend for X" — no design signal at all

```
Constraint:  none nameable yet — extract it before building
Lead:        web-design-engineer
First:       › design calibration  (five dials)
Then:        › design directions   (propose 3, get a pick)
```

Then re-enter the ladder with the picked direction — a chosen direction often
promotes a different lead. "Editorial, motion-led" lands on
`build-awwwards-quality-sites`; "clean product UI" stays here; "conversion page"
moves to `landing-page-design`.

Resist building before the dials are set. A frontend built from no signal gets
rebuilt.

---

## Escape hatch

If the request matches no shape and no ladder rung, say what you think it is,
name the two leads you're choosing between, and ask. One question, then commit.
