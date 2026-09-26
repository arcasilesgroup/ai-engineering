---
name: ai-design-md-planner
description: Interviews the user about their product and visual taste, commits to a specific referenced aesthetic direction, and writes a DESIGN.md design system file in Google's DESIGN.md format — then audits it with the official `@google/design.md` CLI until it lints clean. Use this skill whenever the user wants a design system, design tokens, a DESIGN.md, a style guide, a brand/visual identity, a color palette or type scale for a product, wants to "make this look good" or "not look AI-generated," wants to codify the design of an existing app or site, or is starting a UI/frontend project and hasn't pinned down its visual language yet — even if they never say the words "design system" or "DESIGN.md."
license: MIT
---

# DESIGN.md — design systems that don't look AI-generated

Two jobs, and the second one is the hard one.

**Job one** is mechanical: produce a valid DESIGN.md (Google's format — YAML token frontmatter + markdown rationale) that passes `npx @google/design.md lint` clean. The spec is bundled in `references/designmd-spec.md`; the CLI workflow and every lint rule is in `references/cli.md`.

**Job two** is taste: produce a system with an actual point of view. This is where almost every attempt fails, so it's worth understanding *why* it fails before starting.

## Why AI design looks like AI design

When a model is asked for "a modern, clean design," it returns the statistical center of everything it has seen: indigo-violet primary, Inter, `rounded-2xl` with a soft shadow, a centered hero, a three-column feature grid with icons in tinted rounded squares. Each individual choice is defensible. Together they read as machine-made — not because they're ugly, but because they're **unauthored**. There is no person behind them, no argument, nothing that could have gone differently.

Real design reads as real because someone *decided* something and gave up something else in exchange. A design system with no sacrifices in it is slop.

So the working principle for this whole skill:

> **Every value in the file must trace to a source or an argument.** Not "a nice blue" — *this* blue, because it's the oxide on weathered copper, or because it's the exact ink of a 1968 Braun manual, or because the product is used at 2am in a dark room and this is the only blue that survives at 4% opacity. If a token can't be defended, it was picked from the middle of the distribution and it will look like it.

`references/anti-slop.md` catalogs the specific defaults to avoid and, more usefully, what to do instead. Read it before writing any tokens — it's the highest-leverage file here.

---

## Step 0 — Pick the mode

**Codify-existing** — the user points at a repo, a URL, screenshots, an existing brand, or says "match what we have." Their visual language already exists; the job is to extract it, judge it, and write it down.

**Greenfield** — an idea with no visual language yet. The job is to invent one.

They mix: a repo may have half a system that needs finishing. Say which mode you're in so the user can correct you.

### Codify-existing: extract first, then judge

Before proposing anything, find out what's actually there. Look for `tailwind.config.*`, `theme.css`, `@theme` blocks, `:root` custom properties, `globals.css`, styled-components themes, Figma token exports, `_variables.scss`. Grep the components for hardcoded hex values and font stacks — the gap between the declared theme and the hardcoded reality is usually the most interesting finding.

Then report honestly, because this is the moment the user learns something they didn't know:

- **What's consistent** — becomes a token, unchanged.
- **What's drifted** — 14 near-identical greys, 5 border radii, 3 versions of "primary." Consolidate and say what you collapsed into what.
- **What's slop** — untouched Tailwind defaults, `#6366F1`, Inter-by-default, shadow-on-everything. Name it plainly and propose a specific replacement. Don't launder existing slop into the DESIGN.md just because it's already shipped; a design system that codifies the mistakes makes them permanent.

Then jump to Step 2 with a direction that's *already implied* by the good parts of what exists, and confirm it rather than starting from a blank slate.

### Greenfield: intake

You need enough to make real choices. Ask for what's missing, but pull what you can from context first — the repo, the conversation, the product name. Don't interrogate the user for things you can infer.

What actually changes the design:

- **What is it, and who uses it under what conditions?** A dashboard read for 8 hours by an analyst and a landing page seen once for 20 seconds want opposite things: density and low-fatigue neutrals vs. contrast and a single loud gesture.
- **What should someone feel in the first second?** Push for a specific adjective. "Modern" and "clean" mean nothing — everything wants to be those. "Expensive," "fast," "trustworthy in a boring institutional way," "a little unhinged" are usable.
- **Light, dark, or both?** Both doubles the palette work and constrains hue choices (many colors that sing on white die on black). Ask; don't assume both.
- **Hard constraints** — existing logo/brand colors, accessibility target, a framework whose idioms you're stuck with, a competitor to deliberately not resemble.
- **What do they already like?** The single most valuable question. Ask for two or three products, sites, magazines, album covers, or physical objects whose look they'd defend. Real references beat any adjective. If they name something, actually look at it (WebFetch the site, read what it does) rather than working from your memory of it.

---

## Step 1 — Propose concrete directions, never adjectives

This is where slop gets prevented or baked in. If the user says "modern and clean" and you accept it, you have no constraint and will drift to the center of the distribution. So convert vagueness into a choice between specific, named, referenced aesthetics.

Read `references/style-directions.md` and pick **3–4 directions that genuinely fit this product** — not a random sample. Each gets an honest one-liner: what it commits to, and what it gives up.

Use `AskUserQuestion` if available, one question, four options. Make each label a real name, not a mood:

> **Swiss Editorial** — Mueller-Brockmann grid discipline, flush-left, near-black ink on warm paper, one signal red for anything clickable. Serious and quiet. Gives up: warmth, playfulness, any decoration.
>
> **Terminal Precision** — Linear/Bloomberg density. Warm charcoal (not navy), monospace for all numerics, borders instead of shadows, small type. Rewards expert users. Gives up: approachability for newcomers.
>
> **Warm Analog** — Aesop-adjacent. Off-white paper stock, no pure white or black, muted clay accent, generous margins, serif body. Calm and tactile. Gives up: information density.
>
> **Archival Institutional** — museum/library register. Transitional serif display, hairline rules, restrained ochre, respect for dense text. Credible and permanent. Gives up: any sense of speed or novelty.

Two things to hold onto here:

- **Blending is fine and often better than a pure pick.** "Terminal density with editorial serif headings" is a real, specific system. What isn't fine is blending three directions until the distinctions cancel out and you're back at the center.
- **If the user says "you pick" — pick, and commit.** Don't split the difference to be safe. State the direction and its tradeoff in one sentence and move.

Once a direction is chosen, it is a constraint with teeth. When a later decision is genuinely open, resolve it by asking "what would this direction do?" — not by falling back to defaults.

---

## Step 2 — Derive the system

Now build the actual values. Depth guides, read as needed:

| Need | Read |
|---|---|
| Building a palette that doesn't look stock | `references/color-craft.md` |
| Choosing and pairing typefaces, building the scale | `references/typography.md` |
| Checking yourself against known failure patterns | `references/anti-slop.md` |
| The direction's specific palette/type/shape rules | `references/style-directions.md` |

The condensed version:

**Colors.** Anchor the primary hue to something real and name the referent in the prose — it's what makes the file feel authored. Build ramps in OKLCH so the lightness steps are perceptually even, then convert to hex for the tokens (hex is the recommended default and has the broadest tooling support). Bend the hue slightly across each ramp and taper chroma at the light and dark ends; ramps with flat chroma and a straight hue line are the signature of a generated palette. **Tint the neutrals** — pure `#808080`-family greys are the loudest tell that nobody looked at this. Derive semantic colors (error/success/warning) from the brand family rather than dropping in stock red and green. Give the accent exactly one job and use it on under 5% of the surface; an accent that appears everywhere isn't an accent.

**Typography.** Two typefaces is the sweet spot — one does the talking, one does the labeling — and they should differ by *classification*, not just by weight. Pick a modular ratio (≈1.2 for dense UI, ≈1.333 for editorial) to generate the scale, then hand-tune the display end, because pure geometric scales are timid where they should be loud. Set optical tracking deliberately: negative on large display sizes, positive on small uppercase labels. Line height moves inversely to size. Cap it at two or three weights and space them far apart — 400/700 reads as a decision, 400/500/600 reads as a default. The typeface library with open-source alternatives is in `references/typography.md`.

**Shape, elevation, layout, motion.** Radius should be *hierarchical*, not uniform — one value on everything is the `rounded-2xl` tell. Prefer borders, tonal shifts, and spacing to convey depth; if you use shadows, they should have a light direction and a color drawn from the palette, never neutral black at 10%. Set a spacing base (4px or 8px) and stay on it. Decide whether the layout is symmetric-centered or asymmetric — asymmetry is a strong anti-slop move but has to be committed to, not sprinkled. For motion, name the easing and durations and say what *doesn't* animate; universal fade-up-on-scroll is a tell.

---

## Step 3 — Write DESIGN.md

Start from `assets/DESIGN.template.md` (a commented skeleton — strip the comments on the way out). `assets/DESIGN.example.md` is a complete worked system that lints with zero errors and zero warnings; read it when you want to see the intended depth of the prose, since that's the part most likely to come out thin. Full format details in `references/designmd-spec.md`.

Write it to `.ai-engineering/DESIGN.md` unless the user says otherwise — every skill and agent in this workflow reads it from there, and that discoverability is most of its value. Run the lint commands in `references/cli.md` against that path.

Sections must appear in this order (any may be omitted, but present ones are ordered): **Overview → Colors → Typography → Layout → Elevation & Depth → Shapes → Components → Do's and Don'ts**.

Two rules of thumb that matter more than they look:

**The prose carries the argument; the tokens carry the values.** The tokens are normative — an agent building UI reads those. The prose is what stops a future agent from making a plausible-but-wrong call in a situation you didn't tokenize. So write the prose as *reasoning*, not as a restatement of the hex codes. "Tertiary (#B8422E) is the sole driver of interaction — used for primary actions and critical highlights only" earns its place. "Tertiary is #B8422E" does not. Use the descriptive color name in prose ("weathered oxide") and the systematic name in tokens (`tertiary`); the spec explicitly supports this pairing and it's what makes the document readable by humans.

**Wire the components section properly.** Components are where tokens become usable, and the linter checks two things through them: `orphaned-tokens` fires on any token no component references, and `contrast-ratio` checks each component's `backgroundColor`/`textColor` pair against WCAG AA (4.5:1). Both are load-bearing. Define components with `{colors.x}` / `{typography.y}` / `{rounded.z}` references rather than literal values, cover the real states (`button-primary`, `button-primary-hover`, `button-secondary`, `input`, `input-error`, `card`, `chip`, `tooltip`), and always define background and text together so contrast is actually checkable.

**Do's and Don'ts is not filler.** It's the section that survives contact with a future agent under time pressure. Make each line specific and enforceable for *this* system — "Don't introduce a second accent color; if something needs emphasis, use weight or space" — not generic advice like "maintain good contrast."

---

## Step 4 — Audit with the CLI, and actually fix things

The official CLI is the objective check. Full command reference and a fix for every rule is in `references/cli.md`.

```bash
npx -y @google/design.md@latest lint --format json DESIGN.md
```

(Windows PowerShell: `npx -y -p @google/design.md designmd lint --format json DESIGN.md` — the `design.md` name collides with file associations.)

Exit code is 1 if there are errors, 0 otherwise. Iterate until:

- **zero errors** — `broken-ref` means a `{path.to.token}` doesn't resolve; non-negotiable.
- **zero warnings, or a deliberate `omitted` entry.** `orphaned-tokens` and `missing-*` warnings usually mean the system is genuinely incomplete — fix the design rather than silencing the rule. But if a section truly doesn't apply (a CLI tool with no rounded corners), declare it with a reason so the intent is recorded:
  ```yaml
  omitted:
    - section: rounded
      reason: "Zero-radius is a fixed property of the direction, not a scale"
  ```
- **`contrast-ratio` warnings resolved by changing colors, not by deleting the pair.** Removing `textColor` from a component to silence the check is how a design system becomes a liability.

Report the before/after finding counts to the user so the audit is visible, not just asserted.

---

## Step 5 — Read it back with fresh eyes

The linter validates structure; it cannot tell you the design is generic. Do this pass yourself before handing off, and be honest — catching a problem here is cheap, catching it after a codebase is built on it is not.

- Could a specific person have made this, and would they defend it? Or is every choice the safe median?
- Is there a **sacrifice** in it — something clearly given up in exchange for something else? If not, it's not a direction, it's a default.
- Run the slop checklist at the end of `references/anti-slop.md`. Any hit needs either a fix or a genuine reason.
- Do the tokens and the prose still agree? Values drift during lint fixes and the prose silently goes stale.
- Would an agent handed *only* this file build the right thing — including for a screen you never mentioned? That's the actual job of the document.

Then hand it over: where the file is, the direction chosen and what it trades away, the audit result, and anything you flagged but left for the user to decide.

## Lifecycle

Lane: full
Writes: .ai-engineering/DESIGN.md
Read by: ai-prototype, humans
Dies: when the next design pass rewrites it
Next: none
